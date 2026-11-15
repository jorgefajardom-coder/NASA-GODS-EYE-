"""Batch boundaries and profile opt-in without depending on ROS installation."""

import json
from types import SimpleNamespace as NS

import numpy as np
import pytest

from mge_planning.adapter import SnapshotStore, load_profiles, load_unverified_prior, request_from_ros


def header(stamp=1, frame="map"):
    return NS(frame_id=frame, stamp=NS(sec=stamp, nanosec=0))


def metadata(run="r", version=1, stamp=1):
    return NS(header=header(stamp), run_id=run, dataset_id="illustrative",
              rows=3, cols=3, resolution_m=1.0, origin_x_m=0.0,
              origin_y_m=0.0, map_version=version, nodata_value=-9999.0,
              crs="LOCAL_ENU_SYNTHETIC", vertical_datum="illustrative",
              origin_lat_deg=18.45, origin_lon_deg=77.45, checksum_sha256="0" * 64,
              sources=["MOCK synthetic terrain", "illustrative source registry"])


def image(stamp=1, big=False, padded=False):
    columns = 4 if padded else 3
    values = np.arange(3 * columns, dtype=float).reshape(3, columns)
    data = values.astype(">f4" if big else "<f4").tobytes()
    return NS(header=header(stamp), height=3, width=3, encoding="32FC1",
              step=columns * 4, is_bigendian=int(big), data=data)


def mask(stamp=1):
    return NS(header=header(stamp), data=[0] * 9,
              info=NS(height=3, width=3, resolution=1.0,
                      origin=NS(position=NS(x=0.0, y=0.0, z=0.0),
                                orientation=NS(x=0.0, y=0.0, z=0.0, w=1.0))))


def complete():
    store = SnapshotStore()
    store.ingest_meta(metadata())
    store.ingest_image("belief", image())
    store.ingest_image("sigma", image())
    store.ingest_mask("rover", mask())
    return store


def test_layers_without_matching_metadata_are_never_adopted():
    store = SnapshotStore()
    assert not store.ingest_image("belief", image())
    assert store.snapshot("rover")[1] == "MAP_NOT_READY"
    store.ingest_meta(metadata(stamp=2))
    assert not store.ingest_image("belief", image(stamp=1))
    assert store.snapshot("rover")[1] == "SNAPSHOT_INCOMPLETE"


def test_new_version_or_run_invalidates_all_native_layers():
    store = complete()
    assert store.snapshot("rover")[0].map_version == 1
    store.ingest_meta(metadata(version=2, stamp=2))
    assert store.snapshot("rover")[1] == "SNAPSHOT_INCOMPLETE"
    assert not store.ingest_meta(metadata(version=1, stamp=1))
    assert store.key[:2] == ("r", 2)
    store.ingest_meta(metadata(run="another", version=0, stamp=3))
    assert store.snapshot("rover")[1] == "SNAPSHOT_INCOMPLETE"


@pytest.mark.parametrize("run,version", [("another", 1), ("r", 2)])
def test_stamp_cannot_identify_two_runs_or_versions(run, version):
    store = complete()
    with pytest.raises(ValueError, match="timestamp reused"):
        store.ingest_meta(metadata(run=run, version=version))


@pytest.mark.parametrize("big,padded", [(False, True), (True, False), (True, True)])
def test_image_decoder_handles_endianness_and_padding_without_transposing(big, padded):
    store = SnapshotStore()
    store.ingest_meta(metadata())
    msg = image(big=big, padded=padded)
    store.ingest_image("belief", msg)
    columns = 4 if padded else 3
    np.testing.assert_array_equal(store.layers["belief"], np.arange(3 * columns).reshape(3, columns)[:, :3])


def test_geometry_mismatch_rejected_instead_of_silently_reprojected():
    store = complete()
    msg = mask()
    msg.info.origin.position.x = 1.0
    with pytest.raises(ValueError, match="origin mismatch"):
        store.ingest_mask("rover", msg)
    msg = mask()
    msg.info.origin.orientation.z = 0.5
    with pytest.raises(ValueError, match="rotated"):
        store.ingest_mask("rover", msg)


