import { Color, DoubleSide, Mesh, PlaneGeometry, ShaderMaterial, Vector3 } from "three";

// Light travelling along a ray, drawn as one wavy thread per colour band: each
// thread has its own wavelength and an opacity set by that band's intensity.
// White light shows every thread about as strong; scattered sky light shows
// the blue ones strong and the red ones faint. The ribbon turns about the ray
// to face the camera.

export const MAX_BANDS = 8;
const SEGMENTS = 400;

export interface RibbonBand {
  /** Linear sRGB of the band. */
  colour: [number, number, number];
  /** Scene units. */
  wavelength: number;
  /** Relative intensity, 0 to 1. */
  intensity: number;
}

const VERTEX = /* glsl */ `
uniform vec3 uStart;
uniform vec3 uEnd;
uniform float uHalfWidth;
varying float vS;
varying float vT;
void main() {
  // position.x in [-0.5, 0.5] runs along the ray, position.y across it.
  float s = position.x + 0.5;
  vec3 axis = uEnd - uStart;
  float len = length(axis);
  vec3 p = uStart + axis * s;
  vec3 across = normalize(cross(axis / len, cameraPosition - p));
  vS = s * len;
  vT = position.y * 2.0;
  gl_Position = projectionMatrix * viewMatrix * vec4(p + across * position.y * 2.0 * uHalfWidth, 1.0);
}`;

const FRAGMENT = /* glsl */ `
uniform int uCount;
uniform vec3 uColours[${MAX_BANDS}];
uniform float uK[${MAX_BANDS}];
uniform float uIntensity[${MAX_BANDS}];
uniform float uTime;
uniform float uLength;
uniform float uLineWidth;
varying float vS;
varying float vT;
void main() {
  vec3 colour = vec3(0.0);
  float total = 0.0;
  float clear = 1.0;
  for (int i = 0; i < ${MAX_BANDS}; i++) {
    if (i >= uCount) break;
    float y = 0.8 * sin(uK[i] * vS - uTime);
    float a = uIntensity[i] * (1.0 - smoothstep(uLineWidth, 2.0 * uLineWidth, abs(vT - y)));
    colour += uColours[i] * a;
    total += a;
    clear *= 1.0 - a;
  }
  // Threads fade in and out at the ends of the ray.
  float ends = smoothstep(0.0, 0.06 * uLength, vS) * smoothstep(0.0, 0.06 * uLength, uLength - vS);
  float alpha = (1.0 - clear) * ends;
  if (alpha < 0.01) discard;
  gl_FragColor = vec4(colour / max(total, 1e-4), alpha);
}`;

export function createRibbon(): { mesh: Mesh; place(from: Vector3, to: Vector3, halfWidth: number, bands: RibbonBand[]): void; tick(phase: number): void; dispose(): void } {
  const uniforms = {
    uStart: { value: new Vector3() },
    uEnd: { value: new Vector3(1, 0, 0) },
    uHalfWidth: { value: 0.1 },
    uCount: { value: 0 },
    uColours: { value: Array.from({ length: MAX_BANDS }, () => new Color()) },
    uK: { value: new Array<number>(MAX_BANDS).fill(1) },
    uIntensity: { value: new Array<number>(MAX_BANDS).fill(0) },
    uTime: { value: 0 },
    uLength: { value: 1 },
    uLineWidth: { value: 0.07 },
  };
  const geometry = new PlaneGeometry(1, 1, SEGMENTS, 1);
  const material = new ShaderMaterial({ uniforms, vertexShader: VERTEX, fragmentShader: FRAGMENT, transparent: true, depthWrite: false, side: DoubleSide, toneMapped: false });
  const mesh = new Mesh(geometry, material);
  mesh.frustumCulled = false; // vertices are placed in the shader
  mesh.renderOrder = 14;
  mesh.raycast = () => {};
  return {
    mesh,
    place(from, to, halfWidth, bands) {
      uniforms.uStart.value.copy(from);
      uniforms.uEnd.value.copy(to);
      uniforms.uHalfWidth.value = halfWidth;
      uniforms.uLength.value = from.distanceTo(to);
      const shown = bands.slice(0, MAX_BANDS);
      uniforms.uCount.value = shown.length;
      shown.forEach((b, i) => {
        uniforms.uColours.value[i]!.setRGB(...b.colour);
        uniforms.uK.value[i] = (2 * Math.PI) / b.wavelength;
        uniforms.uIntensity.value[i] = Math.min(1, Math.max(0, b.intensity));
      });
    },
    tick(phase) {
      uniforms.uTime.value = phase;
    },
    dispose() {
      geometry.dispose();
      material.dispose();
    },
  };
}
