from glob import glob

from setuptools import find_packages, setup

package_name = 'mge_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
    ],
    entry_points={'console_scripts': ['mission_replan_node = mge_bringup.mission_replan:main']},
    install_requires=['setuptools'],
    zip_safe=True,
    description='Mars Gods Eye launch files and run configuration.',
    license='MIT',
)
