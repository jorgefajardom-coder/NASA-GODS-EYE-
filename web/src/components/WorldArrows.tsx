import { WORLDS, worldOfRun, type WorldInfo } from '../data/worlds';

/** The worlds that have a scene, in catalogue order. */
const SCENES = WORLDS.filter((w): w is WorldInfo & { runId: string } => w.runId != null);

/** The scene world before and after the current one, wrapping around; null when there is nothing to switch to. */
export function neighbourWorlds(runId: string): { prev: WorldInfo & { runId: string }; next: WorldInfo & { runId: string } } | null {
  const here = worldOfRun(runId);
  const i = SCENES.findIndex((w) => w.id === here?.id);
  if (i < 0 || SCENES.length < 2) return null;
  return { prev: SCENES[(i + SCENES.length - 1) % SCENES.length], next: SCENES[(i + 1) % SCENES.length] };
}

/** Opens another saved run (full reload keeps every run's state separate). */
function openWorld(runId: string) {
  const url = new URL(window.location.href);
  url.searchParams.set('run', runId);
  window.location.assign(url.toString());
}

/**
 * Left and right arrows to move to the previous or next world, shown while the map camera is in use
 * (not while following an agent). No menu tabs: the arrows name the world they lead to on hover.
 */
export function WorldArrows({ runId }: { runId: string }) {
  const n = neighbourWorlds(runId);
  if (!n) return null;
  return (
    <div className="world-arrows" role="group" aria-label="Change world">
      <button type="button" className="world-arrows__btn world-arrows__btn--prev" onClick={() => openWorld(n.prev.runId)} title={`${n.prev.place} · ${n.prev.mission}`} aria-label={`Previous world: ${n.prev.place}`}>
        <span aria-hidden>‹</span>
        <small>{n.prev.place}</small>
      </button>
      <button type="button" className="world-arrows__btn world-arrows__btn--next" onClick={() => openWorld(n.next.runId)} title={`${n.next.place} · ${n.next.mission}`} aria-label={`Next world: ${n.next.place}`}>
        <span aria-hidden>›</span>
        <small>{n.next.place}</small>
      </button>
    </div>
  );
}
