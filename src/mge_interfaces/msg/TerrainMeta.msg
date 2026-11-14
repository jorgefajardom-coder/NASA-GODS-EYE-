# ICD-ROS2-V1 | Static description of the terrain grid for one run.
# Topic: /mge/terrain/meta  (DataProvider -> all, reliable + transient_local)
#
# Grid convention (applies to every raster and OccupancyGrid of the run):
#   frame "map": x east, y north, z up, metres.
#   (origin_x_m, origin_y_m) is the south-west corner of cell (row 0, col 0).
#   row grows to the north, col grows to the east, flat index = row * cols + col.
#   cell centre: x = origin_x_m + (col + 0.5) * resolution_m
#                y = origin_y_m + (row + 0.5) * resolution_m

std_msgs/Header header          # frame_id = "map", stamp = simulated time
string run_id
string dataset_id
uint32 map_version              # grows with every valid observation

float64 origin_x_m
float64 origin_y_m
float64 resolution_m
uint32 rows
uint32 cols

# Georeference of the local origin. Planetocentric latitude, east-positive
# longitude on the Mars body named in `crs`. Never Earth WGS84.
string crs
float64 origin_lat_deg
float64 origin_lon_deg
string vertical_datum           # e.g. "MOLA areoid"; heights are metres above it
float32 nodata_value            # value used in 32FC1 rasters for NoData cells

string[] sources                # one provenance entry per contributing product
string checksum_sha256          # checksum of the prior raster of this run
