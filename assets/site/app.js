import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  MANUAL_OVERRIDE_MS,
  ManualOverrideClock,
  autoplayProgress,
  clamp01,
  damp
} from "./motion.js";

const CATALOG_URL = "catalog.json";
const VIEWER_SCHEMA_VERSION = "1.0.0";
const DEFAULT_CAMERA = { azimuth: 0.66, elevation: 0.32, distance: 1.52 };
const MOTION_PROPERTIES = new Set([
  "rotation.x",
  "rotation.y",
  "rotation.z",
  "position.x",
  "position.y",
  "position.z"
]);
const AUTHORITY_LABELS = Object.freeze({
  manufacturer_published: "Manufacturer published",
  evidence_derived: "Evidence derived",
  reconstructed: "Reconstructed",
  observed: "Observed",
  unresolved: "Unresolved"
});

const dom = {
  scene: document.querySelector("#scene"),
  fallback: document.querySelector("#scene-fallback"),
  fallbackCopy: document.querySelector("#fallback-copy"),
  poster: document.querySelector("#scene-poster"),
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
  motionToggle: document.querySelector("#motion-toggle"),
  technicalView: document.querySelector("#technical-view"),
  resetView: document.querySelector("#reset-view"),
  motionPanel: document.querySelector("#motion-panel"),
  motionState: document.querySelector("#motion-state"),
  motionChannels: document.querySelector("#motion-channels"),
  motionTemplate: document.querySelector("#motion-channel-template"),
  machineIndex: document.querySelector("#machine-index"),
  machineTemplate: document.querySelector("#machine-row-template"),
  machineCount: document.querySelector("#machine-count"),
  search: document.querySelector("#machine-search"),
  categoryFilters: document.querySelector("#category-filters"),
  catalogSummary: document.querySelector("#catalog-summary"),
  catalogEmpty: document.querySelector("#catalog-empty")
};

const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const definitions = new Map();
let catalogEntries = [];
let rows = [];
let activeCategory = "all";
let searchTerm = "";
let currentMachineId = null;
let loadingMachineId = null;
let currentModel = null;
let currentCamera = null;
let currentTechnicalCamera = null;
let activeLoadController = null;
let loadToken = 0;
let cameraAnimationToken = 0;

let scene = null;
let camera = null;
let renderer = null;
let controls = null;
let loader = null;
let interactiveAvailable = true;
let autoRotateRequested = !reducedMotionQuery.matches;
const cameraManualHold = new ManualOverrideClock(MANUAL_OVERRIDE_MS);

const motionRuntime = {
  bindings: [],
  startedAt: 0,
  durationSeconds: 8,
  mode: "sine",
  damping: 7,
  autoRequested: false,
  manualHold: new ManualOverrideClock(MANUAL_OVERRIDE_MS),
  wasManual: false
};

function makeScene() {
  try {
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x11110f, 0.012);
    camera = new THREE.PerspectiveCamera(31, 1, 0.01, 300);
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.12;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.domElement.setAttribute("aria-hidden", "true");
    renderer.domElement.addEventListener("webglcontextlost", (event) => {
      event.preventDefault();
      interactiveAvailable = false;
      document.body.classList.add("is-static", "is-load-error");
      dom.fallback.setAttribute("aria-hidden", "false");
      dom.fallbackCopy.textContent = "The interactive renderer stopped. Machine evidence remains available below.";
      dom.status.textContent = "Interactive renderer unavailable · static evidence view retained";
      for (const control of [dom.orbitToggle, dom.motionToggle, dom.technicalView, dom.resetView]) control.disabled = true;
    });
    dom.scene.append(renderer.domElement);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.055;
    controls.enablePan = false;
    controls.autoRotateSpeed = 0.38;
    controls.minPolarAngle = Math.PI * 0.16;
    controls.maxPolarAngle = Math.PI * 0.49;
    controls.addEventListener("start", () => cameraManualHold.hold(performance.now()));

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
    loader = new GLTFLoader();
  } catch (error) {
    console.error("Interactive renderer unavailable", error);
    interactiveAvailable = false;
    document.body.classList.add("is-static");
    dom.fallback.setAttribute("aria-hidden", "false");
    dom.fallbackCopy.textContent = "This device cannot start the interactive renderer. Machine evidence remains available below.";
    for (const control of [dom.orbitToggle, dom.technicalView, dom.resetView]) control.disabled = true;
  }
}

