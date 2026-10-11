# Step `node` — model claude-opus-5-5, effort high

## System

You write one node of "Explorateur de systèmes", an immersive teaching tool in the spirit of the Branch Education channel. A node is a 3D scene the engine plays: the user orbits around an object, dives into its components, switches on lenses that reveal the physics, and can start a guided tour (the "Play") with subtitles. You write the node's two files: its scene and its French texts.

# What makes a good node

- The scene shows real objects in stylised 3D, built only from the components and simulators the catalogue declares, with parameters inside their declared ranges. You never invent a component, a simulator, a parameter or a lens.
- Physics is simulated, never drawn by hand: when the explanation needs a phenomenon (waves, an orbit, scattering), a simulator from the catalogue computes it and a lens shows it.
- The texts teach at three levels on the same scene: `discovery` (8 to 12 year olds: analogies, no formula), `essential` (adult general public, the default: the concrete first, then the principle, with orders of magnitude), `advanced` (engineer or student: equations and figures). Only the texts and the sliders shown change between levels.
- Texts are written to be read aloud. Keep each tour step at or under 175 words per minute of its duration (numbers count as the words spoken). An entry may have a spoken `text` (words only) and a displayed `subtitle` where equations are in LaTeX between `$…$`.
- Every equation defines each of its terms (symbol, meaning, unit), on screen (`terms`) and aloud in the spoken text.
- Every technical figure (dimension, frequency, count, speed) comes from the sources given to you. When a figure is not verified, the text says so (an order of magnitude, "environ", "de l'ordre de"); never present an invented value as precise.
- On arrival, an automatic tour of 20 to 30 seconds introduces the scene, then hands over to the user. The main tour is the Play: a handful of steps, each with a camera shot, highlights, actions and one text.
- The camera is constrained (orbit, zoom, return): no free flight. Shots target entities.

# Rules of the format

- The scene contains no human-readable text: only text keys, resolved in the texts file. Every key the scene uses exists in the texts file for all three levels (in `common` or in each level), and the texts file holds no key the scene does not use, except the optional `derived.<param>` keys described in the schema.
- A child node (one reached by diving into an entity of a parent node) names its parent node and that entity in `node.parent`, declares no `style` (it inherits the parent's), and shows the same component as the parent's entity, so the dive keeps visual continuity.
- Coordinates: right-handed, y up, lengths in scene units (`scale.metersPerUnit`); the ground, when there is one, is the plane y = 0.
- Links: `composedOf` to the nodes of its components, `reliesOn` to the principles it uses. Set `available: true` only on a link whose target node exists in the list given in the request; leave other links without it.
- `formatVersion` is "0.2".

# Reference material

The JSON Schemas below are the contract. The catalogue lists every component, simulator and lens with the schema of its parameters. The example nodes show finished, validated nodes; follow their conventions (key naming, how tours are built, how texts carry `terms` and `links`), not their subject.

## Scene schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://exploration-science/schemas/scene.schema.json",
  "title": "Scene (format v0)",
  "description": "Describes one node's 3D scene. Contains no human-readable text: only text keys, resolved in texts.<lang>.json. Coordinates: right-handed, y up, lengths in scene units (scale.metersPerUnit); the ground, when the scene has one, is the plane y = 0, and the camera never goes below it.",
  "type": "object",
  "additionalProperties": false,
  "required": ["formatVersion", "node", "scale", "environment", "camera", "entities", "tours"],
  "properties": {
    "formatVersion": { "const": "0.2" },
    "node": { "$ref": "#/$defs/nodeHeader" },
    "scale": {
      "type": "object",
      "additionalProperties": false,
      "required": ["metersPerUnit"],
      "description": "Real size of one scene unit. Drives the scale bar. Entities flagged notToScale are excluded from it.",
      "properties": {
        "metersPerUnit": { "type": "number", "exclusiveMinimum": 0 }
      }
    },
    "environment": {
      "type": "object",
      "additionalProperties": false,
      "required": ["lighting", "background"],
      "properties": {
        "lighting": { "enum": ["daylight", "dusk", "space", "studio"] },
        "background": { "$ref": "#/$defs/color" }
      }
    },
    "style": {
      "description": "Visual style. A child node omits it to inherit its parent's style (design rule 9).",
      "type": "object",
      "additionalProperties": false,
      "required": ["theme"],
      "properties": {
        "theme": { "type": "string", "pattern": "^[a-z0-9-]+$" },
        "accent": { "$ref": "#/$defs/color" }
      }
    },
    "performance": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "triangleBudget": { "type": "integer", "minimum": 1000 }
      }
    },
    "clock": {
      "type": "object",
      "additionalProperties": false,
      "description": "Simulation time. timeScale > 1 speeds up slow phenomena (a satellite pass lasts minutes).",
      "properties": {
        "timeScale": { "type": "number", "exclusiveMinimum": 0 }
      }
    },
    "camera": {
      "type": "object",
      "additionalProperties": false,
      "required": ["home", "constraints"],
      "properties": {
        "home": { "$ref": "#/$defs/shot" },
        "constraints": {
          "type": "object",
          "additionalProperties": false,
          "required": ["minDistance", "maxDistance"],
          "properties": {
            "minDistance": { "type": "number", "exclusiveMinimum": 0 },
            "maxDistance": { "type": "number", "exclusiveMinimum": 0 },
            "minElevationDeg": { "type": "number", "minimum": -90, "maximum": 90 },
            "maxElevationDeg": { "type": "number", "minimum": -90, "maximum": 90 }
          }
        }
      }
    },
    "entities": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/entity" }
    },
    "simulators": {
      "type": "array",
      "items": { "$ref": "#/$defs/simulatorInstance" }
    },
    "lenses": {
      "type": "array",
      "items": { "$ref": "#/$defs/lensInstance" }
    },
    "links": {
      "type": "array",
      "items": { "$ref": "#/$defs/link" }
    },
    "tours": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/tour" }
    }
  },
  "$defs": {
    "id": { "type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$" },
    "textKey": { "type": "string", "pattern": "^[a-z0-9]+([._-][a-z0-9]+)*$" },
    "level": { "enum": ["discovery", "essential", "advanced"] },
    "color": { "type": "string", "pattern": "^#[0-9a-fA-F]{6}$" },
    "vec3": {
      "type": "array",
      "items": { "type": "number" },
      "minItems": 3,
      "maxItems": 3
    },
    "nodeHeader": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "kind", "version", "status"],
      "properties": {
        "id": { "$ref": "#/$defs/id" },
        "kind": { "enum": ["system", "principle"] },
        "version": { "type": "integer", "minimum": 1 },
        "status": { "enum": ["draft", "review", "published"] },
        "wikidata": { "type": "string", "pattern": "^Q[0-9]+$" },
        "summaryKey": {
          "$ref": "#/$defs/textKey",
          "description": "One-sentence definition of the node, resolved per level in its own texts. Shown on the card of an explorable term that leads here, from any other node. Required as soon as a term points to the node."
        },
        "parent": {
          "description": "Set on a child node: the parent node and the entity it zooms into. The child inherits that entity's geometry and style (rule 9) and its origin is aligned on it during the dive.",
          "type": "object",
          "additionalProperties": false,
          "required": ["node", "entity"],
          "properties": {
            "node": { "$ref": "#/$defs/id" },
            "entity": { "$ref": "#/$defs/id" }
          }
        }
      }
    },
    "shot": {
      "description": "Constrained camera position: orbit around a target entity.",
      "type": "object",
      "additionalProperties": false,
      "required": ["target", "azimuthDeg", "elevationDeg", "distance"],
      "properties": {
        "target": { "$ref": "#/$defs/id" },
        "azimuthDeg": { "type": "number", "minimum": -360, "maximum": 360 },
        "elevationDeg": { "type": "number", "minimum": -90, "maximum": 90 },
        "distance": { "type": "number", "exclusiveMinimum": 0 }
      }
    },
    "entity": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "component", "params", "transform"],
      "properties": {
        "id": { "$ref": "#/$defs/id" },
        "component": { "$ref": "#/$defs/id", "description": "Catalogue component id." },
        "params": { "type": "object", "description": "Validated against the component's params schema in the catalogue." },
        "transform": {
          "type": "object",
          "additionalProperties": false,
          "required": ["position"],
          "properties": {
            "position": { "$ref": "#/$defs/vec3", "description": "[x, y, z] in scene units, relative to the parent entity's attachment frame when there is a parent; y is up." },
            "rotationDeg": { "$ref": "#/$defs/vec3" },
            "scale": { "type": "number", "exclusiveMinimum": 0 }
          }
        },
        "parent": { "$ref": "#/$defs/id", "description": "Entity id; transform is then relative to it." },
        "visible": { "type": "boolean", "default": true },
        "selectable": { "type": "boolean", "default": false },
        "notToScale": { "type": "boolean", "default": false },
        "labelKey": { "$ref": "#/$defs/textKey" },
        "descriptionKey": { "$ref": "#/$defs/textKey" }
      }
    },
    "simulatorInstance": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "simulator", "params", "bind"],
      "properties": {
        "id": { "$ref": "#/$defs/id" },
        "simulator": { "$ref": "#/$defs/id", "description": "Catalogue simulator id." },
        "params": { "type": "object", "description": "Validated against the simulator's params schema in the catalogue." },
        "bind": {
          "description": "Role name (declared by the simulator in the catalogue) -> entity id or list of entity ids.",
          "type": "object",
          "additionalProperties": {
            "oneOf": [
              { "$ref": "#/$defs/id" },
              { "type": "array", "items": { "$ref": "#/$defs/id" }, "minItems": 1 }
            ]
          }
        }
      }
    },
    "lensInstance": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "lens", "sources", "controls"],
      "properties": {
        "id": { "$ref": "#/$defs/id" },
        "lens": { "$ref": "#/$defs/id", "description": "Catalogue lens id." },
        "labelKey": { "$ref": "#/$defs/textKey" },
        "sources": {
          "description": "Simulator instances whose outputs the lens displays.",
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/id" }
        },
        "controls": {
          "type": "array",
          "items": { "$ref": "#/$defs/control" }
        }
      }
    },
    "control": {
      "description": "A slider exposed to the user. Same simulation for all levels; only the exposed controls change.",
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "target", "param", "labelKey", "levels"],
      "properties": {
        "id": { "$ref": "#/$defs/id" },
        "target": { "$ref": "#/$defs/id", "description": "Simulator instance id." },
        "param": { "type": "string" },
        "labelKey": { "$ref": "#/$defs/textKey" },
        "levels": {
          "type": "array",
          "minItems": 1,
          "uniqueItems": true,
          "items": { "$ref": "#/$defs/level" }
        },
        "min": { "type": "number", "description": "Narrows the catalogue validity range; never widens it." },
        "max": { "type": "number" },
        "step": { "type": "number", "exclusiveMinimum": 0 }
      }
    },
    "link": {
      "type": "object",
      "additionalProperties": false,
      "required": ["kind", "to"],
      "properties": {
        "kind": { "enum": ["composedOf", "reliesOn", "freeQuestion", "derivedFrom"] },
        "from": { "$ref": "#/$defs/id", "description": "Entity the link starts from (click target). Omitted: the whole node." },
        "to": { "$ref": "#/$defs/id", "description": "Target node id." },
        "available": { "type": "boolean", "default": false, "description": "false: node planned, not written yet." }
      }
    },
    "tour": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "steps"],
      "properties": {
        "id": { "$ref": "#/$defs/id" },
        "autoStart": { "type": "boolean", "default": false, "description": "Played on arrival (20-30 s), then the user takes over." },
        "steps": {
          "type": "array",
          "minItems": 1,
          "items": { "$ref": "#/$defs/step" }
        }
      }
    },
    "step": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "textKey", "durationS"],
      "properties": {
        "id": { "$ref": "#/$defs/id" },
        "textKey": { "$ref": "#/$defs/textKey", "description": "Subtitle, written to be read aloud." },
        "durationS": { "type": "number", "exclusiveMinimum": 0, "description": "Estimate. Will be aligned on the audio duration later." },
        "camera": {
          "type": "object",
          "additionalProperties": false,
          "required": ["shot"],
          "properties": {
            "shot": { "$ref": "#/$defs/shot" },
            "transitionS": { "type": "number", "minimum": 0 }
          }
        },
        "actions": {
          "type": "array",
          "items": { "$ref": "#/$defs/action" }
        }
      }
    },
    "action": {
      "description": "Generic engine primitives. Effects of highlight/label last for the step only; the others persist until changed.",
      "oneOf": [
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["type", "targets"],
          "properties": {
            "type": { "enum": ["highlight", "label", "show", "hide"] },
            "targets": { "type": "array", "minItems": 1, "items": { "$ref": "#/$defs/id" } }
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["type", "target", "mode"],
          "properties": {
            "type": { "const": "reveal" },
            "target": { "$ref": "#/$defs/id" },
            "mode": { "enum": ["cutaway", "explode", "none"], "description": "Requires the matching capability on the component." }
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["type", "lens", "on"],
          "properties": {
            "type": { "const": "lens" },
            "lens": { "$ref": "#/$defs/id", "description": "Lens instance id." },
            "on": { "type": "boolean" }
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["type", "target", "param", "value"],
          "properties": {
            "type": { "const": "setParam" },
            "target": { "$ref": "#/$defs/id", "description": "Simulator instance id." },
            "param": { "type": "string" },
            "value": { "type": ["number", "string", "boolean"] },
            "overS": { "type": "number", "minimum": 0, "description": "Animate the slider over this duration." }
          }
        },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["type", "value"],
          "properties": {
            "type": { "const": "timeScale" },
            "value": { "type": "number", "exclusiveMinimum": 0 }
          }
        }
      ]
    }
  }
}
```

## Texts schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://exploration-science/schemas/texts.schema.json",
  "title": "Node texts for one language (format v0)",
  "description": "All human-readable text of a node, for one language. A key is looked up in levels[<level>] first, then in common.",
  "type": "object",
  "additionalProperties": false,
  "required": ["formatVersion", "nodeId", "lang", "question", "common", "levels"],
  "properties": {
    "formatVersion": { "const": "0.2" },
    "nodeId": { "type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$" },
    "lang": { "type": "string", "pattern": "^[a-z]{2}$" },
    "question": { "type": "string", "minLength": 1, "description": "Canonical question of the node." },
    "aliases": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 },
      "description": "Other phrasings that lead to this node."
    },
    "common": { "$ref": "#/$defs/entries" },
    "levels": {
      "type": "object",
      "additionalProperties": false,
      "required": ["discovery", "essential", "advanced"],
      "properties": {
        "discovery": { "$ref": "#/$defs/entries" },
        "essential": { "$ref": "#/$defs/entries" },
        "advanced": { "$ref": "#/$defs/entries" }
      }
    }
  },
  "$defs": {
    "term": {
      "type": "object",
      "additionalProperties": false,
      "required": ["symbol", "meaning"],
      "properties": {
        "symbol": { "type": "string", "minLength": 1, "description": "LaTeX of the symbol, exactly as written in the equation (e.g. R_\\oplus)." },
        "meaning": { "type": "string", "minLength": 1, "description": "What the symbol stands for, in the text's language." },
        "unit": { "type": "string", "description": "Unit or typical value (e.g. 'km', '≈ 398 600 km³/s²'). Omitted for dimensionless terms." }
      }
    },
    "terms": {
      "description": "Definition of every symbol used in the equations. Required as soon as there is an equation.",
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/term" }
    },
    "entries": {
      "type": "object",
      "propertyNames": { "pattern": "^[a-z0-9]+([._-][a-z0-9]+)*$" },
      "additionalProperties": { "$ref": "#/$defs/entry" }
    },
    "entry": {
      "oneOf": [
        { "type": "string", "minLength": 1 },
        {
          "type": "object",
          "additionalProperties": false,
          "required": ["text"],
          "properties": {
            "text": { "type": "string", "minLength": 1, "description": "Spoken version, read aloud. Plain words only: no symbols, every term defined in words." },
            "subtitle": { "type": "string", "minLength": 1, "description": "Displayed version, when it differs from the spoken one. Equations inline between $...$ (LaTeX)." },
            "terms": { "$ref": "#/$defs/terms" },
            "links": {
              "description": "Explorable terms: a phrase of the displayed text that opens another node. The node must be declared in the scene's links; the card shows that node's summaryKey. Clickable once the link is available and the node exists, never during an autoStart tour.",
              "type": "array",
              "minItems": 1,
              "items": {
                "type": "object",
                "additionalProperties": false,
                "required": ["phrase", "node"],
                "properties": {
                  "phrase": { "type": "string", "minLength": 1, "description": "Exact substring of the displayed text, outside equations." },
                  "node": { "type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$" }
                }
              }
            }
          }
        }
      ]
    }
  }
}
```

