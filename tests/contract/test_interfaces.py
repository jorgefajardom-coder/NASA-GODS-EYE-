"""Contract test for ICD-ROS2-V1: the eight definitions exist and expose the
fields and enum values other modules rely on. Run after sourcing the workspace."""
import pytest
from rosidl_runtime_py.utilities import get_message, get_service

MSG_FIELDS = {
    'TerrainMeta': [
        'header', 'run_id', 'dataset_id', 'map_version', 'origin_x_m', 'origin_y_m',
        'resolution_m', 'rows', 'cols', 'crs', 'vertical_datum', 'nodata_value',
        'sources', 'checksum_sha256'],
    'TerrainObservation': [
        'header', 'observation_id', 'run_id', 'agent_id', 'base_map_version',
        'source_kind', 'cell_indices', 'elevation_m', 'sigma_m', 'obstacle'],
    'AgentState': [
        'header', 'run_id', 'agent_id', 'agent_kind', 'pose', 'velocity', 'mode',
        'time_remaining_s', 'energy_remaining_wh', 'oxygen_remaining_l', 'confidence'],
    'RouteDecision': [
        'header', 'run_id', 'request_id', 'route_id', 'map_version_used', 'status',
        'reason_code', 'outbound_path', 'return_path', 'travel_time_s',
        'energy_est_wh', 'oxygen_est_l', 'min_clearance_m', 'reserve_wh',
        'reserve_oxygen_l'],
    'MissionEvent': [
        'header', 'event_id', 'seq', 'run_id', 'causality_id', 'event_type', 'task_id',
        'agent_id', 'map_version', 'route_id', 'previous_state', 'new_state',
        'reason_code'],
    'MissionState': [
        'header', 'run_id', 'mission_state', 'primary_goal', 'active_task_id',
        'agents', 'map_version', 'route_id', 'active_route'],
}


@pytest.mark.parametrize('name', sorted(MSG_FIELDS))
def test_message_fields(name):
    fields = get_message(f'mge_interfaces/msg/{name}').get_fields_and_field_types()
    missing = [f for f in MSG_FIELDS[name] if f not in fields]
    assert not missing, f'{name} lacks {missing}'


def test_route_status_enum():
    msg = get_message('mge_interfaces/msg/RouteDecision')
    for s in ['FEASIBLE', 'UNKNOWN', 'NO_PATH', 'INSUFFICIENT_BUDGET', 'STALE_MAP', 'ERROR']:
        assert getattr(msg, f'STATUS_{s}') == s


def test_mission_state_enum():
    msg = get_message('mge_interfaces/msg/MissionState')
    for s in ['IDLE', 'PLANNING', 'READY', 'ACTIVE', 'REPLAN', 'RETURNING', 'COMPLETE',
              'BLOCKED', 'ABORTED']:
        assert getattr(msg, f'STATE_{s}') == s


def test_observation_is_simulated():
    assert get_message('mge_interfaces/msg/TerrainObservation').SOURCE_SIMULATED == 'SIMULATED'


def test_services():
    plan = get_service('mge_interfaces/srv/PlanRoute')
    req = plan.Request.get_fields_and_field_types()
    for f in ['run_id', 'request_id', 'agent_id', 'start', 'goal', 'mode', 'map_version',
              'time_budget_s', 'energy_budget_wh', 'oxygen_budget_l', 'reserve_wh']:
        assert f in req
    assert plan.Response.get_fields_and_field_types()['decision'] == 'mge_interfaces/RouteDecision'

    goal = get_service('mge_interfaces/srv/SetMissionGoal')
    assert 'request_id' in goal.Request.get_fields_and_field_types()
    res = goal.Response.get_fields_and_field_types()
    for f in ['accepted', 'run_id', 'reason_code']:
        assert f in res
