import { access, readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const requiredFiles = [
  "index.html",
  "404.html",
  ".nojekyll",
  "assets/site/styles.css",
  "assets/site/app.js",
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

for (const token of ["EXO Equipment Atlas", "assets/site/app.js", "three@0.160.0", "machine-title", "evidence", "method"]) {
  if (!html.includes(token)) errors.push(`index.html: missing ${token}`);
}
for (const token of ["prefers-reduced-motion", "100svh", ":focus-visible", "@media (max-width: 840px)"]) {
  if (!css.includes(token)) errors.push(`styles.css: missing ${token}`);
}
for (const token of ["GLTFLoader", "OrbitControls", "cat-320-structural-study.glb", "john-deere-333-p-tier-structural-study.glb", "john-deere-310-p-tier-structural-study.glb"]) {
  if (!app.includes(token)) errors.push(`app.js: missing ${token}`);
}
for (const forbidden of ["research/private/", "manufacturer_cad", "file://", "/Users/"]) {
  if (html.includes(forbidden) || app.includes(forbidden)) errors.push(`site: forbidden private or local token ${forbidden}`);
}
for (const token of ["actions/configure-pages@v5", "actions/upload-pages-artifact@v3", "actions/deploy-pages@v4", "npm run check:site"]) {
  if (!workflow.includes(token)) errors.push(`pages workflow: missing ${token}`);
}

await access(path.join(ROOT, ".nojekyll"));

if (errors.length) {
  for (const error of errors) console.error(`FAIL ${error}`);
  process.exitCode = 1;
} else {
  console.log("PASS static atlas entrypoint, responsive viewer contract, three GLBs, and Pages workflow");
}
