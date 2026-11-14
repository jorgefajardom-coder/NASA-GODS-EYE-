import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import type { TerrainLayer } from '../lib/layers';
import { heightGrid } from '../lib/layers';
import { smoothHeightAt } from '../lib/terrainSmooth';
import { CAMERA_SMOOTHING, type CameraSmoothing } from '../lib/smoothing';
import { rasterizeUnits, unitPixels, type GeologyData } from '../lib/geology';
import * as THREE from 'three';
import { FollowCamera, type Framing } from './FollowCamera';
import { ViewRotator } from './ViewRotator';
import { TerrainGrowth } from './TerrainGrowth';
import { FirstPersonCamera } from './FirstPersonCamera';
import { DroneScan, type ScanRequest } from './DroneScan';
import { SUN_FROM } from '../lib/sun';
import { enuToThree } from '../lib/coords';
import { CutawayBlock } from './CutawayBlock';
import { DETAIL_FAR_M, DETAIL_FAR_POV_M, TerrainView } from './TerrainView';
import { RouteOverlay } from './RouteOverlay';
import { AgentLayer } from './AgentLayer';
import { SiteMarkers } from './SiteMarkers';
import { BaseModel, CLUSTER_OFFSET } from './BaseModel';
import { ContextTerrain } from './ContextTerrain';

interface Props {
  bundle: ReplayBundle;
  view: ReplayView;
  layer: TerrainLayer;
  exaggeration: number;
  showControlPoints: boolean;
  showLabels: boolean;
  /** The intro has ended: the terrain grows in from the centre, once. */
  reveal: boolean;
  playing: boolean;
  replaySpeed: number;
  /** Agent followed by the third-person camera, or null for the free orbital view. */
  followAgentId: string | null;
  /** Camera fixed on the base (ignored while an agent is followed). */
  baseCamera: boolean;
  /** Free pan: left drag grabs the ground and slides the map; right drag orbits. */
  freePan: boolean;
  selectedAgentId: string | null;
  contours: boolean;
  /** Camera easing for the follow view and the orbit controls. */
  cameraSmoothing: CameraSmoothing;
  /** URL of the run's orbital image to drape on the terrain, or null for height colours. */
  imageryUrl: string | null;
  /** Geologic map draped instead of the image (Ground layers tab), with the selected unit. */
  geology: { data: GeologyData; selected: string | null } | null;
  /** Cosmetic close-range ground grain. */
  surfaceDetail: boolean;
  /** Agents at true size at every zoom (no distance enlargement). */
  trueScale: boolean;
  /** Orthomosaic of the context terrain (null = plain shading, e.g. when imagery is off). */
  contextImageUrl: string | null;
  /** Draw the 20 km surroundings (the block walls are then hidden under them). */
  showContext: boolean;
  /** Schematic cut-away strata block around the terrain (Ground layers tab). */
  cutaway: GeologyData | null;
  /** First-person view from the followed agent (ignored when no agent is followed). */
  firstPerson: boolean;
  /** Last drone-camera scan to draw (display only), or null. */
  scan: ScanRequest | null;
}

/** Horizon haze colour: dusty Martian daytime sky, darkened so the panels stay readable. */
const SKY = '#6e5242';

