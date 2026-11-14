from setuptools import find_packages, setup

package_name = 'mge_gateway'

setup(
    name=package_name,
    version='0.2.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    description='Mars Gods Eye ROS to web gateway (REST and WebSocket).',
    license='MIT',
    entry_points={
        'console_scripts': [
            'gateway = mge_gateway.main:main',
            'replay_recorder = mge_gateway.recorder:main',
            'check_replay = mge_gateway.replay_check:main',
        ],
    },
)
