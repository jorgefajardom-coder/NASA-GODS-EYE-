from setuptools import find_packages, setup

package_name = "mge_mapping"
setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="MARS GODS EYE team",
    maintainer_email="team@example.invalid",
    description="P0 scaffold for mge_mapping; implementation pending",
    license="MIT",
    entry_points={"console_scripts": ["mapping_node = mge_mapping.node:main"]},
)
