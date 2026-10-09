// Content validation shared by tests and (later) the engine's dev mode.
// Schema validation is delegated to Ajv; this module adds the cross-file
// checks a JSON Schema cannot express (catalogue references, text keys, sources).
import Ajv2020, { type ValidateFunction } from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import sceneSchema from "../../../schemas/scene.schema.json";
import catalogueSchema from "../../../schemas/catalogue.schema.json";
import textsSchema from "../../../schemas/texts.schema.json";
import sourcesSchema from "../../../schemas/sources.schema.json";

export const LEVELS = ["discovery", "essential", "advanced"] as const;
export type Level = (typeof LEVELS)[number];

type Json = Record<string, any>;

export interface NodeFiles {
  /** Folder name under content/nodes/. */
  dir: string;
  scene: Json;
  texts: Record<string, Json>;
  sources: Json;
}

const CATALOGUE_KEYWORDS = ["x-unit", "x-ref", "x-alternativeTo"];
// Intro tours are played on arrival and must stay within 20-30 s (CLAUDE.md).
const INTRO_MIN_S = 20;
const INTRO_MAX_S = 30;

function createAjv(): Ajv2020 {
  const ajv = new Ajv2020({ allErrors: true, strict: true, allowUnionTypes: true });
  addFormats(ajv);
  for (const keyword of CATALOGUE_KEYWORDS) ajv.addKeyword({ keyword });
  return ajv;
}

function formatErrors(validate: ValidateFunction): string[] {
  return (validate.errors ?? []).map((e) => `${e.instancePath || "/"} ${e.message ?? ""}`.trim());
}

export class ContentValidator {
  private readonly ajv = createAjv();
  private readonly validateScene = this.ajv.compile<unknown>(sceneSchema);
  private readonly validateCatalogue = this.ajv.compile<unknown>(catalogueSchema);
  private readonly validateTexts = this.ajv.compile<unknown>(textsSchema);
  private readonly validateSources = this.ajv.compile<unknown>(sourcesSchema);
  private readonly paramValidators = new Map<string, ValidateFunction>();

  constructor(private readonly catalogue: Json) {}

  catalogueErrors(): string[] {
    if (!this.validateCatalogue(this.catalogue)) return formatErrors(this.validateCatalogue);
    const errors: string[] = [];
    const seen = new Set<string>();
    for (const kind of ["components", "simulators", "lenses"]) {
      for (const entry of this.catalogue[kind]) {
        if (seen.has(entry.id)) errors.push(`duplicate catalogue id '${entry.id}'`);
        seen.add(entry.id);
        if (entry.params) {
          for (const [name, p] of Object.entries<Json>(entry.params.properties)) {
            const alt = p["x-alternativeTo"];
            if (alt && !(alt in entry.params.properties)) {
              errors.push(`${entry.id}.${name}: x-alternativeTo '${alt}' is not a param`);
            }
          }
        }
      }
    }
    for (const sim of this.catalogue.simulators) {
      for (const [role, spec] of Object.entries<Json>(sim.roles)) {
        for (const c of spec.components) {
          if (!this.find("components", c)) errors.push(`${sim.id}.roles.${role}: unknown component '${c}'`);
        }
      }
    }
    return errors;
  }

  nodeErrors(node: NodeFiles): string[] {
    const errors: string[] = [];
    const { scene, sources } = node;

    if (!this.validateScene(scene)) return formatErrors(this.validateScene).map((e) => `scene ${e}`);
    if (!this.validateSources(sources)) errors.push(...formatErrors(this.validateSources).map((e) => `sources ${e}`));
    for (const [lang, texts] of Object.entries(node.texts)) {
      if (!this.validateTexts(texts)) errors.push(...formatErrors(this.validateTexts).map((e) => `texts.${lang} ${e}`));
    }
    if (errors.length > 0) return errors;

    const nodeId: string = scene.node.id;
    if (node.dir !== nodeId) errors.push(`folder '${node.dir}' does not match node id '${nodeId}'`);
    if (sources.nodeId !== nodeId) errors.push(`sources.nodeId '${sources.nodeId}' != '${nodeId}'`);

    errors.push(...this.sceneReferenceErrors(scene));
    for (const [lang, texts] of Object.entries(node.texts)) {
      if (texts.nodeId !== nodeId) errors.push(`texts.${lang}.nodeId '${texts.nodeId}' != '${nodeId}'`);
      if (texts.lang !== lang) errors.push(`texts.${lang}.lang is '${texts.lang}'`);
      errors.push(...textKeyErrors(scene, texts).map((e) => `texts.${lang}: ${e}`));
    }
    errors.push(...sourcesErrors(sources));
    return errors;
  }

  private find(kind: "components" | "simulators" | "lenses", id: string): Json | undefined {
    return this.catalogue[kind].find((e: Json) => e.id === id);
  }

