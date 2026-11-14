import assert from "node:assert/strict";
import test from "node:test";
import { enuToThree } from "./frames.ts";
import { isCurrentRoute } from "./contracts.ts";

test("ENU control points retain east and altitude while north becomes negative Z", () => {
  assert.deepEqual(enuToThree({ x: 10, y: 20, z: 3 }), [10, 3, -20]);
  assert.deepEqual(enuToThree({ x: 0, y: -5, z: 0 }), [0, 0, 5]);
  assert.throws(() => enuToThree({ x: NaN, y: 0, z: 0 }));
});

test("a route for an earlier map must not be shown as current", () => {
  assert.equal(isCurrentRoute(2, 3), false);
  assert.equal(isCurrentRoute(3, 3), true);
  assert.equal(isCurrentRoute(-1, -1), false);
});
