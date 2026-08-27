import test from "node:test";
import assert from "node:assert/strict";
import { validateRepository } from "../scripts/validate-repository.mjs";

test("tracked machine packages are internally consistent", async () => {
  const result = await validateRepository();
  assert.deepEqual(result.errors, []);
  assert.equal(result.summary.machines, 3);
  assert.ok(result.summary.sources >= 5);
  assert.ok(result.summary.facts >= 30);
});

test("private official sources match the frozen hashes when present", async () => {
  const result = await validateRepository({ requirePrivateSources: true });
  assert.deepEqual(result.errors, []);
  assert.equal(result.summary.private_sources_checked, 3);
});
