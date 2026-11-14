# ICD-ROS2-V1 | One local observation of the terrain made by an agent.
# Topic: /mge/observations  (SimulationAdapter -> Mapping, reliable)
# Only the cells listed here may change in the belief map. Re-sending the
# same observation_id must not be applied twice.

string SOURCE_SIMULATED=SIMULATED

int8 OBSTACLE_UNKNOWN=-1
int8 OBSTACLE_FREE=0
int8 OBSTACLE_BLOCKED=100

std_msgs/Header header          # frame_id = "map", stamp = simulated time
string observation_id           # unique, idempotency key
string run_id
string agent_id
uint32 base_map_version         # map version the observation was taken against
string source_kind              # SOURCE_* ; P0 is always SIMULATED

# Parallel arrays, one entry per observed cell (flat index, see TerrainMeta).
uint32[] cell_indices
float32[] elevation_m
float32[] sigma_m               # 1-sigma of the simulated sensor model
int8[] obstacle                 # OBSTACLE_*
