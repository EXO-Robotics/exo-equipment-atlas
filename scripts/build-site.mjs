import { copyFile, mkdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = path.join(ROOT, "_site");

const publicFiles = [
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
  "machines/cat-320/assets/cat-320-structural-study.glb",
  "machines/cat-320/configuration.json",
  "machines/cat-320/evidence/facts.json",
  "machines/cat-320/production/asset-receipt.json",
  "machines/cat-320/production/validation.json",
  "machines/john-deere-333-p-tier/assets/john-deere-333-p-tier-structural-study.glb",
  "machines/john-deere-333-p-tier/configuration.json",
  "machines/john-deere-333-p-tier/evidence/facts.json",
  "machines/john-deere-333-p-tier/production/asset-receipt.json",
  "machines/john-deere-333-p-tier/production/validation.json",
  "machines/john-deere-310-p-tier/assets/john-deere-310-p-tier-structural-study.glb",
  "machines/john-deere-310-p-tier/configuration.json",
  "machines/john-deere-310-p-tier/evidence/facts.json",
  "machines/john-deere-310-p-tier/production/asset-receipt.json",
  "machines/john-deere-310-p-tier/production/validation.json"
];

await rm(OUTPUT, { recursive: true, force: true });
for (const relativePath of publicFiles) {
  const destination = path.join(OUTPUT, relativePath);
  await mkdir(path.dirname(destination), { recursive: true });
  await copyFile(path.join(ROOT, relativePath), destination);
}

console.log(`Built ${publicFiles.length} public files in _site without private research or Blender sources`);
