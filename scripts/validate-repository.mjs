import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const AUTHORITY_CLASSES = new Set([
  "manufacturer_published",
  "evidence_derived",
  "reconstructed",
  "observed",
  "unresolved"
]);

async function readJson(relativePath) {
  const absolutePath = path.join(ROOT, relativePath);
  return JSON.parse(await readFile(absolutePath, "utf8"));
}

async function sha256(relativePath) {
  const buffer = await readFile(path.join(ROOT, relativePath));
  return createHash("sha256").update(buffer).digest("hex");
}

export async function validateRepository({ requirePrivateSources = false } = {}) {
  const errors = [];
  const warnings = [];
  const catalog = await readJson("catalog.json");
  const seenMachines = new Set();
  let factCount = 0;
  let sourceCount = 0;
  let privateSourceDeclaredCount = 0;
  let privateSourceCheckedCount = 0;

  if (catalog.schema_version !== "1.0.0") errors.push("catalog: unsupported schema_version");
  if (!Array.isArray(catalog.machines) || catalog.machines.length === 0) errors.push("catalog: machines must be non-empty");

  for (const entry of catalog.machines ?? []) {
    const machineId = entry.id;
    if (!machineId || seenMachines.has(machineId)) {
      errors.push(`catalog: duplicate or empty machine id ${machineId ?? "<empty>"}`);
      continue;
    }
    seenMachines.add(machineId);

    const base = `machines/${machineId}`;
    let configuration;
    let manifest;
    let facts;
    let mechanism;
    try {
      [configuration, manifest, facts, mechanism] = await Promise.all([
        readJson(`${base}/configuration.json`),
        readJson(`${base}/evidence/source-manifest.json`),
        readJson(`${base}/evidence/facts.json`),
        readJson(`${base}/mechanism.json`)
      ]);
    } catch (error) {
      errors.push(`${machineId}: cannot load required package: ${error.message}`);
      continue;
    }

    const documents = [configuration, manifest, facts, mechanism];
    for (const document of documents) {
      if (document.schema_version !== "1.0.0") errors.push(`${machineId}: unsupported document schema`);
      if (document.machine_id !== machineId) errors.push(`${machineId}: machine_id drift`);
      if (document.configuration_id !== configuration.configuration_id) errors.push(`${machineId}: configuration_id drift`);
    }

    if (!configuration.identity || !configuration.choices || !configuration.boundary) {
      errors.push(`${machineId}: incomplete configuration identity or boundary`);
    }
    if (configuration.status === "research_candidate" && !(configuration.unresolved_choices?.length > 0)) {
      errors.push(`${machineId}: research candidate must preserve unresolved choices`);
    }
    if (configuration.status !== "frozen" && entry.release_status !== "not_started") {
      errors.push(`${machineId}: non-frozen configuration cannot advance release status`);
    }

    const sourceIds = new Set();
    for (const source of manifest.sources ?? []) {
      sourceCount += 1;
      if (!source.id || sourceIds.has(source.id)) errors.push(`${machineId}: duplicate or empty source id`);
      sourceIds.add(source.id);
      if (!source.publisher || !source.kind || !source.title || !source.official_url || !source.admission) {
        errors.push(`${machineId}/${source.id}: incomplete source identity`);
      }
      if (source.local_path) {
        privateSourceDeclaredCount += 1;
        try {
          const sourceStat = await stat(path.join(ROOT, source.local_path));
          if (sourceStat.size !== source.bytes) errors.push(`${machineId}/${source.id}: byte count mismatch`);
          const digest = await sha256(source.local_path);
          if (digest !== source.sha256) errors.push(`${machineId}/${source.id}: SHA-256 mismatch`);
          privateSourceCheckedCount += 1;
        } catch (error) {
          const message = `${machineId}/${source.id}: private source unavailable (${source.local_path})`;
          if (requirePrivateSources) errors.push(message);
          else warnings.push(message);
        }
      }
    }

    const factIds = new Set();
    for (const fact of facts.facts ?? []) {
      factCount += 1;
      if (!fact.id || factIds.has(fact.id)) errors.push(`${machineId}: duplicate or empty fact id`);
      factIds.add(fact.id);
      if (!sourceIds.has(fact.source_id)) errors.push(`${machineId}/${fact.id}: unknown source_id ${fact.source_id}`);
      if (!AUTHORITY_CLASSES.has(fact.authority)) errors.push(`${machineId}/${fact.id}: invalid authority ${fact.authority}`);
      if (fact.value === null || fact.value === undefined || !fact.unit || !fact.location) {
        errors.push(`${machineId}/${fact.id}: incomplete fact value, unit, or location`);
      }
    }

    if (!Array.isArray(mechanism.joints) || mechanism.joints.length === 0) {
      errors.push(`${machineId}: mechanism must declare joints`);
    }
    for (const joint of mechanism.joints ?? []) {
      if (!joint.id || !joint.type || !AUTHORITY_CLASSES.has(joint.authority)) {
        errors.push(`${machineId}: incomplete joint declaration`);
      }
      for (const sourceId of joint.source_ids ?? []) {
        if (!sourceIds.has(sourceId)) errors.push(`${machineId}/${joint.id}: unknown mechanism source ${sourceId}`);
      }
      if (joint.authority === "reconstructed" && !(joint.unresolved?.length > 0)) {
        errors.push(`${machineId}/${joint.id}: reconstruction must state unresolved geometry`);
      }
    }
    if (!(mechanism.required_gates?.length > 0)) errors.push(`${machineId}: missing machine-specific gates`);
    if (mechanism.release_state !== "no_geometry_no_solver_no_claim") {
      errors.push(`${machineId}: initial research package must not claim geometry or solver proof`);
    }
  }

  return {
    errors,
    warnings,
    summary: {
      machines: seenMachines.size,
      sources: sourceCount,
      private_sources_declared: privateSourceDeclaredCount,
      private_sources_checked: privateSourceCheckedCount,
      facts: factCount
    }
  };
}

const invokedDirectly = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedDirectly) {
  const result = await validateRepository({ requirePrivateSources: process.argv.includes("--require-private-sources") });
  for (const warning of result.warnings) console.warn(`WARN ${warning}`);
  for (const error of result.errors) console.error(`FAIL ${error}`);
  if (result.errors.length > 0) process.exitCode = 1;
  else console.log(`PASS ${result.summary.machines} machines, ${result.summary.sources} sources, ${result.summary.facts} facts, ${result.summary.private_sources_checked}/${result.summary.private_sources_declared} private source hashes checked`);
}
