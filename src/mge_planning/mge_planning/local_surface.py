"""Python-only synthetic local-surface experiment; no operational admission API."""
from dataclasses import dataclass, replace
import hashlib
import math
import numpy as np
from .core import plan_route, RouteResult, RouteStatus, TerrainGrid


@dataclass(frozen=True)
class SurfaceLimits:
    max_native_spacing_m: float
    max_any_heading_cross_slope_deg: float
    max_plane_residual_m: float

    def __post_init__(self):
        for value in (self.max_native_spacing_m,self.max_any_heading_cross_slope_deg,self.max_plane_residual_m):
            if type(value) not in (int,float) or not math.isfinite(value) or value<=0:
                raise ValueError('explicit positive experimental limits required')
        if self.max_any_heading_cross_slope_deg>=90:
            raise ValueError('cross slope must be below 90 degrees')


@dataclass(frozen=True)
class LocalSurface:
    grid: object
    source_id: str
    frame_id: str
    vertical_datum: str
    native_spacing_m: float
    surface_model: str = 'SYNTHETIC_CELL_SURFACE'

    def __post_init__(self):
        if not isinstance(self.grid,TerrainGrid):
            raise ValueError('immutable TerrainGrid required')
        if not self.source_id or self.frame_id!='map' or not self.vertical_datum:
            raise ValueError('source, map ENU frame and explicit vertical datum required')
        if self.surface_model!='SYNTHETIC_CELL_SURFACE':
            raise ValueError('only explicitly synthetic cell-surface fixtures supported')
        if type(self.native_spacing_m) not in (int,float) or not math.isfinite(self.native_spacing_m) or self.native_spacing_m<=0:
            raise ValueError('native spacing required')

    @property
    def fingerprint(self):
        g=self.grid
        digest=hashlib.sha256(repr((self.source_id,self.frame_id,self.vertical_datum,
            self.native_spacing_m,self.surface_model,g.run_id,g.map_version,g.origin_x_m,
            g.origin_y_m,g.resolution_m,g.elevation_m.shape)).encode())
        for a in (g.elevation_m,g.sigma_m,g.traversability):
            digest.update(b'absent' if a is None else a.tobytes())
        return digest.hexdigest()


@dataclass(frozen=True)
class MobilityEvaluation:
    candidate: RouteResult
    evidence_sha256: str
    source_map_version: int
    map_sha256: str
    policy_sha256: str
    evaluation_grid: object = None
    authorization: bool = False

    def is_current(self, surface, terrain, limits, profile):
        return (_map_hash(terrain)==self.map_sha256 and _policy_hash(limits,profile)==self.policy_sha256
                and surface.fingerprint==self.evidence_sha256 and terrain.run_id==self.candidate.run_id
                and terrain.map_version==self.source_map_version==surface.grid.map_version)


def _map_hash(g):
    h=hashlib.sha256(repr((g.run_id,g.map_version,g.origin_x_m,g.origin_y_m,g.resolution_m,g.elevation_m.shape)).encode())
    for a in (g.elevation_m,g.sigma_m,g.traversability):h.update(b'absent' if a is None else a.tobytes())
    return h.hexdigest()

def _policy_hash(limits,profile):
    return hashlib.sha256(repr((limits,profile)).encode()).hexdigest()

