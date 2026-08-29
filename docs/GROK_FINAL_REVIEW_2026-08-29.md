# Grok final review — 2026-08-29

Reviewer: Grok 4.6
Mode: one final read-only pass, always-approve with `Read`, `Glob`, and `Grep`
only
Input: sanitized read-only snapshot excluding Git history, credentials, private
manufacturer binaries, generated `_site`, and `.blend` files
Disposition: findings recorded without a post-review repair or review loop

The inspection phase exhausted its initial turn allowance before emitting a
report. The same session was resumed once with tools prohibited by instruction
and asked only to synthesize evidence already gathered. The report below is the
result.

---

# EXO Equipment Atlas — Batch 10 final critic report

Read-only snapshot review. No hashes, GLB AABB decode, `npm` gates, or browser
session were re-executed in this pass. Blender `.blend` files and private source
binaries are absent from the snapshot by design and are not treated as PASS.

## 1. Overall verdict

**Admit as a `research_candidate` / `technical_structural_study` gallery with
MEDIUM defects. Not a mechanical, collision, load-chart, or
manufacturer-authority release.**

Inspected contracts for all ten new machines, plus shared
catalog/viewer/site/production validators, are internally consistent with that
class: reconstructed joints stay reconstructed, higher-stage gates stay
PENDING, public-build copies exclude private research and Blender sources, and
the viewer hash-binds GLB bytes and retains the prior study on failure.

Visual inspection completed only for Cat 950, Cat D6, Cat 725, Cat 140, Deere
1270G, Deere 470 P-Tier, and Bobcat S76-2 (plus Cat 320 / 333 P-Tier as style
baseline). **Komatsu WA475-10, Volvo DD128C, and Liebherr LTM 1100-5.3 renders
were not successfully read before the prior turn ended; those three have no
visual PASS in this report.**

No HIGH release-blocker was independently proven from snapshot-readable files.
Several MEDIUM defects undercut the claim that every new lane is as mechanically
readable as the existing three-machine set.

## 2. HIGH findings

None.

No independently verified false manufacturer fact, missing public GLB path,
private-binary leakage into `scripts/build-site.mjs` public files, viewer
load-contract break in `assets/site/app.js`, or grossly noncredible whole-machine
silhouette was established. Integrity of GLB/render bytes against receipt
SHA-256 was not re-computed (no hash tool in this pass).

## 3. MEDIUM findings

**M1. Liebherr catalog X-envelope is inconsistent with the declared receipt
AABB.**
`catalog.json` maps `liebherr-ltm-1100-5-3` X to fact
`transport-boom-head-length` = 14.932 m with `toleranceM` 0.16.
`machines/liebherr-ltm-1100-5-3/production/asset-receipt.json`
`scene.bounds.size_m[0]` is **15.09475 m** (delta **0.16275 m > 0.16**). The
machine-lane gate in `production/validation.json`
(`transport-longitudinal-envelope`) uses a looser **0.18 m** and PASSes.
`scripts/validate-production-assets.mjs` `verifyPublishedEnvelope` uses the
catalog rule against independently decoded GLB size, not the machine-lane
tolerance. If decoded X equals the receipt AABB, production admission fails; if
decode is only slightly smaller (receipt/decode slop is 0.02 m), it can scrape
through. That is not a qualified envelope. Hook reconstruction “ahead of carrier
cab” in the same receipt also means complete visible X is not identical to the
boom-head drawing datum.

**M2. Deere 1270G viewer presents transport facts beside a non-transport GLB.**
`catalog.json` correctly marks `public_envelope_coverage: "partial"` and maps
only Z (`minimum-width-600` 2.746 m, measured ~2.798 m). Receipt
`scene.bounds.size_m` is **[12.767158, 4.850481, 2.798]** versus published
transport 12.560 × 3.881 m. `assets/site/app.js`
`john-deere-1270g.factIds` still lists `transport-length` and
`transport-height`. The evidence lede discloses a working pose; the metric list
does not. Users can read manufacturer transport numbers as describing the
loaded study.

**M3. Cat 725 “articulation knuckle” review render does not show a knuckle.**
`machines/cat-725/production/asset-receipt.json` binds
`review/renders/cat-725-articulation-knuckle-detail.png`. The inspected image is
cab sill / steps / a gray pole, not the hitch, yokes, or steering-cylinder
closure. Whole-machine ADT silhouette in `cat-725-operator-side.png` and
`cat-725-raised-body-review.png` is credible; the named mechanical-detail proof
for articulation is not.

**M4. Cat 950 named Z-bar detail renders do not show a readable parallel-lift
Z-bar.**
`cat-950-zbar-linkage-detail.png` is a two-plate pin/lug.
`cat-950-zbar-raised-detail.png` shows cylinders into a bucket-top bracket.
Carry/dump overalls (`cat-950-operator-side.png`,
`cat-950-articulated-lift-dump-review.png`) read as a wheel loader, and receipts
claim `ZBar_Bellcrank_Pivot`, but the hash-bound “Z-bar detail” views do not
demonstrate bellcrank/dogbone topology. That is weaker mechanism evidence than
Cat 140’s isolated 64-tooth circle.

