import type { Catalogue, Scene, Texts } from "./types";

export interface NodeBundle {
  scene: Scene;
  /** Keyed by language code. */
  texts: Record<string, Texts>;
  sources: unknown;
}

/**
 * The only way the engine gets content (design rule 8). Phase 0 reads static
 * files; Phase 1 will call the graph API behind the same interface.
 */
export interface ContentSource {
  catalogue(): Promise<Catalogue>;
  node(id: string): Promise<NodeBundle>;
}
