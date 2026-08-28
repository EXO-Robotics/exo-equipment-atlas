# Third-party boundaries

This repository is an independent visualization research project. Caterpillar,
Cat, John Deere, JLG, their product names, logos, trade dress, publications, and
other marks belong to their respective owners.

Manufacturer publications and imagery are not licensed as repository content.
When acquired for research, they remain under `research/private/`, are ignored
by Git, and are represented in tracked manifests only by identifying metadata,
official URLs, byte counts, and cryptographic hashes.

No manufacturer CAD or extracted manufacturer geometry may be committed. Any
future GLB or Blender source admitted to the repository must be independently
authored and covered by an asset receipt.

## Three.js

The public viewer vendors the unmodified Three.js r160 ES module, GLTFLoader,
OrbitControls, and BufferGeometryUtils under `assets/vendor/three-r160/`. They
are distributed under the MIT License; the upstream license text is retained at
`assets/vendor/three-r160/LICENSE`. Exact file hashes and the upstream package
version are bound in `assets/vendor/three-r160/manifest.json` and checked during
the site build. Vendoring keeps the viewer functional without a runtime CDN
dependency and does not change the manufacturer-content boundary above.
