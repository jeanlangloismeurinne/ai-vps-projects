import { StaticContentSource } from "./content/staticContentSource";
import type { NodeBundle } from "./content/contentSource";
import type { Level, Scene, Texts, Tour } from "./content/types";
import { Engine } from "./core/engine";
import { PluginRegistry } from "./core/registry";
import { TourPlayer } from "./play/player";
import { registerComponents } from "./plugins/components";
import { registerSimulators } from "./plugins/simulators";
import { Overlay } from "./ui/overlay";
import { lookup } from "./ui/texts";

const DEFAULT_NODE = "starlink-terminal";
const LANG = "fr";
const LEVEL_STORAGE_KEY = "xs-level";

const app = document.querySelector<HTMLDivElement>("#app")!;
const source = new StaticContentSource();
const registry = new PluginRegistry();
registerComponents(registry);
registerSimulators(registry);

// What the user is looking at.
let scene: Scene | null = null;
let texts: Texts | undefined;
let level: Level = readLevel();
let selected: string | null = null;
let tourLabels: string[] = [];

const engine = new Engine(app, source, registry, {
  // The camera belongs to the user as soon as they move it: the arrival tour
  // ends, the Play pauses (spec, Parcours type).
  onGesture: () => yieldToUser(),
  onTap: (x, y) => {
    const id = engine.pick(x, y);
    if (id) yieldToUser();
    select(id);
  },
});

const player = new TourPlayer(
  {
    // The engine is the stage; labels are drawn here, in the DOM.
    ...bindStage(),
    setLabels: (ids) => {
      tourLabels = ids;
      refreshLabels();
    },
  },
  {
    onStep: (tour, index) => {
      overlay.setSubtitle(lookup(texts, level, tour.steps[index]!.textKey));
      refreshPlayer();
    },
    onState: () => refreshPlayer(),
    onEnd: () => {
      overlay.setSubtitle(undefined);
      refreshPlayer();
    },
  },
);
engine.addFrameListener((dt) => player.update(dt));
// Labels wait for the camera to land: during a flight they would slide across the screen.
engine.onFrame = () => overlay.placeLabels((id) => engine.screenPosition(id), engine.cameraFlying);

const overlay = new Overlay(app, source.nodeIds(), {
  onHome: () => engine.goHome(),
  onNode: (id) => {
    try {
      history.replaceState(null, "", `?node=${id}`);
    } catch {
      // Sandboxed previews may refuse URL changes; the picker still works.
    }
    void open(id);
  },
  onLevel: (l) => setLevel(l),
  onPlayPause: () => {
    const current = player.current;
    if (player.state === "playing" && current?.tour.autoStart) player.stop();
    else if (player.state === "playing") player.pause();
    else if (player.state === "paused") player.resume();
    else startMainTour();
  },
  onPrevious: () => player.previous(),
  onNext: () => player.next(),
  onStop: () => player.stop(),
  onCloseCard: () => select(null),
});

function bindStage() {
  const methods = ["reset", "advanceSim", "setFrozen", "flyTo", "setVisible", "reveal", "setLens", "getParam", "setParam", "setTimeScale", "setHighlights"] as const;
  return Object.fromEntries(methods.map((m) => [m, (engine[m] as (...args: unknown[]) => unknown).bind(engine)])) as Pick<Engine, (typeof methods)[number]>;
}

function readLevel(): Level {
  try {
    const stored = localStorage.getItem(LEVEL_STORAGE_KEY);
    if (stored === "discovery" || stored === "essential" || stored === "advanced") return stored;
  } catch {
    // Storage may be unavailable (private browsing, sandbox).
  }
  return "essential";
}

function setLevel(l: Level): void {
  level = l;
  try {
    localStorage.setItem(LEVEL_STORAGE_KEY, l);
  } catch {
    // Not remembered, still applied.
  }
  overlay.setLevel(l);
  // Same node, same scene: only the texts change (spec, Niveaux d'explication).
  const current = player.current;
  overlay.setSubtitle(current ? lookup(texts, level, current.step.textKey) : undefined);
  refreshLabels();
  showCard();
}

