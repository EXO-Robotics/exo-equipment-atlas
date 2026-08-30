# Deterministic fleet structural-study generator

This tool turns one small JSON design into an independently authored, neutral,
unbranded Blender technical structural study. It is intended for research
candidates, not engineering, safety, operator-training, or digital-twin use.

## Single-machine build

Keep the design at `machines/<id>/source/design.json`, then run:

```sh
/Applications/Blender.app/Contents/MacOS/Blender \
  --factory-startup \
  --background \
  --python scripts/fleet/build_machine.py \
  -- \
  --design machines/<id>/source/design.json \
  --output-dir machines/<id>
```

The first build also writes the machine-owned reproducibility entrypoint
`source/blender/build_<id_with_underscores>.py`. Later builds may invoke that
wrapper directly with Blender's factory startup and background flags.

## Design contract

Required fields:

```json
{
  "schema_version": "1.0.0",
  "machine_id": "neutral-machine-id",
  "display_name": "Neutral machine study",
  "configuration_id": "NEUTRAL-MACHINE-RESEARCH-CANDIDATE",
  "archetype": "wheeled_tractor",
  "dimensions_m": {
    "length": 5.8,
    "width": 2.65,
    "height": 3.15
  }
}
```

`dimensions_m` is the complete retained visible GLB envelope in machine axes:
length on +X, height on +Y, and width on +Z. The builder calibrates visible
vertices to this envelope, records its reconstructed scale factors, and leaves
the identity root and all mesh-node scales untouched.

Supported archetypes:

- `wheeled_tractor`
- `tracked_tractor` — articulated four-pod layout
- `twin_track_tractor` — rigid twin full-length belt layout
- `combine`
- `forage_harvester`
- `high_clearance_sprayer`
- `self_propelled_mower`
- `square_baler`
- `self_propelled_round_baler`
- `articulated_hauler`
- `excavator`

Optional fields:

- `carrier_dimensions_m`: `{length,width,height}` for the carrier inside a
  wider attachment envelope. Every value must be positive and no larger than
  the corresponding retained-envelope dimension.
- `attachment_span_m`: visible header, mower, or boom span. It must not exceed
  `dimensions_m.width`.
- `tracked_front`: combine-only boolean for front tracks plus rear wheels.
- `tailgate`: articulated-hauler-only boolean; defaults to `true`.
- `palette`: `oxide`, `sand`, `sage`, `slate`, or `amber`.
- `published_constraints_used`: IDs of admitted facts actually used. Do not
  list an unmodeled wheelbase, steering limit, pivot, or motion endpoint.
- `reconstructed_values`: explicit reconstruction metadata.
- `unresolved_choices` and `mechanical_gaps`: nonempty string arrays.

Validate designs without Blender:

```sh
python3 -B scripts/fleet/validate_design.py \
  machines/*/source/design.json \
  --json
```

## Batch build

```sh
python3 -B scripts/fleet/batch_build.py \
  --design-dir /path/to/designs \
  --output-root /path/to/machines \
  --jobs 2 \
  --json
```

`--design` is repeatable when designs are not in one directory. `--dry-run`
validates contracts and prints exact Blender commands without writing outputs.
The batch runner requires both a zero process return code and a parsed
`FLEET_BUILD_RESULT` PASS marker, because Blender may not reliably convert all
Python script exceptions into a failing process code.

## Outputs

Each build writes:

```text
source/blender/build_<id_with_underscores>.py
source/blender/<id>-structural-study.blend
assets/<id>-structural-study.glb
production/asset-receipt.json
production/validation.json
review/renders/<id>-*.png
```

The public GLB has one identity `Machine_Root`, meters, +X forward, +Y up, +Z
right, semantic motion roots and pivots, applied mesh scales, and no cameras,
lights, helper meshes, images, or textures. The density floor is 200 nodes,
180 mesh nodes, 10,000 decoded triangles, and five review renders; the builder
currently emits six review views.

Receipts hash the machine-owned wrapper, shared generator, design JSON, Blend
source, GLB, validation document, and every review render. Hidden geometry and
envelope calibration remain explicitly reconstructed, while configuration,
mechanical, critic, viewer, publication, and deployment gates stay `PENDING`.

Verify generated packages independently:

```sh
python3 -B scripts/fleet/validate_package.py \
  machines/<id> \
  --json
```

The package validator rehashes all declared files and independently inspects
the GLB root, counts, triangle floor, mesh scales, and forbidden payloads.
