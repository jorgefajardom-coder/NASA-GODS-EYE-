"""Every required piece of verified evidence must hold for mission success."""

import pytest

from mge_mission.core import mission_success


EVIDENCE = dict(primary_goal_completed=True, returned_to_base_within_tolerance=True,
                verified_ground_traversal_under_model=True, no_budget_violation=True)


def test_complete_verified_return_within_budget_meets_criterion():
    assert mission_success(**EVIDENCE) is True


@pytest.mark.parametrize("predicate", list(EVIDENCE))
def test_one_failed_required_condition_prevents_mission_success(predicate):
    assert mission_success(**(EVIDENCE | {predicate: False})) is False


@pytest.mark.parametrize("invalid", [None, "false", "true", 0, 1, [], {}])
def test_missing_or_truthy_nonboolean_evidence_cannot_produce_success(invalid):
    with pytest.raises(TypeError, match="explicit boolean"):
        mission_success(**(EVIDENCE | {"no_budget_violation": invalid}))
