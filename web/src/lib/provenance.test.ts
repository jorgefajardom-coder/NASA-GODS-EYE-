import test from "node:test";
import assert from "node:assert/strict";
import { displayState } from "./provenance.ts";

test("replay and mock provenance never become LIVE", () => {
  assert.equal(displayState({ mode: "REPLAY", source: "MOCK" }).label, "REPLAY · MOCK");
  assert.equal(displayState({ mode: "LIVE", source: "MOCK" }).state, "MOCK");
  assert.equal(displayState({ mode: "LIVE", source: "SIMULATION" }).label, "SIMULATION · NOT VALIDATED LIVE");
  assert.equal(displayState({ mode: "LIVE", source: "REAL" }).state, "NOT_READY");
  assert.equal(displayState({ mode: "LIVE", source: "REAL", validatedLive: true }).state, "LIVE");
  assert.equal(displayState({ mode: null, source: "REAL" }).state, "NOT_READY");
  assert.equal(displayState({ mode: "REPLAY", source: "REAL", status: "ERROR" }).state, "ERROR");
});

test("external malformed mode cannot claim LIVE", () => {
  for (const mode of [undefined, "MOCK", "invalid", 1]) {
    assert.equal(displayState({ mode, source: "REAL", validatedLive: true } as unknown as Parameters<typeof displayState>[0]).state, "NOT_READY");
  }
});
