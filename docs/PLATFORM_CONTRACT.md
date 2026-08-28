# Platform contract

Each machine package supplies identity, evidence, mechanics, presentation, and
validation data. The shared viewer owns rendering, input, cameras, selection,
accessibility, responsive controls, diagnostics, and receipt loading.

## Viewer asset contract v1

Every admitted public GLB must satisfy all of the following before the viewer
loads it:

- glTF 2.0 with the normative glTF coordinate convention: right-handed, +Y up;
- machine longitudinal axis +X toward the primary front tool and lateral axis
  +Z toward machine right;
- exactly one node referenced directly by the default scene;
- that scene root has identity translation, rotation, and scale (omitted values
  count as identity); the viewer never applies a per-machine corrective rotation;
- all production meshes are descendants of that one root;
- every public mesh node has identity local scale within `1e-4`; applied or
  sheared mesh transforms are rejected even when the overall AABB looks valid;
- no glTF cameras, punctual lights, review planes, measurement witnesses,
  collision proxies, inspection volumes, or other authoring helpers are shipped
  as visible public meshes;
- position accessors provide finite min/max values; the independent validator
  decodes every POSITION vertex and composes node transforms to reconstruct the
  visible world-space AABB without Blender or receipt code;
- the independently measured AABB agrees with the receipt's declared visible
  bounds within the documented tolerance;
- the validator derives triangle count from each reachable GLB primitive and
  requires an exact match with the public receipt value consumed by the UI.

Receipt min, max, and size coordinates use a 0.02 m absolute tolerance. The
authoritative envelope checks and their tighter or looser machine-specific
tolerances are declared in `scripts/validate-production-assets.mjs` next to the
fact IDs they bind; a dimension is checked only when the public fact describes
the complete visible-machine extent in that axis.

This contract deliberately fixes export orientation at the asset boundary.
Correcting one machine in JavaScript would hide an export defect and make
camera, ground, selection, and future mechanism behavior inconsistent.

## Public-state contract

The viewer may publish a `research_candidate` as an explicitly bounded
`technical_structural_study`. It must display PASS, PENDING, and FAIL counts
separately. A PASS structural-study verdict does not advance configuration,
mechanical solver, collision, human review, browser release, deployment,
engineering, safety, training, or manufacturer-endorsement gates.

The viewer provides a complete-machine technical side camera, a discoverable
keyboard-focusable viewer region, documented arrow/zoom/Home controls, a mobile
navigation path, and WAI-ARIA tabs with roving focus and arrow/Home/End behavior.
On narrow screens, noninteractive hero copy does not intercept pointer input;
the canvas retains a clear hit region and a compact visible drag/pinch legend.

The displayed validation verdict is a declared input classification, never the
sole proof of an artifact. Publication checks independently decode geometry,
transforms, topology, dimensions, receipts, hashes, hierarchy, and helpers.

Machine-specific modules will own:

- exact configuration and asset identity;
- required hierarchy and interaction volumes;
- controls, stow state, motion limits, and solver behavior;
- component inspection definitions and camera poses;
- mechanical closure, invariant, collision, and envelope gates.

Shared rendering, camera, input, and validation primitives must not special-case
manufacturer names, configuration IDs, node names, or motion ranges. A machine
catalog adapter may supply presentation labels and evidence prose. Generic node
presence cannot substitute for a machine-specific mechanical gate.
