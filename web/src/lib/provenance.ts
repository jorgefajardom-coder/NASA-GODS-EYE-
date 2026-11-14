/** Display semantics shared by future live/replay adapters. No availability inference. */
export type DisplayState = "LIVE" | "REPLAY" | "MOCK" | "NOT_READY" | "ERROR";
export interface SourceState {
  mode: "LIVE" | "REPLAY" | null;
  status?: "NOT_READY" | "ERROR" | "OK";
  source: "REAL" | "SIMULATION" | "MOCK" | "UNKNOWN";
  validatedLive?: boolean;
}
export function displayState(input: SourceState): { state: DisplayState; label: string } {
  if (input.status === "ERROR") return { state: "ERROR", label: "ERROR" };
  if (input.status === "NOT_READY" || (input.mode !== "LIVE" && input.mode !== "REPLAY")) return { state: "NOT_READY", label: "NOT_READY" };
  // ICD §7: a recording shows REPLAY plus who produced it (REPLAY · MOCK, REPLAY · SIMULATION, REPLAY · UNKNOWN).
  if (input.mode === "REPLAY") return { state: "REPLAY", label: input.source === "REAL" ? "REPLAY" : `REPLAY · ${input.source}` };
  if (input.source === "MOCK") return { state: "MOCK", label: "MOCK" };
  if (input.source === "SIMULATION") return { state: "MOCK", label: "SIMULATION · NOT VALIDATED LIVE" };
  return input.source === "REAL" && input.validatedLive === true
    ? { state: "LIVE", label: "LIVE" } : { state: "NOT_READY", label: "NOT_READY" };
}

/**
 * Who produced the data of a run (docs/ICD.md §6.1, gateway `source_mode`). Separate from
 * `mode`, which only says whether data arrives now or was recorded. LIVE is reserved for a
 * validated real source and can never be declared by a package or manifest.
 */
export type SourceMode = "MOCK" | "SIMULATION" | "UNKNOWN";
export const DECLARABLE_SOURCE_MODES: readonly SourceMode[] = ["MOCK", "SIMULATION", "UNKNOWN"];

/** True if the terrain metadata itself says the data is a MOCK (same rule as the gateway's mock_evidence). */
export function mockEvidence(meta: { dataset_id?: string; sources?: readonly string[] } | null | undefined): boolean {
  return !!meta && (String(meta.dataset_id ?? "").startsWith("MOCK") || (meta.sources ?? []).some((s) => String(s).includes("MOCK")));
}

/**
 * Resolves the source of a run as the ICD requires: MOCK terrain evidence always yields MOCK,
 * a missing field is UNKNOWN, and anything that is not a declarable mode (LIVE included) is
 * rejected with `null` so the caller refuses the package instead of guessing.
 */
export function resolveSourceMode(declared: unknown, meta?: Parameters<typeof mockEvidence>[0]): SourceMode | null {
  if (declared !== undefined && declared !== null && !DECLARABLE_SOURCE_MODES.includes(declared as SourceMode)) return null;
  if (mockEvidence(meta)) return "MOCK";
  return (declared as SourceMode | undefined | null) ?? "UNKNOWN";
}
