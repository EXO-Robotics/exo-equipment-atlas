import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const FIXTURE = path.join(ROOT, "scripts", "fleet", "fixtures", "minimal-wheeled-tractor.json");

test("fleet batch dry-run emits the exact factory-startup Blender plan", () => {
  const result = spawnSync("python3", [
    "-B", "scripts/fleet/batch_build.py",
    "--design", FIXTURE,
    "--output-root", "/tmp/fleet-builder-dry-run-test",
    "--dry-run", "--json"
  ], { cwd: ROOT, encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  const summary = JSON.parse(result.stdout);
  assert.equal(summary.status, "PASS");
  assert.equal(summary.dry_run, true);
  assert.equal(summary.builds.length, 1);
  const command = summary.builds[0].command;
  assert.ok(command.includes("--factory-startup"));
  assert.ok(command.includes("--background"));
  assert.ok(command.some((value) => value.endsWith(path.join("scripts", "fleet", "build_machine.py"))));
  assert.ok(command.includes(FIXTURE));
});

test("shared builder preserves explicit evidence and export boundaries", async () => {
  const source = await readFile(path.join(ROOT, "scripts", "fleet", "build_machine.py"), "utf8");
  assert.match(source, /ROOT_NAME = "Machine_Root"/u);
  assert.match(source, /export_yup=False/u);
  assert.match(source, /export_cameras=False/u);
  assert.match(source, /export_lights=False/u);
  assert.match(source, /"release_status":"PENDING"/u);
  assert.match(source, /HIDDEN_GEOMETRY_BOUNDARY/u);
  assert.match(source, /normalize_visible_envelope/u);
  assert.match(source, /verification-only/u);
  assert.match(source, /type\(self\) is not FleetBuilder/u);
  assert.match(source, /mechanism_required_gates/u);
  assert.match(source, /no independently measured machine-local proof was supplied/u);
  assert.doesNotMatch(source, /Service_Fastener_\{index \+ 1:03d\}/u);
  assert.doesNotMatch(source, /add_envelope_structure/u);
  assert.match(source, /"Articulation_Knuckle"/u);
  assert.match(source, /"Boom_Cylinder"[\s\S]+self\.materials\["steel"\],upper,role="hydraulic"/u);
});
