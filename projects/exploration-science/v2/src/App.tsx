import { Canvas, useThree } from "@react-three/fiber";
import { useGLTF } from "@react-three/drei";
import { Suspense, useEffect, useLayoutEffect, useMemo, useState } from "react";
import { Box3, MathUtils, PCFSoftShadowMap, PMREMGenerator, Sphere, Vector3, type Mesh, type Object3D } from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { MODELS_BASE, type Manifest } from "./manifest";
import { exposeDebug } from "./debug";

const FOV = 20;
const AZIMUTH = MathUtils.degToRad(-35);
const ELEVATION = MathUtils.degToRad(32);

export function App() {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${MODELS_BASE}/manifest.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`manifest: HTTP ${r.status}`))))
      .then(setManifest)
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return <p className="fatal">{error}</p>;
  return (
    <Canvas
      shadows={{ type: PCFSoftShadowMap }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
      camera={{ fov: FOV, near: 0.1, far: 500 }}
    >
      <Lighting />
      <Suspense fallback={null}>{manifest && <Models manifest={manifest} />}</Suspense>
    </Canvas>
  );
}

function Lighting() {
  const { gl, scene } = useThree();
  useEffect(() => {
    // Local environment for metal and glass reflections: no remote HDRI (QUALITY_BAR §2).
    const pmrem = new PMREMGenerator(gl);
    const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = env;
    scene.environmentIntensity = 0.55;
    return () => {
      env.dispose();
      pmrem.dispose();
    };
  }, [gl, scene]);
  return (
    <>
      <hemisphereLight args={["#ffffff", "#c9cedb", 1.1]} />
      <directionalLight
        position={[6, 10, 4]}
        intensity={1.6}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-radius={6}
        shadow-bias={-0.0004}
        shadow-normalBias={0.02}
        shadow-camera-left={-6}
        shadow-camera-right={6}
        shadow-camera-top={6}
        shadow-camera-bottom={-6}
      />
    </>
  );
}

function Models({ manifest }: { manifest: Manifest }) {
  const urls = useMemo(
    () => Object.values(manifest.assets).map((a) => `${MODELS_BASE}/${a.representations.envelope.file}`),
    [manifest],
  );
  // No Draco (its decoder would come from a CDN); meshopt decodes locally.
  const gltfs = useGLTF(urls, false, true);
  const roots = useMemo(() => gltfs.map((g) => g.scene), [gltfs]);
  const { camera, gl, size } = useThree();

  useLayoutEffect(() => {
    for (const root of roots) {
      root.traverse((o: Object3D) => {
        const mesh = o as Mesh;
        if (mesh.isMesh) {
          mesh.castShadow = true;
          mesh.receiveShadow = true;
        }
      });
    }
    // Frame everything: fit the bounding sphere in the vertical field of view.
    const box = new Box3();
    for (const root of roots) box.expandByObject(root);
    const sphere = box.getBoundingSphere(new Sphere());
    const halfFov = MathUtils.degToRad(FOV / 2);
    const aspect = size.width / size.height;
    const fit = sphere.radius / Math.sin(Math.min(halfFov, Math.atan(Math.tan(halfFov) * aspect)));
    const dir = new Vector3(Math.cos(ELEVATION) * Math.sin(AZIMUTH), Math.sin(ELEVATION), Math.cos(ELEVATION) * Math.cos(AZIMUTH));
    camera.position.copy(sphere.center).addScaledVector(dir, fit * 1.05);
    camera.lookAt(sphere.center);
    exposeDebug(gl);
  }, [roots, camera, gl, size]);

  return (
    <>
      {roots.map((r, i) => (
        <primitive key={urls[i]} object={r} />
      ))}
    </>
  );
}
