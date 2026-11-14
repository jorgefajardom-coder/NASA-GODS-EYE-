"""Public delivery checks; no dataset loading, map fusion or scientific approval."""
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

ROLES = {"prior", "belief", "sigma", "nodata_mask", "traversability_human",
         "traversability_rover", "traversability_drone"}


def validate_delivery(document, dataset_dir=None):
    """Validate semantic identity after dataset.schema.json structural validation.

    Optional byte checks constrain every file to dataset_dir. Callers must also
    validate the JSON Schema; this helper never grants scientific acceptance.
    """
    json.dumps(document, allow_nan=False)
    if document["frame_id"] != "map" or document["row_order"] != "south_to_north":
        raise ValueError("FRAME_OR_ROW_ORDER")
    crs = document["crs"].lower()
    if not ("mars" in crs or "iau:499" in crs or "iau_499" in crs):
        raise ValueError("EXPLICIT_MARTIAN_CRS_REQUIRED")
    if "4326" in crs or "wgs84" in crs or "wgs 84" in crs:
        raise ValueError("EARTH_CRS_FORBIDDEN")
    points = document["control_points"]
    if len(points) != 3 or len({p["id"] for p in points}) != 3:
        raise ValueError("THREE_DISTINCT_CONTROL_POINTS_REQUIRED")
    a, b, c = points
    area = ((b["x_m"] - a["x_m"]) * (c["y_m"] - a["y_m"])
            - (b["y_m"] - a["y_m"]) * (c["x_m"] - a["x_m"]))
    if not math.isfinite(area) or abs(area) < 1e-12:
        raise ValueError("COLLINEAR_CONTROL_POINTS")
    layers = document["layers"]
    if len(layers) != len(ROLES) or {x["role"] for x in layers} != ROLES:
        raise ValueError("PUBLIC_LAYER_SET_REQUIRED")
    expected = {"prior":"32FC1", "belief":"32FC1", "sigma":"32FC1", "nodata_mask":"8UC1",
                **{f"traversability_{kind}":"occupancy" for kind in ("human","rover","drone")}}
    if any(layer["encoding"] != expected[layer["role"]] for layer in layers):
        raise ValueError("LAYER_ENCODING_MISMATCH")
    if any(layer["map_version"] != document["map_version"] for layer in layers):
        raise ValueError("MIXED_MAP_VERSIONS")
    ids = [x["product_id"] for x in document["sources"]]
    if len(ids) != len(set(ids)):
        raise ValueError("DUPLICATE_PRODUCT_ID")
    if any(not set(layer["source_product_ids"]) <= set(ids) for layer in layers):
        raise ValueError("UNKNOWN_LAYER_SOURCE")
    paths = [layer["path"] for layer in layers]
    if len(set(paths)) != len(paths):
        raise ValueError("LAYER_PATH_ALIAS")
    for layer in layers:
        path = PurePosixPath(layer["path"])
        if (path.is_absolute() or not path.parts or ".." in path.parts
                or any("\\" in part or ":" in part for part in path.parts)):
            raise ValueError("UNSAFE_LAYER_PATH")
        if any(token in layer["path"].lower() for token in ("reference", "evaluator", "ground_truth", "hidden")):
            raise ValueError("EVALUATOR_ASSET_FORBIDDEN")
        if dataset_dir is not None:
            base = Path(dataset_dir).resolve()
            target = (base / layer["path"]).resolve()
            if not target.is_relative_to(base):
                raise ValueError("LAYER_ESCAPES_DATASET")
            if hashlib.sha256(target.read_bytes()).hexdigest() != layer["sha256"]:
                raise ValueError("LAYER_CHECKSUM_MISMATCH")
    return document
