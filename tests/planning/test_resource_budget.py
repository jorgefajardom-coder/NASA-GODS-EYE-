"""Resource-model boundary checks; these do not certify physical mission safety."""

import pytest

from mge_planning.core import ResourceBudget, RouteStatus


def human_budget(**changes):
    values = dict(agent_kind="human", time_s=600.0, energy_wh=100.0,
                  reserve_wh=20.0, oxygen_l=50.0, reserve_oxygen_l=10.0)
    return ResourceBudget(**(values | changes))


@pytest.mark.parametrize("missing", ["oxygen_l", "reserve_oxygen_l"])
def test_human_cannot_start_without_explicit_oxygen_budget_and_reserve(missing):
    with pytest.raises(ValueError, match="separate oxygen budget"):
        human_budget(**{missing: None})


@pytest.mark.parametrize("kind", ["rover", "drone"])
@pytest.mark.parametrize("oxygen", [0.0, 1.0])
def test_nonhuman_must_not_inherit_human_oxygen_profile(kind, oxygen):
    with pytest.raises(ValueError, match="must not include human oxygen"):
        ResourceBudget(kind, 600.0, 100.0, 20.0, oxygen_l=oxygen)


@pytest.mark.parametrize("field", ["time_s", "energy_wh", "reserve_wh", "oxygen_l", "reserve_oxygen_l"])
@pytest.mark.parametrize("invalid", [-1.0, float("nan"), float("inf"), -float("inf")])
def test_budget_rejects_negative_or_nonfinite_resources(field, invalid):
    with pytest.raises(ValueError):
        human_budget(**{field: invalid})


@pytest.mark.parametrize("changes", [dict(reserve_wh=101.0), dict(reserve_oxygen_l=51.0)])
def test_reserve_cannot_exceed_available_resource(changes):
    with pytest.raises(ValueError, match="reserve exceeds"):
        human_budget(**changes)


def test_reserve_equal_to_available_is_structurally_valid_but_not_a_route_approval():
    budget = human_budget(reserve_wh=100.0, reserve_oxygen_l=50.0)
    assert budget.energy_wh - budget.reserve_wh == 0.0
    assert budget.oxygen_l - budget.reserve_oxygen_l == 0.0


def test_robot_budget_without_oxygen_is_accepted():
    budget = ResourceBudget("rover", 600.0, 100.0, 20.0)
    assert budget.oxygen_l is None
    assert budget.reserve_oxygen_l is None


def test_unknown_actor_kind_is_rejected():
    with pytest.raises(ValueError, match="agent_kind"):
        ResourceBudget("astronaut_typo", 600.0, 100.0, 20.0)


def test_unknown_route_is_not_reported_as_no_path_or_feasible():
    assert RouteStatus.UNKNOWN != RouteStatus.NO_PATH
    assert RouteStatus.UNKNOWN != RouteStatus.FEASIBLE
