"""MOCK route planner.

Answers PlanRoute with a straight line start -> goal -> return point. It does
not read terrain, slopes or obstacles, so a FEASIBLE answer from this node is
not a verified route. Speeds and consumption rates are placeholders. It exists
so the mission and gateway can be integrated before the real planner.
"""
import math

from geometry_msgs.msg import Point
import rclpy
from rclpy.node import Node

from mge_interfaces.msg import AgentState, RouteDecision, TerrainMeta
from mge_interfaces.srv import PlanRoute
from mge_sim.common import LATCHED, SRV_PLAN_ROUTE, TOPIC_TERRAIN_META

# PLACEHOLDER figures, not mission assumptions: (speed m/s, energy Wh/m).
RATES = {
    AgentState.KIND_HUMAN: (1.0, 0.05),
    AgentState.KIND_ROVER: (0.5, 0.20),
    AgentState.KIND_DRONE: (5.0, 0.10),
}
OXYGEN_L_PER_S = 0.01  # PLACEHOLDER
STEP_M = 5.0


def straight_line(a, b):
    dist = math.hypot(b.x - a.x, b.y - a.y)
    n = max(1, math.ceil(dist / STEP_M))
    return [
        Point(x=a.x + (b.x - a.x) * i / n, y=a.y + (b.y - a.y) * i / n, z=0.0)
        for i in range(n + 1)
    ], dist


class MockPlanner(Node):

    def __init__(self):
        super().__init__('mock_planner')
        self.map_version = 0
        self.counter = 0
        self.create_subscription(TerrainMeta, TOPIC_TERRAIN_META, self.on_meta, LATCHED)
        self.create_service(PlanRoute, SRV_PLAN_ROUTE, self.on_plan)
        self.get_logger().warn('MOCK planner: straight lines, terrain is not evaluated')

    def on_meta(self, meta):
        self.map_version = meta.map_version

    def on_plan(self, req, res):
        d = res.decision
        d.header.stamp = self.get_clock().now().to_msg()
        d.header.frame_id = 'map'
        d.run_id = req.run_id
        d.request_id = req.request_id
        d.agent_id = req.agent_id
        d.mode = req.mode
        d.map_version_used = self.map_version
        human = req.agent_kind == AgentState.KIND_HUMAN
        d.oxygen_est_l = d.reserve_oxygen_l = math.nan

        def fail(status, reason, detail):
            d.status, d.reason_code, d.detail = status, reason, detail
            return res

        if req.map_version != self.map_version:
            return fail(
                RouteDecision.STATUS_STALE_MAP, 'MAP_VERSION_MISMATCH',
                f'Request used map version {req.map_version}, current is {self.map_version}.')
        if req.agent_kind not in RATES:
            return fail(
                RouteDecision.STATUS_ERROR, 'UNKNOWN_AGENT_KIND',
                f'Unknown agent kind {req.agent_kind!r}.')

        speed, wh_per_m = RATES[req.agent_kind]
        outbound, dist = straight_line(req.start, req.goal)
        back = []
        if req.require_return:
            back, dist_back = straight_line(req.goal, req.return_to)
            dist += dist_back
        time_s = dist / speed + req.service_time_s
        energy_wh = dist * wh_per_m
        d.travel_time_s = time_s
        d.energy_est_wh = energy_wh
        d.reserve_time_s = req.time_budget_s - time_s
        d.reserve_wh = req.energy_budget_wh - energy_wh
        d.min_clearance_m = math.nan  # not evaluated by the mock
        if human:
            d.oxygen_est_l = time_s * OXYGEN_L_PER_S
            d.reserve_oxygen_l = req.oxygen_budget_l - d.oxygen_est_l

        short = []
        if d.reserve_time_s < req.reserve_time_s:
            short.append('TIME')
        if d.reserve_wh < req.reserve_wh:
            short.append('ENERGY')
        if human and d.reserve_oxygen_l < req.reserve_oxygen_l:
            short.append('OXYGEN')
        if short:
            return fail(
                RouteDecision.STATUS_INSUFFICIENT_BUDGET,
                'RESERVE_NOT_MET_' + '_'.join(short),
                'Outbound, service and return would leave less than the required '
                f'reserve of: {", ".join(s.lower() for s in short)}.')

        self.counter += 1
        d.route_id = f'{req.run_id}-r{self.counter}'
        d.outbound_path = outbound
        d.return_path = back
        d.status = RouteDecision.STATUS_FEASIBLE
        d.reason_code = 'MOCK_STRAIGHT_LINE'
        d.detail = 'MOCK planner: straight line, terrain not evaluated.'
        return res


def main():
    rclpy.init()
    try:
        rclpy.spin(MockPlanner())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
