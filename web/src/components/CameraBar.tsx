import type { AgentState } from '../types/icd';
import { rotateView, ROTATE_STEP_RAD } from './ViewRotator';

const KIND_ORDER: AgentState['agent_kind'][] = ['HUMAN', 'ROVER', 'DRONE'];
const KIND_LABEL: Record<AgentState['agent_kind'], string> = { HUMAN: 'Astronaut', ROVER: 'Rover', DRONE: 'Drone' };

interface Props {
  agents: AgentState[];
  /** 'free', 'base' or the id of the followed agent. */
  view: string;
  hasBase: boolean;
  onFree: () => void;
  onBase: () => void;
  onAgent: (id: string) => void;
}

/**
 * Camera picker: the free map camera, one follow camera per agent (astronaut, rover, drone)
 * and a fixed view of the base. Only the camera moves; no pose or data is changed.
 */
export function CameraBar({ agents, view, hasBase, onFree, onBase, onAgent }: Props) {
  const sorted = [...agents].sort((a, b) => KIND_ORDER.indexOf(a.agent_kind) - KIND_ORDER.indexOf(b.agent_kind));
  const many = (kind: AgentState['agent_kind']) => agents.filter((a) => a.agent_kind === kind).length > 1;
  return (
    <div className="camera-bar" role="group" aria-label="Camera">
      <span className="camera-bar__label">Camera</span>
      <button type="button" className="chip" aria-pressed={view === 'free'} onClick={onFree}>
        Map
      </button>
      {sorted.map((a) => (
        <button key={a.agent_id} type="button" className="chip" aria-pressed={view === a.agent_id} onClick={() => onAgent(a.agent_id)}>
          {KIND_LABEL[a.agent_kind]}
          {many(a.agent_kind) ? ` ${a.agent_id}` : ''}
        </button>
      ))}
      {hasBase && (
        <button type="button" className="chip" aria-pressed={view === 'base'} onClick={onBase}>
          Base
        </button>
      )}
      <span className="camera-bar__rotate" role="group" aria-label="Rotate the view">
        <button type="button" className="chip" title="Rotate the view left (Q). Also: right drag or Shift + drag." aria-label="Rotate view left" onClick={() => rotateView(-ROTATE_STEP_RAD)}>
          <kbd>Q</kbd> ⟲
        </button>
        <button type="button" className="chip" title="Rotate the view right (E). Also: right drag or Shift + drag." aria-label="Rotate view right" onClick={() => rotateView(ROTATE_STEP_RAD)}>
          ⟳ <kbd>E</kbd>
        </button>
      </span>
    </div>
  );
}
