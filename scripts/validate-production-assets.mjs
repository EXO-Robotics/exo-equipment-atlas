import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const VALID_GATE_STATUSES = new Set(["PASS", "FAIL", "PENDING"]);

async function readJson(absolutePath) {
  return JSON.parse(await readFile(absolutePath, "utf8"));
}

async function sha256(absolutePath) {
  return createHash("sha256").update(await readFile(absolutePath)).digest("hex");
}

function resolveDeclaredPath(machineBase, declaredPath) {
  if (!declaredPath) return null;
  return declaredPath.startsWith("machines/")
    ? path.join(ROOT, declaredPath)
    : path.join(machineBase, declaredPath);
}

async function verifyDeclaredFile({ errors, machineId, machineBase, label, entry }) {
  if (!entry?.path || !entry?.sha256 || !Number.isInteger(entry?.bytes)) {
    errors.push(`${machineId}/${label}: incomplete path, SHA-256, or byte declaration`);
    return null;
  }
  const absolutePath = resolveDeclaredPath(machineBase, entry.path);
  try {
    const fileStat = await stat(absolutePath);
    if (fileStat.size !== entry.bytes) {
      errors.push(`${machineId}/${label}: byte mismatch (${fileStat.size} != ${entry.bytes})`);
    }
    const digest = await sha256(absolutePath);
    if (digest !== entry.sha256) {
      errors.push(`${machineId}/${label}: SHA-256 mismatch`);
    }
    return absolutePath;
  } catch (error) {
    errors.push(`${machineId}/${label}: unavailable (${error.message})`);
    return null;
  }
}

function parseGlb(buffer) {
  if (buffer.length < 20 || buffer.toString("ascii", 0, 4) !== "glTF") {
    throw new Error("invalid GLB magic or truncated header");
  }
  const version = buffer.readUInt32LE(4);
  const declaredLength = buffer.readUInt32LE(8);
  if (version !== 2) throw new Error(`unsupported GLB version ${version}`);
  if (declaredLength !== buffer.length) {
    throw new Error(`GLB length mismatch (${declaredLength} != ${buffer.length})`);
  }
  const jsonChunkLength = buffer.readUInt32LE(12);
  const jsonChunkType = buffer.readUInt32LE(16);
  if (jsonChunkType !== 0x4e4f534a) throw new Error("first GLB chunk is not JSON");
  const jsonEnd = 20 + jsonChunkLength;
  if (jsonEnd > buffer.length) throw new Error("GLB JSON chunk exceeds file length");
  return JSON.parse(buffer.toString("utf8", 20, jsonEnd).replace(/\u0000+$/u, "").trimEnd());
}

function builderEntry(receipt) {
  if (receipt.builder?.path) return receipt.builder;
  if (receipt.deterministic_builder?.path) return receipt.deterministic_builder;
  if (receipt.blender?.builder_path) {
    return {
      path: receipt.blender.builder_path,
      sha256: receipt.blender.builder_sha256,
      bytes: receipt.blender.builder_bytes
    };
  }
  return null;
}

function sceneSemanticNodes(receipt) {
  return receipt.required_semantic_nodes ?? receipt.semantic_nodes ?? {};
}

