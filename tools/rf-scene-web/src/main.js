/**
 * Coherent exposure studio - a real-time mmWave beamforming exposure scene.
 *
 * The physics is the same as the Blender version: the lobe surface is the
 * array factor of a steered rectangular panel, and the colour on the body is
 *
 *     Sab(r) = Sinc(r) * T0 * ReLU(n_hat . (-k_hat))
 *
 * evaluated per vertex, every time the beam moves. Nothing here is a decal or
 * a painted texture - steer the beam and the hot spot follows because the dot
 * product changes.
 */

import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { RenderPass } from "three/examples/jsm/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { SMAAPass } from "three/examples/jsm/postprocessing/SMAAPass.js";
import PHANTOM from "./phantom.json";

const C0 = 299792458;

const CFG = {
  freqHz: 26e9,
  nx: 16,
  nz: 16,
  spacingLambda: 0.5,
  pTxW: 1.0,
  T0: 0.4,
  apdLimit: 20.0, // ICNIRP 2020 local APD, general public, >6 GHz
  mast: new THREE.Vector3(0, 4.5, -4.5), // three.js is Y-up
  phantomAt: new THREE.Vector3(0.8, 0, 0),
  lobeLen: 6.2,
  lobeDynDb: 25,
  lobeNTheta: 96,
  lobeNPhi: 192,
  // Polar cap actually sampled, measured from the panel boresight. Beyond
  // 90 degrees the element pattern is identically zero, so sampling the back
  // hemisphere was spending half the mesh on guaranteed-empty geometry.
  lobeMaxTheta: 92,
};

const lambda = C0 / CFG.freqHz;
const d = CFG.spacingLambda * lambda;
const k = (2 * Math.PI) / lambda;
const peakGain = CFG.nx * CFG.nz * 2.0;

// ---------------------------------------------------------------- utilities

const TURBO = [
  [0.0, [0.19, 0.07, 0.23]],
  [0.25, [0.1, 0.6, 0.85]],
  [0.5, [0.35, 0.93, 0.4]],
  [0.72, [0.98, 0.83, 0.16]],
  [0.88, [0.98, 0.4, 0.09]],
  [1.0, [0.85, 0.1, 0.05]],
];

function turbo(t, out) {
  t = Math.min(1, Math.max(0, t));
  for (let i = 0; i < TURBO.length - 1; i++) {
    const [t0, c0] = TURBO[i];
    const [t1, c1] = TURBO[i + 1];
    if (t <= t1) {
      const f = (t - t0) / (t1 - t0);
      out[0] = c0[0] + f * (c1[0] - c0[0]);
      out[1] = c0[1] + f * (c1[1] - c0[1]);
      out[2] = c0[2] + f * (c1[2] - c0[2]);
      return out;
    }
  }
  out[0] = 0.85;
  out[1] = 0.1;
  out[2] = 0.05;
  return out;
}

function b64ToArray(b64, Type) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Type(bytes.buffer);
}

/**
 * Normalised power pattern of the steered panel in direction u.
 * Separable rectangular array, so the array factor is two Dirichlet kernels.
 * Axes here are three.js world axes with the panel boresight along -Z.
 */
function powerPattern(ux, uy, uz, sx, sy, sz) {
  // Element pattern: broadside patch facing +Z (toward the pedestrian),
  // dead behind. The mast sits at negative Z, so the panel looks along +Z.
  const element = Math.max(uz, 0);
  if (element <= 0) return 0;

  let af = 1;
  // Panel lies in the XY plane, so the two array axes are x and y.
  const psiX = k * d * (ux - sx);
  const denX = Math.sin(psiX / 2);
  af *= Math.abs(
    Math.abs(denX) < 1e-12 ? CFG.nx : Math.sin((CFG.nx * psiX) / 2) / denX
  );
  const psiY = k * d * (uy - sy);
  const denY = Math.sin(psiY / 2);
  af *= Math.abs(
    Math.abs(denY) < 1e-12 ? CFG.nz : Math.sin((CFG.nz * psiY) / 2) / denY
  );

  const v = af * element;
  return v * v;
}

function patternNormalised(ux, uy, uz, s) {
  const raw = powerPattern(ux, uy, uz, s.x, s.y, s.z);
  const peak = CFG.nx * CFG.nx * CFG.nz * CFG.nz; // (nx*nz)^2 with element=1
  return raw / peak;
}

