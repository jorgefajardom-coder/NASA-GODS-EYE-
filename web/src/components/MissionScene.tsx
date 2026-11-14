import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useCallback, useEffect, useMemo } from 'react';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import type { TerrainLayer } from '../lib/layers';
import { heightGrid } from '../lib/layers';
import { smoothHeightAt } from '../lib/terrainSmooth';
import { CAMERA_SMOOTHING, type CameraSmoothing } from '../lib/smoothing';
import { rasterizeUnits, unitPixels, type GeologyData } from '../lib/geology';
import * as THREE from 'three';
import { FollowCamera } from './FollowCamera';
import { TerrainView } from './TerrainView';
import { RouteOverlay } from './RouteOverlay';
import { AgentLayer } from './AgentLayer';
import { SiteMarkers } from './SiteMarkers';

interface Props {
  bundle: ReplayBundle;
  view: ReplayView;
  layer: TerrainLayer;
  exaggeration: number;
  showControlPoints: boolean;
  showLabels: boolean;
  playing: boolean;
  replaySpeed: number;
  /** Agent followed by the third-person camera, or null for the free orbital view. */
  followAgentId: string | null;
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
}

export function MissionScene({ bundle, view, layer, exaggeration, showControlPoints, showLabels, playing, replaySpeed, followAgentId, selectedAgentId, contours, cameraSmoothing, imageryUrl, geology, surfaceDetail }: Props) {
  const geoTexture = useGeologyTexture(geology);
  const meta = bundle.manifest.terrain_meta;
  const mapVersion = view.state?.map_version ?? 1;
  const grid = heightGrid(bundle.rasters, layer, mapVersion);
  // Same interpolation as the mesh, so agents stand on the surface that is drawn.
  const groundHeight = useCallback((x: number, y: number) => smoothHeightAt(meta, grid, x, y), [meta, grid]);
  const followed = view.state?.agents.some((a) => a.agent_id === followAgentId) ? followAgentId : null;
  const smoothing = CAMERA_SMOOTHING[cameraSmoothing];
  const extent = Math.max(meta.rows, meta.cols) * meta.resolution_m;

  return (
    <Canvas
      className="scene"
      camera={{ position: [-0.75 * extent, 1.25 * extent, 1.7 * extent], fov: 38, near: 1, far: extent * 10 }}
      dpr={[1, 1.75]}
      gl={{ antialias: true, powerPreference: 'high-performance' }}
      aria-label="3D view of the mission area"
    >
      <color attach="background" args={['#090D11']} />
      <fog attach="fog" args={['#090D11', extent * 2.5, extent * 6]} />
      <hemisphereLight args={['#ffe2c8', '#2a1a12', 0.4]} />
      <directionalLight position={[-extent * 1.2, extent * 0.55, extent * 0.35]} intensity={2.6} color="#fff1e0" />
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
      />
      <RouteOverlay active={view.activeRoute} previous={view.previousRoutes} verticalExaggeration={exaggeration} />
      <SiteMarkers
        pois={bundle.manifest.pois}
        controlPoints={bundle.manifest.control_points}
        showControlPoints={showControlPoints}
        tasks={view.tasks}
        t={view.t}
        verticalExaggeration={exaggeration}
      />
      <AgentLayer
        agents={view.state?.agents ?? []}
        verticalExaggeration={exaggeration}
        showLabels={showLabels}
        playing={playing}
        replaySpeed={replaySpeed}
        speeds={view.speeds}
        selectedId={selectedAgentId}
        groundHeight={groundHeight}
      />
      <FollowCamera agentId={followed} smoothingS={smoothing.followTauS} />
      <OrbitControls makeDefault enableDamping dampingFactor={smoothing.orbitDamping} maxPolarAngle={Math.PI / 2.05} minDistance={30} maxDistance={extent * 2.5} />
    </Canvas>
  );
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
