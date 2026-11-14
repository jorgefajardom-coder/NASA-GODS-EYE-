import type { AgentKind, AgentState, RouteDecision, RouteStatus, TaskState } from '../types/icd';
import type { ReplayBundle } from '../types/replay';
import { yawFromQuaternion } from './coords';
import {
  fmtDuration,
  fmtNumber,
  fmtSimTime,
  fractionRemaining,
  isTrustedRoute,
  NOT_ESTIMATED,
  ROUTE_STATUS_STYLE,
  routeEta,
} from './format';
import type { ReplayView } from './replay';

/**
 * Data behind the mission management list, the details panel and the alert banner.
 * Everything shown comes from received objects (AgentState, RouteDecision,
 * MissionEvent). Nothing is estimated here; a missing value reads "Not estimated".
 */

export type Glyph = 'human' | 'drone' | 'rover' | 'task' | 'route';
export type Tone = 'neutral' | 'ok' | 'warn' | 'bad' | 'unknown';

export interface Selection {
  kind: 'agent' | 'task' | 'route';
  id: string;
}

export interface ListRow {
  key: string;
  selection: Selection;
  glyph: Glyph;
  name: string;
  state: string;
  value: string;
  tone: Tone;
}

export interface ListGroup {
  key: 'agents' | 'tasks' | 'routes';
  title: string;
  /** Meaning of the right-hand column of this group. */
  valueLabel: string;
  glyph: Glyph;
  rows: ListRow[];
  emptyText: string;
}

export const AGENT_NAME: Record<AgentKind, string> = { HUMAN: 'Astronaut', DRONE: 'Drone', ROVER: 'Rover' };
const AGENT_GLYPH: Record<AgentKind, Glyph> = { HUMAN: 'human', DRONE: 'drone', ROVER: 'rover' };

function agentTone(a: AgentState): Tone {
  if (a.mode === 'HALTED') return 'warn';
  if (a.mode === 'IDLE') return 'neutral';
  return 'ok';
}

function taskTone(s: TaskState): Tone {
  if (s === 'REJECTED' || s === 'BLOCKED') return 'bad';
  if (s === 'ASSIGNED' || s === 'EXECUTING') return 'ok';
  return 'neutral';
}

function routeTone(status: RouteStatus): Tone {
  if (status === 'FEASIBLE') return 'ok';
  if (status === 'UNKNOWN' || status === 'STALE_MAP') return 'unknown';
  return 'bad';
}

export function managementGroups(view: ReplayView): ListGroup[] {
  const agents = view.state?.agents ?? [];
  const agentRows: ListRow[] = agents.map((a) => ({
    key: `agent:${a.agent_id}`,
    selection: { kind: 'agent', id: a.agent_id },
    glyph: AGENT_GLYPH[a.agent_kind],
    name: AGENT_NAME[a.agent_kind],
    state: a.mode.toLowerCase(),
    value: fmtNumber(a.energy_remaining_wh, 'Wh'),
    tone: agentTone(a),
  }));

  const taskRows: ListRow[] = view.tasks.map((k) => ({
    key: `task:${k.task_id}`,
    selection: { kind: 'task', id: k.task_id },
    glyph: 'task',
    name: k.task_id,
    state: k.state.toLowerCase(),
    value: k.agent_id || '—',
    tone: taskTone(k.state),
  }));

  const routes: Array<{ r: RouteDecision; invalidated: boolean }> = [
    ...view.previousRoutes.map((r) => ({ r, invalidated: true })),
    ...(view.activeRoute ? [{ r: view.activeRoute, invalidated: false }] : []),
  ];
  const routeRows: ListRow[] = routes.map(({ r, invalidated }) => ({
    key: `route:${r.route_id}`,
    selection: { kind: 'route', id: r.route_id },
    glyph: 'route',
    name: `${r.route_id} · ${r.mode.toLowerCase()}`,
    state: invalidated ? 'invalidated' : ROUTE_STATUS_STYLE[r.status].label.toLowerCase(),
    value: `map v${r.map_version_used}`,
    tone: invalidated ? 'bad' : routeTone(r.status),
  }));

  return [
    { key: 'agents', title: 'Agents', valueLabel: 'Energy', glyph: 'human', rows: agentRows, emptyText: 'No agent state received' },
    { key: 'tasks', title: 'Tasks', valueLabel: 'Agent', glyph: 'task', rows: taskRows, emptyText: 'No task discovered yet' },
    { key: 'routes', title: 'Routes', valueLabel: 'Planned on', glyph: 'route', rows: routeRows, emptyText: 'No route received yet' },
  ];
}

