import { access, readFile, stat } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
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
  "machines/cat-320/assets/cat-320-structural-study.glb",
  "machines/john-deere-333-p-tier/assets/john-deere-333-p-tier-structural-study.glb",
  "machines/john-deere-310-p-tier/assets/john-deere-310-p-tier-structural-study.glb"
];

const errors = [];
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
for (const token of ["GLTFLoader", "OrbitControls", "cat-320-structural-study.glb", "john-deere-333-p-tier-structural-study.glb", "john-deere-310-p-tier-structural-study.glb"]) {
  if (!app.includes(token)) errors.push(`app.js: missing ${token}`);
}
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
  console.log("PASS static atlas entrypoint, responsive viewer contract, three GLBs, and Pages workflow");
}