**M5. Bobcat S76-2 is below the rest of this batch on structural density and
tire/linkage readability.**
Receipt/public GLB: **250 nodes, 247 mesh nodes, 14,360 triangles** (floor in
`scripts/validate-production-assets.mjs` is 10,000). Blend-source triangles in
the same receipt are 40,448 — public export is heavily reduced.
`bobcat-s76-2-tire-service-detail.png` is circumferential gear-lugs, not a
12×16.5 carcass. `bobcat-s76-2-lift-linkage-detail-stowed.png` is cab cage and
arm pins, not the four-bar/cylinders the mechanism file requires. Full-lift
`bobcat-s76-2-technical-side-full-lift-dump.png` is a recognizable vertical-lift
skid-steer, but it is not at Cat 140 / 470 / D6 / 333-P-Tier inspectability.

**M6. Visual inspection of Komatsu WA475-10, Volvo DD128C, and Liebherr LTM
1100-5.3 did not complete.**
Directory reads for those render trees failed; no PNG for those three was in
context. Contracts were read. **Do not treat those three as visually PASSed.**
This blocks a batch-wide “as realistic as the existing work” claim for the
uninspected third of the new roster.

## 4. LOW findings

- Machine-lane envelope tolerances are often looser than `catalog.json` (Cat
  950 shipping-length gate 0.08 m vs catalog 0.05 m; Liebherr height gate 0.12 m
  vs catalog 0.025 m). Catalog is the production rule; the lane JSON can hide
  tightness.
- Cat 725 published ground-clearance cue: modeled 0.575 m vs 0.533 m, tolerance
  0.05 m (`production/validation.json`). Passes, but it is reconstructed frame,
  not a tight belly datum.
- Komatsu retained AABB `min_m[1] = -0.005595` m
  (`production/validation.json`); Y extent 3.545595 m vs roof-rail 3.54 m.
  Catalog Y tolerance 0.025 m still holds.
- Volvo machine-lane triangle gate uses blend-source 61,772; public receipt
  triangles are 62,024.
- 1270G Z AABB 2.798 m vs 2.746 m is inside catalog 0.07 m; min/max Z signs
  differ between receipt GLB bounds and validation blend bounds.
- Cat 725 `cat-725-tandem-driveline-detail.png` shows tandem hubs and body side,
  not shafts/U-joints.
- D6 sprocket/track (`cat-d6-drive-sprocket-engagement-detail.png`) is block-link
  visual engagement, not bushing-and-segment engineering; already PENDING as
  `track-phase-continuity`.
- 470 `john-deere-470-p-tier-track-sprocket-detail.png` is grouser wrap around
  the end idler/sprocket; tooth-in-bushing mesh is not inspectable there.
- Snapshot still contains `*.blend1` under Deere 310 / 333 blender dirs; public
  build does not copy them.
- Machine `validation.json` files still mark `viewer-browser-…` PENDING even
  though `docs/INVENTORY_BATCH_10_QC.md` records a local browser session.
  Staging is honest; the QC prose is not a machine-owned PASS.

## 5. Per-machine disposition

| Machine | Disposition | Basis (inspected) |
| --- | --- | --- |
| Cat 950 | **Admit with M4** | Envelope 8.479 / 3.457 / 2.994 m vs shipping 8.487, ROPS 3.456, bucket 2.994 m. 460 / 424 / 123,224. Carry, dump, L3 wheel, articulation readable; named Z-bar details are not. |
| Cat D6 | **Admit** | Envelope 5.436 / 3.188 / 3.312 m matches straight-blade / height / 6SU width. 752 / 731 / 107,532. 42-section track, 8 rollers, push-arm 6SU, raised/tilt pose. Sprocket phase reconstructed (PENDING). Style matches Cat 320. |
| Cat 725 | **Admit with M3** | Envelope 10.4525 / 3.4967 / 3.676 m vs 10.445 / 3.498 / 3.676 m. 843 / 814 / 131,088. Three-axle ADT, ~70° body, hoist cylinders. Knuckle render is stairs. |
| Cat 140 | **Admit** | Envelope 10.297 / 3.454 / 3.658 m exact to push-plate–ripper / cab / 12 ft moldboard. 1,358 / 1,305 / 224,404. Isolated 64-tooth circle, 6 shoes, tandem, lean/articulation study. Strongest inspected mechanism evidence. |
| Deere 1270G 8W | **Admit with M2** | Partial envelope only (Z). Working-pose AABB ≠ transport. 442 / 424 / 73,956. 8-wheel carrier, CH7, H480C-style head readable; transport facts still in the viewer. |
| Deere 470 P-Tier | **Admit** | Envelope 12.01 / 3.50 / 3.795 m vs 12.01 / 3.50 / 3.79 m. 470 / 437 / 85,688. Transport and articulated poses, bucket linkage, 53-shoe undercarriage. Bucket-table conflict documented, not silently resolved. |
| Bobcat S76-2 | **Admit with M5** | Envelope 3.61181 / 2.08 / 1.8796 m vs 3.6068 / 2.08026 / 1.8796 m. 250 / 247 / 14,360. Recognizable vertical-lift SSL; public mesh and tire/linkage detail below batch peers. |
| Komatsu WA475-10 | **Contract-admissible; visual PENDING** | Envelope 9.183 / 3.546 / 3.17 m vs 9.185 / 3.54 / 3.17 m. 413 / 407 / 53,132. Hierarchy and Z-bar/steer semantics declared. **No PNG read.** |
| Volvo DD128C | **Contract-admissible; visual PENDING** | Envelope 5.973 / 3.177 / 2.218 m exact. 328 / 325 / 62,024. Drum/spray/wiper counts and ±40°/±10° endpoints declared. Dimension D unresolved (correct). **No PNG read.** |
| Liebherr LTM 1100-5.3 | **Admit contracts only, with M1; visual PENDING** | Receipt 15.095 / 4.001 / 2.535 m vs 14.932 / 4.0 / 2.55 m. 627 / 599 / 108,936. 100 t bounded as identity. Five-axle / 10-wheel / boom-section semantics declared. **No PNG read.** |

