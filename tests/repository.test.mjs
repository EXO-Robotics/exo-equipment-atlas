import test from "node:test";
import assert from "node:assert/strict";
import { validateRepository } from "../scripts/validate-repository.mjs";
import {
  PRODUCTION_STUDY_MINIMUMS,
  validatePublicEnvelopeContract,
  validateProductionAssets
} from "../scripts/validate-production-assets.mjs";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";

const catalog = JSON.parse(await readFile(new URL("../catalog.json", import.meta.url), "utf8"));
const catalogIds = (catalog.machines ?? []).map(({ id }) => id).sort();

test("tracked machine packages are internally consistent", async () => {
  const result = await validateRepository();
  assert.deepEqual(result.errors, []);
  assert.equal(result.summary.machines, catalogIds.length);
  assert.ok(result.summary.sources >= catalogIds.length);
  assert.ok(result.summary.facts >= catalogIds.length * 4);
});

test("private official sources match the frozen hashes when present", async () => {
  const result = await validateRepository();
  assert.deepEqual(result.errors, []);
  assert.ok(result.summary.private_sources_checked >= 0);
  assert.ok(result.summary.private_sources_checked <= result.summary.private_sources_declared);
  assert.equal(
    result.warnings.length,
    result.summary.private_sources_declared - result.summary.private_sources_checked
  );
});

test("every catalog machine declares a hash-bound private official source", async () => {
  for (const machineId of catalogIds) {
    const manifest = JSON.parse(
      await readFile(new URL(`../machines/${machineId}/evidence/source-manifest.json`, import.meta.url), "utf8")
    );
    const declarations = (manifest.sources ?? []).filter((source) =>
      typeof source.publisher === "string" && source.publisher.length > 0 &&
      typeof source.official_url === "string" && /^https:\/\//u.test(source.official_url) &&
      typeof source.local_path === "string" && source.local_path.startsWith(`research/private/${machineId}/`) &&
      !source.local_path.split("/").includes("..") &&
      /^[a-f0-9]{64}$/u.test(source.sha256 ?? "") &&
      Number.isInteger(source.bytes) && source.bytes > 0 &&
      source.admission === "primary"
    );
    assert.ok(
      declarations.length > 0,
      `${machineId} must declare at least one official private source with canonical local_path, SHA-256, and byte count`
    );
  }
});

test("public-envelope declarations fail closed and admit only explicit partial coverage", () => {
  const facts = {
    facts: [
      { id: "published-length", authority: "manufacturer_published", unit: "m", value: 5 },
      { id: "reconstructed-width", authority: "reconstructed", unit: "m", value: 2 }
    ]
  };
  const validate = (machineEntry) => validatePublicEnvelopeContract({
    machineId: "fixture",
    machineEntry,
    facts,
    measuredSize: [5, 3, 2]
  });

  assert.ok(validate({ public_envelope: [] }).length > 0);
  assert.ok(validate({ public_envelope: {} }).length > 0);
  assert.deepEqual(
    validate({
      public_envelope: {},
      public_envelope_coverage: "unresolved",
      public_envelope_reason: "No configuration-applicable first-party overall dimension is frozen."
    }),
    []
  );
  assert.ok(validate({ public_envelope: { q: { factId: "published-length", toleranceM: 0 } } }).length > 0);
  assert.ok(validate({ public_envelope: { x: { factId: "published-length", toleranceM: -1 } } }).length > 0);
  assert.ok(validate({ public_envelope: { z: { factId: "reconstructed-width", toleranceM: 0 } }, public_envelope_coverage: "partial" }).length > 0);
  assert.deepEqual(
    validate({
      public_envelope_coverage: "partial",
      public_envelope: { x: { factId: "published-length", toleranceM: 0 } }
    }),
    []
  );
});

test("technical structural studies match their receipts and exported GLBs", async () => {
  const result = await validateProductionAssets();
  assert.deepEqual(result.errors, []);
  assert.equal(result.summary.machines, catalogIds.length);
  assert.equal(result.summary.blends, catalogIds.length);
  assert.equal(result.summary.glbs, catalogIds.length);
  assert.ok(result.summary.renders >= catalogIds.length * PRODUCTION_STUDY_MINIMUMS.review_renders);
  assert.ok(result.summary.glb_nodes >= catalogIds.length);
  assert.ok(result.summary.glb_mesh_nodes > 0);
  assert.ok(result.summary.glb_triangles > 0);
  assert.ok(result.summary.motion_samples >= catalogIds.length * 39);
  assert.deepEqual(Object.keys(result.summary.glb_contracts).sort(), catalogIds);
  for (const contract of Object.values(result.summary.glb_contracts)) {
    assert.ok(contract.root_name);
    assert.ok(contract.nodes >= PRODUCTION_STUDY_MINIMUMS.nodes);
    assert.ok(contract.mesh_nodes >= PRODUCTION_STUDY_MINIMUMS.mesh_nodes);
    assert.ok(
      Number.isInteger(contract.unique_decoded_triangles) &&
      contract.unique_decoded_triangles >= PRODUCTION_STUDY_MINIMUMS.decoded_triangles
    );
    assert.ok(contract.review_renders >= PRODUCTION_STUDY_MINIMUMS.review_renders);
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
