cmake_minimum_required(VERSION 3.8)
project(mge_interfaces)
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/TerrainMeta.msg"
  "msg/TerrainObservation.msg"
  "msg/AgentState.msg"
  "msg/MissionEvent.msg"
  "msg/MissionState.msg"
  "msg/RouteDecision.msg"
  "srv/PlanRoute.srv"
  "srv/SetMissionGoal.srv"
  DEPENDENCIES std_msgs geometry_msgs nav_msgs
)
ament_export_dependencies(rosidl_default_runtime)
ament_package()