function formatNumber(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function valueWithUnit(fact) {
  if (!fact) return "Pending";
  const units = { m: "m", deg: "°", count: "" };
  const authority = AUTHORITY_LABELS[fact.authority] ?? "Authority unclassified";
  return `${fact.value}${units[fact.unit] ?? ` ${fact.unit}`} · ${authority}`;
}

function isSafePublicPath(value) {
  if (typeof value !== "string" || value.length === 0 || value.startsWith("/") || value.includes("\\")) return false;
  if (/^[a-z]+:/iu.test(value) || value.includes("?") || value.includes("#")) return false;
  const parts = value.split("/");
  return !parts.includes("..") && !value.includes(["research", "private"].join("/") + "/");
}

function requirePublicPath(value, label) {
  if (!isSafePublicPath(value)) throw new Error(`${label} must be a repository-relative public path`);
  return value;
}

function normalizeViewer(document, catalogEntry) {
  if (!document || typeof document !== "object") throw new Error("viewer.json must be an object");
  if (document.schema_version !== VIEWER_SCHEMA_VERSION) {
    throw new Error(`viewer.json schema must be ${VIEWER_SCHEMA_VERSION}`);
  }
  if (document.machineId !== catalogEntry.id) {
    throw new Error(`viewer.json identifies ${document.machineId ?? "no machine"}; expected ${catalogEntry.id}`);
  }
  for (const key of ["displayName", "className", "category", "accent"]) {
    if (typeof document[key] !== "string" || document[key].trim() === "") throw new Error(`viewer.json ${key} is required`);
  }
  if (!/^#[0-9a-f]{6}$/iu.test(document.accent)) throw new Error("viewer.json accent must be a six-digit hex color");

  const assets = {};
  for (const key of ["glb", "configuration", "facts", "receipt", "validation"]) {
    assets[key] = requirePublicPath(document.assets?.[key], `viewer.json assets.${key}`);
  }
  if (document.assets?.poster) assets.poster = requirePublicPath(document.assets.poster, "viewer.json assets.poster");

  const factIds = document.evidence?.factIds;
  if (!Array.isArray(factIds) || factIds.length === 0 || factIds.some((id) => typeof id !== "string" || !id)) {
    throw new Error("viewer.json evidence.factIds must contain at least one fact id");
  }
  const boundary = document.evidence?.boundary;
  const lede = document.evidence?.lede;
  if (typeof boundary !== "string" || !boundary || typeof lede !== "string" || !lede) {
    throw new Error("viewer.json evidence copy is incomplete");
  }

  const cameraBias = {
    azimuth: Number.isFinite(document.camera?.azimuth) ? document.camera.azimuth : DEFAULT_CAMERA.azimuth,
    elevation: Number.isFinite(document.camera?.elevation) ? document.camera.elevation : DEFAULT_CAMERA.elevation,
    distance: Number.isFinite(document.camera?.distance) && document.camera.distance > 0
      ? document.camera.distance
      : DEFAULT_CAMERA.distance
  };

  const motion = normalizeMotion(document.motion);
  return {
    id: catalogEntry.id,
    priority: catalogEntry.priority,
    name: document.displayName.trim(),
    className: document.className.trim(),
    category: document.category.trim(),
    assets,
    boundary,
    evidenceLede: lede,
    factIds: [...new Set(factIds)],
    cameraBias,
    accent: document.accent,
    motion
  };
}

function normalizeMotion(value) {
  if (!value || !Array.isArray(value.channels) || value.channels.length === 0) return null;
  const channels = [];
  for (const channel of value.channels) {
    const nodes = Array.isArray(channel.nodes) ? [...new Set(channel.nodes.filter((node) => typeof node === "string" && node))] : [];
    if (
      typeof channel.id !== "string" || !channel.id ||
      typeof channel.label !== "string" || !channel.label ||
      nodes.length === 0 || !MOTION_PROPERTIES.has(channel.property) ||
      !Number.isFinite(channel.from) || !Number.isFinite(channel.to)
    ) continue;
    channels.push({
      id: channel.id,
      label: channel.label,
      mechanismJointId: channel.mechanismJointId,
      nodes,
      property: channel.property,
      from: channel.from,
      to: channel.to,
      phase: Number.isFinite(channel.phase) ? channel.phase : 0,
      direction: channel.direction === -1 ? -1 : 1,
      transformMode: channel.mode === "absolute" ? "absolute" : "offset",
      autoplayMode: channel.autoplay === "ping-pong" ? "ping-pong" : channel.autoplay === "sine" ? "sine" : null
    });
  }
  if (channels.length === 0) return null;
  return {
    autoplay: value.autoplay !== false,
    durationSeconds: Number.isFinite(value.durationSeconds) && value.durationSeconds > 0 ? value.durationSeconds : 8,
    mode: value.mode === "ping-pong" ? "ping-pong" : "sine",
    damping: Number.isFinite(value.damping) && value.damping > 0 ? value.damping : 7,
    channels
  };
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

function setFallback(definition, message) {
  dom.fallbackCopy.textContent = message;
  dom.poster.hidden = !definition?.assets.poster;
  if (definition?.assets.poster) dom.poster.src = definition.assets.poster;
  else dom.poster.removeAttribute("src");
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
  if (!root || !scene) return;
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
      for (const property of Object.values(material)) {
        if (property?.isTexture && !disposedTextures.has(property)) {
          property.dispose();
          disposedTextures.add(property);
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
  if (!camera || !controls) return;
  const box = new THREE.Box3().setFromObject(root);
  const center = box.getCenter(new THREE.Vector3());
  root.position.x -= center.x;
  root.position.z -= center.z;
  root.position.y -= box.min.y;
  root.updateMatrixWorld(true);

  const fitted = new THREE.Box3().setFromObject(root);
  const fittedSize = fitted.getSize(new THREE.Vector3());
  const dominant = Math.max(fittedSize.x, fittedSize.y * 1.35, fittedSize.z);
  const target = new THREE.Vector3(camera.aspect > 0.8 ? -dominant * 0.14 : 0, fittedSize.y * 0.38, 0);
  const narrowViewportScale = Math.max(1, 1.24 / Math.max(0.1, camera.aspect));
  const { azimuth, elevation } = definition.cameraBias;
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

  if (immediate || reducedMotionQuery.matches) {
    camera.position.copy(destination);
    controls.target.copy(target);
    controls.update();
  } else {
    animateCamera(destination, target);
  }
}

function animateCamera(destination, target) {
  if (!camera || !controls) return;
  const token = ++cameraAnimationToken;
  if (reducedMotionQuery.matches) {
    camera.position.copy(destination);
    controls.target.copy(target);
    controls.update();
    return;
  }
  const startPosition = camera.position.clone();
  const startTarget = controls.target.clone();
  const start = performance.now();
  const duration = 850;
  function frame(now) {
    if (token !== cameraAnimationToken) return;
    const raw = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - raw, 3);
    camera.position.lerpVectors(startPosition, destination, eased);
    controls.target.lerpVectors(startTarget, target, eased);
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
  return new Promise((resolve, reject) => loader.parse(bytes, resourcePath, resolve, reject));
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
  return currentModel && definitions.has(currentMachineId)
    ? `${definitions.get(currentMachineId).name} remains visible`
    : "no study is visible yet";
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
  dom.className.textContent = `${definition.category} · ${definition.className}`;
  dom.boundary.textContent = definition.boundary;
  document.title = `${definition.name} · EXO Equipment Atlas`;
  applyEvidenceSnapshot(evidenceSnapshot);
  updateActiveRows();
  dom.scene.setAttribute("aria-label", `Interactive 3D viewer for ${definition.name}`);
  fitHeroTitle();
}

function updateActiveRows() {
  const activeIsVisible = rows.some((row) => row.dataset.machine === currentMachineId);
  const fallbackRow = rows.find((row) => !row.disabled);
  for (const row of rows) {
    const active = row.dataset.machine === currentMachineId;
    row.classList.toggle("is-active", active);
    row.classList.toggle("is-pending", row.dataset.machine === loadingMachineId);
    row.setAttribute("aria-selected", String(active));
    row.setAttribute("tabindex", active || (!activeIsVisible && row === fallbackRow) ? "0" : "-1");
  }
  const labelledBy = activeIsVisible && currentMachineId
    ? `machine-tab-${currentMachineId} machine-title`
    : "machine-title";
  document.querySelector("#machine-panel")?.setAttribute("aria-labelledby", labelledBy);
}

function updateDeepLink(machineId, mode) {
  if (!mode) return;
  const url = new URL(window.location.href);
  url.searchParams.set("machine", machineId);
  history[`${mode}State`]({ machine: machineId }, "", url);
}

function clearMotion() {
  motionRuntime.bindings = [];
  motionRuntime.manualHold.clear();
  motionRuntime.autoRequested = false;
  motionRuntime.wasManual = false;
  dom.motionChannels.replaceChildren();
  dom.motionPanel.hidden = true;
  dom.motionToggle.hidden = true;
  dom.motionToggle.setAttribute("aria-pressed", "false");
  document.body.classList.remove("has-motion");
}

function setMotionState(label) {
  dom.motionState.textContent = label;
}

function bindMotion(root, definition) {
  clearMotion();
  if (!definition.motion) return;
  const bindings = [];
  for (const channel of definition.motion.channels) {
    const [group, axis] = channel.property.split(".");
    const targets = [];
    for (const nodeName of channel.nodes) {
      const node = root.getObjectByName(nodeName);
      const owner = node?.[group];
      if (!node || !owner || !Number.isFinite(owner[axis])) {
        console.warn(`${definition.id}: motion channel ${channel.id} cannot resolve ${nodeName}.${channel.property}`);
        continue;
      }
      targets.push({ owner, axis, base: owner[axis] });
    }
    if (targets.length === 0) continue;

    const fragment = dom.motionTemplate.content.cloneNode(true);
    const label = fragment.querySelector("label");
    const labelText = fragment.querySelector("span");
    const input = fragment.querySelector("input");
    const output = fragment.querySelector("output");
    const inputId = `motion-${definition.id}-${channel.id}`;
    label.htmlFor = inputId;
    input.id = inputId;
    labelText.textContent = channel.label;
    const binding = { ...channel, targets, current: 0, target: 0, manual: 0, input, output };

    const beginManual = () => {
      if (!motionRuntime.manualHold.isActive(performance.now())) {
        for (const item of motionRuntime.bindings) item.manual = item.current;
      }
      motionRuntime.manualHold.hold(performance.now());
      motionRuntime.wasManual = true;
      setMotionState("Manual control · auto resumes in 6 sec");
    };
    input.addEventListener("input", () => {
      beginManual();
      binding.manual = clamp01(Number(input.value) / 100);
      binding.target = binding.manual;
      if (reducedMotionQuery.matches) binding.current = binding.target;
    });
    input.addEventListener("pointerdown", beginManual);
    input.addEventListener("keydown", (event) => {
      if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End", "PageUp", "PageDown"].includes(event.key)) {
        beginManual();
      }
    });
    dom.motionChannels.append(fragment);
    bindings.push(binding);
  }

  if (bindings.length === 0) return;
  motionRuntime.bindings = bindings;
  motionRuntime.startedAt = performance.now();
  motionRuntime.durationSeconds = definition.motion.durationSeconds;
  motionRuntime.mode = definition.motion.mode;
  motionRuntime.damping = definition.motion.damping;
  motionRuntime.autoRequested = definition.motion.autoplay && !reducedMotionQuery.matches;
  dom.motionPanel.hidden = false;
  dom.motionToggle.hidden = false;
  dom.motionToggle.disabled = reducedMotionQuery.matches;
  dom.motionToggle.setAttribute("aria-pressed", String(motionRuntime.autoRequested));
  setMotionState(reducedMotionQuery.matches ? "Static · reduced motion" : motionRuntime.autoRequested ? "Automatic presentation" : "Manual presentation");
  document.body.classList.add("has-motion");
  updateMotion(performance.now(), 0);
}

function updateMotion(now, deltaSeconds) {
  if (motionRuntime.bindings.length === 0) return;
  const isManual = motionRuntime.manualHold.isActive(now);
  if (motionRuntime.wasManual && !isManual) {
    motionRuntime.wasManual = false;
    setMotionState(motionRuntime.autoRequested ? "Automatic presentation" : "Manual presentation");
  }
  const autoplay = motionRuntime.autoRequested && !reducedMotionQuery.matches && !isManual && !document.hidden;
  const elapsedSeconds = (now - motionRuntime.startedAt) / 1000;
  let settled = true;

  for (const binding of motionRuntime.bindings) {
    if (autoplay) {
      const mode = binding.autoplayMode ?? motionRuntime.mode;
      let progress = autoplayProgress(elapsedSeconds, motionRuntime.durationSeconds, binding.phase, mode);
      if (binding.direction === -1) progress = 1 - progress;
      binding.target = progress;
    } else {
      binding.target = binding.manual;
    }

    binding.current = reducedMotionQuery.matches
      ? binding.target
      : damp(binding.current, binding.target, motionRuntime.damping, Math.min(deltaSeconds, 0.1));
    settled &&= Math.abs(binding.current - binding.target) < 0.002;
    const authoredValue = THREE.MathUtils.lerp(binding.from, binding.to, binding.current);
    for (const target of binding.targets) {
      target.owner[target.axis] = binding.transformMode === "absolute" ? authoredValue : target.base + authoredValue;
    }
    const percent = Math.round(binding.current * 100);
    if (document.activeElement !== binding.input || !isManual) binding.input.value = String(percent);
    binding.output.value = `${percent}%`;
    binding.input.setAttribute("aria-valuetext", `${binding.label}, ${percent} percent`);
  }

  if (!motionRuntime.wasManual && autoplay && settled) setMotionState("Automatic presentation");
}

async function selectMachine(machineId, { scrollToHero = false, historyMode = "push" } = {}) {
  if (!definitions.has(machineId)) return;
  const definition = definitions.get(machineId);
  activeLoadController?.abort();
  const controller = new AbortController();
  activeLoadController = controller;
  loadingMachineId = machineId;
  updateActiveRows();
  const { signal } = controller;
  const token = ++loadToken;
  let candidateModel = null;
  document.body.classList.remove("is-load-error");
  document.body.classList.add("is-loading");
  document.querySelector("#machine-panel")?.setAttribute("aria-busy", "true");
  setFallback(definition, `Loading ${definition.name}. Evidence remains available below if interactive geometry cannot start.`);
  setLoadingStatus(definition, "Loading evidence for");

  if (scrollToHero) {
    document.querySelector("#top")?.scrollIntoView({ behavior: reducedMotionQuery.matches ? "auto" : "smooth" });
  }

  try {
    const [configuration, facts, receipt, validation] = await Promise.all([
      fetchJson(definition.assets.configuration, "Configuration", signal),
      fetchJson(definition.assets.facts, "Facts", signal),
      fetchJson(definition.assets.receipt, "Receipt", signal),
      fetchJson(definition.assets.validation, "Validation", signal)
    ]);
    if (isSuperseded(token, signal)) return;
    assertEvidenceIdentity(machineId, { Configuration: configuration, Facts: facts, Receipt: receipt, Validation: validation });
    const evidenceSnapshot = createEvidenceSnapshot(definition, configuration, facts, receipt, validation);

    if (!interactiveAvailable) {
      clearMotion();
      applyMachineIdentity(machineId, definition, evidenceSnapshot);
      updateDeepLink(machineId, historyMode);
      dom.status.textContent = `${definition.name} · static evidence view`;
      document.body.classList.add("is-ready", "is-static");
      return;
    }

    const expectedHash = String(receipt.artifacts?.glb?.sha256 ?? "").toLowerCase();
    if (!/^[a-f0-9]{64}$/u.test(expectedHash)) throw new Error("Receipt does not provide a valid GLB SHA-256");
    const glbUrl = new URL(definition.assets.glb, document.baseURI);
    glbUrl.searchParams.set("sha256", expectedHash);
    setLoadingStatus(definition, "Loading hash-bound geometry for");
    const glbBytes = await fetchGlb(glbUrl, signal);
    if (isSuperseded(token, signal)) return;

    setLoadingStatus(definition, "Verifying geometry for");
    const actualHash = await sha256Hex(glbBytes);
    if (isSuperseded(token, signal)) return;
    if (actualHash !== expectedHash) throw new Error(`GLB SHA-256 mismatch: expected ${expectedHash}, received ${actualHash}`);

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
    candidateModel.name = `${machineId}-viewer-root`;
    candidateModel.updateMatrixWorld(true);
    setModelShadows(candidateModel);
    fitCamera(candidateModel, definition, !currentModel);

    const previousModel = currentModel;
    scene.add(candidateModel);
    currentModel = candidateModel;
    candidateModel = null;
    bindMotion(currentModel, definition);
    applyMachineIdentity(machineId, definition, evidenceSnapshot);
    dom.fallback.setAttribute("aria-hidden", "true");
    disposeModel(previousModel);
    updateDeepLink(machineId, historyMode);
    dom.status.textContent = `${definition.name} · study loaded`;
    document.body.classList.add("is-ready");
  } catch (error) {
    if (candidateModel) disposeModel(candidateModel);
    if (isSuperseded(token, signal) || error.name === "AbortError") return;
    console.error(error);
    document.body.classList.add("is-load-error");
    setFallback(definition, `${definition.name} could not load interactively. Its catalog metadata remains available.`);
    if (!currentModel) dom.fallback.setAttribute("aria-hidden", "false");
    dom.status.textContent = currentModel && definitions.has(currentMachineId)
      ? `${definition.name} unavailable · ${definitions.get(currentMachineId).name} remains loaded`
      : `${definition.name} unavailable · no study loaded`;
  } finally {
    if (activeLoadController === controller) {
      activeLoadController = null;
      loadingMachineId = null;
      document.body.classList.remove("is-loading");
      document.querySelector("#machine-panel")?.setAttribute("aria-busy", "false");
      updateActiveRows();
    }
  }
}

function createMachineRow(entry) {
  const fragment = dom.machineTemplate.content.cloneNode(true);
  const row = fragment.querySelector("button");
  row.dataset.machine = entry.id;
  row.id = `machine-tab-${entry.id}`;
  row.querySelector(".machine-number").textContent = String(entry.priority).padStart(2, "0");
  row.querySelector(".machine-name").textContent = entry.definition?.name ?? entry.id;
  row.querySelector(".machine-type").textContent = entry.definition?.className ?? "Viewer unavailable";
  row.querySelector(".machine-category").textContent = entry.definition?.category ?? "Unavailable";
  if (!entry.definition) {
    row.disabled = true;
    row.setAttribute("aria-label", `${entry.id}, viewer configuration unavailable`);
  } else {
    row.addEventListener("click", () => selectMachine(entry.id, { scrollToHero: true, historyMode: "push" }));
    row.addEventListener("keydown", selectAdjacentTab);
  }
  return row;
}

function filteredEntries() {
  return catalogEntries.filter((entry) => {
    const definition = entry.definition;
    if (!definition) return activeCategory === "all" && (!searchTerm || entry.id.includes(searchTerm));
    const categoryMatch = activeCategory === "all" || definition.category === activeCategory;
    const haystack = `${entry.id} ${definition.name} ${definition.className} ${definition.category}`.toLocaleLowerCase();
    return categoryMatch && (!searchTerm || haystack.includes(searchTerm));
  });
}

function renderMachineIndex() {
  const visibleEntries = filteredEntries();
  const fragment = document.createDocumentFragment();
  rows = [];
  for (const entry of visibleEntries) {
    const row = createMachineRow(entry);
    rows.push(row);
    fragment.append(row);
  }
  dom.machineIndex.replaceChildren(fragment);
  dom.catalogEmpty.hidden = visibleEntries.length !== 0;
  const available = catalogEntries.filter((entry) => entry.definition).length;
  const unavailable = catalogEntries.length - available;
  dom.catalogSummary.textContent = `${visibleEntries.length} shown · ${available} configured${unavailable ? ` · ${unavailable} unavailable` : ""}`;
  updateActiveRows();
}

function renderCategoryFilters() {
  const categories = [...new Set(catalogEntries.flatMap((entry) => entry.definition ? [entry.definition.category] : []))]
    .sort((a, b) => a.localeCompare(b));
  const fragment = document.createDocumentFragment();
  for (const category of ["all", ...categories]) {
    const button = document.createElement("button");
    button.className = "category-filter";
    button.type = "button";
    button.textContent = category === "all" ? "All machines" : category;
    button.dataset.category = category;
    button.setAttribute("aria-pressed", String(category === activeCategory));
    button.addEventListener("click", () => {
      activeCategory = category;
      for (const candidate of dom.categoryFilters.querySelectorAll("button")) {
        candidate.setAttribute("aria-pressed", String(candidate === button));
      }
      renderMachineIndex();
    });
    fragment.append(button);
  }
  dom.categoryFilters.replaceChildren(fragment);
}

function selectAdjacentTab(event) {
  if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) return;
  const enabledRows = rows.filter((row) => !row.disabled);
  if (enabledRows.length === 0) return;
  event.preventDefault();
  const currentIndex = Math.max(0, enabledRows.indexOf(event.currentTarget));
  const nextIndex = event.key === "Home"
    ? 0
    : event.key === "End"
      ? enabledRows.length - 1
      : (currentIndex + (["ArrowRight", "ArrowDown"].includes(event.key) ? 1 : -1) + enabledRows.length) % enabledRows.length;
  const next = enabledRows[nextIndex];
  next.focus();
  selectMachine(next.dataset.machine, { historyMode: "push" });
}

async function loadCatalog() {
  dom.machineIndex.setAttribute("aria-busy", "true");
  const catalog = await fetchJson(CATALOG_URL, "Catalog");
  if (!Array.isArray(catalog.machines) || catalog.machines.length === 0) throw new Error("Catalog contains no machines");
  const ids = new Set();
  const ordered = [...catalog.machines].sort((a, b) => a.priority - b.priority);
  for (const entry of ordered) {
    if (typeof entry.id !== "string" || !entry.id || ids.has(entry.id)) throw new Error("Catalog machine ids must be unique strings");
    ids.add(entry.id);
  }

  const results = await Promise.allSettled(ordered.map(async (entry) => {
    const document = await fetchJson(`machines/${entry.id}/viewer.json`, `${entry.id} viewer`);
    return normalizeViewer(document, entry);
  }));

  catalogEntries = ordered.map((entry, index) => {
    const result = results[index];
    if (result.status === "rejected") console.error(`${entry.id}: ${result.reason?.message ?? result.reason}`);
    const definition = result.status === "fulfilled" ? result.value : null;
    if (definition) definitions.set(entry.id, definition);
    return { id: entry.id, priority: entry.priority, definition };
  });
  dom.machineCount.textContent = String(catalogEntries.length);
  renderCategoryFilters();
  renderMachineIndex();
  dom.machineIndex.setAttribute("aria-busy", "false");

  const requested = new URL(window.location.href).searchParams.get("machine");
  const initial = definitions.has(requested) ? requested : catalogEntries.find((entry) => entry.definition)?.id;
  if (!initial) throw new Error("No machine viewer configurations are available");
  await selectMachine(initial, { historyMode: "replace" });
}

function resize() {
  if (renderer && camera) {
    const width = dom.scene.clientWidth;
    const height = dom.scene.clientHeight;
    renderer.setSize(width, height, false);
    camera.aspect = width / Math.max(1, height);
    camera.updateProjectionMatrix();
  }
  fitHeroTitle();
}

dom.search.addEventListener("input", () => {
  searchTerm = dom.search.value.trim().toLocaleLowerCase();
  renderMachineIndex();
});

dom.search.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || dom.search.value === "") return;
  dom.search.value = "";
  searchTerm = "";
  renderMachineIndex();
});

