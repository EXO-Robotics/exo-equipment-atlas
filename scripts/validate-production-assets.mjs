import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const VALID_GATE_STATUSES = new Set(["PASS", "FAIL", "PENDING"]);
const IDENTITY_EPSILON = 1e-7;
const RECEIPT_BOUNDS_TOLERANCE_M = 0.02;
const HELPER_NAME_PATTERN = /(?:^|[_-])(COL|COLLISION|HIT|INSP|INSPECT|WITNESS|ENVELOPE|HELPER|GUIDE)(?:$|[_-])/iu;
const EXPECTED_PUBLIC_ENVELOPES = {
  "cat-320": {
    x: { factId: "transport-length", toleranceM: 0.08 },
    y: { factId: "transport-height", toleranceM: 0.05 },
    z: { factId: "undercarriage-width", toleranceM: 0.04 }
  },
  "john-deere-333-p-tier": {
    x: { factId: "length-foundry-bucket", toleranceM: 0.06 },
    y: { factId: "rops-height", toleranceM: 0.04 }
  },
  "john-deere-310-p-tier": {
    x: { factId: "overall-length", toleranceM: 0.06 },
    y: { factId: "backhoe-transport-height", toleranceM: 0.05 },
    z: { factId: "overall-width", toleranceM: 0.04 }
  }
};

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
  let offset = 12;
  let json = null;
  let binary = null;
  while (offset + 8 <= buffer.length) {
    const chunkLength = buffer.readUInt32LE(offset);
    const chunkType = buffer.readUInt32LE(offset + 4);
    const chunkStart = offset + 8;
    const chunkEnd = chunkStart + chunkLength;
    if (chunkEnd > buffer.length) throw new Error("GLB chunk exceeds file length");
    if (chunkType === 0x4e4f534a) {
      if (json) throw new Error("GLB contains more than one JSON chunk");
      json = JSON.parse(buffer.toString("utf8", chunkStart, chunkEnd).replace(/\u0000+$/u, "").trimEnd());
    } else if (chunkType === 0x004e4942) {
      if (binary) throw new Error("GLB contains more than one BIN chunk");
      binary = buffer.subarray(chunkStart, chunkEnd);
    }
    offset = chunkEnd;
  }
  if (!json) throw new Error("GLB has no JSON chunk");
  if (!binary) throw new Error("GLB has no BIN chunk");
  return { json, binary };
}

function identityMatrix() {
  return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
}

function multiplyMatrices(a, b) {
  const result = new Array(16).fill(0);
  for (let column = 0; column < 4; column += 1) {
    for (let row = 0; row < 4; row += 1) {
      for (let index = 0; index < 4; index += 1) {
        result[column * 4 + row] += a[index * 4 + row] * b[column * 4 + index];
      }
    }
  }
  return result;
}

function nodeMatrix(node) {
  if (node.matrix) return [...node.matrix];
  const [x, y, z, w] = node.rotation ?? [0, 0, 0, 1];
  const [sx, sy, sz] = node.scale ?? [1, 1, 1];
  const [tx, ty, tz] = node.translation ?? [0, 0, 0];
  const x2 = x + x;
  const y2 = y + y;
  const z2 = z + z;
  const xx = x * x2;
  const xy = x * y2;
  const xz = x * z2;
  const yy = y * y2;
  const yz = y * z2;
  const zz = z * z2;
  const wx = w * x2;
  const wy = w * y2;
  const wz = w * z2;
  return [
    (1 - (yy + zz)) * sx, (xy + wz) * sx, (xz - wy) * sx, 0,
    (xy - wz) * sy, (1 - (xx + zz)) * sy, (yz + wx) * sy, 0,
    (xz + wy) * sz, (yz - wx) * sz, (1 - (xx + yy)) * sz, 0,
    tx, ty, tz, 1
  ];
}

function transformPoint(matrix, point) {
  const [x, y, z] = point;
  return [
    matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
    matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
    matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14]
  ];
}

function isIdentityTransform(node) {
  const actual = nodeMatrix(node);
  const expected = identityMatrix();
  return actual.every((value, index) => Number.isFinite(value) && Math.abs(value - expected[index]) <= IDENTITY_EPSILON);
}

