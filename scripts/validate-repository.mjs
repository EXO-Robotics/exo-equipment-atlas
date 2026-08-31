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
const SOURCE_ADMISSIONS = new Set(["primary", "reference_only", "visual_only", "quarantined"]);
const BUILT_RELEASE_STATE = "technical_structural_study_built_solver_unverified";

async function readJson(relativePath) {
  const absolutePath = path.join(ROOT, relativePath);
  return JSON.parse(await readFile(absolutePath, "utf8"));
}

async function sha256(relativePath) {
  const buffer = await readFile(path.join(ROOT, relativePath));
  return createHash("sha256").update(buffer).digest("hex");
}

export function validateViewerMechanismBindings({ machineId = "test-machine", viewer, mechanism }) {
  const errors = [];
  const jointsById = new Map();
  for (const joint of mechanism?.joints ?? []) {
    if (jointsById.has(joint.id)) errors.push(`${machineId}: duplicate mechanism joint ID ${joint.id}`);
    jointsById.set(joint.id, joint);
  }
  for (const channel of viewer?.motion?.channels ?? []) {
    const joint = jointsById.get(channel.mechanismJointId);
    if (!joint) {
      errors.push(
        `${machineId}/${channel.id ?? "motion-channel"}: unknown mechanismJointId ` +
        `${channel.mechanismJointId ?? "missing"}`
      );
      continue;
    }
    const channelAxis = channel.property?.split(".")[1]?.toUpperCase();
    const declaredAxis = typeof joint.axis === "string" ? joint.axis.match(/[+-]?([XYZ])(?:\b|\/)/u)?.[1] : null;
    if (declaredAxis && channelAxis && declaredAxis !== channelAxis) {
      errors.push(
        `${machineId}/${channel.id}: viewer ${channel.property} axis conflicts with ` +
        `mechanism joint ${joint.id} axis ${joint.axis}`
      );
    }
  }
  return errors;
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
    let viewer;
    let design = null;
    try {
      [configuration, manifest, facts, mechanism, viewer] = await Promise.all([
        readJson(`${base}/configuration.json`),
        readJson(`${base}/evidence/source-manifest.json`),
        readJson(`${base}/evidence/facts.json`),
        readJson(`${base}/mechanism.json`),
        readJson(`${base}/viewer.json`)
      ]);
      try {
        design = await readJson(`${base}/source/design.json`);
      } catch (error) {
        if (error?.code !== "ENOENT") throw error;
      }
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
    if (viewer.schema_version !== "1.0.0" || viewer.machineId !== machineId) {
      errors.push(`${machineId}: viewer identity or schema drift`);
    }
    if (design && (
      design.schema_version !== "1.0.0" ||
      design.machine_id !== machineId ||
      design.configuration_id !== configuration.configuration_id
    )) {
      errors.push(`${machineId}: source design identity or schema drift`);
    }
    if (entry.configuration_status !== configuration.status) {
      errors.push(`${machineId}: catalog configuration_status does not match configuration.json`);
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

    if (!Array.isArray(manifest.sources) || manifest.sources.length === 0) {
      errors.push(`${machineId}: source manifest must contain at least one source`);
    }
    const sourceIds = new Set();
    for (const source of manifest.sources ?? []) {
      sourceCount += 1;
      if (!source.id || sourceIds.has(source.id)) errors.push(`${machineId}: duplicate or empty source id`);
      sourceIds.add(source.id);
      if (!source.publisher || !source.kind || !source.title || !source.official_url || !source.admission) {
        errors.push(`${machineId}/${source.id}: incomplete source identity`);
      }
      if (!/^https:\/\//u.test(source.official_url ?? "")) {
        errors.push(`${machineId}/${source.id}: official_url must use HTTPS`);
      }
      if (!SOURCE_ADMISSIONS.has(source.admission)) {
        errors.push(`${machineId}/${source.id}: invalid source admission ${source.admission}`);
      }
      if (source.local_path) {
        privateSourceDeclaredCount += 1;
        const expectedPrefix = `research/private/${machineId}/`;
        const localPathIsSafe =
          source.local_path.startsWith(expectedPrefix) &&
          !source.local_path.split("/").includes("..") &&
          !path.isAbsolute(source.local_path);
        if (!localPathIsSafe) {
          errors.push(`${machineId}/${source.id}: local source path must stay under ${expectedPrefix}`);
        }
        if (!/^[a-f0-9]{64}$/u.test(source.sha256 ?? "") || !Number.isInteger(source.bytes) || source.bytes <= 0) {
          errors.push(`${machineId}/${source.id}: local source requires SHA-256 and positive byte count`);
        }
        if (!localPathIsSafe) continue;
        try {
          const sourceStat = await stat(path.join(ROOT, source.local_path));
          if (sourceStat.size !== source.bytes) errors.push(`${machineId}/${source.id}: byte count mismatch`);
          const digest = await sha256(source.local_path);
          if (digest !== source.sha256) errors.push(`${machineId}/${source.id}: SHA-256 mismatch`);
          if (source.local_path.toLowerCase().endsWith(".pdf") && (!Number.isInteger(source.pages) || source.pages <= 0)) {
            errors.push(`${machineId}/${source.id}: local PDF must declare a positive physical page count`);
          }
          privateSourceCheckedCount += 1;
        } catch (error) {
          const message = `${machineId}/${source.id}: private source unavailable (${source.local_path})`;
          if (requirePrivateSources) errors.push(message);
          else warnings.push(message);
        }
      }
    }

    if (!Array.isArray(facts.facts) || facts.facts.length === 0) {
      errors.push(`${machineId}: facts document must contain at least one fact`);
    }
    const factIds = new Set();
    const factsById = new Map();
    for (const fact of facts.facts ?? []) {
      factCount += 1;
      if (!fact.id || factIds.has(fact.id)) errors.push(`${machineId}: duplicate or empty fact id`);
      factIds.add(fact.id);
      factsById.set(fact.id, fact);
      if (!sourceIds.has(fact.source_id)) errors.push(`${machineId}/${fact.id}: unknown source_id ${fact.source_id}`);
      if (!AUTHORITY_CLASSES.has(fact.authority)) errors.push(`${machineId}/${fact.id}: invalid authority ${fact.authority}`);
      if (fact.value === null || fact.value === undefined || !fact.unit || !fact.location) {
        errors.push(`${machineId}/${fact.id}: incomplete fact value, unit, or location`);
      }
    }

    const technicalFactIds = new Set();
    for (const rule of Object.values(entry.public_envelope ?? {})) {
      if (typeof rule?.factId === "string") technicalFactIds.add(rule.factId);
    }
    for (const factId of viewer.evidence?.factIds ?? []) technicalFactIds.add(factId);
    for (const factId of design?.published_constraints_used ?? []) technicalFactIds.add(factId);
    for (const factId of technicalFactIds) {
      const fact = factsById.get(factId);
      if (!fact) {
        errors.push(`${machineId}/${factId}: public or geometry fact is missing`);
        continue;
      }
      if (fact.authority !== "manufacturer_published") {
        errors.push(`${machineId}/${factId}: public or geometry fact must be manufacturer_published`);
      }
      const source = (manifest.sources ?? []).find((item) => item.id === fact.source_id);
      if (
        !source || source.admission !== "primary" ||
        typeof source.local_path !== "string" || !/^[a-f0-9]{64}$/u.test(source.sha256 ?? "") ||
        !Number.isInteger(source.bytes) || source.bytes <= 0
      ) {
        errors.push(`${machineId}/${factId}: public or geometry fact requires a hash-bound local primary source`);
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
    errors.push(...validateViewerMechanismBindings({ machineId, viewer, mechanism }));
    if (!(mechanism.required_gates?.length > 0)) errors.push(`${machineId}: missing machine-specific gates`);
    if (mechanism.release_state !== BUILT_RELEASE_STATE) {
      errors.push(`${machineId}: mechanism release_state must be ${BUILT_RELEASE_STATE}`);
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
