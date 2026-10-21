import { useLayoutEffect, useRef } from "react";
import { cardSources, texts, type Card as CardText } from "./content/data";
import type { Rect } from "./camera";

export type Dock = "right" | "bottom";

/** Wide screens dock the card on the right, tall ones at the bottom. */
export const dockFor = (width: number, height: number): Dock => (width >= height * 1.05 ? "right" : "bottom");

const GAP = 16;

/** The card of a main object, docked beside the scene. Reports the part of the screen it
 * leaves free, so that the camera frames the scene there instead of under the card. */
export function Card({ id, dock, onClose, onFree }: { id: string; dock: Dock; onClose: () => void; onFree: (free: Rect) => void }) {
  const ref = useRef<HTMLElement>(null);
  const card = (texts.cards as Record<string, CardText>)[id]!;
  const { publishers, computed } = cardSources(card);

  useLayoutEffect(() => {
    const el = ref.current!;
    const report = () => {
      const r = el.getBoundingClientRect();
      const [W, H] = [window.innerWidth, window.innerHeight];
      onFree(dock === "right" ? { x: 0, y: 0, width: Math.max(r.left - GAP, 1), height: H } : { x: 0, y: 0, width: W, height: Math.max(r.top - GAP, 1) });
    };
    report();
    const ro = new ResizeObserver(report);
    ro.observe(el);
    window.addEventListener("resize", report);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", report);
    };
  }, [id, dock, onFree]);

  useLayoutEffect(() => {
    const key = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose]);

  return (
    <aside ref={ref} className={`card card--${dock}`} role="dialog" aria-labelledby="card-title" data-object={id}>
      <header>
        <span className="card__mark" aria-hidden="true" />
        <h2 id="card-title">{card.title}</h2>
        <button type="button" className="card__close" aria-label={texts.entries["ui.close"]} onClick={onClose}>
          <svg viewBox="0 0 16 16" aria-hidden="true">
            <path d="M4 4l8 8M12 4l-8 8" />
          </svg>
        </button>
      </header>
      <p className="card__summary">{card.summary}</p>
      <dl className="card__figures">
        {card.figures.map((f) => (
          <div key={f.factId}>
            <dt>{f.label}</dt>
            <dd>{f.value}</dd>
          </div>
        ))}
      </dl>
      <footer className="card__sources">
        {texts.entries["ui.sources"]} : {publishers.join(", ")}
        {computed && <> · {texts.entries["ui.computed"]}</>}
      </footer>
    </aside>
  );
}
