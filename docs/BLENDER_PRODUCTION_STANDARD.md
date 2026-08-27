# Blender production and review standard

This standard governs independently authored machine assets before they can be
admitted to the EXO Equipment Atlas viewer. A Blender file or GLB is evidence
of authoring work, not proof that a configuration, mechanism, or release is
correct.

## Candidate classes

- `technical_structural_study`: allowed while the configuration remains a
  `research_candidate`. Published dimensions may constrain the study, but
  unresolved options, hidden pivots, anchors, and linkage geometry remain
  explicitly reconstructed or unresolved.
- `mechanical_candidate`: allowed only after the exact configuration is frozen
  and the machine-specific solver and geometry gates pass.
- `visual_candidate`: a mechanical candidate with direct-render human review
  bound to exact artifact hashes.
- `release_candidate`: a visual candidate that also passes viewer, browser,
  accessibility, mobile, selection, performance, and release-receipt gates.

No lane may skip a class or use the output of one class as proof of a later
class.

## Deterministic authoring contract

Each machine owns these paths:

```text
machines/<machine>/
  source/blender/build_<machine>.py
  source/blender/<machine>-structural-study.blend
  assets/<machine>-structural-study.glb
  production/asset-receipt.json
  production/validation.json
  review/renders/*.png
```

The build must run with Blender's factory startup in background mode. It must
start from an empty scene, declare units and axes, create all geometry and
materials deterministically, save the `.blend`, export the GLB, render the
review views, and write machine-readable receipts. Network access, downloaded
geometry, manufacturer CAD, copied textures, and opaque add-ons are prohibited.

## Geometry and hierarchy

- Use meters and the coordinate system declared by `mechanism.json`.
- Separate fixed structure, articulated groups, visible hydraulic elements,
  linkage elements, collision proxies, inspection volumes, and pivot markers.
- Use stable semantic names. Decorative object names cannot satisfy required
  mechanical nodes.
- Parent each moving group at its intended pivot. A visual mesh translated
  around an unrelated origin does not count as articulation.
- Keep manufacturer-published dimensions separate from reconstructed modeling
  values in both code and receipts.
- Apply realistic bevels, thickness, fastening cues, glass boundaries, wheel or
  track construction, and service-panel segmentation where evidence supports
  the visible form. Do not fabricate hidden internal assemblies.
- Public-facing materials remain neutral and unbranded unless written rights
  approval is attached to the release.

## Required structural-study receipt

`production/asset-receipt.json` must contain:

- schema, machine, and exact configuration identity;
- candidate class and a statement that it is not engineering authority;
- Blender version and deterministic builder path plus SHA-256;
- `.blend` and GLB paths, SHA-256 hashes, and byte counts;
- scene units, axes, bounds, object/mesh/triangle/material counts;
- required semantic nodes and whether each is present;
- manufacturer-published constraints used by id;
- every reconstructed dimension, pivot, anchor, or range used by the builder;
- unresolved choices and mechanical gaps carried from the source contracts;
- render paths and hashes;
- build and validation verdicts.

`production/validation.json` must list individual gates with `PASS`, `FAIL`, or
`PENDING`. A missing or inapplicable higher-stage gate is `PENDING`, never a
synthetic pass.

## Critic gate

The overall critic reviews the exact hashes in the receipt and may reject a
candidate even when its scripts pass. Review includes:

1. configuration and source applicability;
2. published envelope and endpoint checks;
3. hierarchy, pivot placement, and articulation continuity;
4. cylinder and linkage visual closure;
5. ground, self, and swept-volume collision risks;
6. recognizable silhouette and machine-specific construction;
7. direct PNG inspection from multiple angles and at least one articulated
   pose;
8. neutral-rights boundary and absence of copied manufacturer assets;
9. receipt completeness and exact artifact hashes.

Geometry counts, screenshots, or an attractive render cannot substitute for
mechanical review.

## Publication gate

Only the overall publisher may change a catalog release state, admit a GLB to a
shared viewer, create a release receipt, push a publication commit, or claim a
deployed result. Publication requires the full proof ladder in
`EVIDENCE_POLICY.md`; these initial structural studies remain private research
artifacts until they qualify.