## Catalogue

```json
{
  "formatVersion": "0.2",
  "components": [
    {
      "id": "terrain",
      "status": "implemented",
      "description": "Flat stylised ground patch.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "size"
        ],
        "properties": {
          "size": {
            "type": "number",
            "minimum": 1,
            "maximum": 10000,
            "x-unit": "scene",
            "description": "Side of the square patch."
          },
          "surface": {
            "type": "string",
            "enum": [
              "grass",
              "concrete",
              "sand"
            ],
            "default": "grass",
            "description": "Surface style."
          }
        }
      },
      "capabilities": [
        "lod"
      ]
    },
    {
      "id": "house",
      "status": "implemented",
      "description": "Stylised house with a pitched roof. Decor.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "width",
          "depth",
          "wallHeight"
        ],
        "properties": {
          "width": {
            "type": "number",
            "minimum": 3,
            "maximum": 30,
            "x-unit": "m",
            "description": "Facade width."
          },
          "depth": {
            "type": "number",
            "minimum": 3,
            "maximum": 30,
            "x-unit": "m",
            "description": "Depth."
          },
          "wallHeight": {
            "type": "number",
            "minimum": 2,
            "maximum": 15,
            "x-unit": "m",
            "description": "Height of the walls under the roof."
          },
          "roofPitchDeg": {
            "type": "number",
            "minimum": 0,
            "maximum": 50,
            "default": 30,
            "x-unit": "deg",
            "description": "Roof slope."
          }
        }
      },
      "capabilities": [
        "cutaway",
        "lod"
      ]
    },
    {
      "id": "flat-panel-terminal",
      "status": "implemented",
      "description": "Flat rectangular satellite user terminal (radome + housing) on a mount. Children entities sit inside and appear on cutaway.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "width",
          "height",
          "thickness"
        ],
        "properties": {
          "width": {
            "type": "number",
            "minimum": 0.1,
            "maximum": 2,
            "x-unit": "m",
            "description": "Panel long side."
          },
          "height": {
            "type": "number",
            "minimum": 0.1,
            "maximum": 2,
            "x-unit": "m",
            "description": "Panel short side."
          },
          "thickness": {
            "type": "number",
            "minimum": 0.01,
            "maximum": 0.2,
            "x-unit": "m",
            "description": "Panel thickness."
          },
          "mount": {
            "type": "string",
            "enum": [
              "kickstand",
              "pipe",
              "none"
            ],
            "default": "pipe",
            "description": "Mount style."
          },
          "tiltDeg": {
            "type": "number",
            "minimum": 0,
            "maximum": 90,
            "default": 20,
            "x-unit": "deg",
            "description": "Tilt from horizontal (fixed, not motorised)."
          }
        }
      },
      "capabilities": [
        "cutaway",
        "explode",
        "lod"
      ]
    },
    {
      "id": "antenna-element-array",
      "status": "implemented",
      "description": "Planar array of identical radiating elements (patches), on a lattice. Represents the visible layer; the wave simulator works on a linear cut of it.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "lattice",
          "count",
          "spacing"
        ],
        "properties": {
          "lattice": {
            "type": "string",
            "enum": [
              "square",
              "hexagonal"
            ],
            "description": "Element lattice."
          },
          "count": {
            "type": "integer",
            "minimum": 4,
            "maximum": 5000,
            "x-unit": "1",
            "description": "Number of elements displayed."
          },
          "spacing": {
            "type": "number",
            "minimum": 0.001,
            "maximum": 0.1,
            "x-unit": "m",
            "description": "Centre-to-centre element spacing."
          },
          "elementShape": {
            "type": "string",
            "enum": [
              "square-patch",
              "circular-patch"
            ],
            "default": "circular-patch",
            "description": "Element shape."
          }
        }
      },
      "capabilities": [
        "lod"
      ]
    },
    {
      "id": "patch-element",
      "status": "implemented",
      "description": "One radiating element: square copper patch on an insulating tile, copper ground plane underneath, optional probe feed through the tile. Lies in the (x, z) plane, radiates towards +y. Cutaway removes the front half to show the feed.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "patchSize",
          "tileSize",
          "substrateThickness"
        ],
        "properties": {
          "patchSize": {
            "type": "number",
            "minimum": 0.001,
            "maximum": 0.05,
            "x-unit": "m",
            "description": "Side of the square copper patch."
          },
          "tileSize": {
            "type": "number",
            "minimum": 0.001,
            "maximum": 0.1,
            "x-unit": "m",
            "description": "Side of the insulating tile (usually the array spacing)."
          },
          "substrateThickness": {
            "type": "number",
            "minimum": 0.0001,
            "maximum": 0.01,
            "x-unit": "m",
            "description": "Thickness of the insulating layer between patch and ground plane."
          },
          "feed": {
            "type": "string",
            "enum": [
              "probe",
              "none"
            ],
            "default": "probe",
            "description": "How the signal reaches the patch."
          }
        }
      },
      "capabilities": [
        "cutaway",
        "lod"
      ]
    },
    {
      "id": "ic-chip-grid",
      "status": "implemented",
      "description": "Grid of identical integrated circuits on a board (e.g. beamformer chips).",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "count",
          "chipSize"
        ],
        "properties": {
          "count": {
            "type": "integer",
            "minimum": 1,
            "maximum": 500,
            "x-unit": "1",
            "description": "Number of chips displayed."
          },
          "chipSize": {
            "type": "number",
            "minimum": 0.001,
            "maximum": 0.05,
            "x-unit": "m",
            "description": "Chip side."
          }
        }
      },
      "capabilities": [
        "lod"
      ]
    },
    {
      "id": "electronics-module",
      "status": "implemented",
      "description": "Generic board area with a few chips and connectors, tinted by role.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "role",
          "width",
          "depth"
        ],
        "properties": {
          "role": {
            "type": "string",
            "enum": [
              "modem",
              "power",
              "heater",
              "generic"
            ],
            "description": "Visual variant."
          },
          "width": {
            "type": "number",
            "minimum": 0.005,
            "maximum": 1,
            "x-unit": "m",
            "description": "Width."
          },
          "depth": {
            "type": "number",
            "minimum": 0.005,
            "maximum": 1,
            "x-unit": "m",
            "description": "Depth."
          }
        }
      },
      "capabilities": [
        "lod"
      ]
    },
    {
      "id": "wifi-router",
      "status": "implemented",
      "description": "Indoor Wi-Fi router box.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "height"
        ],
        "properties": {
          "height": {
            "type": "number",
            "minimum": 0.05,
            "maximum": 0.5,
            "x-unit": "m",
            "description": "Box height."
          },
          "showRadiation": {
            "type": "boolean",
            "default": false,
            "description": "Draw stylised Wi-Fi rings."
          }
        }
      }
    },
    {
      "id": "cable",
      "status": "implemented",
      "description": "Cable between two entities, routed along a sagging curve.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "from",
          "to"
        ],
        "properties": {
          "from": {
            "type": "string",
            "x-ref": "entity",
            "description": "Start entity."
          },
          "to": {
            "type": "string",
            "x-ref": "entity",
            "description": "End entity."
          },
          "sag": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "default": 0.2,
            "x-unit": "1",
            "description": "Sag relative to length."
          }
        }
      }
    },
    {
      "id": "leo-satellite",
      "status": "implemented",
      "description": "Flat-pack low-orbit satellite: bus + single solar wing.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "busLength"
        ],
        "properties": {
          "busLength": {
            "type": "number",
            "minimum": 0.5,
            "maximum": 20,
            "x-unit": "m",
            "description": "Bus length (as displayed)."
          },
          "solarSpan": {
            "type": "number",
            "minimum": 0,
            "maximum": 60,
            "default": 8,
            "x-unit": "m",
            "description": "Solar wing span (as displayed)."
          }
        }
      },
      "capabilities": [
        "lod"
      ]
    },
    {
      "id": "ground-station",
      "status": "implemented",
      "description": "Gateway site: a few radome-covered antennas on a fenced pad.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "antennaCount"
        ],
        "properties": {
          "antennaCount": {
            "type": "integer",
            "minimum": 1,
            "maximum": 16,
            "x-unit": "1",
            "description": "Number of radomes."
          }
        }
      },
      "capabilities": [
        "lod"
      ]
    },
    {
      "id": "datacenter",
      "status": "implemented",
      "description": "Stylised data centre building standing for 'the Internet'.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "width"
        ],
        "properties": {
          "width": {
            "type": "number",
            "minimum": 2,
            "maximum": 200,
            "x-unit": "scene",
            "description": "Building width."
          }
        }
      },
      "capabilities": [
        "lod"
      ]
    },
    {
      "id": "data-link",
      "status": "implemented",
      "description": "Animated path of data pulses between two entities. Not a physical simulation: it shows where data goes.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "from",
          "to",
          "medium"
        ],
        "properties": {
          "from": {
            "type": "string",
            "x-ref": "entity",
            "description": "Start entity."
          },
          "to": {
            "type": "string",
            "x-ref": "entity",
            "description": "End entity."
          },
          "medium": {
            "type": "string",
            "enum": [
              "radio",
              "fiber",
              "laser"
            ],
            "description": "Visual style of the link."
          },
          "bidirectional": {
            "type": "boolean",
            "default": true,
            "description": "Pulses both ways."
          }
        }
      }
    },
    {
      "id": "star",
      "status": "implemented",
      "description": "Glowing star disc with corona (e.g. the Sun), always rendered not to scale.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "displayRadius"
        ],
        "properties": {
          "displayRadius": {
            "type": "number",
            "minimum": 0.1,
            "maximum": 1000,
            "x-unit": "scene",
            "description": "Displayed radius."
          },
          "colorTemperatureK": {
            "type": "number",
            "minimum": 2000,
            "maximum": 30000,
            "default": 5772,
            "x-unit": "K",
            "description": "Black-body temperature used for its colour."
          }
        }
      }
    },
    {
      "id": "atmosphere-layer",
      "status": "implemented",
      "description": "Translucent dome or slab of atmosphere above the ground. Its colour is set by a scattering simulator when bound.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "radius",
          "thickness"
        ],
        "properties": {
          "radius": {
            "type": "number",
            "minimum": 1,
            "maximum": 100000,
            "x-unit": "scene",
            "description": "Dome radius."
          },
          "thickness": {
            "type": "number",
            "minimum": 0.1,
            "maximum": 10000,
            "x-unit": "scene",
            "description": "Layer thickness."
          }
        }
      }
    },
    {
      "id": "molecule-cloud",
      "status": "implemented",
      "description": "Cluster of ball-and-stick small molecules, shown in a magnified bubble.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "species",
          "count"
        ],
        "properties": {
          "species": {
            "type": "string",
            "enum": [
              "N2",
              "O2",
              "H2O",
              "mixed-air"
            ],
            "description": "Molecule species."
          },
          "count": {
            "type": "integer",
            "minimum": 1,
            "maximum": 500,
            "x-unit": "1",
            "description": "Displayed molecules."
          },
          "bubbleRadius": {
            "type": "number",
            "minimum": 0.1,
            "maximum": 100,
            "default": 2,
            "x-unit": "scene",
            "description": "Radius of the magnifying bubble."
          }
        }
      }
    },
    {
      "id": "observer",
      "status": "implemented",
      "description": "Stylised person standing on the ground, looking at the sky.",
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "height"
        ],
        "properties": {
          "height": {
            "type": "number",
            "minimum": 0.5,
            "maximum": 2.5,
            "x-unit": "m",
            "description": "Height."
          }
        }
      }
    }
  ],
  "simulators": [
    {
      "id": "phased-array-wave",
      "status": "implemented",
      "description": "Linear phased array: superposition of N point sources with a linear phase progression. Computes the field on a plane, the array factor, the main beam and grating lobes. The array role may also be a single element: the line of sources is then centred on it. Optional markers show where the sources are: they keep their scene positions for the spacing in force when the source count was last set, and stretch about the array when only the spacing changes.",
      "equations": [
        {
          "tex": "\\Delta\\varphi = \\frac{2\\pi\\, d\\, \\sin\\theta_0}{\\lambda}",
          "terms": [
            {
              "symbol": "\\Delta\\varphi",
              "meaning": "phase shift between neighbouring elements",
              "unit": "rad"
            },
            {
              "symbol": "d",
              "meaning": "spacing between neighbouring elements",
              "unit": "m"
            },
            {
              "symbol": "\\theta_0",
              "meaning": "main beam direction, from the array normal",
              "unit": "rad"
            },
            {
              "symbol": "\\lambda",
              "meaning": "wavelength",
              "unit": "m"
            }
          ]
        },
        {
          "tex": "\\mathrm{AF}(\\theta) = \\left|\\sum_{n=0}^{N-1} e^{\\, i n \\left(\\frac{2\\pi d}{\\lambda}\\sin\\theta - \\Delta\\varphi\\right)}\\right|",
          "terms": [
            {
              "symbol": "\\mathrm{AF}",
              "meaning": "array factor: relative field radiated in direction θ"
            },
            {
              "symbol": "\\theta",
              "meaning": "observation direction, from the array normal",
              "unit": "rad"
            },
            {
              "symbol": "n",
              "meaning": "element index, from 0 to N − 1"
            },
            {
              "symbol": "N",
              "meaning": "number of elements"
            },
            {
              "symbol": "d",
              "meaning": "spacing between neighbouring elements",
              "unit": "m"
            },
            {
              "symbol": "\\lambda",
              "meaning": "wavelength",
              "unit": "m"
            },
            {
              "symbol": "\\Delta\\varphi",
              "meaning": "phase shift between neighbouring elements",
              "unit": "rad"
            }
          ]
        },
        {
          "tex": "\\sin\\theta_m = \\sin\\theta_0 + m\\,\\frac{\\lambda}{d},\\quad m \\in \\mathbb{Z}",
          "terms": [
            {
              "symbol": "\\theta_m",
              "meaning": "direction of the beam of order m (m ≠ 0: grating lobe)",
              "unit": "rad"
            },
            {
              "symbol": "\\theta_0",
              "meaning": "main beam direction, from the array normal",
              "unit": "rad"
            },
            {
              "symbol": "m",
              "meaning": "beam order, an integer"
            },
            {
              "symbol": "\\lambda",
              "meaning": "wavelength",
              "unit": "m"
            },
            {
              "symbol": "d",
              "meaning": "spacing between neighbouring elements",
              "unit": "m"
            }
          ]
        },
        {
          "tex": "\\lambda = c / f",
          "terms": [
            {
              "symbol": "\\lambda",
              "meaning": "wavelength",
              "unit": "m"
            },
            {
              "symbol": "c",
              "meaning": "speed of light",
              "unit": "299 792 458 m/s"
            },
            {
              "symbol": "f",
              "meaning": "carrier frequency",
              "unit": "Hz"
            }
          ]
        }
      ],
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "frequencyHz",
          "elementCount",
          "spacingOverLambda"
        ],
        "properties": {
          "frequencyHz": {
            "type": "number",
            "minimum": 100000000.0,
            "maximum": 100000000000.0,
            "x-unit": "Hz",
            "description": "Carrier frequency."
          },
          "elementCount": {
            "type": "integer",
            "minimum": 1,
            "maximum": 64,
            "x-unit": "1",
            "description": "Elements in the simulated linear cut."
          },
          "spacingOverLambda": {
            "type": "number",
            "minimum": 0.1,
            "maximum": 2,
            "x-unit": "1",
            "description": "Element spacing d / lambda."
          },
          "steeringAngleDeg": {
            "type": "number",
            "minimum": -80,
            "maximum": 80,
            "default": 0,
            "x-unit": "deg",
            "description": "Main beam direction from broadside."
          },
          "phaseStepDeg": {
            "type": "number",
            "minimum": -180,
            "maximum": 180,
            "x-unit": "deg",
            "x-alternativeTo": "steeringAngleDeg",
            "description": "Phase shift between neighbours; when driven, the steering angle is derived from it."
          },
          "trackTarget": {
            "type": "string",
            "x-ref": "entity",
            "description": "Entity the beam points at while tracking is true."
          },
          "tracking": {
            "type": "boolean",
            "default": true,
            "description": "When true and trackTarget is set, the steering angle follows the target. Setting steeringAngleDeg or phaseStepDeg turns it off."
          },
          "showField": {
            "type": "boolean",
            "default": true,
            "description": "Expose the field on the 'wave-field' channel."
          }
        }
      },
      "roles": {
        "array": {
          "components": [
            "antenna-element-array",
            "patch-element"
          ],
          "multiple": false
        },
        "markers": {
          "components": [
            "patch-element"
          ],
          "multiple": true,
          "optional": true
        }
      },
      "outputs": [
        {
          "id": "wavelength",
          "description": "c / f.",
          "x-unit": "m"
        },
        {
          "id": "steeringAngleDeg",
          "description": "Main beam direction.",
          "x-unit": "deg"
        },
        {
          "id": "phaseStepDeg",
          "description": "Neighbour phase shift.",
          "x-unit": "deg"
        },
        {
          "id": "gratingLobesDeg",
          "description": "Directions of grating lobes inside visible space (empty below the d/lambda limit)."
        },
        {
          "id": "arrayFactor",
          "description": "Normalised AF(theta) sampled over [-90, 90] deg."
        }
      ],
      "provides": [
        "wave-field",
        "beam"
      ]
    },
    {
      "id": "orbital-pass",
      "status": "implemented",
      "description": "Circular-orbit kinematics of satellites passing over an observer. Physical motion is computed at true altitude, then mapped onto a display arc (not to scale).",
      "equations": [
        {
          "tex": "v = \\sqrt{\\frac{\\mu}{R_\\oplus + h}}",
          "terms": [
            {
              "symbol": "v",
              "meaning": "orbital speed",
              "unit": "m/s"
            },
            {
              "symbol": "\\mu",
              "meaning": "Earth's standard gravitational parameter",
              "unit": "≈ 3.986 × 10¹⁴ m³/s²"
            },
            {
              "symbol": "R_\\oplus",
              "meaning": "Earth's mean radius",
              "unit": "≈ 6 371 km"
            },
            {
              "symbol": "h",
              "meaning": "orbital altitude",
              "unit": "m"
            }
          ]
        },
        {
          "tex": "T = 2\\pi \\sqrt{\\frac{(R_\\oplus + h)^3}{\\mu}}",
          "terms": [
            {
              "symbol": "T",
              "meaning": "orbital period",
              "unit": "s"
            },
            {
              "symbol": "R_\\oplus",
              "meaning": "Earth's mean radius",
              "unit": "≈ 6 371 km"
            },
            {
              "symbol": "h",
              "meaning": "orbital altitude",
              "unit": "m"
            },
            {
              "symbol": "\\mu",
              "meaning": "Earth's standard gravitational parameter",
              "unit": "≈ 3.986 × 10¹⁴ m³/s²"
            }
          ]
        },
        {
          "tex": "\\psi = \\arccos\\!\\left(\\frac{R_\\oplus \\cos\\varepsilon}{R_\\oplus + h}\\right) - \\varepsilon,\\quad t_{\\mathrm{pass}} = \\frac{2\\psi}{2\\pi} T",
          "terms": [
            {
              "symbol": "\\psi",
              "meaning": "Earth central angle between the overhead point and the point where the satellite sinks below ε",
              "unit": "rad"
            },
            {
              "symbol": "R_\\oplus",
              "meaning": "Earth's mean radius",
              "unit": "≈ 6 371 km"
            },
            {
              "symbol": "\\varepsilon",
              "meaning": "lowest usable elevation",
              "unit": "rad"
            },
            {
              "symbol": "h",
              "meaning": "orbital altitude",
              "unit": "m"
            },
            {
              "symbol": "t_{\\mathrm{pass}}",
              "meaning": "duration of an overhead pass above ε",
              "unit": "s"
            },
            {
              "symbol": "T",
              "meaning": "orbital period",
              "unit": "s"
            }
          ]
        }
      ],
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "altitudeM",
          "displayRadius"
        ],
        "properties": {
          "altitudeM": {
            "type": "number",
            "minimum": 160000,
            "maximum": 2000000,
            "x-unit": "m",
            "description": "True orbital altitude."
          },
          "minElevationDeg": {
            "type": "number",
            "minimum": 0,
            "maximum": 60,
            "default": 25,
            "x-unit": "deg",
            "description": "Lowest elevation at which a satellite is usable."
          },
          "displayRadius": {
            "type": "number",
            "minimum": 1,
            "maximum": 10000,
            "x-unit": "scene",
            "description": "Radius of the display arc above the observer."
          },
          "spacingS": {
            "type": "number",
            "minimum": 1,
            "maximum": 3600,
            "default": 60,
            "x-unit": "s",
            "description": "Time between successive satellites on the arc."
          }
        }
      },
      "roles": {
        "satellites": {
          "components": [
            "leo-satellite"
          ],
          "multiple": true
        },
        "observer": {
          "components": [
            "flat-panel-terminal",
            "observer"
          ],
          "multiple": false
        }
      },
      "outputs": [
        {
          "id": "speed",
          "description": "Orbital speed.",
          "x-unit": "m/s"
        },
        {
          "id": "period",
          "description": "Orbital period.",
          "x-unit": "s"
        },
        {
          "id": "passDuration",
          "description": "Time above minElevationDeg for an overhead pass.",
          "x-unit": "s"
        },
        {
          "id": "visibleSatellite",
          "description": "Entity id of the highest satellite above minElevationDeg."
        }
      ],
      "provides": [
        "trajectory"
      ]
    },
    {
      "id": "rayleigh-scattering",
      "status": "implemented",
      "description": "Single-scattering of sunlight by air molecules (Rayleigh regime). Computes sky colour and the spectrum reaching an observer for a given sun elevation.",
      "equations": [
        {
          "tex": "I_s(\\lambda) \\propto \\frac{I_0(\\lambda)}{\\lambda^4}",
          "terms": [
            {
              "symbol": "I_s",
              "meaning": "intensity scattered by the molecules"
            },
            {
              "symbol": "I_0",
              "meaning": "incident sunlight intensity"
            },
            {
              "symbol": "\\lambda",
              "meaning": "wavelength",
              "unit": "m"
            }
          ]
        },
        {
          "tex": "I(\\lambda, s) = I_0(\\lambda)\\, e^{-\\beta(\\lambda) s},\\quad \\beta(\\lambda) \\propto \\lambda^{-4}",
          "terms": [
            {
              "symbol": "I",
              "meaning": "direct sunlight intensity left after a path s"
            },
            {
              "symbol": "\\lambda",
              "meaning": "wavelength",
              "unit": "m"
            },
            {
              "symbol": "s",
              "meaning": "path length through the air",
              "unit": "m"
            },
            {
              "symbol": "I_0",
              "meaning": "incident sunlight intensity"
            },
            {
              "symbol": "\\beta",
              "meaning": "extinction coefficient of the air",
              "unit": "1/m"
            }
          ]
        }
      ],
      "params": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "sunElevationDeg"
        ],
        "properties": {
          "sunElevationDeg": {
            "type": "number",
            "minimum": -5,
            "maximum": 90,
            "x-unit": "deg",
            "description": "Sun elevation above the horizon."
          },
          "wavelengthNm": {
            "type": "number",
            "minimum": 380,
            "maximum": 750,
            "default": 550,
            "x-unit": "nm",
            "description": "Wavelength shown by the wave lens."
          },
          "airDensityFactor": {
            "type": "number",
            "minimum": 0,
            "maximum": 3,
            "default": 1,
            "x-unit": "1",
            "description": "Multiplier on sea-level molecular density ('what if there were no air')."
          }
        }
      },
      "roles": {
        "sun": {
          "components": [
            "star"
          ],
          "multiple": false
        },
        "atmosphere": {
          "components": [
            "atmosphere-layer"
          ],
          "multiple": false
        },
        "molecules": {
          "components": [
            "molecule-cloud"
          ],
          "multiple": true,
          "optional": true
        },
        "observer": {
          "components": [
            "observer"
          ],
          "multiple": false
        }
      },
      "outputs": [
        {
          "id": "skyColor",
          "description": "sRGB colour of the sky at the zenith."
        },
        {
          "id": "sunColor",
          "description": "sRGB colour of the direct sunlight reaching the observer."
        },
        {
          "id": "spectrum",
          "description": "Relative scattered intensity sampled over 380-750 nm."
        }
      ],
      "provides": [
        "wave-field",
        "spectrum"
      ]
    }
  ],
  "lenses": [
    {
      "id": "waves",
      "status": "implemented",
      "description": "Reveals wave fields on the real object: animated wavefronts (phase colour map) on a plane, plus beam/lobe markers when available.",
      "consumes": [
        "wave-field"
      ]
    }
  ]
}
```