  private paramsErrors(where: string, plugin: Json, params: Json, entityIds: Set<string>): string[] {
    let validate = this.paramValidators.get(plugin.id);
    if (!validate) {
      validate = this.ajv.compile(plugin.params);
      this.paramValidators.set(plugin.id, validate);
    }
    const errors = validate(params) ? [] : formatErrors(validate).map((e) => `${where}.params ${e}`);
    for (const [name, p] of Object.entries<Json>(plugin.params.properties)) {
      if (p["x-ref"] === "entity" && name in params && !entityIds.has(params[name])) {
        errors.push(`${where}.params.${name}: unknown entity '${params[name]}'`);
      }
    }
    return errors;
  }

  private sceneReferenceErrors(scene: Json): string[] {
    const errors: string[] = [];
    const entities = new Map<string, Json>();
    for (const e of scene.entities) {
      if (entities.has(e.id)) errors.push(`duplicate entity id '${e.id}'`);
      entities.set(e.id, e);
    }
    const entityIds = new Set(entities.keys());
    const sims = new Map<string, Json>(scene.simulators?.map((s: Json) => [s.id, s]) ?? []);
    const lenses = new Map<string, Json>(scene.lenses?.map((l: Json) => [l.id, l]) ?? []);
    const requireEntity = (where: string, id: string) => {
      if (!entities.has(id)) errors.push(`${where}: unknown entity '${id}'`);
    };

    for (const e of scene.entities) {
      const where = `entity '${e.id}'`;
      const component = this.find("components", e.component);
      if (!component) {
        errors.push(`${where}: unknown component '${e.component}'`);
        continue;
      }
      errors.push(...this.paramsErrors(where, component, e.params, entityIds));
      if (e.parent !== undefined) {
        requireEntity(`${where}.parent`, e.parent);
        if (e.parent === e.id) errors.push(`${where}: is its own parent`);
      }
    }

    // Simulator instances: known plugin, valid params, roles bound to accepted components.
    const simPlugins = new Map<string, Json>();
    for (const s of sims.values()) {
      const where = `simulator '${s.id}'`;
      const plugin = this.find("simulators", s.simulator);
      if (!plugin) {
        errors.push(`${where}: unknown simulator '${s.simulator}'`);
        continue;
      }
      simPlugins.set(s.id, plugin);
      errors.push(...this.paramsErrors(where, plugin, s.params, entityIds));
      for (const [role, spec] of Object.entries<Json>(plugin.roles)) {
        const bound = s.bind[role];
        if (bound === undefined) {
          if (!spec.optional) errors.push(`${where}: role '${role}' not bound`);
          continue;
        }
        const ids: string[] = Array.isArray(bound) ? bound : [bound];
        if (Array.isArray(bound) && !spec.multiple) errors.push(`${where}: role '${role}' takes a single entity`);
        for (const id of ids) {
          const entity = entities.get(id);
          if (!entity) errors.push(`${where}.bind.${role}: unknown entity '${id}'`);
          else if (!spec.components.includes(entity.component)) {
            errors.push(`${where}.bind.${role}: '${id}' is a '${entity.component}', expected ${spec.components.join(" | ")}`);
          }
        }
      }
      for (const role of Object.keys(s.bind)) {
        if (!(role in plugin.roles)) errors.push(`${where}: unknown role '${role}'`);
      }
    }

    const simParam = (where: string, simId: string, param: string): Json | undefined => {
      const plugin = simPlugins.get(simId);
      if (!sims.has(simId)) {
        errors.push(`${where}: unknown simulator instance '${simId}'`);
        return undefined;
      }
      if (!plugin) return undefined;
      const spec = plugin.params.properties[param];
      if (!spec) errors.push(`${where}: '${plugin.id}' has no param '${param}'`);
      return spec;
    };

    for (const l of lenses.values()) {
      const where = `lens '${l.id}'`;
      const plugin = this.find("lenses", l.lens);
      if (!plugin) errors.push(`${where}: unknown lens '${l.lens}'`);
      for (const simId of l.sources) {
        const sim = simPlugins.get(simId);
        if (!sims.has(simId)) errors.push(`${where}: unknown source '${simId}'`);
        else if (sim && plugin && !plugin.consumes.some((c: string) => sim.provides.includes(c))) {
          errors.push(`${where}: '${sim.id}' provides nothing '${plugin.id}' consumes`);
        }
      }
      for (const c of l.controls) {
        const cw = `${where}.control '${c.id}'`;
        const spec = simParam(cw, c.target, c.param);
        if (!spec) continue;
        if (spec.type !== "number" && spec.type !== "integer") errors.push(`${cw}: param '${c.param}' is not numeric`);
        if (c.min !== undefined && spec.minimum !== undefined && c.min < spec.minimum) errors.push(`${cw}: min below validity range`);
        if (c.max !== undefined && spec.maximum !== undefined && c.max > spec.maximum) errors.push(`${cw}: max above validity range`);
        if (c.min !== undefined && c.max !== undefined && c.min >= c.max) errors.push(`${cw}: min >= max`);
      }
    }

    for (const link of scene.links ?? []) {
      if (link.from !== undefined) requireEntity(`link to '${link.to}'`, link.from);
    }

    requireEntity("camera.home", scene.camera.home.target);
    const { minDistance, maxDistance } = scene.camera.constraints;
    if (minDistance >= maxDistance) errors.push("camera: minDistance >= maxDistance");

    const autoStart = scene.tours.filter((t: Json) => t.autoStart);
    if (autoStart.length > 1) errors.push("more than one autoStart tour");
    for (const tour of autoStart) {
      const total = tour.steps.reduce((sum: number, s: Json) => sum + s.durationS, 0);
      if (total < INTRO_MIN_S || total > INTRO_MAX_S) {
        errors.push(`tour '${tour.id}': auto tour lasts ${total} s, expected ${INTRO_MIN_S}-${INTRO_MAX_S} s`);
      }
    }
    const tourIds = new Set<string>();
    for (const tour of scene.tours) {
      if (tourIds.has(tour.id)) errors.push(`duplicate tour id '${tour.id}'`);
      tourIds.add(tour.id);
      for (const step of tour.steps) {
        const where = `tour '${tour.id}' step '${step.id}'`;
        if (step.camera) requireEntity(`${where}.camera`, step.camera.shot.target);
        for (const a of step.actions ?? []) {
          switch (a.type) {
            case "highlight":
            case "label":
            case "show":
            case "hide":
              for (const t of a.targets) requireEntity(`${where}.${a.type}`, t);
              break;
            case "reveal": {
              const entity = entities.get(a.target);
              if (!entity) errors.push(`${where}.reveal: unknown entity '${a.target}'`);
              else if (a.mode !== "none") {
                const caps: string[] = this.find("components", entity.component)?.capabilities ?? [];
                if (!caps.includes(a.mode)) errors.push(`${where}.reveal: '${entity.component}' cannot '${a.mode}'`);
              }
              break;
            }
            case "lens":
              if (!lenses.has(a.lens)) errors.push(`${where}.lens: unknown lens instance '${a.lens}'`);
              break;
            case "setParam": {
              const spec = simParam(`${where}.setParam`, a.target, a.param);
              if (!spec) break;
              const plugin = simPlugins.get(a.target)!;
              const probe = this.ajv.compile({ ...plugin.params, required: [] });
              if (!probe({ [a.param]: a.value })) {
                errors.push(...formatErrors(probe).map((e) => `${where}.setParam ${e}`));
              }
              if (spec["x-ref"] === "entity") requireEntity(`${where}.setParam`, String(a.value));
              break;
            }
          }
        }
      }
    }
    return errors;
  }
}

