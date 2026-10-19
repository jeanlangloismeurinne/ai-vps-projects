// Render prototypes for the arrival on the Starlink scene. ?option = now | a | b | c,
// ?shot = arrival | roof (all options), orbit (option c), lab (?option = now | better).
import { type Texture, Color, Fog, Mesh, MeshStandardMaterial, PCFSoftShadowMap, PlaneGeometry, PMREMGenerator, ShadowMaterial, DirectionalLight, HemisphereLight, type Scene } from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import phasedArrayJson from "../../content/nodes/starlink-phased-array/scene.json";
import type { Scene as SceneFile, Shot } from "../../engine/src/content/types";
import { backgroundColor, createLighting } from "../../engine/src/core/environment";
import { PluginRegistry } from "../../engine/src/core/registry";
import { buildScene } from "../../engine/src/core/sceneBuilder";
import { registerComponents } from "../../engine/src/plugins/components";
import { catalogue, createStage, entity, hide, placeSatellites, run, shoot, starlink, type Stage } from "./common";
import { addKenneyNeighbourhood } from "./kenney";
import { addProceduralNeighbourhood } from "./neighbourhood";
import { buildOrbitScene } from "./orbit";
import { addClouds, addGround, addSkyAndLight, enableShadows } from "./outdoor";
import { addPhotographedSky, realisticMaterials } from "./photo";
import { diorama } from "./diorama";
import { addPhotographedPlace, cameraLook, groundAtCamera, loadPanorama, pathTrace, photographedMaterials, PANORAMAS } from "./mockups";

// ?option=…&shot=… in dev; #option-shot (e.g. #c-orbit) where only the hash reaches the page (published preview).
const q = new URLSearchParams(location.search);
const [hashOption, hashShot] = location.hash.length > 1 ? location.hash.slice(1).split("-") : [];
const option = q.get("option") ?? hashOption ?? "a";
const shotName = q.get("shot") ?? hashShot ?? "arrival";
window.addEventListener("hashchange", () => location.reload());
if (q.has("capture")) document.body.classList.add("capture");
const app = document.querySelector<HTMLElement>("#app")!;
const ready = () => Object.assign(window, { protoReady: true });

const SHOTS: Record<string, Shot> = {
  arrival: { target: "house", azimuthDeg: 25, elevationDeg: 10, distance: 40 },
  roof: { target: "terminal", azimuthDeg: 30, elevationDeg: 16, distance: 3.6 },
};
const PLOT = { streetZ: 14 };

const nav = document.querySelector("#bar")!;
for (const [o, s, label] of [
  ["now", "arrival", "Actuel"], ["a", "arrival", "A · maquette"], ["b", "arrival", "B · photo"], ["c", "arrival", "C · hybride"],
  ["now", "roof", "Actuel (toit)"], ["a", "roof", "A (toit)"], ["b", "roof", "B (toit)"], ["c", "roof", "C (toit)"],
  ["c", "orbit", "C · orbite"], ["now", "lab", "Labo actuel"], ["better", "lab", "Labo amélioré"],
  ["e", "arrival", "E+F+G"], ["e", "roof", "E+F+G (toit)"], ["d", "arrival", "D tracé"], ["d", "roof", "D tracé (toit)"],
  ["studio", "lab", "Labo studio"], ["dpt", "lab", "Labo tracé"], ["m", "overview", "Maquette · système"], ["m", "house", "Maquette · maison"],
] as const) {
  const a = Object.assign(document.createElement("a"), { href: `#${o}-${s}`, textContent: label });
  if (o === option && s === shotName) a.className = "on";
  nav.append(a);
}

function controls(stage: Stage, target: Shot): void {
  const c = new OrbitControls(stage.camera, stage.renderer.domElement);
  c.target.copy(stage.built.focusPoint(target.target));
  c.enableDamping = true;
  c.maxPolarAngle = Math.PI * 0.495;
  stage.tickers.push(() => c.update());
}

