# Superseded overall critic report - 2026-08-27

> **Historical evidence only.** This report approved the exact original GLB
> hashes listed in its table; those files have since been replaced by rebuilt
> structural-study candidates. It does not approve the current GLBs, website,
> or deployment. The current artifacts remain `PENDING` for human critic review.

| Current machine candidate | Current decoded geometry | Current GLB SHA-256 | Human critic state |
| --- | ---: | --- | --- |
| Cat 320 | 64,736 triangles | `152f6f5448182d4278d112720473bae6e4d685020ea3947af434937c144dc20e` | PENDING |
| John Deere 333 P-Tier | 42,688 triangles | `b7ecbdfc24520cc2e678cda7f125e4de0dd561a0a57ee1c13e3d70b8ef1f3bc8` | PENDING |
| John Deere 310 P-Tier | 74,208 triangles | `5e518d6926960c393c038976abafb8323650bf76740de34126be39c4e5c5e93b` | PENDING |

## Historical decision (superseded)

The Cat 320, John Deere 333 P-Tier, and John Deere 310 P-Tier artifacts are
approved for admission to the private repository as
`technical_structural_study` assets. This approval is bound to the exact GLB
hashes below and does not advance any machine to mechanical, visual, release,
viewer, or deployed status.

| Machine | Structural verdict | Geometry | Exact GLB SHA-256 |
| --- | --- | ---: | --- |
| Cat 320 | PASS | 47,672 triangles | `5de7a8296fd8c49d99e92aeed30a2767e1bcad59fbe6ac231ac529dba3bc1a7d` |
| John Deere 333 P-Tier | PASS | 40,312 triangles | `21eaf89b4b83b6ff6847d064d670b14a72bed604225e65e69942012913f0a434` |
| John Deere 310 P-Tier | PASS | 64,580 triangles | `1f6507604d64ee8354356811778c81342d0fa11b32d47cd199713b7f54b3937d` |

The independent production audit verified three Blender files, three GLBs, 18
hashed review renders, and 945 exported GLB nodes. All three builders also pass
Python compilation with an isolated writable bytecode cache.

## Critic interventions

### Cat 320

The first submission was rejected because all review cameras were rolled about
90 degrees, most views cropped the working equipment, and the modeled transport
pose exceeded both length and height gates. The accepted revision uses a stable
Y-up camera basis, complete silhouettes, a separate linkage detail, corrected
transport pose, 49 shoes per side, eight lower rollers per side, and two carrier
rollers per side.

The accepted study is recognizable and mechanically separated into
undercarriage, slew upper, boom, stick, bucket, linkage, hydraulics, pivots, and
inspection volumes. Bucket shell, linkage topology, anchors, pivots, and motion
remain reconstructed rather than manufacturer facts.

### John Deere 333 P-Tier

The first submission was rejected because its render showed only three support
rollers between the idlers despite the publication specifying five rollers and
two idlers per side. Its side view also cropped the bucket, and the dump-angle
convention was not visually auditable. The accepted revision makes all seven
round undercarriage assemblies legible, frames the complete stowed silhouette,
and records the 48-degree full-height bucket-dump witness.

The accepted study separates the cab/ROPS, tracks, reconstructed vertical-lift
links, lift cylinders, tilt linkage, quick-attach placeholder, foundry-bucket
basis, collision proxies, and inspection volumes. Exact bucket part, attachment
interface, lift pivots, cylinder anchors, and lift-path solver remain unresolved.

### John Deere 310 P-Tier

The first submission was rejected as too primitive for the requested technical
bar: cuboid cab, unstructured wheels, rectangular buckets, unclear rear-tool
closure, and no useful stabilizer proof. The accepted revision adds framed and
sloped glazing, rims and hubs, differentiated tire construction, shaped loader
and backhoe buckets, a coherent transport backhoe, visible linkage/cylinders,
and a non-exported deployed-stabilizer review pose.

The stabilizer witness records a 3.10 m foot-center spread and 3.53 m outer
width. It is explicitly reconstructed and absent from the exported GLB. Exact
bucket, coupler, tire, pivot, anchor, and mechanism-solver authority remains
unresolved.

## Publication boundary

This critic approval authorizes only a private source-control publication of
the independently authored studies and their evidence. It does not authorize:

- branded or manufacturer-endorsed presentation;
- a catalog release-state change;
- shared-viewer admission;
- mechanical or collision qualification;
- browser, accessibility, mobile, performance, or selection claims;
- a public website or deployed product claim;
- engineering, load, safety, or operator-training use.

Each machine must next freeze its exact configuration, retain reconstructed
values as non-manufacturer data, and pass its machine-specific solver and
collision gates before visual-polish or viewer-release work begins.