def evaluate_surface(*, terrain, request, profile, surface, limits, vertical_datum,
                     scientific_context=None, allow_continuous_start=False, search_limits=None):
    """Reuse unmodified A* on a fully covered synthetic fine raster.

    No step exemption: every fine edge/connector obeys the original 0.2m gate.
    Missing evidence is UNKNOWN. Metadata incompatibility is ERROR. Conservative
    cross-grade checks every possible heading; this can reject longitudinally
    acceptable ramps. No runtime producer or policy consumes these candidates.
    """
    g=surface.grid
    def fail(status,reason):
        return MobilityEvaluation(RouteResult(status,reason,'Experimental synthetic surface only',
            request.run_id,request.request_id,request.agent_id,str(getattr(request.mode,'value',request.mode)),
            terrain.map_version),surface.fingerprint,terrain.map_version,_map_hash(terrain),_policy_hash(limits,profile))
    if profile.agent_kind not in {'human','rover'}:
        return fail(RouteStatus.ERROR,'GROUND_AGENTS_ONLY')
    if (g.run_id!=terrain.run_id or request.run_id!=terrain.run_id or
            g.map_version!=terrain.map_version or request.map_version!=terrain.map_version):
        return fail(RouteStatus.STALE_MAP,'SURFACE_MAP_MISMATCH')
    if vertical_datum!=surface.vertical_datum:
        return fail(RouteStatus.ERROR,'SURFACE_DATUM_MISMATCH')
    ratio=terrain.resolution_m/g.resolution_m
    n=round(ratio)
    if (n<3 or n%2!=1 or abs(ratio-n)>1e-9 or g.rows!=terrain.rows*n or g.cols!=terrain.cols*n
            or (g.origin_x_m,g.origin_y_m)!=(terrain.origin_x_m,terrain.origin_y_m)):
        return fail(RouteStatus.ERROR,'SURFACE_GEOMETRY_MISMATCH')
    if surface.native_spacing_m>limits.max_native_spacing_m or g.resolution_m<surface.native_spacing_m:
        return fail(RouteStatus.UNKNOWN,'INSUFFICIENT_NATIVE_SUPPORT')
    if (g.sigma_m is None or terrain.sigma_m is None or
            not np.all(np.isfinite(g.elevation_m)) or not np.all(np.isfinite(g.sigma_m)) or
            np.any(g.sigma_m<0) or np.any(g.traversability<0) or
            not np.all(np.isfinite(terrain.elevation_m)) or not np.all(np.isfinite(terrain.sigma_m)) or np.any(terrain.sigma_m<0)):
        return fail(RouteStatus.UNKNOWN,'INSUFFICIENT_TERRAIN_EVIDENCE')
    parent_sigma=np.repeat(np.repeat(terrain.sigma_m,n,0),n,1)
    parent_mask=np.repeat(np.repeat(terrain.traversability,n,0),n,1)
    if np.any(g.sigma_m<parent_sigma) or np.any((parent_mask!=0)&(g.traversability==0)):
        return fail(RouteStatus.ERROR,'SURFACE_EVIDENCE_DOWNGRADE')
    if profile.max_sigma_m is not None and np.any(g.sigma_m>profile.max_sigma_m):
        return fail(RouteStatus.UNKNOWN,'SURFACE_UNCERTAINTY_LIMIT')
    centres=g.elevation_m[n//2::n,n//2::n]
    if not np.allclose(centres,terrain.elevation_m,rtol=0,atol=1e-6):
        return fail(RouteStatus.ERROR,'SURFACE_HEIGHT_MISMATCH')
    dy,dx=np.gradient(g.elevation_m,g.resolution_m)
    grade=np.degrees(np.arctan(np.hypot(dx,dy)))
    # Residual from opposite-neighbour linear interpolation at raster scale.
    residual=np.zeros_like(g.elevation_m)
    residual[1:-1,1:-1]=np.maximum(abs(g.elevation_m[1:-1,1:-1]-(g.elevation_m[:-2,1:-1]+g.elevation_m[2:,1:-1])/2),
        abs(g.elevation_m[1:-1,1:-1]-(g.elevation_m[1:-1,:-2]+g.elevation_m[1:-1,2:])/2))
    mask=g.traversability.copy()
    mask[(grade>limits.max_any_heading_cross_slope_deg)|(residual>limits.max_plane_residual_m)]=100
    constrained=replace(g,traversability=mask)
    options=dict(terrain=constrained,request=request,profile=profile,
                 scientific_context=scientific_context,allow_continuous_start=allow_continuous_start)
    if search_limits is not None: options['limits']=search_limits
    result=plan_route(**options)
    if result.route_id:
        identity=hashlib.sha256(repr((result.route_id,surface.fingerprint,_map_hash(terrain),_policy_hash(limits,profile))).encode()).hexdigest()
        result=replace(result,route_id='experimental-surface-'+identity)
    return MobilityEvaluation(result,surface.fingerprint,terrain.map_version,_map_hash(terrain),_policy_hash(limits,profile),constrained)
