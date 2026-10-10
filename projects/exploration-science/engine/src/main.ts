import { StaticContentSource } from "./content/staticContentSource";
import type { NodeBundle } from "./content/contentSource";
import type { Catalogue, LensInstanceSpec, Level, Scene, Texts, Tour } from "./content/types";
import { Engine } from "./core/engine";
import { PluginRegistry } from "./core/registry";
import { TourPlayer } from "./play/player";
import { registerComponents } from "./plugins/components";
import { registerLenses } from "./plugins/lenses";
import { registerSimulators } from "./plugins/simulators";
import { fadeDuration, Overlay, type ControlView } from "./ui/overlay";
import { scaleBar, scaleUnit } from "./ui/scale";
import { lookup } from "./ui/texts";

const DEFAULT_NODE = "starlink-terminal";
const LANG = "fr";
const LEVEL_STORAGE_KEY = "xs-level";

const app = document.querySelector<HTMLDivElement>("#app")!;
const source = new StaticContentSource();
const registry = new PluginRegistry();
registerComponents(registry);
registerSimulators(registry);
registerLenses(registry);

// What the user is looking at.
let scene: Scene | null = null;
let texts: Texts | undefined;
let level: Level = readLevel();
let selected: string | null = null;
let tourLabels: string[] = [];
let catalogue: Catalogue | null = null;
/** Nodes from the root down to the one shown, for the breadcrumb (zoom levels). */
let path: string[] = [];
/** A dive or a climb is running: ignore further navigation until it lands. */
let navigating = false;

const DIVE_FLIGHT_S = 0.9;
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

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
engine.onFrame = () => {
  overlay.placeLabels((id) => engine.screenPosition(id), engine.cameraFlying);
  overlay.updateControls(controlValue);
  const mpp = engine.metresPerPixel();
  overlay.setScale(mpp === null ? null : scaleBar(mpp));
};
engine.onLensChange = () => refreshLenses();

