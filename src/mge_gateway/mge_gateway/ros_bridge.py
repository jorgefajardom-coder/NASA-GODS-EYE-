"""ROS side of the gateway: subscriptions feed the RunStore, and goal requests
are forwarded to the mission service. Runs in its own executor thread so ROS
callbacks never wait on the web server."""
import threading

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosidl_runtime_py import message_to_ordereddict

from mge_gateway.store import CONVERTERS, NonFiniteValue, RunStore, strict_json
from mge_interfaces.msg import MissionEvent, MissionState, TerrainMeta
from mge_interfaces.srv import SetMissionGoal

RELIABLE = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE)
LATCHED = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)


def msg_json(kind, msg):
    """kind: 'state' | 'event' | 'terrain_meta'. Raises NonFiniteValue."""
    return CONVERTERS[kind](message_to_ordereddict(msg))


class RosBridge(Node):

    def __init__(self):
        super().__init__('mge_gateway')
        self.host = self.declare_parameter('host', '127.0.0.1').value
        self.port = self.declare_parameter('port', 8000).value
        self.cors_origins = self.declare_parameter(
            'cors_origins', ['http://localhost:5173']).value
        self.store = RunStore(
            self.declare_parameter('run_id', 'mock-run').value,
            self.declare_parameter('source_mode', 'UNKNOWN').value)
        self.on_update = None       # set by the web app: fn(kind, payload)
        self.rejected = 0           # messages dropped for invalid numbers

        self.create_subscription(
            MissionState, '/mge/mission/state', self._on_state, LATCHED)
        self.create_subscription(
            MissionEvent, '/mge/mission/events', self._on_event, RELIABLE)
        self.create_subscription(
            TerrainMeta, '/mge/terrain/meta', self._on_meta, LATCHED)
        self.goal_client = self.create_client(SetMissionGoal, '/mge/mission/set_goal')

    def now_s(self):
        return self.get_clock().now().nanoseconds / 1e9

    def _notify(self, kind, payload):
        if self.on_update:
            self.on_update(kind, payload)

    def _convert(self, kind, msg):
        """An invalid message is dropped whole and reported, never patched."""
        try:
            return msg_json(kind, msg)
        except NonFiniteValue as e:
            self.rejected += 1
            self.get_logger().error(f'dropped {kind} message: {e}')
            return None

    def _on_state(self, msg):
        data = self._convert('state', msg)
        if data is not None and self.store.apply_state(data):
            self._notify('state', data)

    def _on_event(self, msg):
        data = self._convert('event', msg)
        if data is not None and self.store.apply_event(data):
            self._notify('event', data)

    def _on_meta(self, msg):
        data = self._convert('terrain_meta', msg)
        if data is not None:
            self.store.apply_meta(data)

    def set_goal(self, fields, timeout_s=5.0):
        """Blocking call from a web worker thread. Returns the response as a
        dict, or None if the mission service is unavailable or silent."""
        if not self.goal_client.service_is_ready():
            return None
        req = SetMissionGoal.Request()
        req.request_id = fields['request_id']
        req.run_id = self.store.run_id
        req.primary_agent_id = fields['primary_agent_id']
        for name in ('base', 'goal'):
            point = getattr(req, name)
            point.x, point.y, point.z = (float(fields[name][k]) for k in ('x', 'y', 'z'))
        req.mode = fields['mode']
        for name in ('time_budget_s', 'energy_budget_wh', 'oxygen_budget_l',
                     'reserve_time_s', 'reserve_wh', 'reserve_oxygen_l'):
            setattr(req, name, float(fields[name]))
        done = threading.Event()
        future = self.goal_client.call_async(req)
        future.add_done_callback(lambda _: done.set())
        if not done.wait(timeout_s):
            future.cancel()
            return None
        return strict_json(message_to_ordereddict(future.result()), 'set_mission_goal')


def spin_in_thread(node):
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    return thread
