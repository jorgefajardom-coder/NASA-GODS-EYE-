import type { KeyboardEvent } from 'react';
import type { ListGroup, Selection } from '../lib/management';
import { GlyphIcon } from './icons';

interface Props {
  groups: ListGroup[];
  selected: Selection;
  onSelect: (s: Selection) => void;
}

/**
 * Agents, tasks and routes as one selectable list. Selecting a row fills the
 * details panel and, for agents, the telemetry block and the follow camera.
 */
export function ManagementList({ groups, selected, onSelect }: Props) {
  const onKey = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    const rows = Array.from(e.currentTarget.querySelectorAll<HTMLButtonElement>('button.row'));
    const i = rows.indexOf(document.activeElement as HTMLButtonElement);
    if (i < 0) return;
    e.preventDefault();
    const next = rows[Math.max(0, Math.min(rows.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))];
    next.focus();
    next.click();
  };

  return (
    <section className="mgmt" aria-label="Mission management list" onKeyDown={onKey}>
      <div className="mgmt__head" aria-hidden>
        <span>Name</span>
        <span>State</span>
      </div>
      <div className="mgmt__scroll">
        {groups.map((g) => (
          <div key={g.key} className="mgmt__group">
            <div className="mgmt__bar">
              <GlyphIcon glyph={g.glyph} size={18} />
              <span className="mgmt__title">{g.title}</span>
              <span className="mgmt__valuelabel">{g.valueLabel}</span>
              <span className="mgmt__count mono">×{g.rows.length}</span>
            </div>
            {g.rows.length === 0 ? (
              <div className="mgmt__empty">{g.emptyText}</div>
            ) : (
              g.rows.map((r) => {
                const isSel = r.selection.kind === selected.kind && r.selection.id === selected.id;
                return (
                  <button
                    key={r.key}
                    type="button"
                    className={`row row--${r.tone}${isSel ? ' is-selected' : ''}`}
                    aria-pressed={isSel}
                    onClick={() => onSelect(r.selection)}
                  >
                    <span className="row__check" aria-hidden />
                    <span className="row__icon">
                      <GlyphIcon glyph={r.glyph} size={16} />
                    </span>
                    <span className="row__name">{r.name}</span>
                    <span className="row__state">{r.state}</span>
                    <span className="row__value mono">{r.value}</span>
                  </button>
                );
              })
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
