import { access, readFile, stat } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ASSET_KEYS = ["glb", "configuration", "facts", "receipt", "validation"];
const MOTION_PROPERTIES = new Set([
  "rotation.x",
  "rotation.y",
  "rotation.z",
  "position.x",
  "position.y",
  "position.z"
]);
const errors = [];

function duplicateValues(values) {
  const seen = new Set();
  const duplicates = new Set();
  for (const value of values) {
    if (seen.has(value)) duplicates.add(value);
    seen.add(value);
  }
  return [...duplicates];
}

function isSafePublicPath(value) {
  if (typeof value !== "string" || !value || value.startsWith("/") || value.includes("\\") || /^[a-z]+:/iu.test(value)) return false;
  const parts = value.split("/");
  return !parts.includes("..") && !value.includes("?") && !value.includes("#") && !value.includes("research/private/");
}

async function requireFile(relativePath) {
  try {
    const fileStat = await stat(path.join(ROOT, relativePath));
    if (!fileStat.isFile()) errors.push(`${relativePath}: not a file`);
    else if (relativePath !== ".nojekyll" && fileStat.size === 0) errors.push(`${relativePath}: empty file`);
  } catch {
    errors.push(`${relativePath}: missing`);
  }
}

function parseGlbStructure(bytes, label) {
  try {
    if (bytes.length < 20 || bytes.toString("utf8", 0, 4) !== "glTF") throw new Error("invalid GLB header");
    let offset = 12;
    while (offset + 8 <= bytes.length) {
      const length = bytes.readUInt32LE(offset);
      const type = bytes.readUInt32LE(offset + 4);
      const start = offset + 8;
      const end = start + length;
      if (end > bytes.length) throw new Error("truncated GLB chunk");
      if (type === 0x4e4f534a) {
        const document = JSON.parse(bytes.toString("utf8", start, end).replace(/\u0000+$/u, "").trim());
        const nodes = document.nodes ?? [];
        const counts = new Map();
        const indexByName = new Map();
        for (const [index, node] of nodes.entries()) {
          if (!node.name) continue;
          counts.set(node.name, (counts.get(node.name) ?? 0) + 1);
          indexByName.set(node.name, index);
        }
        const meshDescendants = new Set();
        function subtreeHasMesh(index, visiting = new Set()) {
          if (visiting.has(index)) return false;
          visiting.add(index);
          const node = nodes[index];
          if (!node) return false;
          if (node.mesh !== undefined) return true;
          const result = (node.children ?? []).some((child) => subtreeHasMesh(child, visiting));
          if (result && node.name) meshDescendants.add(node.name);
          return result;
        }
        for (let index = 0; index < nodes.length; index += 1) subtreeHasMesh(index);
        return { names: new Set(counts.keys()), counts, meshDescendants, nodes, indexByName };
      }
      offset = end;
    }
    throw new Error("missing GLB JSON chunk");
  } catch (error) {
    errors.push(`${label}: ${error.message}`);
    return { names: new Set(), counts: new Map(), meshDescendants: new Set(), nodes: [], indexByName: new Map() };
  }
}

