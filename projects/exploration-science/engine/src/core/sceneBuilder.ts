import {
  Box3,
  EdgesGeometry,
  Group,
  LineBasicMaterial,
  LineSegments,
  MathUtils,
  OctahedronGeometry,
  Vector3,
} from "three";
import type { Catalogue, Entity, Params, Scene } from "../content/types";
import type { ComponentInstance, PluginRegistry } from "./registry";
import { Palette } from "./style";

export interface BuiltEntity {
  entity: Entity;
  /** Carries the entity transform and visibility; the component object sits inside. */
  node: Group;
  instance: ComponentInstance;
  placeholder: boolean;
}

export interface BuiltScene {
  root: Group;
  entities: Map<string, BuiltEntity>;
  /** Materials of the scene's style, shared with lenses. */
  palette: Palette;
  /** Components referenced by the scene but not implemented yet. */
  missingComponents: string[];
  update(dt: number): void;
  /** World-space centre of an entity's bounds, used as camera target. */
  focusPoint(id: string, out?: Vector3): Vector3;
  dispose(): void;
}

/** Catalogue defaults first, scene values over them. */
export function withDefaults(catalogue: Catalogue, pluginId: string, params: Params, kind: "components" | "simulators" = "components"): Params {
  const spec = catalogue[kind].find((c) => c.id === pluginId);
  const merged: Params = {};
  for (const [name, p] of Object.entries(spec?.params.properties ?? {})) {
    if (p.default !== undefined) merged[name] = p.default;
  }
  return { ...merged, ...params };
}

// Stand-in for a component whose plugin is not written yet: visible, obviously
// unfinished, and small inside a parent (children usually sit in a casing).
function placeholder(entity: Entity, ctx: { metres(m: number): number }): ComponentInstance {
  const radius = entity.parent ? ctx.metres(0.05) : ctx.metres(1);
  const geometry = new EdgesGeometry(new OctahedronGeometry(radius));
  const material = new LineBasicMaterial({ color: "#ff3d7f" });
  const object = new LineSegments(geometry, material);
  object.name = `placeholder:${entity.component}`;
  return {
    object,
    dispose() {
      geometry.dispose();
      material.dispose();
    },
  };
}

export function buildScene(scene: Scene, catalogue: Catalogue, registry: PluginRegistry): BuiltScene {
  const root = new Group();
  root.name = `node:${scene.node.id}`;
  const palette = new Palette(scene.style);
  const ctx = { palette, metres: (m: number) => m / scene.scale.metersPerUnit };
  const entities = new Map<string, BuiltEntity>();
  const missing = new Set<string>();

  for (const entity of scene.entities) {
    const plugin = registry.component(entity.component);
    if (!plugin) missing.add(entity.component);
    const instance = plugin ? plugin.create(withDefaults(catalogue, entity.component, entity.params), ctx) : placeholder(entity, ctx);
    const node = new Group();
    node.name = `entity:${entity.id}`;
    node.userData.entityId = entity.id;
    const { position, rotationDeg, scale } = entity.transform;
    node.position.fromArray(position);
    if (rotationDeg) node.rotation.set(...(rotationDeg.map((d) => MathUtils.degToRad(d)) as [number, number, number]));
    if (scale !== undefined) node.scale.setScalar(scale);
    node.visible = entity.visible ?? true;
    node.add(instance.object);
    entities.set(entity.id, { entity, node, instance, placeholder: !plugin });
  }

  for (const built of entities.values()) {
    const parentId = built.entity.parent;
    if (parentId === undefined) {
      root.add(built.node);
      continue;
    }
    assertNoCycle(built.entity.id, entities);
    const parent = entities.get(parentId);
    if (!parent) throw new Error(`entity '${built.entity.id}': unknown parent '${parentId}'`);
    (parent.instance.anchor ?? parent.instance.object).add(built.node);
  }

  root.updateMatrixWorld(true);
  const lookup = (id: string) => entities.get(id)?.node;
  for (const built of entities.values()) built.instance.resolve?.(lookup);

  const box = new Box3();
  return {
    root,
    entities,
    palette,
    missingComponents: [...missing].sort(),
    update(dt) {
      for (const built of entities.values()) built.instance.update?.(dt);
    },
    focusPoint(id, out = new Vector3()) {
      const built = entities.get(id);
      if (!built) throw new Error(`unknown entity '${id}'`);
      box.setFromObject(built.node);
      return box.isEmpty() ? built.node.getWorldPosition(out) : box.getCenter(out);
    },
    dispose() {
      for (const built of entities.values()) built.instance.dispose?.();
      palette.dispose();
      root.clear();
    },
  };
}

function assertNoCycle(id: string, entities: Map<string, BuiltEntity>): void {
  const seen = new Set<string>([id]);
  let current = entities.get(id)?.entity.parent;
  while (current !== undefined) {
    if (seen.has(current)) throw new Error(`entity '${id}': parent cycle through '${current}'`);
    seen.add(current);
    current = entities.get(current)?.entity.parent;
  }
}
