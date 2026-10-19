import type { WebGLRenderer } from "three";

// Read by scripts/v2/capture.ts: the page is ready to be captured once the models are
// in the scene and a few frames have been drawn.
export interface XsDebug {
  ready: boolean;
  renderInfo: () => { calls: number; triangles: number; geometries: number; textures: number };
}

declare global {
  interface Window {
    __xs?: XsDebug;
  }
}

export function exposeDebug(gl: WebGLRenderer): void {
  let frames = 0;
  const debug: XsDebug = {
    ready: false,
    renderInfo: () => ({
      calls: gl.info.render.calls,
      triangles: gl.info.render.triangles,
      geometries: gl.info.memory.geometries,
      textures: gl.info.memory.textures,
    }),
  };
  window.__xs = debug;
  const tick = () => {
    if (++frames >= 5) debug.ready = true;
    else requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}
