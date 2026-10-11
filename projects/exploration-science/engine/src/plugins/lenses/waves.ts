import {
  Color,
  CylinderGeometry,
  DoubleSide,
  Group,
  Matrix4,
  Mesh,
  MeshBasicMaterial,
  PlaneGeometry,
  Quaternion,
  ShaderMaterial,
  Vector3,
} from "three";
import type { LensPlugin } from "../../core/registry";
import { WAVE_FIELD, type WaveField } from "../channels";

// Ondes lens: reveals the wave field of a line of sources on the real object.
// With a disc (a scatterer seen in a magnifier), it shows the wave arriving and
// the wave the source sends back all around it, in the colour of the light.
// The field is computed per pixel from the sources (superposition of cylindrical
// waves, amplitude ∝ 1/√r), never drawn: beams, nulls and grating lobes emerge
// from the sum. Also marks the main beam and the grating lobes the simulator
// predicts, so the two can be compared.

/** Field slice: at least this many wavelengths wide, and this many times the line of sources. */
const SLICE_MIN_WIDTH_L = 10;
const SLICE_WIDTH_PER_LINE = 5;
const SLICE_ASPECT = 0.7; // height / width
/** Visual frequency of the wave animation: the real 12 GHz is slowed ~10^10 times. */
const VISUAL_HZ = 0.8;
const MAX_SOURCES = 64;
const LOBE_COLOR = "#ff4d6d";
const CREST = "#ffd27a";
const TROUGH = "#3a7bd5";
/** In the colour of the light, troughs are the crest colour this much darker. */
const TROUGH_SHADE = 0.12;
const ROD_RADIUS = 0.003; // beam marker radius, as a fraction of the slice height

/**
 * Scattered wave around a single source driven by an incident plane wave, at
 * (u, v) in the slice plane: relative amplitude × √((1 + cos²Θ)/2), the Rayleigh
 * pattern for unpolarised light, Θ between the incident direction and the
 * direction from the source. Same formula as the disc branch of the shader.
 */
export function scatteredAt(f: Pick<WaveField, "amplitude">, incident: { u: number; v: number }, u: number, v: number): number {
  const r = Math.hypot(u, v);
  const cos = r === 0 ? 1 : (u * incident.u + v * incident.v) / r;
  return (f.amplitude ?? 1) * Math.sqrt((1 + cos * cos) / 2);
}

/** Complex amplitude Σ e^{-i(k r_n + n Δφ)} / √r_n at (u, v) in the slice plane (u along the line). */
export function fieldAt(f: Pick<WaveField, "wavelength" | "count" | "spacing" | "phaseStep">, u: number, v: number): { re: number; im: number } {
  const k = (2 * Math.PI) / f.wavelength;
  const rMin = f.wavelength / 8;
  let re = 0;
  let im = 0;
  for (let n = 0; n < f.count; n++) {
    const un = (n - (f.count - 1) / 2) * f.spacing;
    const r = Math.max(Math.hypot(u - un, v), rMin);
    const phase = -(k * r + n * f.phaseStep);
    const a = 1 / Math.sqrt(r);
    re += a * Math.cos(phase);
    im += a * Math.sin(phase);
  }
  return { re, im };
}

