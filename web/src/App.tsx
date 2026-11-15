import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReplayBundle } from './types/replay';
import { assetUrl, DEFAULT_RUN_ENTRY, RECORDED_RECOVERY_ENTRY, loadEvaluatorReference, loadReplay } from './data/replayAdapter';
import { REFERENCE_SOURCES } from './data/referenceSources';
import { CAMERA_SMOOTHING, type CameraSmoothing } from './lib/smoothing';
import { firstMotionTime, viewAt } from './lib/replay';
import { crewDose } from './lib/atmos';
import type { TerrainLayer } from './lib/layers';
import {
  AGENT_NAME,
  detailsFor,
  initialBudgets,
  managementGroups,
  missionAlert,
  resolveSelection,
  type Selection,
} from './lib/management';
import { MissionScene } from './components/MissionScene';
import { FlatMap } from './components/FlatMap';
import { DroneCamFrame } from './components/DroneCam';
import { resourceAlert } from './lib/resourceAlert';
import { SceneBoundary } from './components/SceneBoundary';
import { detectRenderTier } from './lib/gpu';
import { ManagementList } from './components/ManagementList';
import { DetailsPanel } from './components/DetailsPanel';
import { HUD_MAP_PX, RadialHud, type HudOption } from './components/RadialHud';
import { HudGauge } from './components/HudGauge';
import { resourceLines } from './lib/resources';
import { fmtDuration, isTrustedRoute } from './lib/format';
import { fmtMicroSv } from './lib/atmos';
import { EventInspector } from './components/EventInspector';
import { GeologyDetails, GeologyList } from './components/GeologyPanel';
import { AtmosDetails, AtmosList } from './components/AtmosPanel';
import { Minimap } from './components/Minimap';
import { Timeline } from './components/Timeline';
import { CameraBar } from './components/CameraBar';
import { FirstPersonHud } from './components/FirstPersonHud';
import type { ScanRequest } from './components/DroneScan';
import { scanCells, scanSummary, type ScanClass } from './lib/scan';
import { slopeDegrees } from './lib/slope';
import { displayState } from './lib/provenance';
import { aboutData, stateSnapshot } from './lib/stateSnapshot';
import { Intro, introWanted } from './components/Intro';
import { PORTRAITS } from './lib/portraits';
import { rotateView, ROTATE_STEP_RAD } from './components/ViewRotator';
import { LayerStrip, ViewOptions } from './components/LayerPanel';
import { AlertBanner, ModeTabs, StatusBlock, TitleBlock, type UiMode } from './components/Frame';

