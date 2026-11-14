"""Contract and acceptance tests (T-01, T-02, T-03, T-04, T-07) for public terrain data."""

import copy
import json
from pathlib import Path
import shutil

import numpy as np
import pytest
from jsonschema import Draft202012Validator, ValidationError
import yaml

from mge_data.core import (
    GeoTransform,
    ManifestValidator,
    SourceRegistry,
    TerrainMetadata,
    load_public_terrain,
)
from mge_data.node import build_terrain_meta_dict

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "data/manifest.schema.json").read_text(encoding="utf-8"))
TEMPLATE = json.loads((ROOT / "data/sample/manifest.template.json").read_text(encoding="utf-8"))
READY_MANIFEST_PATH = ROOT / "data/sample/manifest.json"
READY_MANIFEST = json.loads(READY_MANIFEST_PATH.read_text(encoding="utf-8"))
TERRAIN_CONFIG = yaml.safe_load((ROOT / "config/terrain.yml").read_text(encoding="utf-8"))


def validator():
    Draft202012Validator.check_schema(SCHEMA)
    return Draft202012Validator(SCHEMA)


def complete_manifest():
    """Synthetic structural test metadata only; no claimed NASA product or asset."""
    document = copy.deepcopy(TEMPLATE)
    document.update(
        status="ready",
        resolution_m=20.0,
        rows=8,
        cols=8,
        row_orientation="north_to_south",
        vertical_datum="test-only-datum",
    )
    document["local_origin"] = dict(lat_planetocentric_deg=18.0, lon_east_deg=77.0)
    for source in document["sources"]:
        source.update(
            product_id="synthetic-schema-test",
            native_resolution_m=20.0,
            source_url="https://example.invalid/schema-test",
            sha256="0" * 64,
            license_or_terms_url="https://example.invalid/terms",
        )
    return document


def test_pending_manifest_preserves_unknown_metadata_without_claiming_ready_data():
    validator().validate(TEMPLATE)
    assert TEMPLATE["status"] == "pending"
    assert TEMPLATE["resolution_m"] is None
    assert all(source["sha256"] is None for source in TEMPLATE["sources"])


def test_flipping_pending_template_to_ready_is_rejected():
    document = copy.deepcopy(TEMPLATE)
    document["status"] = "ready"
    with pytest.raises(ValidationError):
        validator().validate(document)


def test_structurally_complete_manifest_passes_without_claiming_scientific_approval():
    validator().validate(complete_manifest())


@pytest.mark.parametrize(
    "missing",
    ["product_id", "source_url", "sha256", "native_resolution_m", "license_or_terms_url"],
)
def test_ready_manifest_requires_every_source_to_have_provenance(missing):
    document = complete_manifest()
    document["sources"][-1][missing] = None
    with pytest.raises(ValidationError):
        validator().validate(document)


@pytest.mark.parametrize(
    "change",
    [
        dict(frame_id="EPSG:4326"),
        dict(vertical_units="feet"),
        dict(resolution_m=0),
        dict(rows=0),
    ],
)
def test_manifest_rejects_wrong_frame_units_and_grid_shape(change):
    with pytest.raises(ValidationError):
        validator().validate(complete_manifest() | change)


@pytest.mark.parametrize("digest", ["not-a-checksum", "0" * 63, "g" * 64])
def test_ready_source_requires_full_hexadecimal_sha256(digest):
    document = complete_manifest()
    document["sources"][0]["sha256"] = digest
    with pytest.raises(ValidationError):
        validator().validate(document)


@pytest.mark.parametrize(
    "changes",
    [
        dict(rows=0),
        dict(cols=1.5),
        dict(rows=True),
        dict(resolution_m=float("nan")),
        dict(map_version=-1),
        dict(map_version=1.5),
        dict(frame_id="EPSG:4326"),
        dict(vertical_datum=""),
        dict(vertical_datum="WGS84 ellipsoid"),
    ],
)
def test_public_metadata_rejects_invalid_geometry_and_version(changes):
    values = dict(
        dataset_id="test-only-grid",
        rows=8,
        cols=8,
        resolution_m=20.0,
        vertical_datum="test-only-datum",
    )
    with pytest.raises(ValueError):
        TerrainMetadata(**(values | changes))


def test_t01_delivered_jezero_manifest_passes_schema_and_multi_mission_registry():
    """T-01: Delivered data/sample/manifest.json is ready and registers MRO/CTX, MRO/HiRISE, and MGS/MOLA."""
    validator().validate(READY_MANIFEST)
    assert READY_MANIFEST["status"] == "ready"
    assert READY_MANIFEST["frame_id"] == "map"
    assert READY_MANIFEST["row_orientation"] == "south_to_north"
    registry = ManifestValidator().validate_document(READY_MANIFEST, require_ready=True)
    assert isinstance(registry, SourceRegistry)
    assert registry.by_role("prior").instrument == "CTX"
    assert registry.by_role("evaluation_reference").instrument == "HiRISE"
    assert registry.by_role("regional_context").mission == "Mars Global Surveyor"
    assert registry.by_role("regional_context").instrument == "MOLA"


