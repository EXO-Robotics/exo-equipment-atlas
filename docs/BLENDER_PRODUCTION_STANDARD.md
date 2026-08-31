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
- Author dimensions and pivots directly in metres. Non-uniform post-build
  stretching to force an outer AABB is prohibited. Every exported hierarchy
  node, not only mesh leaves, must remain free of scale and shear.
- A semantic motion root must own visible mesh descendants. An empty node is
  permitted only when the receipt classifies it explicitly as a datum, joint,
  or identity marker; marker names cannot satisfy a motion gate.
- Every `viewer.json` motion channel names its exact `mechanism.json` joint via
  `mechanismJointId`. The viewer axis must agree with the declared joint axis;
  rotational targets use a neutral base rotation and all targets use identity
  scale so browser and independent motion sampling evaluate the same transform.
- Keep manufacturer-published dimensions separate from reconstructed modeling
  values in both code and receipts.
- Apply realistic bevels, thickness, fastening cues, glass boundaries, wheel or
  track construction, and service-panel segmentation where evidence supports
  the visible form. Do not fabricate hidden internal assemblies.
- Public-facing materials remain neutral and unbranded unless written rights
  approval is attached to the release. Independent decoded-surface auditing
  limits bright chromatic material to restrained visibility cues (at most 8%
  of modeled surface), so a signature body color cannot pass by calling itself
  “neutral.”

## Required structural-study receipt

`production/asset-receipt.json` must contain:

- schema, machine, and exact configuration identity;
- candidate class and a statement that it is not engineering authority;
- Blender version and deterministic builder path plus SHA-256;
- `.blend` and GLB paths, SHA-256 hashes, and byte counts;
- scene units, axes, bounds, object/mesh/triangle/material counts;
- required semantic nodes and whether each is present;
- published constraint IDs declared by the design plus their machine-gate
evidence bindings; do not label copied ID lists as constraints “used”;
- every reconstructed dimension, pivot, anchor, or range used by the builder;
- unresolved choices and mechanical gaps carried from the source contracts;
- render paths and hashes;
- build and validation verdicts.

`production/validation.json` must list individual gates with `PASS`, `FAIL`, or
`PENDING`. A missing or inapplicable higher-stage gate is `PENDING`, never a
synthetic pass.

Every ID in `mechanism.json.required_gates` must appear exactly once and PASS
for structural-study admission. Its detail object records an explicit method,
measured evidence, semantic nodes, and source fact IDs. `PENDING` is acceptable
for a later engineering/release gate, but never for a required structural gate.
Every cited node and fact must resolve in the exact exported package, and the
receipt's gate IDs, evidence objects, and verdicts must exactly match validation.

All published viewers share the 600S presentation cadence: Auto enabled, an
18-second sine cycle, and damping 8. Machine choreography remains specific to
the documented mechanism. Independent production validation evaluates every
channel endpoint plus 37 synchronized Auto samples against decoded GLB geometry
and rejects ground-plane penetration; this presentation sweep is not a dynamics,
load, stability, self-collision, or safety solver.

## Critic gate

The overall critic reviews the exact hashes in the receipt and may reject a
candidate even when its scripts pass. Review includes:

1. configuration and source applicability;
2. published envelope and endpoint checks;
3. hierarchy, pivot placement, and articulation continuity;
4. cylinder and linkage visual closure;
5. ground, self, and swept-volume collision risks;
6. recognizable silhouette and machine-specific construction;
7. direct inspection of at least six unique decoded PNGs from multiple angles,
   including neutral and relevant articulated endpoints;
8. neutral-rights boundary and absence of copied manufacturer assets;
9. receipt completeness and exact artifact hashes.

Geometry counts are integrity floors only. Repeated fasteners, tread instances,
duplicate renders, or an attractive screenshot cannot substitute for component
coverage, sampled motion, source applicability, or mechanical review.

## Publication gate

Only the overall publisher may change a catalog release state, admit a GLB to a
shared viewer, create a release receipt, push a publication commit, or claim a
deployed result. Publication requires the full proof ladder in
`EVIDENCE_POLICY.md`; these initial structural studies remain private research
artifacts until they qualify.
