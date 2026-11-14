"""Start the simulation adapter scaffold without publishing fictitious sensors."""


def main(args=None) -> None:
    import rclpy
    from rclpy.node import Node

    rclpy.init(args=args)
    node = Node("simulation_adapter")
    node.get_logger().warning(
        "Scaffold only: Gazebo/lite simulation, /clock and observations are not implemented"
    )
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
