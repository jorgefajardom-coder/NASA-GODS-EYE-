import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReplayBundle } from './types/replay';
import { assetUrl, loadEvaluatorReference, loadReplay } from './data/replayAdapter';
import { REFERENCE_SOURCES } from './data/referenceSources';
import { CAMERA_SMOOTHING, type CameraSmoothing } from './lib/smoothing';
import { viewAt } from './lib/replay';
import type { TerrainLayer } from './lib/layers';
import {
  agentStats,
  AGENT_NAME,
  detailsFor,
  initialBudgets,
  managementGroups,
  missionAlert,
  resolveSelection,
  type Selection,
} from './lib/management';
import { MissionScene } from './components/MissionScene';
import { ManagementList } from './components/ManagementList';
import { DetailsPanel } from './components/DetailsPanel';
import { HUD_MAP_PX, Vitals } from './components/Vitals';
import { EventInspector } from './components/EventInspector';
import { GeologyDetails, GeologyList } from './components/GeologyPanel';
import { AtmosDetails, AtmosList } from './components/AtmosPanel';
import { Minimap } from './components/Minimap';
import { Timeline } from './components/Timeline';
import { LayerStrip, ViewOptions } from './components/LayerPanel';
import { AlertBanner, ModeTabs, StatusBlock, TitleBlock, type UiMode } from './components/Frame';

const params = new URLSearchParams(window.location.search);
/** Evaluator view shows the hidden reference DEM. Off by default; enable with ?evaluator=1. */
const EVALUATOR = params.get('evaluator') === '1';
const RUN_ID = params.get('run') ?? 'demo';
const RUN_DIR = `replay/${RUN_ID}`;

type Load = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; bundle: ReplayBundle };

export function App() {
  const [load, setLoad] = useState<Load>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    loadReplay(RUN_DIR)
      .then(async (bundle) => {
        if (EVALUATOR) {
          const reference = await loadEvaluatorReference(bundle.manifest.run_id, bundle.rasters.rows, bundle.rasters.cols);
          if (reference) bundle = { ...bundle, rasters: { ...bundle.rasters, reference } };
        }
        return bundle;
      })
      .then((bundle) => !cancelled && setLoad({ status: 'ready', bundle }))
      .catch((err: unknown) => !cancelled && setLoad({ status: 'error', message: err instanceof Error ? err.message : String(err) }));
    return () => {
      cancelled = true;
    };
  }, []);

  if (load.status === 'loading') return <Splash title="Loading saved run…" detail={`Reading ${RUN_DIR}/manifest.json`} />;
  if (load.status === 'error') return <Splash title="Could not open the saved run" detail={load.message} error />;
  return <Viewer bundle={load.bundle} />;
}

function Splash({ title, detail, error }: { title: string; detail: string; error?: boolean }) {
  return (
    <main className={`splash ${error ? 'splash--error' : ''}`} role={error ? 'alert' : 'status'}>
      <h1>Mars Gods Eye</h1>
      <p>{title}</p>
      <p className="muted small">{detail}</p>
    </main>
  );
}

