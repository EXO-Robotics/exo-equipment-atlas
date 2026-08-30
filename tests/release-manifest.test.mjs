import assert from "node:assert/strict";
import { mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import {
  PUBLIC_MANIFEST_FILENAME,
  createPublicBundleManifest,
  serializePublicBundleManifest,
  verifyDeployedPublicBundle,
  writePublicBundleManifest
} from "../scripts/release-manifest-lib.mjs";

const SOURCE_COMMIT = "0123456789abcdef0123456789abcdef01234567";

async function makeBundle() {
  const root = await mkdtemp(path.join(tmpdir(), "exo-pages-release-"));
  const site = path.join(root, "_site");
  await mkdir(path.join(site, "assets"), { recursive: true });
  await writeFile(path.join(site, "index.html"), "<!doctype html><title>Atlas</title>\n", "utf8");
  await writeFile(path.join(site, "assets", "model.glb"), Buffer.from([0, 1, 2, 3, 255]));
  return { root, site };
}

function bundleFetch(site) {
  return async (requestUrl) => {
    try {
      const pathname = decodeURIComponent(new URL(requestUrl).pathname);
      if (!pathname.startsWith("/atlas/")) {
        return new Response(null, { status: 404 });
      }
      const relativePath = pathname.slice("/atlas/".length);
      if (!relativePath || relativePath.split("/").includes("..")) {
        return new Response(null, { status: 400 });
      }
      const bytes = await readFile(path.join(site, relativePath));
      return new Response(bytes, { status: 200, headers: { "content-length": bytes.byteLength } });
    } catch {
      return new Response(null, { status: 404 });
    }
  };
}

test("public manifest is sorted, deterministic, and bound to exact payload bytes", async (context) => {
  const { root, site } = await makeBundle();
  context.after(() => rm(root, { recursive: true, force: true }));

  const first = await createPublicBundleManifest({ outputDir: site, sourceCommit: SOURCE_COMMIT });
  assert.deepEqual(first.files.map((entry) => entry.path), ["assets/model.glb", "index.html"]);
  assert.equal(first.source_commit, SOURCE_COMMIT);
  assert.equal(first.payload_file_count, 2);
  assert.equal(first.payload_total_bytes, 41);

  await writePublicBundleManifest({ outputDir: site, sourceCommit: SOURCE_COMMIT });
  const firstBytes = await readFile(path.join(site, PUBLIC_MANIFEST_FILENAME), "utf8");
  await writePublicBundleManifest({ outputDir: site, sourceCommit: SOURCE_COMMIT });
  const secondBytes = await readFile(path.join(site, PUBLIC_MANIFEST_FILENAME), "utf8");
  assert.equal(firstBytes, secondBytes);
  assert.equal(firstBytes, serializePublicBundleManifest(first));
});

test("deployed verification checks source commit, file bytes, and SHA-256", async (context) => {
  const { root, site } = await makeBundle();
  context.after(() => rm(root, { recursive: true, force: true }));
  await writePublicBundleManifest({ outputDir: site, sourceCommit: SOURCE_COMMIT });
  const fetchImpl = bundleFetch(site);
  const expectedManifestBytes = await readFile(path.join(site, PUBLIC_MANIFEST_FILENAME));

  const verified = await verifyDeployedPublicBundle({
    baseUrl: "https://example.invalid/atlas/",
    expectedCommit: SOURCE_COMMIT,
    attempts: 1,
    delayMs: 0,
    concurrency: 2,
    expectedManifestBytes,
    fetchImpl
  });
  assert.equal(verified.payload_file_count, 2);

  await writeFile(path.join(site, PUBLIC_MANIFEST_FILENAME), Buffer.concat([expectedManifestBytes, Buffer.from("\n")]));
  await assert.rejects(
    verifyDeployedPublicBundle({
      baseUrl: "https://example.invalid/atlas/",
      expectedCommit: SOURCE_COMMIT,
      attempts: 1,
      delayMs: 0,
      concurrency: 2,
      expectedManifestBytes,
      fetchImpl
    }),
    /deployed manifest byte mismatch/u
  );
  await writeFile(path.join(site, PUBLIC_MANIFEST_FILENAME), expectedManifestBytes);

  await writeFile(path.join(site, "index.html"), "tampered\n", "utf8");
  await assert.rejects(
    verifyDeployedPublicBundle({
      baseUrl: "https://example.invalid/atlas/",
      expectedCommit: SOURCE_COMMIT,
      attempts: 1,
      delayMs: 0,
      concurrency: 2,
      expectedManifestBytes,
      fetchImpl
    }),
    /deployed payload mismatch[\s\S]*(byte mismatch|SHA-256 mismatch)/u
  );
});