dom.orbitToggle.addEventListener("click", () => {
  if (!controls || reducedMotionQuery.matches) return;
  autoRotateRequested = !autoRotateRequested;
  dom.orbitToggle.setAttribute("aria-pressed", String(autoRotateRequested));
});

dom.motionToggle.addEventListener("click", () => {
  if (reducedMotionQuery.matches || motionRuntime.bindings.length === 0) return;
  motionRuntime.autoRequested = !motionRuntime.autoRequested;
  motionRuntime.manualHold.clear();
  motionRuntime.wasManual = false;
  if (!motionRuntime.autoRequested) {
    for (const binding of motionRuntime.bindings) binding.manual = binding.current;
  }
  dom.motionToggle.setAttribute("aria-pressed", String(motionRuntime.autoRequested));
  setMotionState(motionRuntime.autoRequested ? "Automatic presentation" : "Manual presentation");
});

dom.resetView.addEventListener("click", () => {
  if (currentCamera) animateCamera(currentCamera.position, currentCamera.target);
});

dom.technicalView.addEventListener("click", () => {
  if (!currentTechnicalCamera || !controls) return;
  autoRotateRequested = false;
  controls.autoRotate = false;
  dom.orbitToggle.setAttribute("aria-pressed", "false");
  animateCamera(currentTechnicalCamera.position, currentTechnicalCamera.target);
});