function nodeScaleAudit(node) {
  if (!node.matrix) {
    const scale = node.scale ?? [1, 1, 1];
    const valid = scale.length === 3 && scale.every((value) => Number.isFinite(value) && Math.abs(value - 1) <= 1e-4);
    return { valid, scale };
  }
  const matrix = node.matrix;
  const columns = [
    [matrix[0], matrix[1], matrix[2]],
    [matrix[4], matrix[5], matrix[6]],
    [matrix[8], matrix[9], matrix[10]]
  ];
  const scale = columns.map((column) => Math.hypot(...column));
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const determinant =
    matrix[0] * (matrix[5] * matrix[10] - matrix[6] * matrix[9]) -
    matrix[4] * (matrix[1] * matrix[10] - matrix[2] * matrix[9]) +
    matrix[8] * (matrix[1] * matrix[6] - matrix[2] * matrix[5]);
  const valid =
    scale.every((value) => Number.isFinite(value) && Math.abs(value - 1) <= 1e-4) &&
    Math.abs(dot(columns[0], columns[1])) <= 1e-4 &&
    Math.abs(dot(columns[0], columns[2])) <= 1e-4 &&
    Math.abs(dot(columns[1], columns[2])) <= 1e-4 &&
    Math.abs(determinant - 1) <= 1e-4;
  return { valid, scale, determinant };
}

function primitiveTriangleCount(gltf, primitive) {
  const positionAccessor = gltf.accessors?.[primitive.attributes?.POSITION];
  const elementAccessor = primitive.indices === undefined ? positionAccessor : gltf.accessors?.[primitive.indices];
  if (!Number.isInteger(elementAccessor?.count) || elementAccessor.count < 0) {
    throw new Error("primitive lacks a valid indexed or POSITION element count");
  }
  const mode = primitive.mode ?? 4;
  if (mode === 4) {
    if (elementAccessor.count % 3 !== 0) throw new Error(`TRIANGLES primitive count ${elementAccessor.count} is not divisible by three`);
    return elementAccessor.count / 3;
  }
  if (mode === 5 || mode === 6) return Math.max(0, elementAccessor.count - 2);
  throw new Error(`public mesh primitive uses non-triangle topology mode ${mode}`);
}

function receiptTriangleCount(receipt) {
  const scene = receipt.scene ?? {};
  const value = scene.triangles ?? scene.triangle_count ?? scene.counts?.triangles;
  return Number.isInteger(value) && value >= 0 ? value : null;
}

function readComponent(buffer, byteOffset, componentType, normalized) {
  let value;
  if (componentType === 5120) value = buffer.readInt8(byteOffset);
  else if (componentType === 5121) value = buffer.readUInt8(byteOffset);
  else if (componentType === 5122) value = buffer.readInt16LE(byteOffset);
  else if (componentType === 5123) value = buffer.readUInt16LE(byteOffset);
  else if (componentType === 5125) value = buffer.readUInt32LE(byteOffset);
  else if (componentType === 5126) value = buffer.readFloatLE(byteOffset);
  else throw new Error(`unsupported POSITION component type ${componentType}`);
  if (!normalized || componentType === 5126) return value;
  if (componentType === 5120) return Math.max(value / 127, -1);
  if (componentType === 5121) return value / 255;
  if (componentType === 5122) return Math.max(value / 32767, -1);
  if (componentType === 5123) return value / 65535;
  if (componentType === 5125) return value / 4294967295;
  return value;
}

function componentByteSize(componentType) {
  if (componentType === 5120 || componentType === 5121) return 1;
  if (componentType === 5122 || componentType === 5123) return 2;
  if (componentType === 5125 || componentType === 5126) return 4;
  throw new Error(`unsupported POSITION component type ${componentType}`);
}

