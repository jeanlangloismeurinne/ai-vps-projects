import type { ContentSource, NodeBundle } from "./contentSource";
import type { Catalogue, Scene, Texts } from "./types";

type Loader = () => Promise<unknown>;

// Bundled lazily by Vite: each node's files become their own chunk, fetched on demand.
const nodeFiles = import.meta.glob("../../../content/nodes/*/*.json", { import: "default" }) as Record<string, Loader>;
const catalogueFile = import.meta.glob("../../../catalogue/catalogue.json", { import: "default" }) as Record<string, Loader>;

const FILE_PATTERN = /\/content\/nodes\/([^/]+)\/([^/]+)\.json$/;

export class StaticContentSource implements ContentSource {
  private readonly nodes = new Map<string, Map<string, Loader>>();

  constructor() {
    for (const [path, load] of Object.entries(nodeFiles)) {
      const match = FILE_PATTERN.exec(path);
      if (!match) continue;
      const [, id, file] = match as unknown as [string, string, string];
      if (!this.nodes.has(id)) this.nodes.set(id, new Map());
      this.nodes.get(id)!.set(file, load);
    }
  }

  nodeIds(): string[] {
    return [...this.nodes.keys()].sort();
  }

  async catalogue(): Promise<Catalogue> {
    const load = Object.values(catalogueFile)[0];
    if (!load) throw new Error("catalogue/catalogue.json not found");
    return (await load()) as Catalogue;
  }

  async node(id: string): Promise<NodeBundle> {
    const files = this.nodes.get(id);
    const loadScene = files?.get("scene");
    const loadSources = files?.get("sources");
    if (!files || !loadScene || !loadSources) throw new Error(`unknown node '${id}'`);
    const texts: Record<string, Texts> = {};
    for (const [file, load] of files) {
      const lang = /^texts\.([a-z]{2})$/.exec(file)?.[1];
      if (lang) texts[lang] = (await load()) as Texts;
    }
    return { scene: (await loadScene()) as Scene, texts, sources: await loadSources() };
  }
}
