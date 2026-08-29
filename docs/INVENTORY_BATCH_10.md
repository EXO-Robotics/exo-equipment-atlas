# Inventory expansion batch 10

This batch expands EXO Equipment Atlas from three to thirteen independently
authored technical structural studies. The roster is deliberately mixed across
mechanism classes so the platform is proving reusable equipment logic rather
than repeated skins.

| Lane | Machine ID | Display identity | Mechanism class | First-party research anchor |
| --- | --- | --- | --- | --- |
| 01 | `cat-950` | Cat 950 | articulated wheel loader | Caterpillar 950 (14C) product page and technical specifications |
| 02 | `cat-d6` | Cat D6 | crawler dozer | Caterpillar D6 product page and 2025 D6 specification release |
| 03 | `cat-725` | Cat 725 | articulated dump truck | Caterpillar 725 product page and next-generation truck specifications |
| 04 | `cat-140` | Cat 140 | motor grader | Caterpillar 140 product page and technical specifications |
| 05 | `john-deere-1270g` | 1270G 8W | wheeled harvester | John Deere 1270G wheeled harvester specification sheet |
| 06 | `john-deere-470-p-tier` | 470 P-Tier | hydraulic excavator | John Deere 470 P-Tier construction specification sheet |
| 07 | `bobcat-s76-2` | S76-2 | skid-steer loader | Bobcat North America S76-2 product page and dimensions |
| 08 | `komatsu-wa475-10` | WA475-10 | articulated wheel loader | Komatsu WA475-10 AESS942 specification brochure |
| 09 | `volvo-dd128c` | DD128C | tandem asphalt compactor | Volvo Construction Equipment DD128C brochure and product page |
| 10 | `liebherr-ltm-1100-5-3` | LTM 1100-5.3 | five-axle all-terrain crane | Liebherr product page and official technical-data publication |

## Batch boundary

- Each machine remains a `research_candidate` and may enter the viewer only as
  a `technical_structural_study`.
- Manufacturer facts constrain dimensions and identity. Hidden pivots,
  cylinder anchors, linkage geometry, tire construction, articulation paths,
  boom staging, and interpolation remain `reconstructed` or `unresolved`
  unless configuration-applicable first-party evidence establishes them.
- Every model is built from an empty Blender factory-startup scene. Downloaded
  CAD, copied manufacturer geometry, copied textures, logos, and opaque add-ons
  are prohibited.
- Public materials remain neutral and unbranded. Product names are used only
  for study identification and the site retains its unofficial/not-endorsed
  boundary.
- Grok review occurs once, read-only, after all ten lanes are integrated and
  locally validated. It is not used as an authoring or repair loop.
