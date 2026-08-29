# Inventory batch 10 — pre-Grok quality record

Date: 2026-08-29

Scope: the ten-machine expansion identified in `INVENTORY_BATCH_10.md`, plus
the shared thirteen-machine catalog, evidence contracts, static site, and 3D
viewer. This record is pre-release evidence for a technical structural-study
gallery. It is not engineering, safety, training, load-chart, or manufacturer
authority.

## Package review

| Machine | Shipped GLB evidence | Targeted visual/mechanical review |
| --- | --- | --- |
| Cat 950 | 460 nodes, 424 mesh nodes, 123,224 triangles | L3 tread, wheel dishes, cab/access framing, counterweight, grille, and raised/stowed Z-bar cues |
| Cat D6 | 752 nodes, 731 mesh nodes, 107,532 triangles | segmented drive sprockets, visible links/pins, track engagement, blade, and rear work-tool structure |
| Cat 725 | 843 nodes, 814 mesh nodes, 131,088 triangles | stepped hood/cab silhouette, six treaded tires, articulation, scow body, hinge, and raised-body hoist |
| Cat 140 | 1,358 nodes, 1,305 mesh nodes, 224,404 triangles | tandem running gear, 64-tooth circle, guide contacts, pinion, moldboard, and isolated circle-drive view |
| John Deere 1270G 8W | 442 nodes, 424 mesh nodes, 73,956 triangles | eight-wheel carrier, articulated chassis, rotating upper structure, crane, and harvester-head study |
| John Deere 470 P-Tier | 470 nodes, 437 mesh nodes, 85,688 triangles | tracked undercarriage, upper structure, 7.0 m boom, 3.9 m arm, bucket, cylinders, and hose-routing cues |
| Bobcat S76-2 | 250 nodes, 247 mesh nodes, 14,360 triangles | enclosed cab cage, four treaded tires, vertical-path lift linkage, bucket, and compact service envelope |
| Komatsu WA475-10 | 413 nodes, 407 mesh nodes, 53,132 triangles | articulated chassis, tires, ROPS/FOPS cab, standard boom, Z-bar cues, stock-pile bucket, and full-lift pose |
| Volvo DD128C | 328 nodes, 325 mesh nodes, 62,024 triangles | tandem drums, articulation joint, open ROPS/FOPS station, spray-system cues, and straight transport pose |
| Liebherr LTM 1100-5.3 | 627 nodes, 599 mesh nodes, 108,936 triangles | five-axle carrier, transport-height envelope, boom-head reeving/hook, cab/wheel-well cues, and outrigger continuity |

The complete thirteen-machine production set contains 7,003 scene nodes,
6,724 mesh nodes, 1,159,132 decoded triangles, and 113 receipt-hashed review
renders. Each new machine has an independently authored `.blend`, a public GLB,
configuration/mechanism/evidence records, a receipt, and explicit PASS/PENDING/
FAIL validation results.

## Shared contract corrections completed before final review

- Catalog, HTML tabs, JavaScript definitions, priorities, IDs, order, and
  canonical asset paths must agree exactly for all thirteen machines.
- A malformed or non-manufacturer-published public-envelope mapping fails
  production validation instead of silently bypassing dimensional checks.
- Every machine declares a primary first-party source with a private path,
  SHA-256, byte count, access policy, and redistribution boundary.
- Superseded viewer loads are aborted. The current study remains visible until
  replacement evidence and GLB bytes are fetched, identity-checked,
  browser-hashed, parsed, and admitted atomically.
- GLB request URLs are receipt-hash-bound. Loading, retained-study failure,
  reduced-motion, keyboard, and ARIA states are explicit.
- Bounds-aware desktop and mobile camera fitting keeps long machines inside the
  canvas while retaining the JLG-style full-viewport presentation.
- Production admission floors require at least 200 nodes, 180 mesh nodes,
  10,000 decoded triangles, and five receipt-hashed renders per machine.

## Browser proof

Local static build: `http://127.0.0.1:4173/`

- Desktop: 1280 × 900. Cat 320 and Deere 470 P-Tier loaded with visible full
  silhouettes; technical-side, reset-view, and orbit controls responded.
- Narrow phone: 390 × 844. All ten new tabs completed `study loaded` with a
  canvas present and the selected tab/identity synchronized. Cat 140 and the
  LTM 1100-5.3 retained their complete long silhouettes after the final camera
  correction.
- Screenshot-matched phone width: 643 × 1280. Cat 320 loaded with the full
  excavator visible, including both track frame and bucket.
- Rapid selection: an immediate Cat 725 → Cat 140 change cancelled the first
  request and settled on Cat 140 without a blank or error state.
- Synthetic failure retention: aborting only the S76-2 GLB request left Cat 140
  visible and reported `S76-2 unavailable · Cat 140 remains loaded`; removing
  the route allowed S76-2 to load normally.
- Browser errors and console were empty before the deliberate failure test.

## Local gates

The final pre-Grok run must retain these results:

```text
npm test                  PASS — 7/7 tests
npm run check             PASS — 13 machines, 32 sources, 369 facts
npm run check:production  PASS — 13 GLBs, 113 renders, 1,159,132 triangles
npm run check:site        PASS — 77 public files
git diff --check          PASS
```

`npm run check` reports honest availability warnings for ten private source
binaries that are not present in this checkout. Seven of seventeen declared
private source hashes are locally verifiable. The stricter `check:sources` gate
therefore remains PENDING; unavailable private evidence is not represented as
PASS and is not included in the public site.

## Remaining boundaries

- Mechanism solvers, swept collision, hydraulic authority, load behavior, and
  operator/safety qualification remain PENDING unless a machine-specific gate
  explicitly says otherwise.
- Exact branded liveries, manufacturer logos, copied imagery, CAD, and private
  source documents are excluded from the public build.
- Final Grok review is one read-only technical pass after this record and all
  local/browser gates are complete. Its findings are recorded without a
  post-review repair loop.
- Git commit, push, Pages deployment, and public-URL verification are separate
  proof stages and are not established by this pre-Grok record.
