# ICD-ROS2-V1 | State of one agent.
# Topic: /mge/agents/{agent_id}/state  (SimulationAdapter -> Mission, reliable)
# Resource values are assumptions of a simulated mission, never certified limits.

string KIND_HUMAN=HUMAN
string KIND_DRONE=DRONE
string KIND_ROVER=ROVER

string MODE_IDLE=IDLE
string MODE_MOVING=MOVING
string MODE_OBSERVING=OBSERVING
string MODE_WORKING=WORKING
string MODE_RETURNING=RETURNING
string MODE_HALTED=HALTED

std_msgs/Header header          # frame_id = "map", stamp = simulated time
string run_id
string agent_id                 # unique within the run
string agent_kind               # KIND_*
geometry_msgs/Pose pose
geometry_msgs/Twist velocity
string mode                     # MODE_*

float32 time_remaining_s        # estimated
float32 energy_remaining_wh     # estimated
float32 oxygen_remaining_l      # estimated; NaN for agents that are not HUMAN
float32 confidence              # 0..1, confidence in the pose estimate
