import type { Level, TextEntry } from "../content/types";
import { renderEntry, type TermOptions } from "./richText";
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
  /** A pinned label was clicked. */
  onLabel(id: string): void;
  onLens(id: string, on: boolean): void;
  onControl(id: string, value: number): void;
  /** Breadcrumb: back up to an ancestor node. */
  onAscend(nodeId: string): void;
  /** Selection card: dive into the child node. */
  onDive(): void;
  /** An explorable term was touched (spec, Termes explorables). */
  onTerm(nodeId: string): void;
  /** Term card: open the node now. */
  onExplore(): void;
  /** Term card: keep it in the "À explorer" list. */
  onLater(): void;
  onCloseTerm(): void;
  /** Back to the node (and Play step) the exploration started from. */
  onReturn(): void;
  /** "À explorer" list: open one of the saved nodes. */
  onExploreSaved(nodeId: string): void;
  onCloseSaved(): void;
}

export interface TermCardView {
  /** The target node's question. */
  title: string;
  /** Its one-sentence definition, at the current level (node.summaryKey). */
  summary: TextEntry | undefined;
  saved: boolean;
}

export interface LensView {
  id: string;
  label: string;
  on: boolean;
}

export interface ControlView {
  id: string;
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  /** Catalogue unit ("deg", "1"…) used to format the value. */
  unit?: string;
}

