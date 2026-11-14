import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useCallback } from 'react';
import type { ReplayBundle } from '../types/replay';
import type { ReplayView } from '../lib/replay';
import type { TerrainLayer } from '../lib/layers';
import { heightGrid } from '../lib/layers';
import { enuToThree, sampleHeight, yawFromQuaternion } from '../lib/coords';
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
}

export function MissionScene({ bundle, view, layer, exaggeration, showControlPoints, showLabels, playing, replaySpeed, followAgentId, selectedAgentId }: Props) {
  const meta = bundle.manifest.terrain_meta;
  const mapVersion = view.state?.map_version ?? 1;
  const grid = heightGrid(bundle.rasters, layer, mapVersion);
  const groundHeight = useCallback((x: number, y: number) => sampleHeight(meta, grid, x, y), [meta, grid]);
  const followed = view.state?.agents.find((a) => a.agent_id === followAgentId) ?? null;
  const extent = Math.max(meta.rows, meta.cols) * meta.resolution_m;

  return (
    <Canvas
      className="scene"
      camera={{ position: [-0.55 * extent, 0.95 * extent, 1.25 * extent], fov: 40, near: 1, far: extent * 10 }}
      dpr={[1, 2]}
      aria-label="3D view of the mission area"
    >
      <color attach="background" args={['#090D11']} />
      <fog attach="fog" args={['#090D11', extent * 2.5, extent * 6]} />
      <hemisphereLight args={['#ffe2c8', '#2a1a12', 0.55]} />
      <directionalLight position={[-extent, extent * 1.2, extent * 0.4]} intensity={1.6} color="#fff1e0" />
      <TerrainView
        meta={meta}
        rasters={bundle.rasters}
        layer={layer}
        mapVersion={mapVersion}
        verticalExaggeration={exaggeration}
        highlightObserved
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
      <FollowCamera
        target={followed ? enuToThree(followed.pose.position, exaggeration) : null}
        yaw={followed ? yawFromQuaternion(followed.pose.orientation) : 0}
      />
      <OrbitControls makeDefault enableDamping maxPolarAngle={Math.PI / 2.05} minDistance={30} maxDistance={extent * 2.5} />
    </Canvas>
  );
}