function includeAccessorGeometry(bounds, gltf, binary, accessorIndex, worldMatrix) {
  const accessor = gltf.accessors?.[accessorIndex];
  if (!Array.isArray(accessor?.min) || !Array.isArray(accessor?.max) || accessor.min.length < 3 || accessor.max.length < 3) {
    throw new Error("POSITION accessor lacks finite three-dimensional min/max metadata");
  }
  if (![...accessor.min, ...accessor.max].every(Number.isFinite)) {
    throw new Error("POSITION accessor min/max contains a non-finite value");
  }
  if (accessor.type !== "VEC3") throw new Error(`POSITION accessor type is ${accessor.type}, not VEC3`);
  if (accessor.sparse) throw new Error("sparse POSITION accessors are not supported by the independent validator");
  const bufferView = gltf.bufferViews?.[accessor.bufferView];
  if (!bufferView || (bufferView.buffer ?? 0) !== 0) throw new Error("POSITION accessor does not reference the GLB BIN buffer");
  const byteSize = componentByteSize(accessor.componentType);
  const stride = bufferView.byteStride ?? byteSize * 3;
  if (stride < byteSize * 3) throw new Error(`POSITION byte stride ${stride} is smaller than one VEC3`);
  const start = (bufferView.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  const end = start + Math.max(0, accessor.count - 1) * stride + byteSize * 3;
  if (start < 0 || end > binary.length) throw new Error("POSITION accessor exceeds the GLB BIN chunk");
  const observedLocal = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
  for (let index = 0; index < accessor.count; index += 1) {
    const vertexStart = start + index * stride;
    const local = [0, 1, 2].map((axis) => readComponent(binary, vertexStart + axis * byteSize, accessor.componentType, accessor.normalized));
    if (!local.every(Number.isFinite)) throw new Error("POSITION accessor contains a non-finite vertex");
    const point = transformPoint(worldMatrix, local);
    for (let axis = 0; axis < 3; axis += 1) {
      observedLocal.min[axis] = Math.min(observedLocal.min[axis], local[axis]);
      observedLocal.max[axis] = Math.max(observedLocal.max[axis], local[axis]);
      bounds.min[axis] = Math.min(bounds.min[axis], point[axis]);
      bounds.max[axis] = Math.max(bounds.max[axis], point[axis]);
    }
  }
  for (let axis = 0; axis < 3; axis += 1) {
    if (Math.abs(observedLocal.min[axis] - accessor.min[axis]) > 1e-5 || Math.abs(observedLocal.max[axis] - accessor.max[axis]) > 1e-5) {
      throw new Error(`POSITION accessor declared min/max disagrees with decoded vertices on ${"XYZ"[axis]}`);
    }
  }
}

function inspectGlbContract(gltf, binary) {
  const errors = [];
  if (gltf.asset?.version !== "2.0") errors.push(`JSON asset version must be 2.0 (found ${gltf.asset?.version ?? "missing"})`);
  const defaultSceneIndex = gltf.scene ?? 0;
  const defaultScene = gltf.scenes?.[defaultSceneIndex];
  const sceneRoots = defaultScene?.nodes ?? [];
  if (sceneRoots.length !== 1) errors.push(`default scene must reference exactly one root node (found ${sceneRoots.length})`);
  const rootIndex = sceneRoots[0];
  const rootNode = gltf.nodes?.[rootIndex];
  if (rootNode && !rootNode.name) errors.push("scene root must have a stable nonempty name");
  if (rootNode && !isIdentityTransform(rootNode)) errors.push(`scene root ${rootNode.name ?? rootIndex} is not identity-transformed`);
  if ((gltf.cameras?.length ?? 0) > 0) errors.push("public GLB contains one or more cameras");
  if (gltf.extensionsUsed?.includes("KHR_lights_punctual") || gltf.extensions?.KHR_lights_punctual) {
    errors.push("public GLB contains KHR_lights_punctual data");
  }

  const reachable = new Set();
  const bounds = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
  let meshNodeCount = 0;
  let triangleCount = 0;
  function visit(nodeIndex, parentMatrix) {
    if (reachable.has(nodeIndex)) {
      errors.push(`node ${nodeIndex} is referenced more than once or forms a cycle`);
      return;
    }
    reachable.add(nodeIndex);
    const node = gltf.nodes?.[nodeIndex];
    if (!node) {
      errors.push(`scene references missing node ${nodeIndex}`);
      return;
    }
    const worldMatrix = multiplyMatrices(parentMatrix, nodeMatrix(node));
    if (node.mesh !== undefined) {
      meshNodeCount += 1;
      const scaleAudit = nodeScaleAudit(node);
      if (!scaleAudit.valid) {
        errors.push(
          `public mesh node has non-identity scale or shear (${node.name ?? nodeIndex}: ` +
          `${scaleAudit.scale.map((value) => Number(value).toFixed(6)).join(", ")})`
        );
      }
      if (HELPER_NAME_PATTERN.test(node.name ?? "")) {
        errors.push(`helper-like node is exported as visible mesh (${node.name})`);
      }
      const mesh = gltf.meshes?.[node.mesh];
      if (!mesh) errors.push(`node ${node.name ?? nodeIndex} references missing mesh ${node.mesh}`);
      for (const primitive of mesh?.primitives ?? []) {
        const positionAccessorIndex = primitive.attributes?.POSITION;
        try {
          triangleCount += primitiveTriangleCount(gltf, primitive);
          includeAccessorGeometry(bounds, gltf, binary, positionAccessorIndex, worldMatrix);
        } catch (error) {
          errors.push(`${node.name ?? nodeIndex}: ${error.message}`);
        }
      }
    }
    for (const childIndex of node.children ?? []) visit(childIndex, worldMatrix);
  }
  if (rootNode) visit(rootIndex, identityMatrix());

  const unreachableMeshNodes = (gltf.nodes ?? [])
    .map((node, index) => ({ node, index }))
    .filter(({ node, index }) => node.mesh !== undefined && !reachable.has(index));
  if (unreachableMeshNodes.length > 0) {
    errors.push(`${unreachableMeshNodes.length} mesh node(s) are outside the default scene root`);
  }
  const hasBounds = bounds.min.every(Number.isFinite) && bounds.max.every(Number.isFinite);
  if (!hasBounds || meshNodeCount === 0) errors.push("could not reconstruct a visible-mesh world AABB");
  return {
    errors,
    rootName: rootNode?.name ?? null,
    meshNodeCount,
    triangleCount,
    bounds: hasBounds ? { min: bounds.min, max: bounds.max, size: bounds.max.map((value, axis) => value - bounds.min[axis]) } : null
  };
}

function declaredReceiptBounds(receipt) {
  const direct = receipt.scene?.bounds;
  if (Array.isArray(direct?.min_m) && Array.isArray(direct?.max_m)) {
    return { min: direct.min_m, max: direct.max_m, size: direct.size_m };
  }
  const evaluated = direct?.evaluated_public_visible_retained_pose;
  if (Array.isArray(evaluated?.min_m) && Array.isArray(evaluated?.max_m)) {
    return { min: evaluated.min_m, max: evaluated.max_m, size: evaluated.size_m };
  }
  const backhoe = receipt.scene?.bounds_m;
  if (Array.isArray(backhoe?.min_xyz) && Array.isArray(backhoe?.max_xyz)) {
    return { min: backhoe.min_xyz, max: backhoe.max_xyz, size: backhoe.dimensions_xyz };
  }
  const loader = receipt.scene?.bounds?.machine_axes_m?.stowed_with_reconstructed_foundry_bucket;
  if (Array.isArray(loader?.min_m) && Array.isArray(loader?.max_m)) {
    return { min: loader.min_m, max: loader.max_m, size: loader.size_m };
  }
  if (Array.isArray(loader?.min) && Array.isArray(loader?.max)) {
    return { min: loader.min, max: loader.max, size: loader.size };
  }
  return null;
}

function compareVector(errors, label, actual, expected, toleranceM) {
  for (let axis = 0; axis < 3; axis += 1) {
    if (!Number.isFinite(expected?.[axis]) || Math.abs(actual[axis] - expected[axis]) > toleranceM) {
      errors.push(`${label} axis ${"XYZ"[axis]} mismatch (${actual[axis].toFixed(4)} != ${expected?.[axis] ?? "missing"}, tolerance ${toleranceM} m)`);
    }
  }
}

function verifyPublishedEnvelope({ errors, machineId, facts, measuredSize }) {
  const expected = EXPECTED_PUBLIC_ENVELOPES[machineId];
  if (!expected) {
    errors.push(`${machineId}/glb: no authoritative public-envelope mapping is declared`);
    return;
  }
  const factsById = new Map((facts.facts ?? []).map((fact) => [fact.id, fact]));
  for (const [axisName, rule] of Object.entries(expected)) {
    const axisIndex = { x: 0, y: 1, z: 2 }[axisName];
    const fact = factsById.get(rule.factId);
    if (!fact || fact.unit !== "m" || !Number.isFinite(fact.value)) {
      errors.push(`${machineId}/glb: authoritative envelope fact unavailable (${rule.factId})`);
      continue;
    }
    if (Math.abs(measuredSize[axisIndex] - fact.value) > rule.toleranceM) {
      errors.push(
        `${machineId}/glb: measured ${axisName.toUpperCase()} envelope ${measuredSize[axisIndex].toFixed(4)} m ` +
        `does not match ${rule.factId} ${fact.value} m within ${rule.toleranceM} m`
      );
    }
  }
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
  const summary = {
    machines: 0,
    blends: 0,
    glbs: 0,
    renders: 0,
    glb_nodes: 0,
    glb_mesh_nodes: 0,
    glb_triangles: 0,
    glb_contracts: {}
  };

  for (const machine of catalog.machines ?? []) {
    const machineId = machine.id;
    const machineBase = path.join(ROOT, "machines", machineId);
    const receiptPath = path.join(machineBase, "production", "asset-receipt.json");
    const validationPath = path.join(machineBase, "production", "validation.json");
    let configuration;
    let facts;
    let receipt;
    let validation;
    try {
      [configuration, facts, receipt, validation] = await Promise.all([
        readJson(path.join(machineBase, "configuration.json")),
        readJson(path.join(machineBase, "evidence", "facts.json")),
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
        const parsedGlb = parseGlb(await readFile(glbPath));
        const gltf = parsedGlb.json;
        const nodeNames = new Set((gltf.nodes ?? []).map((node) => node.name).filter(Boolean));
        summary.glb_nodes += gltf.nodes?.length ?? 0;
        const contract = inspectGlbContract(gltf, parsedGlb.binary);
        summary.glb_mesh_nodes += contract.meshNodeCount;
        summary.glb_triangles += contract.triangleCount;
        summary.glb_contracts[machineId] = {
          root_name: contract.rootName,
          mesh_nodes: contract.meshNodeCount,
          decoded_triangles: contract.triangleCount,
          visible_bounds_m: contract.bounds
        };
        for (const contractError of contract.errors) errors.push(`${machineId}/glb: ${contractError}`);
        const declaredTriangles = receiptTriangleCount(receipt);
        if (declaredTriangles === null) {
          errors.push(`${machineId}/glb: public receipt lacks an integer triangle metric for the viewer`);
        } else if (declaredTriangles !== contract.triangleCount) {
          errors.push(
            `${machineId}/glb: decoded triangle count ${contract.triangleCount} does not match ` +
            `public receipt/viewer metric ${declaredTriangles}`
          );
        }
        if (contract.bounds) {
          const declaredBounds = declaredReceiptBounds(receipt);
          if (!declaredBounds) {
            errors.push(`${machineId}/glb: receipt lacks declared visible bounds`);
          } else {
            compareVector(
              errors,
              `${machineId}/glb receipt min`,
              contract.bounds.min,
              declaredBounds.min,
              RECEIPT_BOUNDS_TOLERANCE_M
            );
            compareVector(
              errors,
              `${machineId}/glb receipt max`,
              contract.bounds.max,
              declaredBounds.max,
              RECEIPT_BOUNDS_TOLERANCE_M
            );
            compareVector(
              errors,
              `${machineId}/glb receipt size`,
              contract.bounds.size,
              declaredBounds.size,
              RECEIPT_BOUNDS_TOLERANCE_M
            );
          }
          verifyPublishedEnvelope({ errors, machineId, facts, measuredSize: contract.bounds.size });
        }
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
    if (!VALID_GATE_STATUSES.has(validation.verdict)) {
      errors.push(`${machineId}: declared technical-study input verdict is invalid (${validation.verdict ?? "missing"})`);
    }
    if (failed.length > 0) {
      errors.push(`${machineId}: declared technical-study gates contain FAIL (${failed.join(", ")})`);
    }
    if (validation.verdict !== "PASS") {
      errors.push(
        `${machineId}: declared technical-study input classification is ${validation.verdict ?? "missing"}; ` +
        "independent artifact checks do not upgrade it"
      );
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
        `${result.summary.glbs} GLBs, ${result.summary.renders} renders, ${result.summary.glb_nodes} GLB nodes, ` +
        `${result.summary.glb_mesh_nodes} independently measured mesh nodes, ${result.summary.glb_triangles} decoded triangles`
    );
  }
}
