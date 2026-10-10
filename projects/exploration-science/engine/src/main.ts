import { StaticContentSource } from "./content/staticContentSource";
import type { NodeBundle } from "./content/contentSource";
import { Engine } from "./core/engine";
import { PluginRegistry } from "./core/registry";
import { registerComponents } from "./plugins/components";
import { Overlay } from "./ui/overlay";

const DEFAULT_NODE = "starlink-terminal";
const LANG = "fr";

const app = document.querySelector<HTMLDivElement>("#app")!;
const source = new StaticContentSource();
const registry = new PluginRegistry();
registerComponents(registry);

const engine = new Engine(app, source, registry);
const overlay = new Overlay(app, source.nodeIds(), {
  onHome: () => engine.goHome(),
  onNode: (id) => {
    history.replaceState(null, "", `?node=${id}`);
    void open(id);
  },
});

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
    const { bundle, built } = await engine.load(id);
    const notices: string[] = [];
    if (built.missingComponents.length > 0) notices.push(`Composants pas encore dessinés (repères roses) : ${built.missingComponents.join(", ")}`);
    const errors = await contentErrors(bundle);
    if (errors.length > 0) {
      console.error(`content errors in '${id}'`, errors);
      notices.push(`${errors.length} erreur(s) de contenu, voir la console`);
    }
    overlay.show(id, bundle.texts[LANG]?.question ?? id, notices);
  } catch (error) {
    console.error(error);
    overlay.show(id, `Impossible d'ouvrir « ${id} »`, [String(error)]);
  }
}

void open(new URLSearchParams(location.search).get("node") ?? DEFAULT_NODE);
