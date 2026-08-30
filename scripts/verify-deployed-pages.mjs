import { readFile } from "node:fs/promises";
import path from "node:path";
import { verifyDeployedPublicBundle } from "./release-manifest-lib.mjs";

function optionValue(name) {
  const index = process.argv.indexOf(name);
  if (index === -1) return undefined;
  if (!process.argv[index + 1] || process.argv[index + 1].startsWith("--")) throw new Error(`${name} requires a value`);
  return process.argv[index + 1];
}

function integerOption(name, fallback) {
  const value = optionValue(name);
  if (value === undefined) return fallback;
  if (!/^\d+$/u.test(value)) throw new Error(`${name} must be an integer`);
  return Number(value);
}

if (process.argv.includes("--help")) {
  console.log(
    "Usage: node scripts/verify-deployed-pages.mjs --base-url URL " +
    "[--expected-commit FULL_GIT_SHA] [--expected-manifest _site/public-bundle-manifest.json] " +
    "[--attempts 6] [--delay-ms 5000] [--concurrency 8]"
  );
  process.exit(0);
}

const baseUrl = optionValue("--base-url") ?? process.env.PAGES_URL;
if (!baseUrl) throw new Error("--base-url or PAGES_URL is required");
const expectedCommit = optionValue("--expected-commit") ?? process.env.SOURCE_COMMIT;
const expectedManifestPath = optionValue("--expected-manifest");
const expectedManifestBytes = expectedManifestPath ? await readFile(path.resolve(expectedManifestPath)) : undefined;
const manifest = await verifyDeployedPublicBundle({
  baseUrl,
  expectedCommit,
  expectedManifestBytes,
  attempts: integerOption("--attempts", 6),
  delayMs: integerOption("--delay-ms", 5000),
  concurrency: integerOption("--concurrency", 8)
});

console.log(
  `PASS deployed Pages bundle: ${manifest.payload_file_count} files, ` +
  `${manifest.payload_total_bytes} bytes, source ${manifest.source_commit}`
);