const params = new URLSearchParams(window.location.search);
/** Evaluator view shows the hidden reference DEM. Off by default; enable with ?evaluator=1. */
const EVALUATOR = params.get('evaluator') === '1';
// The URL/selector identifies a package folder; its recorded run_id is kept intact.
const RUN_ID = params.get('run') ?? DEFAULT_RUN_ENTRY;
/** Rendering tier, probed once: full 3D, lite 3D (software / slow GPU) or a 2D map without WebGL. */
const RENDER_TIER = detectRenderTier();
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
  // Opens where Restart goes: 4 s before the first motion (see firstMotionTime).
  const [t, setT] = useState(() => firstMotionTime(bundle));
  const [playing, setPlaying] = useState(false);
  // Short recorded runs (seconds long) start at real time; the long demo starts at 10x (the cap).
  const [speed, setSpeed] = useState(duration < 120 ? 1 : 10);
  const [layer, setLayer] = useState<TerrainLayer>('belief');
  const [exaggeration, setExaggeration] = useState(m.vertical_exaggeration_default);
  const [showControlPoints, setShowControlPoints] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  // Intro clip first (unless reduced motion or ?nointro=1); the terrain grows in once it ends.
  const [introDone, setIntroDone] = useState(() => RUN_ID === RECORDED_RECOVERY_ENTRY || !introWanted());
  // Camera: 'free' (map), 'base', or the id of the agent it follows.
  const [camView, setCamView] = useState<string>('free');
  const follow = camView !== 'free' && camView !== 'base';
  // First or third person while following an agent (V toggles; no effect on the free/base cameras).
  const [firstPerson, setFirstPerson] = useState(false);
  /** Drone camera window: on by default with a full GPU (it renders the scene a second time). */
  const [droneCam, setDroneCam] = useState(RENDER_TIER === 'full');
  /** Astronaut helmet lights (L), display only. */
  const [helmetLight, setHelmetLight] = useState(false);
  /** Artificial light (I): terrain lit as by day whatever the real hour at the site. */
  const [artificialLight, setArtificialLight] = useState(false);
  const pov = follow && firstPerson && RENDER_TIER !== 'map2d';
  // First-person camera sway: a per-viewer preference, off by default with reduced motion.
  const [povSway, setPovSwayState] = useState<boolean>(() => {
    try {
      const v = localStorage.getItem('mge.povSway');
      if (v === '1' || v === '0') return v === '1';
    } catch {
      /* per-viewer convenience only */
    }
    return !(typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches);
  });
  const setPovSway = useCallback((v: boolean) => {
    setPovSwayState(v);
    try {
      localStorage.setItem('mge.povSway', v ? '1' : '0');
    } catch {
      /* per-viewer convenience only */
    }
  }, []);
  // Drone-camera scan (display only): orbital slope bands around the drone, see lib/scan.
  const slope = useMemo(() => slopeDegrees(bundle.rasters.prior, m.terrain_meta.rows, m.terrain_meta.cols, m.terrain_meta.resolution_m), [bundle, m.terrain_meta]);
  const [scan, setScan] = useState<(ScanRequest & { counts: Record<ScanClass, number>; fromId: string }) | null>(null);
  // Grab-to-drag is the default for the free camera: left drag slides the map, right drag orbits.
  const [freePan, setFreePan] = useState(true);
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
  // HUD option shown in the dial's inner circle (none: the minimap).
  const [hudOption, setHudOption] = useState<HudOption | null>(null);
  const hudLines = agent ? resourceLines(bundle, t, agent, view.activeRoute, budgets[agent.agent_id]) : [];
  const hudWarn = new Set<HudOption>();
  const hudHints: Partial<Record<HudOption, string>> = {};
  for (const l of hudLines) {
    if (l.tone === 'warn' || l.tone === 'alert') hudWarn.add(l.key);
    hudHints[l.key] = l.key === 'time' ? fmtDuration(l.remaining) : l.remaining == null ? 'no data' : `${l.remaining.toFixed(0)} ${l.unit}`;
  }
  if (agent?.agent_kind !== 'HUMAN') hudHints.oxygen = 'not applicable';
  if (view.activeRoute && (!isTrustedRoute(view.activeRoute) || view.state?.mission_state === 'REPLAN')) hudWarn.add('route');
  hudHints.route = view.activeRoute ? view.activeRoute.route_id : 'none';
  if (agent?.agent_kind === 'HUMAN' && bundle.atmosphere) hudHints.dose = `${fmtMicroSv(crewDose(bundle.atmosphere, t).usv)} µSv`;
  // Following an agent shows its telemetry too; F toggles following the selected agent.
  const followAgent = useCallback((id: string) => {
    setCamView(id);
    setSelection({ kind: 'agent', id });
  }, []);
  const setFollow = useCallback((on: boolean) => setCamView(on && agentId ? agentId : 'free'), [agentId]);
  const hasBase = m.pois.some((p) => p.kind === 'base');
  const drone = view.state?.agents.find((a) => a.agent_kind === 'DRONE') ?? null;
  // First person only (not on the 2D map), and not while the main view already looks through the drone.
  const canDroneCam = !!drone && RENDER_TIER !== 'map2d' && pov && camView !== drone.agent_id;
  const showDroneCam = droneCam && canDroneCam;
  const povAgent = pov ? view.state?.agents.find((a) => a.agent_id === camView) ?? null : null;
  const povAlert = povAgent ? resourceAlert(resourceLines(bundle, t, povAgent, view.activeRoute, budgets[povAgent.agent_id]), budgets[povAgent.agent_id], view.activeRoute, povAgent.agent_id, povAgent.pose.position) : null;
  const runScan = useCallback(() => {
    if (!drone) return;
    const { x, y } = drone.pose.position;
    const marks = scanCells(m.terrain_meta, slope, x, y);
    setScan((prev) => ({ seq: (prev?.seq ?? 0) + 1, x, y, marks, counts: scanSummary(marks), fromId: drone.agent_id }));
  }, [drone, m.terrain_meta, slope]);
  // While following, picking another agent in the list moves the camera to it.
  useEffect(() => {
    if (follow && sel.kind === 'agent' && sel.id && sel.id !== camView) setCamView(sel.id);
  }, [follow, sel.kind, sel.id, camView]);

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
  // Restart shortens the lead-in where every agent is still idle (10 s in the demo, which at 1x
  // looks like a frozen replay) to 4 s. Earlier events stay listed; the scrubber can still reach t = 0.
  const startT = useMemo(() => firstMotionTime(bundle), [bundle]);
  const restart = useCallback(() => {
    setT(startT);
    setPlaying(false);
  }, [startT]);
  const playPause = useCallback(() => {
    setT((prev) => (prev >= duration ? startT : prev));
    setPlaying((p) => !p);
  }, [duration, startT]);

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
      else if (e.code === 'KeyF') setFollow(!follow);
      else if (e.code === 'KeyG') setFreePan((g) => !g);
      else if (e.code === 'KeyV') setFirstPerson((v) => !v);
      else if (e.code === 'KeyB' && pov) setPovSway(!povSway);
      else if (e.code === 'KeyR') runScan();
      else if (e.code === 'KeyC') setDroneCam((c) => !c);
      else if (e.code === 'KeyL') setHelmetLight((v) => !v);
      else if (e.code === 'KeyI') setArtificialLight((v) => !v);
      else if (e.code === 'KeyQ') rotateView(-ROTATE_STEP_RAD);
      else if (e.code === 'KeyE') rotateView(ROTATE_STEP_RAD);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [playPause, seek, restart, t, follow, setFollow, runScan, pov, povSway, setPovSway]);

  // Machine-readable view of the replay for language models and test agents: window.mge.state()
  // returns what is on screen as JSON (see public/llms.txt). Read-only; it changes nothing.
  const snapshotInput = useRef({ view, playing, speed, mode, layer, camView, pov });
  snapshotInput.current = { view, playing, speed, mode, layer, camView, pov };
  useEffect(() => {
    const w = window as unknown as { mge?: unknown };
    w.mge = {
      about: aboutData(bundle),
      docs: { llms: './llms.txt', about: './about.html' },
      state: () => {
        const c = snapshotInput.current;
        return stateSnapshot(bundle, c.view, { playing: c.playing, speed: c.speed, tab: c.mode, layer: c.layer, camera: c.camView, firstPerson: c.pov });
      },
    };
    return () => {
      delete w.mge;
    };
  }, [bundle]);

  // The footer wraps to more lines on narrow screens; the panels above it sit on its measured height.
  const appRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const app = appRef.current;
    const foot = app?.querySelector('.disclaimer') as HTMLElement | null;
    if (!app || !foot || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => app.style.setProperty('--bottom', `${Math.ceil(foot.getBoundingClientRect().height) + 8}px`));
    ro.observe(foot);
    return () => ro.disconnect();
  }, []);

  // The agent dial (menu + map), shared by the third-person column and the first-person HUD.
  const radialHud = (
    <RadialHud
      who={agent ? `${AGENT_NAME[agent.agent_kind]} · ${agent.agent_id}` : 'No agent'}
      center={
        // The 2D map only with no option or Route; every other option fills the circle with its own gauge.
        hudOption && hudOption !== 'route' ? (
          <HudGauge option={hudOption} size={HUD_MAP_PX} bundle={bundle} view={view} t={t} agent={agent} route={view.activeRoute} budget={agent ? budgets[agent.agent_id] : undefined} atmosphere={bundle.atmosphere} />
        ) : (
          <Minimap bundle={bundle} view={view} agentId={agentId} size={HUD_MAP_PX} />
        )
      }
      active={hudOption}
      onSelect={setHudOption}
      warn={hudWarn}
      hints={hudHints}
    />
  );

  return (
    <div className={`app${pov ? ' app--pov' : ''}`} ref={appRef}>
      {RENDER_TIER === 'map2d' ? (
        <FlatMap bundle={bundle} view={view} selectedAgentId={agentId} reason="map2d" />
      ) : (
      <SceneBoundary fallback={<FlatMap bundle={bundle} view={view} selectedAgentId={agentId} reason="failed" />}>
      <MissionScene
        bundle={bundle}
        view={view}
        layer={layer}
        exaggeration={exaggeration}
        showControlPoints={showControlPoints}
        showLabels={showLabels}
        reveal={introDone}
        playing={playing}
        replaySpeed={speed}
        followAgentId={follow ? camView : null}
        baseCamera={camView === 'base'}
        freePan={freePan && camView === 'free'}
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
        firstPerson={firstPerson}
        scan={scan}
        povSway={povSway}
        lite={RENDER_TIER === 'lite'}
        droneCam={showDroneCam}
        helmetLight={helmetLight}
        artificialLight={artificialLight}
      />
      </SceneBoundary>
      )}
      <div className="vignette" aria-hidden />
      {pov && agent && (
        <FirstPersonHud
          agent={view.state?.agents.find((a) => a.agent_id === camView) ?? agent}
          terrainMeta={m.terrain_meta}
          sourceLabel={displayState({ mode: 'REPLAY', source: m.source_mode ?? 'UNKNOWN' }).label}
          pois={m.pois.filter((p) => p.revealed_at_s <= t)}
          scan={scan}
          canScan={!!drone}
          onScan={runScan}
          onExit={() => setFirstPerson(false)}
          route={view.activeRoute}
          dial={radialHud}
          alert={povAlert}
          droneCam={showDroneCam && drone ? <DroneCamFrame droneId={drone.agent_id} onClose={() => setDroneCam(false)} /> : null}
          droneCamOn={showDroneCam}
          canDroneCam={canDroneCam}
          onDroneCam={() => setDroneCam((v) => !v)}
          helmetLight={helmetLight}
          canHelmetLight={!!view.state?.agents.some((a) => a.agent_kind === 'HUMAN')}
          onHelmetLight={() => setHelmetLight((v) => !v)}
          artificialLight={artificialLight}
          onArtificialLight={() => setArtificialLight((v) => !v)}
          sway={povSway}
          onSway={setPovSway}
        />
      )}
      {!introDone && <Intro onDone={() => setIntroDone(true)} />}

      {/* The interface waits behind the intro, then enters (panels slide in, the dial spins in). */}
      <div className={`overlay ${introDone ? 'overlay--enter' : 'overlay--waiting'}`}>
        <div className="left">
          <TitleBlock manifest={m} runId={RUN_ID} />
          <ModeTabs mode={mode} onMode={setMode} />
          <LayerStrip layer={layer} onLayer={setLayer} evaluator={EVALUATOR && !!bundle.rasters.reference} terrainMeta={m.terrain_meta} />
          {mode === 'geology' ? (
            <GeologyList data={bundle.geology} selected={geoUnit} onSelect={setGeoUnit} showMap={showGeoMap} onShowMap={setShowGeoMap} showCut={showCut} onShowCut={setShowCut} />
          ) : mode === 'atmos' ? (
            <AtmosList data={bundle.atmosphere} t={t} duration={duration} />
          ) : (
            <ManagementList groups={groups} selected={sel} onSelect={setSelection} />
          )}
          <CameraBar
            agents={view.state?.agents ?? []}
            view={camView}
            hasBase={hasBase}
            onFree={() => setCamView('free')}
            onBase={() => setCamView('base')}
            onAgent={followAgent}
            firstPerson={firstPerson}
            onFirstPerson={setFirstPerson}
            canScan={!!drone}
            onScan={runScan}
            helmetLight={helmetLight}
            canHelmetLight={!!view.state?.agents.some((a) => a.agent_kind === 'HUMAN')}
            onHelmetLight={() => setHelmetLight((v) => !v)}
            artificialLight={artificialLight}
            onArtificialLight={() => setArtificialLight((v) => !v)}
          />
          <div className="prompts">
            <button type="button" className="chip" aria-pressed={freePan} onClick={() => setFreePan((g) => !g)} title="On: left drag slides the map, right drag orbits. Off: left drag orbits, right drag slides. Wheel zooms.">
              <kbd>G</kbd> Grab map
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
            details && <DetailsPanel data={details} portrait={sel.kind === 'agent' ? PORTRAITS[sel.id] ?? null : null} />
          )}
          {/* One stacked column: the details scroll, the dial keeps its height below them. */}
          {radialHud}
        </aside>

        <AlertBanner alert={alert} />

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
            Terrain: {m.terrain_meta.dataset_id}, {m.terrain_meta.cols * m.terrain_meta.resolution_m} × {m.terrain_meta.rows * m.terrain_meta.resolution_m} m in the recorded datum.
            <ul>{m.terrain_meta.sources.map((source) => <li key={source}>{source}</li>)}</ul>
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
