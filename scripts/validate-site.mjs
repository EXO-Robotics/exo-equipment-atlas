import { access, readFile, stat } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const catalog = JSON.parse(await readFile(path.join(ROOT, "catalog.json"), "utf8"));
const EXPECTED_MACHINE_ORDER = [
  "cat-320",
  "john-deere-333-p-tier",
  "john-deere-310-p-tier",
  "cat-950",
  "cat-d6",
  "cat-725",
  "cat-140",
  "john-deere-1270g",
  "john-deere-470-p-tier",
  "bobcat-s76-2",
  "komatsu-wa475-10",
  "volvo-dd128c",
  "liebherr-ltm-1100-5-3"
];
const MACHINE_PATH_PROPERTIES = {
  glb: (id) => `machines/${id}/assets/${id}-structural-study.glb`,
  configuration: (id) => `machines/${id}/configuration.json`,
  facts: (id) => `machines/${id}/evidence/facts.json`,
  receipt: (id) => `machines/${id}/production/asset-receipt.json`,
  validation: (id) => `machines/${id}/production/validation.json`
};
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

function compareExactOrder(label, actual, expected) {
  const duplicates = duplicateValues(actual);
  if (duplicates.length > 0) errors.push(`${label}: duplicate value(s): ${duplicates.join(", ")}`);
  if (actual.length !== expected.length || actual.some((value, index) => value !== expected[index])) {
    errors.push(`${label}: exact order mismatch (${actual.join(", ")} != ${expected.join(", ")})`);
  }
}

function parseMachineDefinitions(source) {
  const startMarker = "const MACHINE_DEFINITIONS = {";
  const start = source.indexOf(startMarker);
  const endMarker = "\n};\n\nconst dom =";
  const end = start < 0 ? -1 : source.indexOf(endMarker, start + startMarker.length);
  if (start < 0 || end < 0) {
    errors.push("app.js: cannot isolate MACHINE_DEFINITIONS literal");
    return [];
  }
  const bodyStart = start + startMarker.length;
  const body = source.slice(bodyStart, end);
  const entryMatches = [...body.matchAll(/^  "([a-z0-9-]+)": \{$/gmu)];
  if (entryMatches.length === 0) {
    errors.push("app.js: MACHINE_DEFINITIONS contains no parseable top-level entries");
    return [];
  }
  return entryMatches.map((match, index) => {
    const blockStart = match.index;
    const blockEnd = index + 1 < entryMatches.length ? entryMatches[index + 1].index : body.length;
    const block = body.slice(blockStart, blockEnd);
    const paths = {};
    for (const property of Object.keys(MACHINE_PATH_PROPERTIES)) {
      const matches = [...block.matchAll(new RegExp(`^    ${property}: "([^"]+)",?$`, "gmu"))];
      if (matches.length !== 1) {
        errors.push(`app.js: ${match[1]} must declare exactly one string ${property} path`);
      } else {
        paths[property] = matches[0][1];
      }
    }
    return { id: match[1], paths };
  });
}

function parseAttributes(tag) {
  const attributes = new Map();
  for (const match of tag.matchAll(/([:\w-]+)\s*=\s*"([^"]*)"/gu)) {
    if (attributes.has(match[1])) errors.push(`index.html: duplicate ${match[1]} attribute on machine tab`);
    attributes.set(match[1], match[2]);
  }
  return attributes;
}

const catalogMachines = Array.isArray(catalog.machines) ? catalog.machines : [];
if (!Array.isArray(catalog.machines)) errors.push("catalog.json: machines must be an array");
const catalogIds = catalogMachines.map((machine) => machine?.id);
compareExactOrder("catalog.json machine ids", catalogIds, EXPECTED_MACHINE_ORDER);
for (const [index, machine] of catalogMachines.entries()) {
  if (!Number.isInteger(machine?.priority) || machine.priority !== index + 1) {
    errors.push(`${machine?.id ?? `machine-${index + 1}`}: catalog priority must be ${index + 1}`);
  }
}
const machineRequiredFiles = (catalog.machines ?? []).map(({ id }) =>
  `machines/${id}/assets/${id}-structural-study.glb`
);
const requiredFiles = [
  "index.html",
  "404.html",
  ".nojekyll",
  "assets/site/styles.css",
  "assets/site/app.js",
  "assets/vendor/three-r160/LICENSE",
  "assets/vendor/three-r160/manifest.json",
  "assets/vendor/three-r160/build/three.module.min.js",
  "assets/vendor/three-r160/examples/jsm/loaders/GLTFLoader.js",
  "assets/vendor/three-r160/examples/jsm/controls/OrbitControls.js",
  "assets/vendor/three-r160/examples/jsm/utils/BufferGeometryUtils.js",
  ".github/workflows/pages.yml",
  ...machineRequiredFiles
];

