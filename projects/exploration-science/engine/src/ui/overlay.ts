import type { Level, TextEntry } from "../content/types";
import { renderEntry } from "./richText";
import { LEVELS } from "./texts";

// DOM overlay above the canvas: question, level, node picker, Play bar,
// subtitles, labels pinned on entities and the selection card. It only
// displays; main.ts decides what happens.

export interface OverlayHandlers {
  onHome(): void;
  onNode(id: string): void;
  onLevel(level: Level): void;
  onPlayPause(): void;
  onPrevious(): void;
  onNext(): void;
  onStop(): void;
  onCloseCard(): void;
}

export interface PlayerView {
  state: "idle" | "playing" | "paused";
  /** The arrival tour: shown as "skip" rather than full controls. */
  intro: boolean;
  index: number;
  count: number;
}

export interface CardView {
  title: string;
  description: TextEntry | undefined;
  /** Child node the entity leads to, if any. */
  dive?: { available: boolean };
}

const CSS = `
.xs-overlay { position: absolute; inset: 0; pointer-events: none; font: 15px/1.45 system-ui, -apple-system, sans-serif; color: #10151c; }
.xs-overlay button, .xs-overlay select { font: inherit; color: inherit; }
.xs-panel { pointer-events: auto; background: rgba(255,255,255,.88); border-radius: 14px; box-shadow: 0 2px 10px rgba(0,0,0,.18); }
.xs-title { position: absolute; top: 12px; left: 16px; max-width: calc(100% - 330px); margin: 0; padding: 6px 14px; font-size: 17px; font-weight: 600; }
.xs-notice { position: absolute; top: 60px; left: 16px; max-width: 340px; padding: 8px 12px; border-radius: 8px; background: rgba(16,21,28,.75); color: #fff; font-size: 12px; }
.xs-notice:empty { display: none; }
.xs-top-right { position: absolute; top: 12px; right: 16px; display: flex; flex-direction: column; align-items: flex-end; gap: 8px; }
.xs-node { pointer-events: auto; min-height: 36px; border-radius: 8px; }
.xs-levels { display: flex; padding: 3px; gap: 2px; }
.xs-levels button { min-height: 36px; padding: 0 12px; border: 0; border-radius: 11px; background: transparent; cursor: pointer; }
.xs-levels button[aria-pressed="true"] { background: #10151c; color: #fff; }
.xs-home { position: absolute; left: 16px; bottom: 16px; min-width: 44px; min-height: 44px; padding: 0 16px; border: 0; font-weight: 600; cursor: pointer; }
.xs-bar { position: absolute; left: 50%; bottom: 16px; transform: translateX(-50%); display: flex; align-items: center; gap: 4px; padding: 4px; }
.xs-bar button { min-width: 44px; min-height: 44px; border: 0; border-radius: 10px; background: transparent; cursor: pointer; font-size: 17px; }
.xs-bar button:hover { background: rgba(0,0,0,.07); }
.xs-bar .xs-play { min-width: 96px; font-weight: 600; font-size: 15px; }
.xs-dots { display: flex; gap: 5px; padding: 0 8px; }
.xs-dots span { width: 8px; height: 8px; border-radius: 50%; background: rgba(0,0,0,.2); }
.xs-dots span.on { background: #10151c; }
.xs-subtitle { position: absolute; left: 50%; bottom: 76px; transform: translateX(-50%); width: min(780px, calc(100% - 32px)); max-height: 45%; overflow: auto; padding: 12px 18px; font-size: 17px; }
.xs-subtitle:empty { display: none; }
.xs-text { margin: 0; }
.xs-terms { display: grid; grid-template-columns: auto 1fr; gap: 2px 10px; margin: 10px 0 0; padding-top: 8px; border-top: 1px solid rgba(0,0,0,.12); font-size: 13px; }
.xs-terms dt { text-align: right; } .xs-terms dd { margin: 0; color: #3a4350; }
.xs-term { text-decoration: underline dotted 2px; text-underline-offset: 3px; text-decoration-color: #d18a00; }
.xs-labels { position: absolute; inset: 0; overflow: hidden; }
.xs-label { position: absolute; left: 0; top: 0; transform: translate(-50%, calc(-100% - 10px)); padding: 3px 10px; border-radius: 12px; background: #10151c; color: #fff; font-size: 13px; font-weight: 600; white-space: nowrap; }
.xs-label::after { content: ""; position: absolute; left: 50%; top: 100%; width: 2px; height: var(--leader, 10px); margin-left: -1px; background: #10151c; }
.xs-card { position: absolute; right: 16px; top: 50%; transform: translateY(-50%); width: min(320px, calc(100% - 32px)); padding: 14px 16px; }
.xs-card h2 { margin: 0 32px 6px 0; font-size: 17px; }
.xs-card .xs-close { position: absolute; top: 6px; right: 6px; width: 36px; height: 36px; border: 0; border-radius: 50%; background: transparent; cursor: pointer; font-size: 18px; }
.xs-card .xs-dive { margin-top: 10px; min-height: 40px; padding: 0 14px; border: 0; border-radius: 10px; background: #10151c; color: #fff; font-weight: 600; }
.xs-card .xs-dive:disabled { background: rgba(0,0,0,.12); color: #5a6370; }
[hidden] { display: none !important; }
@media (max-width: 640px) {
  .xs-title { max-width: calc(100% - 32px); font-size: 15px; }
  .xs-top-right { top: 64px; }
  .xs-subtitle { font-size: 15px; bottom: 72px; }
  .xs-card { top: auto; bottom: 76px; transform: none; }
}
`;

