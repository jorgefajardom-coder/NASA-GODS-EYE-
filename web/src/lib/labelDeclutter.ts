/**
 * Keeps the floating 3D labels (agents, sites, routes, rover stops) from covering each other when the
 * camera pulls back: labels are taken in priority order and one that would overlap an already shown
 * label is hidden until there is room. Display only; nothing in the scene or the data changes.
 */
export interface LabelBox {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export interface LabelItem<T> {
  id: T;
  box: LabelBox;
  /** Lower is shown first. */
  priority: number;
}

const overlaps = (a: LabelBox, b: LabelBox, pad: number): boolean =>
  a.left < b.right + pad && a.right + pad > b.left && a.top < b.bottom + pad && a.bottom + pad > b.top;

/** The ids to show: greedy by priority (then left to right), skipping any label that overlaps a shown one. */
export function pickVisibleLabels<T>(items: ReadonlyArray<LabelItem<T>>, pad = 4): Set<T> {
  const order = [...items].sort((a, b) => a.priority - b.priority || a.box.left - b.box.left || a.box.top - b.box.top);
  const shown: LabelBox[] = [];
  const out = new Set<T>();
  for (const it of order) {
    if (shown.some((s) => overlaps(it.box, s, pad))) continue;
    shown.push(it.box);
    out.add(it.id);
  }
  return out;
}

/** Priority of a label element from its classes: the selected agent first, routes and plain stops last. */
export function labelPriority(el: Element): number {
  const c = el.classList;
  if (c.contains('agent-label--selected')) return 0;
  if (c.contains('agent-label')) return 1;
  if (c.contains('stop-tag--on')) return 2;
  if (c.contains('site-label--base') || c.contains('site-label--primary_goal')) return 2;
  if (c.contains('site-label')) return 3;
  if (c.contains('stop-tag')) return 4;
  if (c.contains('route-label')) return 5;
  return 6;
}

const SELECTOR = '.agent-label, .site-label, .route-label, .stop-tag';

/** Runs the declutter a few times a second over the labels inside `root`; returns a stop function. */
export function startLabelDeclutter(root: HTMLElement, everyMs = 140): () => void {
  const tick = () => {
    const els = Array.from(root.querySelectorAll<HTMLElement>(SELECTOR));
    if (els.length < 2) {
      for (const el of els) el.style.visibility = '';
      return;
    }
    const items = els
      .map((el, i) => {
        const r = el.getBoundingClientRect();
        return { id: i, box: { left: r.left, top: r.top, right: r.right, bottom: r.bottom }, priority: labelPriority(el), w: r.width };
      })
      // A label that is not on screen (zero size) takes no room.
      .filter((it) => it.w > 0);
    const visible = pickVisibleLabels(items);
    for (const it of items) els[it.id].style.visibility = visible.has(it.id) ? '' : 'hidden';
  };
  const id = window.setInterval(tick, everyMs);
  return () => {
    window.clearInterval(id);
    for (const el of Array.from(root.querySelectorAll<HTMLElement>(SELECTOR))) el.style.visibility = '';
  };
}
