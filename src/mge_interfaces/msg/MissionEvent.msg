# ICD-ROS2-V1 | One ordered, idempotent mission event.
# Topic: /mge/mission/events  (Mission -> Gateway/logs, reliable)
# Consumers order by `seq` and ignore an event_id they have already applied.
# Events of another run_id must be dropped.

string TYPE_MISSION_STATE_CHANGED=MISSION_STATE_CHANGED
string TYPE_GOAL_ACCEPTED=GOAL_ACCEPTED
string TYPE_GOAL_REJECTED=GOAL_REJECTED
string TYPE_MAP_UPDATED=MAP_UPDATED
string TYPE_ROUTE_PUBLISHED=ROUTE_PUBLISHED
string TYPE_ROUTE_INVALIDATED=ROUTE_INVALIDATED
string TYPE_TASK_DISCOVERED=TASK_DISCOVERED
string TYPE_TASK_STATE_CHANGED=TASK_STATE_CHANGED
string TYPE_ERROR=ERROR

std_msgs/Header header          # stamp = simulated time
string event_id                 # unique, idempotency key
uint64 seq                      # strictly increasing within a run
string run_id
string causality_id             # event_id / request_id / observation_id that caused it
string event_type               # TYPE_*
string task_id
string agent_id
uint32 map_version
string route_id
string previous_state
string new_state
string reason_code              # machine-readable, UPPER_SNAKE_CASE
string detail                   # short English sentence for the UI
