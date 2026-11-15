import { useEffect, useRef, useState } from 'react';
import { RAW_GALLERY_URL, parseRawImages, pickRawImages, rawFeedUrl, type RawImage } from '../lib/perseveranceRaw';

type State = { status: 'idle' } | { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; images: RawImage[] };

const SHOWN = 6;
const FETCH = 40;
const TIMEOUT_MS = 12000;

/**
 * Latest Perseverance raw images from NASA's public feed. Nothing is requested until the button is
 * pressed, so the saved replay keeps working offline. The images show where the rover is now, not
 * the replay's site; they are not terrain data and never reach the map or the planner.
 */
export function RawImagesPanel() {
  const [state, setState] = useState<State>({ status: 'idle' });
  const abort = useRef<AbortController | null>(null);
  useEffect(() => () => abort.current?.abort(), []);

  const load = async () => {
    abort.current?.abort();
    const ctl = new AbortController();
    abort.current = ctl;
    const timer = window.setTimeout(() => ctl.abort(), TIMEOUT_MS);
    setState({ status: 'loading' });
    try {
      const res = await fetch(rawFeedUrl(FETCH), { signal: ctl.signal });
      if (!res.ok) throw new Error(`NASA feed answered ${res.status}`);
      const images = pickRawImages(parseRawImages(await res.json()), SHOWN);
      if (images.length === 0) throw new Error('The feed returned no usable images');
      setState({ status: 'ready', images });
    } catch (e) {
      if (ctl.signal.aborted && abort.current !== ctl) return;
      setState({ status: 'error', message: ctl.signal.aborted ? 'The NASA feed did not answer in time' : e instanceof Error ? e.message : 'Could not read the NASA feed' });
    } finally {
      window.clearTimeout(timer);
    }
  };

  return (
    <section className="rawimg" aria-label="Perseverance raw images">
      <h3 className="atmos__h3">Perseverance raw images</h3>
      <p className="muted small atmos__note">
        Real, unprocessed images from NASA&apos;s public feed (NASA/JPL-Caltech). They show where the rover is <strong>now</strong>, not the site of this replay; they are not terrain data and never reach the map or the planner. Loading them needs a network connection.
      </p>
      {state.status !== 'ready' && (
        <button type="button" className="rawimg__load" onClick={load} disabled={state.status === 'loading'}>
          {state.status === 'loading' ? 'Loading…' : state.status === 'error' ? 'Try again' : 'Load the latest images'}
        </button>
      )}
      {state.status === 'error' && <p className="small rawimg__err" role="status">{state.message}. The replay does not depend on it.</p>}
      {state.status === 'ready' && (
        <>
          <ul className="rawimg__grid">
            {state.images.map((i) => (
              <li key={i.id}>
                <a href={i.pageUrl} target="_blank" rel="noreferrer" title={`${i.instrument} · sol ${i.sol}${i.site != null ? ` · site ${i.site}` : ''} · ${i.credit}`}>
                  <img src={i.thumbUrl} alt={`Perseverance ${i.instrument}, sol ${i.sol}`} loading="lazy" width={160} height={160} referrerPolicy="no-referrer" />
                </a>
                <span className="small">
                  Sol {i.sol} · {i.instrument.replace(/_/g, ' ')}
                </span>
              </li>
            ))}
          </ul>
          <p className="muted small atmos__note">
            Credit: NASA/JPL-Caltech. <a href={RAW_GALLERY_URL} target="_blank" rel="noreferrer">All raw images</a>.{' '}
            <button type="button" className="rawimg__link" onClick={load}>
              Refresh
            </button>
          </p>
        </>
      )}
    </section>
  );
}