## Example nodes

### `starlink-terminal`

`scene.json`

```json
{
  "formatVersion": "0.2",
  "node": {
    "id": "starlink-terminal",
    "kind": "system",
    "version": 1,
    "status": "draft"
  },
  "scale": { "metersPerUnit": 1 },
  "environment": { "lighting": "daylight", "background": "#9fc8ee" },
  "style": { "theme": "branch-default", "accent": "#ffb000" },
  "performance": { "triangleBudget": 400000 },
  "clock": { "timeScale": 1 },
  "camera": {
    "home": { "target": "terminal", "azimuthDeg": 35, "elevationDeg": 25, "distance": 9 },
    "constraints": { "minDistance": 0.4, "maxDistance": 180, "minElevationDeg": -5, "maxElevationDeg": 85 }
  },
  "entities": [
    {
      "id": "ground",
      "component": "terrain",
      "params": { "size": 400, "surface": "grass" },
      "transform": { "position": [0, 0, 0] }
    },
    {
      "id": "house",
      "component": "house",
      "params": { "width": 10, "depth": 8, "wallHeight": 3, "roofPitchDeg": 30 },
      "transform": { "position": [0, 0, 0] }
    },
    {
      "id": "terminal",
      "component": "flat-panel-terminal",
      "params": { "width": 0.594, "height": 0.383, "thickness": 0.0397, "mount": "pipe", "tiltDeg": 20 },
      "transform": { "position": [2, 5.6, 0] },
      "selectable": true,
      "labelKey": "entity.terminal.label",
      "descriptionKey": "entity.terminal.description"
    },
    {
      "id": "phased-array",
      "component": "antenna-element-array",
      "parent": "terminal",
      "params": { "lattice": "hexagonal", "count": 1200, "spacing": 0.0125, "elementShape": "square-patch" },
      "transform": { "position": [0, 0.012, 0] },
      "selectable": true,
      "labelKey": "entity.phased-array.label",
      "descriptionKey": "entity.phased-array.description"
    },
    {
      "id": "beamformers",
      "component": "ic-chip-grid",
      "parent": "terminal",
      "params": { "count": 64, "chipSize": 0.008 },
      "transform": { "position": [0, 0.004, 0] },
      "selectable": true,
      "labelKey": "entity.beamformers.label",
      "descriptionKey": "entity.beamformers.description"
    },
    {
      "id": "modem",
      "component": "electronics-module",
      "parent": "terminal",
      "params": { "role": "modem", "width": 0.12, "depth": 0.08 },
      "transform": { "position": [0.18, -0.006, 0.1] },
      "selectable": true,
      "labelKey": "entity.modem.label",
      "descriptionKey": "entity.modem.description"
    },
    {
      "id": "power",
      "component": "electronics-module",
      "parent": "terminal",
      "params": { "role": "power", "width": 0.1, "depth": 0.07 },
      "transform": { "position": [-0.18, -0.006, 0.1] },
      "selectable": true,
      "labelKey": "entity.power.label",
      "descriptionKey": "entity.power.description"
    },
    {
      "id": "router",
      "component": "wifi-router",
      "params": { "height": 0.2, "showRadiation": false },
      "transform": { "position": [-2, 1, 1.5] },
      "selectable": true,
      "labelKey": "entity.router.label",
      "descriptionKey": "entity.router.description"
    },
    {
      "id": "terminal-cable",
      "component": "cable",
      "params": { "from": "terminal", "to": "router", "sag": 0.1 },
      "transform": { "position": [0, 0, 0] }
    },
    {
      "id": "sat-a",
      "component": "leo-satellite",
      "params": { "busLength": 4, "solarSpan": 14 },
      "transform": { "position": [-30, 55, -10] },
      "notToScale": true,
      "selectable": true,
      "labelKey": "entity.satellite.label",
      "descriptionKey": "entity.satellite.description"
    },
    {
      "id": "sat-b",
      "component": "leo-satellite",
      "params": { "busLength": 4, "solarSpan": 14 },
      "transform": { "position": [-80, 25, -20] },
      "notToScale": true,
      "selectable": true,
      "labelKey": "entity.satellite.label",
      "descriptionKey": "entity.satellite.description"
    },
    {
      "id": "sat-c",
      "component": "leo-satellite",
      "params": { "busLength": 4, "solarSpan": 14 },
      "transform": { "position": [-120, 5, -30] },
      "notToScale": true,
      "selectable": true,
      "labelKey": "entity.satellite.label",
      "descriptionKey": "entity.satellite.description"
    },
    {
      "id": "gateway",
      "component": "ground-station",
      "params": { "antennaCount": 4 },
      "transform": { "position": [-90, 0, -60] },
      "notToScale": true,
      "selectable": true,
      "labelKey": "entity.gateway.label",
      "descriptionKey": "entity.gateway.description"
    },
    {
      "id": "internet",
      "component": "datacenter",
      "params": { "width": 20 },
      "transform": { "position": [-130, 0, -90] },
      "notToScale": true,
      "selectable": true,
      "labelKey": "entity.internet.label",
      "descriptionKey": "entity.internet.description"
    },
    {
      "id": "link-user-a",
      "component": "data-link",
      "params": { "from": "terminal", "to": "sat-a", "medium": "radio" },
      "transform": { "position": [0, 0, 0] },
      "visible": false
    },
    {
      "id": "link-user-b",
      "component": "data-link",
      "params": { "from": "terminal", "to": "sat-b", "medium": "radio" },
      "transform": { "position": [0, 0, 0] },
      "visible": false
    },
    {
      "id": "link-feeder",
      "component": "data-link",
      "params": { "from": "sat-b", "to": "gateway", "medium": "radio" },
      "transform": { "position": [0, 0, 0] },
      "visible": false
    },
    {
      "id": "link-backbone",
      "component": "data-link",
      "params": { "from": "gateway", "to": "internet", "medium": "fiber" },
      "transform": { "position": [0, 0, 0] },
      "visible": false
    }
  ],
  "simulators": [
    {
      "id": "beam",
      "simulator": "phased-array-wave",
      "params": {
        "frequencyHz": 12000000000,
        "elementCount": 16,
        "spacingOverLambda": 0.5,
        "steeringAngleDeg": 0,
        "trackTarget": "sat-a",
        "tracking": true
      },
      "bind": { "array": "phased-array" }
    },
    {
      "id": "orbit",
      "simulator": "orbital-pass",
      "params": { "altitudeM": 480000, "minElevationDeg": 25, "displayRadius": 30, "spacingS": 230 },
      "bind": { "satellites": ["sat-a", "sat-b", "sat-c"], "observer": "terminal" }
    }
  ],
  "lenses": [
    {
      "id": "waves-lens",
      "lens": "waves",
      "labelKey": "lens.waves.label",
      "sources": ["beam"],
      "controls": [
        { "id": "steer", "target": "beam", "param": "steeringAngleDeg", "labelKey": "control.steer", "levels": ["discovery", "essential"], "min": -60, "max": 60, "step": 1 },
        { "id": "count", "target": "beam", "param": "elementCount", "labelKey": "control.count", "levels": ["essential", "advanced"], "min": 2, "max": 32, "step": 1 },
        { "id": "phase", "target": "beam", "param": "phaseStepDeg", "labelKey": "control.phase", "levels": ["advanced"], "min": -180, "max": 180, "step": 1 },
        { "id": "spacing", "target": "beam", "param": "spacingOverLambda", "labelKey": "control.spacing", "levels": ["advanced"], "min": 0.25, "max": 1.5, "step": 0.05 }
      ]
    }
  ],
  "links": [
    { "kind": "composedOf", "from": "phased-array", "to": "starlink-phased-array", "available": true },
    { "kind": "composedOf", "from": "beamformers", "to": "starlink-beamformer" },
    { "kind": "composedOf", "from": "modem", "to": "starlink-modem" },
    { "kind": "composedOf", "from": "power", "to": "starlink-power-deicing" },
    { "kind": "composedOf", "from": "router", "to": "starlink-wifi-router" },
    { "kind": "reliesOn", "from": "phased-array", "to": "wave-interference", "available": true },
    { "kind": "reliesOn", "from": "sat-a", "to": "circular-orbit" },
    { "kind": "freeQuestion", "from": "terminal", "to": "why-flat-antenna" }
  ],
  "tours": [
    {
      "id": "intro",
      "autoStart": true,
      "steps": [
        {
          "id": "arrival",
          "textKey": "intro.arrival",
          "durationS": 9,
          "camera": { "shot": { "target": "house", "azimuthDeg": 40, "elevationDeg": 8, "distance": 110 }, "transitionS": 0 },
          "actions": [
            { "type": "show", "targets": ["link-user-a"] },
            { "type": "highlight", "targets": ["terminal", "sat-a"] }
          ]
        },
        {
          "id": "subsystems",
          "textKey": "intro.subsystems",
          "durationS": 10,
          "camera": { "shot": { "target": "terminal", "azimuthDeg": 30, "elevationDeg": 45, "distance": 1.6 }, "transitionS": 3 },
          "actions": [
            { "type": "reveal", "target": "terminal", "mode": "cutaway" },
            { "type": "label", "targets": ["phased-array", "beamformers", "modem", "power"] }
          ]
        },
        {
          "id": "handover-to-user",
          "textKey": "intro.handover-to-user",
          "durationS": 6,
          "camera": { "shot": { "target": "terminal", "azimuthDeg": 35, "elevationDeg": 25, "distance": 9 }, "transitionS": 2 },
          "actions": [
            { "type": "reveal", "target": "terminal", "mode": "none" },
            { "type": "hide", "targets": ["link-user-a"] }
          ]
        }
      ]
    },
    {
      "id": "main",
      "steps": [
        {
          "id": "contact",
          "textKey": "play.contact",
          "durationS": 24,
          "camera": { "shot": { "target": "terminal", "azimuthDeg": 60, "elevationDeg": 8, "distance": 100 }, "transitionS": 3 },
          "actions": [
            { "type": "timeScale", "value": 1 },
            { "type": "show", "targets": ["link-user-a"] },
            { "type": "highlight", "targets": ["terminal", "sat-a"] },
            { "type": "label", "targets": ["terminal", "sat-a"] }
          ]
        },
        {
          "id": "problem",
          "textKey": "play.problem",
          "durationS": 22,
          "camera": { "shot": { "target": "house", "azimuthDeg": 90, "elevationDeg": 5, "distance": 90 }, "transitionS": 3 },
          "actions": [
            { "type": "timeScale", "value": 10 },
            { "type": "highlight", "targets": ["sat-a"] }
          ]
        },
        {
          "id": "cutaway",
          "textKey": "play.cutaway",
          "durationS": 18,
          "camera": { "shot": { "target": "terminal", "azimuthDeg": 20, "elevationDeg": 55, "distance": 1.2 }, "transitionS": 4 },
          "actions": [
            { "type": "timeScale", "value": 1 },
            { "type": "reveal", "target": "terminal", "mode": "cutaway" },
            { "type": "highlight", "targets": ["phased-array"] },
            { "type": "label", "targets": ["phased-array", "beamformers"] }
          ]
        },
        {
          "id": "beam-steering",
          "textKey": "play.beam-steering",
          "durationS": 30,
          "camera": { "shot": { "target": "terminal", "azimuthDeg": 90, "elevationDeg": 10, "distance": 1.8 }, "transitionS": 3 },
          "actions": [
            { "type": "reveal", "target": "terminal", "mode": "none" },
            { "type": "lens", "lens": "waves-lens", "on": true },
            { "type": "setParam", "target": "beam", "param": "tracking", "value": false },
            { "type": "setParam", "target": "beam", "param": "steeringAngleDeg", "value": 0 },
            { "type": "setParam", "target": "beam", "param": "steeringAngleDeg", "value": 35, "overS": 5 }
          ]
        },
        {
          "id": "handover",
          "textKey": "play.handover",
          "durationS": 22,
          "camera": { "shot": { "target": "terminal", "azimuthDeg": 70, "elevationDeg": 10, "distance": 80 }, "transitionS": 3 },
          "actions": [
            { "type": "setParam", "target": "beam", "param": "tracking", "value": true },
            { "type": "timeScale", "value": 5 },
            { "type": "setParam", "target": "beam", "param": "trackTarget", "value": "sat-b" },
            { "type": "hide", "targets": ["link-user-a"] },
            { "type": "show", "targets": ["link-user-b"] },
            { "type": "highlight", "targets": ["sat-a", "sat-b"] }
          ]
        },
        {
          "id": "data-path",
          "textKey": "play.data-path",
          "durationS": 22,
          "camera": { "shot": { "target": "house", "azimuthDeg": 120, "elevationDeg": 25, "distance": 170 }, "transitionS": 3 },
          "actions": [
            { "type": "lens", "lens": "waves-lens", "on": false },
            { "type": "timeScale", "value": 1 },
            { "type": "show", "targets": ["link-feeder", "link-backbone"] },
            { "type": "highlight", "targets": ["sat-b", "gateway", "internet"] },
            { "type": "label", "targets": ["gateway", "internet"] }
          ]
        },
        {
          "id": "other-subsystems",
          "textKey": "play.other-subsystems",
          "durationS": 25,
          "camera": { "shot": { "target": "house", "azimuthDeg": 30, "elevationDeg": 35, "distance": 14 }, "transitionS": 4 },
          "actions": [
            { "type": "hide", "targets": ["link-user-b", "link-feeder", "link-backbone"] },
            { "type": "reveal", "target": "house", "mode": "cutaway" },
            { "type": "reveal", "target": "terminal", "mode": "cutaway" },
            { "type": "highlight", "targets": ["modem", "power", "router"] },
            { "type": "label", "targets": ["modem", "power", "router"] }
          ]
        }
      ]
    }
  ]
}
```