// Same sum as fieldAt, per fragment. Keep the two in step.
const FRAGMENT = /* glsl */ `
uniform float uWavelength;
uniform float uSpacing;
uniform int uCount;
uniform float uPhaseStep;
uniform float uTime;
uniform vec2 uSize;
uniform vec3 uCrest;
uniform vec3 uTrough;
uniform float uDisc;
uniform float uAmplitude;
uniform vec2 uIncident;
uniform float uIncidentAmp;
varying vec2 vPos;
const float TAU = 6.283185307;
void main() {
  float k = TAU / uWavelength;
  if (uDisc > 0.5) {
    // A single scatterer at the centre, driven by a plane wave travelling along uIncident.
    float R = 0.5 * uSize.x;
    float r = length(vPos);
    float inside = 1.0 - smoothstep(0.9 * R, R, r);
    float c = r > 1e-6 ? dot(vPos / r, uIncident) : 1.0;
    float scattered = uAmplitude * sqrt(0.5 * (1.0 + c * c)) * smoothstep(0.0, uWavelength * 0.25, r);
    float sWave = cos(uTime - k * r);
    float iWave = cos(uTime - k * dot(vPos, uIncident));
    float aS = clamp(0.9 * scattered, 0.0, 0.9);
    float aI = 0.3 * uIncidentAmp;
    vec3 cS = mix(uTrough, uCrest, 0.5 + 0.5 * sWave);
    vec3 cI = mix(uTrough, uCrest, 0.5 + 0.5 * iWave) * 0.7;
    float a = aS + aI * (1.0 - aS);
    vec3 col = (cS * aS + cI * aI * (1.0 - aS)) / max(a, 1e-4);
    gl_FragColor = vec4(col, a * inside);
    return;
  }
  float rMin = uWavelength / 8.0;
  float re = 0.0;
  float im = 0.0;
  for (int n = 0; n < ${MAX_SOURCES}; n++) {
    if (n >= uCount) break;
    float un = (float(n) - 0.5 * float(uCount - 1)) * uSpacing;
    float r = max(length(vec2(vPos.x - un, vPos.y)), rMin);
    float phase = -(k * r + float(n) * uPhaseStep);
    float a = inversesqrt(r);
    re += a * cos(phase);
    im += a * sin(phase);
  }
  float amp = sqrt(re * re + im * im);
  // Normalised so a full beam in the far field reads ~1 (≈ the array factor).
  float strength = amp * sqrt(max(length(vPos), uWavelength)) / float(uCount);
  // Instantaneous field Re(A e^{iωt}), divided by |A|: crests and troughs everywhere.
  float wave = (re * cos(uTime) - im * sin(uTime)) / max(amp, 1e-6);
  vec3 color = mix(uTrough, uCrest, 0.5 + 0.5 * wave);
  float edge = smoothstep(0.0, 0.08, min(min(vPos.x / uSize.x + 0.5, 0.5 - vPos.x / uSize.x), min(vPos.y / uSize.y, 1.0 - vPos.y / uSize.y)) * 2.0);
  float alpha = (0.12 + 0.8 * smoothstep(0.03, 0.45, strength)) * edge;
  gl_FragColor = vec4(color * (0.55 + 0.6 * clamp(strength, 0.0, 1.0)), alpha);
}`;

