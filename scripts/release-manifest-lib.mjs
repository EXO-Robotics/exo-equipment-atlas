import { createHash } from "node:crypto";
import { readdir, readFile, stat, writeFile } from "node:fs/promises";
import path from "node:path";

export const PUBLIC_MANIFEST_FILENAME = "public-bundle-manifest.json";
export const PUBLIC_MANIFEST_SCHEMA = "1.0.0";

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function validateCommit(value, label = "source commit") {
  if (typeof value !== "string" || !/^[0-9a-f]{40,64}$/iu.test(value)) {
    throw new Error(`${label} must be a full 40- or 64-character hexadecimal Git commit`);
  }
  return value.toLowerCase();
}

function isSafePayloadPath(value) {
  if (typeof value !== "string" || !value || value.startsWith("/") || value.includes("\\")) return false;
  if (value.includes("?") || value.includes("#") || value.includes("%") || /^[a-z][a-z0-9+.-]*:/iu.test(value)) return false;
  return value.split("/").every((part) => part && part !== "." && part !== "..");
}

async function listPayloadFiles(outputDir) {
  const outputStat = await stat(outputDir);
  if (!outputStat.isDirectory()) throw new Error(`${outputDir} is not a directory`);

  const files = [];
  async function visit(directory, relativeDirectory = "") {
    const entries = await readdir(directory, { withFileTypes: true });
    entries.sort((left, right) => left.name.localeCompare(right.name, "en"));
    for (const entry of entries) {
      const relativePath = relativeDirectory ? `${relativeDirectory}/${entry.name}` : entry.name;
      const absolutePath = path.join(directory, entry.name);
      if (entry.isSymbolicLink()) throw new Error(`public bundle cannot contain symlink ${relativePath}`);
      if (entry.isDirectory()) await visit(absolutePath, relativePath);
      else if (entry.isFile() && relativePath !== PUBLIC_MANIFEST_FILENAME) files.push(relativePath);
      else if (!entry.isFile()) throw new Error(`public bundle contains unsupported entry ${relativePath}`);
    }
  }

  await visit(outputDir);
  return files.sort((left, right) => left.localeCompare(right, "en"));
}

function payloadDigest(files) {
  const digest = createHash("sha256");
  for (const entry of files) digest.update(`${entry.path}\0${entry.bytes}\0${entry.sha256}\n`, "utf8");
  return digest.digest("hex");
}

export async function createPublicBundleManifest({ outputDir, sourceCommit }) {
  const normalizedCommit = validateCommit(sourceCommit);
  const relativePaths = await listPayloadFiles(outputDir);
  if (relativePaths.length === 0) throw new Error("public bundle contains no payload files");

  const files = [];
  for (const relativePath of relativePaths) {
    if (!isSafePayloadPath(relativePath)) throw new Error(`unsafe public bundle path ${relativePath}`);
    const bytes = await readFile(path.join(outputDir, relativePath));
    files.push({ path: relativePath, bytes: bytes.byteLength, sha256: sha256(bytes) });
  }

  const totalBytes = files.reduce((total, entry) => total + entry.bytes, 0);
  return {
    schema_version: PUBLIC_MANIFEST_SCHEMA,
    hash_algorithm: "sha256",
    source_commit: normalizedCommit,
    manifest_path: PUBLIC_MANIFEST_FILENAME,
    manifest_excluded_from_payload: true,
    payload_file_count: files.length,
    payload_total_bytes: totalBytes,
    payload_sha256: payloadDigest(files),
    files
  };
}

export function serializePublicBundleManifest(manifest) {
  return `${JSON.stringify(manifest, null, 2)}\n`;
}

export async function writePublicBundleManifest({ outputDir, sourceCommit }) {
  const manifest = await createPublicBundleManifest({ outputDir, sourceCommit });
  await writeFile(
    path.join(outputDir, PUBLIC_MANIFEST_FILENAME),
    serializePublicBundleManifest(manifest),
    "utf8"
  );
  return manifest;
}

export function validatePublicBundleManifest(manifest, { expectedCommit } = {}) {
  if (!manifest || typeof manifest !== "object" || Array.isArray(manifest)) throw new Error("manifest must be an object");
  if (manifest.schema_version !== PUBLIC_MANIFEST_SCHEMA) throw new Error(`unsupported manifest schema ${manifest.schema_version}`);
  if (manifest.hash_algorithm !== "sha256") throw new Error("manifest hash_algorithm must be sha256");
  const sourceCommit = validateCommit(manifest.source_commit, "manifest source_commit");
  if (expectedCommit && sourceCommit !== validateCommit(expectedCommit, "expected commit")) {
    throw new Error(`source commit mismatch: expected ${expectedCommit.toLowerCase()}, received ${sourceCommit}`);
  }
  if (manifest.manifest_path !== PUBLIC_MANIFEST_FILENAME || manifest.manifest_excluded_from_payload !== true) {
    throw new Error("manifest self-exclusion contract is invalid");
  }
  if (!Array.isArray(manifest.files) || manifest.files.length === 0) throw new Error("manifest files must be a non-empty array");

  const seen = new Set();
  let previousPath = "";
  let totalBytes = 0;
  for (const [index, entry] of manifest.files.entries()) {
    if (!entry || typeof entry !== "object" || !isSafePayloadPath(entry.path)) {
      throw new Error(`manifest file ${index + 1} has an unsafe path`);
    }
    if (entry.path === PUBLIC_MANIFEST_FILENAME) throw new Error("manifest cannot include itself in payload files");
    if (seen.has(entry.path)) throw new Error(`manifest contains duplicate path ${entry.path}`);
    if (previousPath && previousPath.localeCompare(entry.path, "en") >= 0) throw new Error("manifest files are not strictly sorted");
    if (!Number.isSafeInteger(entry.bytes) || entry.bytes < 0) throw new Error(`${entry.path}: bytes must be a non-negative safe integer`);
    if (typeof entry.sha256 !== "string" || !/^[0-9a-f]{64}$/u.test(entry.sha256)) throw new Error(`${entry.path}: invalid SHA-256`);
    seen.add(entry.path);
    previousPath = entry.path;
    totalBytes += entry.bytes;
  }

  if (manifest.payload_file_count !== manifest.files.length) throw new Error("manifest payload_file_count is incorrect");
  if (manifest.payload_total_bytes !== totalBytes) throw new Error("manifest payload_total_bytes is incorrect");
  if (manifest.payload_sha256 !== payloadDigest(manifest.files)) throw new Error("manifest payload_sha256 is incorrect");
  return manifest;
}

