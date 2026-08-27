import test from "node:test";
import assert from "node:assert/strict";
import { validateRepository } from "../scripts/validate-repository.mjs";
import { validateProductionAssets } from "../scripts/validate-production-assets.mjs";
import { spawnSync } from "node:child_process";

test("tracked machine packages are internally consistent", async () => {
  const result = await validateRepository();
  assert.deepEqual(result.errors, []);
  assert.equal(result.summary.machines, 3);
  assert.ok(result.summary.sources >= 5);
  assert.ok(result.summary.facts >= 30);
});

test("private official sources match the frozen hashes when present", async () => {
  const result = await validateRepository();
  assert.deepEqual(result.errors, []);
  assert.equal(result.summary.private_sources_declared, 3);
  assert.ok(result.summary.private_sources_checked >= 0);
  assert.ok(result.summary.private_sources_checked <= result.summary.private_sources_declared);
  assert.equal(
    result.warnings.length,
    result.summary.private_sources_declared - result.summary.private_sources_checked
  );
});

test("technical structural studies match their receipts and exported GLBs", async () => {
  const result = await validateProductionAssets();
  assert.deepEqual(result.errors, []);
  assert.equal(result.summary.machines, 3);
  assert.equal(result.summary.blends, 3);
  assert.equal(result.summary.glbs, 3);
  assert.equal(result.summary.renders, 18);
  assert.ok(result.summary.glb_nodes >= 900);
});

test("static atlas entrypoint and Pages bundle validate", () => {
  const result = spawnSync(process.execPath, ["scripts/validate-site.mjs"], {
    cwd: new URL("..", import.meta.url),
    encoding: "utf8"
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
});
