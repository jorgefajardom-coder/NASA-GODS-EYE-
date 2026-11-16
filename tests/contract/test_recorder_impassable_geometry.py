"""Recorder consumes stamped public masks without moving or rewriting their cells."""
from types import MethodType, SimpleNamespace as NS
from unittest.mock import Mock

import pytest

pytest.importorskip('rclpy', reason='Requires ROS 2 Jazzy messages')
from nav_msgs.msg import OccupancyGrid  # noqa: E402
from mge_gateway.public_rasters import PublicRasterAssembler  # noqa: E402
from mge_gateway.recorder import ReplayRecorder  # noqa: E402


def consumer():
    raster = PublicRasterAssembler('geometry-test')
    header = {'frame_id': 'map', 'stamp': {'sec': 5, 'nanosec': 0}}
    raster.on_prior(1, 2, [0., 0.])
    raster.on_meta({'header': header, 'run_id': 'geometry-test', 'map_version': 1,
                    'dataset_id': 'synthetic', 'rows': 1, 'cols': 2,
                    'origin_x_m': -2., 'origin_y_m': -1., 'resolution_m': 2.,
                    'crs': 'local', 'origin_lat_deg': 0., 'origin_lon_deg': 0.,
                    'vertical_datum': 'test', 'nodata_value': None})
    for layer, values in [('belief', [0., 0.]), ('sigma', [.25, .25]), ('observed', [1, 1])]:
        raster.on_layer(layer, header, 1, 2, values)
    recorder = NS(rasters=raster, writer=Mock(), get_logger=lambda: NS(error=Mock()))
    recorder.update_rasters = MethodType(ReplayRecorder.update_rasters, recorder)
    return recorder


def mask():
    msg = OccupancyGrid()
    msg.header.frame_id, msg.header.stamp.sec = 'map', 5
    msg.info.width, msg.info.height, msg.info.resolution = 2, 1, 2.
    msg.info.origin.position.x, msg.info.origin.position.y = -2., -1.
    msg.info.origin.orientation.w = 1.
    msg.data = [100, 0]
    return msg


def test_recorder_attaches_valid_mask_then_refuses_same_version_mutation():
    recorder, msg = consumer(), mask()
    ReplayRecorder.on_traversability(recorder, msg)
    assert recorder.rasters.attachment()['versions']['1']['impassable'] == [0]
    msg.data = [0, 100]
    ReplayRecorder.on_traversability(recorder, msg)
    assert recorder.rasters.attachment()['versions']['1']['impassable'] == [0]
    assert recorder.writer.write_public_rasters.call_count == 1


@pytest.mark.parametrize('change', ['origin', 'resolution', 'rotation', 'height'])
def test_recorder_drops_a_mask_from_another_grid(change):
    recorder, msg = consumer(), mask()
    if change == 'origin':
        msg.info.origin.position.x += 1.
    elif change == 'resolution':
        msg.info.resolution = 1.
    elif change == 'rotation':
        msg.info.origin.orientation.z = .5
    else:
        msg.info.origin.position.z = 2.
    ReplayRecorder.on_traversability(recorder, msg)
    assert 'impassable' not in recorder.rasters.attachment()['versions']['1']
    recorder.writer.write_public_rasters.assert_not_called()