function validateViewerShape(viewer, machineId, viewerPath) {
  if (!viewer || typeof viewer !== "object" || Array.isArray(viewer)) {
    errors.push(`${viewerPath}: must be an object`);
    return;
  }
  if (viewer.schema_version !== "1.0.0") errors.push(`${viewerPath}: schema_version must be 1.0.0`);
  if (viewer.machineId !== machineId) errors.push(`${viewerPath}: machineId must be ${machineId}`);
  for (const key of ["displayName", "className", "category"]) {
    if (typeof viewer[key] !== "string" || !viewer[key].trim()) errors.push(`${viewerPath}: ${key} must be a non-empty string`);
  }
  if (!/^#[0-9a-f]{6}$/iu.test(viewer.accent ?? "")) errors.push(`${viewerPath}: accent must be a six-digit hex color`);
  if (typeof viewer.evidence?.boundary !== "string" || !viewer.evidence.boundary.trim()) errors.push(`${viewerPath}: evidence.boundary required`);
  if (typeof viewer.evidence?.lede !== "string" || !viewer.evidence.lede.trim()) errors.push(`${viewerPath}: evidence.lede required`);
  if (!Array.isArray(viewer.evidence?.factIds) || viewer.evidence.factIds.length === 0) {
    errors.push(`${viewerPath}: evidence.factIds must be a non-empty array`);
  } else {
    const invalid = viewer.evidence.factIds.some((id) => typeof id !== "string" || !id);
    if (invalid) errors.push(`${viewerPath}: evidence.factIds must contain non-empty strings`);
    const duplicates = duplicateValues(viewer.evidence.factIds);
    if (duplicates.length) errors.push(`${viewerPath}: duplicate evidence factIds ${duplicates.join(", ")}`);
  }
  for (const key of ["azimuth", "elevation", "distance"]) {
    if (!Number.isFinite(viewer.camera?.[key])) errors.push(`${viewerPath}: camera.${key} must be finite`);
  }
  if (Number.isFinite(viewer.camera?.distance) && viewer.camera.distance <= 0) errors.push(`${viewerPath}: camera.distance must be positive`);

  for (const key of ASSET_KEYS) {
    const assetPath = viewer.assets?.[key];
    if (!isSafePublicPath(assetPath)) errors.push(`${viewerPath}: assets.${key} must be a safe public path`);
    else if (!assetPath.startsWith(`machines/${machineId}/`)) errors.push(`${viewerPath}: assets.${key} must stay inside its machine package`);
  }
  if (viewer.assets?.poster && (!isSafePublicPath(viewer.assets.poster) || !viewer.assets.poster.startsWith(`machines/${machineId}/`))) {
    errors.push(`${viewerPath}: assets.poster must be a safe path inside its machine package`);
  }

  if (!viewer.motion || !Array.isArray(viewer.motion.channels) || viewer.motion.channels.length === 0) {
    errors.push(`${viewerPath}: every published machine requires at least one interactive motion channel`);
    return;
  }
  if (viewer.motion.autoplay !== undefined && typeof viewer.motion.autoplay !== "boolean") errors.push(`${viewerPath}: motion.autoplay must be boolean`);
  if (viewer.motion.durationSeconds !== undefined && (!Number.isFinite(viewer.motion.durationSeconds) || viewer.motion.durationSeconds <= 0)) {
    errors.push(`${viewerPath}: motion.durationSeconds must be positive`);
  }
  if (viewer.motion.damping !== undefined && (!Number.isFinite(viewer.motion.damping) || viewer.motion.damping <= 0)) {
    errors.push(`${viewerPath}: motion.damping must be positive`);
  }
  if (viewer.motion.mode !== undefined && !["sine", "ping-pong"].includes(viewer.motion.mode)) errors.push(`${viewerPath}: unsupported motion.mode`);
  if (viewer.motion.autoplay !== true) errors.push(`${viewerPath}: standardized Auto mode requires autoplay=true`);
  if (viewer.motion.durationSeconds !== 18) errors.push(`${viewerPath}: standardized Auto cycle must be 18 seconds`);
  if (viewer.motion.mode !== "sine") errors.push(`${viewerPath}: standardized Auto mode must use sine sequencing`);
  if (viewer.motion.damping !== 8) errors.push(`${viewerPath}: standardized motion damping must be 8`);
  const channelIds = viewer.motion.channels.map((channel) => channel?.id);
  const duplicateIds = duplicateValues(channelIds);
  if (duplicateIds.length) errors.push(`${viewerPath}: duplicate motion channel ids ${duplicateIds.join(", ")}`);
  const transformOwners = new Set();
  for (const [index, channel] of viewer.motion.channels.entries()) {
    const label = `${viewerPath}: motion channel ${channel?.id ?? index}`;
    if (typeof channel?.id !== "string" || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/u.test(channel.id)) errors.push(`${label} id must be a slug`);
    if (typeof channel?.label !== "string" || !channel.label.trim()) errors.push(`${label} label required`);
    if (typeof channel?.mechanismJointId !== "string" || !/^[a-z0-9]+(?:[-_][a-z0-9]+)*$/u.test(channel.mechanismJointId)) {
      errors.push(`${label} mechanismJointId must identify its mechanism.json joint`);
    }
    if (!Array.isArray(channel?.nodes) || channel.nodes.length === 0 || channel.nodes.some((node) => typeof node !== "string" || !node)) {
      errors.push(`${label} nodes must be a non-empty string array`);
    } else {
      const duplicateNodes = duplicateValues(channel.nodes);
      if (duplicateNodes.length) errors.push(`${label} duplicate nodes ${duplicateNodes.join(", ")}`);
      for (const node of channel.nodes) {
        const owner = `${node}:${channel.property}`;
        if (transformOwners.has(owner)) errors.push(`${label} conflicts with another channel on ${owner}`);
        transformOwners.add(owner);
      }
    }
    if (!MOTION_PROPERTIES.has(channel?.property)) errors.push(`${label} property is unsupported`);
    if (!Number.isFinite(channel?.from) || !Number.isFinite(channel?.to)) errors.push(`${label} from/to must be finite`);
    if (Number.isFinite(channel?.from) && Number.isFinite(channel?.to) && channel.from === channel.to) {
      errors.push(`${label} from/to must produce visible motion`);
    }
    if (channel?.direction !== undefined && ![1, -1].includes(channel.direction)) errors.push(`${label} direction must be 1 or -1`);
    if (channel?.mode !== undefined && !["offset", "absolute"].includes(channel.mode)) errors.push(`${label} mode must be offset or absolute`);
    if (channel?.autoplay !== undefined && !["sine", "ping-pong"].includes(channel.autoplay)) errors.push(`${label} autoplay must be sine or ping-pong`);
  }
}

const catalog = JSON.parse(await readFile(path.join(ROOT, "catalog.json"), "utf8"));
const catalogMachines = Array.isArray(catalog.machines) ? catalog.machines : [];
if (!Array.isArray(catalog.machines) || catalogMachines.length === 0) errors.push("catalog.json: machines must be a non-empty array");
const catalogIds = catalogMachines.map((machine) => machine?.id);
const duplicateIds = duplicateValues(catalogIds);
if (duplicateIds.length) errors.push(`catalog.json: duplicate machine ids ${duplicateIds.join(", ")}`);
for (const [index, machine] of catalogMachines.entries()) {
  if (typeof machine?.id !== "string" || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/u.test(machine.id)) errors.push(`catalog.json: machine ${index + 1} id must be a slug`);
  if (!Number.isInteger(machine?.priority) || machine.priority <= 0) errors.push(`${machine?.id ?? index}: priority must be a positive integer`);
}
const duplicatePriorities = duplicateValues(catalogMachines.map((machine) => machine?.priority));
if (duplicatePriorities.length) errors.push(`catalog.json: duplicate priorities ${duplicatePriorities.join(", ")}`);

const sharedRequiredFiles = [
  "index.html",
  "404.html",
  ".nojekyll",
  "catalog.json",
  "schemas/viewer.schema.json",
  "assets/site/styles.css",
  "assets/site/app.js",
  "assets/site/motion.js",
  "assets/vendor/three-r160/LICENSE",
  "assets/vendor/three-r160/manifest.json",
  "assets/vendor/three-r160/build/three.module.min.js",
  "assets/vendor/three-r160/examples/jsm/loaders/GLTFLoader.js",
  "assets/vendor/three-r160/examples/jsm/controls/OrbitControls.js",
  "assets/vendor/three-r160/examples/jsm/utils/BufferGeometryUtils.js",
  ".github/workflows/pages.yml"
];
await Promise.all(sharedRequiredFiles.map(requireFile));

for (const { id } of catalogMachines) {
  const viewerPath = `machines/${id}/viewer.json`;
  let viewer;
  try {
    viewer = JSON.parse(await readFile(path.join(ROOT, viewerPath), "utf8"));
  } catch (error) {
    errors.push(`${viewerPath}: ${error.code === "ENOENT" ? "missing" : error.message}`);
    continue;
  }
  validateViewerShape(viewer, id, viewerPath);
  const assetPaths = [...ASSET_KEYS.map((key) => viewer.assets?.[key]), viewer.assets?.poster].filter(isSafePublicPath);
  await Promise.all(assetPaths.map(requireFile));

  try {
    const facts = JSON.parse(await readFile(path.join(ROOT, viewer.assets.facts), "utf8"));
    const factsById = new Set((facts.facts ?? []).map((fact) => fact.id));
    for (const factId of viewer.evidence?.factIds ?? []) {
      if (!factsById.has(factId)) errors.push(`${viewerPath}: evidence fact ${factId} is absent from ${viewer.assets.facts}`);
    }
  } catch (error) {
    errors.push(`${viewerPath}: cannot validate facts (${error.message})`);
  }

  if ((viewer.motion?.channels?.length ?? 0) > 0 && isSafePublicPath(viewer.assets?.glb)) {
    try {
      const glb = await readFile(path.join(ROOT, viewer.assets.glb));
      const structure = parseGlbStructure(glb, viewer.assets.glb);
      for (const channel of viewer.motion.channels) {
        for (const nodeName of channel.nodes ?? []) {
          if (!structure.names.has(nodeName)) errors.push(`${viewerPath}: motion node ${nodeName} is absent from the exported GLB`);
          else if (structure.counts.get(nodeName) !== 1) errors.push(`${viewerPath}: motion node ${nodeName} does not resolve uniquely`);
          else {
            const node = structure.nodes[structure.indexByName.get(nodeName)];
            if (node?.mesh === undefined && !structure.meshDescendants.has(nodeName)) {
              errors.push(`${viewerPath}: motion node ${nodeName} owns no visible mesh descendant`);
            }
            if (node?.matrix !== undefined) {
              errors.push(`${viewerPath}: motion node ${nodeName} must use decomposed transforms, not matrix`);
            }
            const scale = node?.scale ?? [1, 1, 1];
            if (!Array.isArray(scale) || scale.length !== 3 || scale.some((value) => !Number.isFinite(value) || Math.abs(value - 1) > 1e-7)) {
              errors.push(`${viewerPath}: motion node ${nodeName} must have identity scale`);
            }
          }
        }
      }
    } catch (error) {
      errors.push(`${viewerPath}: cannot validate motion nodes (${error.message})`);
    }
  }
}

const [html, css, app, motionSource, workflow, viewerSchema] = await Promise.all([
  readFile(path.join(ROOT, "index.html"), "utf8"),
  readFile(path.join(ROOT, "assets/site/styles.css"), "utf8"),
  readFile(path.join(ROOT, "assets/site/app.js"), "utf8"),
  readFile(path.join(ROOT, "assets/site/motion.js"), "utf8"),
  readFile(path.join(ROOT, ".github/workflows/pages.yml"), "utf8"),
  readFile(path.join(ROOT, "schemas/viewer.schema.json"), "utf8")
]);

for (const token of [
  "EXO Equipment Atlas",
  "assets/site/app.js",
  "./assets/vendor/three-r160/build/three.module.min.js",
  "role=\"tabpanel\"",
  "role=\"region\"",
  "aria-describedby=\"viewer-help\"",
  "class=\"viewer-panel\"",
  "id=\"viewer-panel-title\"",
  "href=\"#scene\">Skip to interactive viewer",
  "role=\"tablist\"",
  "id=\"machine-search\"",
  "id=\"category-filters\"",
  "id=\"motion-panel\"",
  "id=\"motion-channel-template\"",
  "Not released:"
]) {
  if (!html.includes(token)) errors.push(`index.html: missing ${token}`);
}
if (/\bdata-machine\s*=/u.test(html)) errors.push("index.html: machine rows must be generated from catalog, not hardcoded");
if (/\b(?:Thirteen|Twenty|Thirty-three) machines\b/iu.test(html)) errors.push("index.html: machine count must be generated from catalog");

for (const token of [
  "prefers-reduced-motion",
  "100svh",
  ":focus-visible",
  "@media (max-width: 840px)",
  ".machine-search",
  ".category-filters",
  ".motion-panel",
  ".scene-fallback",
  "[hidden] { display: none !important; }"
]) {
  if (!css.includes(token)) errors.push(`styles.css: missing ${token}`);
}

for (const token of [
  "fetchJson(CATALOG_URL",
  "machines/${entry.id}/viewer.json",
  "new URL(window.location.href).searchParams.get(\"machine\")",
  "history[`${mode}State`]",
  "renderCategoryFilters",
  "renderMachineIndex",
  "AUTHORITY_LABELS",
  "MANUAL_OVERRIDE_MS",
  "updateMotion",
  "reducedMotionQuery",
  "scene-fallback",
  "Higher-stage PENDING gates are not release approval",
  "sceneData.triangles ?? sceneData.triangle_count ?? counts.triangles",
  "sceneData.objects ?? sceneData.object_count ?? counts.objects ?? counts.nodes"
]) {
  if (!app.includes(token)) errors.push(`app.js: missing catalog, accessibility, evidence, or motion token ${token}`);
}
if (app.includes("MACHINE_DEFINITIONS")) errors.push("app.js: hardcoded MACHINE_DEFINITIONS are forbidden");
for (const token of ["MANUAL_OVERRIDE_MS = 6000", "Math.exp(-rate * delta)", "autoplayProgress", "ping-pong"]) {
  if (!motionSource.includes(token)) errors.push(`motion.js: missing ${token}`);
}

for (const forbidden of ["https://cdn.jsdelivr.net", "gltfRotationX", "research/private/", "manufacturer_cad", "file://", "/Users/"]) {
  if (html.includes(forbidden) || app.includes(forbidden)) errors.push(`site: forbidden fragile, private, or local token ${forbidden}`);
}
for (const token of ["actions/configure-pages@v5", "actions/upload-pages-artifact@v3", "actions/deploy-pages@v4", "npm run check:site"]) {
  if (!workflow.includes(token)) errors.push(`pages workflow: missing ${token}`);
}

try {
  const schema = JSON.parse(viewerSchema);
  if (schema.$schema !== "https://json-schema.org/draft/2020-12/schema") errors.push("viewer schema: must use JSON Schema draft 2020-12");
  if (schema.properties?.schema_version?.const !== "1.0.0") errors.push("viewer schema: unexpected contract version");
} catch (error) {
  errors.push(`viewer schema: ${error.message}`);
}

await access(path.join(ROOT, ".nojekyll"));
const vendorBase = path.join(ROOT, "assets/vendor/three-r160");
try {
  const manifest = JSON.parse(await readFile(path.join(vendorBase, "manifest.json"), "utf8"));
  if (manifest.package !== "three" || manifest.version !== "0.160.0" || manifest.license !== "MIT") {
    errors.push("three vendor manifest: unexpected package, version, or license");
  }
  if (manifest.files?.length !== 5) errors.push("three vendor manifest: expected five bound files");
  for (const entry of manifest.files ?? []) {
    const bytes = await readFile(path.join(vendorBase, entry.path));
    const digest = createHash("sha256").update(bytes).digest("hex");
    if (digest !== entry.sha256) errors.push(`three vendor manifest: SHA-256 mismatch for ${entry.path}`);
  }
} catch (error) {
  errors.push(`three vendor manifest: ${error.message}`);
}

if (errors.length) {
  for (const error of errors) console.error(`FAIL ${error}`);
  process.exitCode = 1;
} else {
  console.log(
    `PASS catalog-driven responsive atlas, ${catalogMachines.length} viewer contracts, deep links, ` +
    "accessible filters, static fallback, and capability-driven motion"
  );
}