`texts.fr.json`

```json
{
  "formatVersion": "0.2",
  "nodeId": "starlink-terminal",
  "lang": "fr",
  "question": "Comment fonctionne l'antenne Starlink ?",
  "aliases": [
    "Comment marche une parabole Starlink ?",
    "Comment l'antenne Starlink capte-t-elle Internet par satellite ?",
    "Comment fonctionne Starlink ?"
  ],
  "common": {
    "derived.steering-angle-deg": "Direction du faisceau",
    "entity.terminal.label": "Antenne Starlink",
    "entity.phased-array.label": "Réseau d'éléments rayonnants",
    "entity.beamformers.label": "Puces de formation de faisceau",
    "entity.modem.label": "Modem",
    "entity.power.label": "Alimentation et dégivrage",
    "entity.router.label": "Routeur Wi-Fi",
    "entity.satellite.label": "Satellite Starlink",
    "entity.gateway.label": "Station au sol",
    "entity.internet.label": "Internet",
    "lens.waves.label": "Ondes",
    "control.steer": "Angle du faisceau",
    "control.count": "Nombre d'éléments",
    "control.phase": "Déphasage entre voisins",
    "control.spacing": "Espacement d / λ",

    "entity.terminal.description": "Un panneau plat et fixe qui échange des ondes radio avec les satellites qui passent au-dessus de lui.",
    "entity.phased-array.description": "Des centaines de petites antennes identiques. Ensemble, elles forment un faisceau qu'on oriente sans rien bouger.",
    "entity.beamformers.description": "Des puces qui décalent très légèrement le signal de chaque petite antenne. C'est ce décalage qui oriente le faisceau.",
    "entity.modem.description": "Il transforme les ondes reçues en données, et les données à envoyer en ondes.",
    "entity.power.description": "Il alimente l'antenne et peut chauffer sa surface pour faire fondre la neige.",
    "entity.router.description": "Il distribue la connexion dans la maison, par Wi-Fi.",
    "entity.satellite.description": "Un satellite en orbite basse, l'un des milliers de la constellation. Il relaie les données entre les antennes et les stations au sol.",
    "entity.gateway.description": "Une station équipée de grandes antennes, reliée à Internet par la fibre optique. Elle échange les données avec les satellites.",
    "entity.internet.description": "Le reste du réseau mondial : serveurs, sites, services."
  },
  "levels": {
    "discovery": {
      "entity.phased-array.label": "Les petites antennes",
      "entity.beamformers.label": "Les puces chefs d'orchestre",
      "entity.power.label": "Alimentation et chauffage",
      "entity.router.label": "La boîte Wi-Fi",
      "control.steer": "Direction du faisceau",
      "entity.terminal.description": "Une antenne toute plate qui ne bouge jamais, et qui parle pourtant avec des satellites qui filent dans le ciel.",
      "entity.phased-array.description": "Des centaines de toutes petites antennes. Elles travaillent ensemble, comme une chorale.",
      "entity.beamformers.description": "Elles disent à chaque petite antenne quand « chanter », un tout petit peu avant ou après sa voisine.",
      "entity.modem.description": "Un traducteur : il change les ondes en messages, et les messages en ondes.",
      "entity.power.description": "Il donne de l'énergie à l'antenne, et la chauffe quand il neige.",

      "intro.arrival": "Regarde ce toit : il y a une antenne toute plate. Elle discute avec un satellite, tout là-haut dans l'espace.",
      "intro.subsystems": "Dedans, il y a des centaines de minuscules antennes, des puces qui les commandent, un traducteur appelé modem, et de quoi chauffer l'antenne quand il neige.",
      "intro.handover-to-user": "Touche une pièce pour aller voir dedans, ou appuie sur Play pour la visite.",

      "play.contact": "Cette antenne parle avec un satellite qui vole environ cinquante fois plus haut qu'un avion. Il va si vite qu'il fait le tour de la Terre en une heure et demie !",
      "play.problem": "Mais il y a un problème : le satellite traverse le ciel en quelques minutes. L'antenne doit le suivre sans jamais bouger. Essaie de suivre un oiseau du regard sans tourner la tête ni les yeux : impossible ! L'antenne, elle, a une astuce.",
      "play.cutaway": "Ouvrons-la ! Dedans, il y a des centaines de toutes petites antennes, rangées bien serrées les unes à côté des autres. Derrière elles, des puces leur donnent des ordres.",
      "play.beam-steering": "Jette plein de cailloux dans une mare, un peu l'un après l'autre : les vagues s'additionnent dans une seule direction. L'antenne fait pareil avec des ondes radio.",
      "play.handover": "Quand le satellite s'en va vers l'horizon, l'antenne se tourne vers le suivant, toujours sans bouger. Comme dans une course de relais : le témoin passe d'un coureur à l'autre sans s'arrêter.",
      "play.data-path": "Ensuite, tes messages voyagent : de l'antenne jusqu'au satellite, du satellite jusqu'à une grande station au sol, puis par des câbles jusqu'à Internet. Et tout ça en un clin d'œil !",
      "play.other-subsystems": "Il reste trois aides. Le modem traduit les ondes en messages. Un chauffage fait fondre la neige sur l'antenne. Et la boîte Wi-Fi envoie Internet partout dans la maison."
    },
    "essential": {
      "intro.arrival": "Sur ce toit, une antenne plate, à peine plus grande qu'un écran d'ordinateur, échange des données avec un satellite qui file au-dessus de nos têtes.",
      "intro.subsystems": "Sous son capot : un réseau de petites antennes, les puces qui forment le faisceau, le modem, l'alimentation avec son dégivrage. Et dans la maison, le routeur Wi-Fi.",
      "intro.handover-to-user": "Touchez une pièce pour plonger à l'intérieur, ou lancez la visite guidée.",

      "play.contact": "Cette antenne communique avec un satellite Starlink situé à un peu moins de 500 kilomètres d'altitude. Il se déplace à plus de 27 000 kilomètres par heure : il fait le tour de la Terre en une heure et demie.",
      "play.problem": "Voilà le problème. Vu d'ici, le satellite traverse le ciel en quelques minutes. Il faut le viser en permanence, avec précision. Et l'antenne n'a aucune pièce mobile : elle ne tourne pas, elle ne s'incline pas.",
      "play.cutaway": "Ouvrons le capot. Sous la surface lisse, des centaines de petites antennes identiques sont serrées les unes contre les autres. Juste derrière, des puces pilotent chacune un petit groupe d'antennes.",
      "play.beam-steering": {
        "text": "Chaque petite antenne émet la même onde avec un léger décalage sur sa voisine. Les ondes s'additionnent dans une direction et s'annulent ailleurs. On oriente ainsi le faisceau électroniquement, sans rien bouger.",
        "links": [
          {"phrase": "Les ondes s'additionnent dans une direction et s'annulent ailleurs", "node": "wave-interference"}
        ]
      },
      "play.handover": "Le satellite finit par descendre vers l'horizon. Avant de le perdre, l'antenne bascule son faisceau vers un autre satellite, plus haut dans le ciel. Le réseau réorganise d'ailleurs ces liaisons environ toutes les quinze secondes, et la connexion continue.",
      "play.data-path": "Les données font ensuite le voyage : du toit au satellite, du satellite à une station au sol équipée de grandes antennes, puis par la fibre optique jusqu'à Internet. Le tout prend une fraction de seconde.",
      "play.other-subsystems": "Trois autres sous-systèmes complètent l'ensemble. Le modem transforme les ondes reçues en données, et l'inverse. L'alimentation fournit environ une centaine de watts et peut chauffer l'antenne pour faire fondre la neige. Enfin, le routeur Wi-Fi distribue la connexion dans la maison."
    },
    "advanced": {
      "entity.phased-array.description": "Antenne réseau plane : des éléments imprimés identiques, espacés d'environ une demi-longueur d'onde. Leur rayonnement combiné forme un faisceau orientable par la phase.",
      "entity.beamformers.description": "Circuits intégrés qui appliquent à chaque élément un déphasage et un gain. Le déphasage entre voisins fixe la direction du faisceau.",
      "entity.modem.description": "Module et démodule le signal en bande Ku, et gère l'accès au réseau.",
      "entity.power.description": "Environ 75 à 100 watts en moyenne sur le modèle Standard. Un mode de fonte de neige chauffe le panneau.",
      "entity.satellite.description": "Satellite en orbite basse circulaire, vers 480 kilomètres d'altitude depuis l'abaissement de 2026. Liaison utilisateur en bande Ku, liaison vers les passerelles en bande Ka.",

      "intro.arrival": "Un terminal Starlink à antenne réseau plane, fixe sur son toit, en liaison bande Ku avec un satellite en orbite basse.",
      "intro.subsystems": "Cinq sous-systèmes : le réseau d'éléments rayonnants, les circuits de formation de faisceau, le modem, l'alimentation et le dégivrage, et le routeur Wi-Fi.",
      "intro.handover-to-user": "Sélectionnez un sous-système pour descendre d'un niveau, ou lancez la visite.",

      "play.contact": {
        "text": "Le satellite est à environ 480 kilomètres d'altitude. En orbite circulaire, sa vitesse est la racine carrée de mu sur r : mu, la constante gravitationnelle de la Terre, et r, la distance au centre de la Terre, soit son rayon plus l'altitude. On trouve 7,6 kilomètres par seconde, plus de 27 000 kilomètres par heure : un tour de la Terre en 94 minutes.",
        "subtitle": "Le satellite est à environ 480 km d'altitude. En orbite circulaire, $v = \\sqrt{\\dfrac{\\mu}{R_\\oplus + h}} \\approx 7{,}6\\ \\text{km/s}$, soit plus de 27 000 km/h, et une période $T \\approx 94\\ \\text{min}$.",
        "terms": [
          {"symbol": "v", "meaning": "vitesse orbitale", "unit": "km/s"},
          {"symbol": "\\mu", "meaning": "constante gravitationnelle de la Terre", "unit": "≈ 398 600 km³/s²"},
          {"symbol": "R_\\oplus", "meaning": "rayon moyen de la Terre", "unit": "≈ 6 371 km"},
          {"symbol": "h", "meaning": "altitude du satellite", "unit": "≈ 480 km"},
          {"symbol": "T", "meaning": "période orbitale : durée d'un tour de la Terre", "unit": "min"}
        ],
        "links": [
          {"phrase": "orbite circulaire", "node": "circular-orbit"}
        ]
      },
      "play.problem": "En prenant 25 degrés d'élévation minimale, un passage au zénith ne dure qu'environ quatre minutes. Le champ de vision du terminal couvre environ 110 degrés. Suivre une telle cible avec une parabole motorisée serait lent et fragile : ici, le pointage est entièrement électronique.",
      "play.cutaway": "En coupe : la surface est un réseau plan d'éléments rayonnants imprimés, plus d'un millier sur les premiers modèles démontés. Derrière, des circuits de formation de faisceau appliquent à chaque élément son propre déphasage.",
      "play.beam-steering": {
        "text": "Chaque élément est déphasé de delta phi par rapport à son voisin. Le faisceau s'oriente alors d'un angle thêta, mesuré depuis la perpendiculaire au panneau, tel que delta phi égale deux pi fois d sinus thêta, divisé par lambda, où d est l'espacement entre deux éléments et lambda la longueur d'onde. En bande Ku, vers 12 gigahertz, lambda vaut environ 2,5 centimètres, d'où un espacement d'environ lambda sur deux, soit 1,25 centimètre. Au-delà, des faisceaux parasites apparaissent : les lobes de réseau.",
        "subtitle": "Chaque élément est déphasé de $\\Delta\\varphi$ par rapport à son voisin. Le faisceau s'oriente d'un angle $\\theta$ tel que $\\Delta\\varphi = \\dfrac{2\\pi\\, d \\sin\\theta}{\\lambda}$. En bande Ku (≈ 12 GHz), $\\lambda \\approx 2{,}5\\ \\text{cm}$, d'où $d \\approx \\lambda / 2 \\approx 1{,}25\\ \\text{cm}$. Au-delà de $\\lambda / 2$, des faisceaux parasites apparaissent : les lobes de réseau.",
        "terms": [
          {"symbol": "\\Delta\\varphi", "meaning": "déphasage entre deux éléments voisins", "unit": "rad"},
          {"symbol": "\\theta", "meaning": "direction du faisceau, mesurée depuis la perpendiculaire au panneau", "unit": "°"},
          {"symbol": "d", "meaning": "espacement entre deux éléments voisins", "unit": "cm"},
          {"symbol": "\\lambda", "meaning": "longueur d'onde du signal", "unit": "cm"}
        ],
        "links": [
          {"phrase": "déphasé", "node": "wave-interference"}
        ]
      },
      "play.handover": "Quand l'élévation du satellite décroît, le terminal commute vers un autre satellite, sans repointage mécanique. Des mesures publiées montrent une réaffectation des liaisons, synchronisée à l'échelle mondiale, toutes les 15 secondes, visible comme un bref pic de latence.",
      "play.data-path": "Liaison utilisateur en bande Ku : réception de 10,7 à 12,7 gigahertz, émission de 14 à 14,5 gigahertz. Le satellite relaie vers une station passerelle en bande Ka, puis le trafic rejoint Internet par la fibre optique.",
      "play.other-subsystems": "Le modem module et démodule le signal et gère l'accès au réseau. L'alimentation consomme en moyenne 75 à 100 watts sur le modèle Standard, et un mode de fonte de neige chauffe le panneau. Le routeur Wi-Fi 6 distribue le débit dans le logement."
    }
  }
}
```

