// Validation of the V2 content (content/v2/, art/assets.json), shared by the tests and
// `npm run assets`. Ajv checks each file against schemas/v2/; this module adds the
// cross-file checks a JSON Schema cannot express (ids, anchors, shots, narrative rule).
// No relative import besides JSON: Node runs it without a bundler (scripts/v2/assets.ts).
import Ajv2020, { type ValidateFunction } from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import systemSchema from "../../../schemas/v2/system.schema.json" with { type: "json" };
import assetsSchema from "../../../schemas/v2/assets.schema.json" with { type: "json" };
import renderSchema from "../../../schemas/v2/render.schema.json" with { type: "json" };
import tourSchema from "../../../schemas/v2/tour.schema.json" with { type: "json" };
import textsSchema from "../../../schemas/v2/texts.schema.json" with { type: "json" };
import sourcesSchema from "../../../schemas/v2/sources.schema.json" with { type: "json" };

type Json = Record<string, any>;

export interface V2Content {
  system: Json;
  render: Json;
  tour: Json;
  /** Keyed by language. */
  texts: Record<string, Json>;
  sources: Json;
  /** art/assets.json */
  assets: Json;
  /** Swatch names of art/palette.json. */
  palette: Set<string>;
}

const ajv = new Ajv2020({ allErrors: true, strict: true, allowUnionTypes: true });
addFormats(ajv);
const validators = {
  system: ajv.compile(systemSchema),
  assets: ajv.compile(assetsSchema),
  render: ajv.compile(renderSchema),
  tour: ajv.compile(tourSchema),
  texts: ajv.compile(textsSchema),
  sources: ajv.compile(sourcesSchema),
};

function schemaErrors(kind: keyof typeof validators, data: unknown): string[] {
  const validate: ValidateFunction = validators[kind];
  if (validate(data)) return [];
  return (validate.errors ?? []).map((e) => `${kind} ${e.instancePath || "/"} ${e.message ?? ""}`.trim());
}

function duplicates(ids: string[]): string[] {
  return ids.filter((id, i) => ids.indexOf(id) !== i);
}

/** System file alone: schema, ids, supports, anchors, connections, flows. */
export function systemErrors(system: Json): string[] {
  const schema = schemaErrors("system", system);
  if (schema.length) return schema;
  const errors: string[] = [];
  const objects: Json[] = system.objects;
  const externals: Json[] = system.externals ?? [];
  const byId = new Map(objects.map((o) => [o.id, o]));
  const anchors = new Map<string, string[]>([...objects, ...externals].map((o) => [o.id, o.anchors ?? []]));

  for (const id of duplicates([...objects, ...externals].map((o) => o.id))) errors.push(`system: duplicate id '${id}'`);
  for (const o of objects) {
    const p = o.placement;
    if (o.role === "setting" && p) errors.push(`system: setting '${o.id}' must not have a placement`);
    if (o.role !== "setting" && !p) errors.push(`system: '${o.id}' has no placement`);
    if (!p?.on) continue;
    const support = byId.get(p.on);
    if (!support) errors.push(`system: '${o.id}' is placed on unknown object '${p.on}'`);
    else if (p.anchor && !(support.anchors ?? []).includes(p.anchor)) errors.push(`system: '${o.id}' is placed on unknown anchor '${p.on}#${p.anchor}'`);
  }
  for (const o of objects) {
    const seen = new Set<string>();
    for (let cur: Json | undefined = o; cur?.placement?.on; cur = byId.get(cur.placement.on)) {
      if (seen.has(cur.id)) {
        errors.push(`system: support cycle through '${o.id}'`);
        break;
      }
      seen.add(cur.id);
    }
  }

  const connections = new Map<string, Json>();
  for (const id of duplicates(system.connections.map((c: Json) => c.id))) errors.push(`system: duplicate connection '${id}'`);
  for (const c of system.connections) {
    connections.set(c.id, c);
    for (const end of [c.from, c.to]) {
      const [id, anchor] = end.split("#");
      if (!anchors.has(id)) errors.push(`system: connection '${c.id}' refers to unknown object '${id}'`);
      else if (!anchors.get(id)!.includes(anchor)) errors.push(`system: connection '${c.id}' refers to unknown anchor '${end}'`);
    }
  }
  const owner = (end: string) => end.split("#")[0];
  for (const f of system.flows ?? []) {
    const path: Json[] = [];
    for (const id of f.path) {
      const c = connections.get(id);
      if (c) path.push(c);
      else errors.push(`system: flow '${f.id}' refers to unknown connection '${id}'`);
    }
    for (let i = 1; i < path.length; i++) {
      const [a, b] = [path[i - 1]!, path[i]!];
      const shared = [a.from, a.to].map(owner).some((x) => [b.from, b.to].map(owner).includes(x));
      if (!shared) errors.push(`system: flow '${f.id}' is broken between '${a.id}' and '${b.id}'`);
    }
  }
  return errors;
}

/** art/assets.json covers every object of the system and each of its representations. */
export function assetsErrors(assets: Json, system: Json): string[] {
  const schema = schemaErrors("assets", assets);
  if (schema.length) return schema;
  const errors: string[] = [];
  for (const o of system.objects) {
    const entry = assets.assets[o.id];
    if (!entry) {
      errors.push(`assets: no model for '${o.id}' in art/assets.json`);
      continue;
    }
    for (const rep of o.representations ?? ["envelope"]) {
      if (!entry[rep]) errors.push(`assets: no '${rep}' script for '${o.id}'`);
    }
  }
  return errors;
}