async function outdoor(): Promise<void> {
  // A photographed ground only holds near the photo's eye height: arrive at street level.
  const shot = option === "e" || option === "d" ? { ...SHOTS[shotName]!, ...(shotName === "arrival" ? { elevationDeg: 2, distance: 26 } : option === "d" ? { elevationDeg: 24, distance: 5.5 } : {}) } : (SHOTS[shotName] ?? SHOTS.arrival!);
  const fov = shotName === "arrival" ? 50 : 45;
  const stage = createStage(app, { ao: option !== "now" && option !== "e" && !q.has("noao"), bloom: 0, exposure: option === "b" ? 0.85 : option === "now" ? 1 : option === "e" || option === "d" ? 1 : 0.62, fov });
  hide(stage, ["gateway", "internet"]);
  let pano: Texture | undefined;
  entity(stage, "link-user-a").visible = true;
  if (option === "now") {
    stage.scene.add(createLighting(starlink.environment));
    stage.scene.background = backgroundColor(starlink.environment);
    stage.renderer.shadowMap.enabled = false;
  } else {
    hide(stage, ["ground"]);
    // Far in the sky, along one track: the serving satellite, the next one following lower.
    placeSatellites(stage, { azimuthDeg: 205, elevationsDeg: [19, 9], distance: 700, scale: 4 });
    enableShadows(stage.built.root);
    if (option === "e" || option === "d") {
      pano = await addPhotographedPlace(stage, { pathTraced: option === "d" });
      await photographedMaterials(stage);
      stage.scene.traverse((o) => {
        if (o instanceof Mesh && !(o.material instanceof ShadowMaterial) && o.name !== "grounded-sky") {
          o.receiveShadow = true;
          o.castShadow = o.geometry.type !== "PlaneGeometry";
        }
      });
    } else {
      if (option === "b") await addPhotographedSky(stage);
      else addSkyAndLight(stage);
      if (q.has("nofog")) stage.scene.fog = null;
      const meadow = addGround(stage, PLOT);
      if (!q.has("noclouds") && option !== "b") addClouds(stage);
      if (option === "c") await addKenneyNeighbourhood(stage, PLOT);
      else addProceduralNeighbourhood(stage, PLOT);
      if (option === "b") realisticMaterials(stage, meadow);
      // Everything casts and receives shadows, except instanced far trees (outside the shadow area anyway).
      stage.scene.traverse((o) => {
        if (o instanceof Mesh && !(o as { isInstancedMesh?: boolean }).isInstancedMesh) {
          o.receiveShadow = true;
          o.castShadow = o.geometry.type !== "PlaneGeometry"; // flat ground casts nothing
        }
      });
    }
  }
  shoot(stage, shot);
  controls(stage, shot);
  if (option === "e" && pano) groundAtCamera(stage, pano);
  if (option === "e") cameraLook(stage, { focus: shotName === "roof" ? shot.distance : undefined });
  if (option === "d") return pathTrace(stage, Number(q.get("samples") ?? 64), ready);
  let frames = 0;
  run(stage, () => ++frames === 40 && ready());
}

function orbit(): void {
  const stage = createStage(app, { bloom: 0.35, fov: 42 });
  const { scene, camera } = buildOrbitScene(app.clientWidth / app.clientHeight);
  let frames = 0;
  stage.renderer.setAnimationLoop(() => {
    stage.renderer.render(scene, camera);
    if (++frames === 40) ready();
  });
}

async function lab(near = false): Promise<void> {
  const better = option !== "now";
  const stage = createStage(app, { ao: better, bloom: 0, exposure: better ? 0.8 : 1, fov: 45 });
  // Swap the Starlink scene for the level-2 one (the lab views).
  stage.scene.remove(stage.built.root);
  const registry = new PluginRegistry();
  registerComponents(registry);
  const file = phasedArrayJson as unknown as SceneFile;
  const built = buildScene({ ...file, style: starlink.style }, catalogue, registry);
  stage.built = built;
  const scene: Scene = stage.scene;
  scene.add(built.root);
  if (better) {
    if (option === "better") {
      const pmrem = new PMREMGenerator(stage.renderer);
      scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
      scene.environmentIntensity = 0.45;
    } else {
      // A photographed studio as the only light, as in a product shot.
      scene.environment = await loadPanorama(PANORAMAS.studio);
      scene.environmentIntensity = 0.9;
    }
    scene.background = new Color("#1b2532");
    scene.fog = new Fog("#1b2532", 150, 420);
    const key = new DirectionalLight("#ffffff", 1.6);
    key.position.set(40, 90, 60);
    key.castShadow = true;
    key.shadow.mapSize.set(2048, 2048);
    Object.assign(key.shadow.camera, { left: -60, right: 60, top: 60, bottom: -60, near: 1, far: 300 });
    key.shadow.radius = 6;
    scene.add(key, new HemisphereLight("#cfe0ff", "#20262e", 0.4));
    const floor = new Mesh(new PlaneGeometry(600, 600).rotateX(-Math.PI / 2), new ShadowMaterial({ opacity: 0.35 }));
    floor.position.y = -4;
    floor.receiveShadow = true;
    const stage2 = new Mesh(new PlaneGeometry(600, 600).rotateX(-Math.PI / 2), new MeshStandardMaterial({ color: option === "better" ? "#26303d" : "#8d939b", roughness: 0.9 }));
    stage2.position.y = -4.02;
    stage2.receiveShadow = true;
    scene.add(stage2, floor);
    stage.renderer.shadowMap.type = PCFSoftShadowMap;
    enableShadows(built.root);
  } else {
    scene.add(createLighting(file.environment));
    scene.background = backgroundColor(file.environment);
  }
  // A lower angle than the home shot, so depth (layers, chips, shadows) reads in a still image.
  const shot = near ? { ...file.camera.home, azimuthDeg: file.camera.home.azimuthDeg + 20, elevationDeg: 28, distance: 14 } : { ...file.camera.home, elevationDeg: 22, distance: 70 };
  shoot(stage, shot);
  controls(stage, shot);
  if (option === "studio") cameraLook(stage, {});
  if (option === "dpt") return pathTrace(stage, Number(q.get("samples") ?? 64), ready);
  let frames = 0;
  run(stage, () => ++frames === 40 && ready());
}

if (option === "m") void diorama(app, shotName, ready);
else if (shotName === "orbit") orbit();
else if (shotName === "lab" || shotName === "labnear") void lab(shotName === "labnear");
else void outdoor();
