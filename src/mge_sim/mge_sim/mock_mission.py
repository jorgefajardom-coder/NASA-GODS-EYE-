"""MOCK mission manager.

Stand-in for the mission authority: accepts a goal, asks the planner for a
route, publishes the route in force, and replans from the agent's current
pose when the map version changes. It covers IDLE / PLANNING / READY / REPLAN
/ BLOCKED only. It has no tasks, precedences or execution; those belong to
the real mge_mission package.
"""
import math
from copy import deepcopy

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path
import rclpy
from rclpy.node import Node

from mge_interfaces.msg import (
    AgentState, MissionEvent, MissionState, RouteDecision, TerrainMeta)
from mge_interfaces.srv import PlanRoute, SetMissionGoal
from mge_sim.common import (
    agent_state_topic, LATCHED, RELIABLE, SRV_PLAN_ROUTE, SRV_SET_GOAL,
    TOPIC_ACTIVE_PATH, TOPIC_MISSION_EVENTS, TOPIC_MISSION_STATE, TOPIC_TERRAIN_META)
from mge_sim.mock_agents import load_agents
from mge_sim.recovery import remaining_allocation, stamp_key, stopped_after

S = MissionState
E = MissionEvent

# Planner answers that only mean "the new map batch has not arrived yet".
TRANSIENT = {'MAP_NOT_READY', 'SNAPSHOT_INCOMPLETE', 'MAP_VERSION_MISMATCH',
             'SNAPSHOT_CHANGED_DURING_SEARCH'}
MAX_RETRIES = 20
# The planner search is time-limited, so SEARCH_LIMIT can be an effect of load
# (for instance while it ingests a new map batch). A few more tries tell that
# apart from a search that really does not fit in the limit.
MAX_LIMIT_RETRIES = 2
RETRY_PERIOD_S = 0.25