def test_t02_corrupted_sha256_is_detected_and_rejected(tmp_path):
    """T-02: Mismatched or corrupted SHA-256 in manifest or terrain.npz raises ValueError."""
    sample_copy = tmp_path / "sample"
    shutil.copytree(ROOT / "data/sample", sample_copy)
    manifest_copy_path = sample_copy / "manifest.json"
    tampered = json.loads(manifest_copy_path.read_text(encoding="utf-8"))
    tampered["sources"][0]["sha256"] = "a" * 64
    manifest_copy_path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        load_public_terrain(manifest_copy_path)


def test_t03_control_points_match_enu_latlon_elevation_and_reject_transpose():
    """T-03: >=3 non-collinear control points with off-diagonal cells match within tolerance and detect x/y transpose."""
    tile = load_public_terrain(READY_MANIFEST_PATH)
    assert len(tile.control_points) >= 3
    assert any(cp["row"] != cp["col"] for cp in tile.control_points)
    tile.transform.verify_control_points(tile.control_points, tile.prior)
    tile.transform.verify_control_points(TERRAIN_CONFIG["control_points"], tile.prior)

    # Transposing the elevation grid (swapping row/col -> x/y) must fail verification on off-diagonal points
    with pytest.raises(ValueError, match="elevation mismatch"):
        tile.transform.verify_control_points(tile.control_points, tile.prior.T)

    # Diagonal-only control points must be rejected because they cannot detect x/y transpose
    diagonal_only = [cp for cp in tile.control_points if cp["row"] == cp["col"]]
    diagonal_three = [
        diagonal_only[0],
        {
            "id": "cp_mid_diag",
            "row": 16,
            "col": 16,
            "x_east_m": 2.0,
            "y_north_m": 2.0,
            "elevation_m": float(tile.prior[16, 16]),
            "lat_planetocentric_deg": tile.transform.enu_to_planetocentric(2.0, 2.0)[0],
            "lon_east_deg": tile.transform.enu_to_planetocentric(2.0, 2.0)[1],
        },
        diagonal_only[-1],
    ]
    with pytest.raises(ValueError, match="off-diagonal"):
        tile.transform.verify_control_points(diagonal_three, tile.prior)


def test_t04_orbital_prior_is_not_locally_observed_and_preserves_nodata_semantics():
    """T-04: Valid orbital prior cells start with observed_mask=False, and NoData cells are never marked observed."""
    tile = load_public_terrain(READY_MANIFEST_PATH)
    assert tile.prior.shape == (32, 32)
    assert np.all(~tile.observed_mask)
    assert np.array_equal(tile.nodata_mask, ~np.isfinite(tile.prior))
    meta_dict = build_terrain_meta_dict(tile, run_id="test-run")
    assert meta_dict["frame_id"] == "map"
    assert meta_dict["rows"] == 32 and meta_dict["cols"] == 32
    assert all("HiRISE" not in src for src in meta_dict["sources"])


def test_t07_reference_isolation_prevents_loading_or_bundling_evaluator_assets(tmp_path):
    """T-07: Public loader rejects paths under reference/ and rejects forbidden reference keys in terrain.npz."""
    ref_dir = tmp_path / "reference"
    ref_dir.mkdir()
    ref_manifest = ref_dir / "manifest.json"
    ref_manifest.write_text(json.dumps(READY_MANIFEST), encoding="utf-8")
    with pytest.raises(PermissionError, match="evaluator reference"):
        load_public_terrain(ref_manifest)

    sample_copy = tmp_path / "sample"
    shutil.copytree(ROOT / "data/sample", sample_copy)
    npz_path = sample_copy / "terrain.npz"
    with np.load(npz_path, allow_pickle=False) as current:
        arrays = {k: current[k] for k in current.files}
    np.savez_compressed(npz_path, **arrays, hirise=np.zeros((32, 32), dtype=np.float32))
    import hashlib

    manifest_copy = json.loads((sample_copy / "manifest.json").read_text(encoding="utf-8"))
    manifest_copy["sources"][0]["sha256"] = hashlib.sha256(npz_path.read_bytes()).hexdigest()
    (sample_copy / "manifest.json").write_text(json.dumps(manifest_copy), encoding="utf-8")
    with pytest.raises(PermissionError, match="forbidden reference key"):
        load_public_terrain(sample_copy / "manifest.json")