/** Keeps the selection when it still exists at this time, else falls back to the primary agent. */
export function resolveSelection(sel: Selection, view: ReplayView): Selection {
  const exists =
    sel.kind === 'agent'
      ? !!view.state?.agents.some((a) => a.agent_id === sel.id)
      : sel.kind === 'task'
        ? view.tasks.some((k) => k.task_id === sel.id)
        : [...view.previousRoutes, ...(view.activeRoute ? [view.activeRoute] : [])].some((r) => r.route_id === sel.id);
  if (exists) return sel;
  return { kind: 'agent', id: view.state?.primary_agent_id ?? view.state?.agents[0]?.agent_id ?? '' };
}

export interface Budget {
  time_s: number | null;
  energy_wh: number | null;
  oxygen_l: number | null;
}

/**
 * Reference for the percentage bars: the first received sample of each agent.
 * It is not a certified budget; the bars say "of first sample" through their tooltip.
 */
export function initialBudgets(bundle: ReplayBundle): Record<string, Budget> {
  const out: Record<string, Budget> = {};
  for (const a of bundle.timeline.frames[0]?.mission_state.agents ?? []) {
    out[a.agent_id] = { time_s: a.time_remaining_s, energy_wh: a.energy_remaining_wh, oxygen_l: a.oxygen_remaining_l };
  }
  return out;
}

export interface Stat {
  label: string;
  /** Text next to the bar. */
  value: string;
  fraction: number | null;
  percent: string | null;
  applicable: boolean;
}

function amount(remaining: number | null | undefined, budget: number | null | undefined, unit: string): string {
  if (remaining == null || !Number.isFinite(remaining)) return NOT_ESTIMATED;
  if (budget == null || !Number.isFinite(budget)) return `${remaining.toFixed(0)} ${unit}`;
  return `${remaining.toFixed(0)}/${budget.toFixed(0)} ${unit}`;
}

function stat(label: string, value: string, fraction: number | null, applicable = true): Stat {
  return { label, value, fraction, percent: fraction == null ? null : `${Math.round(fraction * 100)} %`, applicable };
}

export function agentStats(a: AgentState, b: Budget | undefined): Stat[] {
  const human = a.agent_kind === 'HUMAN';
  return [
    human
      ? stat('Oxygen', amount(a.oxygen_remaining_l, b?.oxygen_l, 'L'), fractionRemaining(a.oxygen_remaining_l, b?.oxygen_l))
      : stat('Oxygen', 'Not applicable', null, false),
    stat('Energy', amount(a.energy_remaining_wh, b?.energy_wh, 'Wh'), fractionRemaining(a.energy_remaining_wh, b?.energy_wh)),
    stat('Time', fmtDuration(a.time_remaining_s), fractionRemaining(a.time_remaining_s, b?.time_s)),
  ];
}

export interface DetailData {
  glyph: Glyph;
  title: string;
  subtitle: string;
  stats: Stat[];
  facts: Array<[string, string]>;
  body: string;
  source: string[];
}

/** Compass heading in degrees clockwise from north, from an ENU yaw (0 = east). */
export function headingFromNorth(yawRad: number): number {
  const deg = (yawRad * 180) / Math.PI;
  return (((90 - deg) % 360) + 360) % 360;
}

function sourceLines(view: ReplayView, bundle: ReplayBundle): string[] {
  const m = bundle.manifest;
  return [`Provenance: ${m.provenance.join(' · ')}${m.illustrative ? ' · illustrative' : ''}`, `Run ${m.run_id} · map v${view.state?.map_version ?? '–'}`];
}

