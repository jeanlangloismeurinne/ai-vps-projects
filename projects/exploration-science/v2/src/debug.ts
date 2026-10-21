import type { WebGLRenderer } from "three";

// Read by scripts/v2/capture.ts: the page is ready to be captured once the models are in
// the scene, the camera has reached its pose and a few frames have been drawn.
export interface XsDebug {
  ready: boolean;
  renderInfo: () => { calls: number; triangles: number; geometries: number; textures: number };
  /** Selected main object (its card is open), or null. */
  selected: string | null;
  select: (id: string | null) => void;
  /** Share of each main object's projected area under the open card (0 without card). */
  overlap: () => Record<string, number>;
  /** A screen point (CSS px) where the first object hit is `id`, to click it for real. */
  pickPoint: (id: string) => { x: number; y: number } | null;
  /** Current view: its shot, how deep in the navigation stack, the user's orbit and zoom. */
  nav: { shot: string; depth: number; view: { orbitDeg: number; elevationDeg: number; zoom: number } };
  enter: (id: string) => void;
  back: () => void;
  /** Camera pose as last drawn. */
  pose: () => { position: number[]; target: number[]; azimuthDeg: number; elevationDeg: number; distance: number; offset: number[] } | null;
  /** With `?step`: draws one more frame. */
  advance: () => void;
}

declare global {
  interface Window {
    __xs?: XsDebug;
  }
}

export const debug: XsDebug = {
  ready: false,
  renderInfo: () => ({ calls: 0, triangles: 0, geometries: 0, textures: 0 }),
  selected: null,
  select: () => {},
  overlap: () => ({}),
  pickPoint: () => null,
  nav: { shot: "global", depth: 1, view: { orbitDeg: 0, elevationDeg: 0, zoom: 1 } },
  enter: () => {},
  back: () => {},
  pose: () => null,
  advance: () => {},
};
window.__xs = debug;

export function exposeRenderer(gl: WebGLRenderer): void {
  debug.renderInfo = () => ({
    calls: gl.info.render.calls,
    triangles: gl.info.render.triangles,
    geometries: gl.info.memory.geometries,
    textures: gl.info.memory.textures,
  });
}