const LABEL_HEIGHT = 28; // px, a label and its gap

function el<K extends keyof HTMLElementTagNameMap>(tag: K, props: Record<string, unknown> = {}): HTMLElementTagNameMap[K] {
  return Object.assign(document.createElement(tag), props);
}

export class Overlay {
  private readonly title = el("h1", { className: "xs-title xs-panel" });
  private readonly picker = el("select", { className: "xs-node", ariaLabel: "Nœud" });
  private readonly levelButtons = new Map<Level, HTMLButtonElement>();
  private readonly notice = el("div", { className: "xs-notice" });
  private readonly bar = el("div", { className: "xs-bar xs-panel" });
  private readonly previous = el("button", { type: "button", textContent: "⏮", title: "Étape précédente", ariaLabel: "Étape précédente" });
  private readonly play = el("button", { type: "button", className: "xs-play" });
  private readonly next = el("button", { type: "button", textContent: "⏭", title: "Étape suivante", ariaLabel: "Étape suivante" });
  private readonly dots = el("div", { className: "xs-dots" });
  private readonly stop = el("button", { type: "button", textContent: "✕", title: "Quitter la visite", ariaLabel: "Quitter la visite" });
  private readonly subtitle = el("div", { className: "xs-subtitle xs-panel", ariaLive: "polite" });
  private readonly labelLayer = el("div", { className: "xs-labels" });
  private readonly labels = new Map<string, HTMLDivElement>();
  private readonly card = el("aside", { className: "xs-card xs-panel", hidden: true });

  constructor(container: HTMLElement, nodeIds: string[], handlers: OverlayHandlers) {
    document.head.appendChild(el("style", { textContent: CSS }));
    const root = el("div", { className: "xs-overlay" });

    const home = el("button", { className: "xs-home xs-panel", type: "button", textContent: "↺ Retour" });
    home.addEventListener("click", () => handlers.onHome());
    for (const id of nodeIds) this.picker.add(new Option(id, id));
    this.picker.addEventListener("change", () => handlers.onNode(this.picker.value));

    const levels = el("div", { className: "xs-levels xs-panel", role: "group", ariaLabel: "Niveau d'explication" });
    for (const level of LEVELS) {
      const button = el("button", { type: "button", textContent: level.name });
      button.addEventListener("click", () => handlers.onLevel(level.id));
      this.levelButtons.set(level.id, button);
      levels.append(button);
    }
    const topRight = el("div", { className: "xs-top-right" });
    topRight.append(this.picker, levels);

    this.previous.addEventListener("click", () => handlers.onPrevious());
    this.play.addEventListener("click", () => handlers.onPlayPause());
    this.next.addEventListener("click", () => handlers.onNext());
    this.stop.addEventListener("click", () => handlers.onStop());
    this.bar.append(this.previous, this.play, this.next, this.dots, this.stop);

    const close = el("button", { type: "button", className: "xs-close", textContent: "✕", ariaLabel: "Fermer" });
    close.addEventListener("click", () => handlers.onCloseCard());
    this.card.append(close);

    root.append(this.labelLayer, this.title, this.notice, topRight, this.subtitle, this.card, home, this.bar);
    container.appendChild(root);
  }

