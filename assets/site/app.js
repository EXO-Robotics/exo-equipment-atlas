import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const MACHINE_DEFINITIONS = {
  "cat-320": {
    name: "Cat 320",
    className: "Hydraulic excavator",
    glb: "machines/cat-320/assets/cat-320-structural-study.glb",
    configuration: "machines/cat-320/configuration.json",
    facts: "machines/cat-320/evidence/facts.json",
    receipt: "machines/cat-320/production/asset-receipt.json",
    validation: "machines/cat-320/production/validation.json",
    boundary: "Independent 07H structural study. Pivots, anchors, linkage, and motion remain reconstructed.",
    evidenceLede: "Published 07H dimensions constrain the transport envelope and front equipment. Hidden pivot and cylinder geometry remains reconstructed.",
    factIds: ["transport-length", "transport-height", "undercarriage-width", "maximum-ground-reach"],
    cameraBias: { azimuth: 0.62, elevation: 0.34, distance: 1.48 },
    accent: "#d6943d"
  },
  "john-deere-333-p-tier": {
    name: "333 P-Tier",
    className: "Compact track loader",
    glb: "machines/john-deere-333-p-tier/assets/john-deere-333-p-tier-structural-study.glb",
    configuration: "machines/john-deere-333-p-tier/configuration.json",
    facts: "machines/john-deere-333-p-tier/evidence/facts.json",
    receipt: "machines/john-deere-333-p-tier/production/asset-receipt.json",
    validation: "machines/john-deere-333-p-tier/production/validation.json",
    boundary: "Independent vertical-lift study. Exact bucket, interface, lift pivots, and hydraulic anchors remain unresolved.",
    evidenceLede: "Published endpoints establish hinge height, dump height, reach, rollback, and dump angle. The path between them is not yet solver-qualified.",
    factIds: ["length-foundry-bucket", "width-450-track", "hinge-pin-height", "dump-height"],
    cameraBias: { azimuth: 0.72, elevation: 0.34, distance: 1.62 },
    accent: "#c8a45b"
  },
  "john-deere-310-p-tier": {
    name: "310 P-Tier",
    className: "Backhoe loader",
    glb: "machines/john-deere-310-p-tier/assets/john-deere-310-p-tier-structural-study.glb",
    configuration: "machines/john-deere-310-p-tier/configuration.json",
    facts: "machines/john-deere-310-p-tier/evidence/facts.json",
    receipt: "machines/john-deere-310-p-tier/production/asset-receipt.json",
    validation: "machines/john-deere-310-p-tier/production/validation.json",
    boundary: "Independent MFWD standard-dipper study. Buckets, tires, couplers, pivots, and anchors remain unresolved.",
    evidenceLede: "The transport envelope, wheelbase, cylinder dimensions, and standard-backhoe ranges are published. Multi-mechanism motion remains reconstructed.",
    factIds: ["overall-length", "overall-width", "cab-height", "mfwd-wheelbase"],
    cameraBias: { azimuth: 0.68, elevation: 0.33, distance: 1.58 },
    accent: "#bda575"
  },
  "cat-950": {
    name: "Cat 950",
    className: "Articulated wheel loader",
    glb: "machines/cat-950/assets/cat-950-structural-study.glb",
    configuration: "machines/cat-950/configuration.json",
    facts: "machines/cat-950/evidence/facts.json",
    receipt: "machines/cat-950/production/asset-receipt.json",
    validation: "machines/cat-950/production/validation.json",
    boundary: "Independent 14C standard-lift study. Hitch, axle, Z-bar, hydraulic-anchor, and tire mechanics remain reconstructed.",
    evidenceLede: "Published 14C dimensions constrain the 3.1 m³ general-purpose bucket, carry envelope, and maximum-lift endpoints. Hidden linkage geometry remains reconstructed.",
    factIds: ["shipping-length", "bucket-width", "rops-height", "max-lift-hinge-height"],
    cameraBias: { azimuth: 0.66, elevation: 0.33, distance: 1.52 },
    accent: "#d6943d"
  },
  "cat-d6": {
    name: "Cat D6",
    className: "Crawler dozer",
    glb: "machines/cat-d6/assets/cat-d6-structural-study.glb",
    configuration: "machines/cat-d6/configuration.json",
    facts: "machines/cat-d6/evidence/facts.json",
    receipt: "machines/cat-d6/production/asset-receipt.json",
    validation: "machines/cat-d6/production/validation.json",
    boundary: "Independent 20C 6SU push-arm study. Track phase, blade joints, cylinder anchors, motion limits, and load paths remain reconstructed.",
    evidenceLede: "Published 20C dimensions establish the HDXL undercarriage, 610 mm shoes, 6SU blade, and straight-blade envelope. Hidden actuation remains unresolved.",
    factIds: ["machine-length-blade-straight", "blade-width-end-bits", "machine-height", "track-on-ground-length"],
    cameraBias: { azimuth: 0.68, elevation: 0.31, distance: 1.5 },
    accent: "#cb8f3f"
  },
  "cat-725": {
    name: "Cat 725",
    className: "Articulated dump truck",
    glb: "machines/cat-725/assets/cat-725-structural-study.glb",
    configuration: "machines/cat-725/configuration.json",
    facts: "machines/cat-725/evidence/facts.json",
    receipt: "machines/cat-725/production/asset-receipt.json",
    validation: "machines/cat-725/production/validation.json",
    boundary: "Independent 05A standard-body study. Articulation centers, suspension, hoist anchors, tire construction, and load behavior remain reconstructed.",
    evidenceLede: "Published dimensions constrain the three-axle carrier, 24 t body, 45° steering range, suspension oscillation, and 70° tip reference. Hidden joints remain reconstructed.",
    factIds: ["overall-length", "overall-width", "height-transport-position", "rated-payload"],
    cameraBias: { azimuth: 0.65, elevation: 0.31, distance: 1.55 },
    accent: "#c9873b"
  },
  "cat-140": {
    name: "Cat 140",
    className: "Motor grader",
    glb: "machines/cat-140/assets/cat-140-structural-study.glb",
    configuration: "machines/cat-140/configuration.json",
    facts: "machines/cat-140/evidence/facts.json",
    receipt: "machines/cat-140/production/asset-receipt.json",
    validation: "machines/cat-140/production/validation.json",
    boundary: "Independent 16A non-AWD study. Steering linkage, circle teeth, pivots, cylinder anchors, hose routing, and motion interpolation remain reconstructed.",
    evidenceLede: "Published dimensions constrain the tandem carrier, 12 ft moldboard, drawbar circle, wheel lean, articulation, and rear-ripper envelope. Hidden mechanics remain unresolved.",
    factIds: ["push-plate-to-ripper-length", "cab-height", "moldboard-width", "front-axle-to-rear-axle"],
    cameraBias: { azimuth: 0.64, elevation: 0.29, distance: 1.52 },
    accent: "#ca8e42"
  },
  "john-deere-1270g": {
    name: "1270G 8W",
    className: "Wheeled harvester",
    glb: "machines/john-deere-1270g/assets/john-deere-1270g-structural-study.glb",
    configuration: "machines/john-deere-1270g/configuration.json",
    facts: "machines/john-deere-1270g/evidence/facts.json",
    receipt: "machines/john-deere-1270g/production/asset-receipt.json",
    validation: "machines/john-deere-1270g/production/validation.json",
    boundary: "Independent 8×8 CH7 working-pose study. Boom pivots, head internals, articulation, hydraulic anchors, and pose interpolation remain reconstructed.",
    evidenceLede: "Published specifications freeze the 8×8 carrier, CH7 boom, 8.6 m head-included reach, and H480C reference head. The retained working pose is not a transport-envelope claim.",
    factIds: ["transport-length", "transport-height", "minimum-width-600", "selected-maximum-reach"],
    cameraBias: { azimuth: 0.65, elevation: 0.32, distance: 1.54 },
    accent: "#b8a65f"
  },
  "john-deere-470-p-tier": {
    name: "470 P-Tier",
    className: "Hydraulic excavator",
    glb: "machines/john-deere-470-p-tier/assets/john-deere-470-p-tier-structural-study.glb",
    configuration: "machines/john-deere-470-p-tier/configuration.json",
    facts: "machines/john-deere-470-p-tier/evidence/facts.json",
    receipt: "machines/john-deere-470-p-tier/production/asset-receipt.json",
    validation: "machines/john-deere-470-p-tier/production/validation.json",
    boundary: "Independent 7.0 m boom, 3.9 m arm study. Linkage, pivot placement, attachment geometry, motion, and hydraulic routing remain reconstructed.",
    evidenceLede: "Published ME470PAU dimensions constrain the operating-gauge undercarriage, front equipment, cylinder sizes, and working ranges. Conflicting bucket-table values remain documented.",
    factIds: ["overall-length", "overall-height", "overall-width-operating", "maximum-ground-reach"],
    cameraBias: { azimuth: 0.62, elevation: 0.33, distance: 1.5 },
    accent: "#b9a161"
  },
  "bobcat-s76-2": {
    name: "S76-2",
    className: "Skid-steer loader",
    glb: "machines/bobcat-s76-2/assets/bobcat-s76-2-structural-study.glb",
    configuration: "machines/bobcat-s76-2/configuration.json",
    facts: "machines/bobcat-s76-2/evidence/facts.json",
    receipt: "machines/bobcat-s76-2/production/asset-receipt.json",
    validation: "machines/bobcat-s76-2/production/validation.json",
    boundary: "Independent North American Pro S76-2 study. Lift pivots, hydraulic anchors, tire construction, bucket section, and lift-path interpolation remain reconstructed.",
    evidenceLede: "Published dimensions constrain the standard 74-inch bucket, 12×16.5 tires, enclosed cab, stowed envelope, and hinge-pin endpoint. Hidden mechanics remain unresolved.",
    factIds: ["length-standard-bucket", "bucket-width", "overall-height", "hinge-pin-height"],
    cameraBias: { azimuth: 0.72, elevation: 0.34, distance: 1.58 },
    accent: "#c47a50"
  },
  "komatsu-wa475-10": {
    name: "WA475-10",
    className: "Articulated wheel loader",
    glb: "machines/komatsu-wa475-10/assets/komatsu-wa475-10-structural-study.glb",
    configuration: "machines/komatsu-wa475-10/configuration.json",
    facts: "machines/komatsu-wa475-10/evidence/facts.json",
    receipt: "machines/komatsu-wa475-10/production/asset-receipt.json",
    validation: "machines/komatsu-wa475-10/production/validation.json",
    boundary: "Independent standard-boom study. Hitch, pivots, anchors, driveline, tire construction, bucket section, and motion interpolation remain reconstructed.",
    evidenceLede: "The 2025 North American brochure constrains the 4.2 m³ stock-pile bucket, 26.5R25 tires, ROPS/FOPS envelope, cylinder dimensions, and steering endpoints.",
    factIds: ["overall-length-stock-pile", "bucket-width-stock-pile", "height-roof-rail", "hinge-pin-height-max-standard"],
    cameraBias: { azimuth: 0.66, elevation: 0.32, distance: 1.52 },
    accent: "#a9845d"
  },
  "volvo-dd128c": {
    name: "DD128C",
    className: "Tandem asphalt compactor",
    glb: "machines/volvo-dd128c/assets/volvo-dd128c-structural-study.glb",
    configuration: "machines/volvo-dd128c/configuration.json",
    facts: "machines/volvo-dd128c/evidence/facts.json",
    receipt: "machines/volvo-dd128c/production/asset-receipt.json",
    validation: "machines/volvo-dd128c/production/validation.json",
    boundary: "Independent North American open-canopy study. Articulation, oscillation, eccentric, steering-cylinder, and spray-routing geometry remain reconstructed.",
    evidenceLede: "Published dimensions constrain the 2,000 mm drums, open ROPS/FOPS canopy, articulation and oscillation limits, water system, and straight transport envelope.",
    factIds: ["overall-length", "overall-height", "overall-width", "drum-width"],
    cameraBias: { azimuth: 0.7, elevation: 0.3, distance: 1.5 },
    accent: "#b98a52"
  },
  "liebherr-ltm-1100-5-3": {
    name: "LTM 1100-5.3",
    className: "All-terrain mobile crane",
    glb: "machines/liebherr-ltm-1100-5-3/assets/liebherr-ltm-1100-5-3-structural-study.glb",
    configuration: "machines/liebherr-ltm-1100-5-3/configuration.json",
    facts: "machines/liebherr-ltm-1100-5-3/evidence/facts.json",
    receipt: "machines/liebherr-ltm-1100-5-3/production/asset-receipt.json",
    validation: "machines/liebherr-ltm-1100-5-3/production/validation.json",
    boundary: "Independent five-axle transport study. Boom staging, rigging, pivots, anchors, outriggers, and deployed review motion remain reconstructed.",
    evidenceLede: "Published S3586.02 dimensions constrain the 10×6×10 carrier, five-axle spacing, transport envelope, 62 m boom endpoint, and support footprint. No load-chart claim is made.",
    factIds: ["transport-boom-head-length", "transport-height-445", "transport-width", "telescopic-boom-maximum"],
    cameraBias: { azimuth: 0.64, elevation: 0.27, distance: 1.5 },
    accent: "#d2a153"
  }
};