export function MissionScene({ bundle, view, layer, exaggeration, showControlPoints, showLabels, reveal, playing, replaySpeed, followAgentId, baseCamera, freePan, selectedAgentId, contours, cameraSmoothing, imageryUrl, geology, surfaceDetail, cutaway, trueScale, contextImageUrl, showContext, firstPerson, scan }: Props) {
  const geoTexture = useGeologyTexture(geology);
  const meta = bundle.manifest.terrain_meta;
  const mapVersion = view.state?.map_version ?? 1;
  const grid = heightGrid(bundle.rasters, layer, mapVersion);
  // Same interpolation as the mesh, so agents stand on the surface that is drawn.
  const groundHeight = useCallback((x: number, y: number) => smoothHeightAt(meta, grid, x, y), [meta, grid]);
  const followed = view.state?.agents.some((a) => a.agent_id === followAgentId) ? followAgentId : null;
  const smoothing = CAMERA_SMOOTHING[cameraSmoothing];
  const followedKind = view.state?.agents.find((a) => a.agent_id === followed)?.agent_kind ?? null;
  const pov = !!followed && firstPerson && !!followedKind;
  const drone = view.state?.agents.find((a) => a.agent_kind === 'DRONE') ?? null;
  // Opening growth: the terrain appears from the centre of the map outwards, to the farthest
  // corner (of the 20 km surroundings when they are drawn). Labels show once it has finished.
  const [grown, setGrown] = useState(false);
  // Base camera anchor: on the drawn ground at the centre of the habitat cluster.
  const base = bundle.manifest.pois.find((p) => p.kind === 'base');
  const baseAnchor = useMemo(() => {
    if (!base) return null;
    // The habitat cluster is drawn offset from the base point; aim at the habitat.
    const x = base.position.x + CLUSTER_OFFSET.x;
    const y = base.position.y + CLUSTER_OFFSET.y;
    const h = smoothHeightAt(meta, grid, x, y);
    return enuToThree({ x, y, z: h ?? base.position.z }, exaggeration);
  }, [base, meta, grid, exaggeration]);
  const cameraTarget = followed ? `agent-${followed}` : baseCamera && baseAnchor ? BASE_ANCHOR : null;
  const extent = Math.max(meta.rows, meta.cols) * meta.resolution_m;
  const ctx = showContext ? bundle.context : undefined;
  // Far plane and haze reach the edge of the context terrain when there is one.
  const reach = ctx ? Math.max(ctx.frame.rows, ctx.frame.cols) * ctx.frame.resolution_m * 0.75 : extent * 6;
  // Growth centre (Three.js ground plane) and the distance to the farthest drawn corner.
  const growCx = meta.origin_x_m + (meta.cols * meta.resolution_m) / 2;
  const growCz = -(meta.origin_y_m + (meta.rows * meta.resolution_m) / 2);
  const growR = useMemo(() => {
    const corner = (f: { origin_x_m: number; origin_y_m: number; resolution_m: number; rows: number; cols: number }) => {
      const xs = [f.origin_x_m, f.origin_x_m + f.cols * f.resolution_m];
      const ys = [f.origin_y_m, f.origin_y_m + f.rows * f.resolution_m];
      return Math.max(...xs.flatMap((x) => ys.map((y) => Math.hypot(x - growCx, y + growCz)))) * 1.02;
    };
    const block = corner(meta);
    return { block, max: ctx ? Math.max(block, corner(ctx.frame)) : block };
  }, [ctx, meta, growCx, growCz]);
  const hole = useMemo(
    () => ({ origin_x_m: meta.origin_x_m, origin_y_m: meta.origin_y_m, width_m: meta.cols * meta.resolution_m, height_m: meta.rows * meta.resolution_m }),
    [meta],
  );

  return (
    <Canvas
      className={`scene${freePan ? ' scene--grab' : ''}`}
      camera={{ position: [-0.75 * extent, 1.25 * extent, 1.7 * extent], fov: 38, near: 1, far: Math.max(extent * 10, reach * 2) }}
      dpr={[1, 1.75]}
      gl={{ antialias: true, powerPreference: 'high-performance', stencil: true /* the astronaut's projected shadow darkens each pixel once */ }}
      aria-label="3D view of the mission area"
    >
      {/* Dusty daytime haze toward the horizon (display only, not an atmospheric model). */}
      <color attach="background" args={[SKY]} />
      <fog attach="fog" args={[SKY, extent * 2.5, reach]} />
      <hemisphereLight args={['#ffe2c8', '#2a1a12', 0.4]} />
      <directionalLight position={SUN_FROM.clone().multiplyScalar(extent * 1.37).toArray()} intensity={2.6} color="#fff1e0" />
      <TerrainView
        meta={meta}
        rasters={bundle.rasters}
        layer={layer}
        mapVersion={mapVersion}
        verticalExaggeration={exaggeration}
        highlightObserved
        contours={contours}
        zOffsetM={bundle.manifest.local_z_offset_m ?? 0}
        imagery={imageryUrl && bundle.manifest.imagery ? { url: imageryUrl, extent: bundle.manifest.imagery.extent } : null}
        overlay={geoTexture && geology ? { texture: geoTexture, extent: geology.data.frame } : null}
        surfaceDetail={surfaceDetail}
        detailFarM={pov ? DETAIL_FAR_POV_M : DETAIL_FAR_M}
      />
      {ctx && (
        <ContextTerrain
          data={ctx}
          imageUrl={contextImageUrl}
          hole={hole}
          verticalExaggeration={exaggeration}
        />
      )}
      {/* Always a solid block; schematic strata only in the Ground layers tab. Hidden under the surroundings. */}
      {!ctx && <CutawayBlock meta={meta} heights={grid} geology={cutaway} verticalExaggeration={exaggeration} />}
      {/* The route is a map overlay: hidden in the follow view, where it reads as a line painted on the ground. */}
      {/* Route lines and site markers ignore the growth clipping, so they appear once the terrain has grown. */}
      {grown && !followed && <RouteOverlay active={view.activeRoute} previous={view.previousRoutes} verticalExaggeration={exaggeration} />}
      {bundle.manifest.pois.filter((p) => p.kind === 'base').map((p) => (
        <BaseModel key={p.id} site={p.position} verticalExaggeration={exaggeration} groundHeight={groundHeight} />
      ))}
      {grown && (
        <SiteMarkers
          pois={bundle.manifest.pois}
          controlPoints={bundle.manifest.control_points}
          showControlPoints={showControlPoints}
          tasks={view.tasks}
          t={view.t}
          verticalExaggeration={exaggeration}
        />
      )}
      <AgentLayer
        agents={view.state?.agents ?? []}
        t={view.t}
        verticalExaggeration={exaggeration}
        showLabels={showLabels && grown}
        playing={playing}
        replaySpeed={replaySpeed}
        speeds={view.speeds}
        selectedId={selectedAgentId}
        groundHeight={groundHeight}
        trueScale={trueScale}
        hideLabelFor={pov ? followed : null}
      />
      {grown && <DroneScan scan={scan} droneName={drone ? `agent-${drone.agent_id}` : null} groundHeight={groundHeight} verticalExaggeration={exaggeration} />}
      {baseAnchor && <group name={BASE_ANCHOR} position={baseAnchor} />}
      <FollowCamera target={cameraTarget} framing={followed ? undefined : BASE_FRAMING} />
      {/* Mounted after the follow camera: same frame priority, so it places the eye after the follow update. */}
      <FirstPersonCamera target={pov ? `agent-${followed}` : null} kind={pov ? followedKind : null} />
      <OrbitControls
        makeDefault
        enabled={!pov}
        enableDamping
        dampingFactor={smoothing.orbitDamping}
        maxPolarAngle={Math.PI / 2.05}
        minDistance={MIN_ORBIT_DISTANCE_M}
        maxDistance={extent * 2.5}
        zoomToCursor
        // Free pan grabs the ground plane (not the screen plane), so dragging slides the map like a chart.
        screenSpacePanning={!freePan}
        mouseButtons={freePan ? { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE } : { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN }}
        touches={freePan ? { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE } : { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN }}
      />
      <ViewRotator />
      {!grown && <TerrainGrowth start={reveal} centerX={growCx} centerZ={growCz} maxRadius={growR.max} blockRadius={growR.block} onDone={() => setGrown(true)} />}
      {/* Mounted after the controls and the follow camera so it corrects their result in the same frame. */}
      <CameraGroundClamp meta={meta} groundHeight={groundHeight} verticalExaggeration={exaggeration} />
    </Canvas>
  );
}

