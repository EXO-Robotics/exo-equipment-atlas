#!/usr/bin/env node
import { createHash } from "node:crypto";
import { readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const bind = process.argv.includes("--bind");
const machinesRoot = path.join(ROOT, "machines");
const machineIds = (await readdir(machinesRoot, { withFileTypes: true }))
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .sort();

const changed = [];
const missing = [];
const verified = [];

for (const machineId of machineIds) {
  const manifestPath = path.join(machinesRoot, machineId, "evidence", "source-manifest.json");
  let manifest;
  try {
    manifest = JSON.parse(await readFile(manifestPath, "utf8"));
  } catch {
    continue;
  }
  let dirty = false;
  for (const source of manifest.sources ?? []) {
    if (!source.local_path) continue;
    const expectedPrefix = `research/private/${machineId}/`;
    if (
      typeof source.local_path !== "string" ||
      !source.local_path.startsWith(expectedPrefix) ||
      source.local_path.split("/").includes("..")
    ) {
      throw new Error(`${machineId}/${source.id}: unsafe private-source path`);
    }
    if (typeof source.official_url !== "string" || !source.official_url.startsWith("https://")) {
      throw new Error(`${machineId}/${source.id}: official_url must use HTTPS`);
    }
    const absolutePath = path.join(ROOT, source.local_path);
    let bytes;
    try {
      bytes = await readFile(absolutePath);
      await stat(absolutePath);
    } catch {
      missing.push({ machine_id: machineId, source_id: source.id, path: source.local_path });
      continue;
    }
    const sha256 = createHash("sha256").update(bytes).digest("hex");
    verified.push({ machine_id: machineId, source_id: source.id, path: source.local_path, sha256, bytes: bytes.length });
    if (source.sha256 !== sha256 || source.bytes !== bytes.length) {
      if (bind) {
        source.sha256 = sha256;
        source.bytes = bytes.length;
        dirty = true;
      } else {
        changed.push({ machine_id: machineId, source_id: source.id, path: source.local_path, sha256, bytes: bytes.length });
      }
    }
  }
  if (dirty) {
    await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
    changed.push({ machine_id: machineId, manifest: path.relative(ROOT, manifestPath) });
  }
}

console.log(JSON.stringify({
  status: missing.length === 0 && (bind || changed.length === 0) ? "PASS" : "PENDING",
  mode: bind ? "bind" : "check",
  verified_sources: verified.length,
  changed,
  missing
}, null, 2));

if (!bind && changed.length > 0) process.exitCode = 1;