function yieldToUser(): void {
  if (player.state !== "playing") return;
  if (player.current?.tour.autoStart) player.stop();
  else player.pause();
}

function startMainTour(): void {
  const tour = scene?.tours.find((t) => !t.autoStart) ?? scene?.tours[0];
  if (!tour) return;
  select(null);
  player.play(tour);
}

function select(id: string | null): void {
  if (id === selected) return;
  selected = id;
  engine.select(id);
  showCard();
  refreshLabels();
}

function showCard(): void {
  const entity = selected ? scene?.entities.find((e) => e.id === selected) : undefined;
  if (!entity) {
    overlay.showCard(null);
    return;
  }
  const child = scene?.links?.find((l) => l.kind === "composedOf" && l.from === entity.id);
  overlay.showCard({
    title: textOf(entity.labelKey) || entity.id,
    description: lookup(texts, level, entity.descriptionKey),
    dive: child && { available: child.available ?? false },
  });
}

function textOf(key: string | undefined): string {
  const entry = lookup(texts, level, key);
  return entry === undefined ? "" : typeof entry === "string" ? entry : entry.text;
}

function refreshLabels(): void {
  const ids = new Set(tourLabels);
  if (selected) ids.add(selected);
  const labelKey = (id: string) => scene?.entities.find((e) => e.id === id)?.labelKey;
  overlay.setLabels([...ids].map((id) => ({ id, text: textOf(labelKey(id)) || id })));
}

function refreshPlayer(): void {
  const current = player.current;
  overlay.setPlayer({
    state: player.state,
    intro: current?.tour.autoStart ?? false,
    index: current?.index ?? 0,
    count: current?.tour.steps.length ?? 0,
  });
}

// Dev only: the browser bundle stays free of Ajv and the schemas.
async function contentErrors(bundle: NodeBundle): Promise<string[]> {
  if (!import.meta.env.DEV) return [];
  const { ContentValidator } = await import("./content/validation");
  const validator = new ContentValidator(await source.catalogue());
  const dir = bundle.scene.node.id;
  return validator.nodeErrors({ dir, scene: bundle.scene, texts: bundle.texts, sources: bundle.sources as Record<string, unknown> });
}

async function open(id: string): Promise<void> {
  try {
    player.stop();
    const { bundle, built, simulation, missingLenses } = await engine.load(id);
    scene = bundle.scene;
    texts = bundle.texts[LANG];
    selected = null;
    tourLabels = [];
    overlay.showCard(null);
    refreshLabels();
    const notices: string[] = [];
    if (built.missingComponents.length > 0) notices.push(`Composants pas encore dessinés (repères roses) : ${built.missingComponents.join(", ")}`);
    if (simulation.missing.length > 0) notices.push(`Simulateurs pas encore écrits : ${simulation.missing.join(", ")}`);
    if (missingLenses.length > 0) notices.push(`Lentilles à venir (jalon 4) : ${missingLenses.join(", ")}`);
    const errors = await contentErrors(bundle);
    if (errors.length > 0) {
      console.error(`content errors in '${id}'`, errors);
      notices.push(`${errors.length} erreur(s) de contenu, voir la console`);
    }
    overlay.show(id, texts?.question ?? id, notices);
    const intro: Tour | undefined = scene.tours.find((t) => t.autoStart);
    if (intro) player.play(intro);
    else refreshPlayer();
  } catch (error) {
    console.error(error);
    overlay.show(id, `Impossible d'ouvrir « ${id} »`, [String(error)]);
  }
}

overlay.setLevel(level);
void open(new URLSearchParams(location.search).get("node") ?? DEFAULT_NODE);

// Dev only: a handle for driving the app from the console or a headless browser.
if (import.meta.env.DEV) Object.assign(window, { xs: { engine, player, scene: () => scene, select, setLevel, startMainTour } });
