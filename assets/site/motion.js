export const MANUAL_OVERRIDE_MS = 6000;

export function clamp01(value) {
  return Math.min(1, Math.max(0, Number.isFinite(value) ? value : 0));
}

export function dampingAlpha(ratePerSecond, deltaSeconds) {
  const rate = Math.max(0, Number.isFinite(ratePerSecond) ? ratePerSecond : 0);
  const delta = Math.max(0, Number.isFinite(deltaSeconds) ? deltaSeconds : 0);
  return 1 - Math.exp(-rate * delta);
}

export function damp(current, target, ratePerSecond, deltaSeconds) {
  return current + (target - current) * dampingAlpha(ratePerSecond, deltaSeconds);
}

export function autoplayProgress(elapsedSeconds, durationSeconds, phase = 0, mode = "sine") {
  const duration = Math.max(0.001, Number.isFinite(durationSeconds) ? durationSeconds : 8);
  const time = Number.isFinite(elapsedSeconds) ? elapsedSeconds : 0;
  const offset = Number.isFinite(phase) ? phase : 0;
  const cycle = ((time / duration + offset) % 1 + 1) % 1;

  if (mode === "ping-pong") return cycle < 0.5 ? cycle * 2 : (1 - cycle) * 2;
  return 0.5 - 0.5 * Math.cos(cycle * Math.PI * 2);
}

export class ManualOverrideClock {
  constructor(holdMs = MANUAL_OVERRIDE_MS) {
    this.holdMs = Math.max(0, holdMs);
    this.until = 0;
  }

  hold(nowMs) {
    const now = Number.isFinite(nowMs) ? nowMs : 0;
    this.until = now + this.holdMs;
    return this.until;
  }

  clear() {
    this.until = 0;
  }

  isActive(nowMs) {
    return (Number.isFinite(nowMs) ? nowMs : 0) < this.until;
  }

  remainingMs(nowMs) {
    return Math.max(0, this.until - (Number.isFinite(nowMs) ? nowMs : 0));
  }
}
