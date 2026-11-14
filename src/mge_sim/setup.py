from setuptools import find_packages, setup

package_name = 'mge_sim'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    description='Mars Gods Eye simulation adapter and minimal P0 emulator.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'mock_agents = mge_sim.mock_agents:main',
            'sim_node = mge_sim.node:main',
        ],
    },
)
