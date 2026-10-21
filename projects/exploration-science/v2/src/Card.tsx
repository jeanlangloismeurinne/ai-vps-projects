import { useLayoutEffect, useRef } from "react";
import { cardSources, texts, type Card as CardText } from "./content/data";
import type { Rect } from "./camera";

export type Dock = "right" | "bottom";

/** Wide screens dock the card on the right, tall ones at the bottom. */
export const dockFor = (width: number, height: number): Dock => (width >= height * 1.05 ? "right" : "bottom");

const GAP = 16;

interface CardProps {
  id: string;
  dock: Dock;
  /** Depth of the view in the navigation (1 = global view). */
  depth: number;
  /** Kind of the next closer view on this object, if render.json has one. */
  closer: "object" | "detail" | null;
  onCloser: () => void;
  /** Closes the card in the global view, goes back one view otherwise. */
  onBack: () => void;
  onFree: (id: string, free: Rect) => void;
}

/** The card of a main object, docked beside the scene. Reports the part of the screen it
 * leaves free, so that the camera frames the scene there instead of under the card. Its
 * buttons lead one view closer to the object, and back. */
export function Card({ id, dock, depth, closer, onCloser, onBack, onFree }: CardProps) {
  const ref = useRef<HTMLElement>(null);
  const card = (texts.cards as Record<string, CardText>)[id]!;
  const { publishers, computed } = cardSources(card);

  useLayoutEffect(() => {
    const el = ref.current!;
    const report = () => {
      const r = el.getBoundingClientRect();
      const [W, H] = [window.innerWidth, window.innerHeight];
      onFree(id, dock === "right" ? { x: 0, y: 0, width: Math.max(r.left - GAP, 1), height: H } : { x: 0, y: 0, width: W, height: Math.max(r.top - GAP, 1) });
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

  return (
    <aside ref={ref} className={`card card--${dock}`} role="dialog" aria-labelledby="card-title" data-object={id}>
      <header>
        <span className="card__mark" aria-hidden="true" />
        <h2 id="card-title">{card.title}</h2>
        {depth === 1 && (
          <button type="button" className="card__close" aria-label={texts.entries["ui.close"]} onClick={onBack}>
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="M4 4l8 8M12 4l-8 8" />
            </svg>
          </button>
        )}
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
      {(depth > 1 || closer) && (
        <nav className="card__actions">
          {depth > 1 && (
            <button type="button" className="card__back" onClick={onBack}>
              <svg viewBox="0 0 16 16" aria-hidden="true">
                <path d="M10 3.5L5.5 8l4.5 4.5" />
              </svg>
              {texts.entries["ui.back"]}
            </button>
          )}
          {closer && (
            <button type="button" className="card__closer" onClick={onCloser}>
              {texts.entries[closer === "detail" ? "ui.zoom-detail" : "ui.zoom-object"]}
              <svg viewBox="0 0 16 16" aria-hidden="true">
                <path d="M6 3.5L10.5 8 6 12.5" />
              </svg>
            </button>
          )}
        </nav>
      )}
      <footer className="card__sources">
        {texts.entries["ui.sources"]} : {publishers.join(", ")}
        {computed && <> · {texts.entries["ui.computed"]}</>}
      </footer>
    </aside>
  );
}
