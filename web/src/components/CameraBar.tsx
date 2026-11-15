import type { AgentState } from '../types/icd';
import { ORBITAL_PREVIEW_LABEL, ORBITAL_PREVIEW_LIMIT } from '../lib/terrainPresentation';
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
  /** First or third person while an agent is followed. */
  firstPerson: boolean;
  onFirstPerson: (on: boolean) => void;
  canScan: boolean;
  onScan: () => void;
  /** Astronaut helmet lights (L). */
  helmetLight?: boolean;
  /** Terrain lit as by day whatever the hour (I). */
  artificialLight?: boolean;
  onArtificialLight?: () => void;
  canHelmetLight?: boolean;
  onHelmetLight?: () => void;
}

/**
 * Camera picker: the free map camera, one follow camera per agent (astronaut, rover, drone)
 * and a fixed view of the base. Only the camera moves; no pose or data is changed.
 */
export function CameraBar({ agents, view, hasBase, onFree, onBase, onAgent, firstPerson, onFirstPerson, canScan, onScan, helmetLight = false, canHelmetLight = false, onHelmetLight, artificialLight = true, onArtificialLight }: Props) {
  const following = view !== 'free' && view !== 'base';
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
      <button
        type="button"
        className="chip"
        aria-pressed={following && firstPerson}
        disabled={!following}
        title={following ? 'Switch between the over-the-shoulder view and the agent’s own eyes (V)' : 'Follow an agent first (Astronaut, Rover or Drone)'}
        onClick={() => onFirstPerson(!firstPerson)}
      >
        <kbd>V</kbd> {following && firstPerson ? '1st person' : '3rd person'}
      </button>
      <button type="button" className="chip" disabled={!canScan} title={canScan ? `${ORBITAL_PREVIEW_LABEL} at the drone position (R). ${ORBITAL_PREVIEW_LIMIT}` : 'No drone in this run'} onClick={onScan}>
        <kbd>R</kbd> {ORBITAL_PREVIEW_LABEL}
      </button>
      <button type="button" className="chip" aria-pressed={helmetLight} disabled={!canHelmetLight} title={canHelmetLight ? "Astronaut's helmet lights (L). Display only." : 'No astronaut in this run'} onClick={onHelmetLight}>
        <kbd>L</kbd> Lights
      </button>
      <button
        type="button"
        className="chip"
        aria-pressed={!artificialLight}
        disabled={!onArtificialLight}
        title={artificialLight ? 'Artificial light is on (terrain lit as by day). Show the terrain with the real light of the hour at the site (I).' : 'Real light of the hour at the site. Switch back to artificial light (I). Display only.'}
        onClick={onArtificialLight}
      >
        <kbd>I</kbd> {artificialLight ? 'Real light' : 'Artificial light'}
      </button>
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
