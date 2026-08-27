# EXO Equipment Atlas

EXO Equipment Atlas is a manufacturer-neutral foundation for independently
authored, mechanically meaningful heavy-equipment explorers. It extracts the
repeatable evidence and validation method proven in the JLG equipment case
studies without copying the JLG runtime or its dirty working state.

The repository begins with three research candidates:

1. Cat 320 hydraulic excavator — flagship mechanism candidate.
2. John Deere 333 P-Tier compact track loader — first production candidate.
3. John Deere 310 P-Tier backhoe loader — later multi-mechanism hero candidate.

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
a mechanical release. All three machine packages remain `research_candidate`.
The web viewer presents the admitted neutral GLBs and evidence boundaries; it
does not promote them to solved mechanisms, engineering data, or manufacturer
authority.
