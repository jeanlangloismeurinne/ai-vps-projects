// Quick still mockups of the complementary directions, to judge them before a
// real prototype: E photographed ground and sky (ground-projected panorama),
// F photographed materials, G camera look (grade, vignette, grain, depth of
// field), D path tracing once the camera stops. Stills only: nothing here is tuned
// for frame rate.
import {
  BufferAttribute,
  Color,
  BufferGeometry,
  InstancedMesh,
  Matrix3,
  Matrix4,
  DirectionalLight,
  EquirectangularReflectionMapping,
  Mesh,
  MeshStandardMaterial,
  PlaneGeometry,
  RepeatWrapping,
  ShadowMaterial,
  SRGBColorSpace,
  TextureLoader,
  Vector3,
  type Material,
  type Texture,
} from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { HDRLoader } from "three/examples/jsm/loaders/HDRLoader.js";
import { GroundedSkybox } from "three/examples/jsm/objects/GroundedSkybox.js";
import { BokehPass } from "three/examples/jsm/postprocessing/BokehPass.js";
import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
import { WebGLPathTracer } from "three-gpu-pathtracer";
import meadowUrl from "./assets/noon_grass_2k.hdr?url";
import studioUrl from "./assets/studio_small_09_2k.hdr?url";
import brickUrl from "./assets/pbr/brick_diffuse.jpg?url";
import brickBumpUrl from "./assets/pbr/brick_bump.jpg?url";
import brickRoughUrl from "./assets/pbr/brick_roughness.jpg?url";
import grassUrl from "./assets/pbr/grasslight-big.jpg?url";
import { type Stage } from "./common";
import { houseMaterials, sunDirection } from "./photo";

export const PANORAMAS = { meadow: meadowUrl, studio: studioUrl };

export async function loadPanorama(url: string): Promise<Texture> {
  const t = await new HDRLoader().loadAsync(url);
  t.mapping = EquirectangularReflectionMapping;
  return t;
}

/** Sun as a shadow-casting light, aimed from the brightest pixel of the panorama. */
async function sunFromPanorama(stage: Stage, url: string, intensity: number): Promise<DirectionalLight> {
  const dir = await sunDirection(url);
  const light = new DirectionalLight(new Color("#fff4e4"), intensity);
  light.position.copy(dir).multiplyScalar(200);
  light.castShadow = true;
  light.shadow.mapSize.set(4096, 4096);
  Object.assign(light.shadow.camera, { left: -45, right: 45, top: 45, bottom: -45, near: 10, far: 500 });
  light.shadow.bias = -0.0004;
  light.shadow.normalBias = 0.04;
  light.shadow.radius = 3;
  stage.scene.add(light, light.target);
  return light;
}

/**
 * E: the photo is projected on a ground disc, so the house stands in the
 * photographed meadow; a shadow catcher puts our shadows on the photo.
 * `pathTraced`: the path tracer cannot draw the projected ground (custom shader),
 * so the ground is a photographed grass texture instead and the panorama stays the sky.
 */
export async function addPhotographedPlace(stage: Stage, opts: { pathTraced: boolean }): Promise<Texture> {
  const pano = await loadPanorama(meadowUrl);
  stage.scene.environment = pano;
  stage.scene.environmentIntensity = 1;
  stage.scene.fog = null;
  if (opts.pathTraced) {
    stage.scene.background = pano;
    const grass = await photoTexture(grassUrl, true);
    grass.repeat.set(160, 160);
    const ground = new Mesh(new PlaneGeometry(1600, 1600).rotateX(-Math.PI / 2), new MeshStandardMaterial({ map: grass, roughness: 1 }));
    ground.receiveShadow = true;
    stage.scene.add(ground);
  } else {
    const catcher = new Mesh(new PlaneGeometry(200, 200).rotateX(-Math.PI / 2), new ShadowMaterial({ opacity: 0.7, color: "#141d0c" }));
    catcher.position.y = 0.005;
    catcher.receiveShadow = true;
    stage.scene.add(catcher);
  }
  await sunFromPanorama(stage, meadowUrl, opts.pathTraced ? 2.2 : 2.6);
  return pano;
}

/**
 * The projected photo is exact only from where it was taken: centre it under the
 * camera, at the camera's height (call after placing the camera). A camera that
 * moves would need the ground to follow it, or several panoramas.
 */
export function groundAtCamera(stage: Stage, pano: Texture): void {
  const cam = stage.camera.position;
  const sky = new GroundedSkybox(pano, Math.max(cam.y, 0.5), 400, 192);
  sky.name = "grounded-sky";
  sky.position.set(cam.x, cam.y - 0.01, cam.z);
  stage.scene.add(sky);
}

/** World-scale UVs (box projection), so a photo texture keeps its real size on every face. */
export function worldUVs(mesh: Mesh, tile: number): void {
  mesh.updateMatrixWorld(true);
  const g = mesh.geometry.index ? mesh.geometry.toNonIndexed() : mesh.geometry.clone();
  g.computeVertexNormals();
  const pos = g.attributes.position!;
  const nor = g.attributes.normal!;
  const uv = new Float32Array(pos.count * 2);
  const p = new Vector3();
  const n = new Vector3();
  const normalMatrix = new Matrix3().getNormalMatrix(mesh.matrixWorld);
  for (let i = 0; i < pos.count; i++) {
    p.fromBufferAttribute(pos, i).applyMatrix4(mesh.matrixWorld);
    n.fromBufferAttribute(nor, i).applyMatrix3(normalMatrix);
    const [ax, ay, az] = [Math.abs(n.x), Math.abs(n.y), Math.abs(n.z)];
    const [u, v] = ay > ax && ay > az ? [p.x, p.z] : ax > az ? [p.z, p.y] : [p.x, p.y];
    uv[i * 2] = u / tile;
    uv[i * 2 + 1] = v / tile;
  }
  g.setAttribute("uv", new BufferAttribute(uv, 2));
  mesh.geometry = g;
}