export interface CrumbView {
  nodeId: string;
  label: string;
  /** Unit the level is named after (m, cm, mm). */
  unit: string;
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
/* Left column: its panels stack, whatever the height of the question. */
.xs-left { position: absolute; top: 12px; left: 16px; right: 370px; display: flex; flex-direction: column; align-items: flex-start; gap: 8px; }
.xs-title { max-width: 100%; box-sizing: border-box; margin: 0; padding: 6px 14px; font-size: 17px; font-weight: 600; }
.xs-notice { max-width: 340px; padding: 8px 12px; border-radius: 8px; background: rgba(16,21,28,.75); color: #fff; font-size: 12px; }
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
button.xs-term { pointer-events: auto; display: inline; margin: 0; padding: 0 1px; border: 0; border-radius: 3px; background: rgba(209,138,0,.12); font: inherit; color: inherit; cursor: pointer; text-decoration: underline solid 2px; text-decoration-color: #d18a00; text-underline-offset: 3px; }
button.xs-term:hover, button.xs-term:focus-visible { background: rgba(209,138,0,.28); }
.xs-term-card .xs-actions, .xs-saved .xs-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.xs-term-card .xs-actions button, .xs-saved li button { min-height: 40px; padding: 0 14px; border: 0; border-radius: 10px; font-weight: 600; cursor: pointer; background: rgba(0,0,0,.08); }
.xs-term-card .xs-actions .xs-primary, .xs-saved li .xs-primary { background: #b87400; color: #fff; }
.xs-term-card .xs-kicker, .xs-saved .xs-kicker { margin: 0 32px 4px 0; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: #b87400; }
.xs-return { pointer-events: auto; min-height: 40px; padding: 0 16px; border: 0; font-weight: 600; cursor: pointer; color: #fff; background: #b87400; }
.xs-saved { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: min(420px, calc(100% - 32px)); padding: 14px 16px; }
.xs-saved h2 { margin: 0 32px 8px 0; font-size: 17px; }
.xs-saved ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; }
.xs-saved li { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.xs-saved .xs-close, .xs-term-card .xs-close { position: absolute; top: 6px; right: 6px; width: 36px; height: 36px; border: 0; border-radius: 50%; background: transparent; cursor: pointer; font-size: 18px; }
.xs-labels { position: absolute; inset: 0; overflow: hidden; }
.xs-label { pointer-events: auto; cursor: pointer; position: absolute; left: 0; top: 0; transform: translate(-50%, calc(-100% - 10px)); padding: 3px 10px; border-radius: 12px; background: #10151c; color: #fff; font-size: 13px; font-weight: 600; white-space: nowrap; }
.xs-label::after { content: ""; position: absolute; left: 50%; top: 100%; width: 2px; height: var(--leader, 10px); margin-left: -1px; background: #10151c; }
.xs-card { position: absolute; right: 16px; top: 50%; transform: translateY(-50%); width: min(320px, calc(100% - 32px)); padding: 14px 16px; }
.xs-card h2 { margin: 0 32px 6px 0; font-size: 17px; }
.xs-card .xs-close { position: absolute; top: 6px; right: 6px; width: 36px; height: 36px; border: 0; border-radius: 50%; background: transparent; cursor: pointer; font-size: 18px; }
.xs-card .xs-dive { margin-top: 10px; min-height: 40px; padding: 0 14px; border: 0; border-radius: 10px; background: #10151c; color: #fff; font-weight: 600; }
.xs-card .xs-dive:disabled { background: rgba(0,0,0,.12); color: #5a6370; }
.xs-card .xs-dive:not(:disabled) { cursor: pointer; background: #b87400; }
.xs-lenses { display: flex; gap: 6px; }
.xs-lenses button { pointer-events: auto; min-height: 40px; padding: 0 14px; border: 0; border-radius: 20px; font-weight: 600; cursor: pointer; background: rgba(255,255,255,.88); box-shadow: 0 2px 10px rgba(0,0,0,.18); }
.xs-lenses button[aria-pressed="true"] { background: #3a7bd5; color: #fff; }
.xs-controls { width: 260px; box-sizing: border-box; max-height: 50vh; overflow: auto; padding: 12px 14px; display: flex; flex-direction: column; gap: 12px; }
.xs-control label { display: flex; justify-content: space-between; gap: 8px; font-size: 13px; font-weight: 600; }
.xs-control output { font-variant-numeric: tabular-nums; font-weight: 500; color: #3a4350; }
.xs-control input { width: 100%; min-height: 32px; accent-color: #3a7bd5; }
.xs-where { display: flex; flex-direction: column; align-items: flex-start; gap: 6px; }
.xs-crumbs { display: flex; flex-wrap: wrap; align-items: center; gap: 2px; padding: 3px 6px; font-size: 13px; }
.xs-crumbs button { min-height: 32px; padding: 0 8px; border: 0; border-radius: 8px; background: transparent; cursor: pointer; font-weight: 600; color: #b87400; }
.xs-crumbs span.here { padding: 0 8px; font-weight: 600; }
.xs-crumbs small { margin-left: 4px; font-weight: 500; color: #5a6370; }
.xs-crumbs .sep { color: #8a93a0; }
.xs-scale { display: flex; flex-direction: column; gap: 2px; padding: 5px 10px 6px; font-size: 12px; font-weight: 600; }
.xs-scale i { display: block; height: 6px; border: 2px solid #10151c; border-top: 0; }
.xs-scale.magnified i { border-color: var(--xs-accent, #4da3ff); }
.xs-fade { position: absolute; inset: 0; pointer-events: none; opacity: 0; transition: opacity .3s ease; background: #0d1218; }
.xs-fade.on { opacity: 1; }
@media (prefers-reduced-motion: reduce) { .xs-fade { transition: none; } }
[hidden] { display: none !important; }
/* Phones: the panels flow in one column (their heights vary with the text), the Play bar and Retour stay pinned below. */
@media (max-width: 640px) {
  .xs-overlay { display: flex; flex-direction: column; gap: 8px; padding: 12px 12px 72px; box-sizing: border-box; }
  .xs-left { display: contents; }
  .xs-title { order: 1; font-size: 15px; }
  .xs-top-right { position: static; order: 2; flex-direction: row; flex-wrap: wrap; align-items: center; justify-content: space-between; }
  .xs-node { max-width: 45%; }
  .xs-levels button { padding: 0 9px; }
  .xs-where { order: 3; flex-direction: row; flex-wrap: wrap; align-items: center; }
  .xs-crumbs { font-size: 12px; }
  .xs-notice { order: 4; }
  .xs-controls { order: 5; width: auto; align-self: stretch; max-height: 26vh; overflow: auto; gap: 6px; padding: 8px 12px; }
  .xs-subtitle { position: static; order: 6; margin-top: auto; transform: none; width: auto; max-height: 34vh; font-size: 15px; }
  .xs-card { top: auto; bottom: 72px; transform: none; }
  .xs-overlay:has(.xs-card:not([hidden])) .xs-subtitle { display: none; }
  .xs-home { left: 12px; bottom: 12px; }
  .xs-bar { left: auto; right: 12px; bottom: 12px; transform: none; }
  .xs-dots { display: none; }
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
  private readonly lensBar = el("div", { className: "xs-lenses" });
  private readonly controls = el("div", { className: "xs-controls xs-panel", hidden: true });
  private readonly controlInputs = new Map<string, { input: HTMLInputElement; output: HTMLOutputElement; unit?: string }>();
  private readonly crumbs = el("nav", { className: "xs-crumbs xs-panel", ariaLabel: "Niveaux de zoom" });
  private readonly scale = el("div", { className: "xs-scale xs-panel", ariaHidden: "true" });
  private readonly scaleLabel = el("span");
  private readonly scaleRule = el("i");
  private readonly fade = el("div", { className: "xs-fade" });
  private readonly termCard = el("aside", { className: "xs-card xs-term-card xs-panel", hidden: true, ariaLive: "polite" });
  private readonly returnButton = el("button", { type: "button", className: "xs-return xs-panel", hidden: true });
  private readonly saved = el("section", { className: "xs-saved xs-panel", hidden: true, ariaLabel: "À explorer" });
  private terms: TermOptions | undefined;

  constructor(container: HTMLElement, nodeIds: string[], private readonly handlers: OverlayHandlers) {
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
    topRight.append(this.picker, levels, this.lensBar);
    this.scale.append(this.scaleLabel, this.scaleRule);
    const where = el("div", { className: "xs-where" });
    where.append(this.returnButton, this.crumbs, this.scale);

    this.previous.addEventListener("click", () => handlers.onPrevious());
    this.play.addEventListener("click", () => handlers.onPlayPause());
    this.next.addEventListener("click", () => handlers.onNext());
    this.stop.addEventListener("click", () => handlers.onStop());
    this.bar.append(this.previous, this.play, this.next, this.dots, this.stop);

    const close = el("button", { type: "button", className: "xs-close", textContent: "✕", ariaLabel: "Fermer" });
    close.addEventListener("click", () => handlers.onCloseCard());
    this.card.append(close);

    this.returnButton.addEventListener("click", () => handlers.onReturn());

    const left = el("div", { className: "xs-left" });
    left.append(this.title, where, this.notice, this.controls);
    root.append(this.labelLayer, left, topRight, this.subtitle, this.card, this.termCard, this.saved, home, this.bar, this.fade);
    container.appendChild(root);
  }

  /** Names a node in the picker (its question, once its texts are loaded). */
  nameNode(nodeId: string, name: string): void {
    const option = [...this.picker.options].find((o) => o.value === nodeId);
    if (option) option.textContent = name;
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

  /** How explorable terms behave in subtitles and cards rendered from now on. */
  setTermOptions(options: TermOptions): void {
    this.terms = options;
  }

  setSubtitle(entry: TextEntry | undefined): void {
    this.subtitle.replaceChildren(...(entry === undefined ? [] : [renderEntry(entry, this.terms)]));
  }

  /** The card of an explorable term: definition, « Explorer », « Plus tard ». */
  showTermCard(view: TermCardView | null): void {
    this.termCard.hidden = view === null;
    if (!view) {
      this.termCard.replaceChildren();
      return;
    }
    const close = el("button", { type: "button", className: "xs-close", textContent: "✕", ariaLabel: "Fermer" });
    close.addEventListener("click", () => this.handlers.onCloseTerm());
    const explore = el("button", { type: "button", className: "xs-primary", textContent: "Explorer" });
    explore.addEventListener("click", () => this.handlers.onExplore());
    const later = el("button", { type: "button", textContent: view.saved ? "✓ Dans « À explorer »" : "Plus tard", disabled: view.saved });
    later.addEventListener("click", () => this.handlers.onLater());
    const actions = el("div", { className: "xs-actions" });
    actions.append(explore, later);
    // The definition is shown without its own terms: one card at a time.
    this.termCard.replaceChildren(close, el("p", { className: "xs-kicker", textContent: "Notion" }), el("h2", { textContent: view.title }), renderEntry(view.summary), actions);
  }

  /** null hides the button; label says where it goes back to. */
  setReturn(label: string | null): void {
    this.returnButton.hidden = label === null;
    this.returnButton.textContent = label ?? "";
  }

  /** The "À explorer" list proposed at the end of the Play; null or empty hides it. */
  showSaved(items: { nodeId: string; title: string }[] | null): void {
    this.saved.hidden = !items || items.length === 0;
    if (!items || items.length === 0) {
      this.saved.replaceChildren();
      return;
    }
    const close = el("button", { type: "button", className: "xs-close", textContent: "✕", ariaLabel: "Fermer" });
    close.addEventListener("click", () => this.handlers.onCloseSaved());
    const list = el("ul");
    for (const item of items) {
      const li = el("li");
      const go = el("button", { type: "button", className: "xs-primary", textContent: "Explorer" });
      go.addEventListener("click", () => this.handlers.onExploreSaved(item.nodeId));
      li.append(el("span", { textContent: item.title }), go);
      list.append(li);
    }
    this.saved.replaceChildren(close, el("p", { className: "xs-kicker", textContent: "Fin de la visite" }), el("h2", { textContent: "À explorer" }), list);
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
        div.addEventListener("click", () => this.handlers.onLabel(id));
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
    this.card.append(el("h2", { textContent: view.title }), renderEntry(view.description, this.terms));
    if (view.dive) {
      const dive = el("button", { type: "button", className: "xs-dive", disabled: !view.dive.available, textContent: view.dive.available ? "Plonger à l'intérieur" : "Plonger à l'intérieur (à venir)" });
      dive.addEventListener("click", () => this.handlers.onDive());
      this.card.append(dive);
    }
  }

  setLenses(lenses: LensView[]): void {
    this.lensBar.replaceChildren(
      ...lenses.map((lens) => {
        const button = el("button", { type: "button", textContent: lens.label, ariaPressed: String(lens.on), title: lens.on ? "Masquer la lentille" : "Afficher la lentille" });
        button.addEventListener("click", () => this.handlers.onLens(lens.id, !lens.on));
        return button;
      }),
    );
  }

  /** Sliders of the active lenses for the current level; empty hides the panel. */
  setControls(controls: ControlView[]): void {
    this.controlInputs.clear();
    this.controls.hidden = controls.length === 0;
    this.controls.replaceChildren(
      ...controls.map((c) => {
        const id = `xs-control-${c.id}`;
        const wrap = el("div", { className: "xs-control" });
        const output = el("output", { htmlFor: id });
        const label = el("label", { htmlFor: id });
        label.append(el("span", { textContent: c.label }), output);
        const input = el("input", { type: "range", id, min: String(c.min), max: String(c.max), step: String(c.step), value: String(c.value) });
        input.addEventListener("input", () => {
          output.textContent = formatValue(Number(input.value), c.unit, c.step);
          this.handlers.onControl(c.id, Number(input.value));
        });
        output.textContent = formatValue(c.value, c.unit, c.step);
        this.controlInputs.set(c.id, { input, output, unit: c.unit });
        wrap.append(label, input);
        return wrap;
      }),
    );
  }

  /** Follows values changed elsewhere (a tour animating a slider). Call once per frame. */
  updateControls(value: (id: string) => number | undefined): void {
    for (const [id, { input, output, unit }] of this.controlInputs) {
      if (document.activeElement === input) continue;
      const v = value(id);
      if (v === undefined || !Number.isFinite(v)) continue;
      input.value = String(v);
      output.textContent = formatValue(v, unit, Number(input.step));
    }
  }

  setBreadcrumb(crumbs: CrumbView[]): void {
    this.crumbs.hidden = crumbs.length <= 1;
    const items: Node[] = [];
    crumbs.forEach((c, i) => {
      if (i > 0) items.push(el("span", { className: "sep", textContent: "›" }));
      const last = i === crumbs.length - 1;
      const item = last ? el("span", { className: "here" }) : el("button", { type: "button", title: `Remonter à ${c.label}` });
      item.append(document.createTextNode(c.label), el("small", { textContent: c.unit }));
      if (!last) item.addEventListener("click", () => this.handlers.onAscend(c.nodeId));
      items.push(item);
    });
    this.crumbs.replaceChildren(...items);
  }

  /** null hides the bar (the camera looks at something not to scale); magnified: the scale inside a magnifier. */
  setScale(bar: { pixels: number; label: string; magnified?: boolean } | null): void {
    this.scale.hidden = bar === null;
    if (!bar) return;
    this.scaleLabel.textContent = bar.magnified ? `🔍 dans la loupe : ${bar.label}` : bar.label;
    this.scale.classList.toggle("magnified", bar.magnified ?? false);
    this.scaleRule.style.width = `${bar.pixels.toFixed(1)}px`;
  }

  /** Covers the view (true) or reveals it, for the cut between two nodes. */
  setFade(on: boolean, color?: string): void {
    if (color) this.fade.style.background = color;
    this.fade.classList.toggle("on", on);
  }
}

const FADE_MS = 300;
export const fadeDuration = () => (matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : FADE_MS);

function formatValue(value: number, unit: string | undefined, step: number): string {
  const decimals = step >= 1 ? 0 : Math.min(3, Math.ceil(-Math.log10(step)));
  const text = value.toLocaleString("fr-FR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  if (unit === "deg") return `${text}°`;
  if (unit && unit !== "1" && unit !== "scene") return `${text} ${unit}`;
  return text;
}