// ------------------------------------------------------------------- scene

const app = document.getElementById("app");
const renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.95;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
app.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x04060b, 0.0075);

const camera = new THREE.PerspectiveCamera(42, innerWidth / innerHeight, 0.1, 400);

// Frame the panel-to-torso axis rather than hand-placing the camera. Standing
// off to one side of that axis puts the mast at one end of the picture and the
// pedestrian at the other, with the beam running between them, and it keeps
// working if the mast or the pedestrian is moved.
const torso = new THREE.Vector3(CFG.phantomAt.x, 1.3, CFG.phantomAt.z);
const viewMid = new THREE.Vector3().addVectors(CFG.mast, torso).multiplyScalar(0.5);
{
  const axis = new THREE.Vector3().subVectors(torso, CFG.mast).normalize();
  const side = new THREE.Vector3()
    .crossVectors(axis, new THREE.Vector3(0, 1, 0))
    .normalize();
  camera.position
    .copy(viewMid)
    .addScaledVector(side, 5.9)
    .addScaledVector(axis, 0.30)
    .add(new THREE.Vector3(0, 0.15, 0));
}

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(viewMid).lerp(torso, 0.62);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.maxPolarAngle = Math.PI * 0.495;
controls.minDistance = 3;
controls.maxDistance = 45;

// ------------------------------------------------------------------ lights

scene.add(new THREE.HemisphereLight(0x32456b, 0x0a0c14, 0.85));

const key = new THREE.DirectionalLight(0x9fc2ff, 0.34);
key.position.set(-9, 12, 6);
key.castShadow = true;
key.shadow.mapSize.set(1024, 1024);
key.shadow.camera.near = 1;
key.shadow.camera.far = 45;
key.shadow.camera.left = -14;
key.shadow.camera.right = 14;
key.shadow.camera.top = 14;
key.shadow.camera.bottom = -14;
key.shadow.bias = -0.0012;
scene.add(key);

const warmFill = new THREE.PointLight(0xff9a4d, 10, 20, 2);
warmFill.position.set(-5.5, 3.2, 3.5);
scene.add(warmFill);

const rim = new THREE.DirectionalLight(0x7fb0ff, 0.28);
rim.position.set(6.0, 2.6, 4.5);
scene.add(rim);

// ------------------------------------------------------------------ ground

const groundMat = new THREE.MeshStandardMaterial({
  color: 0x11141c,
  roughness: 0.28,
  metalness: 0.6,
});
const ground = new THREE.Mesh(new THREE.PlaneGeometry(300, 300), groundMat);
ground.rotation.x = -Math.PI / 2;
ground.receiveShadow = true;
scene.add(ground);

// --------------------------------------------------------------- buildings

/** Facade shader: windows are a world-space grid, so every block matches. */
const facadeMat = new THREE.ShaderMaterial({
  uniforms: {
    uFogColor: { value: new THREE.Color(0x04060b) },
    uFogDensity: { value: 0.0075 },
  },
  vertexShader: `
    varying vec3 vWorld;
    varying vec3 vNormal;
    void main() {
      vec4 wp = modelMatrix * vec4(position, 1.0);
      vWorld = wp.xyz;
      vNormal = normalize(mat3(modelMatrix) * normal);
      gl_Position = projectionMatrix * viewMatrix * wp;
    }
  `,
  fragmentShader: `
    varying vec3 vWorld;
    varying vec3 vNormal;
    uniform vec3 uFogColor;
    uniform float uFogDensity;

    float hash(vec2 p) {
      return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
    }

    void main() {
      // Pick the two axes that run across this face.
      vec3 n = normalize(vNormal);
      vec2 uv = abs(n.x) > 0.5 ? vec2(vWorld.z, vWorld.y)
                               : vec2(vWorld.x, vWorld.y);

      vec2 cell = vec2(1.05, 1.45);        // window pitch in metres
      vec2 id = floor(uv / cell);
      vec2 f = fract(uv / cell);

      // Window rectangle inside each cell, leaving a concrete frame.
      float win = step(0.16, f.x) * step(f.x, 0.84)
                * step(0.20, f.y) * step(f.y, 0.78);

      // Only some windows are lit, and floors near the ground stay darker.
      float lit = step(0.62, hash(id));
      float upper = smoothstep(1.0, 6.0, vWorld.y);
      float on = win * lit * upper;

      vec3 warm = mix(vec3(1.0, 0.62, 0.28), vec3(0.75, 0.86, 1.0), hash(id + 7.3));
      vec3 concrete = vec3(0.035, 0.038, 0.048);
      // Top faces get no windows.
      on *= step(abs(n.y), 0.5);

      vec3 col = concrete + warm * on * 0.42;

      // Match the scene's exponential fog.
      float dist = length(vWorld - cameraPosition);
      float fogF = 1.0 - exp(-uFogDensity * uFogDensity * dist * dist);
      col = mix(col, uFogColor, clamp(fogF, 0.0, 1.0));

      gl_FragColor = vec4(col, 1.0);
    }
  `,
});

