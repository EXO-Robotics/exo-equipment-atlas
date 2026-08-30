import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const VALIDATOR = path.join(ROOT, "scripts", "fleet", "validate_design.py");
const SCHEMA_PATH = path.join(ROOT, "scripts", "fleet", "design.schema.json");
const FIXTURE_PATH = path.join(ROOT, "scripts", "fleet", "fixtures", "minimal-wheeled-tractor.json");

const archetypes = [
  "wheeled_tractor",
  "tracked_tractor",
  "twin_track_tractor",
  "combine",
  "forage_harvester",
  "high_clearance_sprayer",
  "self_propelled_mower",
  "square_baler",
  "self_propelled_round_baler",
  "articulated_hauler",
  "excavator"
];

function validate(paths) {
  return spawnSync("python3", ["-B", VALIDATOR, ...paths, "--json"], {
    cwd: ROOT,
    encoding: "utf8"
  });
}

test("fleet design schema and pure-Python validator agree on every supported archetype", async () => {
  const schema = JSON.parse(await readFile(SCHEMA_PATH, "utf8"));
  assert.deepEqual(schema.properties.archetype.enum, archetypes);
  assert.equal(schema.properties.dimensions_m.properties.width.maximum, 60);

  const directory = await mkdtemp(path.join(os.tmpdir(), "fleet-builder-contract-"));
  const paths = [];
  for (const [index, archetype] of archetypes.entries()) {
    const design = {
      schema_version: "1.0.0",
      machine_id: `fleet-contract-${index + 1}`,
      display_name: `Fleet contract ${archetype}`,
      configuration_id: `FLEET-CONTRACT-${index + 1}-CANDIDATE`,
      archetype,
      dimensions_m: { length: 10, width: archetype === "high_clearance_sprayer" ? 36.6 : 4, height: 4 },
      carrier_dimensions_m: { length: 9, width: 3.5, height: 3.8 },
      attachment_span_m: archetype === "high_clearance_sprayer" ? 36.6 : 4,
      tracked_front: archetype === "combine",
      reconstructed_values: {},
      unresolved_choices: ["test fixture"],
      mechanical_gaps: ["test fixture"]
    };
    if (archetype === "articulated_hauler") design.tailgate = false;
    const designPath = path.join(directory, `${index + 1}.json`);
    await writeFile(designPath, `${JSON.stringify(design)}\n`);
    paths.push(designPath);
  }
  const result = validate(paths);
  assert.equal(result.status, 0, result.stderr || result.stdout);
  const summary = JSON.parse(result.stdout);
  assert.equal(summary.status, "PASS");
  assert.equal(summary.results.length, archetypes.length);
});

test("fleet design contract fails closed on unsupported or contradictory input", async () => {
  const valid = JSON.parse(await readFile(FIXTURE_PATH, "utf8"));
  const directory = await mkdtemp(path.join(os.tmpdir(), "fleet-builder-invalid-"));
  const invalid = [
    { ...valid, machine_id: "Not Kebab" },
    { ...valid, extra_untrusted_field: true },
    { ...valid, dimensions_m: { ...valid.dimensions_m, width: 61 } },
    { ...valid, tracked_front: true },
    { ...valid, carrier_dimensions_m: { length: 7, width: 2, height: 2 } }
  ];
  for (const [index, design] of invalid.entries()) {
    const designPath = path.join(directory, `${index}.json`);
    await writeFile(designPath, `${JSON.stringify(design)}\n`);
    const result = validate([designPath]);
    assert.notEqual(result.status, 0, `invalid fixture ${index} unexpectedly passed`);
    assert.equal(JSON.parse(result.stdout).status, "FAIL");
  }
});
