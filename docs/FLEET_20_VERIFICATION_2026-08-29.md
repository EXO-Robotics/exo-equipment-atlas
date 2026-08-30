# Fleet Expansion 20 Verification — 2026-08-29

## Exact candidate

- Catalog size: 33 machines (13 retained + 20 added).
- Shared new-machine builder SHA-256:
  `02b99250651741b462b3dae8b2471db723beb689dfe89e1c7e251d7402fe0f55`.
- Candidate boundary: independently authored, neutral, unbranded technical
  structural studies. They are not manufacturer CAD, engineering digital
  twins, load guidance, operator training, or safety authority.

## Automated gates

```text
npm test                  PASS — 16/16
npm run check             PASS — 33 machines, 78 sources, 802 facts
npm run check:sources     PASS — 35/35 private hashes verified
npm run check:production  PASS — 33 blends, 33 GLBs, 233 renders,
                                  11,310 GLB nodes, 10,589 mesh nodes,
                                  1,745,880 decoded triangles
npm run check:site        PASS — 33 viewer contracts, 232 public files
```

## Direct artifact review

- One or more direct 640×480 review renders were inspected for every new
  machine.
- First-pass detached witness rails, floating headers/tailgate, an open hauler
  articulation, and a detached excavator boom cylinder were rejected and
  rebuilt before the final generator hash was frozen.
- A stricter final audit then rejected five machine-specific issues: the JCB
  front-linkage omission, a merged KRONE mower-deck hierarchy, the Vermeer
  pickup at the wrong end of the feed path, a Volvo hoist/bed intersection, and
  missing Komatsu arm/bucket actuation hardware. All five packages were rebuilt
  locally without changing the frozen shared generator.
- Final representative renders show attached machine assemblies and retain
  neutral procedural materials with no logos or copied textures.
- A final independent pass inspected all 30 current renders for those five
  repaired machines and found no remaining technical-structural-study visual
  blocker. This visual result does not promote any package to manufacturer CAD
  or a solved mechanical candidate.
- Grok subsequently identified and verified fixes for two required-node
  contract gaps, five missing static-fallback posters, one ignored source
  orphan, and a detached Fendt 1167 rear interface. The Fendt repair now has a
  fail-closed 1 mm continuity gate and a measured 0.046876 m minimum overlap.

## Grok review

Grok's final read-only verdict is **SHIP WITH CARRIED PENDING**, with no
remaining Blocker, High, or Medium finding. See
[`GROK_FLEET_20_REVIEW_2026-08-30.md`](GROK_FLEET_20_REVIEW_2026-08-30.md).

## Local HTTP smoke proof

- `/`: `200`, 9,772 bytes.
- `/?machine=john-deere-x9-1100`: `200`, identical static shell.
- `/machines/john-deere-x9-1100/viewer.json`: `200`, matching machine id and
  enabled autoplay contract.
- `/research/private/john-deere-x9-1100/primary-source.pdf`: `404`, confirming
  ignored private research is absent from the public bundle.

## Browser interaction boundary

`PENDING`: the configured in-app browser reported no available browser backend
in this session. Therefore desktop/mobile visual layout, pointer/keyboard
selection, reduced-motion media-query behavior, and live WebGL animation were
not marked PASS. Static/runtime validators, motion unit tests, HTTP checks, GLB
node-contract checks, and direct Blender render inspection passed independently.
