/** Compact provenance/explanation: a small (i) mark whose text shows on hover or focus. */
export function Info({ text }: { text: string }) {
  return (
    <span className="info" tabIndex={0} role="note" aria-label={text} title={text}>
      i
    </span>
  );
}
