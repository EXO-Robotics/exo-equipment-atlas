import { copyFile, mkdir, readFile, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const OUTPUT = path.join(ROOT, "_site");
const ASSET_KEYS = ["glb", "configuration", "facts", "receipt", "validation"];

function requirePublicPath(value, label) {
  if (typeof value !== "string" || !value || value.startsWith("/") || value.includes("\\") || /^[a-z]+:/iu.test(value)) {
    throw new Error(`${label} must be a repository-relative public path`);
  }
  const parts = value.split("/");
  if (parts.includes("..") || value.includes("?") || value.includes("#") || value.includes("research/private/")) {
    throw new Error(`${label} is not safe to publish`);
  }
  return value;
}

const catalog = JSON.parse(await readFile(path.join(ROOT, "catalog.json"), "utf8"));
if (!Array.isArray(catalog.machines) || catalog.machines.length === 0) throw new Error("catalog.json contains no machines");

const publicFiles = new Set([
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
  "assets/vendor/three-r160/examples/jsm/utils/BufferGeometryUtils.js"
]);

for (const { id } of catalog.machines) {
  const viewerPath = `machines/${id}/viewer.json`;
  const viewer = JSON.parse(await readFile(path.join(ROOT, viewerPath), "utf8"));
  if (viewer.machineId !== id) throw new Error(`${viewerPath} identifies ${viewer.machineId ?? "no machine"}`);
  publicFiles.add(viewerPath);
  for (const key of ASSET_KEYS) {
    const assetPath = requirePublicPath(viewer.assets?.[key], `${viewerPath} assets.${key}`);
    if (!assetPath.startsWith(`machines/${id}/`)) throw new Error(`${viewerPath} assets.${key} must stay inside its machine package`);
    publicFiles.add(assetPath);
  }
  if (viewer.assets?.poster) {
    const posterPath = requirePublicPath(viewer.assets.poster, `${viewerPath} assets.poster`);
    if (!posterPath.startsWith(`machines/${id}/`)) throw new Error(`${viewerPath} assets.poster must stay inside its machine package`);
    publicFiles.add(posterPath);
  }
}

await rm(OUTPUT, { recursive: true, force: true });
for (const relativePath of [...publicFiles].sort()) {
  const destination = path.join(OUTPUT, relativePath);
  await mkdir(path.dirname(destination), { recursive: true });
  await copyFile(path.join(ROOT, relativePath), destination);
}

console.log(
  `Built ${publicFiles.size} public files for ${catalog.machines.length} catalog machines in _site ` +
  "without private research or Blender sources"
);