export function detailsFor(
  sel: Selection,
  view: ReplayView,
  bundle: ReplayBundle,
  budgets: Record<string, Budget>,
): DetailData | null {
  const source = sourceLines(view, bundle);

  if (sel.kind === 'agent') {
    const a = view.state?.agents.find((x) => x.agent_id === sel.id);
    if (!a || !view.state) return null;
    const p = a.pose.position;
    const own = view.tasks.filter((k) => k.agent_id === a.agent_id && (k.state === 'ASSIGNED' || k.state === 'EXECUTING'));
    const parts = [`${AGENT_NAME[a.agent_kind]} ${a.agent_id}, currently ${a.mode.toLowerCase()}.`];
    if (view.state.primary_agent_id === a.agent_id) {
      const base = bundle.manifest.pois.find((x) => x.kind === 'base')?.label;
      const goal = bundle.manifest.pois.find((x) => x.kind === 'primary_goal')?.label;
      if (base && goal) parts.push(`Primary agent: reach ${goal} and return to ${base}.`);
      if (view.state.active_task_id) parts.push(`Mission task: ${view.state.active_task_id} (${view.state.active_task_state.toLowerCase()}).`);
    }
    parts.push(own.length ? `Active tasks: ${own.map((k) => k.task_id).join(', ')}.` : 'No other active task reported.');
    return {
      glyph: AGENT_GLYPH[a.agent_kind],
      title: AGENT_NAME[a.agent_kind],
      subtitle: a.agent_id,
      stats: agentStats(a, budgets[a.agent_id]),
      facts: [
        ['Position', `E ${p.x.toFixed(1)}  N ${p.y.toFixed(1)}  U ${p.z.toFixed(1)} m`],
        ['Heading', `${headingFromNorth(yawFromQuaternion(a.pose.orientation)).toFixed(0).padStart(3, '0')}° from north`],
        ['Mode', a.mode.toLowerCase()],
        ['Pose confidence', a.confidence == null ? NOT_ESTIMATED : `${Math.round(a.confidence * 100)} %`],
      ],
      body: parts.join(' '),
      source,
    };
  }

  if (sel.kind === 'task') {
    const k = view.tasks.find((x) => x.task_id === sel.id);
    if (!k) return null;
    return {
      glyph: 'task',
      title: k.task_id,
      subtitle: k.state.toLowerCase(),
      stats: [],
      facts: [
        ['State', k.state.toLowerCase()],
        ['Assigned to', k.agent_id || 'Nobody'],
        ['Reason', k.reason_code || 'Not available'],
        ['Updated', fmtSimTime(k.updated_at_s)],
      ],
      body: k.detail || 'No detail reported.',
      source,
    };
  }

  const route = bundle.routes.get(sel.id);
  if (!route) return null;
  const invalidated = view.previousRoutes.some((r) => r.route_id === route.route_id);
  const trusted = isTrustedRoute(route);
  const style = ROUTE_STATUS_STYLE[route.status];
  const replan = view.replans.find((r) => r.invalidated.route_id === route.route_id);
  const body = [route.detail, `Reason: ${route.reason_code}.`];
  if (invalidated && replan) body.push(`Invalidated at ${fmtSimTime(replan.invalidated.timestamp_sim_s)}: ${replan.invalidated.detail}`);
  if (!trusted) body.push(style.description);
  return {
    glyph: 'route',
    title: route.route_id,
    subtitle: invalidated ? 'invalidated' : style.label.toLowerCase(),
    stats: [],
    facts: [
      ['Agent', route.agent_id],
      ['Mode', route.mode.toLowerCase()],
      ['Planned on', `map v${route.map_version_used}`],
      ['Round trip', trusted ? routeEta(route) : 'No ETA (route not verified)'],
      ['Reserve time', trusted ? fmtDuration(route.reserve_time_s) : NOT_ESTIMATED],
      ['Reserve energy', trusted ? fmtNumber(route.reserve_wh, 'Wh') : NOT_ESTIMATED],
      ['Reserve oxygen', trusted ? fmtNumber(route.reserve_oxygen_l, 'L') : NOT_ESTIMATED],
      ['Min. clearance', fmtNumber(route.min_clearance_m, 'm', 1)],
      ['Waypoints', `${route.outbound_path.length} out · ${route.return_path.length} back`],
    ],
    body: body.join(' '),
    source,
  };
}

export interface MissionAlert {
  tone: 'warn' | 'bad';
  title: string;
  detail: string;
}

export function missionAlert(view: ReplayView): MissionAlert | null {
  const s = view.state;
  if (!s) return null;
  if (s.mission_state === 'REPLAN') {
    const last = view.replans[view.replans.length - 1];
    return { tone: 'warn', title: 'Route invalidated · replanning', detail: last?.invalidated.detail ?? 'Waiting for a new route decision.' };
  }
  if (s.mission_state === 'BLOCKED' || s.mission_state === 'ABORTED') {
    return { tone: 'bad', title: `Mission ${s.mission_state.toLowerCase()}`, detail: s.reason_code || 'No reason reported.' };
  }
  if (view.activeRoute && !isTrustedRoute(view.activeRoute)) {
    return {
      tone: 'warn',
      title: `Route ${ROUTE_STATUS_STYLE[view.activeRoute.status].label.toLowerCase()} · not verified`,
      detail: view.activeRoute.detail,
    };
  }
  return null;
}
