import { useTerrainScanner } from '../hooks/useTerrainScanner';
import { SCAN_CONFIG } from '../scanner/ScanConfig';
import './TerrainScanButton.css';

/**
 * Terrain-scan key of the first-person dock, styled like the other keys (no icon). Its text and the
 * thin progress line under it come from the one scan state machine: the front position while
 * SCANNING, the recharge while COOLDOWN. The click and the keyboard both call triggerScan().
 */
export function TerrainScanButton() {
  const { snap, trigger } = useTerrainScanner();
  const { state } = snap;
  const progress = state === 'SCANNING' ? snap.scanProgress : state === 'COOLDOWN' ? snap.cooldownProgress : 0;
  const text = state === 'SCANNING' ? 'Scanning' : state === 'COOLDOWN' ? `Recharging ${snap.cooldownLeftS.toFixed(1)} s` : 'Terrain scan';
  const title =
    state === 'DISABLED'
      ? snap.reason ?? 'Scanner unavailable'
      : `Terrain scan (${SCAN_CONFIG.keyLabel}): a visual pulse that redraws the run's orbital slope classes and NoData around the astronaut. Display only, not a sensor.`;
  return (
    <button
      type="button"
      className={`pov__key tscan-key tscan-key--${state.toLowerCase()}`}
      onClick={(e) => {
        e.stopPropagation(); // never moves the camera or the astronaut
        trigger();
      }}
      onPointerDown={(e) => e.stopPropagation()}
      disabled={state !== 'READY'}
      aria-label={state === 'COOLDOWN' ? `Recharging, ${snap.cooldownLeftS.toFixed(1)} seconds left` : text}
      title={title}
    >
      <kbd>{SCAN_CONFIG.keyLabel}</kbd> {text}
      <span className="tscan-key__bar" style={{ transform: `scaleX(${progress})` }} aria-hidden />
    </button>
  );
}