function addBuildings() {
  const group = new THREE.Group();
  // Keep a clear corridor around the mast-to-pedestrian line.
  const blocks = [
    [-17, -16, 12, 26], [-3, -23, 10, 18], [15, -19, 13, 31],
    [31, 16, 11, 15], [-21, 8, 10, 20], [7, -30, 14, 24],
    [-11, -34, 12, 29], [27, -12, 12, 19], [-30, -8, 11, 23],
    [3, 14, 12, 13], [-14, 17, 10, 16], [30, -30, 13, 27],
  ];
  for (const [x, z, foot, h] of blocks) {
    const geo = new THREE.BoxGeometry(foot, h, foot * 0.85);
    const mesh = new THREE.Mesh(geo, facadeMat);
    mesh.position.set(x, h / 2, z);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
  }
  scene.add(group);
  return group;
}
addBuildings();

// ------------------------------------------------------------ mast + panel

const mastGroup = new THREE.Group();
scene.add(mastGroup);

const metal = new THREE.MeshStandardMaterial({ color: 0x14171d, roughness: 0.35, metalness: 0.9 });
const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.095, CFG.mast.y, 20), metal);
pole.position.set(CFG.mast.x, CFG.mast.y / 2, CFG.mast.z);
pole.castShadow = true;
mastGroup.add(pole);

const apertureW = (CFG.nx - 1) * d;
const apertureH = (CFG.nz - 1) * d;
const panel = new THREE.Mesh(
  new THREE.BoxGeometry(apertureW + 3 * d, apertureH + 3 * d, 0.03),
  new THREE.MeshStandardMaterial({ color: 0x0b0d12, roughness: 0.4, metalness: 0.5 })
);
panel.position.copy(CFG.mast);
mastGroup.add(panel);

// Radiating elements, drawn as a real 16x16 grid.
const patchGeo = new THREE.PlaneGeometry(d * 0.68, d * 0.68);
const patchMat = new THREE.MeshBasicMaterial({ color: 0xffb066 });
const patches = new THREE.InstancedMesh(patchGeo, patchMat, CFG.nx * CFG.nz);
{
  const m = new THREE.Matrix4();
  let i = 0;
  for (let ix = 0; ix < CFG.nx; ix++) {
    for (let iz = 0; iz < CFG.nz; iz++) {
      m.makeTranslation(
        CFG.mast.x + (ix - (CFG.nx - 1) / 2) * d,
        CFG.mast.y + (iz - (CFG.nz - 1) / 2) * d,
        CFG.mast.z - 0.017
      );
      patches.setMatrixAt(i++, m);
    }
  }
  patches.instanceMatrix.needsUpdate = true;
}
mastGroup.add(patches);

// ------------------------------------------------------------------- lobe

const lobeGeo = new THREE.BufferGeometry();
{
  const nT = CFG.lobeNTheta;
  const nP = CFG.lobeNPhi;
  const positions = new Float32Array(nT * nP * 3);
  const colors = new Float32Array(nT * nP * 3);
  const indices = [];
  for (let i = 0; i < nT - 1; i++) {
    for (let j = 0; j < nP; j++) {
      const j2 = (j + 1) % nP;
      const a = i * nP + j;
      const b = i * nP + j2;
      const c = (i + 1) * nP + j2;
      const e = (i + 1) * nP + j;
      indices.push(a, b, c, a, c, e);
    }
  }
  lobeGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  lobeGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  lobeGeo.setIndex(indices);
}