/** Every text key the scene references. */
export function sceneTextKeys(scene: Json): Set<string> {
  const keys = new Set<string>();
  for (const e of scene.entities) {
    if (e.labelKey) keys.add(e.labelKey);
    if (e.descriptionKey) keys.add(e.descriptionKey);
  }
  for (const l of scene.lenses ?? []) {
    if (l.labelKey) keys.add(l.labelKey);
    for (const c of l.controls) keys.add(c.labelKey);
  }
  for (const t of scene.tours) for (const s of t.steps) keys.add(s.textKey);
  return keys;
}

/** Level text first, then common. */
export function resolveText(texts: Json, level: Level, key: string): unknown {
  return texts.levels[level][key] ?? texts.common[key];
}

function textKeyErrors(scene: Json, texts: Json): string[] {
  const errors: string[] = [];
  const used = sceneTextKeys(scene);
  for (const key of used) {
    for (const level of LEVELS) {
      if (resolveText(texts, level, key) === undefined) errors.push(`key '${key}' missing for level '${level}'`);
    }
  }
  const defined = new Set([...Object.keys(texts.common), ...LEVELS.flatMap((l) => Object.keys(texts.levels[l]))]);
  for (const key of defined) {
    if (!used.has(key)) errors.push(`key '${key}' is not used by the scene`);
  }
  return errors;
}

function sourcesErrors(sources: Json): string[] {
  const errors: string[] = [];
  const ids = new Set<string>();
  for (const s of sources.sources) {
    if (ids.has(s.id)) errors.push(`duplicate source id '${s.id}'`);
    ids.add(s.id);
  }
  const factIds = new Set<string>();
  for (const f of sources.facts) {
    if (factIds.has(f.id)) errors.push(`duplicate fact id '${f.id}'`);
    factIds.add(f.id);
    for (const s of f.sources) if (!ids.has(s)) errors.push(`fact '${f.id}': unknown source '${s}'`);
    if (f.status === "verified" && f.sources.length === 0) errors.push(`fact '${f.id}': verified without source`);
    if (f.status === "computed" && !f.formula) errors.push(`fact '${f.id}': computed without formula`);
  }
  return errors;
}
