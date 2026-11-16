"""Cosmetic drone rotor animation shared by the Gazebo world generator and gz_mirror.

Pure Python on purpose: gz_mirror imports this module at node start-up, so it must not pull
in numpy, scipy or the world generator (mge_sim.gz_world). Rates and the airborne rule copy
the web viewer (web/src/components/VehicleModel.tsx); this is display only, never telemetry.
"""
import math

# About 525 rpm drawn, spin-up ~4 s, spin-down ~5 s (VehicleModel.tsx).
ROTOR_RAD_S = 55.0
ROTOR_SPINUP_PER_S = 0.25
ROTOR_SPINDOWN_PER_S = 0.2
# Drawn height above ground (m) above which the drone counts as airborne (VehicleModel AIRBORNE_M).
AIRBORNE_M = 0.3


def rotor_command(share, mode, dt, airborne=False):
    """Next rotor speed share (0..1), like the web's `target = rotorsOn || airborne`.

    The rotors head to full speed while the drone is not IDLE, and also while it is drawn above
    AIRBORNE_M even if its mode is already IDLE (still climbing or settling); they ramp at the
    web's spin-up and spin-down rates."""
    target = 0.0 if mode == 'IDLE' and not airborne else 1.0
    rate = ROTOR_SPINUP_PER_S if target > share else ROTOR_SPINDOWN_PER_S
    step = rate * max(0.0, dt)
    return min(target, share + step) if target > share else max(target, share - step)


def should_publish(previous, share):
    """A still rotor that stays still needs no new velocity command."""
    return previous > 0.0 or share > 0.0


def ground_at(meta, x, y):
    """Gazebo ground height (m) under (x, y), bilinear between cell centres of world.json's
    `ground_z_m` (rows from origin_y upwards, columns from origin_x), clamped to the grid edge.
    None when the world file predates that field or the value is not finite."""
    rows = meta.get('ground_z_m')
    if not rows:
        return None
    res = meta['resolution_m']
    fi = min(max((y - meta['origin_y_m']) / res - 0.5, 0.0), len(rows) - 1.0)
    fj = min(max((x - meta['origin_x_m']) / res - 0.5, 0.0), len(rows[0]) - 1.0)
    i0, j0 = int(fi), int(fj)
    i1, j1 = min(i0 + 1, len(rows) - 1), min(j0 + 1, len(rows[0]) - 1)
    ti, tj = fi - i0, fj - j0
    z = ((rows[i0][j0] * (1 - tj) + rows[i0][j1] * tj) * (1 - ti)
         + (rows[i1][j0] * (1 - tj) + rows[i1][j1] * tj) * ti)
    return z if math.isfinite(z) else None


def is_airborne(meta, gz_xyz):
    """True when a mirrored pose (Gazebo frame) is drawn more than AIRBORNE_M above the ground."""
    ground = ground_at(meta, gz_xyz[0], gz_xyz[1])
    return ground is not None and gz_xyz[2] - ground > AIRBORNE_M
