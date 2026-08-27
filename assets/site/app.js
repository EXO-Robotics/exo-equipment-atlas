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
    gltfRotationX: Math.PI / 2,
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
    gltfRotationX: 0,
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
    gltfRotationX: Math.PI / 2,
    accent: "#bda575"
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
  orbitToggle: document.querySelector("#orbit-toggle"),
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
controls.autoRotate = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
controls.autoRotateSpeed = 0.38;
controls.minPolarAngle = Math.PI * 0.16;
controls.maxPolarAngle = Math.PI * 0.49;

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
let loadToken = 0;

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
    nodes: sceneData.objects ?? sceneData.object_count ?? counts.objects ?? 0
  };
}

function updateEvidence(definition, configuration, factsDocument, receipt, validation) {
  const factsById = new Map((factsDocument.facts ?? []).map((fact) => [fact.id, fact]));
  const counts = normalizeReceiptCounts(receipt);
  const passed = (validation.gates ?? []).filter((gate) => gate.status === "PASS").length;
  const failed = (validation.gates ?? []).filter((gate) => gate.status === "FAIL").length;

  dom.triangles.textContent = formatNumber(counts.triangles);
  dom.nodes.textContent = formatNumber(counts.nodes);
  dom.gates.textContent = `${passed} / ${failed}`;
  dom.evidenceLede.textContent = definition.evidenceLede;
  dom.unresolved.textContent = `${configuration.unresolved_choices?.length ?? 0} configuration choices remain unresolved.`;
  dom.factList.replaceChildren();

  for (const factId of definition.factIds) {
    const fact = factsById.get(factId);
    if (!fact) continue;
    const row = document.createElement("div");
    const term = document.createElement("dt");
    const detail = document.createElement("dd");
    term.textContent = fact.subject;
    detail.textContent = valueWithUnit(fact);
    row.append(term, detail);
    dom.factList.append(row);
  }
}

function setModelShadows(root) {
  root.traverse((object) => {
    if (!object.isMesh) return;
    object.castShadow = true;
    object.receiveShadow = true;
  });
}

function disposeModel(root) {
  if (!root) return;
  scene.remove(root);
  root.traverse((object) => {
    if (!object.isMesh) return;
    object.geometry?.dispose();
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of materials) material?.dispose();
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
  const narrowViewportScale = Math.max(1, 0.72 / Math.max(0.1, camera.aspect));
  const distance = dominant * definition.cameraBias.distance * narrowViewportScale;
  const azimuth = definition.cameraBias.azimuth;
  const elevation = definition.cameraBias.elevation;
  const destination = new THREE.Vector3(
    Math.cos(azimuth) * Math.cos(elevation) * distance,
    target.y + Math.sin(elevation) * distance,
    Math.sin(azimuth) * Math.cos(elevation) * distance
  );

  camera.near = Math.max(0.01, distance / 1000);
  camera.far = distance * 20;
  camera.updateProjectionMatrix();
  controls.minDistance = distance * 0.38;
  controls.maxDistance = distance * 2.2;
  currentCamera = { position: destination, target };

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

function loadGltf(url, token) {
  return new Promise((resolve, reject) => {
    loader.load(
      url,
      (gltf) => token === loadToken ? resolve(gltf) : reject(new Error("Superseded load")),
      (event) => {
        if (token !== loadToken || !event.total) return;
        dom.status.textContent = `Loading geometry · ${Math.round((event.loaded / event.total) * 100)}%`;
      },
      reject
    );
  });
}

async function selectMachine(machineId, { scrollToHero = false } = {}) {
  if (!MACHINE_DEFINITIONS[machineId]) return;
  currentMachineId = machineId;
  const definition = MACHINE_DEFINITIONS[machineId];
  const token = ++loadToken;

  document.documentElement.style.setProperty("--accent", definition.accent);
  document.body.classList.remove("is-ready");
  dom.title.textContent = definition.name;
  dom.className.textContent = definition.className;
  dom.boundary.textContent = definition.boundary;
  dom.status.textContent = `Loading ${definition.name}`;

  for (const row of dom.rows) {
    const active = row.dataset.machine === machineId;
    row.classList.toggle("is-active", active);
    row.setAttribute("aria-selected", String(active));
  }

  if (scrollToHero) document.querySelector("#top")?.scrollIntoView({ behavior: "smooth" });

  try {
    const [gltf, configuration, facts, receipt, validation] = await Promise.all([
      loadGltf(definition.glb, token),
      fetch(definition.configuration).then((response) => response.ok ? response.json() : Promise.reject(new Error("Configuration unavailable"))),
      fetch(definition.facts).then((response) => response.ok ? response.json() : Promise.reject(new Error("Facts unavailable"))),
      fetch(definition.receipt).then((response) => response.ok ? response.json() : Promise.reject(new Error("Receipt unavailable"))),
      fetch(definition.validation).then((response) => response.ok ? response.json() : Promise.reject(new Error("Validation unavailable")))
    ]);
    if (token !== loadToken) return;

    disposeModel(currentModel);
    currentModel = gltf.scene;
    currentModel.name = `${machineId}-viewer-root`;
    currentModel.rotation.x = definition.gltfRotationX;
    currentModel.updateMatrixWorld(true);
    setModelShadows(currentModel);
    scene.add(currentModel);
    fitCamera(currentModel, definition, !currentCamera);
    updateEvidence(definition, configuration, facts, receipt, validation);

    dom.status.textContent = `${definition.name} · study loaded`;
    document.body.classList.add("is-ready");
  } catch (error) {
    if (token !== loadToken || error.message === "Superseded load") return;
    console.error(error);
    dom.status.textContent = "Viewer unavailable · evidence remains below";
  }
}

function resize() {
  const width = dom.scene.clientWidth;
  const height = dom.scene.clientHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / Math.max(1, height);
  camera.updateProjectionMatrix();
}

dom.orbitToggle.addEventListener("click", () => {
  controls.autoRotate = !controls.autoRotate;
  dom.orbitToggle.setAttribute("aria-pressed", String(controls.autoRotate));
});

dom.resetView.addEventListener("click", () => {
  if (!currentCamera) return;
  animateCamera(currentCamera.position, currentCamera.target);
});

for (const row of dom.rows) {
  row.addEventListener("click", () => selectMachine(row.dataset.machine, { scrollToHero: true }));
}

window.addEventListener("keydown", (event) => {
  if (!event.key.startsWith("Arrow")) return;
  const ids = Object.keys(MACHINE_DEFINITIONS);
  const currentIndex = ids.indexOf(currentMachineId);
  const offset = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
  const next = ids[(currentIndex + offset + ids.length) % ids.length];
  selectMachine(next);
});

window.addEventListener("resize", resize);
document.addEventListener("visibilitychange", () => {
  controls.autoRotate = !document.hidden && dom.orbitToggle.getAttribute("aria-pressed") === "true";
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