export async function validateProductionAssets() {
  const errors = [];
  const warnings = [];
  const catalog = await readJson(path.join(ROOT, "catalog.json"));
  const summary = { machines: 0, blends: 0, glbs: 0, renders: 0, glb_nodes: 0 };

  for (const machine of catalog.machines ?? []) {
    const machineId = machine.id;
    const machineBase = path.join(ROOT, "machines", machineId);
    const receiptPath = path.join(machineBase, "production", "asset-receipt.json");
    const validationPath = path.join(machineBase, "production", "validation.json");
    let configuration;
    let receipt;
    let validation;
    try {
      [configuration, receipt, validation] = await Promise.all([
        readJson(path.join(machineBase, "configuration.json")),
        readJson(receiptPath),
        readJson(validationPath)
      ]);
    } catch (error) {
      errors.push(`${machineId}: production package unavailable (${error.message})`);
      continue;
    }

    summary.machines += 1;
    if (receipt.machine_id !== machineId || validation.machine_id !== machineId) {
      errors.push(`${machineId}: machine identity drift in production documents`);
    }
    if (
      receipt.configuration_id !== configuration.configuration_id ||
      validation.configuration_id !== configuration.configuration_id
    ) {
      errors.push(`${machineId}: configuration identity drift in production documents`);
    }
    if (configuration.status !== "research_candidate") {
      errors.push(`${machineId}: initial study validator expects research_candidate status`);
    }
    if (receipt.candidate_class !== "technical_structural_study" || validation.candidate_class !== "technical_structural_study") {
      errors.push(`${machineId}: production output must remain a technical_structural_study`);
    }

    const builder = builderEntry(receipt);
    if (!builder?.path || !builder?.sha256) {
      errors.push(`${machineId}/builder: missing deterministic builder path or SHA-256`);
    } else {
      const absoluteBuilder = resolveDeclaredPath(machineBase, builder.path);
      try {
        if (await sha256(absoluteBuilder) !== builder.sha256) {
          errors.push(`${machineId}/builder: SHA-256 mismatch`);
        }
      } catch (error) {
        errors.push(`${machineId}/builder: unavailable (${error.message})`);
      }
    }

    const blendPath = await verifyDeclaredFile({
      errors,
      machineId,
      machineBase,
      label: "blend",
      entry: receipt.artifacts?.blend
    });
    if (blendPath) summary.blends += 1;

    const glbPath = await verifyDeclaredFile({
      errors,
      machineId,
      machineBase,
      label: "glb",
      entry: receipt.artifacts?.glb
    });
    if (glbPath) {
      summary.glbs += 1;
      try {
        const gltf = parseGlb(await readFile(glbPath));
        const nodeNames = new Set((gltf.nodes ?? []).map((node) => node.name).filter(Boolean));
        summary.glb_nodes += gltf.nodes?.length ?? 0;
        for (const [nodeName, claimedPresent] of Object.entries(sceneSemanticNodes(receipt))) {
          if (claimedPresent === true && !nodeNames.has(nodeName)) {
            errors.push(`${machineId}/glb: claimed semantic node missing from export (${nodeName})`);
          }
        }
        if ((gltf.images?.length ?? 0) > 0 || (gltf.textures?.length ?? 0) > 0) {
          errors.push(`${machineId}/glb: embedded images or textures violate the neutral structural-study boundary`);
        }
        if (!(gltf.scenes?.length > 0) || !(gltf.nodes?.length > 0) || !(gltf.meshes?.length > 0)) {
          errors.push(`${machineId}/glb: missing scenes, nodes, or meshes`);
        }
      } catch (error) {
        errors.push(`${machineId}/glb: ${error.message}`);
      }
    }

    if (!Array.isArray(receipt.renders) || receipt.renders.length < 4) {
      errors.push(`${machineId}: at least four hashed review renders are required`);
    }
    for (const [index, render] of (receipt.renders ?? []).entries()) {
      const renderPath = await verifyDeclaredFile({
        errors,
        machineId,
        machineBase,
        label: `render-${index + 1}`,
        entry: render
      });
      if (renderPath) summary.renders += 1;
    }

    if (!Array.isArray(validation.gates) || validation.gates.length === 0) {
      errors.push(`${machineId}: validation gates are missing`);
      continue;
    }
    const failed = [];
    for (const gate of validation.gates) {
      if (!gate.id || !VALID_GATE_STATUSES.has(gate.status)) {
        errors.push(`${machineId}: invalid production gate declaration`);
      }
      if (gate.status === "FAIL") failed.push(gate.id);
    }
    if (failed.length > 0 || validation.verdict !== "PASS") {
      errors.push(`${machineId}: technical-study validation is not PASS (${failed.join(", ") || validation.verdict})`);
    }
    if (!validation.gates.some((gate) => gate.status === "PENDING")) {
      warnings.push(`${machineId}: no higher-stage PENDING gates were preserved`);
    }
  }

  return { errors, warnings, summary };
}

const invokedDirectly = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invokedDirectly) {
  const result = await validateProductionAssets();
  for (const warning of result.warnings) console.warn(`WARN ${warning}`);
  for (const error of result.errors) console.error(`FAIL ${error}`);
  if (result.errors.length > 0) process.exitCode = 1;
  else {
    console.log(
      `PASS ${result.summary.machines} production studies, ${result.summary.blends} blends, ` +
        `${result.summary.glbs} GLBs, ${result.summary.renders} renders, ${result.summary.glb_nodes} GLB nodes`
    );
  }
}