const lobe = new THREE.Mesh(
  lobeGeo,
  new THREE.MeshBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.22,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  })
);
lobe.frustumCulled = false;
scene.add(lobe);

const lobeDirs = (() => {
  const nT = CFG.lobeNTheta;
  const nP = CFG.lobeNPhi;
  const dirs = new Float32Array(nT * nP * 3);
  let p = 0;
  for (let i = 0; i < nT; i++) {
    const thMax = (CFG.lobeMaxTheta * Math.PI) / 180;
    const th = 1e-4 + (thMax - 1e-4) * (i / (nT - 1));
    for (let j = 0; j < nP; j++) {
      const ph = (2 * Math.PI * j) / nP;
      dirs[p++] = Math.sin(th) * Math.cos(ph);
      dirs[p++] = Math.sin(th) * Math.sin(ph);
      dirs[p++] = Math.cos(th);
    }
  }
  return dirs;
})();

function updateLobe(steer) {
  const pos = lobeGeo.attributes.position.array;
  const col = lobeGeo.attributes.color.array;
  const rgb = [0, 0, 0];
  const n = lobeDirs.length / 3;
  for (let i = 0; i < n; i++) {
    const ux = lobeDirs[i * 3];
    const uy = lobeDirs[i * 3 + 1];
    const uz = lobeDirs[i * 3 + 2];
    const p = patternNormalised(ux, uy, uz, steer);
    const db = 10 * Math.log10(Math.max(p, 1e-30));
    const level = Math.max(0, (db + CFG.lobeDynDb) / CFG.lobeDynDb);
    const r = level * CFG.lobeLen;
    pos[i * 3] = CFG.mast.x + ux * r;
    pos[i * 3 + 1] = CFG.mast.y + uy * r;
    pos[i * 3 + 2] = CFG.mast.z + uz * r;
    turbo(Math.min(1, level), rgb);
    col[i * 3] = rgb[0];
    col[i * 3 + 1] = rgb[1];
    col[i * 3 + 2] = rgb[2];
  }
  lobeGeo.attributes.position.needsUpdate = true;
  lobeGeo.attributes.color.needsUpdate = true;
}

// ---------------------------------------------------------------- phantom

const phantomPositions = b64ToArray(PHANTOM.positions, Float32Array);
const phantomNormals = b64ToArray(PHANTOM.normals, Float32Array);
const phantomIndices = b64ToArray(PHANTOM.indices, Uint16Array);

const phantomGeo = new THREE.BufferGeometry();
// The STL is Z-up in metres and centred on its bounding box; rotate to Y-up
// and stand it on the ground.
{
  const n = PHANTOM.vertexCount;
  const pos = new Float32Array(n * 3);
  const nrm = new Float32Array(n * 3);
  let minY = Infinity;
  for (let i = 0; i < n; i++) {
    const x = phantomPositions[i * 3];
    const y = phantomPositions[i * 3 + 1];
    const z = phantomPositions[i * 3 + 2];
    // Z-up -> Y-up, and turn to face the mast (mast sits at -Z).
    pos[i * 3] = -x;
    pos[i * 3 + 1] = z;
    pos[i * 3 + 2] = y;
    minY = Math.min(minY, z);

    const nx = phantomNormals[i * 3];
    const ny = phantomNormals[i * 3 + 1];
    const nz = phantomNormals[i * 3 + 2];
    nrm[i * 3] = -nx;
    nrm[i * 3 + 1] = nz;
    nrm[i * 3 + 2] = ny;
  }
  for (let i = 0; i < n; i++) pos[i * 3 + 1] -= minY;
  phantomGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  phantomGeo.setAttribute("normal", new THREE.BufferAttribute(nrm, 3));
  phantomGeo.setAttribute(
    "color",
    new THREE.BufferAttribute(new Float32Array(n * 3), 3)
  );
  phantomGeo.setIndex(new THREE.BufferAttribute(phantomIndices, 1));
}

const phantom = new THREE.Mesh(
  phantomGeo,
  new THREE.MeshStandardMaterial({
    vertexColors: true,
    roughness: 0.45,
    metalness: 0.0,
    emissive: 0xffffff,
    emissiveIntensity: 0.42,
  })
);
phantom.material.emissiveMap = null;
phantom.position.copy(CFG.phantomAt);
phantom.castShadow = true;
phantom.receiveShadow = true;
scene.add(phantom);

