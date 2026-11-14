export type RouteStatus = "FEASIBLE" | "UNKNOWN" | "NO_PATH" | "INSUFFICIENT_BUDGET" | "STALE_MAP" | "ERROR";
export type MissionStatus = "IDLE" | "PLANNING" | "READY" | "ACTIVE" | "REPLAN" | "RETURNING" | "COMPLETE" | "BLOCKED" | "ABORTED";

/** ICD-WEB-V1. Null identifiers mean that no mission has been loaded. */
export interface RunEnvelope {
  schema_version: "1.0.0";
  run_id: string | null;
  mode: "LIVE" | "REPLAY" | null;
  map_version: number | null;
  timestamp_sim_s: number | null;
}

export interface UnavailableResponse extends RunEnvelope {
  status: "NOT_READY" | "ERROR";
  reason_code: string;
}

/** A display guard; this does not certify route safety or calculate a route. */
export function isCurrentRoute(routeVersion: number, mapVersion: number): boolean {
  return Number.isSafeInteger(routeVersion) && routeVersion >= 0 && routeVersion === mapVersion;
}