  show(nodeId: string, question: string, notices: string[]): void {
    this.title.textContent = question;
    this.picker.value = nodeId;
    this.notice.replaceChildren(...notices.map((n) => el("div", { textContent: n })));
  }

  setLevel(level: Level): void {
    for (const [id, button] of this.levelButtons) button.ariaPressed = String(id === level);
  }

  setPlayer(view: PlayerView): void {
    const touring = view.state !== "idle";
    const full = touring && !view.intro;
    this.previous.hidden = this.next.hidden = this.dots.hidden = !full;
    this.stop.hidden = !touring;
    this.play.textContent = view.intro && touring ? "Passer ⏭" : view.state === "playing" ? "❚❚ Pause" : touring ? "▶ Reprendre" : "▶ Visite";
    this.dots.replaceChildren(...Array.from({ length: full ? view.count : 0 }, (_, i) => el("span", { className: i <= view.index ? "on" : "" })));
  }

  setSubtitle(entry: TextEntry | undefined): void {
    this.subtitle.replaceChildren(...(entry === undefined ? [] : [renderEntry(entry)]));
  }

  /** Labels to pin, by entity id. */
  setLabels(labels: { id: string; text: string }[]): void {
    const wanted = new Set(labels.map((l) => l.id));
    for (const [id, div] of this.labels) {
      if (!wanted.has(id)) {
        div.remove();
        this.labels.delete(id);
      }
    }
    for (const { id, text } of labels) {
      let div = this.labels.get(id);
      if (!div) {
        div = el("div", { className: "xs-label" });
        this.labels.set(id, div);
        this.labelLayer.append(div);
      }
      div.textContent = text;
    }
  }

  /**
   * Moves the labels; call once per frame. A label that would cover another one
   * climbs above it, with a longer leader line.
   */
  placeLabels(position: (id: string) => { x: number; y: number } | null, hidden = false): void {
    const placed: { x: number; y: number; w: number }[] = [];
    const entries = [...this.labels].map(([id, div]) => ({ div, p: hidden ? null : position(id) }));
    entries.sort((a, b) => (b.p?.y ?? 0) - (a.p?.y ?? 0));
    for (const { div, p } of entries) {
      div.hidden = p === null;
      if (!p) continue;
      const w = div.offsetWidth;
      let lift = 0;
      for (const other of placed) {
        if (Math.abs(other.x - p.x) < (w + other.w) / 2 + 4 && Math.abs(other.y - (p.y - lift)) < LABEL_HEIGHT) lift = p.y - other.y + LABEL_HEIGHT;
      }
      placed.push({ x: p.x, y: p.y - lift, w });
      div.style.translate = `${p.x}px ${p.y - lift}px`;
      div.style.setProperty("--leader", `${10 + lift}px`);
    }
  }

  showCard(view: CardView | null): void {
    this.card.hidden = view === null;
    const close = this.card.firstElementChild!;
    this.card.replaceChildren(close);
    if (!view) return;
    this.card.append(el("h2", { textContent: view.title }), renderEntry(view.description));
    if (view.dive) {
      // Diving into child nodes arrives with milestone 4.
      this.card.append(el("button", { type: "button", className: "xs-dive", disabled: true, textContent: view.dive.available ? "Plonger à l'intérieur" : "Plonger à l'intérieur (à venir)" }));
    }
  }
}
