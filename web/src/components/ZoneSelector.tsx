import { useCallback, useEffect, useRef, useState } from 'react';
import { assetUrl } from '../data/replayAdapter';
import { WORLDS, initialZoneIndex, stepZone, zoneUrl, type WorldInfo } from '../data/worlds';

/** Session key that carries the card image across the page load, for the arrival fade. */
export const ARRIVAL_KEY = 'mge-zone-arrival';
/** Card-to-screen zoom before the page changes (ms). */
const TRAVEL_MS = 750;

const STATUS_TEXT: Record<WorldInfo['status'], string> = { scene: 'Scene' };

/** Whether this load comes from the selector (the arrival fade will show), without consuming it. */
export function arrivalPending(runId: string): boolean {
  try {
    const raw = window.sessionStorage.getItem(ARRIVAL_KEY);
    return raw != null && (JSON.parse(raw) as { runId?: string }).runId === runId;
  } catch {
    return false;
  }
}

function readArrival(runId: string): string | null {
  try {
    const raw = window.sessionStorage.getItem(ARRIVAL_KEY);
    if (!raw) return null;
    window.sessionStorage.removeItem(ARRIVAL_KEY);
    const a = JSON.parse(raw) as { runId?: string; image?: string };
    return a.runId === runId && typeof a.image === 'string' ? a.image : null;
  } catch {
    return null;
  }
}

/**
 * After travelling from the selector, the zone's card image (the same north-up orthomosaic that is draped
 * on the terrain) covers the screen and fades into the 3D scene. Nothing is shown on a normal load.
 */
export function ZoneArrival({ runId }: { runId: string }) {
  const [image] = useState(() => readArrival(runId));
  const [gone, setGone] = useState(false);
  useEffect(() => {
    if (!image) return;
    const id = window.setTimeout(() => setGone(true), 1600);
    return () => window.clearTimeout(id);
  }, [image]);
  if (!image || gone) return null;
  return (
    <div className="zone-arrival" aria-hidden>
      <img src={image} alt="" />
    </div>
  );
}

function ZoneCard({ zone, place, onPick }: { zone: WorldInfo; place: 'prev' | 'current' | 'next'; onPick: () => void }) {
  return (
    <button
      type="button"
      className={`zone-card zone-card--${place} zone-card--${zone.status}`}
      onClick={onPick}
      aria-current={place === 'current'}
      aria-label={`${zone.place}, ${zone.mission}: ${STATUS_TEXT[zone.status]}`}
      tabIndex={place === 'current' ? 0 : -1}
    >
      <span className="zone-card__img">
        {zone.image && <img src={assetUrl(zone.image)} alt={zone.imageCaption ?? ''} draggable={false} />}
      </span>
      <span className="zone-card__place">{zone.place}</span>
      <span className="zone-card__mission">
        {zone.mission} · {STATUS_TEXT[zone.status]}
      </span>
    </button>
  );
}

/**
 * Zone selector: a carousel of the Mars zones (one scene per place), each shown with real
 * orbital imagery of that place. Travel zooms the card
 * to the screen and opens its scene; the same image then fades into the terrain (ZoneArrival).
 * It opens right after the intro on load (instantly, so the scene never shows behind it); travelling to the zone already loaded simply enters it.
 * Keys: left/right, Enter to travel, Esc to go back.
 */
export function ZoneSelector({ runId, onClose, instant = false }: { runId: string; onClose: () => void; instant?: boolean }) {
  const [i, setI] = useState(() => initialZoneIndex(runId));
  const [flight, setFlight] = useState<{ rect: DOMRect; image: string } | null>(null);
  const currentRef = useRef<HTMLDivElement>(null);
  const zone = WORLDS[i];
  const prev = WORLDS[stepZone(i, -1)];
  const next = WORLDS[stepZone(i, 1)];
  const canTravel = zone.status === 'scene';

  const travel = useCallback(() => {
    if (flight) return;
    if (zone.status !== 'scene' || !zone.runId) return;
    if (zone.runId === runId) return onClose();
    const image = zone.image ? assetUrl(zone.image) : '';
    try {
      window.sessionStorage.setItem(ARRIVAL_KEY, JSON.stringify({ runId: zone.runId, image }));
    } catch {
      /* no session storage: travel without the arrival fade */
    }
    const card = currentRef.current?.querySelector('.zone-card__img');
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const go = () => window.location.assign(zoneUrl(window.location.href, zone.runId!));
    if (!card || !image || reduced) return go();
    setFlight({ rect: card.getBoundingClientRect(), image });
    window.setTimeout(go, TRAVEL_MS);
  }, [flight, zone, runId, onClose]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (flight) return;
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowLeft') setI((v) => stepZone(v, -1));
      else if (e.key === 'ArrowRight') setI((v) => stepZone(v, 1));
      else if (e.key === 'Enter') travel();
      else return;
      e.preventDefault();
      e.stopPropagation();
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [flight, onClose, travel]);

  return (
    <div className={`zones${instant ? ' zones--instant' : ''}`} role="dialog" aria-modal="true" aria-label="Select zone">
      <header className="zones__head">
        <h2 className="zones__title">Select zone</h2>
        <p className="zones__body">Mars</p>
      </header>

      <div className="zones__carousel">
        <button type="button" className="zones__arrow zones__arrow--prev" onClick={() => setI(stepZone(i, -1))} aria-label={`Previous zone: ${prev.place}`}>
          ‹
        </button>
        <div className="zones__track">
          <div className="zones__slot zones__slot--side">
            <ZoneCard zone={prev} place="prev" onPick={() => setI(stepZone(i, -1))} />
          </div>
          <div className="zones__slot" ref={currentRef}>
            <ZoneCard zone={zone} place="current" onPick={travel} />
          </div>
          <div className="zones__slot zones__slot--side">
            <ZoneCard zone={next} place="next" onPick={() => setI(stepZone(i, 1))} />
          </div>
        </div>
        <button type="button" className="zones__arrow zones__arrow--next" onClick={() => setI(stepZone(i, 1))} aria-label={`Next zone: ${next.place}`}>
          ›
        </button>
      </div>

      <div className="zones__dots" role="tablist" aria-label="Zones">
        {WORLDS.map((w, k) => (
          <button key={w.id} type="button" role="tab" aria-selected={k === i} aria-label={w.place} className="zones__dot" onClick={() => setI(k)} />
        ))}
      </div>

      <footer className="zones__foot">
        <button type="button" className="zones__back" onClick={onClose}>
          <kbd>Esc</kbd> Back
        </button>
        <button type="button" className="zones__travel" onClick={travel} disabled={!canTravel}>
          Travel <span aria-hidden>›</span>
        </button>
      </footer>

      {flight && (
        <div
          className="zones__flight"
          style={{ ['--x' as string]: `${flight.rect.left}px`, ['--y' as string]: `${flight.rect.top}px`, ['--w' as string]: `${flight.rect.width}px`, ['--h' as string]: `${flight.rect.height}px` }}
          aria-hidden
        >
          <img src={flight.image} alt="" />
        </div>
      )}
    </div>
  );
}
