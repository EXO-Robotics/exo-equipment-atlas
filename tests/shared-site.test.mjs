import test from "node:test";
import assert from "node:assert/strict";
import {
  MANUAL_OVERRIDE_MS,
  ManualOverrideClock,
  autoplayProgress,
  damp,
  dampingAlpha
} from "../assets/site/motion.js";

test("manual articulation override lasts exactly six seconds", () => {
  const hold = new ManualOverrideClock();
  assert.equal(MANUAL_OVERRIDE_MS, 6000);
  hold.hold(1250);
  assert.equal(hold.isActive(7249.999), true);
  assert.equal(hold.remainingMs(4250), 3000);
  assert.equal(hold.isActive(7250), false);
  assert.equal(hold.remainingMs(9000), 0);
});

test("motion damping is frame-rate independent", () => {
  const rate = 7;
  const oneFrame = damp(0, 1, rate, 1);
  let sixtyFrames = 0;
  for (let frame = 0; frame < 60; frame += 1) sixtyFrames = damp(sixtyFrames, 1, rate, 1 / 60);
  assert.ok(Math.abs(oneFrame - sixtyFrames) < 1e-12);
  assert.ok(dampingAlpha(rate, 0) === 0);
  assert.ok(oneFrame > 0.99 && oneFrame < 1);
});

test("sine and ping-pong autoplay remain normalized and phaseable", () => {
  for (const mode of ["sine", "ping-pong"]) {
    for (let step = -20; step <= 40; step += 1) {
      const value = autoplayProgress(step / 4, 8, 0.17, mode);
      assert.ok(value >= 0 && value <= 1, `${mode} returned ${value}`);
    }
  }
  assert.equal(autoplayProgress(0, 8, 0, "ping-pong"), 0);
  assert.equal(autoplayProgress(4, 8, 0, "ping-pong"), 1);
  assert.ok(Math.abs(autoplayProgress(2, 8, 0, "sine") - 0.5) < 1e-12);
});