async function photoTexture(url: string, srgb: boolean): Promise<Texture> {
  const t = await new TextureLoader().loadAsync(url);
  t.wrapS = t.wrapT = RepeatWrapping;
  t.anisotropy = 8;
  if (srgb) t.colorSpace = SRGBColorSpace;
  return t;
}

/**
 * F: photographed brick (colour, relief, roughness) on the format's house walls.
 * No photographed roof tile is reachable from this session: the roof keeps the
 * drawn tiles of option B, on world-scale UVs.
 */
export async function photographedMaterials(stage: Stage): Promise<void> {
  const [map, bumpMap, roughnessMap] = await Promise.all([photoTexture(brickUrl, true), photoTexture(brickBumpUrl, false), photoTexture(brickRoughUrl, false)]);
  const brick = new MeshStandardMaterial({ map, bumpMap, bumpScale: 3, roughnessMap });
  const { roof } = houseMaterials();
  const roofMat = roof as MeshStandardMaterial;
  for (const t of [roofMat.map, roofMat.bumpMap]) t?.repeat.set(1, 1);
  const palette = stage.built.palette;
  const swap = new Map<Material, [Material, number]>([
    [palette.material("roof"), [roof, 1.6]],
    [palette.material("wall"), [brick, 2.2]],
  ]);
  stage.built.root.traverse((o) => {
    if (!(o instanceof Mesh) || Array.isArray(o.material)) return;
    const hit = swap.get(o.material);
    if (!hit) return;
    worldUVs(o, hit[1]);
    o.material = hit[0];
  });
}

/** G: what a real camera adds — colour grade, vignette, film grain, optional depth of field. */
export function cameraLook(stage: Stage, opts: { focus?: number; aperture?: number }): void {
  const passes = stage.composer.passes;
  const output = passes.pop()!; // keep OutputPass last-but-one: grade after tone mapping
  if (opts.focus) passes.push(new BokehPass(stage.scene, stage.camera, { focus: opts.focus, aperture: opts.aperture ?? 0.002, maxblur: 0.008 }));
  passes.push(output);
  stage.composer.addPass(
    new ShaderPass({
      uniforms: { tDiffuse: { value: null }, time: { value: 0 } },
      vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
      fragmentShader: `
        uniform sampler2D tDiffuse; uniform float time; varying vec2 vUv;
        float hash(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233)) + time) * 43758.5453); }
        void main(){
          vec3 c = texture2D(tDiffuse, vUv).rgb;
          float l = dot(c, vec3(0.2126, 0.7152, 0.0722));
          c = mix(vec3(l), c, 1.08);                                  // a touch more saturation
          c = c * vec3(1.03, 1.0, 0.96) + vec3(0.0, 0.004, 0.012);   // warm highlights, cool lift
          c = pow(c, vec3(1.04));                                     // gentle contrast
          float v = smoothstep(0.95, 0.35, distance(vUv, vec2(0.5)));
          c *= mix(0.78, 1.0, v);                                     // vignette
          c += (hash(vUv * 1000.0) - 0.5) * 0.025;                    // grain
          gl_FragColor = vec4(c, 1.0);
        }`,
    }),
  );
}

/** D: progressive path tracing of the whole scene; `onDone` after `samples` samples. */
export function pathTrace(stage: Stage, samples: number, onDone: () => void): void {
  // The tracer reads plain meshes only: bake each instanced mesh into one merged
  // mesh; shadow catchers have no meaning here (the tracer computes real shadows).
  const instanced: InstancedMesh[] = [];
  const catchers: Mesh[] = [];
  stage.scene.traverse((o) => {
    if (o instanceof InstancedMesh) instanced.push(o);
    else if (o instanceof Mesh && o.material instanceof ShadowMaterial) catchers.push(o);
  });
  for (const c of catchers) c.visible = false;
  const m = new Matrix4();
  for (const im of instanced) {
    if (!im.visible) continue;
    const parts: BufferGeometry[] = [];
    for (let i = 0; i < im.count; i++) {
      im.getMatrixAt(i, m);
      parts.push(im.geometry.clone().applyMatrix4(m));
    }
    const baked = new Mesh(mergeGeometries(parts), im.material);
    baked.matrix.copy(im.matrix);
    baked.matrixAutoUpdate = false;
    baked.castShadow = baked.receiveShadow = true;
    im.parent?.add(baked);
    im.visible = false;
  }
  stage.scene.updateMatrixWorld(true);
  const tracer = new WebGLPathTracer(stage.renderer);
  tracer.bounces = 5;
  tracer.tiles.set(3, 3);
  tracer.minSamples = 0;
  tracer.renderDelay = 0;
  tracer.fadeDuration = 0;
  tracer.filterGlossyFactor = 0.5;
  tracer.setScene(stage.scene, stage.camera);
  let done = false;
  stage.renderer.setAnimationLoop(() => {
    tracer.renderSample();
    Object.assign(window, { protoSamples: tracer.samples });
    if (!done && tracer.samples >= samples) {
      done = true;
      onDone();
    }
  });
}
