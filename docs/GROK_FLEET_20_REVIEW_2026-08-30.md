# Grok fleet-20 shipment review — 2026-08-30

## Review identity

- Reviewer: Grok CLI `1.0.5 (5115b46bc909)`.
- Read-only session: `01a04e5a-0881-7f93-9eda-4ef12571e6bc`.
- Candidate: uncommitted `codex/atlas-20-machine-expansion` working tree,
  subsequently hardened in response to the review.
- Permission boundary: read-only Grok sandbox; no files were edited by Grok.

## Initial review outcome

Grok independently reproduced the 33-machine catalog, 78 sources, 802 facts,
35/35 private hashes, 33 Blend/GLB packages, 233 renders, 16/16 tests, motion
contracts, source boundaries, and Pages manifest workflow. Its initial verdict
was **SHIP WITH CARRIED PENDING**, with no Blocker or High finding.

It raised two Medium findings:

1. The repaired JCB linkage/PTO and Komatsu actuation nodes were not all listed
   in their production required-node contracts.
2. JCB Category 3N wording was stronger than the admitted page-bound evidence.

It also noted missing posters on five farm viewers, one undeclared ignored Case
IH HTML download, and a visually detached Fendt 1167 rear interface.

All actionable findings were corrected before the final follow-up review.

## Exact final Grok response

> **SHIP WITH CARRIED PENDING**
>
> Focused reinspection and re-run gates: `npm test` 16/16; `check:sources`
> 33 / 78 / 802 / **35/35**; production 33 blends/GLBs, 233 renders,
> 11,310 / 10,589 / 1,745,880; site 33 viewer contracts. Public bundle is now
> **232 files** (previous 227 plus the five posters). That count change is the
> poster fix, not a regression.
>
> ## Prior findings: disposition
>
> | Prior finding | Status |
> | --- | --- |
> | **Medium 1** — JCB repaired hitch/PTO/rear-axle nodes missing from production required-node contract; Komatsu actuation chain not required | **Resolved** |
> | **Medium 2** — JCB Category 3N treated as a published class | **Resolved** |
> | **Low** — five farm machines lacked `viewer.assets.poster` | **Resolved** |
> | **Low** — unbound Case IH HTML orphan | **Resolved** |
> | **Low** — Fendt 1167 rear hitch read as detached in side view | **Resolved** |
>
> **JCB Mediums.** Receipt and `required-semantic-nodes` now list the same 27
> nodes, including `Front_Hitch_*`, `Front_Hitch_Coupler`,
> `Rear_Hitch_{L,R}_Lower_Link` / `Top_Link` / `Coupler`, `Rear_Axle_ROOT`, and
> `Rear_540E_1000_PTO_Shaft` (`asset-receipt.json:128-154`,
> `validation.json:158-187`). All 27 are present in the GLB. Public wording
> denies a published 3N claim: configuration choice is
> `optional_3500_kg_front_lift_selected_with_reconstructed_three_point_presentation`
> (`configuration.json:18,37`); viewer label is “Selected front linkage study”
> (`viewer.json:16,31`); facts issue `front-linkage-presentation`
> (`facts.json:28`). Remaining “Category 3N” strings are explicit denials only.
>
> **Komatsu Medium.** Receipt requires 38 nodes covering
> crowd/curl/H-link/dogbone/pin/clevis/ear (`asset-receipt.json:127-166`); all
> 38 exist in the GLB. Production admission uses
> `receipt.required_semantic_nodes` (`validate-production-assets.mjs:466-467`)
> and PASSed. Dedicated gate `komatsu-visible-actuation-chain` PASSes the full
> parent chain as reconstructed static visual closure
> (`validation.json:317-353`).
>
> **Posters.** All 20 new machines now have an on-disk `assets.poster`. The five
> previously missing point at existing front-three-quarter renders. `_site`
> contains 20 PNGs.
>
> **Orphan.** `research/private/case-ih-axial-flow-8250/` is only
> `primary-source.pdf`. 35 private files, 35 declared hashes, 0 orphans, all
> hashes match.
>
> **Fendt.** Side/right renders now show a continuous rear hitch/drawbar into
> the chassis. Machine-local builder fail-closes below 1 mm XYZ overlap
> (`build_fendt_1167_vario_mt.py:28,76-78,88-90`). Gate
> `fendt-rear-interface-continuity` PASSes: required `0.001` m, measured minimum
> **`0.046876` m**, with reconstructed/non-engineering authority
> (`validation.json:310-390`).
>
> ## Remaining Blocker / High / Medium
>
> None independently proven on this disk state.
>
> ## Carried PENDING (only these, before commit/deploy)
>
> 1. **Live browser interaction** — desktop/mobile layout, pointer/keyboard,
>    live reduced-motion, live WebGL. Still unexecuted; not a content blocker.
> 2. **Live Pages exact-byte/source-commit proof** — workflow and verifier remain
>    sufficient. This tree is still uncommitted/undeployed. **Complete Pages
>    proof after push**, not before: checkout of `github.sha`, attest `_site` to
>    that commit, deploy, then `verify-deployed-pages.mjs --expected-commit` and
>    `--expected-manifest`.
>
> Structural-study limits (reconstructed joints, PENDING higher-stage gates, not
> manufacturer CAD/engineering/safety authority) stay limitations, not defects.

## Release interpretation

Grok's final verdict authorizes this candidate only as a public research gallery
of independently authored technical structural studies. Browser interaction
remains PENDING by explicit session/tool boundary. GitHub Pages deployment and
exact-byte/source-commit proof must be completed against the final pushed SHA.
