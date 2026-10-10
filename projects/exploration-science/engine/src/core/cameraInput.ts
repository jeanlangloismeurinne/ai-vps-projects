import type { CameraRig } from "./camera";

// Mouse, trackpad and touch (iPad) gestures mapped onto the constrained rig:
// one pointer drags the orbit, two pointers pinch to zoom, the wheel zooms.

const ORBIT_RAD_PER_PX = 0.006;
const WHEEL_ZOOM_PER_PX = 0.0015;

const TAP_MAX_PX = 6;
const TAP_MAX_MS = 500;

export interface InputHandlers {
  /** The user starts moving the camera (drag, pinch or wheel). */
  onGesture?(): void;
  /** A short press without movement, in client coordinates. */
  onTap?(clientX: number, clientY: number): void;
}

export function attachCameraInput(element: HTMLElement, rig: CameraRig, handlers: InputHandlers = {}): () => void {
  const pointers = new Map<number, { x: number; y: number }>();
  let tap: { id: number; x: number; y: number; time: number; moved: boolean } | null = null;
  let lastMove = 0;
  let pinchDistance = 0;

  const spread = () => {
    const [a, b] = [...pointers.values()];
    return a && b ? Math.hypot(a.x - b.x, a.y - b.y) : 0;
  };

  const onDown = (e: PointerEvent) => {
    element.setPointerCapture(e.pointerId);
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    lastMove = e.timeStamp;
    rig.setDragging(true);
    tap = pointers.size === 1 ? { id: e.pointerId, x: e.clientX, y: e.clientY, time: e.timeStamp, moved: false } : null;
    if (pointers.size === 2) {
      pinchDistance = spread();
      handlers.onGesture?.();
    }
  };

  const onMove = (e: PointerEvent) => {
    const previous = pointers.get(e.pointerId);
    if (!previous) return;
    const dx = e.clientX - previous.x;
    const dy = e.clientY - previous.y;
    previous.x = e.clientX;
    previous.y = e.clientY;
    if (tap && !tap.moved) {
      if (Math.hypot(e.clientX - tap.x, e.clientY - tap.y) <= TAP_MAX_PX) return;
      tap.moved = true;
      handlers.onGesture?.();
    }
    if (pointers.size === 1) {
      const dt = (e.timeStamp - lastMove) / 1000;
      lastMove = e.timeStamp;
      // Dragging right turns the scene right, so the camera goes left.
      rig.orbitBy(-dx * ORBIT_RAD_PER_PX, dy * ORBIT_RAD_PER_PX, dt);
    } else if (pointers.size === 2) {
      const d = spread();
      if (pinchDistance > 0 && d > 0) rig.zoomBy(pinchDistance / d);
      pinchDistance = d;
    }
  };

  const onUp = (e: PointerEvent) => {
    if (tap && tap.id === e.pointerId && !tap.moved && e.type === "pointerup" && e.timeStamp - tap.time <= TAP_MAX_MS) handlers.onTap?.(e.clientX, e.clientY);
    tap = null;
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinchDistance = 0;
    if (pointers.size === 0) rig.setDragging(false);
    lastMove = e.timeStamp;
  };

  const onWheel = (e: WheelEvent) => {
    e.preventDefault();
    handlers.onGesture?.();
    const px = e.deltaMode === WheelEvent.DOM_DELTA_LINE ? e.deltaY * 16 : e.deltaY;
    rig.zoomBy(Math.exp(px * WHEEL_ZOOM_PER_PX));
  };

  // Safari on iPad fires its own gesture events for pinch; the pointer path handles it.
  const preventGesture = (e: Event) => e.preventDefault();

  element.style.touchAction = "none";
  element.addEventListener("pointerdown", onDown);
  element.addEventListener("pointermove", onMove);
  element.addEventListener("pointerup", onUp);
  element.addEventListener("pointercancel", onUp);
  element.addEventListener("wheel", onWheel, { passive: false });
  element.addEventListener("gesturestart", preventGesture);

  return () => {
    element.removeEventListener("pointerdown", onDown);
    element.removeEventListener("pointermove", onMove);
    element.removeEventListener("pointerup", onUp);
    element.removeEventListener("pointercancel", onUp);
    element.removeEventListener("wheel", onWheel);
    element.removeEventListener("gesturestart", preventGesture);
  };
}