function withCacheBuster(url, value) {
  const requestUrl = new URL(url);
  requestUrl.searchParams.set("exo_verify", value);
  return requestUrl;
}

async function fetchBytes(fetchImpl, url) {
  const response = await fetchImpl(url, {
    cache: "no-store",
    headers: { "cache-control": "no-cache", pragma: "no-cache" },
    signal: AbortSignal.timeout(30000)
  });
  if (!response.ok) throw new Error(`${url.pathname}: HTTP ${response.status}`);
  return Buffer.from(await response.arrayBuffer());
}

async function verifyOnce({ baseUrl, expectedCommit, expectedManifestBytes, concurrency, attempt, fetchImpl }) {
  const base = new URL(baseUrl);
  if (!/^https?:$/u.test(base.protocol)) throw new Error("base URL must use http or https");
  if (!base.pathname.endsWith("/")) base.pathname += "/";
  base.search = "";
  base.hash = "";
  const cacheKey = `${expectedCommit ?? "unbound"}-${attempt}`;
  const manifestUrl = withCacheBuster(new URL(PUBLIC_MANIFEST_FILENAME, base), cacheKey);
  const manifestBytes = await fetchBytes(fetchImpl, manifestUrl);
  if (expectedManifestBytes) {
    if (manifestBytes.byteLength !== expectedManifestBytes.byteLength) {
      throw new Error(
        `deployed manifest byte mismatch: expected ${expectedManifestBytes.byteLength}, received ${manifestBytes.byteLength}`
      );
    }
    const expectedManifestSha256 = sha256(expectedManifestBytes);
    const deployedManifestSha256 = sha256(manifestBytes);
    if (deployedManifestSha256 !== expectedManifestSha256) {
      throw new Error(`deployed manifest SHA-256 mismatch: expected ${expectedManifestSha256}, received ${deployedManifestSha256}`);
    }
  }

  let manifest;
  try {
    manifest = JSON.parse(manifestBytes.toString("utf8"));
  } catch (error) {
    throw new Error(`deployed ${PUBLIC_MANIFEST_FILENAME} is not valid JSON: ${error.message}`);
  }
  validatePublicBundleManifest(manifest, { expectedCommit });

  let cursor = 0;
  const failures = [];
  const workers = Array.from({ length: Math.min(concurrency, manifest.files.length) }, async () => {
    while (cursor < manifest.files.length) {
      const entry = manifest.files[cursor++];
      try {
        const assetUrl = withCacheBuster(new URL(entry.path, base), cacheKey);
        const bytes = await fetchBytes(fetchImpl, assetUrl);
        if (bytes.byteLength !== entry.bytes) {
          throw new Error(`byte mismatch: expected ${entry.bytes}, received ${bytes.byteLength}`);
        }
        const digest = sha256(bytes);
        if (digest !== entry.sha256) throw new Error(`SHA-256 mismatch: expected ${entry.sha256}, received ${digest}`);
      } catch (error) {
        failures.push(`${entry.path}: ${error.message}`);
      }
    }
  });
  await Promise.all(workers);
  if (failures.length) throw new Error(`deployed payload mismatch:\n${failures.join("\n")}`);
  return manifest;
}

export async function verifyDeployedPublicBundle({
  baseUrl,
  expectedCommit,
  attempts = 6,
  delayMs = 5000,
  concurrency = 8,
  expectedManifestBytes,
  fetchImpl = globalThis.fetch
}) {
  if (typeof fetchImpl !== "function") throw new Error("Fetch API is unavailable; Node 20 or newer is required");
  if (!Number.isInteger(attempts) || attempts < 1 || attempts > 30) throw new Error("attempts must be an integer from 1 to 30");
  if (!Number.isInteger(delayMs) || delayMs < 0 || delayMs > 60000) throw new Error("delay-ms must be an integer from 0 to 60000");
  if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 32) throw new Error("concurrency must be an integer from 1 to 32");
  if (expectedManifestBytes !== undefined && !Buffer.isBuffer(expectedManifestBytes) && !(expectedManifestBytes instanceof Uint8Array)) {
    throw new Error("expectedManifestBytes must be a Buffer or Uint8Array");
  }
  const normalizedExpectedManifestBytes = expectedManifestBytes === undefined ? undefined : Buffer.from(expectedManifestBytes);

  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      return await verifyOnce({
        baseUrl,
        expectedCommit,
        expectedManifestBytes: normalizedExpectedManifestBytes,
        concurrency,
        attempt,
        fetchImpl
      });
    } catch (error) {
      lastError = error;
      if (attempt < attempts && delayMs > 0) await new Promise((resolve) => setTimeout(resolve, delayMs));
    }
  }
  throw new Error(`Pages verification failed after ${attempts} attempt${attempts === 1 ? "" : "s"}: ${lastError.message}`);
}
