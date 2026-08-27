# Evidence policy

## Authority classes

- `manufacturer_published`: directly stated in a configuration-applicable
  first-party publication.
- `evidence_derived`: calculated from admitted manufacturer facts with the
  derivation recorded.
- `reconstructed`: independently selected geometry or motion needed for a
  coherent visualization but not published by the manufacturer.
- `observed`: a visual observation from first-party imagery, not a dimension.
- `unresolved`: unknown, conflicting, or not yet configuration-bound.

Manufacturer-published facts may constrain a reconstruction. They do not turn
hidden pivot positions, anchor locations, mesh dimensions, or interpolation
curves into manufacturer facts.

## Source admission

Each source records publisher, document identity, market/configuration scope,
official URL, retrieval date, local filename, SHA-256, byte count, page count,
and admission status. A source is `primary` only when its applicability matches
the target configuration. Other sources must be `visual_only`, `reference_only`,
or `quarantined`.

Downloaded publications stay in `research/private/`. The repository validator
can prove their hashes when present but normal tracked validation does not claim
that private evidence is universally available.

## Proof ladder

1. Configuration freeze.
2. Source and fact admission.
3. Independently authored hierarchy, pivots, and geometry.
4. Deterministic asset build and receipt.
5. Machine-specific mechanical and collision gates.
6. Browser, accessibility, mobile, performance, and selection gates.
7. Human visual review bound to the exact candidate.
8. Deployment and exact-byte verification.

No lower stage substitutes for a higher one.