/** Scene name of the base camera anchor, and how that camera frames the habitat. */
const BASE_ANCHOR = 'camera-anchor-base';
const BASE_FRAMING: Framing = { distanceM: 32, heightM: 14, lookAtM: 3 };

/** Least height of the camera above the drawn ground (m), and the radius sampled around it (m). */
const CAMERA_CLEARANCE_M = 0.15;
const CAMERA_CLEARANCE_RADIUS_M = 0.3;
/** Closest the free camera may orbit to its target (m): close enough to look at a boot. */
export const MIN_ORBIT_DISTANCE_M = 0.35;
/** Near clipping plane as a share of the distance to the orbit target, and its bounds (m). */
const NEAR_SHARE = 0.04;
const NEAR_MIN_M = 0.01;
const NEAR_MAX_M = 1;

/**
 * Keeps the camera above the drawn terrain: orbiting low, zooming to the cursor, panning or the
 * follow view can otherwise put it under the surface. Also adapts the near plane to the zoom. The ground is sampled at the camera and
 * around it (the near plane reaches 1 m ahead); beyond the terrain edge the edge height is used.
 * Display only.
 */
function CameraGroundClamp({
  meta,
  groundHeight,
  verticalExaggeration,
}: {
  meta: { origin_x_m: number; origin_y_m: number; resolution_m: number; rows: number; cols: number };
  groundHeight: (x: number, y: number) => number | null;
  verticalExaggeration: number;
}) {
  useFrame(({ camera, controls }) => {
    const half = meta.resolution_m / 2;
    const clampX = (x: number) => THREE.MathUtils.clamp(x, meta.origin_x_m + half, meta.origin_x_m + meta.cols * meta.resolution_m - half);
    const clampY = (y: number) => THREE.MathUtils.clamp(y, meta.origin_y_m + half, meta.origin_y_m + meta.rows * meta.resolution_m - half);
    // Three.js -> ENU: east = x, north = -z.
    const e = camera.position.x;
    const n = -camera.position.z;
    const r = CAMERA_CLEARANCE_RADIUS_M;
    let top = -Infinity;
    for (const [dx, dy] of [[0, 0], [r, 0], [-r, 0], [0, r], [0, -r]]) {
      const h = groundHeight(clampX(e + dx), clampY(n + dy));
      if (h != null) top = Math.max(top, h);
    }
    if (top === -Infinity) return;
    const floor = top * verticalExaggeration + CAMERA_CLEARANCE_M;
    if (camera.position.y < floor) camera.position.y = floor;

    // Near plane follows the zoom: small up close (no clipping of the agent or the ground under
    // it), back to 1 m when far so the distant terrain keeps its depth precision.
    const target = (controls as unknown as { target?: THREE.Vector3 } | null)?.target;
    const d = target ? camera.position.distanceTo(target) : 25;
    const near = THREE.MathUtils.clamp(d * NEAR_SHARE, NEAR_MIN_M, NEAR_MAX_M);
    const cam = camera as THREE.PerspectiveCamera;
    if (Math.abs(cam.near - near) > near * 0.1) {
      cam.near = near;
      cam.updateProjectionMatrix();
    }
  }, -1); // after the orbit controls (mounted after them), before scaling and labels
  return null;
}

/** Grid of the draped geologic map (2.5 m cells over the 2 km crop; boundaries are only ~100-200 m accurate). */
const GEOLOGY_TEXTURE_PX = 800;

/** Rasterized geologic units as a texture; rebuilt when the selected unit changes. */
function useGeologyTexture(geology: { data: GeologyData; selected: string | null } | null): THREE.DataTexture | null {
  const data = geology?.data ?? null;
  const grid = useMemo(() => (data ? rasterizeUnits(data, GEOLOGY_TEXTURE_PX) : null), [data]);
  const texture = useMemo(() => {
    if (!data || !grid) return null;
    const t = new THREE.DataTexture(unitPixels(data, grid, geology?.selected ?? null), GEOLOGY_TEXTURE_PX, GEOLOGY_TEXTURE_PX, THREE.RGBAFormat);
    t.colorSpace = THREE.SRGBColorSpace;
    t.magFilter = THREE.NearestFilter;
    t.needsUpdate = true;
    return t;
  }, [data, grid, geology?.selected]);
  useEffect(() => () => texture?.dispose(), [texture]);
  return texture;
}
