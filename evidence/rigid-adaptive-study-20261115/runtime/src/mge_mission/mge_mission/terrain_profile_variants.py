"""Local orbital-prior projection experiments; never approve physical passage."""
from copy import deepcopy
import math


def orbital_grade_projection(projection, resolution_m):
    """Make the grid height-difference bound consistent with existing grades.

    The pinned planner applies max_step_m to endpoint elevation difference,
    not obstacle height above local grade. Its separate directed slope check
    remains responsible for the actual edge length/direction. This variant
    prevents a 20 cm obstacle assumption from imposing an unintended 2.86 deg
    axial grade limit on a 4 m grid. It supplies no micro-obstacle knowledge.
    """
    if isinstance(resolution_m, bool) or not isinstance(resolution_m, (float, int)) or not math.isfinite(resolution_m) or resolution_m <= 0:
        raise ValueError("resolution_m must be finite and positive")
    if projection.get("status") != "illustrative":
        raise ValueError("This local variant requires an illustrative projection")
    result = deepcopy(projection)
    receipts = {}
    for agent, values in result["profiles"].items():
        if values["agent_kind"] not in {"human", "rover"}:
            continue
        up = values["max_slope_deg"]
        down = values.get("max_downhill_slope_deg")
        down = up if down is None else down
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v < 90 for v in (up, down)):
            raise ValueError("Finite ground grade limits below 90 degrees are required")
        bound = math.nextafter(math.sqrt(2) * resolution_m * math.tan(math.radians(max(up, down))), math.inf)
        receipts[agent] = {"previous_endpoint_height_limit_m": values["max_step_m"],
                           "derived_endpoint_height_limit_m": bound,
                           "uphill_grade_deg": up, "downhill_grade_deg": down,
                           "physical_obstacle_height_limit_verified": False}
        values["max_step_m"] = bound
    result["research_terrain_constraint"] = {
        "policy_id": "LOCAL-CTX-GRID-GRADE-01", "status": "LOCAL_EXPERIMENT_ONLY",
        "resolution_m": resolution_m, "longest_neighbour_horizontal_m": math.sqrt(2) * resolution_m,
        "derivation": "max_step_m = sqrt(2)*resolution_m*tan(max(existing_uphill_grade, existing_downhill_grade)); directed slope checks unchanged",
        "receipts": receipts, "physical_micro_obstacles": "UNRESOLVED_WITHOUT_SUITABLE_LOCAL_EVIDENCE",
        "changes_to_obstacles_nodata_uncertainty_or_footprints": False,
        "scientific_profile_approval": False, "cost_agreement": False, "execution_authorization": False,
    }
    return result
