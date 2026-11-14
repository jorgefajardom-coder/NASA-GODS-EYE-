"""Pending templates cannot become ready products without complete provenance."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from mge_data.core import TerrainMetadata


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "data/manifest.schema.json").read_text(encoding="utf-8"))
TEMPLATE = json.loads((ROOT / "data/sample/manifest.template.json").read_text(encoding="utf-8"))


def validator():
    Draft202012Validator.check_schema(SCHEMA)
    return Draft202012Validator(SCHEMA)


def complete_manifest():
    """Synthetic structural test metadata only; no claimed NASA product or asset."""
    document = copy.deepcopy(TEMPLATE)
    document.update(status="ready", resolution_m=20.0, rows=8, cols=8,
                    row_orientation="north_to_south", vertical_datum="test-only-datum")
    document["local_origin"] = dict(lat_planetocentric_deg=18.0, lon_east_deg=77.0)
    for source in document["sources"]:
        source.update(product_id="synthetic-schema-test", native_resolution_m=20.0,
                      source_url="https://example.invalid/schema-test",
                      sha256="0" * 64, license_or_terms_url="https://example.invalid/terms")
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


@pytest.mark.parametrize("missing", ["product_id", "source_url", "sha256",
                                      "native_resolution_m", "license_or_terms_url"])
def test_ready_manifest_requires_every_source_to_have_provenance(missing):
    document = complete_manifest()
    document["sources"][-1][missing] = None
    with pytest.raises(ValidationError):
        validator().validate(document)


@pytest.mark.parametrize("change", [dict(frame_id="EPSG:4326"), dict(vertical_units="feet"),
                                    dict(resolution_m=0), dict(rows=0)])
def test_manifest_rejects_wrong_frame_units_and_grid_shape(change):
    with pytest.raises(ValidationError):
        validator().validate(complete_manifest() | change)


@pytest.mark.parametrize("digest", ["not-a-checksum", "0" * 63, "g" * 64])
def test_ready_source_requires_full_hexadecimal_sha256(digest):
    document = complete_manifest()
    document["sources"][0]["sha256"] = digest
    with pytest.raises(ValidationError):
        validator().validate(document)


@pytest.mark.parametrize("changes", [dict(rows=0), dict(cols=1.5), dict(rows=True),
                                     dict(resolution_m=float("nan")),
                                     dict(map_version=-1), dict(map_version=1.5),
                                     dict(frame_id="EPSG:4326"), dict(vertical_datum="")])
def test_public_metadata_rejects_invalid_geometry_and_version(changes):
    values = dict(dataset_id="test-only-grid", rows=8, cols=8, resolution_m=20.0,
                  vertical_datum="test-only-datum")
    with pytest.raises(ValueError):
        TerrainMetadata(**(values | changes))
