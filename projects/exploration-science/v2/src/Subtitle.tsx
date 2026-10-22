import { useLayoutEffect, useRef } from "react";
import type { Rect } from "./camera";
import { texts } from "./content/data";

const GAP = 16;

interface SubtitleProps {
  text: string;
  index: number;
  count: number;
  /** Seconds the step lasts (drives the progress bar of the current step), null when paused. */
  duration: number | null;
  onSkip: () => void;
  onFree: (free: Rect) => void;
}

/** Subtitle of the guided tour, at the bottom of the screen, with the steps as dots and a
 * way out. Reports the part of the screen it leaves free (above it) for the camera. */
export function Subtitle({ text, index, count, duration, onSkip, onFree }: SubtitleProps) {
  const ref = useRef<HTMLElement>(null);
  useLayoutEffect(() => {
    const el = ref.current!;
    const report = () => onFree({ x: 0, y: 0, width: window.innerWidth, height: Math.max(el.getBoundingClientRect().top - GAP, 1) });
    report();
    const ro = new ResizeObserver(report);
    ro.observe(el);
    window.addEventListener("resize", report);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", report);
    };
  }, [onFree]);

  return (
    <section ref={ref} className="tour" aria-live="polite">
      <p key={index} className="tour__text">
        {text}
      </p>
      <footer className="tour__bar">
        <ol className="tour__steps" aria-hidden="true">
          {Array.from({ length: count }, (_, i) => (
            <li key={i} className={i < index ? "done" : i === index ? "now" : ""}>
              {i === index && duration !== null && <span key={index} style={{ animationDuration: `${duration}s` }} />}
            </li>
          ))}
        </ol>
        <button type="button" className="tour__skip" onClick={onSkip}>
          {texts.entries["ui.tour-skip"]}
        </button>
      </footer>
    </section>
  );
}

/** Button that starts the tour again once the user has the hand. */
export function TourButton({ onPlay }: { onPlay: () => void }) {
  return (
    <button type="button" className="tour-replay" onClick={onPlay}>
      <svg viewBox="0 0 16 16" aria-hidden="true">
        <path d="M5 3.5v9l7.5-4.5z" />
      </svg>
      {texts.entries["ui.tour-replay"]}
    </button>
  );
}