const dom = {
  scene: document.querySelector("#scene"),
  title: document.querySelector("#machine-title"),
  className: document.querySelector("#machine-class"),
  boundary: document.querySelector("#machine-boundary"),
  status: document.querySelector("#load-status"),
  evidenceLede: document.querySelector("#evidence-lede"),
  factList: document.querySelector("#fact-list"),
  unresolved: document.querySelector("#unresolved-count"),
  triangles: document.querySelector("#metric-triangles"),
  nodes: document.querySelector("#metric-nodes"),
  gates: document.querySelector("#metric-gates"),
  releaseState: document.querySelector("#release-state"),
  validationSummary: document.querySelector("#validation-summary"),
  orbitToggle: document.querySelector("#orbit-toggle"),
  technicalView: document.querySelector("#technical-view"),
  resetView: document.querySelector("#reset-view"),
  rows: [...document.querySelectorAll("[data-machine]")]
};

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x11110f, 0.012);

const camera = new THREE.PerspectiveCamera(31, 1, 0.01, 300);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.12;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
dom.scene.append(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.055;
controls.enablePan = false;
const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
let autoRotateRequested = !reducedMotionQuery.matches;
controls.autoRotate = autoRotateRequested;
controls.autoRotateSpeed = 0.38;
controls.minPolarAngle = Math.PI * 0.16;
controls.maxPolarAngle = Math.PI * 0.49;
dom.orbitToggle.setAttribute("aria-pressed", String(controls.autoRotate));

scene.add(new THREE.HemisphereLight(0xe9e1d1, 0x252521, 2.15));

const keyLight = new THREE.DirectionalLight(0xffead0, 5.2);
keyLight.position.set(-6, 11, 8);
keyLight.castShadow = true;
keyLight.shadow.mapSize.set(2048, 2048);
keyLight.shadow.camera.near = 0.1;
keyLight.shadow.camera.far = 40;
keyLight.shadow.camera.left = -12;
keyLight.shadow.camera.right = 12;
keyLight.shadow.camera.top = 12;
keyLight.shadow.camera.bottom = -12;
scene.add(keyLight);

const rimLight = new THREE.DirectionalLight(0x8292a7, 3.4);
rimLight.position.set(8, 7, -9);
scene.add(rimLight);

const ground = new THREE.Mesh(
  new THREE.CircleGeometry(28, 96),
  new THREE.MeshStandardMaterial({ color: 0x161613, roughness: 0.92, metalness: 0.02 })
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.012;
ground.receiveShadow = true;
scene.add(ground);

const grid = new THREE.GridHelper(42, 42, 0x33332e, 0x242420);
grid.position.y = -0.006;
grid.material.opacity = 0.24;
grid.material.transparent = true;
scene.add(grid);

const loader = new GLTFLoader();
let currentModel = null;
let currentMachineId = "cat-320";
let currentCamera = null;
let currentTechnicalCamera = null;
let loadToken = 0;
let activeLoadController = null;
let loadingMachineId = null;

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function valueWithUnit(fact) {
  if (!fact) return "Pending";
  const units = { m: "m", deg: "°", count: "" };
  return `${fact.value}${units[fact.unit] ?? ` ${fact.unit}`}`;
}

function normalizeReceiptCounts(receipt) {
  const sceneData = receipt.scene ?? {};
  const counts = sceneData.counts ?? {};
  return {
    triangles: sceneData.triangles ?? sceneData.triangle_count ?? counts.triangles ?? 0,
    nodes: sceneData.objects ?? sceneData.object_count ?? counts.objects ?? counts.nodes ?? 0
  };
}

function createEvidenceSnapshot(definition, configuration, factsDocument, receipt, validation) {
  const factsById = new Map((factsDocument.facts ?? []).map((fact) => [fact.id, fact]));
  const counts = normalizeReceiptCounts(receipt);
  const passed = (validation.gates ?? []).filter((gate) => gate.status === "PASS").length;
  const pending = (validation.gates ?? []).filter((gate) => gate.status === "PENDING").length;
  const failed = (validation.gates ?? []).filter((gate) => gate.status === "FAIL").length;
  const configurationStatus = String(configuration.status ?? "unknown").replaceAll("_", " ");
  const candidateClass = String(validation.candidate_class ?? receipt.candidate_class ?? "unclassified").replaceAll("_", " ");
  const factRows = document.createDocumentFragment();

  for (const factId of definition.factIds) {
    const fact = factsById.get(factId);
    if (!fact) continue;
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = fact.subject;
    detail.textContent = valueWithUnit(fact);
    row.append(term, detail);
    factRows.append(row);
  }

  return {
    triangles: formatNumber(counts.triangles),
    nodes: formatNumber(counts.nodes),
    gates: `${passed} / ${pending} / ${failed}`,
    evidenceLede: definition.evidenceLede,
    releaseState: `${configurationStatus} · ${candidateClass}`,
    validationSummary:
      `Declared ${candidateClass} input verdict ${validation.verdict ?? "PENDING"}; ` +
      `${passed} pass, ${pending} pending, ${failed} fail. Higher-stage PENDING gates are not release approval.`,
    unresolved: `${configuration.unresolved_choices?.length ?? 0} configuration choices remain unresolved.`,
    factRows
  };
}

function applyEvidenceSnapshot(snapshot) {
  dom.triangles.textContent = snapshot.triangles;
  dom.nodes.textContent = snapshot.nodes;
  dom.gates.textContent = snapshot.gates;
  dom.evidenceLede.textContent = snapshot.evidenceLede;
  dom.releaseState.textContent = snapshot.releaseState;
  dom.validationSummary.textContent = snapshot.validationSummary;
  dom.unresolved.textContent = snapshot.unresolved;
  dom.factList.replaceChildren(snapshot.factRows);
}

function setModelShadows(root) {
  root.traverse((object) => {
    if (!object.isMesh) return;
    object.castShadow = true;
    object.receiveShadow = true;
  });
}

function assertViewerContract(gltf) {
  const roots = gltf.scene?.children ?? [];
  if (roots.length !== 1) throw new Error(`Viewer contract requires one scene root; found ${roots.length}`);
  const root = roots[0];
  const identity =
    root.position.length() < 1e-7 &&
    root.quaternion.angleTo(new THREE.Quaternion()) < 1e-7 &&
    root.scale.distanceTo(new THREE.Vector3(1, 1, 1)) < 1e-7;
  if (!identity) throw new Error(`Viewer contract requires an identity model root (${root.name || "unnamed"})`);
  if ((gltf.cameras?.length ?? 0) > 0) throw new Error("Viewer contract rejects embedded cameras");
  let meshes = 0;
  root.traverse((object) => { if (object.isMesh) meshes += 1; });
  if (meshes === 0) throw new Error("Viewer contract requires visible mesh geometry");
}

function disposeModel(root) {
  if (!root) return;
  scene.remove(root);
  const disposedGeometries = new Set();
  const disposedMaterials = new Set();
  const disposedTextures = new Set();
  root.traverse((object) => {
    if (!object.isMesh) return;
    if (object.geometry && !disposedGeometries.has(object.geometry)) {
      object.geometry.dispose();
      disposedGeometries.add(object.geometry);
    }
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of materials) {
      if (!material || disposedMaterials.has(material)) continue;
      for (const value of Object.values(material)) {
        if (value?.isTexture && !disposedTextures.has(value)) {
          value.dispose();
          disposedTextures.add(value);
        }
      }
      material.dispose();
      disposedMaterials.add(material);
    }
    const boneTexture = object.skeleton?.boneTexture;
    if (boneTexture && !disposedTextures.has(boneTexture)) {
      boneTexture.dispose();
      disposedTextures.add(boneTexture);
    }
  });
}

function fitCamera(root, definition, immediate = false) {
  const box = new THREE.Box3().setFromObject(root);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());

  root.position.x -= center.x;
  root.position.z -= center.z;
  root.position.y -= box.min.y;
  root.updateMatrixWorld(true);

  const fitted = new THREE.Box3().setFromObject(root);
  const fittedSize = fitted.getSize(new THREE.Vector3());
  const dominant = Math.max(fittedSize.x, fittedSize.y * 1.35, fittedSize.z);
  const target = new THREE.Vector3(
    camera.aspect > 0.8 ? -dominant * 0.14 : 0,
    fittedSize.y * 0.38,
    0
  );
  // Tall mobile canvases need extra horizontal breathing room so long machines
  // remain fully visible between the compact identity and control panel.
  const narrowViewportScale = Math.max(1, 1.24 / Math.max(0.1, camera.aspect));
  const azimuth = definition.cameraBias.azimuth;
  const elevation = definition.cameraBias.elevation;
  const viewDirection = new THREE.Vector3(
    Math.cos(azimuth) * Math.cos(elevation),
    Math.sin(elevation),
    Math.sin(azimuth) * Math.cos(elevation)
  ).normalize();

  const verticalFov = THREE.MathUtils.degToRad(camera.fov);
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * Math.max(camera.aspect, 0.1));
  const forward = viewDirection.clone().negate();
  const right = new THREE.Vector3().crossVectors(forward, camera.up).normalize();
  const up = new THREE.Vector3().crossVectors(right, forward).normalize();
  const tanHalfHorizontal = Math.tan(horizontalFov / 2);
  const tanHalfVertical = Math.tan(verticalFov / 2);
  let boundsFitDistance = 0;
  for (const x of [fitted.min.x, fitted.max.x]) {
    for (const y of [fitted.min.y, fitted.max.y]) {
      for (const z of [fitted.min.z, fitted.max.z]) {
        const relative = new THREE.Vector3(x, y, z).sub(target);
        const depthOffset = relative.dot(viewDirection);
        boundsFitDistance = Math.max(
          boundsFitDistance,
          depthOffset + Math.abs(relative.dot(right)) / tanHalfHorizontal,
          depthOffset + Math.abs(relative.dot(up)) / tanHalfVertical
        );
      }
    }
  }
  const authoredDistance = dominant * definition.cameraBias.distance * narrowViewportScale;
  const distance = Math.max(authoredDistance, boundsFitDistance * 1.12);
  const destination = target.clone().addScaledVector(viewDirection, distance);
  const technicalDistance = Math.max(
    (fittedSize.y * 0.5) / Math.tan(verticalFov / 2),
    (fittedSize.x * 0.5) / Math.tan(horizontalFov / 2)
  ) * 1.22;
  const technicalTarget = new THREE.Vector3(0, fittedSize.y * 0.5, 0);
  const technicalPosition = new THREE.Vector3(0, technicalTarget.y + fittedSize.y * 0.08, technicalDistance);

  camera.near = Math.max(0.01, distance / 1000);
  camera.far = distance * 20;
  camera.updateProjectionMatrix();
  controls.minDistance = distance * 0.38;
  controls.maxDistance = distance * 2.2;
  currentCamera = { position: destination, target };
  currentTechnicalCamera = { position: technicalPosition, target: technicalTarget };

  if (immediate) {
    camera.position.copy(destination);
    controls.target.copy(target);
    controls.update();
  } else {
    animateCamera(destination, target);
  }
}

