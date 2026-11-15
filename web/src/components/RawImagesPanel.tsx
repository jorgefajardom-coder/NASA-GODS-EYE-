import { useRawImages, rawImages, rawImagesRequestMatches } from '../lib/rawImagesStore';
import { RAW_GALLERY_URL } from '../lib/perseveranceRaw';

/**
 * Latest Perseverance raw images from NASA's public feed (Atmos tab). Nothing is requested until the
 * button is pressed, so the saved replay keeps working offline. The images show where the rover is
 * now, not the replay's site; they are not terrain data and never reach the map or the planner.
 * The same loaded images feed the first-person "Mars now" window.
 */
export function RawImagesPanel() {
  const state = useRawImages();
  const matches = rawImagesRequestMatches(state, 'mars2020');
  const ready = state.status === 'ready' && matches ? state : null;
  const loading = state.status === 'loading' && matches;
  const error = state.status === 'error' && matches ? state.message : null;
  return (
    <section className="rawimg" aria-label="Perseverance raw images">
      <h3 className="atmos__h3">Perseverance raw images</h3>
      <p className="muted small atmos__note">
        Real, unprocessed images from NASA&apos;s public feed (NASA/JPL-Caltech). They show where the rover is <strong>now</strong>, not the site of this replay; they are not terrain data and never reach the map or the planner. Loading them needs a network connection. In first person, <kbd>M</kbd> opens them beside the simulated view.
      </p>
      {!ready && (
        <button type="button" className="rawimg__load" onClick={() => void rawImages.load()} disabled={loading}>
          {loading ? 'Loading…' : error ? 'Try again' : 'Load the latest images'}
        </button>
      )}
      {error && <p className="small rawimg__err" role="status">{error}. The replay does not depend on it.</p>}
      {ready && (
        <>
          <ul className="rawimg__grid">
            {ready.images.map((i) => (
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
            <button type="button" className="rawimg__link" onClick={() => void rawImages.load()}>
              Refresh
            </button>
          </p>
        </>
      )}
    </section>
  );
}
