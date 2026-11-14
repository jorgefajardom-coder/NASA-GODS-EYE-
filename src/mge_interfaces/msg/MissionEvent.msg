# event_id is unique and idempotent within run_id; sequence increases per run.
std_msgs/Header header
string schema_version
string event_id
string run_id
uint64 sequence
string causality_id
string event_type
string task_id
string agent_id
uint64 map_version
string route_id
string previous_state
string new_state
string reason_code