for (const file of requiredFiles) {
  try {
    const fileStat = await stat(path.join(ROOT, file));
    if (fileStat.isFile() && file !== ".nojekyll" && fileStat.size === 0) errors.push(`${file}: empty file`);
  } catch {
    errors.push(`${file}: missing`);
  }
}

const [html, css, app, workflow] = await Promise.all([
  readFile(path.join(ROOT, "index.html"), "utf8"),
  readFile(path.join(ROOT, "assets/site/styles.css"), "utf8"),
  readFile(path.join(ROOT, "assets/site/app.js"), "utf8"),
  readFile(path.join(ROOT, ".github/workflows/pages.yml"), "utf8")
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
  "legend-mobile",
  "role=\"tablist\"",
  "aria-controls=\"machine-panel\"",
  "technical-view",
  "Pass / pending / fail",
  "Research candidate · technical structural study",
  "Not released:"
]) {
  if (!html.includes(token)) errors.push(`index.html: missing ${token}`);
}
for (const token of [
  "prefers-reduced-motion",
  "100svh",
  ":focus-visible",
  "@media (max-width: 840px)",
  ":root { --header-height: 58px; --gutter: 16px; }",
  ".viewer-panel {",
  ".hero-statement,\n  .hero-boundary,\n  .hero-metrics { display: none; }",
  "grid-template-columns: repeat(3, minmax(0, 1fr));",
  ".hero-copy :is(a, button, input, select, textarea, [tabindex]) { pointer-events: auto; }",
  ".legend-mobile { display: inline; }",
  ".scene { z-index: -2; pointer-events: auto; }"
]) {
  if (!css.includes(token)) errors.push(`styles.css: missing ${token}`);
}
for (const token of [
  "GLTFLoader",
  "OrbitControls"
]) {
  if (!app.includes(token)) errors.push(`app.js: missing ${token}`);
}

const definitions = parseMachineDefinitions(app);
const definitionIds = definitions.map(({ id }) => id);
compareExactOrder("app.js MACHINE_DEFINITIONS ids", definitionIds, catalogIds);
for (const definition of definitions) {
  for (const [property, canonicalPath] of Object.entries(MACHINE_PATH_PROPERTIES)) {
    const expectedPath = canonicalPath(definition.id);
    if (definition.paths[property] !== expectedPath) {
      errors.push(
        `app.js: ${definition.id}.${property} must be ${expectedPath} ` +
        `(found ${definition.paths[property] ?? "missing"})`
      );
    }
  }
}

const tabTags = [...html.matchAll(/<button\b[^>]*\brole\s*=\s*"tab"[^>]*>/gsu)].map((match) => match[0]);
const tabs = tabTags.map((tag) => parseAttributes(tag));
const tabMachineIds = tabs.map((attributes) => attributes.get("data-machine"));
const tabElementIds = tabs.map((attributes) => attributes.get("id"));
compareExactOrder("index.html machine tab data-machine ids", tabMachineIds, catalogIds);
compareExactOrder("index.html machine tab element ids", tabElementIds, catalogIds.map((id) => `machine-tab-${id}`));
const allHtmlMachineIds = [...html.matchAll(/\bdata-machine\s*=\s*"([^"]+)"/gu)].map((match) => match[1]);
compareExactOrder("index.html all data-machine ids", allHtmlMachineIds, catalogIds);
for (const token of [
  "selectAdjacentTab",
  "currentTechnicalCamera",
  "dom.scene.addEventListener(\"keydown\"",
  "Higher-stage PENDING gates are not release approval",
  "Declared ${candidateClass} input verdict",
  "sceneData.triangles ?? sceneData.triangle_count ?? counts.triangles",
  "sceneData.objects ?? sceneData.object_count ?? counts.objects ?? counts.nodes"
]) {
  if (!app.includes(token)) errors.push(`app.js: missing interaction or release-boundary token ${token}`);
}
for (const forbidden of ["https://cdn.jsdelivr.net", "gltfRotationX"]) {
  if (html.includes(forbidden) || app.includes(forbidden)) errors.push(`site: forbidden fragile or machine-specific transform token ${forbidden}`);
}
for (const forbidden of ["research/private/", "manufacturer_cad", "file://", "/Users/"]) {
  if (html.includes(forbidden) || app.includes(forbidden)) errors.push(`site: forbidden private or local token ${forbidden}`);
}
for (const token of ["actions/configure-pages@v5", "actions/upload-pages-artifact@v3", "actions/deploy-pages@v4", "npm run check:site"]) {
  if (!workflow.includes(token)) errors.push(`pages workflow: missing ${token}`);
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
  console.log(`PASS static atlas entrypoint, responsive viewer contract, ${machineRequiredFiles.length} GLBs, and Pages workflow`);
}
