import test from "node:test";
import assert from "node:assert/strict";
import { validateRepository } from "../scripts/validate-repository.mjs";
import { validateProductionAssets } from "../scripts/validate-production-assets.mjs";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

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
  assert.ok(result.summary.renders >= 18);
  assert.ok(result.summary.glb_nodes >= 900);
  assert.ok(result.summary.glb_mesh_nodes > 0);
  assert.ok(result.summary.glb_triangles > 0);
  assert.deepEqual(Object.keys(result.summary.glb_contracts).sort(), [
    "cat-320",
    "john-deere-310-p-tier",
    "john-deere-333-p-tier"
  ]);
  for (const contract of Object.values(result.summary.glb_contracts)) {
    assert.ok(contract.root_name);
    assert.ok(contract.mesh_nodes > 0);
    assert.ok(Number.isInteger(contract.decoded_triangles) && contract.decoded_triangles > 0);
    assert.equal(contract.visible_bounds_m.size.length, 3);
    assert.ok(contract.visible_bounds_m.size.every((value) => Number.isFinite(value) && value > 0));
  }
});

test("static atlas entrypoint and Pages bundle validate", () => {
  const result = spawnSync(process.execPath, ["scripts/validate-site.mjs"], {
    cwd: new URL("..", import.meta.url),
    encoding: "utf8"
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
});

test("historical critic report cannot imply approval of current GLB bytes", async () => {
  const report = await readFile(new URL("../docs/CRITIC_REPORT_2026-08-27.md", import.meta.url), "utf8");
  assert.match(report, /^# Superseded overall critic report/m);
  assert.match(report, /Historical evidence only/);
  assert.match(report, /current artifacts remain `PENDING` for human critic review/i);

  for (const relativePath of [
    "../machines/cat-320/assets/cat-320-structural-study.glb",
    "../machines/john-deere-333-p-tier/assets/john-deere-333-p-tier-structural-study.glb",
    "../machines/john-deere-310-p-tier/assets/john-deere-310-p-tier-structural-study.glb"
  ]) {
    const bytes = await readFile(new URL(relativePath, import.meta.url));
    const digest = createHash("sha256").update(bytes).digest("hex");
    assert.match(report, new RegExp(digest));
  }
});
