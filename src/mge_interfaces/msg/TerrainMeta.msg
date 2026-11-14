# ICD-V1 draft: ENU map frame, metres, no terrestrial WGS84 assumption.
std_msgs/Header header
string schema_version
string run_id
string dataset_id
string frame_id
geometry_msgs/Point origin_enu_m
float64 resolution_m
uint32 rows
uint32 cols
string horizontal_crs
string vertical_datum
float64 nodata_value
string nodata_mask_uri
string[] sources
string checksum_sha256
uint64 map_version
