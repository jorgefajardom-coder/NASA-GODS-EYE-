"""Fresh-crop interchange checks; no network access or mission claims."""

import importlib.util
import io
import json
from pathlib import Path
import re

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("prepare_planner_terrain", ROOT / "scripts/prepare_planner_terrain.py")
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)


def fixture_crop(tmp_path):
    path = tmp_path / "terrain.npz"
    elevation = np.array([[1.0, np.nan], [3.0, 4.0]], dtype=np.float32)
    np.savez_compressed(path, elevation_m=elevation, valid_mask=np.isfinite(elevation),
                        resolution_m=np.array(4.0), origin_x_m=np.array(-4.0), origin_y_m=np.array(-4.0),
                        row_orientation=np.array("south_to_north"))
    return path, {"role": "prior", "source": {"instrument": "CTX"},
                  "row_orientation": "south_to_north", "rows": 2, "cols": 2,
                  "resolution_m": 4.0, "origin_x_m": -4.0, "origin_y_m": -4.0,
                  "sha256": importer.file_sha256(path)}


def test_north_first_conversion_preserves_masks_and_control_points():
    # North row is y=+2; south row is y=-2. East/west is never transposed.
    north = np.array([[11.0, 12.0], [21.0, np.nan]])
    south, valid = importer.south_first(north, np.isfinite(north))
    np.testing.assert_equal(south, [[21.0, np.nan], [11.0, 12.0]])
    np.testing.assert_array_equal(valid, [[True, False], [True, True]])
    assert north[0, 0] == 11.0  # source memory remains unchanged


def test_crop_validity_and_checksum(tmp_path):
    path, manifest = fixture_crop(tmp_path)
    importer.validate_public_crop(manifest, path)
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="checksum"):
        importer.validate_public_crop(manifest, path)


def test_reference_cannot_be_validated_as_public_input(tmp_path):
    path, manifest = fixture_crop(tmp_path)
    manifest["role"] = "evaluation_reference"
    manifest["source"]["instrument"] = "HiRISE"
    with pytest.raises(ValueError, match="CTX prior"):
        importer.validate_public_crop(manifest, path)


def test_wrong_row_convention_is_rejected(tmp_path):
    path, manifest = fixture_crop(tmp_path)
    manifest["row_orientation"] = "north_to_south"
    with pytest.raises(ValueError, match="south-first"):
        importer.validate_public_crop(manifest, path)


def test_public_bundle_cannot_hide_extra_reference_arrays(tmp_path):
    path, manifest = fixture_crop(tmp_path)
    with np.load(path) as dataset:
        arrays = {key: dataset[key] for key in dataset.files}
    np.savez_compressed(path, **arrays, reference=np.ones((2, 2)))
    manifest["sha256"] = importer.file_sha256(path)
    with pytest.raises(ValueError, match="unexpected arrays"):
        importer.validate_public_crop(manifest, path)


def test_missing_source_pixels_remain_invalid(tmp_path):
    path, manifest = fixture_crop(tmp_path)
    with np.load(path) as dataset:
        arrays = {key: dataset[key] for key in dataset.files}
    arrays["valid_mask"] = np.ones((2, 2), dtype=bool)
    np.savez_compressed(path, **arrays)
    manifest["sha256"] = importer.file_sha256(path)
    with pytest.raises(ValueError, match="finite source elevations"):
        importer.validate_public_crop(manifest, path)


def test_range_reader_seeks_without_fetching_whole_upstream_file(monkeypatch):
    source = bytes(range(256)) * 800
    requests = []

    class Response(io.BytesIO):
        status = 206

    def request_slice(request, timeout):
        start, end = map(int, re.fullmatch(r"bytes=(\d+)-(\d+)", request.headers["Range"]).groups())
        response = Response(source[start:end + 1])
        response.headers = {"Content-Range": f"bytes {start}-{end}/{len(source)}"}
        requests.append((start, end))
        return response

    monkeypatch.setattr(importer.urllib.request, "urlopen", request_slice)
    reader = importer.HTTPRangeReader("https://example.invalid/source.tif", {"Content-Length": str(len(source))}, block_size=65536)
    reader.seek(65530)
    assert reader.read(20) == source[65530:65550]
    reader.seek(-11, 2)
    assert reader.read() == source[-11:]
    reader.seek(65530)
    assert reader.read(20) == source[65530:65550]
    assert len(requests) == 3  # repeated reads use cached bounded pages
    assert all(end - start + 1 <= 65536 for start, end in requests)


def test_range_reader_rejects_a_server_ignoring_ranges(monkeypatch):
    response = io.BytesIO(b"whole upstream response")
    response.status = 200
    response.headers = {}
    monkeypatch.setattr(importer.urllib.request, "urlopen", lambda *args, **kwargs: response)
    reader = importer.HTTPRangeReader("https://example.invalid/source.tif", {"Content-Length": "100"})
    with pytest.raises(OSError, match="bounded HTTP Range"):
        reader.read(1)


def test_committed_public_crop_integrity_and_control_points():
    directory = ROOT / "data/planner_provisional"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    importer.validate_public_crop(manifest, directory / "terrain.npz")
    assert manifest["knowledge_state"] == "orbital_prior_not_locally_verified"
    assert manifest["source"]["native_resolution_m"] == 20.0
    assert manifest["resolution_m"] == 4.0
    assert manifest["source"]["mission"] == "MRO"
    with np.load(directory / "terrain.npz", allow_pickle=False) as dataset:
        for point in manifest["control_points"]:
            assert point["x_m"] == manifest["origin_x_m"] + (point["col"] + 0.5) * manifest["resolution_m"]
            assert point["y_m"] == manifest["origin_y_m"] + (point["row"] + 0.5) * manifest["resolution_m"]
            assert point["elevation_m"] == dataset["elevation_m"][point["row"], point["col"]]
