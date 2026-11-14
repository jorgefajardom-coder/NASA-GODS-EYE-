/**
 * z-index range of the 3D labels (drei Html). Kept at or below 1 so the interface panels
 * (overlay at z-index 2) always cover them: a label must never sit over a panel or the HUD.
 */
export const LABEL_Z: [number, number] = [1, 0];
