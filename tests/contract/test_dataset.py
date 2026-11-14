"""Synthetic delivery metadata only; no NASA data or geographic approval."""
import copy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from mge_data.dataset_contract import validate_delivery

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "data/dataset.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def delivery():
    roles = ["prior", "belief", "sigma", "nodata_mask", "traversability_human", "traversability_rover", "traversability_drone"]
    return dict(schema_version="1.0.0", dataset_id="synthetic-contract-grid", run_id="contract-only", status="provisional",
                frame_id="map", crs="test-only Mars ENU; radius unspecified, not a georeferenced product",
                vertical_datum="synthetic-test", origin=dict(lat_planetocentric_deg=0, lon_east_deg=0, x_m=0, y_m=0),
                rows=2, cols=2, resolution_m=4, row_order="south_to_north", index_order="row * cols + col",
                map_version=1, snapshot_stamp=dict(sec=1, nanosec=0),
                sources=[dict(product_id="synthetic", source_url="https://example.invalid/product", license_or_terms_url="https://example.invalid/terms", sha256="0"*64)],
                layers=[dict(role=r, path=r+".bin", sha256=hashlib.sha256(r.encode()).hexdigest(), map_version=1,
                             encoding="occupancy" if r.startswith("traversability_") else "8UC1" if r=="nodata_mask" else "32FC1",
                             nodata=None, source_product_ids=["synthetic"]) for r in roles],
                control_points=[dict(id=str(i), lat_planetocentric_deg=0, lon_east_deg=0, x_m=x, y_m=y, z_m=0, tolerance_m=1) for i,(x,y) in enumerate([(0,0),(8,0),(0,8)])],
                approval=dict(owner="David", state="pending", evidence=None))


def validate(document, directory=None):
    VALIDATOR.validate(document)
    return validate_delivery(document, directory)


def test_delivery_schema_and_exact_bytes(tmp_path):
    Draft202012Validator.check_schema(SCHEMA)
    doc = delivery()
    for layer in doc["layers"]:
        (tmp_path / layer["path"]).write_bytes(layer["role"].encode())
    validate(doc, tmp_path)
    (tmp_path / "belief.bin").write_bytes(b"changed")
    with pytest.raises(ValueError, match="CHECKSUM"):
        validate(doc, tmp_path)


@pytest.mark.parametrize("key", ["dataset_id", "run_id", "crs", "vertical_datum", "control_points", "snapshot_stamp"])
def test_required_metadata(key):
    doc=delivery(); del doc[key]
    with pytest.raises(ValidationError): validate(doc)


@pytest.mark.parametrize("change", [dict(frame_id="earth"),dict(row_order="north_to_south"),dict(status="approved"),dict(map_version=2**32)])
def test_schema_rejects_incompatible_or_unapproved(change):
    with pytest.raises(ValidationError): validate(delivery() | change)


@pytest.mark.parametrize("path", ["../reference.bin", "/secret.bin", "C:/secret.bin", "foo\\bar.bin", "hidden.bin", "evaluation_reference.bin"])
def test_forbid_reference_and_unsafe_paths(path):
    doc=delivery(); doc["layers"][0]["path"]=path
    with pytest.raises(ValueError): validate(doc)


def test_reject_mixed_layers_earth_crs_and_missing_masks():
    doc=delivery(); doc["layers"][2]["map_version"]=0
    with pytest.raises(ValueError, match="MIXED_MAP"): validate(doc)
    with pytest.raises(ValueError, match="EARTH_CRS"): validate(delivery() | dict(crs="Mars using EPSG:4326"))
    doc=delivery(); doc["layers"][3]["role"]="belief"
    with pytest.raises(ValueError, match="LAYER_SET"): validate(doc)


def test_reject_fake_controls_nonfinite_and_evaluator_layer():
    doc=delivery(); doc["control_points"][2]["y_m"]=0
    with pytest.raises(ValueError, match="COLLINEAR"): validate(doc)
    doc=delivery(); doc["origin"]["x_m"]=float("nan")
    with pytest.raises(ValueError): validate(doc)
    doc=delivery(); doc["layers"][0]["role"]="evaluation_reference"
    with pytest.raises(ValidationError): validate(doc)