## 6. Shared viewer / evidence / privacy disposition

**Viewer (code, not re-run in a browser):** `assets/site/app.js` hash-binds
`definition.glb?sha256=`, SHA-256-checks bytes, aborts superseded loads
(`loadToken` / `AbortController`), admits only after identity + parse +
`assertViewerContract` (single identity root, no embedded cameras, visible
meshes), swaps atomically, and on failure keeps the current model (`… remains
loaded`). Camera fit uses AABB + narrow-aspect scale. Reduced-motion disables
auto-orbit. Tab order matches `catalog.json` / `index.html` /
`EXPECTED_MACHINE_ORDER` in `scripts/validate-site.mjs`. Forbidden tokens
`research/private/`, `file://`, `/Users/`, CDN, `gltfRotationX` are gated for
`index.html` and `app.js`.

**Evidence:** Authority classes in facts/joints match
`docs/EVIDENCE_POLICY.md`. Reconstructed joints declare `unresolved`.
`release_state` remains `no_geometry_no_solver_no_claim`. Catalog
public-envelope rules require `manufacturer_published` metre facts; 1270G and
333 P-Tier are the only partial mappings.

**Privacy / public build:** `scripts/build-site.mjs` copies HTML/CSS/JS, vendor
three r160, `catalog.json`, and per machine only GLB + `configuration.json` +
`facts.json` + receipt + validation. It does **not** copy `mechanism.json`,
`source-manifest.json`, Blender sources, or review PNGs. `facts.json` does ship
PDF page citations; that is not a binary leak. Private paths live in source
manifests, which are not public-build inputs.

**Production validator (unread against live GLB in this pass):** Independent
GLB parse, identity root, helper-name reject, no cameras/lights/textures, receipt
triangle match, receipt AABB 0.02 m, catalog envelope, semantic-node presence,
≥200/180/10k/5 floors. Snapshot cannot satisfy blend-hash checks because
`.blend` files are excluded; QC’s `npm run check:production PASS` is **not
re-verified here**.

## 7. PENDING / limitations that must remain disclosed

- **`check:sources` PENDING.** Ten declared private binaries are absent;
  unavailable hashes are warnings, not PASS
  (`docs/INVENTORY_BATCH_10_QC.md`, `scripts/validate-repository.mjs`).
- **No byte-for-byte Blender rebuild identity** (Cat 950 and peers explicitly
  PENDING).
- **No kinematic solver, cylinder-stroke authority, linkage closure across
  poses, or load/stability model** on any machine.
- **No ground / self / swept-volume collision solver.**
- **No track-phase, boom-staging, Telematik, VarioBase, eccentric-phase, or
  Ackermann qualification.**
- **Viewer/browser/accessibility/mobile/selection/performance** remains PENDING
  in each machine `validation.json`. QC browser notes at
  `http://127.0.0.1:4173/` were not reproduced in this pass.
- **Git commit, push, Pages deploy, and public-URL byte verification** are not
  established.
- **This critic pass did not hash GLBs or renders, did not decode public-GLB
  AABB, and did not inspect Komatsu / Volvo / Liebherr PNGs or any public GLB
  JSON.** Those gaps stay disclosed; they are not silent PASS.
- Public materials are **unofficial, unbranded, not endorsed**; reconstructed
  geometry is not manufacturer CAD or engineering authority.
- 1270G retained pose is a **working-pose study**, not a transport-envelope
  proof.
- Liebherr **100 t is product-class identity only**; deployed 42° / ~28 m boom
  is a review pose, not a load case.
- Deere 470 **2.34 m³ / 1370 mm operating-weight bucket vs 2.01 m³ / 1372 mm
  table** remains an open publication conflict.

A structural-study gallery of thirteen research candidates can ship with the
MEDIUM items above recorded. It cannot be described as solver-qualified,
visually complete for all ten new machines, or as having a closed Liebherr
X-envelope.
