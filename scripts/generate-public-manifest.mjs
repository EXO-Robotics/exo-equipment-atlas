import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import { writePublicBundleManifest } from "./release-manifest-lib.mjs";

const execFileAsync = promisify(execFile);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

function optionValue(name) {
  const index = process.argv.indexOf(name);
  if (index === -1) return undefined;
  if (!process.argv[index + 1] || process.argv[index + 1].startsWith("--")) throw new Error(`${name} requires a value`);
  return process.argv[index + 1];
}

async function resolveSourceCommit() {
  const explicit = optionValue("--source-commit") ?? process.env.GITHUB_SHA;
  if (explicit) return explicit;
  const { stdout } = await execFileAsync("git", ["rev-parse", "HEAD"], { cwd: ROOT, encoding: "utf8" });
  return stdout.trim();
}

if (process.argv.includes("--help")) {
  console.log("Usage: node scripts/generate-public-manifest.mjs [--output _site] [--source-commit FULL_GIT_SHA]");
  process.exit(0);
}

const outputDir = path.resolve(ROOT, optionValue("--output") ?? "_site");
const sourceCommit = await resolveSourceCommit();
const manifest = await writePublicBundleManifest({ outputDir, sourceCommit });
console.log(
  `Wrote ${manifest.manifest_path}: ${manifest.payload_file_count} files, ` +
  `${manifest.payload_total_bytes} bytes, source ${manifest.source_commit}`
);
