"""ROS startup placeholder. It intentionally publishes no state or decisions."""


def main(args=None):
    import rclpy
    from rclpy.node import Node

    rclpy.init(args=args)
    node = Node("planning_node")
    node.get_logger().warning(
        "mge_planning is a scaffold: no algorithms, services or publications are implemented"
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
