# EXO Equipment Atlas

EXO Equipment Atlas is a manufacturer-neutral foundation for independently
authored, mechanically meaningful heavy-equipment explorers. It extracts the
repeatable evidence and validation method proven in the JLG equipment case
studies without copying the JLG runtime or its dirty working state.

The repository contains thirty-three research candidates across construction,
forestry, lifting, roadbuilding, and agricultural mechanism classes. The
original thirteen-machine foundation is:

1. Cat 320 hydraulic excavator.
2. John Deere 333 P-Tier compact track loader.
3. John Deere 310 P-Tier backhoe loader.
4. Cat 950 articulated wheel loader.
5. Cat D6 track-type tractor.
6. Cat 725 articulated truck.
7. Cat 140 motor grader.
8. John Deere 1270G 8W wheeled harvester.
9. John Deere 470 P-Tier hydraulic excavator.
10. Bobcat S76-2 skid-steer loader.
11. Komatsu WA475-10 articulated wheel loader.
12. Volvo DD128C tandem asphalt compactor.
13. Liebherr LTM 1100-5.3 all-terrain mobile crane.

The twenty-machine farm expansion adds tractors, tracked tractors, combines,
forage harvesters, a high-clearance applicator, balers, a mower-conditioner,
and two complementary earthmoving studies. The exact roster, market/configuration
boundaries, and interaction thesis are recorded in
[`docs/FLEET_EXPANSION_20.md`](docs/FLEET_EXPANSION_20.md).
The independent Grok shipment review and finding dispositions are recorded in
[`docs/GROK_FLEET_20_REVIEW_2026-08-30.md`](docs/GROK_FLEET_20_REVIEW_2026-08-30.md).

## Non-negotiable boundaries

- One exact configuration must be frozen before geometry production begins.
- Every numeric or mechanical claim is classified as manufacturer-published,
  evidence-derived, reconstructed, observed, or unresolved.
- Manufacturer PDFs, imagery, CAD, and geometry are not committed.
- Cross-market and cross-configuration sources remain references, not truth for
  the active machine.
- A static model, local validator, browser capture, and deployed release are
  separate proof stages.
- These experiences are product visualizations, not engineering digital twins,
  load charts, operator training, or safety authority.

## Repository map

```text
catalog.json                     catalog order and release state
machines/<machine>/
  configuration.json            exact target choices and unresolved options
  mechanism.json                joints, motion authority, and solver gates
  evidence/source-manifest.json official sources and frozen binary identity
  evidence/facts.json           page-bound fact register
  source/blender/               deterministic independent authoring scripts
  production/                   asset receipts and explicit gate results
  review/renders/               direct visual-review evidence
schemas/                         documented JSON contracts
scripts/validate-repository.mjs  fail-closed repository and source validator
scripts/fleet/                   shared deterministic neutral-study builder
scripts/generate-public-manifest.mjs exact public bundle attestation
scripts/verify-deployed-pages.mjs deployed SHA-256 and source-commit verifier
research/private/                gitignored manufacturer research inputs
docs/                            evidence, rights, and platform policies
```

## Validation

```bash
npm run check
npm test
npm run check:sources
npm run check:production
npm run check:site
```

The first two commands validate tracked contracts. `check:sources` additionally
requires the private PDFs to exist locally and match the tracked SHA-256 hashes.

## Current state

This is a research foundation with a public-facing structural-study gallery, not
a mechanical release. All thirty-three machine packages remain
`research_candidate`. The catalog-driven web viewer presents admitted neutral
GLBs, searchable fleet filters, stable deep links, and capability-driven motion
channels with a six-second manual override. It does not promote reconstructed
motion to solved mechanisms, engineering data, or manufacturer authority.
