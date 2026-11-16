"""Experimental physics rover adapter with measured stop and watchdog feedback.

Gazebo drives the rover; MissionState and its matching Path are the authority.
The adapter preserves odometry acquisition stamps and all six velocity axes.
Resource accounting remains explicitly illustrative MOCK accounting.
Height diagnostics retained from PR49 never project or recalibrate AgentState:
only the world's declared Z offset transforms physics coordinates to map.
"""
import json
import math
import threading
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node

from mge_interfaces.msg import AgentState, MissionState
from nav_msgs.msg import Path
from mge_sim.common import LATCHED, RELIABLE, TOPIC_ACTIVE_PATH, TOPIC_MISSION_STATE, agent_state_topic
from mge_sim.gz_control import RoverControl, odometry_sample
# Preserve PR49's diagnostic API; these helpers never alter acquired telemetry.
from mge_sim.gz_control import MAX_DATUM_OFFSET_M, datum_offset, map_height
from mge_sim.mock_agents import load_agents


class GzRoverDriver(Node):

    def __init__(self):
        super().__init__('gz_rover_driver')
        if not self.get_parameter('use_sim_time').value:
            raise ValueError('Gazebo requires use_sim_time=true and an external /clock bridge')
        self.run_id = self.declare_parameter('run_id', 'mock-run').value
        self.agent_id = self.declare_parameter('agent_id', 'rover_1').value
        world_json = self.declare_parameter('world_json', '').value
        agents_file = self.declare_parameter('agents_file', '').value
        speed = float(self.declare_parameter('speed_m_s', 0.65).value)
        odom_timeout = float(self.declare_parameter('odom_timeout_s', 0.5).value)
        stop_window = float(self.declare_parameter('stop_window_s', 0.3).value)
        with open(world_json, encoding='utf-8') as f:
            world = json.load(f)
        self.z_ref = float(world['z_ref_m'])
        if (not math.isfinite(self.z_ref)
                or not world['agents'].get(self.agent_id, {}).get('physical')):
            raise ValueError('world_json must declare this physical agent and a finite Z offset')
        spec = next(a for a in load_agents(agents_file) if a['id'] == self.agent_id)
        self.kind = spec['kind']
        if self.kind != 'ROVER':
            raise ValueError('gz_rover_driver only supports a ROVER')
        self.control = RoverControl(self.run_id, self.agent_id, float(spec['time_budget_s']),
                                    float(spec['energy_budget_wh']), speed, odom_timeout, stop_window)
        self.mission, self.path = None, []
        self.lock = threading.Lock()
        self.last_reason = ''
        from gz.msgs10.odometry_pb2 import Odometry
        from gz.msgs10.twist_pb2 import Twist
        from gz.transport13 import Node as GzNode
        self.Twist = Twist
        self.gz = GzNode()
        self.cmd = self.gz.advertise(f'/model/{self.agent_id}/cmd_vel', Twist)
        if not self.gz.subscribe(Odometry, f'/model/{self.agent_id}/odometry_gt', self.on_odom):
            raise RuntimeError('Gazebo odometry subscription failed')
        self.pub = self.create_publisher(AgentState, agent_state_topic(self.agent_id), RELIABLE)
        self.create_subscription(MissionState, TOPIC_MISSION_STATE, self.on_mission, LATCHED)
        self.create_subscription(Path, TOPIC_ACTIVE_PATH, self.on_path, LATCHED)
        # ROS simulation timers pause with /clock. The stop watchdog must keep running.
        self.watchdog_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.05, self.tick, clock=self.watchdog_clock)
        self.get_logger().warn(f'Gazebo-driven {self.agent_id}: physics pose, MOCK resource accounting')

    def on_odom(self, msg):
        try:
            sample = odometry_sample(msg, self.z_ref, time.monotonic())
        except (AttributeError, TypeError, ValueError, OverflowError):
            with self.lock:
                self.control.fault = 'INVALID_ODOMETRY'
            self.drive(0.0, 0.0)
            return
        with self.lock:
            self.control.receive(sample)

    def on_mission(self, msg):
        if msg.run_id == self.run_id:
            self.mission = msg

    def on_path(self, msg):
        self.path = ([(p.pose.position.x, p.pose.position.y, p.pose.position.z) for p in msg.poses]
                     if msg.header.frame_id == 'map' else [])

    def drive(self, v, w):
        msg = self.Twist()
        msg.linear.x, msg.angular.z = float(v), float(w)
        self.cmd.publish(msg)

    def tick(self):
        with self.lock:
            command, sample = self.control.step(self.mission, self.path,
                                                self.get_clock().now().nanoseconds,
                                                time.monotonic())
            self.drive(*command)
            if self.control.reason and self.control.reason != self.last_reason:
                self.get_logger().warn(self.control.reason)
                self.last_reason = self.control.reason
            if sample is not None:
                self.publish(sample)

    def publish(self, sample):
        msg = AgentState()
        msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(sample.stamp_ns, 10**9)
        msg.header.frame_id = 'map'
        msg.run_id, msg.agent_id, msg.agent_kind = self.run_id, self.agent_id, self.kind
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = sample.position
        (msg.pose.orientation.x, msg.pose.orientation.y,
         msg.pose.orientation.z, msg.pose.orientation.w) = sample.orientation
        msg.velocity.linear.x, msg.velocity.linear.y, msg.velocity.linear.z = sample.linear
        msg.velocity.angular.x, msg.velocity.angular.y, msg.velocity.angular.z = sample.angular
        msg.mode = self.control.mode
        msg.time_remaining_s, msg.energy_remaining_wh = self.control.time_s, self.control.energy_wh
        msg.oxygen_remaining_l, msg.confidence = math.nan, 1.0
        self.pub.publish(msg)

    def stop(self):
        """Send a brake even when ROS simulation time is paused or shutting down."""
        self.drive(0.0, 0.0)

    def destroy_node(self):
        self.stop()
        return super().destroy_node()


def main():
    rclpy.init()
    node = None
    try:
        node = GzRoverDriver()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
