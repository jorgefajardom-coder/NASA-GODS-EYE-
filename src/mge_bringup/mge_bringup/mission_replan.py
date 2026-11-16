"""Compose the existing authority with an advisory planner-owned policy; no second manager."""
def main(args=None):
    from mge_mission.node import main as mission_main
    from mge_planning.mission_replan import ScientificReplanBridge
    mission_main(args, replan_factory=ScientificReplanBridge)
