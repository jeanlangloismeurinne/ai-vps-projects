// Option C, second scale: the satellites in orbit, seen from space. The roof
// view keeps them as points in the sky; this view shows where they really are.
// Distances in km; the Earth and the 480 km altitude are to scale, the
// satellites and beams are enlarged to be visible.
import {
  AdditiveBlending,
  BackSide,
  BufferGeometry,
  Color,
  CylinderGeometry,
  DirectionalLight,
  Float32BufferAttribute,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PerspectiveCamera,
  Points,
  PointsMaterial,
  Scene,
  ShaderMaterial,
  SphereGeometry,
  SRGBColorSpace,
  TextureLoader,
  Vector3,
  AmbientLight,
  BoxGeometry,
  Group,
  Line,
  LineBasicMaterial,
  LineDashedMaterial,
} from "three";
import earthUrl from "./assets/earth_day_4096.jpg?url";
import { random } from "./common";

const R = 6371;
const ALT = 480;

function latLon(lat: number, lon: number, r: number): Vector3 {
  const phi = ((90 - lat) * Math.PI) / 180;
  const theta = ((lon + 180) * Math.PI) / 180;
  return new Vector3(-r * Math.sin(phi) * Math.cos(theta), r * Math.cos(phi), r * Math.sin(phi) * Math.sin(theta));
}

function satellite(): Group {
  const g = new Group();
  const metal = new MeshStandardMaterial({ color: "#c9ccd2", metalness: 0.6, roughness: 0.35 });
  const solar = new MeshStandardMaterial({ color: "#1f3a6b", metalness: 0.4, roughness: 0.3, emissive: "#0a1830" });
  const bus = new Mesh(new BoxGeometry(110, 16, 60), metal);
  const wing = new Mesh(new BoxGeometry(330, 4, 66), solar);
  wing.position.x = 230;
  g.add(bus, wing);
  return g;
}

export function buildOrbitScene(aspect: number): { scene: Scene; camera: PerspectiveCamera } {
  const scene = new Scene();
  scene.background = new Color("#02040a");
  const tex = new TextureLoader().load(earthUrl);
  tex.colorSpace = SRGBColorSpace;
  tex.anisotropy = 8;
  const earth = new Mesh(new SphereGeometry(R, 128, 96), new MeshStandardMaterial({ map: tex, roughness: 0.9 }));
  scene.add(earth);

  // Thin atmosphere glow at the limb.
  const atmosphere = new Mesh(
    new SphereGeometry(R * 1.018, 96, 64),
    new ShaderMaterial({
      side: BackSide,
      transparent: true,
      blending: AdditiveBlending,
      depthWrite: false,
      vertexShader: `varying vec3 vN; varying vec3 vV; void main(){ vec4 p = modelViewMatrix*vec4(position,1.); vN = normalize(normalMatrix*normal); vV = normalize(-p.xyz); gl_Position = projectionMatrix*p; }`,
      fragmentShader: `varying vec3 vN; varying vec3 vV; void main(){ float f = pow(1.0 - abs(dot(vN, vV)), 3.0); gl_FragColor = vec4(vec3(0.35,0.6,1.0)*f*1.6, f); }`,
    }),
  );
  scene.add(atmosphere);

  const rnd = random(9);
  const stars: number[] = [];
  for (let i = 0; i < 4000; i++) {
    const v = new Vector3(rnd() - 0.5, rnd() - 0.5, rnd() - 0.5).normalize().multiplyScalar(90000);
    stars.push(v.x, v.y, v.z);
  }
  const starGeo = new BufferGeometry();
  starGeo.setAttribute("position", new Float32BufferAttribute(stars, 3));
  scene.add(new Points(starGeo, new PointsMaterial({ color: "#ffffff", size: 1.6, sizeAttenuation: false })));

  const sunLight = new DirectionalLight("#ffffff", 3);
  scene.add(sunLight, new AmbientLight("#223", 0.4));

  // A home in France, its gateway ~600 km away, a train of satellites along one orbit.
  const home = latLon(46.5, 2.5, R);
  const gateway = latLon(44.5, 8.5, R);
  const marker = (p: Vector3, color: string) => {
    const m = new Mesh(new SphereGeometry(14, 16, 12), new MeshBasicMaterial({ color }));
    m.position.copy(p);
    scene.add(m);
  };
  marker(home, "#ffb000");
  marker(gateway, "#3fd0ff");

  const up = home.clone().normalize();
  const east = new Vector3(0, 1, 0).cross(up).normalize();
  const north = up.clone().cross(east).normalize();
  const track = east.clone().multiplyScalar(Math.cos(0.9)).addScaledVector(north, Math.sin(0.9)).normalize();
  const orbitPoints: Vector3[] = [];
  for (let a = -0.5; a <= 0.5; a += 0.005) orbitPoints.push(up.clone().applyAxisAngle(up.clone().cross(track).normalize(), a).multiplyScalar(R + ALT));
  scene.add(new Line(new BufferGeometry().setFromPoints(orbitPoints), new LineBasicMaterial({ color: "#8fa6c8", transparent: true, opacity: 0.5 })));
  const sats: Vector3[] = [];
  for (const a of [-0.3, -0.15, 0.02, 0.17, 0.32]) {
    const p = up.clone().applyAxisAngle(up.clone().cross(track).normalize(), a).multiplyScalar(R + ALT);
    const s = satellite();
    s.position.copy(p);
    s.lookAt(0, 0, 0);
    scene.add(s);
    sats.push(p);
  }
  const serving = sats[2]!;
  const beam = (from: Vector3, to: Vector3, color: string) => {
    const l = new Line(new BufferGeometry().setFromPoints([from, to]), new LineDashedMaterial({ color, dashSize: 25, gapSize: 15 }));
    l.computeLineDistances();
    scene.add(l);
    const len = from.distanceTo(to);
    const cone = new Mesh(new CylinderGeometry(4, 40, len, 24, 1, true), new MeshBasicMaterial({ color, transparent: true, opacity: 0.12, depthWrite: false }));
    cone.position.copy(from).add(to).multiplyScalar(0.5);
    cone.lookAt(to);
    cone.rotateX(Math.PI / 2);
    scene.add(cone);
  };
  beam(home, serving, "#ffb000");
  beam(serving, gateway, "#3fd0ff");

  // Camera behind and above the train, looking down along the orbit towards the limb.
  const camera = new PerspectiveCamera(42, aspect, 10, 200000);
  camera.position.copy(up.clone().multiplyScalar(R + 1500)).addScaledVector(track, -1800).addScaledVector(east.clone().cross(track).normalize(), 600);
  camera.up.copy(up);
  camera.lookAt(up.clone().multiplyScalar(R + 150).addScaledVector(track, 900));
  // Daytime below the satellites: the Sun is behind the camera, a little to the side.
  sunLight.position.copy(camera.position).normalize().multiplyScalar(30000).addScaledVector(east, 12000);
  return { scene, camera };
}
