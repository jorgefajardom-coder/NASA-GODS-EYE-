import { useEffect } from 'react';
import { rawImages, useRawImages } from '../lib/rawImagesStore';
import { stopLabel } from '../lib/roverStops';
import type { RoverMission, RoverStop } from '../types/replay';

const PERSEVERANCE: RoverMission = { id: 'mars2020', name: 'Perseverance', raw_category: 'mars2020', image_match: 'stop' };

/**
 * Window of the first-person dock with real Perseverance images from NASA's public feed.
 *
 * Standing on a real rover stop (`stop`), it shows the images NASA lists for that exact stop (same
 * sol, site and drive): where the astronaut stands, the real rover stood. Anywhere else it shows the
 * newest images from where the rover is now, which is not the replay's site. Nothing is requested
 * until the person presses the load button; the images are not terrain data. Display only.
 */
/** Photo tour controls: the images load by themselves because the person pressed the tour button. */
export interface TourControls {
  index: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
  onStop: () => void;
}

export function MarsNowFrame({ stop, mission = PERSEVERANCE, onClose, tour }: { stop: RoverStop | null; mission?: RoverMission; onClose: () => void; tour?: TourControls | null }) {
  const state = useRawImages();
  const stopId = stop?.rmc ?? null;
  // On the tour, each stop loads its own images on arrival (once per stop; the sol is cached).
  useEffect(() => {
    if (tour && stop) void rawImages.loadStop(stop, mission);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [!!tour, stopId]);
  const wanted = stop?.rmc ?? null;
  // Images loaded for another place are not shown as this one's.
  const matches = state.status === 'ready' && state.forStop === wanted;
  const img = matches ? state.images[state.index] : null;
  const load = () => void (stop ? rawImages.loadStop(stop, mission) : rawImages.load(mission));
  const failed = state.status === 'error';
  return (
    <div className="marsnow" role="region" aria-label={stop ? `Real ${mission.name} images of this stop` : `Mars now: real ${mission.name} image`}>
      <div className="marsnow__bar">
        <span>{stop ? `Real stop${tour ? ` ${tour.index + 1}/${tour.total}` : ''} · ${stopLabel(stop)}` : `Real · ${mission.name}${img ? ` · sol ${img.sol}` : ''}`}</span>
        <button type="button" onClick={onClose} title="Close (M)" aria-label="Close the real images window">
          ×
        </button>
      </div>
      <div className="marsnow__shot">
        {img ? (
          <img src={img.mediumUrl} alt={`Perseverance ${img.instrument}, sol ${img.sol}`} referrerPolicy="no-referrer" />
        ) : state.status === 'loading' ? (
          <p>Loading from NASA…</p>
        ) : tour && !stop ? (
          <p>Driving to the next real stop…</p>
        ) : (
          <>
            <p>
              {failed
                ? `${(state as { message: string }).message}.`
                : stop
                  ? mission.image_match === 'sol'
                    ? `The real rover stopped here on sol ${stop.sol}. Load the images NASA took that sol (the feed does not say where).`
                    : 'The real rover stopped here on this sol. Load the images NASA took at this stop.'
                  : `A real image from where ${mission.name} is now.`}
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
      {tour && (
        <div className="marsnow__tour" role="group" aria-label="Photo tour">
          <button type="button" onClick={tour.onPrev} aria-label="Previous stop">
            ⏮ Stop
          </button>
          <button type="button" onClick={tour.onNext} aria-label="Next stop">
            Stop ⏭
          </button>
          <button type="button" onClick={tour.onStop}>
            End tour
          </button>
        </div>
      )}
      <small className="marsnow__note">{stop ? (mission.image_match === 'sol' ? 'Real photos of this sol · the rover may have moved · not terrain data' : 'Real photos of this spot · not terrain data') : 'Not the replay’s site · not terrain data'}</small>
    </div>
  );
}
