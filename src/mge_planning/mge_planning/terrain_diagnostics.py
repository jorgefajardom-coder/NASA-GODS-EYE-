"""Experimental raster-scale diagnostics. Never route admission or certification."""
from dataclasses import dataclass
import math
import numpy as np
from .core import _Geometry, _segment_clearance


@dataclass(frozen=True)
class TerrainEvidence:
    source_kind: str
    native_resolution_m: float
    source_id: str

    def __post_init__(self):
        if self.source_kind not in {'MEASURED', 'ORBITAL_ESTIMATE', 'SYNTHETIC'}:
            raise ValueError('explicit terrain provenance required')
        if (not isinstance(self.source_id,str) or not self.source_id.strip() or
                type(self.native_resolution_m) not in (int,float) or
                not math.isfinite(self.native_resolution_m) or self.native_resolution_m <= 0):
            raise ValueError('positive native resolution and source ID required')


@dataclass(frozen=True)
class DiscontinuityEvidence:
    """Explicit two-sided near-coincident samples, not coarse centre differences."""
    left_x_m: float
    right_x_m: float
    left_z_m: float
    right_z_m: float
    source: TerrainEvidence

    def __post_init__(self):
        values=(self.left_x_m,self.right_x_m,self.left_z_m,self.right_z_m)
        if not all(math.isfinite(v) for v in values) or self.right_x_m <= self.left_x_m:
            raise ValueError('ordered finite samples required')
        if not isinstance(self.source,TerrainEvidence) or self.source.source_kind != 'SYNTHETIC':
            raise ValueError('only declared synthetic two-sided samples are supported; measured discontinuities require a spatial evidence contract')


def diagnose(grid, profile, start_cell, end_cell, evidence, *, discontinuity=None):
    """One directed adjacent-cell diagnostic; local fit requires a known 3x3 patch.

    Transverse grade is relative to heading; plane residual is raster roughness,
    not wheel-scale roughness. Even complete diagnostics never authorize movement.
    Discontinuity samples are along-track offsets from the segment start.
    """
    if grid.frame_id != 'map':
        raise ValueError('map ENU frame required')
    if profile.agent_kind not in {'human','rover'}:
        raise ValueError('ground diagnostics only')
    if not isinstance(evidence,TerrainEvidence):
        raise ValueError('explicit evidence required')
    for cell in (start_cell,end_cell):
        if len(cell)!=2 or any(type(v) is not int for v in cell) or not (0<=cell[0]<grid.rows and 0<=cell[1]<grid.cols):
            raise ValueError('in-bounds integer cells required')
    a,b=grid.point(start_cell),grid.point(end_cell)
    d=np.asarray(b[:2])-a[:2];h=float(np.linalg.norm(d))
    if h==0 or max(abs(x-y) for x,y in zip(start_cell,end_cell))!=1:
        raise ValueError('distinct adjacent cells required')
    geometry=_Geometry(grid,profile)
    reasons=[]
    r,c=start_cell
    patch=[(i,j) for i in range(r-1,r+2) for j in range(c-1,c+2)]
    valid=all(0<=i<grid.rows and 0<=j<grid.cols and geometry.known[i,j] for i,j in patch)
    cross=rough=None
    if valid:
        points=np.array([grid.point(p) for p in patch]);design=np.c_[points[:,:2]-a[:2],np.ones(9)]
        fit=np.linalg.lstsq(design,points[:,2],rcond=None)[0]
        cross=math.degrees(math.atan(float(np.dot(fit[:2],[-d[1]/h,d[0]/h]))))
        rough=float(np.sqrt(np.mean((design@fit-points[:,2])**2)))
    else: reasons.append('INSUFFICIENT_LOCAL_PATCH')
    dz=b[2]-a[2];grade=math.degrees(math.atan2(dz,h)) if math.isfinite(dz) else None
    limit=profile.max_slope_deg if dz>=0 or profile.max_downhill_slope_deg is None else profile.max_downhill_slope_deg
    if grade is not None and abs(grade)>limit: reasons.append('LONGITUDINAL_LIMIT_EXCEEDED')
    clearance=_segment_clearance(geometry,a,b)
    if clearance is None: reasons.append('CLEARANCE_UNKNOWN')
    elif clearance<=0: reasons.append('OBSTACLE_OR_UNKNOWN_FOOTPRINT')
    step=None
    if discontinuity is None:
        reasons.append('INSUFFICIENT_TERRAIN_EVIDENCE')
    else:
        if discontinuity.source != evidence or not 0<=discontinuity.left_x_m<discontinuity.right_x_m<=h:
            raise ValueError('discontinuity must belong to this segment evidence')
        gap=discontinuity.right_x_m-discontinuity.left_x_m
        if gap < evidence.native_resolution_m and not math.isclose(gap,evidence.native_resolution_m,rel_tol=1e-12,abs_tol=0.):
            raise ValueError('samples do not resolve the declared native spacing')
        # A sampled jump indicator, not proof of a mathematically discontinuous surface.
        step=abs(discontinuity.right_z_m-discontinuity.left_z_m)
        if step>profile.max_step_m: reasons.append('RESOLVED_LOCAL_JUMP_EXCEEDS_STEP_LIMIT')
    reject=any(x in reasons for x in ('LONGITUDINAL_LIMIT_EXCEEDED','OBSTACLE_OR_UNKNOWN_FOOTPRINT','RESOLVED_LOCAL_JUMP_EXCEEDS_STEP_LIMIT'))
    return dict(status='REJECT_DIAGNOSTIC' if reject else 'INSUFFICIENT_TERRAIN_EVIDENCE',
                reasons=tuple(reasons),longitudinal_deg=grade,transverse_deg=cross,
                raster_plane_residual_rms_m=rough,delta_z_m=dz if math.isfinite(dz) else None,
                local_jump_m=step,clearance_m=clearance,grid_resolution_m=grid.resolution_m,
                native_resolution_m=evidence.native_resolution_m,source_kind=evidence.source_kind,
                sigma_start_m=None if grid.sigma_m is None else float(grid.sigma_m[start_cell]),
                authorization=False)
