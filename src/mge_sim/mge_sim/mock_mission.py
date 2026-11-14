"""MOCK mission manager.

Stand-in for the mission authority: accepts a goal, asks the planner for a
route, publishes the route in force, and replans from the agent's current
pose when the map version changes. It covers IDLE / PLANNING / READY / REPLAN
/ BLOCKED only. It has no tasks, precedences or execution; those belong to
the real mge_mission package.
"""
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

S = MissionState
E = MissionEvent


class MockMission(Node):

    def __init__(self):
        super().__init__('mock_mission')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        agents_file = self.declare_parameter('agents_file', '').value

        self.state = S.STATE_IDLE
        self.reason = ''
        self.seq = 0
        self.map_version = 0
        self.agents = {}
        self.goal = None            # SetMissionGoal.Request in force
        self.pending = None         # request_id of the plan we are waiting for
        self.route = RouteDecision()
        self.answers = {}           # request_id -> SetMissionGoal.Response

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
        self.get_logger().warn('MOCK mission manager: goal -> route -> replan only')

    # ---- inputs -----------------------------------------------------------
    def on_agent(self, msg):
        if msg.run_id == self.run_id:
            self.agents[msg.agent_id] = msg

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
            if self.route.route_id:
                self.emit(E.TYPE_ROUTE_INVALIDATED, cause=f'map-v{meta.map_version}',
                          route_id=self.route.route_id, reason='MAP_UPDATED',
                          detail='Route was computed on an older map version.')
                self.route = RouteDecision()
                self.publish_path()
            self.set_state(S.STATE_REPLAN, cause=f'map-v{meta.map_version}',
                           reason='MAP_UPDATED')
            self.request_plan()

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
        if reject:
            res.accepted = False
            res.reason_code, res.detail = reject
            self.emit(E.TYPE_GOAL_REJECTED, cause=req.request_id,
                      agent_id=req.primary_agent_id, reason=res.reason_code,
                      detail=res.detail)
        else:
            self.goal = req
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
            self.request_plan()
        res.mission_state = self.state
        if req.request_id:
            self.answers[req.request_id] = res
        return res

    # ---- planning ---------------------------------------------------------
    def request_plan(self):
        g = self.goal
        agent = self.agents[g.primary_agent_id]
        req = PlanRoute.Request()
        req.run_id = self.run_id
        req.request_id = f'{g.request_id}#v{self.map_version}'
        req.agent_id = agent.agent_id
        req.agent_kind = agent.agent_kind
        req.start = agent.pose.position      # current pose, not the original start
        req.goal = g.goal
        req.return_to = g.base
        req.require_return = True
        req.mode = g.mode or RouteDecision.MODE_FAST
        req.map_version = self.map_version
        req.time_budget_s = g.time_budget_s
        req.energy_budget_wh = g.energy_budget_wh
        req.oxygen_budget_l = g.oxygen_budget_l
        req.reserve_time_s = g.reserve_time_s
        req.reserve_wh = g.reserve_wh
        req.reserve_oxygen_l = g.reserve_oxygen_l
        self.pending = req.request_id
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
        if d.map_version_used != self.map_version or d.status == RouteDecision.STATUS_STALE_MAP:
            self.get_logger().info('plan answer for an older map, replanning')
            self.request_plan()
            return
        if d.status == RouteDecision.STATUS_FEASIBLE:
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