def test_profile_mask_is_not_reused_for_another_agent_kind():
    store = complete()
    assert store.snapshot("human")[1] == "SNAPSHOT_INCOMPLETE"


def test_same_stamp_changed_layer_invalidates_inflight_snapshot_token():
    store = complete()
    token = store.key
    changed = mask()
    changed.data[4] = 100
    with pytest.raises(ValueError, match="changed without"):
        store.ingest_mask("rover", changed)
    assert store.key != token
    assert store.snapshot("rover")[1] == "IMMUTABLE_BATCH_CHANGED"


def test_exact_duplicate_packets_do_not_invalidate_a_batch():
    store = complete()
    token = store.key
    assert store.ingest_meta(metadata())
    store.ingest_image("belief", image())
    store.ingest_mask("rover", mask())
    assert store.key == token


def test_late_metadata_cannot_reactivate_a_retired_run():
    store = complete()
    store.ingest_meta(metadata(run="new", version=0, stamp=2))
    assert not store.ingest_meta(metadata())
    assert store.key[:2] == ("new", 0)


@pytest.mark.parametrize("field,value", [("nodata_value", -123.0), ("crs", "OTHER_CRS"), ("vertical_datum", "OTHER_DATUM")])
def test_same_version_cannot_change_coordinate_or_nodata_semantics(field, value):
    store = complete()
    changed = metadata()
    setattr(changed, field, value)
    with pytest.raises(ValueError, match="changed without"):
        store.ingest_meta(changed)


def test_nonhuman_ros_nan_oxygen_is_converted_to_not_applicable():
    request = NS(agent_kind="ROVER", time_budget_s=100.0, energy_budget_wh=100.0,
                 reserve_wh=1.0, oxygen_budget_l=float("nan"), reserve_oxygen_l=float("nan"),
                 run_id="r", request_id="q", agent_id="rover_1", map_version=1,
                 start=NS(x=0.5, y=0.5, z=0.0), goal=NS(x=1.5, y=1.5, z=0.0),
                 return_to=NS(x=0.5, y=0.5, z=0.0), require_return=True,
                 mode="FAST", service_time_s=0.0, reserve_time_s=0.0)
    converted = request_from_ros(request)
    assert converted.budget.oxygen_l is None
    request.oxygen_budget_l = 0.0
    with pytest.raises(ValueError, match="must be NaN"):
        request_from_ros(request)


def test_illustrative_profiles_require_explicit_opt_in(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps({"status": "illustrative", "profiles": {}}))
    with pytest.raises(ValueError, match="approval"):
        load_profiles(path)
    assert load_profiles(path, allow_illustrative=True) == {}


def test_finite_ctx_prior_is_still_unknown_to_the_planner():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    grid = load_unverified_prior(root / "data/planner_provisional/manifest.json", "new-run")
    assert np.isfinite(grid.elevation_m).all()
    assert (grid.traversability == -1).all()
    assert np.isnan(grid.sigma_m).all()


def test_batch_key_ignores_other_kinds_completing_the_same_batch():
    # A rover search must survive the human and drone masks of its own batch arriving.
    store = complete()
    token = store.batch_key
    revision = store.key
    store.ingest_mask("human", mask())
    store.ingest_mask("drone", mask())
    assert store.key != revision          # the store did change...
    assert store.batch_key == token       # ...but not the inputs of the rover search


def test_batch_key_changes_on_a_new_version_or_a_rejected_layer():
    store = complete()
    token = store.batch_key
    store.ingest_meta(metadata(version=2, stamp=2))
    assert store.batch_key != token

    store = complete()
    token = store.batch_key
    changed = mask()
    changed.data[4] = 100
    with pytest.raises(ValueError, match="changed without"):
        store.ingest_mask("rover", changed)
    assert store.batch_key != token


