# ICD-ROS2-V1 | Authoritative mission state. Only MissionManager publishes it.
# Topic: /mge/mission/state  (Mission -> Gateway, reliable + transient_local)

string STATE_IDLE=IDLE
string STATE_PLANNING=PLANNING
string STATE_READY=READY
string STATE_ACTIVE=ACTIVE
string STATE_REPLAN=REPLAN
string STATE_RETURNING=RETURNING
string STATE_COMPLETE=COMPLETE
string STATE_BLOCKED=BLOCKED
string STATE_ABORTED=ABORTED

string TASK_DISCOVERED=DISCOVERED
string TASK_ELIGIBLE=ELIGIBLE
string TASK_ASSIGNED=ASSIGNED
string TASK_EXECUTING=EXECUTING
string TASK_DONE=DONE
string TASK_REJECTED=REJECTED
string TASK_BLOCKED=BLOCKED

std_msgs/Header header          # frame_id = "map", stamp = simulated time
string run_id
uint64 last_event_seq           # seq of the last MissionEvent reflected here
string mission_state            # STATE_*
string reason_code              # why BLOCKED / ABORTED, empty otherwise

geometry_msgs/Point base
geometry_msgs/Point primary_goal
string primary_agent_id

string active_task_id
string active_task_kind         # e.g. primary, inspect, sample, return
string active_task_state        # TASK_*

uint32 map_version
string route_id                 # route in force, empty if none
RouteDecision active_route      # full decision of the route in force
AgentState[] agents
