"""Give every integration module its own ROS domain.

Each module launches a complete graph. Run in one domain, a module could start
while DDS still listed the previous module's nodes: services that no longer
answer, publishers of another run. On loaded CI runners that overlap made
planner and mission requests time out. docs/LAUNCH_PROFILES.md already asks
for a dedicated ROS_DOMAIN_ID per run; this applies it to the tests.

Launched processes inherit the variable and rclpy.init() reads it. Modules
that set their own domain explicitly keep it.
"""
import itertools
import os

import pytest

# 60.. stays clear of the dev container's default (42), of explicit test
# domains (173) and within the range DDS maps to fixed ports on Linux.
_DOMAINS = itertools.count(60)


@pytest.fixture(scope='module', autouse=True)
def isolated_ros_domain():
    previous = os.environ.get('ROS_DOMAIN_ID')
    os.environ['ROS_DOMAIN_ID'] = str(next(_DOMAINS))
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('ROS_DOMAIN_ID', None)
        else:
            os.environ['ROS_DOMAIN_ID'] = previous


@pytest.fixture(scope='session')
def planner_ready():
    """Wait until /mge/planner/plan_route has a server in the module's domain.

    The gateway answers before slow nodes finish starting; a goal sent first
    finds no planner and the mission blocks on PLANNER_UNAVAILABLE.
    """
    def wait(timeout_s=60.0):
        import rclpy
        from rclpy.context import Context
        from mge_interfaces.srv import PlanRoute

        context = Context()
        rclpy.init(context=context)
        node = rclpy.create_node('planner_readiness_probe', context=context)
        try:
            client = node.create_client(PlanRoute, '/mge/planner/plan_route')
            if not client.wait_for_service(timeout_sec=timeout_s):
                raise AssertionError('no PlanRoute server came up')
        finally:
            node.destroy_node()
            context.shutdown()
    return wait
