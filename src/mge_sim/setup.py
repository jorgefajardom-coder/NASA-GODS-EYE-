from setuptools import find_packages, setup

package_name = 'mge_sim'
setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='MARS GODS EYE team',
    maintainer_email='team@example.invalid',
    description='Simulation adapter scaffold',
    license='LicenseRef-UNSPECIFIED',
    entry_points={'console_scripts': ['sim_node = mge_sim.node:main']},
)