function Viewer({ bundle }: { bundle: ReplayBundle }) {
  const m = bundle.manifest;
  const duration = m.duration_s;
  const [t, setT] = useState(0);
  const [playing, setPlaying] = useState(false);
  // Short recorded runs (seconds long) start at real time; the long demo starts at 20x.
  const [speed, setSpeed] = useState(duration < 120 ? 1 : 20);
  const [layer, setLayer] = useState<TerrainLayer>('belief');
  const [exaggeration, setExaggeration] = useState(m.vertical_exaggeration_default);
  const [showControlPoints, setShowControlPoints] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const [follow, setFollow] = useState(false);
  // The follow view plays at 1x so the walk is drawn at its natural pace (legs synced to the
  // ground); leaving it restores the speed chosen before. The speed can still be changed while following.
  const speedBeforeFollow = useRef<number | null>(null);
  useEffect(() => {
    if (follow) {
      setSpeed((prev) => {
        speedBeforeFollow.current = prev;
        return 1;
      });
    } else if (speedBeforeFollow.current != null) {
      const restore = speedBeforeFollow.current;
      speedBeforeFollow.current = null;
      setSpeed(restore);
    }
  }, [follow]);
  const [contours, setContours] = useState(true);
  const [showImagery, setShowImagery] = useState(true);
  const [surfaceDetail, setSurfaceDetail] = useState(true);
  const [trueScale, setTrueScale] = useState(true);
  const [showContext, setShowContext] = useState(false);
  const imageryUrl = m.imagery && showImagery ? assetUrl(`${RUN_DIR}/${m.imagery.file}`) : null;
  const contextImageUrl = m.context?.image && showImagery ? assetUrl(`${RUN_DIR}/${m.context.image}`) : null;
  const [cameraSmoothing, setCameraSmoothingState] = useState<CameraSmoothing>(() => {
    try {
      const v = localStorage.getItem('mge.cameraSmoothing');
      return v && v in CAMERA_SMOOTHING ? (v as CameraSmoothing) : 'soft';
    } catch {
      return 'soft';
    }
  });
  const setCameraSmoothing = useCallback((v: CameraSmoothing) => {
    setCameraSmoothingState(v);
    try {
      localStorage.setItem('mge.cameraSmoothing', v);
    } catch {
      /* per-viewer convenience only */
    }
  }, []);
  const [mode, setMode] = useState<UiMode>('exploration');
  const [geoUnit, setGeoUnit] = useState<string | null>(null);
  const [showGeoMap, setShowGeoMap] = useState(true);
  const [showCut, setShowCut] = useState(true);
  const [selection, setSelection] = useState<Selection>({ kind: 'agent', id: '' });

  const view = useMemo(() => viewAt(bundle, t), [bundle, t]);
  const budgets = useMemo(() => initialBudgets(bundle), [bundle]);
  const groups = useMemo(() => managementGroups(view), [view]);
  const sel = resolveSelection(selection, view);
  const details = useMemo(() => detailsFor({ kind: sel.kind, id: sel.id }, view, bundle, budgets), [sel.kind, sel.id, view, bundle, budgets]);

  // The telemetry block follows the selected agent; for a task or route it shows the primary agent.
  const primaryId = view.state?.primary_agent_id ?? '';
  const agentId = sel.kind === 'agent' ? sel.id : primaryId;
  const agent = view.state?.agents.find((a) => a.agent_id === agentId) ?? null;
  const alert = useMemo(() => missionAlert(view), [view]);

  // Replay clock: advances simulated time by wall time x speed.
  const last = useRef<number | null>(null);
  useEffect(() => {
    if (!playing) {
      last.current = null;
      return;
    }
    let raf = 0;
    const tick = (now: number) => {
      const dt = last.current == null ? 0 : (now - last.current) / 1000;
      last.current = now;
      setT((prev) => {
        const next = Math.min(duration, prev + dt * speed);
        if (next >= duration) setPlaying(false);
        return next;
      });
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing, speed, duration]);

  const seek = useCallback((v: number) => setT(Math.max(0, Math.min(duration, v))), [duration]);
  const restart = useCallback(() => {
    setT(0);
    setPlaying(false);
  }, []);
  const playPause = useCallback(() => {
    setT((prev) => (prev >= duration ? 0 : prev));
    setPlaying((p) => !p);
  }, [duration]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;
      if (e.code === 'Space' && tag !== 'BUTTON') {
        e.preventDefault();
        playPause();
      } else if (e.code === 'ArrowRight' && tag !== 'BUTTON') seek(t + 5);
      else if (e.code === 'ArrowLeft' && tag !== 'BUTTON') seek(t - 5);
      else if (e.code === 'Home') restart();
      else if (e.code === 'KeyF') setFollow((f) => !f);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [playPause, seek, restart, t]);

  return (
    <div className="app">
      <MissionScene
        bundle={bundle}
        view={view}
        layer={layer}
        exaggeration={exaggeration}
        showControlPoints={showControlPoints}
        showLabels={showLabels}
        playing={playing}
        replaySpeed={speed}
        followAgentId={follow ? agentId : null}
        selectedAgentId={agentId}
        contours={contours}
        cameraSmoothing={cameraSmoothing}
        imageryUrl={imageryUrl}
        surfaceDetail={surfaceDetail}
        trueScale={trueScale}
        contextImageUrl={contextImageUrl}
        showContext={showContext}
        geology={mode === 'geology' && showGeoMap && bundle.geology ? { data: bundle.geology, selected: geoUnit } : null}
        cutaway={mode === 'geology' && showCut && bundle.geology ? bundle.geology : null}
      />
      <div className="vignette" aria-hidden />

      <div className="overlay">
        <div className="left">
          <TitleBlock manifest={m} runId={RUN_ID} />
          <ModeTabs mode={mode} onMode={setMode} />
          <LayerStrip layer={layer} onLayer={setLayer} evaluator={EVALUATOR && !!bundle.rasters.reference} />
          {mode === 'geology' ? (
            <GeologyList data={bundle.geology} selected={geoUnit} onSelect={setGeoUnit} showMap={showGeoMap} onShowMap={setShowGeoMap} showCut={showCut} onShowCut={setShowCut} />
          ) : mode === 'atmos' ? (
            <AtmosList data={bundle.atmosphere} t={t} duration={duration} />
          ) : (
            <ManagementList groups={groups} selected={sel} onSelect={setSelection} />
          )}
          <div className="prompts">
            <button type="button" className="chip" aria-pressed={follow} onClick={() => setFollow((f) => !f)}>
              <kbd>F</kbd> Follow camera
            </button>
            <button type="button" className="chip" onClick={playPause}>
              <kbd>Space</kbd> {playing ? 'Pause' : 'Play'}
            </button>
            <span className="chip chip--static">
              <kbd>←</kbd>
              <kbd>→</kbd> ±5 s
            </span>
          </div>
          <ViewOptions
            exaggeration={exaggeration}
            onExaggeration={setExaggeration}
            showControlPoints={showControlPoints}
            onShowControlPoints={setShowControlPoints}
            showLabels={showLabels}
            onShowLabels={setShowLabels}
            follow={follow}
            onFollow={setFollow}
            contours={contours}
            onContours={setContours}
            cameraSmoothing={cameraSmoothing}
            onCameraSmoothing={setCameraSmoothing}
            imagery={m.imagery ? { title: m.imagery.title, resolutionM: m.imagery.resolution_m } : null}
            showImagery={showImagery}
            onShowImagery={setShowImagery}
            surfaceDetail={surfaceDetail}
            onSurfaceDetail={setSurfaceDetail}
            trueScale={trueScale}
            onTrueScale={setTrueScale}
            surroundings={bundle.context ? showContext : null}
            onSurroundings={setShowContext}
          />
        </div>

        <aside className="right">
          <StatusBlock
            manifest={m}
            missionState={view.state?.mission_state ?? 'IDLE'}
            mapVersion={view.state?.map_version ?? 1}
            t={t}
            agent={agent}
            evaluator={EVALUATOR}
            evaluatorMissing={EVALUATOR && !bundle.rasters.reference}
            exaggeration={exaggeration}
          />
          {mode === 'replay' ? (
            <EventInspector view={view} onSeek={seek} />
          ) : mode === 'geology' ? (
            <GeologyDetails data={bundle.geology} unitId={geoUnit} />
          ) : mode === 'atmos' ? (
            <AtmosDetails data={bundle.atmosphere} />
          ) : (
            details && <DetailsPanel data={details} />
          )}
        </aside>

        <AlertBanner alert={alert} />

        <Vitals
          who={agent ? `${AGENT_NAME[agent.agent_kind]} · ${agent.agent_id}` : 'No agent'}
          map={<Minimap bundle={bundle} view={view} agentId={agentId} size={HUD_MAP_PX} />}
          stats={agent ? agentStats(agent, budgets[agent.agent_id]) : []}
          route={view.activeRoute}
          replanning={view.state?.mission_state === 'REPLAN'}
        />

        <Timeline
          t={t}
          duration={duration}
          playing={playing}
          speed={speed}
          events={bundle.timeline.events}
          onPlayPause={playPause}
          onRestart={restart}
          onSeek={seek}
          onSpeed={setSpeed}
        />

        <footer className="disclaimer">
          {m.disclaimer} {trueScale ? 'Agents and base at true size.' : 'Agents are enlarged with distance (visual only).'}{' '}
          <details className="credits">
            <summary>Credits</summary>
            Terrain: NASA/USGS Mars 2020 TRN CTX DTM mosaic, USGS Astrogeology Science Center (provisional 2 km crop).
            {m.imagery && <> Surface image: {m.imagery.title}, {m.imagery.credit}, via JPL Mars Trek (resampled to {m.imagery.resolution_m} m).</>} "Animated Astronaut Character in Space Suit Loop" (
            <a href="https://skfb.ly/o9nHu" target="_blank" rel="noreferrer">
              https://skfb.ly/o9nHu
            </a>
            ) by LasquetiSpice is licensed under Creative Commons Attribution (
            <a href="http://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">
              http://creativecommons.org/licenses/by/4.0/
            </a>
            ). Materials converted to metallic-roughness for this viewer. Fonts: Rajdhani, Barlow Condensed and IBM Plex Mono (SIL OFL 1.1).
            <div className="credits__refs">
              <strong>NASA reference resources</strong>
              <ul>
                {REFERENCE_SOURCES.map((r) => (
                  <li key={r.url}>
                    <a href={r.url} target="_blank" rel="noreferrer">
                      {r.name}
                    </a>{' '}
                    <span className="credits__status">{r.status}</span> {r.use}
                  </li>
                ))}
              </ul>
            </div>
          </details>
        </footer>
      </div>
    </div>
  );
}
