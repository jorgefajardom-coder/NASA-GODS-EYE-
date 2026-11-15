import { rawImages, useRawImages } from '../lib/rawImagesStore';
import { stopLabel } from '../lib/roverStops';
import type { RoverStop } from '../types/replay';

/**
 * Window of the first-person dock with real Perseverance images from NASA's public feed.
 *
 * Standing on a real rover stop (`stop`), it shows the images NASA lists for that exact stop (same
 * sol, site and drive): where the astronaut stands, the real rover stood. Anywhere else it shows the
 * newest images from where the rover is now, which is not the replay's site. Nothing is requested
 * until the person presses the load button; the images are not terrain data. Display only.
 */
export function MarsNowFrame({ stop, onClose }: { stop: RoverStop | null; onClose: () => void }) {
  const state = useRawImages();
  const wanted = stop?.rmc ?? null;
  // Images loaded for another place are not shown as this one's.
  const matches = state.status === 'ready' && state.forStop === wanted;
  const img = matches ? state.images[state.index] : null;
  const load = () => void (stop ? rawImages.loadStop(stop) : rawImages.load());
  const failed = state.status === 'error' && (state.message.includes(wanted ?? '\u0000') || !wanted);
  return (
    <div className="marsnow" role="region" aria-label={stop ? 'Real Perseverance images of this stop' : 'Mars now: real Perseverance image'}>
      <div className="marsnow__bar">
        <span>{stop ? `Real stop · ${stopLabel(stop)}` : `Real · Perseverance${img ? ` · sol ${img.sol}` : ''}`}</span>
        <button type="button" onClick={onClose} title="Close (M)" aria-label="Close the real images window">
          ×
        </button>
      </div>
      <div className="marsnow__shot">
        {img ? (
          <img src={img.mediumUrl} alt={`Perseverance ${img.instrument}, sol ${img.sol}`} referrerPolicy="no-referrer" />
        ) : state.status === 'loading' ? (
          <p>Loading from NASA…</p>
        ) : (
          <>
            <p>
              {failed
                ? `${(state as { message: string }).message}.`
                : stop
                  ? 'The real rover stopped here on this sol. Load the images NASA took at this stop.'
                  : 'A real image from where Perseverance is now.'}
            </p>
            <button type="button" onClick={load}>
              {failed ? 'Try again' : stop ? 'Load this stop’s images' : 'Load from NASA'}
            </button>
          </>
        )}
      </div>
      {img && (
        <div className="marsnow__foot">
          <span title={`${img.instrument} · ${img.takenUtc} UTC`}>
            {img.instrument.replace(/_/g, ' ')} · {img.credit}
          </span>
          <span className="marsnow__btns">
            <button type="button" onClick={() => rawImages.step(-1)} aria-label="Previous image">
              ‹
            </button>
            <button type="button" onClick={() => rawImages.step(1)} aria-label="Next image">
              ›
            </button>
          </span>
        </div>
      )}
      <small className="marsnow__note">{stop ? 'Real photos of this spot · not terrain data' : 'Not the replay’s site · not terrain data'}</small>
    </div>
  );
}
