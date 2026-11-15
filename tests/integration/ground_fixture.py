"""Test-only initialization of a declared SIMULATED ground scene, never telemetry.

The scene contains explicit simulated observations copied from the public prior.
It is separate from the ROS belief (which starts unobserved). No hidden reference,
datum conversion, runtime pose projection or production provider change occurs.
"""
from copy import deepcopy
from math import isfinite

from mge_planning.core import TerrainGrid


def simulated_ground_point(surface, xy):
    """Create a NEW synthetic ground position from known scene data and XY only.

    This API cannot reinterpret an existing 3-D pose or treat explicit z=0 as
    missing. The planner remains responsible for footprint/transition safety.
    """
    if len(xy) != 2:
        raise ValueError("Initialization requires XY, never an existing physical XYZ pose")
    cell = surface.cell(xy)
    if surface.traversability[cell] != 0:
        raise ValueError("No known admissible simulated surface at this position")
    z = surface.point(cell)[2]
    if not isfinite(z):
        raise ValueError("No finite simulated surface elevation")
    if surface.sigma_m is not None:
        sigma = surface.sigma_m[cell]
        if not isfinite(sigma) or sigma < 0:
            raise ValueError("Unknown simulated surface uncertainty")
    return (*xy, z)


def initialize_ground_agents(template, surface):
    """Fill absent initial Z for this NEW scene, including its PARKED drone.

    Explicit XYZ remains unchanged; this helper never handles live telemetry.
    """
    result = deepcopy(template)
    for agent in result['agents']:
        if agent['kind'] in ('HUMAN', 'ROVER', 'DRONE') and 'z_m' not in agent:
            agent['z_m'] = simulated_ground_point(surface, (agent['x_m'], agent['y_m']))[2]
    return result


def observed_public_scene(run_id, indices):
    """Prepare this fixture's explicit prior-repeating SIMULATED observations.

    This is a test scene definition, not permission to use an unobserved ROS
    belief as a known surface. Only the supplied observation footprint becomes
    known here. The actual mapping node still starts at unknown map version 1.
    """
    from mge_data.core import default_manifest_path, load_public_terrain
    from mge_mapping.core import BeliefMap, SimulatedObservation, fuse_observation

    tile = load_public_terrain(default_manifest_path())
    initial = BeliefMap.from_terrain_tile(tile, run_id=run_id)
    indices = tuple(indices)
    observations = SimulatedObservation(
        'fixture-scene-only', 'drone_1', run_id, initial.map_version, 0., indices,
        tuple(float(tile.prior.flat[i]) for i in indices),
        sigmas_m=(.25,)*len(indices), obstacles=(0,)*len(indices))
    known = fuse_observation(initial, observations)
    surface = TerrainGrid(run_id, known.map_version, known.belief,
                          known.traversability_grid(), known.resolution_m,
                          known.origin_x_m, known.origin_y_m, known.frame_id, known.sigma)
    return surface, tile.metadata.vertical_datum