// Emissive colour has to track the vertex colour, which a standard material
// will not do on its own; patch the shader so emissive uses vColor.
phantom.material.onBeforeCompile = (shader) => {
  // <emissivemap_fragment> sits after <color_fragment>, so vColor is in scope
  // here. Patching the `totalEmissiveRadiance = emissive` declaration instead
  // put the reference above the point where three declares the varying.
  shader.fragmentShader = shader.fragmentShader.replace(
    "#include <emissivemap_fragment>",
    "#include <emissivemap_fragment>\n\ttotalEmissiveRadiance *= vColor.rgb;"
  );
};

const stats = { peakSab: 0, peakSinc: 0, litFraction: 0, hotIndex: 0 };

function updateExposure(steer) {
  const pos = phantomGeo.attributes.position.array;
  const nrm = phantomGeo.attributes.normal.array;
  const col = phantomGeo.attributes.color.array;
  const n = PHANTOM.vertexCount;

  const ox = CFG.phantomAt.x;
  const oy = CFG.phantomAt.y;
  const oz = CFG.phantomAt.z;

  const sab = new Float32Array(n);
  let peak = 0;
  let peakSinc = 0;
  let lit = 0;
  let hotIndex = 0;

  for (let i = 0; i < n; i++) {
    const wx = pos[i * 3] + ox - CFG.mast.x;
    const wy = pos[i * 3 + 1] + oy - CFG.mast.y;
    const wz = pos[i * 3 + 2] + oz - CFG.mast.z;
    const dist = Math.max(Math.sqrt(wx * wx + wy * wy + wz * wz), 1e-6);
    const kx = wx / dist;
    const ky = wy / dist;
    const kz = wz / dist;

    const p = patternNormalised(kx, ky, kz, steer);
    const gain = p * peakGain;
    const sInc = (CFG.pTxW * gain) / (4 * Math.PI * dist * dist);
    if (sInc > peakSinc) peakSinc = sInc;

    // ReLU(n_hat . (-k_hat)) - only surfaces turned toward the panel absorb.
    const cosInc = Math.max(
      -(nrm[i * 3] * kx + nrm[i * 3 + 1] * ky + nrm[i * 3 + 2] * kz),
      0
    );
    if (cosInc > 0) lit++;

    const v = sInc * CFG.T0 * cosInc;
    sab[i] = v;
    if (v > peak) {
      peak = v;
      hotIndex = i;
    }
  }

  const rgb = [0, 0, 0];
  const inv = peak > 0 ? 1 / peak : 0;
  for (let i = 0; i < n; i++) {
    turbo(Math.pow(sab[i] * inv, 0.75), rgb);
    col[i * 3] = rgb[0];
    col[i * 3 + 1] = rgb[1];
    col[i * 3 + 2] = rgb[2];
  }
  phantomGeo.attributes.color.needsUpdate = true;

  stats.peakSab = peak;
  stats.peakSinc = peakSinc;
  stats.litFraction = lit / n;
  stats.hotIndex = hotIndex;
}

// ------------------------------------------------------------ beam ribbon

const beamLine = new THREE.Line(
  new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]),
  new THREE.LineBasicMaterial({ color: 0xff5a2b, transparent: true, opacity: 0.55 })
);
scene.add(beamLine);

// ------------------------------------------------------------ compositing

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(
  new THREE.Vector2(innerWidth, innerHeight),
  0.42, // strength
  0.45, // radius
  0.85 // threshold - only emissive surfaces cross this
);
composer.addPass(bloom);
composer.addPass(new SMAAPass(innerWidth, innerHeight));
composer.addPass(new OutputPass());

// ------------------------------------------------------------------ steer

const targetPoint = new THREE.Vector3();
const steer = new THREE.Vector3();
let autoSteer = !matchMedia("(prefers-reduced-motion: reduce)").matches;
let manualAim = 1.3;

function computeSteer(aimHeight, sway) {
  targetPoint.set(
    CFG.phantomAt.x + sway,
    aimHeight,
    CFG.phantomAt.z
  );
  steer.copy(targetPoint).sub(CFG.mast).normalize();
  return steer;
}

