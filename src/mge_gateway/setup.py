from setuptools import find_packages, setup

package_name = 'mge_gateway'

setup(
    name=package_name,
    version='0.2.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    # Runtime dependencies are declared in package.xml (rosdep) and in
    # requirements.txt (pip); pinning them here would reject the apt versions.
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='MARS GODS EYE team',
    maintainer_email='team@example.invalid',
    description='Mars Gods Eye ROS to web gateway (REST and WebSocket) and replay recorder.',
    license='LicenseRef-UNSPECIFIED',
    entry_points={
        'console_scripts': [
            'gateway = mge_gateway.main:main',
            'replay_recorder = mge_gateway.recorder:main',
            'check_replay = mge_gateway.replay_check:main',
        ],
    },
)