dom.scene.addEventListener("keydown", (event) => {
  if (!camera || !controls || !currentCamera) return;
  const keys = new Set(["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "+", "=", "-", "_", "Home"]);
  if (!keys.has(event.key)) return;
  event.preventDefault();
  cameraManualHold.hold(performance.now());
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
  if (["+", "="].includes(event.key)) spherical.radius = Math.max(controls.minDistance, spherical.radius * 0.9);
  if (["-", "_"].includes(event.key)) spherical.radius = Math.min(controls.maxDistance, spherical.radius * 1.1);
  camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));
  controls.update();
});

window.addEventListener("resize", resize);
window.addEventListener("popstate", () => {
  const machineId = new URL(window.location.href).searchParams.get("machine");
  if (definitions.has(machineId) && machineId !== currentMachineId) selectMachine(machineId, { historyMode: null });
});

document.addEventListener("visibilitychange", () => {
  if (controls) controls.autoRotate = false;
});

reducedMotionQuery.addEventListener("change", (event) => {
  if (event.matches) {
    autoRotateRequested = false;
    if (controls) controls.autoRotate = false;
    dom.orbitToggle.disabled = true;
    dom.orbitToggle.setAttribute("aria-pressed", "false");
    motionRuntime.autoRequested = false;
    motionRuntime.manualHold.clear();
    dom.motionToggle.disabled = true;
    dom.motionToggle.setAttribute("aria-pressed", "false");
    setMotionState("Static · reduced motion");
    return;
  }
  dom.orbitToggle.disabled = !interactiveAvailable;
  dom.motionToggle.disabled = !interactiveAvailable || motionRuntime.bindings.length === 0;
  if (motionRuntime.bindings.length > 0) setMotionState("Manual presentation");
});

const clock = new THREE.Clock();
function render(now = performance.now()) {
  if (!renderer || !scene || !camera || !controls) return;
  const delta = Math.min(clock.getDelta(), 0.1);
  controls.autoRotate =
    autoRotateRequested && !document.hidden && !reducedMotionQuery.matches && !cameraManualHold.isActive(now);
  controls.update(delta);
  updateMotion(now, delta);
  renderer.render(scene, camera);
  requestAnimationFrame(render);
}

async function boot() {
  makeScene();
  dom.orbitToggle.disabled = reducedMotionQuery.matches || !interactiveAvailable;
  dom.orbitToggle.setAttribute("aria-pressed", String(autoRotateRequested && interactiveAvailable));
  resize();
  if (renderer) render();
  try {
    await loadCatalog();
  } catch (error) {
    console.error(error);
    document.body.classList.add("is-load-error", "is-static");
    dom.fallback.setAttribute("aria-hidden", "false");
    dom.fallbackCopy.textContent = "The machine catalog could not be loaded. Please refresh or use a deployed build.";
    dom.status.textContent = "Machine catalog unavailable";
    dom.catalogSummary.textContent = "Catalog unavailable.";
    dom.machineIndex.setAttribute("aria-busy", "false");
  }
}

boot();