export function contentErrors(c: V2Content): string[] {
  const errors = [
    ...systemErrors(c.system),
    ...schemaErrors("render", c.render),
    ...schemaErrors("tour", c.tour),
    ...Object.values(c.texts).flatMap((t) => schemaErrors("texts", t)),
    ...schemaErrors("sources", c.sources),
  ];
  if (errors.length) return errors;
  errors.push(...assetsErrors(c.assets, c.system));

  const systemId: string = c.system.id;
  for (const [name, file] of [["render", c.render], ["tour", c.tour], ["sources", c.sources]] as const) {
    if (file.systemId !== systemId) errors.push(`${name}: systemId '${file.systemId}' != '${systemId}'`);
  }
  const objects = new Map<string, Json>(c.system.objects.map((o: Json) => [o.id, o]));
  const main = [...objects.values()].filter((o) => o.role === "main").map((o) => o.id as string);
  const flows = new Set<string>((c.system.flows ?? []).map((f: Json) => f.id));

  // Render: shots on known objects, one per main object, one detail per detailed object, link styles.
  const { shots, linkStyles, lighting } = c.render;
  for (const [key, shot] of Object.entries<Json>(shots)) {
    const target = key.split(":")[1];
    if (target && !objects.has(target)) errors.push(`render: shot '${key}' targets unknown object '${target}'`);
    for (const id of shot.fit) if (!objects.has(id)) errors.push(`render: shot '${key}' fits unknown object '${id}'`);
  }
  for (const id of main) if (!shots[`object:${id}`]) errors.push(`render: no shot 'object:${id}' for main object '${id}'`);
  for (const o of objects.values()) {
    if ((o.representations ?? []).includes("detail") && !shots[`detail:${o.id}`]) errors.push(`render: no shot 'detail:${o.id}'`);
  }
  for (const k of new Set<string>(c.system.connections.map((x: Json) => x.kind))) {
    if (!linkStyles[k]) errors.push(`render: no link style for connection kind '${k}'`);
  }
  const swatches = [lighting.hemisphere.sky, lighting.hemisphere.ground, ...Object.values<Json>(linkStyles).map((s) => s.color)];
  for (const s of swatches) if (!c.palette.has(s)) errors.push(`render: '${s}' is not a palette swatch`);

  // Tour: references, then the narrative rule (system before object).
  const tour = c.tour;
  if (tour.systemId !== systemId) errors.push(`tour: systemId '${tour.systemId}' != '${systemId}'`);
  if (tour.steps[0].focus.kind !== "system") errors.push(`tour: the first step '${tour.steps[0].id}' must be about the system`);
  for (const id of duplicates(tour.steps.map((s: Json) => s.id))) errors.push(`tour: duplicate step '${id}'`);
  const introduced = new Set<string>();
  for (const step of tour.steps) {
    const where = `tour step '${step.id}'`;
    if (!shots[step.shot]) errors.push(`${where}: unknown shot '${step.shot}'`);
    for (const id of step.highlight ?? []) if (!objects.has(id)) errors.push(`${where}: highlights unknown object '${id}'`);
    for (const id of step.flows ?? []) if (!flows.has(id)) errors.push(`${where}: unknown flow '${id}'`);
    if (step.focus.kind === "system") {
      for (const id of step.highlight ?? []) introduced.add(id);
      continue;
    }
    const subject = objects.get(step.focus.id);
    if (!subject) errors.push(`${where}: focus on unknown object '${step.focus.id}'`);
    else if (subject.role !== "main") errors.push(`${where}: focus on '${step.focus.id}', which is not a main object`);
    else if (!introduced.has(subject.id)) errors.push(`${where}: '${subject.id}' is the subject before a system step has highlighted it`);
  }

  // Texts: keys used by the system and tour, one card per main object, figures sourced.
  const facts = new Map<string, Json>(c.sources.facts.map((f: Json) => [f.id, f]));
  for (const [lang, texts] of Object.entries(c.texts)) {
    const where = `texts.${lang}`;
    if (texts.lang !== lang) errors.push(`${where}: lang is '${texts.lang}'`);
    if (texts.systemId !== systemId) errors.push(`${where}: systemId '${texts.systemId}' != '${systemId}'`);
    for (const key of [c.system.titleKey, ...tour.steps.map((s: Json) => s.textKey)]) {
      if (!(key in texts.entries)) errors.push(`${where}: missing key '${key}'`);
    }
    for (const id of main) if (!texts.cards[id]) errors.push(`${where}: no card for main object '${id}'`);
    for (const [id, card] of Object.entries<Json>(texts.cards)) {
      if (!main.includes(id)) errors.push(`${where}: card '${id}' is not a main object`);
      for (const fig of card.figures) {
        const fact = facts.get(fig.factId);
        if (!fact) errors.push(`${where}: card '${id}' cites unknown fact '${fig.factId}'`);
        else if (fact.status === "unverified") errors.push(`${where}: card '${id}' states unverified fact '${fig.factId}'`);
      }
    }
  }

  // Sources: facts cite listed sources.
  const sourceIds = new Set<string>(c.sources.sources.map((s: Json) => s.id));
  for (const id of duplicates(c.sources.facts.map((f: Json) => f.id))) errors.push(`sources: duplicate fact '${id}'`);
  for (const id of duplicates(c.sources.sources.map((s: Json) => s.id))) errors.push(`sources: duplicate source '${id}'`);
  for (const f of c.sources.facts) {
    for (const s of f.sources) if (!sourceIds.has(s)) errors.push(`sources: fact '${f.id}' cites unknown source '${s}'`);
  }
  return errors;
}