class MockMission(Node):

    def __init__(self):
        super().__init__('mock_mission')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        agents_file = self.declare_parameter('agents_file', '').value
        self.require_stop_ack = self.declare_parameter('require_stop_ack', False).value
        self.stop_ack_timeout_s = self.declare_parameter('stop_ack_timeout_s', 5.0).value
        if not math.isfinite(self.stop_ack_timeout_s) or self.stop_ack_timeout_s <= 0:
            raise ValueError('stop_ack_timeout_s must be positive and finite')

        self.state = S.STATE_IDLE
        self.reason = ''
        self.seq = 0
        self.map_version = 0
        self.agents = {}
        self.goal = None            # SetMissionGoal.Request in force
        self.pending = None         # request_id of the plan we are waiting for
        self.attempt = 0            # plan requests sent for the current goal and map
        self.retry_timer = None
        self.route = RouteDecision()
        self.answers = {}           # request_id -> SetMissionGoal.Response
        self.stop_barrier = None
        self.stop_deadline = None
        self.goal_resources = None
        self.dispatched = None

        self.pub_event = self.create_publisher(E, TOPIC_MISSION_EVENTS, RELIABLE)
        self.pub_state = self.create_publisher(S, TOPIC_MISSION_STATE, LATCHED)
        self.pub_path = self.create_publisher(Path, TOPIC_ACTIVE_PATH, LATCHED)
        self.planner = self.create_client(PlanRoute, SRV_PLAN_ROUTE)
        self.create_subscription(TerrainMeta, TOPIC_TERRAIN_META, self.on_meta, LATCHED)
        for a in load_agents(agents_file):
            self.create_subscription(
                AgentState, agent_state_topic(a['id']), self.on_agent, RELIABLE)
        self.create_service(SetMissionGoal, SRV_SET_GOAL, self.on_set_goal)
        self.create_timer(1.0, self.publish_state)
        self.create_timer(0.1, self.check_stop_timeout)
        self.get_logger().warn('MOCK mission manager: goal -> route -> replan only')

    # ---- inputs -----------------------------------------------------------
    def on_agent(self, msg):
        if msg.run_id != self.run_id or msg.header.frame_id != 'map':
            return
        previous = self.agents.get(msg.agent_id)
        if previous is not None and stamp_key(msg.header) < stamp_key(previous.header):
            return
        self.agents[msg.agent_id] = msg
        if (self.stop_barrier is not None and self.goal is not None
                and msg.agent_id == self.goal.primary_agent_id
                and stopped_after(msg, self.stop_barrier)):
            self.stop_barrier = self.stop_deadline = None
            self.request_plan()

    def check_stop_timeout(self):
        if self.stop_deadline is not None and self.get_clock().now().nanoseconds >= self.stop_deadline:
            self.stop_barrier = self.stop_deadline = None
            self.pending = None
            self.set_state(S.STATE_BLOCKED, reason='STOP_ACK_TIMEOUT')

    def invalidate_planning(self):
        self.pending = self.dispatched = None
        self.stop_barrier = self.stop_deadline = None
        if self.retry_timer is not None:
            self.retry_timer.cancel()
            self.retry_timer = None

    def plan_after_stop(self):
        if self.require_stop_ack:
            now = self.get_clock().now()
            stamp = now.to_msg()
            self.stop_barrier = (stamp.sec, stamp.nanosec)
            self.stop_deadline = now.nanoseconds + int(self.stop_ack_timeout_s * 1e9)
        else:
            self.request_plan()

    def on_meta(self, meta):
        if meta.run_id != self.run_id or meta.map_version <= self.map_version:
            return
        first = self.map_version == 0
        self.map_version = meta.map_version
        if first:
            return
        self.emit(E.TYPE_MAP_UPDATED, cause=f'map-v{meta.map_version}',
                  detail=f'Map updated to version {meta.map_version}.')
        if self.goal is not None and self.state in (
                S.STATE_PLANNING, S.STATE_READY, S.STATE_REPLAN, S.STATE_BLOCKED):
            self.invalidate_planning()
            if self.route.route_id:
                self.emit(E.TYPE_ROUTE_INVALIDATED, cause=f'map-v{meta.map_version}',
                          route_id=self.route.route_id, reason='MAP_UPDATED',
                          detail='Route was computed on an older map version.')
                self.route = RouteDecision()
                self.publish_path()
            self.set_state(S.STATE_REPLAN, cause=f'map-v{meta.map_version}',
                           reason='MAP_UPDATED')
            self.attempt = 0
            self.limit_retries = 0
            self.plan_after_stop()

    def on_set_goal(self, req, res):
        if req.request_id in self.answers:
            return self.answers[req.request_id]
        res.request_id = req.request_id
        res.run_id = self.run_id
        reject = None
        if not req.request_id:
            reject = ('MISSING_REQUEST_ID', 'request_id is required.')
        elif req.run_id and req.run_id != self.run_id:
            reject = ('RUN_MISMATCH', f'Current run is {self.run_id}.')
        elif req.primary_agent_id not in self.agents:
            reject = ('UNKNOWN_AGENT', f'No state received for agent {req.primary_agent_id!r}.')
        elif self.map_version == 0:
            reject = ('NO_MAP', 'No terrain metadata received yet.')
        elif (self.require_stop_ack and self.goal is not None
              and req.primary_agent_id != self.goal.primary_agent_id
              and self.agents[self.goal.primary_agent_id].mode == AgentState.MODE_MOVING):
            reject = ('PRIMARY_SWITCH_REQUIRES_STOP', 'Stop the current primary before switching agents.')
        if reject:
            res.accepted = False
            res.reason_code, res.detail = reject
            self.emit(E.TYPE_GOAL_REJECTED, cause=req.request_id,
                      agent_id=req.primary_agent_id, reason=res.reason_code,
                      detail=res.detail)
        else:
            moving = self.agents[req.primary_agent_id].mode == AgentState.MODE_MOVING
            self.invalidate_planning()
            self.goal = req
            agent = self.agents[req.primary_agent_id]
            self.goal_resources = (agent.time_remaining_s, agent.energy_remaining_wh,
                                   agent.oxygen_remaining_l)
            if self.route.route_id:
                self.emit(E.TYPE_ROUTE_INVALIDATED, cause=req.request_id,
                          route_id=self.route.route_id, reason='NEW_GOAL',
                          detail='A new goal replaced the previous one.')
            self.route = RouteDecision()
            self.publish_path()
            res.accepted = True
            res.reason_code = 'ACCEPTED'
            res.detail = 'Goal accepted, planning.'
            self.emit(E.TYPE_GOAL_ACCEPTED, cause=req.request_id,
                      agent_id=req.primary_agent_id, reason=res.reason_code,
                      detail=res.detail)
            self.set_state(S.STATE_PLANNING, cause=req.request_id)
            self.attempt = 0
            self.limit_retries = 0
            if self.require_stop_ack and moving:
                self.plan_after_stop()
            else:
                self.request_plan()
        res.mission_state = self.state
        if req.request_id:
            self.answers[req.request_id] = res
        return res

    # ---- planning ---------------------------------------------------------
    def request_plan(self):
        if self.stop_barrier is not None:
            return
        if self.retry_timer is not None:
            self.retry_timer.cancel()
            self.retry_timer = None
        g = self.goal
        agent = self.agents[g.primary_agent_id]
        self.attempt += 1
        req = PlanRoute.Request()
        req.run_id = self.run_id
        req.request_id = f'{g.request_id}#v{self.map_version}.{self.attempt}'
        req.agent_id = agent.agent_id
        req.agent_kind = agent.agent_kind
        req.start = deepcopy(agent.pose.position)  # frozen current pose, not the original start
        req.goal = g.goal
        req.return_to = g.base
        req.require_return = True
        req.mode = g.mode or RouteDecision.MODE_FAST
        req.map_version = self.map_version
        initial = self.goal_resources
        human = agent.agent_kind == AgentState.KIND_HUMAN
        try:
            req.time_budget_s = remaining_allocation(g.time_budget_s, initial[0], agent.time_remaining_s)
            req.energy_budget_wh = remaining_allocation(g.energy_budget_wh, initial[1], agent.energy_remaining_wh)
            req.oxygen_budget_l = (remaining_allocation(g.oxygen_budget_l, initial[2], agent.oxygen_remaining_l)
                                   if human else math.nan)
        except ValueError:
            self.pending = None
            self.set_state(S.STATE_BLOCKED, cause=req.request_id, reason='INVALID_RESOURCE_STATE')
            return
        req.reserve_time_s = g.reserve_time_s
        req.reserve_wh = g.reserve_wh
        # Only a human has oxygen; the contract carries NaN for everyone else.
        req.reserve_oxygen_l = g.reserve_oxygen_l if human else math.nan
        short = [name for name, available, reserve in (
            ('TIME', req.time_budget_s, req.reserve_time_s),
            ('ENERGY', req.energy_budget_wh, req.reserve_wh),
            ('OXYGEN', req.oxygen_budget_l, req.reserve_oxygen_l))
            if (name != 'OXYGEN' or human) and available < reserve]
        if short:
            self.pending = None
            d = RouteDecision()
            d.header.frame_id = 'map'
            d.header.stamp = self.get_clock().now().to_msg()
            d.run_id, d.request_id, d.agent_id = req.run_id, req.request_id, req.agent_id
            d.mode, d.map_version_used = req.mode, req.map_version
            d.status = RouteDecision.STATUS_INSUFFICIENT_BUDGET
            d.reason_code = 'RESERVE_NOT_MET_' + '_'.join(short)
            d.detail = 'Remaining allocation is below the required reserve; no route requested.'
            for name in ('travel_time_s', 'energy_est_wh', 'oxygen_est_l', 'min_clearance_m',
                         'reserve_time_s', 'reserve_wh', 'reserve_oxygen_l'):
                setattr(d, name, math.nan)
            self.route = d
            self.emit(E.TYPE_ERROR, cause=req.request_id, agent_id=req.agent_id,
                      reason=d.reason_code, detail=d.detail)
            self.set_state(S.STATE_BLOCKED, cause=req.request_id, reason=d.status)
            return
        self.pending = req.request_id
        self.dispatched = req
        if not self.planner.service_is_ready():
            self.pending = None
            self.set_state(S.STATE_BLOCKED, cause=req.request_id,
                           reason='PLANNER_UNAVAILABLE')
            return
        self.planner.call_async(req).add_done_callback(self.on_plan_done)

    def on_plan_done(self, future):
        d = future.result().decision
        if d.request_id != self.pending:
            self.get_logger().info(f'stale plan answer {d.request_id} ignored')
            return
        self.pending = None
        behind = (d.map_version_used != self.map_version
                  or d.status == RouteDecision.STATUS_STALE_MAP
                  or d.reason_code in TRANSIENT)
        if behind and self.attempt < MAX_RETRIES:
            # The planner has not assembled the batch of this map version yet.
            self.get_logger().info(f'planner not on map v{self.map_version} yet '
                                   f'({d.status}/{d.reason_code}), retrying')
            self.retry_timer = self.create_timer(RETRY_PERIOD_S, self.request_plan)
            return
        if behind:
            # Exhausting retries never makes an obsolete result executable.
            self.set_state(S.STATE_BLOCKED, cause=d.request_id, reason='STALE_MAP')
            return
        if d.reason_code == 'SEARCH_LIMIT' and self.limit_retries < MAX_LIMIT_RETRIES:
            self.limit_retries += 1
            self.get_logger().info('planner hit its search limit, trying again')
            self.retry_timer = self.create_timer(RETRY_PERIOD_S, self.request_plan)
            return
        if d.status == RouteDecision.STATUS_FEASIBLE:
            agent = self.agents[self.goal.primary_agent_id]
            if d.run_id != self.run_id or d.agent_id != agent.agent_id:
                self.set_state(S.STATE_BLOCKED, cause=d.request_id, reason='PLAN_CONTEXT_MISMATCH')
                return
            try:
                checks = [(d.travel_time_s, self.goal.time_budget_s, self.goal_resources[0],
                           agent.time_remaining_s, self.goal.reserve_time_s),
                          (d.energy_est_wh, self.goal.energy_budget_wh, self.goal_resources[1],
                           agent.energy_remaining_wh, self.goal.reserve_wh)]
                if agent.agent_kind == AgentState.KIND_HUMAN:
                    checks.append((d.oxygen_est_l, self.goal.oxygen_budget_l, self.goal_resources[2],
                                   agent.oxygen_remaining_l, self.goal.reserve_oxygen_l))
                fits = all(math.isfinite(cost) and cost >= 0
                           and cost + reserve <= remaining_allocation(limit, initial, current) + 1e-5
                           for cost, limit, initial, current, reserve in checks)
            except ValueError:
                fits = False
            if not fits:
                self.set_state(S.STATE_BLOCKED, cause=d.request_id, reason='INSUFFICIENT_BUDGET')
                return
            expected = self.dispatched.start
            actual = agent.pose.position
            if (self.require_stop_ack and (not stopped_after(agent, (0, 0))
                    or math.dist((expected.x, expected.y, expected.z),
                                 (actual.x, actual.y, actual.z)) > 1e-6)):
                self.set_state(S.STATE_BLOCKED, cause=d.request_id, reason='POSE_CHANGED_DURING_SEARCH')
                return
            if (self.require_stop_ack and (not d.outbound_path
                    or math.dist((expected.x, expected.y, expected.z),
                                 (d.outbound_path[0].x, d.outbound_path[0].y,
                                  d.outbound_path[0].z)) > 1e-6)):
                self.set_state(S.STATE_BLOCKED, cause=d.request_id, reason='CANDIDATE_START_MISMATCH')
                return
            self.route = d
            self.publish_path()
            self.emit(E.TYPE_ROUTE_PUBLISHED, cause=d.request_id, agent_id=d.agent_id,
                      route_id=d.route_id, reason=d.reason_code, detail=d.detail)
            self.set_state(S.STATE_READY, cause=d.request_id)
        else:
            self.route = d  # keeps status and reason visible, route_id is empty
            self.emit(E.TYPE_ERROR, cause=d.request_id, agent_id=d.agent_id,
                      reason=d.reason_code, detail=d.detail)
            self.set_state(S.STATE_BLOCKED, cause=d.request_id, reason=d.status)

    # ---- outputs ----------------------------------------------------------
    def emit(self, event_type, cause='', agent_id='', route_id='', reason='', detail='',
             previous='', new=''):
        self.seq += 1
        ev = E()
        ev.header.stamp = self.get_clock().now().to_msg()
        ev.event_id = f'{self.run_id}-e{self.seq}'
        ev.seq = self.seq
        ev.run_id = self.run_id
        ev.causality_id = cause
        ev.event_type = event_type
        ev.agent_id = agent_id
        ev.map_version = self.map_version
        ev.route_id = route_id
        ev.previous_state = previous
        ev.new_state = new
        ev.reason_code = reason
        ev.detail = detail
        self.pub_event.publish(ev)

    def set_state(self, new, cause='', reason=''):
        previous, self.state, self.reason = self.state, new, reason
        self.emit(E.TYPE_MISSION_STATE_CHANGED, cause=cause, reason=reason,
                  previous=previous, new=new,
                  detail=f'Mission state {previous} -> {new}.')
        self.publish_state()

    def publish_state(self):
        msg = S()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.run_id = self.run_id
        msg.last_event_seq = self.seq
        msg.mission_state = self.state
        msg.reason_code = self.reason
        if self.goal is not None:
            msg.base = self.goal.base
            msg.primary_goal = self.goal.goal
            msg.primary_agent_id = self.goal.primary_agent_id
            msg.active_task_id = 'primary'
            msg.active_task_kind = 'primary'
        msg.map_version = self.map_version
        msg.route_id = self.route.route_id
        msg.active_route = self.route
        msg.agents = [self.agents[k] for k in sorted(self.agents)]
        self.pub_state.publish(msg)

    def publish_path(self):
        path = Path()
        path.header.stamp = self.get_clock().now().to_msg()
        path.header.frame_id = 'map'
        for p in list(self.route.outbound_path) + list(self.route.return_path):
            pose = PoseStamped()
            pose.header = path.header
            pose.pose.position = p
            pose.pose.orientation.w = 1.0
            path.poses.append(pose)
        self.pub_path.publish(path)


def main():
    rclpy.init()
    try:
        rclpy.spin(MockMission())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
