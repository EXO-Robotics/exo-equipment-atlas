import { copyFile, mkdir, readFile, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = path.join(ROOT, "_site");

const catalog = JSON.parse(await readFile(path.join(ROOT, "catalog.json"), "utf8"));
const machinePublicFiles = (catalog.machines ?? []).flatMap(({ id }) => [
  `machines/${id}/assets/${id}-structural-study.glb`,
  `machines/${id}/configuration.json`,
  `machines/${id}/evidence/facts.json`,
  `machines/${id}/production/asset-receipt.json`,
  `machines/${id}/production/validation.json`
]);

const publicFiles = [
  "index.html",
  "404.html",
  ".nojekyll",
  "catalog.json",
  "assets/site/styles.css",
  "assets/site/app.js",
  "assets/vendor/three-r160/LICENSE",
  "assets/vendor/three-r160/manifest.json",
  "assets/vendor/three-r160/build/three.module.min.js",
  "assets/vendor/three-r160/examples/jsm/loaders/GLTFLoader.js",
  "assets/vendor/three-r160/examples/jsm/controls/OrbitControls.js",
  "assets/vendor/three-r160/examples/jsm/utils/BufferGeometryUtils.js",
  ...machinePublicFiles
];

await rm(OUTPUT, { recursive: true, force: true });
for (const relativePath of publicFiles) {
  const destination = path.join(OUTPUT, relativePath);
  await mkdir(path.dirname(destination), { recursive: true });
  await copyFile(path.join(ROOT, relativePath), destination);
}

console.log(`Built ${publicFiles.length} public files in _site without private research or Blender sources`);