@pytest.mark.parametrize("field,value", [
    ("origin_lat_deg", -18.45),
    ("origin_lon_deg", 177.45),
    ("checksum_sha256", "1" * 64),
    ("sources", ["MOCK another terrain source"]),
    ("sources", ["illustrative source registry", "MOCK synthetic terrain"]),
])
def test_same_version_cannot_change_georeference_or_provenance(field, value):
    store = complete()
    token, batch = store.key, store.batch_key
    original = store.meta
    changed = metadata()
    setattr(changed, field, value)
    with pytest.raises(ValueError, match="metadata changed without a new version"):
        store.ingest_meta(changed)
    assert store.meta is original
    assert store.key == token and store.batch_key == batch
    assert store.snapshot("rover")[0] is not None


def test_metadata_copies_source_sequence_and_preserves_exact_georeference():
    store = SnapshotStore()
    message = metadata()
    assert store.ingest_meta(message)
    assert store.meta.origin_lat_deg == message.origin_lat_deg
    assert store.meta.origin_lon_deg == message.origin_lon_deg
    assert store.meta.checksum_sha256 == message.checksum_sha256
    assert store.meta.sources == tuple(message.sources)
    original_sources = store.meta.sources
    message.sources.append("later caller mutation")
    assert store.meta.sources == original_sources
    with pytest.raises(ValueError, match="metadata changed without a new version"):
        store.ingest_meta(message)


def test_duplicate_metadata_preserves_ready_layers_and_search_identity():
    store = complete()
    original_meta, token = store.meta, store.key
    original_layers = dict(store.layers)
    duplicate = metadata()
    duplicate.sources = tuple(duplicate.sources)
    assert store.ingest_meta(duplicate)
    assert store.meta is original_meta and store.key == token
    assert all(store.layers[name] is array for name, array in original_layers.items())
    assert store.snapshot("rover")[0] is not None
    assert store.ingest_meta(metadata(version=2, stamp=2))
    assert store.meta.sources == original_meta.sources
    assert store.snapshot("rover")[1] == "SNAPSHOT_INCOMPLETE"


@pytest.mark.parametrize("checksum", ["", "sha", "0" * 64])
def test_metadata_retains_legacy_checksum_strings_without_new_wire_restrictions(checksum):
    store = SnapshotStore()
    message = metadata()
    message.checksum_sha256 = checksum
    message.sources = []
    message.origin_lat_deg = message.origin_lon_deg = 0.0
    assert store.ingest_meta(message)
    assert store.meta.checksum_sha256 == checksum and store.meta.sources == ()
    assert store.ingest_meta(message)


@pytest.mark.parametrize("field,value", [
    ("origin_lat_deg", float("nan")),
    ("origin_lon_deg", float("inf")),
    ("origin_lat_deg", "18.45"),
    ("origin_lon_deg", True),
    ("origin_lat_deg", np.array(18.45)),
    ("checksum_sha256", None),
    ("checksum_sha256", 123),
    ("sources", None),
    ("sources", "CTX"),
    ("sources", {"CTX": "not a wire sequence"}),
    ("sources", ["CTX", 1]),
])
def test_invalid_georeference_or_provenance_does_not_replace_a_snapshot(field, value):
    store = complete()
    token = store.key
    changed = metadata(version=2, stamp=2)
    setattr(changed, field, value)
    with pytest.raises(ValueError):
        store.ingest_meta(changed)
    assert store.key == token
    assert store.snapshot("rover")[0] is not None


def test_ready_native_batch_is_consumed_by_the_real_planner():
    from mge_planning.core import MotionProfile, PlanRequest, ResourceBudget, RouteStatus, plan_route

    store = complete()
    assert store.ingest_meta(metadata())
    grid, reason = store.snapshot("rover")
    assert not reason
    start, goal = grid.point((1, 0)), grid.point((1, 2))
    request = PlanRequest("r", "adapter-consumer", "rover_1", "rover", 1,
                          start, goal, ResourceBudget("rover", 100., 100., 0.),
                          return_to=start)
    profile = MotionProfile("rover", 1., 90., 20., 0., 0., 1.)
    result = plan_route(terrain=grid, request=request, profile=profile)
    assert result.status == RouteStatus.FEASIBLE
    assert result.outbound_path[0] == start and result.outbound_path[-1] == goal
    assert result.return_path[-1] == start
