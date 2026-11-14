from setuptools import find_packages, setup

package_name = "mge_planning"
setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools", "numpy>=1.26,<3", "scipy>=1.11,<2"],
    zip_safe=True,
    maintainer="MARS GODS EYE team",
    maintainer_email="team@example.invalid",
    description="Bounded resource-constrained planner and ROS service adapter",
    license="LicenseRef-UNSPECIFIED",
    entry_points={"console_scripts": ["planning_node = mge_planning.node:main"]},
)
