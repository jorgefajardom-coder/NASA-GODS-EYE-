"""Target ROS launch must fail before creating providers without owner inputs."""
import json
from pathlib import Path
import runpy

import pytest

pytest.importorskip("launch_ros", reason="Requires ROS 2 Jazzy launch runtime")
from launch import LaunchContext

ROOT=Path(__file__).resolve().parents[2]


def test_launch_rejects_missing_receipt_before_starting_any_provider():
    launch=runpy.run_path(str(ROOT/"src/mge_bringup/launch/profile.launch.py"))
    context=LaunchContext()
    context.launch_configurations.update(profile="mock",run_id="contract-only",approval_receipt="")
    with pytest.raises(RuntimeError,match="NOT_READY.*approval_receipt"):
        launch["_start"](context)


def test_live_profile_rejected_even_with_explicit_receipt(tmp_path):
    launch=runpy.run_path(str(ROOT/"src/mge_bringup/launch/profile.launch.py"))
    receipt=tmp_path/"receipt.json"; receipt.write_text(json.dumps({}))
    context=LaunchContext()
    context.launch_configurations.update(profile="live",run_id="contract-only",approval_receipt=str(receipt))
    with pytest.raises(ValueError,match="LIVE_BACKEND_UNAVAILABLE"):
        launch["_start"](context)
