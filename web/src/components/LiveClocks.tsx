import { useEffect, useState } from 'react';
import { fmtHms, JEZERO_LON_E_DEG, lmstH, ltstH, marsTime, missionSol, northernSeason, SITE_CLOCKS } from '../lib/marsClock';

/** Ticks once a second (aligned to the second), so the clocks stay in step with the system clock. */
function useNow(): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    let timer = 0;
    const tick = () => {
      setNow(Date.now());
      timer = window.setTimeout(tick, 1000 - (Date.now() % 1000) + 5);
    };
    timer = window.setTimeout(tick, 1000 - (Date.now() % 1000) + 5);
    return () => window.clearTimeout(timer);
  }, []);
  return now;
}

const earthFmt = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZoneName: 'short' });

/**
 * Rows of the status block with the real present time: the viewer's local Earth time (its own
 * time zone) and the time on Mars now (Mars24 algorithm): Mars Coordinated Time, local mean solar
 * time at Jezero, the Perseverance sol and the season. Independent of the replay's simulated time.
 */
export function LiveClocks({ lonEastDeg = JEZERO_LON_E_DEG, world = 'jezero' }: { lonEastDeg?: number; world?: string }) {
  const site = SITE_CLOCKS[world] ?? SITE_CLOCKS.jezero;
  const now = useNow();
  const m = marsTime(now);
  const lmst = lmstH(m, lonEastDeg);
  const ltst = ltstH(m, lonEastDeg);
  const sol = missionSol(now, lonEastDeg, site.landingMs);
  return (
    <>
      <dt>Earth (you)</dt>
      <dd title="Your local time, from this device's clock and time zone">{earthFmt.format(now)}</dd>
      <dt>Mars MTC</dt>
      <dd title={`Mars Coordinated Time now (mean solar time at the prime meridian), Mars Sol Date ${m.msd.toFixed(4)}. Mars24 algorithm, NASA GISS.`}>{fmtHms(m.mtcH)}</dd>
      <dt>{site.place}</dt>
      <dd title={`Local mean solar time at ${site.place} (${lonEastDeg.toFixed(2)}° E) now; true solar (sundial) time ${fmtHms(ltst)}. Mars24 algorithm, NASA GISS.`}>
        {fmtHms(lmst)} LMST
      </dd>
      <dt>Sol</dt>
      <dd title={`${site.mission} mission sol now (sol 0 = its landing sol); season Ls ${m.lsDeg.toFixed(1)}°, ${northernSeason(m.lsDeg)}`}>
        {sol} · Ls {m.lsDeg.toFixed(0)}°
      </dd>
    </>
  );
}