### `wave-interference`

`scene.json`

```json
{
  "formatVersion": "0.2",
  "node": {
    "id": "wave-interference",
    "kind": "principle",
    "version": 1,
    "status": "review",
    "summaryKey": "node.summary"
  },
  "scale": {
    "metersPerUnit": 0.001
  },
  "environment": {
    "lighting": "studio",
    "background": "#1d2733"
  },
  "performance": {
    "triangleBudget": 60000
  },
  "camera": {
    "home": {
      "target": "frame",
      "azimuthDeg": 20,
      "elevationDeg": 25,
      "distance": 340
    },
    "constraints": {
      "minDistance": 40,
      "maxDistance": 900,
      "minElevationDeg": 0,
      "maxElevationDeg": 85
    }
  },
  "entities": [
    {
      "id": "frame",
      "component": "patch-element",
      "params": {
        "patchSize": 0.005,
        "tileSize": 0.008,
        "substrateThickness": 0.0015,
        "feed": "none"
      },
      "transform": {
        "position": [
          0,
          100,
          0
        ]
      },
      "visible": false
    },
    {
      "id": "centre",
      "component": "patch-element",
      "params": {
        "patchSize": 0.005,
        "tileSize": 0.008,
        "substrateThickness": 0.0015,
        "feed": "none"
      },
      "transform": {
        "position": [
          0,
          0,
          0
        ]
      },
      "visible": false,
      "labelKey": "entity.source.label"
    },
    {
      "id": "source-1",
      "component": "patch-element",
      "params": {
        "patchSize": 0.005,
        "tileSize": 0.008,
        "substrateThickness": 0.0015,
        "feed": "none"
      },
      "transform": {
        "position": [
          -43.75,
          0,
          0
        ]
      },
      "labelKey": "entity.source.label",
      "visible": false
    },
    {
      "id": "source-2",
      "component": "patch-element",
      "params": {
        "patchSize": 0.005,
        "tileSize": 0.008,
        "substrateThickness": 0.0015,
        "feed": "none"
      },
      "transform": {
        "position": [
          -31.25,
          0,
          0
        ]
      },
      "labelKey": "entity.source.label",
      "visible": false
    },
    {
      "id": "source-3",
      "component": "patch-element",
      "params": {
        "patchSize": 0.005,
        "tileSize": 0.008,
        "substrateThickness": 0.0015,
        "feed": "none"
      },
      "transform": {
        "position": [
          -18.75,
          0,
          0
        ]
      },
      "labelKey": "entity.source.label"
    },
    {
      "id": "source-4",
      "component": "patch-element",
      "params": {
        "patchSize": 0.005,
        "tileSize": 0.008,
        "substrateThickness": 0.0015,
        "feed": "none"
      },
      "transform": {
        "position": [
          -6.25,
          0,
          0
        ]
      },
      "labelKey": "entity.source.label",
      "visible": false
    },
    {
      "id": "source-5",
      "component": "patch-element",
      "params": {
        "patchSize": 0.005,
        "tileSize": 0.008,
        "substrateThickness": 0.0015,
        "feed": "none"
      },
      "transform": {
        "position": [
          6.25,
          0,
          0
        ]
      },
      "labelKey": "entity.source.label",
      "visible": false
    },
    {
      "id": "source-6",
      "component": "patch-element",
      "params": {
        "patchSize": 0.005,
        "tileSize": 0.008,
        "substrateThickness": 0.0015,
        "feed": "none"
      },
      "transform": {
        "position": [
          18.75,
          0,
          0
        ]
      },
      "labelKey": "entity.source.label"
    },
    {
      "id": "source-7",
      "component": "patch-element",
      "params": {
        "patchSize": 0.005,
        "tileSize": 0.008,
        "substrateThickness": 0.0015,
        "feed": "none"
      },
      "transform": {
        "position": [
          31.25,
          0,
          0
        ]
      },
      "labelKey": "entity.source.label",
      "visible": false
    },
    {
      "id": "source-8",
      "component": "patch-element",
      "params": {
        "patchSize": 0.005,
        "tileSize": 0.008,
        "substrateThickness": 0.0015,
        "feed": "none"
      },
      "transform": {
        "position": [
          43.75,
          0,
          0
        ]
      },
      "labelKey": "entity.source.label",
      "visible": false
    }
  ],
  "simulators": [
    {
      "id": "field",
      "simulator": "phased-array-wave",
      "params": {
        "frequencyHz": 12000000000,
        "elementCount": 2,
        "spacingOverLambda": 1.5,
        "phaseStepDeg": 0,
        "tracking": false
      },
      "bind": {
        "array": "centre",
        "markers": [
          "source-1",
          "source-2",
          "source-3",
          "source-4",
          "source-5",
          "source-6",
          "source-7",
          "source-8"
        ]
      }
    }
  ],
  "lenses": [
    {
      "id": "waves-lens",
      "lens": "waves",
      "labelKey": "lens.waves.label",
      "sources": [
        "field"
      ],
      "controls": [
        {
          "id": "phase",
          "target": "field",
          "param": "phaseStepDeg",
          "labelKey": "control.phase",
          "levels": [
            "discovery",
            "essential",
            "advanced"
          ],
          "min": -180,
          "max": 180,
          "step": 1
        },
        {
          "id": "spacing",
          "target": "field",
          "param": "spacingOverLambda",
          "labelKey": "control.spacing",
          "levels": [
            "advanced"
          ],
          "min": 0.25,
          "max": 2,
          "step": 0.05
        }
      ]
    }
  ],
  "links": [
    {
      "kind": "reliesOn",
      "to": "electromagnetic-wave"
    }
  ],
  "tours": [
    {
      "id": "intro",
      "autoStart": true,
      "steps": [
        {
          "id": "arrival",
          "textKey": "intro.arrival",
          "durationS": 9,
          "camera": {
            "shot": {
              "target": "frame",
              "azimuthDeg": 20,
              "elevationDeg": 25,
              "distance": 340
            },
            "transitionS": 0
          },
          "actions": [
            {
              "type": "lens",
              "lens": "waves-lens",
              "on": true
            },
            {
              "type": "highlight",
              "targets": [
                "source-3",
                "source-6"
              ]
            }
          ]
        },
        {
          "id": "bands",
          "textKey": "intro.bands",
          "durationS": 9,
          "camera": {
            "shot": {
              "target": "frame",
              "azimuthDeg": 0,
              "elevationDeg": 8,
              "distance": 300
            },
            "transitionS": 3
          }
        },
        {
          "id": "handover-to-user",
          "textKey": "intro.handover-to-user",
          "durationS": 7,
          "camera": {
            "shot": {
              "target": "frame",
              "azimuthDeg": 20,
              "elevationDeg": 25,
              "distance": 340
            },
            "transitionS": 2
          }
        }
      ]
    },
    {
      "id": "main",
      "steps": [
        {
          "id": "one",
          "textKey": "play.one",
          "durationS": 18,
          "camera": {
            "shot": {
              "target": "frame",
              "azimuthDeg": 0,
              "elevationDeg": 8,
              "distance": 300
            },
            "transitionS": 2
          },
          "actions": [
            {
              "type": "show",
              "targets": [
                "centre"
              ]
            },
            {
              "type": "hide",
              "targets": [
                "source-3",
                "source-6"
              ]
            },
            {
              "type": "setParam",
              "target": "field",
              "param": "elementCount",
              "value": 1
            },
            {
              "type": "lens",
              "lens": "waves-lens",
              "on": true
            },
            {
              "type": "highlight",
              "targets": [
                "centre"
              ]
            }
          ]
        },
        {
          "id": "two",
          "textKey": "play.two",
          "durationS": 22,
          "actions": [
            {
              "type": "hide",
              "targets": [
                "centre"
              ]
            },
            {
              "type": "show",
              "targets": [
                "source-3",
                "source-6"
              ]
            },
            {
              "type": "setParam",
              "target": "field",
              "param": "elementCount",
              "value": 2
            },
            {
              "type": "highlight",
              "targets": [
                "source-3",
                "source-6"
              ]
            },
            {
              "type": "label",
              "targets": [
                "source-3",
                "source-6"
              ]
            }
          ]
        },
        {
          "id": "bands",
          "textKey": "play.bands",
          "durationS": 24,
          "camera": {
            "shot": {
              "target": "frame",
              "azimuthDeg": 0,
              "elevationDeg": 10,
              "distance": 260
            },
            "transitionS": 2
          }
        },
        {
          "id": "shift",
          "textKey": "play.shift",
          "durationS": 22,
          "actions": [
            {
              "type": "setParam",
              "target": "field",
              "param": "phaseStepDeg",
              "value": 0
            },
            {
              "type": "setParam",
              "target": "field",
              "param": "phaseStepDeg",
              "value": 120,
              "overS": 5
            },
            {
              "type": "highlight",
              "targets": [
                "source-6"
              ]
            }
          ]
        },
        {
          "id": "many",
          "textKey": "play.many",
          "durationS": 24,
          "camera": {
            "shot": {
              "target": "frame",
              "azimuthDeg": 0,
              "elevationDeg": 12,
              "distance": 480
            },
            "transitionS": 3
          },
          "actions": [
            {
              "type": "setParam",
              "target": "field",
              "param": "phaseStepDeg",
              "value": 0
            },
            {
              "type": "setParam",
              "target": "field",
              "param": "spacingOverLambda",
              "value": 0.5
            },
            {
              "type": "setParam",
              "target": "field",
              "param": "elementCount",
              "value": 8
            },
            {
              "type": "show",
              "targets": [
                "source-1",
                "source-2",
                "source-4",
                "source-5",
                "source-7",
                "source-8"
              ]
            },
            {
              "type": "highlight",
              "targets": [
                "source-3",
                "source-6",
                "source-1",
                "source-2",
                "source-4",
                "source-5",
                "source-7",
                "source-8"
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

`texts.fr.json`

```json
{
  "formatVersion": "0.2",
  "nodeId": "wave-interference",
  "lang": "fr",
  "question": "Pourquoi deux ondes peuvent-elles se renforcer ou s'annuler ?",
  "aliases": [
    "Que sont les interférences ?",
    "Comment des ondes s'additionnent-elles ?"
  ],
  "common": {
    "derived.steering-angle-deg": "Direction du faisceau",
    "entity.source.label": "Source",
    "lens.waves.label": "Ondes",
    "control.phase": "Décalage entre sources",
    "control.spacing": "Espacement d / λ"
  },
  "levels": {
    "discovery": {
      "node.summary": "Quand deux vagues se rencontrent, elles s'additionnent : parfois elles deviennent plus grandes, parfois elles s'effacent.",
      "control.phase": "Décalage",
      "intro.arrival": "Voici deux petites sources qui font des vagues en même temps, comme deux cailloux tombés ensemble dans une mare.",
      "intro.bands": "Regarde bien : à certains endroits les vagues deviennent plus grandes, à d'autres elles disparaissent presque.",
      "intro.handover-to-user": "Joue avec le curseur de la lentille Ondes, ou appuie sur Play pour la visite.",
      "play.one": "D'abord, une seule source. Ses vagues partent en cercles : une bosse, un creux, une bosse, comme dans une mare.",
      "play.two": "Ajoutons une deuxième source. Quand deux bosses arrivent au même endroit, la vague devient deux fois plus haute. Quand une bosse tombe sur un creux, elles s'effacent.",
      "play.bands": "C'est pour ça qu'on voit des rayons : des chemins où les vagues s'aident, et entre eux, des chemins où elles s'annulent.",
      "play.shift": "Si une source attend un tout petit peu avant de faire sa vague, tous les rayons tournent. Rien n'a bougé, sauf le moment où chaque vague part !",
      "play.many": "Avec beaucoup de sources serrées les unes contre les autres, il ne reste qu'un seul grand rayon. C'est exactement ce que fait l'antenne Starlink pour viser le satellite."
    },
    "essential": {
      "node.summary": "Deux ondes qui se croisent s'additionnent : elles se renforcent là où leurs crêtes coïncident et s'annulent là où une crête rencontre un creux.",
      "intro.arrival": "Deux sources émettent la même onde radio, au même rythme. Leurs ondes se croisent et s'additionnent en chaque point.",
      "intro.bands": "Résultat : des directions où l'onde est renforcée et, entre elles, des directions où elle s'éteint presque. Ce sont des interférences.",
      "intro.handover-to-user": "Réglez le décalage dans la lentille Ondes, ou lancez la visite guidée.",
      "play.one": "Une seule source d'abord. Elle émet des ondes circulaires : une crête, un creux, une crête, espacées d'une longueur d'onde, ici deux centimètres et demi.",
      "play.two": "Une deuxième source, à une longueur d'onde et demie de la première. Là où deux crêtes se rencontrent, l'onde est deux fois plus forte. Là où une crête rencontre un creux, les deux s'annulent.",
      "play.bands": "Tout dépend de la différence de trajet. Si un point est plus loin d'une source que de l'autre d'un nombre entier de longueurs d'onde, les crêtes arrivent ensemble. Avec une demi-longueur d'onde de plus, elles s'opposent.",
      "play.shift": "Retardons maintenant une source d'un tiers de période. Toutes les directions renforcées tournent d'un bloc : on oriente l'onde sans rien bouger, simplement en décalant son départ.",
      "play.many": "Avec huit sources espacées d'une demi-longueur d'onde, une seule direction reste renforcée : un faisceau. C'est le principe du réseau d'antennes de Starlink."
    },
    "advanced": {
      "node.summary": "Superposition d'ondes cohérentes : l'amplitude résultante dépend de leur différence de phase, maximale pour un multiple de deux pi, nulle pour un multiple impair de pi.",
      "intro.arrival": "Deux sources ponctuelles cohérentes, en phase, à douze gigahertz : longueur d'onde d'environ vingt-cinq millimètres. Le champ affiché est la somme des deux ondes.",
      "intro.bands": "Les maxima et minima d'intensité dessinent des directions fixes : la figure d'interférence de deux sources.",
      "intro.handover-to-user": "Lentille Ondes : réglez le déphasage et l'espacement, ou lancez la visite.",
      "play.one": {
        "text": "Une source seule émet des ondes cylindriques dont l'amplitude décroît comme l'inverse de la racine de la distance r. Leur longueur d'onde lambda vaut c sur f, la vitesse de la lumière divisée par la fréquence : vingt-cinq millimètres à douze gigahertz.",
        "subtitle": "Source seule : ondes cylindriques, amplitude $\\propto 1/\\sqrt{r}$. Longueur d'onde $\\lambda = c/f \\approx 25\\ \\text{mm}$ à $f = 12\\ \\text{GHz}$.",
        "terms": [
          {
            "symbol": "r",
            "meaning": "distance à la source",
            "unit": "mm"
          },
          {
            "symbol": "\\lambda",
            "meaning": "longueur d'onde",
            "unit": "mm"
          },
          {
            "symbol": "c",
            "meaning": "vitesse de la lumière",
            "unit": "≈ 3 × 10⁸ m/s"
          },
          {
            "symbol": "f",
            "meaning": "fréquence de l'onde",
            "unit": "Hz"
          }
        ]
      },
      "play.two": "Deux sources en phase, espacées d'une longueur d'onde et demie. En chaque point, les deux champs s'additionnent : en phase, ils doublent l'amplitude ; en opposition de phase, ils s'annulent.",
      "play.bands": {
        "text": "Loin des sources, la différence de trajet delta vaut d sinus thêta, où d est l'espacement et thêta la direction mesurée depuis la perpendiculaire à la ligne des sources. L'intensité est maximale quand delta vaut un nombre entier m de longueurs d'onde lambda, nulle quand il vaut m plus un demi.",
        "subtitle": "Différence de trajet $\\delta = d \\sin\\theta$. Maxima : $\\delta = m\\lambda$ ; minima : $\\delta = (m + \\tfrac{1}{2})\\lambda$. Avec $d = 1{,}5\\,\\lambda$ : maxima à $0^\\circ$ et $\\pm 41{,}8^\\circ$.",
        "terms": [
          {
            "symbol": "\\delta",
            "meaning": "différence de trajet entre les deux sources",
            "unit": "mm"
          },
          {
            "symbol": "d",
            "meaning": "espacement des sources",
            "unit": "mm"
          },
          {
            "symbol": "\\theta",
            "meaning": "direction, mesurée depuis la perpendiculaire à la ligne des sources",
            "unit": "°"
          },
          {
            "symbol": "m",
            "meaning": "ordre du maximum, un entier"
          },
          {
            "symbol": "\\lambda",
            "meaning": "longueur d'onde",
            "unit": "≈ 25 mm"
          }
        ]
      },
      "play.shift": {
        "text": "Un déphasage delta phi de cent vingt degrés entre les deux sources décale toutes les directions de maximum : d sinus thêta égale m plus delta phi sur deux pi, le tout multiplié par lambda. Le maximum central passe de zéro à environ treize degrés.",
        "subtitle": "Déphasage $\\Delta\\varphi = 120^\\circ$ : maxima pour $d \\sin\\theta = \\left(m + \\dfrac{\\Delta\\varphi}{2\\pi}\\right)\\lambda$. Le maximum central passe de $0^\\circ$ à $\\approx 12{,}8^\\circ$.",
        "terms": [
          {
            "symbol": "\\Delta\\varphi",
            "meaning": "déphasage entre les deux sources",
            "unit": "°"
          },
          {
            "symbol": "d",
            "meaning": "espacement des sources",
            "unit": "mm"
          },
          {
            "symbol": "\\theta",
            "meaning": "direction d'un maximum, depuis la perpendiculaire",
            "unit": "°"
          },
          {
            "symbol": "m",
            "meaning": "ordre du maximum, un entier"
          },
          {
            "symbol": "\\lambda",
            "meaning": "longueur d'onde",
            "unit": "≈ 25 mm"
          }
        ]
      },
      "play.many": "Huit sources au pas d'une demi-longueur d'onde : la condition de maximum n'a plus qu'une solution dans l'espace visible, et le lobe central s'affine quand le nombre de sources augmente. Au-delà d'une demi-longueur d'onde d'espacement, orienter le faisceau fait apparaître des lobes de réseau : essayez le curseur."
    }
  }
}
```

# Answer format

Answer with one JSON object and nothing else: `{"scene": <scene.json>, "texts": <texts.fr.json>}`. No prose before or after it.


## user

Write the node `starlink-phased-array`.

- Question it answers (French, as the user would ask it): « Comment le réseau d'antennes de Starlink oriente-t-il son faisceau ? »
- Kind: system
- Child node of `starlink-terminal`: the user dives into its entity `phased-array`.
- Nodes that exist today (the only valid targets of an `available` link): `blue-sky`, `starlink-phased-array`, `starlink-radiating-element`, `starlink-terminal`, `wave-interference`

## Sources

The figures you use come from these sources (already gathered; cite nothing else). A fact marked unverified must stay hedged in the texts.

```json
{
  "formatVersion": "0.2",
  "nodeId": "starlink-phased-array",
  "facts": [
    {
      "id": "wavelength",
      "claim": "À 12 GHz, λ ≈ 2,5 cm ; λ/2 ≈ 1,25 cm.",
      "value": 0.02498,
      "unit": "m",
      "status": "computed",
      "formula": "lambda = c / f, c = 299 792 458 m/s, f = 12 GHz",
      "sources": [],
      "usedBy": ["levels.advanced.intro.arrival", "simulators.beam.params.frequencyHz"]
    },
    {
      "id": "element-spacing",
      "claim": "Éléments espacés d'environ une demi-longueur d'onde, environ un centimètre.",
      "value": 0.0125,
      "unit": "m",
      "status": "order-of-magnitude",
      "sources": ["mwrf-grating-lobes", "adi-phased-array-2"],
      "usedBy": ["entities.array.params.spacing", "intro.arrival", "play.spacing"],
      "note": "Règle de conception générale des réseaux à balayage électronique. Espacement réel du terminal Starlink non vérifié."
    },
    {
      "id": "grating-lobe-condition",
      "claim": "Pas de lobe de réseau sur un dépointage ±θmax tant que d < λ / (1 + |sin θmax|) ; à d = λ/2, aucun lobe sur tout l'horizon.",
      "status": "verified",
      "sources": ["mwrf-grating-lobes", "adi-phased-array-2", "rfessentials-spacing"],
      "usedBy": ["play.spacing"]
    },
    {
      "id": "scan-limit",
      "claim": "Dépointage maximal pris égal à la moitié du champ de vision de 110° du terminal Standard : 55°.",
      "value": 55,
      "unit": "deg",
      "status": "computed",
      "formula": "110° / 2",
      "sources": ["speedcast-standard"],
      "usedBy": ["levels.advanced.play.spacing"],
      "note": "Hypothèse : le champ de vision est symétrique autour de l'axe du panneau."
    },
    {
      "id": "spacing-limit",
      "claim": "Pour 55°, d < 0,55 λ.",
      "value": 0.55,
      "unit": "1",
      "status": "computed",
      "formula": "1 / (1 + sin 55°) = 0,550",
      "sources": [],
      "usedBy": ["levels.advanced.play.spacing"]
    },
    {
      "id": "lobe-at-lambda",
      "claim": "Avec d = λ et un faisceau à 35°, le lobe de réseau est vers −25°.",
      "value": -25.2,
      "unit": "deg",
      "status": "computed",
      "formula": "asin(sin 35° − λ/d) avec d = λ",
      "sources": [],
      "usedBy": ["levels.advanced.play.spacing"]
    },
    {
      "id": "beamwidth-formula",
      "claim": "Largeur à mi-puissance d'un réseau linéaire uniforme dans l'axe : θ3dB ≈ 0,886 λ / (N d) radians.",
      "status": "verified",
      "sources": ["rfessentials-broadside", "tuberlin-ula"],
      "usedBy": ["levels.advanced.play.few-elements", "levels.advanced.play.many-elements"],
      "note": "Approximation valable quand N n'est pas trop petit ; à N = 4 elle reste correcte à quelques degrés près (vérifié par le test du champ de la lentille)."
    },
    {
      "id": "beamwidth-4",
      "claim": "N = 4, d = λ/2 : environ 25°.",
      "value": 25.4,
      "unit": "deg",
      "status": "computed",
      "formula": "0,886 / (4 × 0,5) rad",
      "sources": [],
      "usedBy": ["levels.essential.play.few-elements", "levels.advanced.play.few-elements"]
    },
    {
      "id": "beamwidth-32",
      "claim": "N = 32, d = λ/2 : environ 3°.",
      "value": 3.2,
      "unit": "deg",
      "status": "computed",
      "formula": "0,886 / (32 × 0,5) rad",
      "sources": [],
      "usedBy": ["levels.essential.play.many-elements", "levels.advanced.play.many-elements"]
    },
    {
      "id": "phase-35",
      "claim": "Faisceau à 35° avec d = λ/2 : Δφ ≈ 103°.",
      "value": 103.2,
      "unit": "deg",
      "status": "computed",
      "formula": "360° × 0,5 × sin 35°",
      "sources": [],
      "usedBy": ["levels.advanced.play.steer"]
    },
    {
      "id": "beamformer-role",
      "claim": "Les puces de formation de faisceau appliquent à chaque élément un déphasage et un gain réglables.",
      "status": "verified",
      "sources": ["adi-phased-array-2"],
      "usedBy": ["play.chips", "entity.beamformers.description"],
      "note": "Principe général des réseaux à commande de phase. L'architecture interne des puces Starlink n'est pas vérifiée."
    },
    {
      "id": "element-count",
      "claim": "Nombre d'éléments et de puces affichés.",
      "value": "1200 / 64",
      "status": "unverified",
      "sources": [],
      "usedBy": ["entities.array.params.count", "entities.beamformers.params.count"],
      "note": "Valeurs d'affichage reprises du nœud parent. Les textes disent « des centaines » et ne citent aucun nombre de puces."
    }
  ],
  "sources": [
    {
      "id": "mwrf-grating-lobes",
      "title": "Phased-Array Antenna Patterns (Part 4)—Grating Lobes",
      "url": "https://www.mwrf.com/technologies/systems/article/21141406/phasedarray-antenna-patterns-part4grating-lobes",
      "publisher": "Microwaves & RF",
      "accessed": "2026-10-10",
      "access": "search-result"
    },
    {
      "id": "adi-phased-array-2",
      "title": "Phased Array Antenna Patterns—Part 2: Grating Lobes and Beam Squint",
      "url": "https://www.analog.com/en/resources/analog-dialogue/articles/phased-array-antenna-patterns-part2.html",
      "publisher": "Analog Devices",
      "accessed": "2026-10-10",
      "access": "search-result"
    },
    {
      "id": "rfessentials-spacing",
      "title": "What is the element spacing requirement for a phased array to avoid grating lobes?",
      "url": "https://rfessentials.com/rf-knowledge-base/what-is-the-element-spacing-requirement-for-a-phased-array-to-avoid-grating-lobe/",
      "publisher": "RF Essentials",
      "accessed": "2026-10-10",
      "access": "search-result"
    },
    {
      "id": "rfessentials-broadside",
      "title": "Broadside Array",
      "url": "https://rfessentials.com/resources/rf-glossary/broadside-array/",
      "publisher": "RF Essentials",
      "accessed": "2026-10-10",
      "access": "search-result"
    },
    {
      "id": "tuberlin-ula",
      "title": "Antenna Arrays: Uniform Linear Arrays",
      "url": "https://platform.commit.tu-berlin.de/en/book/telecom/chapter/ch07/section/s02",
      "publisher": "TU Berlin",
      "accessed": "2026-10-10",
      "access": "search-result"
    },
    {
      "id": "speedcast-standard",
      "title": "Starlink Standard Kit — Product Specifications",
      "url": "https://www.speedcast.com/shop/starlink-standard-4-kit/",
      "publisher": "Speedcast",
      "accessed": "2026-10-09",
      "access": "search-result"
    }
  ]
}
```


## assistant

{
  "scene": {
    "formatVersion": "0.2",
    "node": {
      "id": "starlink-phased-array",
      "kind": "system",
      "version": 1,
      "status": "draft",
      "summaryKey": "node.summary",
      "parent": { "node": "starlink-terminal", "entity": "phased-array" }
    },
    "scale": { "metersPerUnit": 0.001 },
    "environment": { "lighting": "studio", "background": "#1d2733" },
    "performance": { "triangleBudget": 300000 },
    "clock": { "timeScale": 1 },
    "camera": {
      "home": { "target": "array", "azimuthDeg": 35, "elevationDeg": 30, "distance": 700 },
      "constraints": { "minDistance": 20, "maxDistance": 1500, "minElevationDeg": -40, "maxElevationDeg": 89 }
    },
    "entities": [
      {
        "id": "array",
        "component": "antenna-element-array",
        "params": { "lattice": "hexagonal", "count": 1200, "spacing": 0.0125, "elementShape": "square-patch" },
        "transform": { "position": [0, 0, 0] },
        "selectable": true,
        "labelKey": "entity.array.label",
        "descriptionKey": "entity.array.description"
      },
      {
        "id": "beamformers",
        "component": "ic-chip-grid",
        "parent": "array",
        "params": { "count": 64, "chipSize": 0.008 },
        "transform": { "position": [0, -8, 0] },
        "selectable": true,
        "labelKey": "entity.beamformers.label",
        "descriptionKey": "entity.beamformers.description"
      },
      {
        "id": "element",
        "component": "patch-element",
        "parent": "array",
        "params": { "patchSize": 0.008, "tileSize": 0.0125, "substrateThickness": 0.0015, "feed": "probe" },
        "transform": { "position": [0, 20, 0] },
        "visible": false,
        "selectable": true,
        "labelKey": "entity.element.label",
        "descriptionKey": "entity.element.description"
      }
    ],
    "simulators": [
      {
        "id": "beam",
        "simulator": "phased-array-wave",
        "params": {
          "frequencyHz": 12000000000,
          "elementCount": 16,
          "spacingOverLambda": 0.5,
          "steeringAngleDeg": 0,
          "tracking": false
        },
        "bind": { "array": "array" }
      }
    ],
    "lenses": [
      {
        "id": "waves-lens",
        "lens": "waves",
        "labelKey": "lens.waves.label",
        "sources": ["beam"],
        "controls": [
          { "id": "steer", "target": "beam", "param": "steeringAngleDeg", "labelKey": "control.steer", "levels": ["discovery", "essential", "advanced"], "min": -60, "max": 60, "step": 1 },
          { "id": "count", "target": "beam", "param": "elementCount", "labelKey": "control.count", "levels": ["discovery", "essential", "advanced"], "min": 2, "max": 32, "step": 1 },
          { "id": "phase", "target": "beam", "param": "phaseStepDeg", "labelKey": "control.phase", "levels": ["advanced"], "min": -180, "max": 180, "step": 1 },
          { "id": "spacing", "target": "beam", "param": "spacingOverLambda", "labelKey": "control.spacing", "levels": ["essential", "advanced"], "min": 0.25, "max": 1.5, "step": 0.05 }
        ]
      }
    ],
    "links": [
      { "kind": "composedOf", "from": "element", "to": "starlink-radiating-element", "available": true },
      { "kind": "composedOf", "from": "beamformers", "to": "starlink-beamformer" },
      { "kind": "reliesOn", "from": "array", "to": "wave-interference", "available": true },
      { "kind": "reliesOn", "to": "electromagnetic-wave" }
    ],
    "tours": [
      {
        "id": "intro",
        "autoStart": true,
        "steps": [
          {
            "id": "arrival",
            "textKey": "intro.arrival",
            "durationS": 9,
            "camera": { "shot": { "target": "array", "azimuthDeg": 35, "elevationDeg": 30, "distance": 700 }, "transitionS": 0 },
            "actions": [
              { "type": "highlight", "targets": ["array"] }
            ]
          },
          {
            "id": "layers",
            "textKey": "intro.layers",
            "durationS": 10,
            "camera": { "shot": { "target": "beamformers", "azimuthDeg": 20, "elevationDeg": -20, "distance": 450 }, "transitionS": 3 },
            "actions": [
              { "type": "highlight", "targets": ["beamformers"] },
              { "type": "label", "targets": ["array", "beamformers"] }
            ]
          },
          {
            "id": "handover-to-user",
            "textKey": "intro.handover-to-user",
            "durationS": 7,
            "camera": { "shot": { "target": "array", "azimuthDeg": 35, "elevationDeg": 30, "distance": 700 }, "transitionS": 2 }
          }
        ]
      },
      {
        "id": "main",
        "steps": [
          {
            "id": "elements",
            "textKey": "play.elements",
            "durationS": 20,
            "camera": { "shot": { "target": "element", "azimuthDeg": 30, "elevationDeg": 35, "distance": 120 }, "transitionS": 3 },
            "actions": [
              { "type": "show", "targets": ["element"] },
              { "type": "highlight", "targets": ["element"] },
              { "type": "label", "targets": ["element"] }
            ]
          },
          {
            "id": "chips",
            "textKey": "play.chips",
            "durationS": 22,
            "camera": { "shot": { "target": "beamformers", "azimuthDeg": 60, "elevationDeg": -25, "distance": 400 }, "transitionS": 3 },
            "actions": [
              { "type": "hide", "targets": ["element"] },
              { "type": "highlight", "targets": ["beamformers"] },
              { "type": "label", "targets": ["beamformers"] }
            ]
          },
          {
            "id": "steer",
            "textKey": "play.steer",
            "durationS": 32,
            "camera": { "shot": { "target": "array", "azimuthDeg": 0, "elevationDeg": 8, "distance": 900 }, "transitionS": 3 },
            "actions": [
              { "type": "setParam", "target": "beam", "param": "elementCount", "value": 16 },
              { "type": "setParam", "target": "beam", "param": "spacingOverLambda", "value": 0.5 },
              { "type": "setParam", "target": "beam", "param": "steeringAngleDeg", "value": 0 },
              { "type": "lens", "lens": "waves-lens", "on": true },
              { "type": "setParam", "target": "beam", "param": "steeringAngleDeg", "value": 35, "overS": 5 }
            ]
          },
          {
            "id": "few-elements",
            "textKey": "play.few-elements",
            "durationS": 24,
            "actions": [
              { "type": "setParam", "target": "beam", "param": "steeringAngleDeg", "value": 0 },
              { "type": "setParam", "target": "beam", "param": "elementCount", "value": 4 }
            ]
          },
          {
            "id": "many-elements",
            "textKey": "play.many-elements",
            "durationS": 24,
            "actions": [
              { "type": "setParam", "target": "beam", "param": "elementCount", "value": 32 }
            ]
          },
          {
            "id": "spacing",
            "textKey": "play.spacing",
            "durationS": 40,
            "camera": { "shot": { "target": "array", "azimuthDeg": 0, "elevationDeg": 10, "distance": 1000 }, "transitionS": 2 },
            "actions": [
              { "type": "setParam", "target": "beam", "param": "elementCount", "value": 16 },
              { "type": "setParam", "target": "beam", "param": "steeringAngleDeg", "value": 35 },
              { "type": "setParam", "target": "beam", "param": "spacingOverLambda", "value": 0.5 },
              { "type": "setParam", "target": "beam", "param": "spacingOverLambda", "value": 1, "overS": 6 }
            ]
          },
          {
            "id": "wrap",
            "textKey": "play.wrap",
            "durationS": 12,
            "camera": { "shot": { "target": "array", "azimuthDeg": 35, "elevationDeg": 30, "distance": 700 }, "transitionS": 3 },
            "actions": [
              { "type": "setParam", "target": "beam", "param": "spacingOverLambda", "value": 0.5 },
              { "type": "setParam", "target": "beam", "param": "steeringAngleDeg", "value": 0 },
              { "type": "lens", "lens": "waves-lens", "on": false },
              { "type": "show", "targets": ["element"] },
              { "type": "highlight", "targets": ["element"] },
              { "type": "label", "targets": ["element"] }
            ]
          }
        ]
      }
    ]
  },
  "texts": {
    "formatVersion": "0.2",
    "nodeId": "starlink-phased-array",
    "lang": "fr",
    "question": "Comment le réseau d'antennes de Starlink oriente-t-il son faisceau ?",
    "aliases": [
      "Comment l'antenne Starlink vise-t-elle un satellite sans bouger ?",
      "Comment fonctionne une antenne à balayage électronique ?",
      "Qu'est-ce qu'une antenne réseau à commande de phase ?"
    ],
    "common": {
      "derived.steering-angle-deg": "Direction du faisceau",
      "entity.array.label": "Réseau d'éléments rayonnants",
      "entity.beamformers.label": "Puces de formation de faisceau",
      "entity.element.label": "Élément rayonnant",
      "lens.waves.label": "Ondes",
      "control.steer": "Angle du faisceau",
      "control.count": "Nombre d'éléments (coupe)",
      "control.phase": "Déphasage entre voisins",
      "control.spacing": "Espacement d / λ",
      "entity.array.description": "Des centaines de petites antennes identiques, espacées d'environ un centimètre. Ensemble, elles forment un faisceau qu'on oriente sans rien bouger.",
      "entity.beamformers.description": "Des puces qui règlent, pour chaque petite antenne, un léger décalage et une puissance. C'est ce décalage qui oriente le faisceau.",
      "entity.element.description": "Une seule petite antenne : un carré de cuivre posé sur une couche isolante, au-dessus d'un plan de cuivre."
    },
    "levels": {
      "discovery": {
        "node.summary": "Des centaines de petites antennes qui chantent ensemble, chacune un tout petit peu après sa voisine : c'est comme ça que l'antenne vise le satellite sans bouger.",
        "entity.array.label": "Les petites antennes",
        "entity.beamformers.label": "Les puces chefs d'orchestre",
        "entity.element.label": "Une petite antenne",
        "control.steer": "Direction du faisceau",
        "control.count": "Nombre d'antennes",
        "entity.array.description": "Des centaines de toutes petites antennes, rangées comme les cases d'un nid d'abeilles. Elles travaillent ensemble, comme une chorale.",
        "entity.beamformers.description": "Elles disent à chaque petite antenne quand « chanter », un tout petit peu avant ou après sa voisine.",
        "entity.element.description": "Une seule petite antenne : un carré de métal posé sur une plaque, pas plus grand qu'un ongle.",

        "intro.arrival": "Nous voici sous la surface de l'antenne Starlink. Regarde : des centaines de toutes petites antennes, rangées serrées comme les cases d'un nid d'abeilles.",
        "intro.layers": "Juste en dessous, des puces leur donnent des ordres. Ensemble, elles fabriquent un faisceau d'ondes radio qu'on peut tourner sans rien bouger.",
        "intro.handover-to-user": "Touche une pièce pour aller voir dedans, ou appuie sur Play pour la visite.",

        "play.elements": "Chacune de ces petites antennes envoie des ondes radio vers le ciel. Toute seule, elle est très faible, et ses ondes partent un peu partout. Mais elles sont des centaines, et elles travaillent ensemble, comme une chorale.",
        "play.chips": "Sous les antennes, il y a des puces. Ce sont les chefs d'orchestre : elles disent à chaque petite antenne quand chanter, un tout petit peu avant ou après sa voisine.",
        "play.steer": "Voici les ondes. Quand toutes les petites antennes chantent en même temps, le faisceau part tout droit vers le haut. Maintenant, chaque antenne attend un tout petit peu plus que sa voisine. Regarde : le faisceau penche sur le côté ! Rien n'a bougé, seul le moment où chaque onde part a changé.",
        "play.few-elements": "Avec seulement quatre petites antennes, le faisceau est très large, comme une lampe de poche sans miroir. On éclaire partout, mais pas très fort.",
        "play.many-elements": "Avec beaucoup plus d'antennes, le faisceau devient fin comme le rayon d'un phare. Presque toute l'énergie part dans la même direction, vers le satellite.",
        "play.spacing": "Et si on écartait les petites antennes ? Regarde : un deuxième faisceau apparaît, et il part dans la mauvaise direction ! Une partie des ondes est gâchée. C'est pour ça que les antennes sont serrées : environ un centimètre entre deux voisines.",
        "play.wrap": "Voilà l'astuce de l'antenne plate : des centaines de petites voix bien réglées. Touche une petite antenne pour voir comment elle est faite."
      },
      "essential": {
        "node.summary": "Des centaines de petites antennes émettent la même onde avec un léger décalage de l'une à l'autre : leurs ondes s'additionnent dans une seule direction, qu'on change électroniquement.",

        "intro.arrival": "Sous le capot de l'antenne Starlink : des centaines d'éléments rayonnants identiques, espacés d'environ un centimètre, soit une demi-longueur d'onde.",
        "intro.layers": "Derrière eux, des puces règlent le signal de chaque élément. C'est ce réglage qui oriente le faisceau, sans aucune pièce mobile.",
        "intro.handover-to-user": "Touchez une pièce pour plonger à l'intérieur, ou lancez la visite guidée.",

        "play.elements": {
          "text": "Chaque élément est une petite antenne plate, qui émet et reçoit des ondes radio vers 12 gigahertz. Seul, il rayonne dans presque toutes les directions du ciel. Le faisceau étroit naît du travail d'équipe de tous les éléments.",
          "links": [
            { "phrase": "Chaque élément est une petite antenne plate", "node": "starlink-radiating-element" }
          ]
        },
        "play.chips": "Juste derrière, des puces de formation de faisceau appliquent à chaque élément deux réglages : un léger décalage dans le temps, qu'on appelle un déphasage, et une puissance. Leur conception exacte chez Starlink n'est pas connue en détail, mais le principe est celui de toutes les antennes de ce type.",
        "play.steer": {
          "text": "Allumons la lentille Ondes, sur une coupe de seize éléments. Tous en phase : les ondes s'additionnent droit vers le haut. Décalons maintenant chaque élément un peu plus que son voisin. Les crêtes s'alignent dans une direction inclinée, et le faisceau tourne jusqu'à 35 degrés. Le panneau, lui, n'a pas bougé.",
          "links": [
            { "phrase": "Les crêtes s'alignent dans une direction inclinée", "node": "wave-interference" }
          ]
        },
        "play.few-elements": "Le nombre d'éléments compte. Avec une coupe de seulement quatre éléments, le faisceau est large : environ 25 degrés. L'énergie s'étale sur une grande partie du ciel, et une petite part seulement va vers le satellite.",
        "play.many-elements": "Avec 32 éléments, le faisceau ne fait plus qu'environ 3 degrés de large. Plus il y a d'éléments alignés, plus le faisceau est fin, et plus le signal est concentré vers le satellite. Le vrai panneau en compte des centaines.",
        "play.spacing": "Pourquoi les éléments sont-ils si serrés ? Écartons-les jusqu'à une longueur d'onde entière, avec le faisceau toujours à 35 degrés. Un second faisceau apparaît, vers environ 25 degrés de l'autre côté : c'est un lobe de réseau. Il gaspille de l'énergie dans une direction inutile. Avec un écart d'une demi-longueur d'onde, environ un centimètre, aucun lobe de ce genre n'apparaît, quelle que soit la direction visée.",
        "play.wrap": "Des centaines d'éléments, un décalage réglé pour chacun : voilà comment l'antenne vise sans bouger. Touchez un élément pour voir comment il est fait."
      },
      "advanced": {
        "node.summary": "Antenne réseau à commande de phase : une progression linéaire de phase entre éléments espacés d'environ une demi-longueur d'onde oriente le lobe principal, sans lobe de réseau dans l'espace visible.",
        "entity.array.description": "Réseau plan à maille hexagonale d'éléments imprimés, au pas d'environ une demi-longueur d'onde (≈ 1,25 cm à 12 GHz). Pas réel du terminal Starlink non vérifié.",
        "entity.beamformers.description": "Circuits intégrés appliquant à chaque élément un déphasage et un gain réglables. Architecture interne des puces Starlink non vérifiée.",
        "entity.element.description": "Élément patch imprimé : carré de cuivre sur substrat diélectrique, plan de masse dessous, alimenté par une sonde à travers le substrat.",

        "intro.arrival": "Réseau plan d'éléments imprimés, en bande Ku. À 12 gigahertz, la longueur d'onde vaut environ 2,5 centimètres ; le pas, environ la moitié.",
        "intro.layers": "Sous le réseau, les circuits de formation de faisceau appliquent à chaque élément un déphasage et un gain.",
        "intro.handover-to-user": "Sélectionnez un sous-ensemble pour descendre d'un niveau, ou lancez la visite.",

        "play.elements": {
          "text": "Chaque élément, une antenne imprimée, rayonne seul un diagramme large vers le ciel. La directivité du terminal vient de la somme cohérente des champs de tous les éléments : c'est le facteur de réseau.",
          "links": [
            { "phrase": "antenne imprimée", "node": "starlink-radiating-element" }
          ]
        },
        "play.chips": "Les circuits de formation de faisceau appliquent à chaque élément un déphasage et un gain réglables. Le gain pondère l'amplitude de chaque élément ; le déphasage fixe la direction du lobe principal. L'architecture interne des puces Starlink, et le nombre d'éléments servis par chaque puce, ne sont pas vérifiés.",
        "play.steer": {
          "text": "Avec un déphasage delta phi constant entre voisins, le lobe principal pointe dans la direction thêta zéro, mesurée depuis la normale au panneau, telle que delta phi égale deux pi fois d fois sinus thêta zéro, divisé par lambda, où d est le pas entre éléments et lambda la longueur d'onde. Avec un pas d'une demi-longueur d'onde, viser 35 degrés demande un déphasage d'environ 103 degrés.",
          "subtitle": "Déphasage constant $\\Delta\\varphi$ entre voisins : le lobe principal pointe vers $\\theta_0$ tel que $\\Delta\\varphi = \\dfrac{2\\pi\\, d \\sin\\theta_0}{\\lambda}$. Avec $d = \\lambda/2$, viser $\\theta_0 = 35^\\circ$ demande $\\Delta\\varphi \\approx 103^\\circ$.",
          "terms": [
            { "symbol": "\\Delta\\varphi", "meaning": "déphasage entre deux éléments voisins", "unit": "rad ou °" },
            { "symbol": "\\theta_0", "meaning": "direction du lobe principal, mesurée depuis la normale au panneau", "unit": "°" },
            { "symbol": "d", "meaning": "pas entre deux éléments voisins", "unit": "≈ 1,25 cm" },
            { "symbol": "\\lambda", "meaning": "longueur d'onde", "unit": "≈ 2,5 cm à 12 GHz" }
          ],
          "links": [
            { "phrase": "Déphasage constant", "node": "wave-interference" }
          ]
        },
        "play.few-elements": {
          "text": "Dans l'axe, la largeur du lobe à mi-puissance vaut environ 0,886 fois lambda, divisé par N fois d, en radians, où lambda est la longueur d'onde, N le nombre d'éléments de la coupe et d le pas. Avec quatre éléments au pas d'une demi-longueur d'onde, on trouve environ 25 degrés.",
          "subtitle": "Largeur à mi-puissance dans l'axe : $\\theta_{3\\,\\mathrm{dB}} \\approx 0{,}886\\,\\dfrac{\\lambda}{N d}$ rad. Pour $N = 4$ et $d = \\lambda/2$ : $\\theta_{3\\,\\mathrm{dB}} \\approx 25^\\circ$.",
          "terms": [
            { "symbol": "\\theta_{3\\,\\mathrm{dB}}", "meaning": "largeur du lobe principal à mi-puissance", "unit": "rad" },
            { "symbol": "\\lambda", "meaning": "longueur d'onde", "unit": "≈ 2,5 cm" },
            { "symbol": "N", "meaning": "nombre d'éléments de la coupe linéaire" },
            { "symbol": "d", "meaning": "pas entre deux éléments voisins", "unit": "cm" }
          ]
        },
        "play.many-elements": {
          "text": "Avec 32 éléments au même pas, la même formule, 0,886 fois lambda divisé par N fois d, donne environ 3 degrés, lambda étant la longueur d'onde, N le nombre d'éléments et d le pas. La largeur du lobe varie comme l'inverse de la longueur du réseau, N fois d.",
          "subtitle": "$N = 32$, $d = \\lambda/2$ : $\\theta_{3\\,\\mathrm{dB}} \\approx 0{,}886\\,\\dfrac{\\lambda}{N d} = \\dfrac{0{,}886}{16}\\ \\text{rad} \\approx 3^\\circ$. La largeur varie comme $1/(N d)$.",
          "terms": [
            { "symbol": "\\theta_{3\\,\\mathrm{dB}}", "meaning": "largeur du lobe principal à mi-puissance", "unit": "rad" },
            { "symbol": "\\lambda", "meaning": "longueur d'onde", "unit": "≈ 2,5 cm" },
            { "symbol": "N", "meaning": "nombre d'éléments de la coupe linéaire" },
            { "symbol": "d", "meaning": "pas entre deux éléments voisins", "unit": "cm" }
          ]
        },
        "play.spacing": {
          "text": "Le réseau rayonne aussi dans les directions thêta m telles que sinus thêta m égale sinus thêta zéro plus m fois lambda sur d, où m est un entier, lambda la longueur d'onde et d le pas. Pour m non nul, ce sont des lobes de réseau. Avec d égal à lambda et un faisceau à 35 degrés, l'un d'eux apparaît vers moins 25 degrés. Pour n'en avoir aucun jusqu'à 55 degrés de dépointage, moitié du champ de vision de 110 degrés supposé symétrique, il faut d inférieur à lambda sur un plus sinus 55 degrés, soit environ 0,55 lambda.",
          "subtitle": "Lobes de réseau : $\\sin\\theta_m = \\sin\\theta_0 + m\\,\\dfrac{\\lambda}{d}$, $m \\neq 0$. Avec $d = \\lambda$ et $\\theta_0 = 35^\\circ$ : un lobe vers $-25^\\circ$. Aucun lobe jusqu'à $\\pm 55^\\circ$ (moitié du champ de vision de 110°, supposé symétrique) si $d < \\dfrac{\\lambda}{1 + \\sin 55^\\circ} \\approx 0{,}55\\,\\lambda$.",
          "terms": [
            { "symbol": "\\theta_m", "meaning": "direction du lobe d'ordre m (m non nul : lobe de réseau), depuis la normale au panneau", "unit": "°" },
            { "symbol": "\\theta_0", "meaning": "direction du lobe principal, depuis la normale au panneau", "unit": "°" },
            { "symbol": "m", "meaning": "ordre du lobe, un entier" },
            { "symbol": "\\lambda", "meaning": "longueur d'onde", "unit": "≈ 2,5 cm" },
            { "symbol": "d", "meaning": "pas entre deux éléments voisins", "unit": "cm" }
          ]
        },
        "play.wrap": "Pointage purement électronique : une progression linéaire de phase, et un pas sous la limite d'apparition des lobes de réseau. Sélectionnez un élément pour descendre d'un niveau."
      }
    }
  }
}


## user

The validator rejected your node with these errors:

- starlink-radiating-element: explorable from 'starlink-phased-array' but has no summaryKey

Fix them and answer again with the complete corrected JSON object `{"scene": …, "texts": …}`, nothing else.