const overlay = new Overlay(app, source.nodeIds(), {
  onHome: () => engine.goHome(),
  onNode: (id) => void open(id),
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
  onLabel: (id) => {
    yieldToUser();
    select(id);
  },
  onLens: (id, on) => engine.setLens(id, on),
  onControl: (id, value) => {
    const control = controlSpec(id);
    if (!control) return;
    yieldToUser();
    engine.setParam(control.target, control.param, value);
  },
  onDive: () => void dive(),
  onAscend: (id) => void climb(id),
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
  refreshLenses();
  refreshBreadcrumb();
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
  const child = diveTarget(entity.id);
  overlay.showCard({
    title: textOf(entity.labelKey) || entity.id,
    description: lookup(texts, level, entity.descriptionKey),
    dive: child && { available: child.available },
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

/** The child node an entity leads to; available once written and present in the content. */
function diveTarget(entityId: string): { node: string; available: boolean } | undefined {
  const link = scene?.links?.find((l) => l.kind === "composedOf" && l.from === entityId);
  if (!link) return undefined;
  return { node: link.to, available: (link.available ?? false) && source.nodeIds().includes(link.to) };
}

// ---- Lenses and sliders ----

function activeLensSpecs(): LensInstanceSpec[] {
  const on = new Set(engine.lensStates().filter((l) => l.on).map((l) => l.id));
  return (scene?.lenses ?? []).filter((l) => on.has(l.id));
}

function controlSpec(id: string) {
  for (const lens of activeLensSpecs()) {
    const control = lens.controls.find((c) => c.id === id);
    if (control) return control;
  }
  return undefined;
}

/** A slider shows the simulator's current value: derived outputs first (a steering angle set through the phase), then params. */
function controlValue(id: string): number | undefined {
  const control = controlSpec(id);
  if (!control) return undefined;
  const output = engine.simulatorOutputs(control.target)?.[control.param];
  const value = typeof output === "number" ? output : engine.getParam(control.target, control.param);
  return typeof value === "number" ? value : undefined;
}

function refreshLenses(): void {
  const labels = new Map((scene?.lenses ?? []).map((l) => [l.id, textOf(l.labelKey) || l.id]));
  overlay.setLenses(engine.lensStates().map((l) => ({ ...l, label: labels.get(l.id) ?? l.id })));
  const controls: ControlView[] = [];
  for (const lens of activeLensSpecs()) {
    for (const c of lens.controls) {
      if (!c.levels.includes(level)) continue;
      const simulator = scene?.simulators?.find((s) => s.id === c.target)?.simulator;
      const spec = catalogue?.simulators.find((s) => s.id === simulator)?.params.properties[c.param] as
        | { minimum?: number; maximum?: number; "x-unit"?: string; type?: string }
        | undefined;
      const min = c.min ?? spec?.minimum ?? 0;
      const max = c.max ?? spec?.maximum ?? 1;
      const step = c.step ?? (spec?.type === "integer" ? 1 : (max - min) / 100);
      controls.push({ id: c.id, label: textOf(c.labelKey) || c.param, min, max, step, value: controlValue(c.id) ?? min, unit: spec?.["x-unit"] });
    }
  }
  overlay.setControls(controls);
}

// ---- Zoom levels: breadcrumb, dive, climb ----

/** Root first. Follows node.parent up the graph. */
async function ancestry(id: string): Promise<string[]> {
  const chain = [id];
  let current = (await source.node(id)).scene;
  while (current.node.parent && chain.length < 16) {
    chain.unshift(current.node.parent.node);
    current = (await source.node(current.node.parent.node)).scene;
  }
  return chain;
}

// Each level is named after what its home shot looks at, and the unit of its scale.
async function refreshBreadcrumb(): Promise<void> {
  const crumbs = await Promise.all(
    path.map(async (id) => {
      const bundle = await source.node(id);
      const home = bundle.scene.entities.find((e) => e.id === bundle.scene.camera.home.target);
      const entry = lookup(bundle.texts[LANG], level, home?.labelKey);
      const label = entry === undefined ? id : typeof entry === "string" ? entry : entry.text;
      return { nodeId: id, label, unit: scaleUnit(bundle.scene.scale.metersPerUnit) };
    }),
  );
  overlay.setBreadcrumb(crumbs);
}

async function cut(load: () => Promise<void>): Promise<void> {
  overlay.setFade(true, scene?.environment.background);
  await wait(fadeDuration());
  await load();
  overlay.setFade(true, scene?.environment.background);
  await wait(50);
  overlay.setFade(false);
}

/** Flies into the selected entity, then cuts to its child node (spec, Zoom continu). */
async function dive(): Promise<void> {
  const from = selected;
  const target = from ? diveTarget(from) : undefined;
  if (navigating || !from || !target?.available) return;
  navigating = true;
  try {
    player.stop();
    overlay.showCard(null);
    engine.flyInto(from, DIVE_FLIGHT_S);
    await wait(DIVE_FLIGHT_S * 1000);
    await cut(() => open(target.node));
  } finally {
    navigating = false;
  }
}

/** Back up to an ancestor: lands close to the entity we came from, then pulls out around it. */
async function climb(ancestor: string): Promise<void> {
  const index = path.indexOf(ancestor);
  const below = path[index + 1];
  if (navigating || index < 0 || !below) return;
  navigating = true;
  try {
    const entity = (await source.node(below)).scene.node.parent?.entity;
    await cut(() => open(ancestor, { comingBackFrom: entity }));
  } finally {
    navigating = false;
  }
}

// Dev only: the browser bundle stays free of Ajv and the schemas.
async function contentErrors(bundle: NodeBundle): Promise<string[]> {
  if (!import.meta.env.DEV) return [];
  const { ContentValidator } = await import("./content/validation");
  const validator = new ContentValidator(await source.catalogue());
  const dir = bundle.scene.node.id;
  return validator.nodeErrors({ dir, scene: bundle.scene, texts: bundle.texts, sources: bundle.sources as Record<string, unknown> });
}

async function open(id: string, arrival: { comingBackFrom?: string } = {}): Promise<void> {
  try {
    player.stop();
    catalogue ??= await source.catalogue();
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
    try {
      history.replaceState(null, "", `?node=${id}`);
    } catch {
      // Sandboxed previews may refuse URL changes.
    }
    path = await ancestry(id);
    void refreshBreadcrumb();
    refreshLenses();
    const back = arrival.comingBackFrom;
    const close = back ? engine.shotAround(back, 0.5) : null;
    if (back && close) {
      // Coming back up: no arrival tour. Start inside the entity, then pull out around it (selection flight).
      engine.jumpTo(close);
      select(back);
      refreshPlayer();
      return;
    }
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
