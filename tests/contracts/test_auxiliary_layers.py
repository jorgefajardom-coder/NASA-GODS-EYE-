"""Public auxiliary layers are bounded visual context, never navigation evidence."""

from dataclasses import replace
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from mge_data.core import load_auxiliary_terrain_layers, load_public_terrain
from mge_data.node import build_aux_layer_messages_dict

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("prepare_auxiliary_test", ROOT / "scripts/prepare_jezero_aux_layers.py")
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


@pytest.fixture
def sample(tmp_path):
    target = tmp_path / "sample"
    shutil.copytree(ROOT / "data/sample", target)
    return target


def read_manifest(sample):
    return json.loads((sample / "aux_layers_manifest.json").read_text(encoding="utf-8"))


def write_manifest(sample, document):
    (sample / "aux_layers_manifest.json").write_text(json.dumps(document), encoding="utf-8")


def change_array(sample, key, value):
    path = sample / "jezero_aux_layers.npz"
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    arrays[key] = value
    np.savez_compressed(path, **arrays)
    document = read_manifest(sample)
    document["files"]["aux_npz"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_manifest(sample, document)


@pytest.mark.parametrize("field,value", [
    ("aligned_terrain_npz_sha256", "0" * 64),
    ("region_id", "another-region"),
    ("frame_id", "odom"),
    ("vertical_datum", "another vertical datum"),
    ("crs", "another Mars projection"),
    ("row_orientation", "north_to_south"),
    ("grid.origin_x_m", -60.0),
    ("grid.origin_y_m", -60.0),
    ("grid.lat_planetocentric_deg", -18.45),
    ("grid.lon_east_deg", 177.45),
    ("grid.resolution_m", 8.0),
    ("grid.rows", 31),
])
def test_auxiliary_manifest_is_bound_to_the_exact_public_terrain(sample, field, value):
    tile = load_public_terrain(sample / "manifest.json")
    document = read_manifest(sample)
    if field.startswith("grid."):
        document["grid"][field.split(".")[1]] = value
    else:
        document[field] = value
    write_manifest(sample, document)
    with pytest.raises(ValueError):
        load_auxiliary_terrain_layers(sample / "manifest.json", tile=tile, strict=True)


@pytest.mark.parametrize("key,value", [
    ("x_m", np.arange(31, dtype=np.float32)),
    ("x_m", np.arange(32, dtype=np.float32)),
    ("y_m", np.full(32, np.nan, dtype=np.float32)),
    ("surface_zone_code", np.full((32, 32), 9, dtype=np.int8)),
    ("ctx_ortho_dn", np.full((32, 32), 300, dtype=np.int32)),
    ("hidden_dem", np.zeros((32, 32), dtype=np.float32)),
])
def test_auxiliary_array_geometry_and_public_schema_are_checked_before_casting(sample, key, value):
    tile = load_public_terrain(sample / "manifest.json")
    change_array(sample, key, value)
    with pytest.raises((ValueError, PermissionError)):
        load_auxiliary_terrain_layers(sample / "manifest.json", tile=tile, strict=True)


@pytest.mark.parametrize("role", ["aux_npz", "geology_json", "ctx_ortho_png"])
def test_every_auxiliary_file_requires_its_hash(sample, role):
    tile = load_public_terrain(sample / "manifest.json")
    document = read_manifest(sample)
    document["files"][role].pop("sha256")
    write_manifest(sample, document)
    with pytest.raises(ValueError):
        load_auxiliary_terrain_layers(sample / "manifest.json", tile=tile)


@pytest.mark.parametrize("role", ["aux_npz", "geology_json", "ctx_ortho_png"])
def test_declared_paths_cannot_escape_the_public_bundle(sample, role):
    tile = load_public_terrain(sample / "manifest.json")
    document = read_manifest(sample)
    source = sample / document["files"][role]["path"]
    outside = sample.parent / source.name
    shutil.copyfile(source, outside)
    document["files"][role]["path"] = "../" + source.name
    write_manifest(sample, document)
    with pytest.raises(PermissionError):
        load_auxiliary_terrain_layers(sample / "manifest.json", tile=tile)


def test_auxiliary_symlinks_cannot_read_an_external_file(sample):
    tile = load_public_terrain(sample / "manifest.json")
    path = sample / "geology.json"
    outside = sample.parent / "geology.json"
    shutil.copyfile(path, outside)
    path.unlink()
    try:
        path.symlink_to(outside)
    except OSError:
        pytest.skip("Host does not permit creation of a symlink")
    with pytest.raises(PermissionError):
        load_auxiliary_terrain_layers(sample / "manifest.json", tile=tile)


def test_incomplete_present_bundle_is_not_treated_as_absent(sample):
    tile = load_public_terrain(sample / "manifest.json")
    (sample / "ctx_ortho.png").unlink()
    with pytest.raises((ValueError, FileNotFoundError)):
        load_auxiliary_terrain_layers(sample / "manifest.json", tile=tile)


def test_message_consumer_rejects_a_tile_from_another_origin(sample):
    tile = load_public_terrain(sample / "manifest.json")
    aux = load_auxiliary_terrain_layers(sample / "manifest.json", tile=tile, strict=True)
    other = replace(tile, metadata=replace(tile.metadata, origin_x_m=tile.metadata.origin_x_m + 4))
    with pytest.raises(ValueError):
        build_aux_layer_messages_dict(other, aux)


@pytest.mark.parametrize("change", ["missing", "rows", "resolution", "latitude", "longitude"])
def test_producer_rejects_unbound_terrain_before_any_remote_request(sample, monkeypatch, change):
    calls = []
    monkeypatch.setattr(producer, "crop_ctx_orthomosaic", lambda **kw: calls.append(kw))
    monkeypatch.setattr(producer, "fetch_and_rasterize_sim3464_geology", lambda **kw: calls.append(kw))
    kwargs = {}
    if change == "missing":
        (sample / "terrain.npz").unlink()
    else:
        kwargs[{"rows": "rows_override", "resolution": "resolution_override",
                "latitude": "lat_override", "longitude": "lon_override"}[change]] = {
                    "rows": 31, "resolution": 8.0, "latitude": -18.45, "longitude": 177.45}[change]
    with pytest.raises((ValueError, FileNotFoundError)):
        producer.build_auxiliary_package(manifest_path=sample / "manifest.json", **kwargs)
    assert calls == []


def test_surface_proxy_preserves_nodata_and_does_not_certify_agent_passage():
    elevation = np.zeros((4, 4), dtype=np.float32)
    elevation[0, 0] = np.nan
    ortho = np.full((4, 4), 100, dtype=np.uint8)
    valid = np.ones((4, 4), dtype=bool)
    valid[3, 3] = False
    slope, code, occupancy, _ = producer.compute_literal_surface_zones(
        elevation, ortho, valid, resolution_m=4., slope_limits_deg={"human": 10., "rover": 20.})
    assert code[0, 0] == code[3, 3] == 0
    assert occupancy[0, 0] == occupancy[3, 3] == -1
    assert all(not item.get("traversable_agents") for item in producer.SURFACE_ZONE_DEFINITIONS)


def test_valid_published_auxiliary_bundle_is_visual_only_and_keeps_the_prior(sample):
    tile = load_public_terrain(sample / "manifest.json")
    before = tile.prior.copy()
    aux = load_auxiliary_terrain_layers(sample / "manifest.json", tile=tile, strict=True)
    assert aux.manifest["classification"] == "ESTIMATED_VISUAL_CONTEXT"
    assert aux.manifest["navigation_authorization"] is False
    assert aux.zone_at_row_col(16, 16)["navigation_authorization"] is False
    messages = build_aux_layer_messages_dict(tile, aux)
    assert len(messages["ctx_ortho"]["data"]) == 32 * 32
    assert set(messages["surface_zones"]["data"]) <= {-1, 15, 35, 55, 75, 95}
    np.testing.assert_array_equal(tile.prior, before)
    assert not tile.observed_mask.any()



def test_loader_validates_binding_even_without_an_explicit_tile(sample):
    aux = load_auxiliary_terrain_layers(sample / "aux_layers_manifest.json", strict=True)
    assert aux.manifest["aligned_terrain_npz_sha256"] == load_public_terrain(sample / "manifest.json").metadata.checksum_sha256


def test_terrain_nodata_cannot_be_presented_as_a_valid_surface_proxy(sample):
    tile = load_public_terrain(sample / "manifest.json")
    nodata = tile.nodata_mask.copy()
    nodata[0, 0] = True
    prior = tile.prior.copy()
    prior[0, 0] = np.nan
    with pytest.raises(ValueError, match="NoData"):
        load_auxiliary_terrain_layers(sample / "manifest.json", tile=replace(tile, prior=prior, nodata_mask=nodata))


def test_valid_producer_preserves_real_prior_slope_and_roundtrips_through_the_consumer(sample, tmp_path, monkeypatch):
    tile = load_public_terrain(sample / "manifest.json")
    shape = tile.prior.shape
    def synthetic_ortho(**kwargs):
        return (np.full(shape, 100, dtype=np.uint8), np.zeros(shape, dtype=np.float32),
                np.ones(shape, dtype=bool), {"source_kind": "SIMULATED_TEST_FIXTURE"})
    def synthetic_geology(**kwargs):
        return (np.zeros(shape, dtype=np.int16), np.full(shape, -1, dtype=np.int8),
                {"source": {"doi": "TEST_ONLY", "scale": "TEST_ONLY"},
                 "units": [], "polygons": [], "context_polygons": []})
    monkeypatch.setattr(producer, "crop_ctx_orthomosaic", synthetic_ortho)
    monkeypatch.setattr(producer, "fetch_and_rasterize_sim3464_geology", synthetic_geology)
    before_prior, before_sigma, before_observed = tile.prior.copy(), tile.sigma.copy(), tile.observed_mask.copy()
    out = tmp_path / "generated-auxiliary-test-only"
    manifest = producer.build_auxiliary_package(
        manifest_path=sample / "manifest.json", out_dir=out,
        lat_override=tile.metadata.origin_lat_deg, lon_override=tile.metadata.origin_lon_deg,
        rows_override=tile.metadata.rows, resolution_override=tile.metadata.resolution_m)
    aux = load_auxiliary_terrain_layers(out / "aux_layers_manifest.json", tile=tile, strict=True)
    assert np.nanmax(aux.slope_deg) > 0  # The real nonflat prior did not become a zero DEM.
    assert manifest["aligned_terrain_npz_sha256"] == tile.metadata.checksum_sha256
    assert manifest["vertical_datum"] == tile.metadata.vertical_datum
    assert build_aux_layer_messages_dict(tile, aux)["ctx_ortho"]["height"] == shape[0]
    np.testing.assert_array_equal(tile.prior, before_prior)
    np.testing.assert_array_equal(tile.sigma, before_sigma)
    np.testing.assert_array_equal(tile.observed_mask, before_observed)


@pytest.mark.parametrize("field,value", [("width", 31), ("height", 31), ("row0", "south")])
def test_png_geometry_and_orientation_are_bound_to_the_same_grid(sample, field, value):
    tile = load_public_terrain(sample / "manifest.json")
    document = read_manifest(sample)
    document["files"]["ctx_ortho_png"][field] = value
    write_manifest(sample, document)
    with pytest.raises(ValueError, match="PNG"):
        load_auxiliary_terrain_layers(sample / "manifest.json", tile=tile)
