# Arrays have the same length; cell_indices are row-major in TerrainMeta.
# A receiver must reject duplicate IDs, stale runs, invalid indices and NaN values.
string SOURCE_SIMULATED=SIMULATED
std_msgs/Header header
string schema_version
string observation_id
string run_id
string agent_id
uint64 prior_map_version
uint32[] cell_indices
float32[] elevation_m
int8[] obstacle_state
float32[] sigma_m
string source_kind