function animateCamera(destination, target) {
  const startPosition = camera.position.clone();
  const startTarget = controls.target.clone();
  const start = performance.now();
  const duration = 850;

  function frame(now) {
    const raw = Math.min(1, (now - start) / duration);
    const t = 1 - Math.pow(1 - raw, 3);
    camera.position.lerpVectors(startPosition, destination, t);
    controls.target.lerpVectors(startTarget, target, t);
    if (raw < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}

function fetchJson(url, label, signal) {
  return fetch(url, { cache: "no-cache", signal }).then((response) => {
    if (!response.ok) throw new Error(`${label} unavailable (${response.status})`);
    return response.json();
  });
}

function fetchGlb(url, signal) {
  return fetch(url, { cache: "no-cache", signal }).then((response) => {
    if (!response.ok) throw new Error(`Geometry unavailable (${response.status})`);
    return response.arrayBuffer();
  });
}

function parseGltf(bytes, resourcePath) {
  return new Promise((resolve, reject) => {
    loader.parse(
      bytes,
      resourcePath,
      resolve,
      reject
    );
  });
}

function sha256Hex(bytes) {
  if (!globalThis.crypto?.subtle) throw new Error("Browser SHA-256 verification is unavailable");
  return crypto.subtle.digest("SHA-256", bytes).then((digest) =>
    [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("")
  );
}

function assertEvidenceIdentity(machineId, documents) {
  const configurationIds = new Set();
  for (const [label, document] of Object.entries(documents)) {
    if (document.machine_id !== machineId) {
      throw new Error(`${label} identifies ${document.machine_id ?? "no machine"}; expected ${machineId}`);
    }
    if (!document.configuration_id) throw new Error(`${label} does not identify a configuration`);
    configurationIds.add(document.configuration_id);
  }
  if (configurationIds.size !== 1) throw new Error("Evidence documents identify different configurations");
}

function isSuperseded(token, signal) {
  return token !== loadToken || signal.aborted;
}

function retainedStudyLabel() {
  return currentModel ? `${MACHINE_DEFINITIONS[currentMachineId].name} remains visible` : "no study is visible yet";
}

function setLoadingStatus(definition, phase) {
  dom.status.textContent = `${phase} ${definition.name} · ${retainedStudyLabel()}`;
}

function fitHeroTitle() {
  dom.title.classList.remove("is-compact-title", "is-wrapped-title");
  const titleLeft = dom.title.getBoundingClientRect().left;
  const rootGutter = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--gutter")) || 16;
  const availableWidth = Math.max(240, window.innerWidth - titleLeft - rootGutter);
  dom.title.style.setProperty("--hero-title-available", `${availableWidth}px`);

  if (dom.title.scrollWidth <= availableWidth + 1) return;
  dom.title.classList.add("is-compact-title");
  if (dom.title.scrollWidth > availableWidth + 1) dom.title.classList.add("is-wrapped-title");
}

function applyMachineIdentity(machineId, definition, evidenceSnapshot) {
  currentMachineId = machineId;
  document.documentElement.style.setProperty("--accent", definition.accent);
  dom.title.textContent = definition.name;
  dom.className.textContent = definition.className;
  dom.boundary.textContent = definition.boundary;
  applyEvidenceSnapshot(evidenceSnapshot);

  for (const row of dom.rows) {
    const active = row.dataset.machine === machineId;
    row.classList.toggle("is-active", active);
    row.setAttribute("aria-selected", String(active));
    row.setAttribute("tabindex", active ? "0" : "-1");
  }
  document.querySelector("#machine-panel")?.setAttribute("aria-labelledby", `machine-tab-${machineId} machine-title`);
  fitHeroTitle();
}

async function selectMachine(machineId, { scrollToHero = false } = {}) {
  if (!MACHINE_DEFINITIONS[machineId]) return;
  const definition = MACHINE_DEFINITIONS[machineId];
  activeLoadController?.abort();
  const controller = new AbortController();
  activeLoadController = controller;
  loadingMachineId = machineId;
  const { signal } = controller;
  const token = ++loadToken;
  let candidateModel = null;
  document.body.classList.remove("is-load-error");
  document.body.classList.add("is-loading");
  document.querySelector("#machine-panel")?.setAttribute("aria-busy", "true");
  setLoadingStatus(definition, "Loading evidence for");

  if (scrollToHero) document.querySelector("#top")?.scrollIntoView({ behavior: "smooth" });

  try {
    const [configuration, facts, receipt, validation] = await Promise.all([
      fetchJson(definition.configuration, "Configuration", signal),
      fetchJson(definition.facts, "Facts", signal),
      fetchJson(definition.receipt, "Receipt", signal),
      fetchJson(definition.validation, "Validation", signal)
    ]);
    if (isSuperseded(token, signal)) return;

    assertEvidenceIdentity(machineId, { Configuration: configuration, Facts: facts, Receipt: receipt, Validation: validation });
    const expectedHash = String(receipt.artifacts?.glb?.sha256 ?? "").toLowerCase();
    if (!/^[a-f0-9]{64}$/.test(expectedHash)) throw new Error("Receipt does not provide a valid GLB SHA-256");
    const glbUrl = new URL(definition.glb, document.baseURI);
    glbUrl.searchParams.set("sha256", expectedHash);
    setLoadingStatus(definition, "Loading hash-bound geometry for");
    const glbBytes = await fetchGlb(glbUrl, signal);
    if (isSuperseded(token, signal)) return;

    setLoadingStatus(definition, "Verifying geometry for");
    const actualHash = await sha256Hex(glbBytes);
    if (isSuperseded(token, signal)) return;
    if (actualHash !== expectedHash) {
      throw new Error(`GLB SHA-256 mismatch: expected ${expectedHash}, received ${actualHash}`);
    }

    setLoadingStatus(definition, "Parsing verified geometry for");
    const resourcePath = new URL("./", glbUrl).href;
    const gltf = await parseGltf(glbBytes, resourcePath);
    candidateModel = gltf.scene;
    if (isSuperseded(token, signal)) {
      disposeModel(candidateModel);
      candidateModel = null;
      return;
    }
    assertViewerContract(gltf);
    const evidenceSnapshot = createEvidenceSnapshot(definition, configuration, facts, receipt, validation);

    candidateModel.name = `${machineId}-viewer-root`;
    candidateModel.updateMatrixWorld(true);
    setModelShadows(candidateModel);
    fitCamera(candidateModel, definition, !currentModel);

    const previousModel = currentModel;
    scene.add(candidateModel);
    currentModel = candidateModel;
    candidateModel = null;
    applyMachineIdentity(machineId, definition, evidenceSnapshot);
    disposeModel(previousModel);
    dom.status.textContent = `${definition.name} · study loaded`;
    document.body.classList.add("is-ready");
  } catch (error) {
    if (candidateModel) disposeModel(candidateModel);
    if (isSuperseded(token, signal) || error.name === "AbortError") return;
    console.error(error);
    document.body.classList.add("is-load-error");
    dom.status.textContent = currentModel
      ? `${definition.name} unavailable · ${MACHINE_DEFINITIONS[currentMachineId].name} remains loaded`
      : `${definition.name} unavailable · no study loaded`;
  } finally {
    if (activeLoadController === controller) {
      activeLoadController = null;
      loadingMachineId = null;
      document.body.classList.remove("is-loading");
      document.querySelector("#machine-panel")?.setAttribute("aria-busy", "false");
    }
  }
}

function resize() {
  const width = dom.scene.clientWidth;
  const height = dom.scene.clientHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / Math.max(1, height);
  camera.updateProjectionMatrix();
  fitHeroTitle();
}

dom.orbitToggle.addEventListener("click", () => {
  autoRotateRequested = reducedMotionQuery.matches ? false : !autoRotateRequested;
  controls.autoRotate = autoRotateRequested && !document.hidden;
  dom.orbitToggle.setAttribute("aria-pressed", String(autoRotateRequested));
});

dom.resetView.addEventListener("click", () => {
  if (!currentCamera) return;
  animateCamera(currentCamera.position, currentCamera.target);
});

dom.technicalView.addEventListener("click", () => {
  if (!currentTechnicalCamera) return;
  autoRotateRequested = false;
  controls.autoRotate = false;
  dom.orbitToggle.setAttribute("aria-pressed", "false");
  animateCamera(currentTechnicalCamera.position, currentTechnicalCamera.target);
});

function selectAdjacentTab(event) {
  if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
  event.preventDefault();
  const ids = Object.keys(MACHINE_DEFINITIONS);
  const navigationMachineId = loadingMachineId ?? currentMachineId;
  const currentIndex = ids.indexOf(navigationMachineId);
  const nextIndex = event.key === "Home"
    ? 0
    : event.key === "End"
      ? ids.length - 1
      : (currentIndex + (event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1) + ids.length) % ids.length;
  const next = ids[nextIndex];
  const nextTab = dom.rows.find((row) => row.dataset.machine === next);
  nextTab?.focus();
  selectMachine(next);
}

for (const row of dom.rows) {
  row.addEventListener("click", () => selectMachine(row.dataset.machine, { scrollToHero: true }));
  row.addEventListener("keydown", selectAdjacentTab);
}

dom.scene.addEventListener("keydown", (event) => {
  const keys = new Set(["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "+", "=", "-", "_", "Home"]);
  if (!keys.has(event.key) || !currentCamera) return;
  event.preventDefault();
  if (event.key === "Home") {
    const view = currentTechnicalCamera ?? currentCamera;
    animateCamera(view.position, view.target);
    return;
  }
  const offset = camera.position.clone().sub(controls.target);
  const spherical = new THREE.Spherical().setFromVector3(offset);
  if (event.key === "ArrowLeft") spherical.theta -= 0.12;
  if (event.key === "ArrowRight") spherical.theta += 0.12;
  if (event.key === "ArrowUp") spherical.phi = Math.max(controls.minPolarAngle, spherical.phi - 0.08);
  if (event.key === "ArrowDown") spherical.phi = Math.min(controls.maxPolarAngle, spherical.phi + 0.08);
  if (event.key === "+" || event.key === "=") spherical.radius = Math.max(controls.minDistance, spherical.radius * 0.9);
  if (event.key === "-" || event.key === "_") spherical.radius = Math.min(controls.maxDistance, spherical.radius * 1.1);
  camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));
  controls.update();
});

window.addEventListener("resize", resize);
document.addEventListener("visibilitychange", () => {
  controls.autoRotate = !document.hidden && autoRotateRequested && !reducedMotionQuery.matches;
});
reducedMotionQuery.addEventListener("change", (event) => {
  if (!event.matches) return;
  autoRotateRequested = false;
  controls.autoRotate = false;
  dom.orbitToggle.setAttribute("aria-pressed", "false");
});

const clock = new THREE.Clock();
function render() {
  const delta = Math.min(clock.getDelta(), 0.05);
  controls.update(delta);
  renderer.render(scene, camera);
  requestAnimationFrame(render);
}

resize();
selectMachine(currentMachineId);
render();