// -------------------------------------------------------------------- HUD

const hud = {
  eirp: document.getElementById("eirp"),
  sab: document.getElementById("sab"),
  limit: document.getElementById("limit"),
  scan: document.getElementById("scan"),
  dist: document.getElementById("dist"),
  bar: document.getElementById("bar"),
};

const eirpDbm = 10 * Math.log10(CFG.pTxW * peakGain * 1000);
hud.eirp.textContent = eirpDbm.toFixed(1) + " dBm";

function refreshHud() {
  const pct = (stats.peakSab / CFG.apdLimit) * 100;
  hud.sab.textContent = stats.peakSab.toFixed(3) + " W/m²";
  hud.limit.textContent = pct.toFixed(2) + "%";
  hud.bar.style.width = Math.min(100, pct * 10).toFixed(1) + "%";
  hud.bar.style.background =
    pct >= 50 ? "var(--crit)" : pct >= 10 ? "var(--warn)" : "var(--ok)";
  const boresight = new THREE.Vector3(0, 0, 1);
  const scanDeg = (Math.acos(Math.min(1, Math.max(-1, steer.dot(boresight)))) * 180) / Math.PI;
  hud.scan.textContent = scanDeg.toFixed(1) + "°";
  const dm = CFG.mast.distanceTo(
    new THREE.Vector3(CFG.phantomAt.x, 1.3, CFG.phantomAt.z)
  );
  hud.dist.textContent = dm.toFixed(2) + " m";
}

const toggleBtn = document.getElementById("toggle");
toggleBtn.textContent = autoSteer ? "Auto steer: on" : "Auto steer: off";
toggleBtn.addEventListener("click", (e) => {
  autoSteer = !autoSteer;
  e.target.textContent = autoSteer ? "Auto steer: on" : "Auto steer: off";
});

const aimSlider = document.getElementById("aim");
aimSlider.addEventListener("input", () => {
  autoSteer = false;
  document.getElementById("toggle").textContent = "Auto steer: off";
  manualAim = parseFloat(aimSlider.value);
});

// ------------------------------------------------------------------- loop

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  composer.setSize(innerWidth, innerHeight);
});

let frame = 0;
const clock = new THREE.Clock();

function animate() {
  requestAnimationFrame(animate);
  const t = clock.getElapsedTime();

  let aim;
  let sway;
  if (autoSteer) {
    // Sweep the beam up and down the body, with a little lateral drift.
    aim = 1.05 + 0.62 * Math.sin(t * 0.42);
    sway = 0.34 * Math.sin(t * 0.27);
  } else {
    aim = manualAim;
    sway = 0;
  }
  const s = computeSteer(aim, sway);

  // The exposure map is cheap enough to run every frame; the lobe surface is
  // heavier, so it refreshes at about a third of the frame rate.
  updateExposure(s);
  if (frame % 3 === 0) updateLobe(s);

  const bp = beamLine.geometry.attributes.position;
  bp.setXYZ(0, CFG.mast.x, CFG.mast.y, CFG.mast.z);
  bp.setXYZ(1, targetPoint.x, targetPoint.y, targetPoint.z);
  bp.needsUpdate = true;

  if (frame % 6 === 0) refreshHud();

  controls.update();
  composer.render();
  frame++;
}

updateLobe(computeSteer(1.3, 0));
updateExposure(steer);
refreshHud();
animate();

// Multi-angle inspection hook. One camera angle hides mistakes: a surface
// facing away, or a lobe aimed into the back half-space, both look plausible
// head-on. The harness orbits this to check the build from several sides.
window.__studio = {
  camera,
  controls,
  orbit(azimuthDeg, elevationDeg, radius) {
    const a = (azimuthDeg * Math.PI) / 180;
    const e = (elevationDeg * Math.PI) / 180;
    camera.position.set(
      controls.target.x + radius * Math.cos(e) * Math.sin(a),
      controls.target.y + radius * Math.sin(e),
      controls.target.z + radius * Math.cos(e) * Math.cos(a)
    );
    camera.lookAt(controls.target);
    controls.update();
  },
  stats: () => ({ ...stats }),
};

// Signal to the screenshot harness that the first frame is up.
setTimeout(() => {
  document.body.dataset.ready = "1";
}, 600);
