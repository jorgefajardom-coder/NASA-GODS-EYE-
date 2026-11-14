import rclpy
import uvicorn

from mge_gateway.app import create_app
from mge_gateway.ros_bridge import RosBridge, spin_in_thread


def main():
    rclpy.init()
    bridge = RosBridge()
    spin_in_thread(bridge)
    bridge.get_logger().info(
        f'gateway on http://{bridge.host}:{bridge.port} (run_id={bridge.store.run_id})')
    try:
        uvicorn.run(create_app(bridge), host=bridge.host, port=bridge.port, log_level='warning')
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
