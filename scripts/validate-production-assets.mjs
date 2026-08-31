import { createHash } from "node:crypto";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { inflateSync } from "node:zlib";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const VALID_GATE_STATUSES = new Set(["PASS", "FAIL", "PENDING"]);
const IDENTITY_EPSILON = 1e-7;
const RECEIPT_BOUNDS_TOLERANCE_M = 0.02;
const HELPER_NAME_PATTERN = /(?:^|[_-])(COL|COLLISION|HIT|INSP|INSPECT|WITNESS|ENVELOPE|HELPER|GUIDE)(?:$|[_-])/iu;
const PUBLIC_ENVELOPE_AXES = ["x", "y", "z"];
export const PRODUCTION_STUDY_MINIMUMS = Object.freeze({
  // These are corruption/empty-export floors, not fidelity scores.  Technical
  // completeness is established by machine-specific gates and semantic parts.
  nodes: 80,
  mesh_nodes: 60,
  decoded_triangles: 5_000,
  review_renders: 6
});

async function readJson(absolutePath) {
  return JSON.parse(await readFile(absolutePath, "utf8"));
}

async function sha256(absolutePath) {
  return createHash("sha256").update(await readFile(absolutePath)).digest("hex");
}

function resolveDeclaredPath(machineBase, declaredPath) {
  if (!declaredPath) return null;
  return path.resolve(declaredPath.startsWith("machines/")
    ? path.join(ROOT, declaredPath)
    : path.join(machineBase, declaredPath));
}

function pathIsWithin(candidate, allowedBase) {
  const relative = path.relative(path.resolve(allowedBase), path.resolve(candidate));
  return relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative));
}

async function verifyDeclaredFile({ errors, machineId, machineBase, label, entry, allowedBase = ROOT }) {
  if (!entry?.path || !entry?.sha256 || !Number.isInteger(entry?.bytes)) {
    errors.push(`${machineId}/${label}: incomplete path, SHA-256, or byte declaration`);
    return null;
  }
  const absolutePath = resolveDeclaredPath(machineBase, entry.path);
  if (!pathIsWithin(absolutePath, allowedBase)) {
    errors.push(`${machineId}/${label}: declared path escapes ${path.relative(ROOT, allowedBase) || "repository"}`);
    return null;
  }
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

const CRC32_TABLE = Uint32Array.from({ length: 256 }, (_, initial) => {
  let value = initial;
  for (let bit = 0; bit < 8; bit += 1) {
    value = (value >>> 1) ^ ((value & 1) ? 0xedb88320 : 0);
  }
  return value >>> 0;
});

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) crc = CRC32_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

