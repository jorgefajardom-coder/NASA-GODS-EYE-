"""QoS profiles and topic names shared by the nodes (see docs/ICD.md)."""
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

RELIABLE = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE)
LATCHED = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
)

TOPIC_TERRAIN_META = '/mge/terrain/meta'
TOPIC_OBSERVATIONS = '/mge/observations'
TOPIC_MISSION_EVENTS = '/mge/mission/events'
TOPIC_MISSION_STATE = '/mge/mission/state'
TOPIC_ACTIVE_PATH = '/mge/planner/active_path'
SRV_PLAN_ROUTE = '/mge/planner/plan_route'
SRV_SET_GOAL = '/mge/mission/set_goal'


def agent_state_topic(agent_id):
    return f'/mge/agents/{agent_id}/state'
