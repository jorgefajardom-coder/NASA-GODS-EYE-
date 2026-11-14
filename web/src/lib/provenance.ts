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
  if (input.mode === "REPLAY") return { state: "REPLAY", label: input.source === "MOCK" ? "REPLAY · MOCK" : "REPLAY" };
  if (input.source === "MOCK") return { state: "MOCK", label: "MOCK" };
  if (input.source === "SIMULATION") return { state: "MOCK", label: "SIMULATION · NOT VALIDATED LIVE" };
  return input.source === "REAL" && input.validatedLive === true
    ? { state: "LIVE", label: "LIVE" } : { state: "NOT_READY", label: "NOT_READY" };
}
