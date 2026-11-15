import { useEffect, useRef, useState } from 'react';
import { scanController, triggerScan } from '../scanner/ScanController';
import type { ScanSnapshot } from '../scanner/ScanStateMachine';

/**
 * React view of the single scan state machine. It samples the controller on animation frames and
 * re-renders only when what the button shows changes, so the progress ring follows the real wave
 * instead of running its own animation.
 */
export function useTerrainScanner(): { snap: ScanSnapshot; trigger: () => boolean } {
  const [snap, setSnap] = useState<ScanSnapshot>(() => scanController.snapshot());
  const key = useRef('');
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const s = scanController.snapshot();
      // Quantise what the button draws (1/200 of a turn, 0.1 s) to avoid needless renders.
      const k = `${s.state}|${Math.round(s.scanProgress * 200)}|${Math.round(s.cooldownProgress * 200)}|${Math.ceil(s.cooldownLeftS * 10)}|${s.reason}`;
      if (k !== key.current) {
        key.current = k;
        setSnap(s);
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);
  return { snap, trigger: triggerScan };
}