const VERTEX = /* glsl */ `
uniform vec2 uSize;
uniform float uCentre;
varying vec2 vPos;
void main() {
  // The geometry is a unit plane scaled by uSize: the field is computed in scene units.
  vPos = (position.xy - vec2(0.0, uCentre)) * uSize;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;

export const waves: LensPlugin = {
  id: "waves",
  create(ctx) {
    const group = new Group();
    group.name = "lens:waves";
    group.visible = false;
    group.matrixAutoUpdate = false;

    const uniforms = {
      uWavelength: { value: 1 },
      uSpacing: { value: 0.5 },
      uCount: { value: 1 },
      uPhaseStep: { value: 0 },
      uTime: { value: 0 },
      uSize: { value: [1, 1] as [number, number] },
      uCrest: { value: new Color(CREST) },
      uTrough: { value: new Color(TROUGH) },
      uDisc: { value: 0 },
      uCentre: { value: 0 },
      uAmplitude: { value: 1 },
      uIncident: { value: [1, 0] as [number, number] },
      uIncidentAmp: { value: 0 },
    };
    // Unit plane spanning u in [-0.5, 0.5], v in [0, 1]; scaled per frame to the wavelength.
    const planeGeometry = new PlaneGeometry(1, 1);
    planeGeometry.translate(0, 0.5, 0);
    const planeMaterial = new ShaderMaterial({ uniforms, vertexShader: VERTEX, fragmentShader: FRAGMENT, transparent: true, depthWrite: false, side: DoubleSide });
    const plane = new Mesh(planeGeometry, planeMaterial);
    plane.renderOrder = 10;
    group.add(plane);

    // Beam markers: a thin rod along each predicted beam.
    const rodGeometry = new CylinderGeometry(1, 1, 1, 8);
    rodGeometry.translate(0, 0.5, 0);
    const mainMaterial = new MeshBasicMaterial({ color: ctx.palette.accent, transparent: true, opacity: 0.95, depthWrite: false });
    const lobeMaterial = new MeshBasicMaterial({ color: LOBE_COLOR, transparent: true, opacity: 0.9, depthWrite: false });
    const rods: Mesh[] = [];
    const rod = (i: number) => {
      while (rods.length <= i) {
        const r = new Mesh(rodGeometry, mainMaterial);
        r.renderOrder = 11;
        rods.push(r);
        group.add(r);
      }
      return rods[i]!;
    };

    const basis = new Matrix4();
    const side = new Vector3();
    const up = new Vector3(0, 1, 0);
    const dir = new Vector3();
    const q = new Quaternion();
    let active = false;
    let phase = 0;

    const field = (): WaveField | undefined => {
      for (const source of ctx.sources) {
        const data = source.instance()?.channel?.(WAVE_FIELD) as WaveField | undefined;
        if (data) return data;
      }
      return undefined;
    };

    return {
      object: group,
      setActive(on) {
        active = on;
        group.visible = on;
      },
      update(dt) {
        if (!active) return;
        const f = field();
        if (!f) {
          group.visible = false;
          return;
        }
        group.visible = true;
        phase = (phase + dt * 2 * Math.PI * VISUAL_HZ) % (2 * Math.PI);
        const disc = f.discRadius !== undefined;
        const w = disc ? 2 * f.discRadius! : Math.max(SLICE_MIN_WIDTH_L * f.wavelength, SLICE_WIDTH_PER_LINE * f.count * f.spacing);
        const h = disc ? w : w * SLICE_ASPECT;
        uniforms.uDisc.value = disc ? 1 : 0;
        uniforms.uCentre.value = disc ? 0.5 : 0;
        uniforms.uAmplitude.value = f.amplitude ?? 1;
        if (f.colour) {
          uniforms.uCrest.value.setRGB(...f.colour);
          uniforms.uTrough.value.setRGB(...(f.colour.map((c) => c * TROUGH_SHADE) as [number, number, number]));
        } else {
          uniforms.uCrest.value.set(CREST);
          uniforms.uTrough.value.set(TROUGH);
        }
        uniforms.uWavelength.value = f.wavelength;
        uniforms.uSpacing.value = f.spacing;
        uniforms.uCount.value = Math.min(f.count, MAX_SOURCES);
        uniforms.uPhaseStep.value = f.phaseStep;
        uniforms.uTime.value = phase;
        uniforms.uSize.value = [w, h];
        // Slice plane: x along the line of sources, y along the normal.
        side.crossVectors(f.axis, f.normal).normalize();
        basis.makeBasis(f.axis, f.normal, side).setPosition(f.origin);
        group.matrix.copy(basis);
        group.matrixWorldNeedsUpdate = true;
        plane.scale.set(w, h, 1);
        plane.position.set(0, disc ? -h / 2 : 0, 0);
        // The incident wave, in slice coordinates (x along the axis, y along the normal).
        if (f.incident) {
          uniforms.uIncident.value = [f.incident.direction.dot(f.axis), f.incident.direction.dot(f.normal)];
          const n = Math.hypot(...uniforms.uIncident.value) || 1;
          uniforms.uIncident.value = [uniforms.uIncident.value[0] / n, uniforms.uIncident.value[1] / n];
          uniforms.uIncidentAmp.value = f.incident.amplitude;
        } else uniforms.uIncidentAmp.value = 0;

        const beams = [
          ...(f.steeringDeg === null ? [] : [{ deg: f.steeringDeg, main: true }]),
          ...f.gratingLobesDeg.map((deg) => ({ deg, main: false })),
        ];
        const radius = h * ROD_RADIUS;
        beams.forEach((b, i) => {
          const r = rod(i);
          r.visible = true;
          r.material = b.main ? mainMaterial : lobeMaterial;
          const a = (b.deg * Math.PI) / 180;
          dir.set(Math.sin(a), Math.cos(a), 0);
          r.quaternion.copy(q.setFromUnitVectors(up, dir));
          r.scale.set(radius, h * 0.95, radius);
        });
        for (let i = beams.length; i < rods.length; i++) rods[i]!.visible = false;
      },
      dispose() {
        planeGeometry.dispose();
        planeMaterial.dispose();
        rodGeometry.dispose();
        mainMaterial.dispose();
        lobeMaterial.dispose();
      },
    };
  },
};