export function inspectPng(buffer) {
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  if (buffer.length < 33 || !buffer.subarray(0, 8).equals(signature)) {
    throw new Error("invalid PNG signature or truncated stream");
  }
  if (buffer.toString("ascii", 12, 16) !== "IHDR") throw new Error("PNG lacks an IHDR first chunk");
  const width = buffer.readUInt32BE(16);
  const height = buffer.readUInt32BE(20);
  if (width < 640 || height < 480) throw new Error(`PNG is only ${width}x${height}; minimum is 640x480`);
  const bitDepth = buffer[24];
  const colorType = buffer[25];
  const compression = buffer[26];
  const filter = buffer[27];
  const interlace = buffer[28];
  if (compression !== 0 || filter !== 0 || ![0, 1].includes(interlace)) throw new Error("PNG uses unsupported encoding metadata");
  const channels = new Map([[0, 1], [2, 3], [3, 1], [4, 2], [6, 4]]).get(colorType);
  if (!channels || ![1, 2, 4, 8, 16].includes(bitDepth)) throw new Error("PNG uses an invalid color type or bit depth");
  const idatChunks = [];
  let offset = 8;
  let sawIend = false;
  let chunkIndex = 0;
  while (offset < buffer.length) {
    if (offset + 12 > buffer.length) throw new Error("PNG has a truncated chunk header");
    const length = buffer.readUInt32BE(offset);
    const typeStart = offset + 4;
    const dataStart = offset + 8;
    const dataEnd = dataStart + length;
    const crcOffset = dataEnd;
    if (dataEnd + 4 > buffer.length) throw new Error("PNG chunk exceeds stream length");
    const type = buffer.toString("ascii", typeStart, dataStart);
    const storedCrc = buffer.readUInt32BE(crcOffset);
    const actualCrc = crc32(buffer.subarray(typeStart, dataEnd));
    if (storedCrc !== actualCrc) throw new Error(`PNG ${type} chunk has a CRC mismatch`);
    if (chunkIndex === 0 && (type !== "IHDR" || length !== 13)) throw new Error("PNG first chunk is not a 13-byte IHDR");
    if (type === "IDAT") idatChunks.push(buffer.subarray(dataStart, dataEnd));
    if (type === "IEND") {
      if (length !== 0) throw new Error("PNG IEND chunk is not empty");
      sawIend = true;
      offset = dataEnd + 4;
      break;
    }
    offset = dataEnd + 4;
    chunkIndex += 1;
  }
  if (!sawIend || offset !== buffer.length || idatChunks.length === 0) throw new Error("PNG lacks a terminal IEND or pixel payload");
  let decoded;
  try {
    decoded = inflateSync(Buffer.concat(idatChunks));
  } catch (error) {
    throw new Error(`PNG pixel payload cannot be decompressed (${error.message})`);
  }
  if (interlace === 0) {
    const rowBytes = Math.ceil(width * channels * bitDepth / 8);
    const expectedBytes = height * (rowBytes + 1);
    if (decoded.length !== expectedBytes) {
      throw new Error(`PNG decoded payload length ${decoded.length} does not match ${expectedBytes}`);
    }
  } else if (decoded.length === 0) {
    throw new Error("PNG interlaced pixel payload is empty");
  }
  return { width, height };
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
  const chunkOrder = [];
  while (offset + 8 <= buffer.length) {
    const chunkLength = buffer.readUInt32LE(offset);
    const chunkType = buffer.readUInt32LE(offset + 4);
    const chunkStart = offset + 8;
    const chunkEnd = chunkStart + chunkLength;
    if (chunkEnd > buffer.length) throw new Error("GLB chunk exceeds file length");
    if (chunkType === 0x4e4f534a) {
      if (json) throw new Error("GLB contains more than one JSON chunk");
      json = JSON.parse(buffer.toString("utf8", chunkStart, chunkEnd).replace(/\u0000+$/u, "").trimEnd());
      chunkOrder.push("JSON");
    } else if (chunkType === 0x004e4942) {
      if (binary) throw new Error("GLB contains more than one BIN chunk");
      binary = buffer.subarray(chunkStart, chunkEnd);
      chunkOrder.push("BIN");
    } else {
      chunkOrder.push(`0x${chunkType.toString(16)}`);
    }
    offset = chunkEnd;
  }
  if (offset !== buffer.length) throw new Error("GLB ends with a truncated chunk header");
  if (!json) throw new Error("GLB has no JSON chunk");
  if (!binary) throw new Error("GLB has no BIN chunk");
  if (chunkOrder.length !== 2 || chunkOrder[0] !== "JSON" || chunkOrder[1] !== "BIN") {
    throw new Error(`GLB chunk order must be exactly JSON,BIN (found ${chunkOrder.join(",")})`);
  }
  if (!Array.isArray(json.buffers) || json.buffers.length !== 1 || json.buffers[0]?.uri !== undefined) {
    throw new Error("GLB must declare exactly one embedded buffer");
  }
  const declaredBinaryBytes = json.buffers[0].byteLength;
  if (!Number.isInteger(declaredBinaryBytes) || declaredBinaryBytes < 0 || binary.length - declaredBinaryBytes < 0 || binary.length - declaredBinaryBytes > 3) {
    throw new Error(`GLB embedded buffer length mismatch (${declaredBinaryBytes ?? "missing"} vs ${binary.length})`);
  }
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

function quaternionFromEulerXYZ(x, y, z) {
  const c1 = Math.cos(x / 2);
  const c2 = Math.cos(y / 2);
  const c3 = Math.cos(z / 2);
  const s1 = Math.sin(x / 2);
  const s2 = Math.sin(y / 2);
  const s3 = Math.sin(z / 2);
  return [
    s1 * c2 * c3 + c1 * s2 * s3,
    c1 * s2 * c3 - s1 * c2 * s3,
    c1 * c2 * s3 + s1 * s2 * c3,
    c1 * c2 * c3 - s1 * s2 * s3
  ];
}

function matrixWithViewerOverride(node, override) {
  if (!override) return nodeMatrix(node);
  const translation = [...(node.translation ?? [0, 0, 0])];
  const rotationEuler = [0, 0, 0];
  let hasRotationOverride = false;
  for (const [property, value] of Object.entries(override)) {
    const [group, axisName] = property.split(".");
    const axis = { x: 0, y: 1, z: 2 }[axisName];
    if (axis === undefined) continue;
    if (group === "position") translation[axis] = value;
    else if (group === "rotation") {
      rotationEuler[axis] = value;
      hasRotationOverride = true;
    }
  }
  return nodeMatrix({
    translation,
    rotation: hasRotationOverride ? quaternionFromEulerXYZ(...rotationEuler) : (node.rotation ?? [0, 0, 0, 1]),
    scale: node.scale ?? [1, 1, 1]
  });
}

function measureViewerPoseBounds(gltf, binary, overrides) {
  const bounds = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
  const scene = gltf.scenes?.[gltf.scene ?? 0];
  const visited = new Set();
  function visit(index, parentMatrix) {
    if (visited.has(index)) throw new Error(`viewer pose contains repeated/cyclic node ${index}`);
    visited.add(index);
    const node = gltf.nodes?.[index];
    if (!node) throw new Error(`viewer pose references missing node ${index}`);
    const world = multiplyMatrices(parentMatrix, matrixWithViewerOverride(node, overrides.get(index)));
    if (Number.isInteger(node.mesh)) {
      for (const primitive of gltf.meshes?.[node.mesh]?.primitives ?? []) {
        includeAccessorGeometry(bounds, gltf, binary, primitive.attributes?.POSITION, world);
      }
    }
    for (const child of node.children ?? []) visit(child, world);
  }
  for (const root of scene?.nodes ?? []) visit(root, identityMatrix());
  return bounds;
}

function viewerProgress(mode, progress, phase = 0) {
  const wrapped = ((progress + phase) % 1 + 1) % 1;
  if (mode === "ping-pong") return 1 - Math.abs(2 * wrapped - 1);
  return 0.5 - 0.5 * Math.cos(wrapped * Math.PI * 2);
}

function buildViewerOverrides(gltf, viewer, progress, onlyChannel = null) {
  const nameToIndex = new Map((gltf.nodes ?? []).map((node, index) => [node.name, index]));
  const overrides = new Map();
  const channels = onlyChannel ? [onlyChannel.channel] : (viewer.motion?.channels ?? []);
  for (const channel of channels) {
    let amount = onlyChannel
      ? onlyChannel.amount
      : viewerProgress(channel.autoplay ?? viewer.motion.mode, progress, channel.phase ?? 0);
    if (!onlyChannel && channel.direction === -1) amount = 1 - amount;
    const authored = channel.from + (channel.to - channel.from) * amount;
    for (const name of channel.nodes ?? []) {
      const index = nameToIndex.get(name);
      if (!Number.isInteger(index)) continue;
      const node = gltf.nodes[index];
      const [group, axisName] = channel.property.split(".");
      const axis = { x: 0, y: 1, z: 2 }[axisName];
      const base = group === "position" ? (node.translation ?? [0, 0, 0])[axis] : 0;
      const value = channel.mode === "absolute" ? authored : base + authored;
      const record = overrides.get(index) ?? {};
      record[channel.property] = value;
      overrides.set(index, record);
    }
  }
  return overrides;
}

export function validateViewerMotionSamples(gltf, binary, viewer, machineId) {
  const errors = [];
  const samples = [];
  const toleranceY = -0.03;
  for (const channel of viewer.motion?.channels ?? []) {
    for (const amount of [0, 1]) {
      const bounds = measureViewerPoseBounds(gltf, binary, buildViewerOverrides(gltf, viewer, 0, { channel, amount }));
      samples.push({ label: `${channel.id}@${amount}`, minY: bounds.min[1] });
      if (!Number.isFinite(bounds.min[1]) || bounds.min[1] < toleranceY) {
        errors.push(
          `${machineId}/motion: ${channel.id} endpoint ${amount} has conservative ground bound ` +
          `${Number.isFinite(bounds.min[1]) ? bounds.min[1].toFixed(4) : "non-finite"} m`
        );
      }
    }
  }
  for (let step = 0; step <= 36; step += 1) {
    const progress = step / 36;
    const bounds = measureViewerPoseBounds(gltf, binary, buildViewerOverrides(gltf, viewer, progress));
    samples.push({ label: `auto@${progress.toFixed(4)}`, minY: bounds.min[1] });
    if (!Number.isFinite(bounds.min[1]) || bounds.min[1] < toleranceY) {
      errors.push(
        `${machineId}/motion: Auto sample ${progress.toFixed(4)} has conservative ground bound ` +
        `${Number.isFinite(bounds.min[1]) ? bounds.min[1].toFixed(4) : "non-finite"} m`
      );
      break;
    }
  }
  return { errors, samples };
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

function readAccessorRecords(gltf, binary, accessorIndex, expectedType = null) {
  const accessor = gltf.accessors?.[accessorIndex];
  if (!accessor || (expectedType && accessor.type !== expectedType)) {
    throw new Error(`accessor ${accessorIndex} is missing or not ${expectedType}`);
  }
  if (accessor.sparse) throw new Error("sparse accessors are not supported by the independent material audit");
  const componentCounts = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 };
  const components = componentCounts[accessor.type];
  if (!components) throw new Error(`unsupported accessor type ${accessor.type}`);
  const bufferView = gltf.bufferViews?.[accessor.bufferView];
  if (!bufferView || (bufferView.buffer ?? 0) !== 0) throw new Error("accessor does not reference the embedded GLB buffer");
  const byteSize = componentByteSize(accessor.componentType);
  const stride = bufferView.byteStride ?? components * byteSize;
  if (stride < components * byteSize) throw new Error("accessor stride is smaller than one record");
  const start = (bufferView.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  const end = start + Math.max(0, accessor.count - 1) * stride + components * byteSize;
  if (start < 0 || end > binary.length) throw new Error("accessor exceeds the GLB BIN chunk");
  return Array.from({ length: accessor.count }, (_, recordIndex) => {
    const recordStart = start + recordIndex * stride;
    return Array.from({ length: components }, (_, componentIndex) =>
      readComponent(binary, recordStart + componentIndex * byteSize, accessor.componentType, accessor.normalized)
    );
  });
}

function primitiveSurfaceArea(gltf, binary, primitive) {
  const positions = readAccessorRecords(gltf, binary, primitive.attributes?.POSITION, "VEC3");
  const indices = primitive.indices === undefined
    ? positions.map((_, index) => index)
    : readAccessorRecords(gltf, binary, primitive.indices, "SCALAR").map(([index]) => index);
  const triangles = [];
  const mode = primitive.mode ?? 4;
  if (mode === 4) {
    for (let index = 0; index < indices.length; index += 3) triangles.push(indices.slice(index, index + 3));
  } else if (mode === 5) {
    for (let index = 0; index + 2 < indices.length; index += 1) triangles.push(indices.slice(index, index + 3));
  } else if (mode === 6) {
    for (let index = 1; index + 1 < indices.length; index += 1) triangles.push([indices[0], indices[index], indices[index + 1]]);
  } else {
    throw new Error(`unsupported surface-area topology mode ${mode}`);
  }
  let area = 0;
  for (const triangle of triangles) {
    if (triangle.length !== 3 || triangle.some((index) => !Number.isInteger(index) || !positions[index])) {
      throw new Error("primitive index is not a valid POSITION vertex");
    }
    const [a, b, c] = triangle.map((index) => positions[index]);
    const ab = b.map((value, axis) => value - a[axis]);
    const ac = c.map((value, axis) => value - a[axis]);
    const cross = [
      ab[1] * ac[2] - ab[2] * ac[1],
      ab[2] * ac[0] - ab[0] * ac[2],
      ab[0] * ac[1] - ab[1] * ac[0]
    ];
    area += Math.hypot(...cross) * 0.5;
  }
  return area;
}

export function inspectMaterialArea(gltf, binary, meshIndices) {
  const areaByMaterial = new Map();
  for (const meshIndex of meshIndices) {
    for (const primitive of gltf.meshes?.[meshIndex]?.primitives ?? []) {
      const materialIndex = primitive.material ?? -1;
      const area = primitiveSurfaceArea(gltf, binary, primitive);
      areaByMaterial.set(materialIndex, (areaByMaterial.get(materialIndex) ?? 0) + area);
    }
  }
  const totalArea = [...areaByMaterial.values()].reduce((sum, area) => sum + area, 0);
  let brightChromaticArea = 0;
  const records = [];
  for (const [materialIndex, area] of areaByMaterial) {
    const factor = gltf.materials?.[materialIndex]?.pbrMetallicRoughness?.baseColorFactor ?? [1, 1, 1, 1];
    if (!Array.isArray(factor) || factor.length !== 4 || factor.some((value) => !Number.isFinite(value) || value < 0 || value > 1)) {
      throw new Error(`material ${materialIndex} has an invalid baseColorFactor`);
    }
    const rgb = factor.slice(0, 3);
    const maximum = Math.max(...rgb);
    const minimum = Math.min(...rgb);
    const saturation = maximum > 0 ? (maximum - minimum) / maximum : 0;
    const brightChromatic = maximum >= 0.35 && saturation >= 0.6 && (factor[3] ?? 1) >= 0.5;
    if (brightChromatic) brightChromaticArea += area;
    records.push({
      material_index: materialIndex,
      name: gltf.materials?.[materialIndex]?.name ?? null,
      surface_area_m2: area,
      area_share: totalArea > 0 ? area / totalArea : 0,
      base_color_factor: factor,
      saturation,
      bright_chromatic: brightChromatic
    });
  }
  return {
    total_surface_area_m2: totalArea,
    bright_chromatic_area_share: totalArea > 0 ? brightChromaticArea / totalArea : 0,
    materials: records
  };
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
  if ((gltf.animations?.length ?? 0) > 0) errors.push("public GLB contains embedded animations outside the viewer motion contract");
  if ((gltf.skins?.length ?? 0) > 0) errors.push("public GLB contains skinned deformation outside the structural-study contract");
  if ((gltf.meshes ?? []).some((mesh) => (mesh.primitives ?? []).some((primitive) => (primitive.targets?.length ?? 0) > 0))) {
    errors.push("public GLB contains morph targets outside the structural-study contract");
  }
  if (gltf.extensionsUsed?.includes("KHR_lights_punctual") || gltf.extensions?.KHR_lights_punctual) {
    errors.push("public GLB contains KHR_lights_punctual data");
  }

  const reachable = new Set();
  const parentByIndex = new Map();
  const bounds = { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity] };
  let meshNodeCount = 0;
  let triangleCount = 0;
  const triangleCountByMesh = new Map();
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
    const scaleAudit = nodeScaleAudit(node);
    if (!scaleAudit.valid) {
      errors.push(
        `public node has non-identity scale or shear (${node.name ?? nodeIndex}: ` +
        `${scaleAudit.scale.map((value) => Number(value).toFixed(6)).join(", ")})`
      );
    }
    if (node.mesh !== undefined) {
      meshNodeCount += 1;
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
    for (const childIndex of node.children ?? []) {
      if (parentByIndex.has(childIndex)) errors.push(`node ${childIndex} has more than one parent`);
      parentByIndex.set(childIndex, nodeIndex);
      visit(childIndex, worldMatrix);
    }
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
  const nameCounts = new Map();
  for (const index of reachable) {
    const name = gltf.nodes?.[index]?.name;
    if (!name) continue;
    nameCounts.set(name, (nameCounts.get(name) ?? 0) + 1);
  }
  for (const [name, count] of nameCounts) {
    if (count > 1) errors.push(`reachable node name is not unique (${name}: ${count})`);
  }

  const meshDescendantNames = new Set();
  function subtreeHasMesh(nodeIndex, visiting = new Set()) {
    if (visiting.has(nodeIndex)) return false;
    visiting.add(nodeIndex);
    const node = gltf.nodes?.[nodeIndex];
    if (!node) return false;
    if (node.mesh !== undefined) return true;
    const result = (node.children ?? []).some((childIndex) => subtreeHasMesh(childIndex, visiting));
    if (result && node.name) meshDescendantNames.add(node.name);
    return result;
  }
  for (const index of reachable) subtreeHasMesh(index);

  // Count each mesh payload once.  Reusing one mesh on hundreds of nodes must
  // not inflate the independent complexity floor.
  for (const index of reachable) {
    const meshIndex = gltf.nodes?.[index]?.mesh;
    if (!Number.isInteger(meshIndex) || triangleCountByMesh.has(meshIndex)) continue;
    let uniqueTriangles = 0;
    for (const primitive of gltf.meshes?.[meshIndex]?.primitives ?? []) {
      try {
        uniqueTriangles += primitiveTriangleCount(gltf, primitive);
      } catch {
        // The detailed primitive error was already emitted during traversal.
      }
    }
    triangleCountByMesh.set(meshIndex, uniqueTriangles);
  }

  const topologyRecords = [...reachable].map((index) => {
    const node = gltf.nodes?.[index] ?? {};
    const parent = parentByIndex.get(index);
    return [
      node.name ?? `<unnamed-${index}>`,
      node.mesh === undefined ? "E" : "M",
      parent === undefined ? "<scene>" : (gltf.nodes?.[parent]?.name ?? `<unnamed-${parent}>`),
      (node.children ?? []).length
    ].join("|");
  }).sort().join("\n");
  function anonymousSubtreeSignature(index) {
    const node = gltf.nodes?.[index] ?? {};
    let meshSignature = "E";
    if (Number.isInteger(node.mesh)) {
      const primitives = (gltf.meshes?.[node.mesh]?.primitives ?? []).map((primitive) => {
        const positionCount = gltf.accessors?.[primitive.attributes?.POSITION]?.count ?? -1;
        let triangles = -1;
        try { triangles = primitiveTriangleCount(gltf, primitive); } catch { /* recorded elsewhere */ }
        return `${primitive.mode ?? 4}:${positionCount}:${triangles}`;
      }).sort();
      meshSignature = `M[${primitives.join(",")}]`;
    }
    const children = (node.children ?? []).map(anonymousSubtreeSignature).sort();
    return `${meshSignature}{${children.join(";")}}`;
  }
  const anonymousTopology = rootNode ? anonymousSubtreeSignature(rootIndex) : "missing-root";
  let materialAudit = null;
  try {
    materialAudit = inspectMaterialArea(gltf, binary, triangleCountByMesh.keys());
    if (!Number.isFinite(materialAudit.total_surface_area_m2) || materialAudit.total_surface_area_m2 <= 0) {
      errors.push("public GLB has no finite decoded material surface area");
    } else if (materialAudit.bright_chromatic_area_share > 0.08) {
      errors.push(
        `bright chromatic materials cover ${(materialAudit.bright_chromatic_area_share * 100).toFixed(2)}% of decoded surface; ` +
        "neutral/unbranded studies allow at most 8% for restrained visibility cues"
      );
    }
  } catch (error) {
    errors.push(`material surface audit failed: ${error.message}`);
  }
  return {
    errors,
    rootName: rootNode?.name ?? null,
    meshNodeCount,
    triangleCount,
    uniqueTriangleCount: [...triangleCountByMesh.values()].reduce((sum, value) => sum + value, 0),
    nodeNameCounts: Object.fromEntries(nameCounts),
    meshDescendantNames,
    topologySignature: createHash("sha256").update(topologyRecords).digest("hex"),
    anonymousTopologySignature: createHash("sha256").update(anonymousTopology).digest("hex"),
    materialAudit,
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

function isPlainObject(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

export function validateRequiredGateCoverage({
  machineId = "test-machine",
  mechanism,
  validation,
  availableSemanticNodes = null,
  factIds = null
}) {
  const errors = [];
  const requiredGateIds = mechanism?.required_gates;
  if (!Array.isArray(requiredGateIds) || requiredGateIds.length === 0) {
    return [`${machineId}: mechanism.required_gates must be nonempty`];
  }
  if (new Set(requiredGateIds).size !== requiredGateIds.length) {
    errors.push(`${machineId}: mechanism.required_gates contains duplicate IDs`);
  }
  if (
    !Array.isArray(validation?.required_machine_gate_ids) ||
    JSON.stringify(validation.required_machine_gate_ids) !== JSON.stringify(requiredGateIds)
  ) {
    errors.push(`${machineId}: validation.required_machine_gate_ids must exactly match mechanism.required_gates`);
  }
  const gates = validation?.gates;
  if (!Array.isArray(gates)) return [...errors, `${machineId}: validation gates are missing`];
  const gateIds = gates.map((gate) => gate?.id);
  if (new Set(gateIds).size !== gateIds.length) errors.push(`${machineId}: duplicate validation gate ID`);
  const gatesById = new Map(gates.map((gate) => [gate?.id, gate]));
  for (const requiredGateId of requiredGateIds) {
    const gate = gatesById.get(requiredGateId);
    if (!gate) errors.push(`${machineId}: required mechanism gate missing from validation (${requiredGateId})`);
    else if (gate.status !== "PASS") errors.push(`${machineId}: required mechanism gate is not PASS (${requiredGateId}: ${gate.status})`);
    else {
      const detail = gate.detail;
      if (!isPlainObject(detail) || typeof detail.method !== "string" || !detail.method.trim()) {
        errors.push(`${machineId}: required gate lacks an explicit evidence method (${requiredGateId})`);
      }
      if (!isPlainObject(detail?.evidence) || Object.keys(detail.evidence).length === 0) {
        errors.push(`${machineId}: required gate lacks measured evidence (${requiredGateId})`);
      }
      if (!isPlainObject(detail) || !Array.isArray(detail.semantic_nodes)) {
        errors.push(`${machineId}: required gate must declare its semantic_nodes array (${requiredGateId})`);
      } else if (new Set(detail.semantic_nodes).size !== detail.semantic_nodes.length) {
        errors.push(`${machineId}: required gate repeats semantic nodes (${requiredGateId})`);
      } else if (
        availableSemanticNodes instanceof Set &&
        detail.semantic_nodes.some((nodeName) => !availableSemanticNodes.has(nodeName))
      ) {
        errors.push(`${machineId}: required gate cites absent or non-visible semantic nodes (${requiredGateId})`);
      }
      if (!isPlainObject(detail) || !Array.isArray(detail.fact_ids)) {
        errors.push(`${machineId}: required gate must declare its fact_ids array (${requiredGateId})`);
      } else if (
        detail.fact_ids.some((factId) => typeof factId !== "string" || !factId) ||
        new Set(detail.fact_ids).size !== detail.fact_ids.length
      ) {
        errors.push(`${machineId}: required gate has invalid or duplicate fact IDs (${requiredGateId})`);
      } else if (factIds instanceof Set && detail.fact_ids.some((factId) => !factIds.has(factId))) {
        errors.push(`${machineId}: required gate cites unknown fact IDs (${requiredGateId})`);
      }
    }
  }
  return errors;
}

export function validateReceiptEvidenceAlignment({ machineId = "test-machine", mechanism, design, receipt, validation }) {
  const errors = [];
  const requiredIds = mechanism?.required_gates ?? [];
  const receiptConstraints = receipt?.published_constraint_ids_declared;
  const designConstraints = design?.published_constraints_used ?? [];
  if (!Array.isArray(receiptConstraints) || JSON.stringify(receiptConstraints) !== JSON.stringify(designConstraints)) {
    errors.push(`${machineId}: receipt published constraints must exactly match source/design.json`);
  }
  const receiptEvidence = receipt?.machine_specific_gate_evidence;
  if (!Array.isArray(receiptEvidence)) {
    errors.push(`${machineId}: receipt lacks machine_specific_gate_evidence`);
  } else {
    const receiptIds = receiptEvidence.map((gate) => gate?.id);
    if (JSON.stringify(receiptIds) !== JSON.stringify(requiredIds)) {
      errors.push(`${machineId}: receipt machine gate IDs must exactly match mechanism.required_gates`);
    }
    const validationById = new Map((validation?.gates ?? []).map((gate) => [gate?.id, gate]));
    for (const receiptGate of receiptEvidence) {
      const validationGate = validationById.get(receiptGate?.id);
      const expected = validationGate && {
        id: validationGate.id,
        status: validationGate.status,
        detail: validationGate.detail
      };
      if (!expected || JSON.stringify(receiptGate) !== JSON.stringify(expected)) {
        errors.push(`${machineId}: receipt machine gate evidence drifts from validation (${receiptGate?.id ?? "missing"})`);
      }
    }
  }
  if (receipt?.build_verdict !== validation?.verdict || receipt?.validation_verdict !== validation?.verdict) {
    errors.push(`${machineId}: receipt verdicts must match production validation verdict`);
  }
  return errors;
}

export function validateRenderRecordSet(records, machineId = "test-machine") {
  const errors = [];
  if (!Array.isArray(records)) return [`${machineId}: render records must be an array`];
  const paths = new Set();
  const hashes = new Set();
  for (const record of records) {
    if (paths.has(record?.path)) errors.push(`${machineId}: duplicate render path (${record?.path ?? "missing"})`);
    if (hashes.has(record?.sha256)) errors.push(`${machineId}: duplicate render image hash (${record?.sha256 ?? "missing"})`);
    paths.add(record?.path);
    hashes.add(record?.sha256);
  }
  return errors;
}

export function validatePublishedConstraintCoverage({ machineId = "test-machine", design, validation, factIds = [] }) {
  const errors = [];
  if (!design) return errors;
  const declared = design.published_constraints_used;
  if (!Array.isArray(declared)) return [`${machineId}: design published_constraints_used must be an array`];
  const validFactIds = new Set(factIds);
  const covered = new Set();
  for (const gate of validation?.gates ?? []) {
    for (const factId of gate?.detail?.fact_ids ?? []) covered.add(factId);
  }
  for (const factId of declared) {
    if (!validFactIds.has(factId)) errors.push(`${machineId}: declared published constraint is not a fact (${factId})`);
    if (!covered.has(factId)) errors.push(`${machineId}: declared published constraint lacks machine-gate evidence (${factId})`);
  }
  return errors;
}

function verifyPublishedEnvelope({ errors, machineId, machineEntry, facts, measuredSize }) {
  const expected = machineEntry.public_envelope;
  if (!isPlainObject(expected)) {
    errors.push(`${machineId}/glb: public_envelope must be a plain object declared in catalog.json`);
    return;
  }
  const axisNames = Object.keys(expected);
  if (axisNames.length === 0) {
    if (machineEntry.public_envelope_coverage !== "unresolved") {
      errors.push(`${machineId}/glb: empty public_envelope requires public_envelope_coverage "unresolved"`);
    }
    if (typeof machineEntry.public_envelope_reason !== "string" || !machineEntry.public_envelope_reason.trim()) {
      errors.push(`${machineId}/glb: unresolved public envelope requires a nonempty public_envelope_reason`);
    }
    return;
  }
  const unexpectedAxes = axisNames.filter((axisName) => !PUBLIC_ENVELOPE_AXES.includes(axisName));
  if (unexpectedAxes.length > 0) {
    errors.push(`${machineId}/glb: public_envelope has unsupported key(s): ${unexpectedAxes.join(", ")}`);
  }
  const mappedAxes = PUBLIC_ENVELOPE_AXES.filter((axisName) => Object.hasOwn(expected, axisName));
  const coverage = machineEntry.public_envelope_coverage;
  if (mappedAxes.length < PUBLIC_ENVELOPE_AXES.length) {
    if (coverage !== "partial") {
      errors.push(
        `${machineId}/glb: fewer than x/y/z public-envelope axes require ` +
        `public_envelope_coverage \"partial\" (mapped ${mappedAxes.join(", ") || "none"})`
      );
    }
  } else if (coverage !== undefined) {
    errors.push(`${machineId}/glb: public_envelope_coverage is only permitted for an intentionally partial mapping`);
  }

  const factsById = new Map((facts.facts ?? []).map((fact) => [fact.id, fact]));
  for (const axisName of mappedAxes) {
    const rule = expected[axisName];
    const axisIndex = PUBLIC_ENVELOPE_AXES.indexOf(axisName);
    if (!isPlainObject(rule)) {
      errors.push(`${machineId}/glb: public_envelope.${axisName} must be a plain rule object`);
      continue;
    }
    const unexpectedRuleKeys = Object.keys(rule).filter((key) => !["factId", "toleranceM"].includes(key));
    if (unexpectedRuleKeys.length > 0) {
      errors.push(`${machineId}/glb: public_envelope.${axisName} has unsupported key(s): ${unexpectedRuleKeys.join(", ")}`);
    }
    if (typeof rule.factId !== "string" || rule.factId.length === 0) {
      errors.push(`${machineId}/glb: public_envelope.${axisName}.factId must be a nonempty string`);
      continue;
    }
    if (!Number.isFinite(rule.toleranceM) || rule.toleranceM < 0) {
      errors.push(`${machineId}/glb: public_envelope.${axisName}.toleranceM must be finite and nonnegative`);
      continue;
    }
    const fact = factsById.get(rule.factId);
    if (!fact) {
      errors.push(`${machineId}/glb: public-envelope fact does not exist (${rule.factId})`);
      continue;
    }
    if (fact.authority !== "manufacturer_published") {
      errors.push(
        `${machineId}/glb: public-envelope fact ${rule.factId} must have authority manufacturer_published ` +
        `(found ${fact.authority ?? "missing"})`
      );
      continue;
    }
    if (fact.unit !== "m" || !Number.isFinite(fact.value)) {
      errors.push(`${machineId}/glb: public-envelope fact ${rule.factId} must have a finite value in metres`);
      continue;
    }
    if (!Number.isFinite(measuredSize?.[axisIndex])) {
      errors.push(`${machineId}/glb: measured ${axisName.toUpperCase()} envelope is unavailable or non-finite`);
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

export function validatePublicEnvelopeContract({ machineId = "test-machine", machineEntry, facts, measuredSize }) {
  const errors = [];
  verifyPublishedEnvelope({ errors, machineId, machineEntry, facts, measuredSize });
  return errors;
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

export async function validateProductionAssets({ machineIds = null } = {}) {
  const errors = [];
  const warnings = [];
  const catalog = await readJson(path.join(ROOT, "catalog.json"));
  const topologyOwners = new Map();
  const anonymousTopologyOwners = new Map();
  const summary = {
    machines: 0,
    blends: 0,
    glbs: 0,
    renders: 0,
    glb_nodes: 0,
    glb_mesh_nodes: 0,
    glb_triangles: 0,
    motion_samples: 0,
    glb_contracts: {}
  };
  const selectedMachineIds = machineIds === null ? null : new Set(machineIds);

  for (const machine of catalog.machines ?? []) {
    const machineId = machine.id;
    if (selectedMachineIds && !selectedMachineIds.has(machineId)) continue;
    const machineBase = path.join(ROOT, "machines", machineId);
    const receiptPath = path.join(machineBase, "production", "asset-receipt.json");
    const validationPath = path.join(machineBase, "production", "validation.json");
    let configuration;
    let facts;
    let mechanism;
    let receipt;
    let validation;
    let viewer;
    let design = null;
    let glbGateEvidenceNodes = null;
    try {
      [configuration, facts, mechanism, receipt, validation, viewer] = await Promise.all([
        readJson(path.join(machineBase, "configuration.json")),
        readJson(path.join(machineBase, "evidence", "facts.json")),
        readJson(path.join(machineBase, "mechanism.json")),
        readJson(receiptPath),
        readJson(validationPath),
        readJson(path.join(machineBase, "viewer.json"))
      ]);
      try {
        design = await readJson(path.join(machineBase, "source", "design.json"));
      } catch (error) {
        if (error?.code !== "ENOENT") throw error;
      }
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

    await verifyDeclaredFile({
      errors,
      machineId,
      machineBase,
      label: "builder",
      entry: builderEntry(receipt),
      allowedBase: ROOT
    });
    if (receipt.shared_generator !== undefined) {
      await verifyDeclaredFile({ errors, machineId, machineBase, label: "shared-generator", entry: receipt.shared_generator, allowedBase: ROOT });
    }
    if (receipt.design !== undefined) {
      await verifyDeclaredFile({ errors, machineId, machineBase, label: "design", entry: receipt.design, allowedBase: machineBase });
    }
    await verifyDeclaredFile({
      errors,
      machineId,
      machineBase,
      label: "validation",
      entry: receipt.artifacts?.validation,
      allowedBase: machineBase
    });

    const blendPath = await verifyDeclaredFile({
      errors,
      machineId,
      machineBase,
      label: "blend",
      entry: receipt.artifacts?.blend,
      allowedBase: machineBase
    });
    if (blendPath) summary.blends += 1;

    const glbPath = await verifyDeclaredFile({
      errors,
      machineId,
      machineBase,
      label: "glb",
      entry: receipt.artifacts?.glb,
      allowedBase: machineBase
    });
    if (glbPath) {
      summary.glbs += 1;
      try {
        const parsedGlb = parseGlb(await readFile(glbPath));
        const gltf = parsedGlb.json;
        const nodeNames = new Set((gltf.nodes ?? []).map((node) => node.name).filter(Boolean));
        summary.glb_nodes += gltf.nodes?.length ?? 0;
        const contract = inspectGlbContract(gltf, parsedGlb.binary);
        glbGateEvidenceNodes = new Set(
          (gltf.nodes ?? [])
            .filter((node) => (
              typeof node.name === "string" &&
              contract.nodeNameCounts[node.name] === 1 &&
              (node.mesh !== undefined || contract.meshDescendantNames.has(node.name))
            ))
            .map((node) => node.name)
        );
        const motionAudit = validateViewerMotionSamples(gltf, parsedGlb.binary, viewer, machineId);
        summary.motion_samples += motionAudit.samples.length;
        errors.push(...motionAudit.errors);
        const priorTopologyOwner = topologyOwners.get(contract.topologySignature);
        if (priorTopologyOwner && priorTopologyOwner !== machineId) {
          errors.push(
            `${machineId}/glb: normalized node/mesh hierarchy is identical to ${priorTopologyOwner}; ` +
            "distinct machine identities require machine-specific topology"
          );
        } else {
          topologyOwners.set(contract.topologySignature, machineId);
        }
        const priorAnonymousOwner = anonymousTopologyOwners.get(contract.anonymousTopologySignature);
        if (priorAnonymousOwner && priorAnonymousOwner !== machineId) {
          errors.push(
            `${machineId}/glb: anonymous hierarchy/mesh signature is identical to ${priorAnonymousOwner}; ` +
            "renaming nodes cannot qualify a shared archetype as machine-specific"
          );
        } else {
          anonymousTopologyOwners.set(contract.anonymousTopologySignature, machineId);
        }
        summary.glb_mesh_nodes += contract.meshNodeCount;
        summary.glb_triangles += contract.triangleCount;
        summary.glb_contracts[machineId] = {
          root_name: contract.rootName,
          nodes: gltf.nodes?.length ?? 0,
          mesh_nodes: contract.meshNodeCount,
          decoded_triangles: contract.triangleCount,
          unique_decoded_triangles: contract.uniqueTriangleCount,
          review_renders: Array.isArray(receipt.renders) ? receipt.renders.length : 0,
          visible_bounds_m: contract.bounds,
          material_audit: contract.materialAudit
        };
        for (const contractError of contract.errors) errors.push(`${machineId}/glb: ${contractError}`);
        if ((gltf.nodes?.length ?? 0) < PRODUCTION_STUDY_MINIMUMS.nodes) {
          errors.push(
            `${machineId}/glb: ${gltf.nodes?.length ?? 0} nodes is below the technical-study floor ` +
            `${PRODUCTION_STUDY_MINIMUMS.nodes}`
          );
        }
        if (contract.meshNodeCount < PRODUCTION_STUDY_MINIMUMS.mesh_nodes) {
          errors.push(
            `${machineId}/glb: ${contract.meshNodeCount} mesh nodes is below the technical-study floor ` +
            `${PRODUCTION_STUDY_MINIMUMS.mesh_nodes}`
          );
        }
        if (contract.uniqueTriangleCount < PRODUCTION_STUDY_MINIMUMS.decoded_triangles) {
          errors.push(
            `${machineId}/glb: ${contract.uniqueTriangleCount} unique decoded triangles is below the integrity floor ` +
            `${PRODUCTION_STUDY_MINIMUMS.decoded_triangles}`
          );
        }
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
        }
        errors.push(...validatePublicEnvelopeContract({
          machineId,
          machineEntry: machine,
          facts,
          measuredSize: contract.bounds?.size
        }));
        const semanticNodes = sceneSemanticNodes(receipt);
        const semanticNodeRoles = isPlainObject(receipt.semantic_node_roles) ? receipt.semantic_node_roles : {};
        if (!isPlainObject(semanticNodes) || Object.keys(semanticNodes).length === 0) {
          errors.push(`${machineId}/glb: required semantic-node map must be nonempty`);
        }
        for (const [nodeName, claimedPresent] of Object.entries(semanticNodes)) {
          if (claimedPresent !== true) {
            errors.push(`${machineId}/glb: semantic node ${nodeName} is not explicitly present=true`);
          }
          if (!nodeNames.has(nodeName)) {
            errors.push(`${machineId}/glb: claimed semantic node missing from export (${nodeName})`);
          } else if ((contract.nodeNameCounts[nodeName] ?? 0) !== 1) {
            errors.push(`${machineId}/glb: semantic node must resolve exactly once (${nodeName})`);
          } else if (!contract.meshDescendantNames.has(nodeName) && !(gltf.nodes ?? []).some((node) => node.name === nodeName && node.mesh !== undefined)) {
            const markerRole = semanticNodeRoles[nodeName];
            if (!["datum_marker", "joint_marker", "identity_marker"].includes(markerRole)) {
              errors.push(
                `${machineId}/glb: semantic node owns no visible mesh descendant and lacks an explicit marker role (${nodeName})`
              );
            }
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

    if (!Array.isArray(receipt.renders) || receipt.renders.length < PRODUCTION_STUDY_MINIMUMS.review_renders) {
      errors.push(
        `${machineId}: at least ${PRODUCTION_STUDY_MINIMUMS.review_renders} hashed review renders are required`
      );
    }
    errors.push(...validateRenderRecordSet(receipt.renders ?? [], machineId));
    for (const [index, render] of (receipt.renders ?? []).entries()) {
      const renderPath = await verifyDeclaredFile({
        errors,
        machineId,
        machineBase,
        label: `render-${index + 1}`,
        entry: render,
        allowedBase: machineBase
      });
      if (renderPath) {
        summary.renders += 1;
        try {
          inspectPng(await readFile(renderPath));
        } catch (error) {
          errors.push(`${machineId}/render-${index + 1}: ${error.message}`);
        }
      }
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
    const factIds = new Set((facts.facts ?? []).map((fact) => fact.id));
    errors.push(...validateRequiredGateCoverage({
      machineId,
      mechanism,
      validation,
      availableSemanticNodes: glbGateEvidenceNodes,
      factIds
    }));
    errors.push(...validatePublishedConstraintCoverage({
      machineId,
      design,
      validation,
      factIds: [...factIds]
    }));
    errors.push(...validateReceiptEvidenceAlignment({ machineId, mechanism, design, receipt, validation }));
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
        `${result.summary.glb_mesh_nodes} independently measured mesh nodes, ${result.summary.glb_triangles} decoded triangles, ` +
        `${result.summary.motion_samples} independently sampled motion poses`
    );
  }
}
