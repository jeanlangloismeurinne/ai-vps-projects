"""Validation de la vue knowledge_federation_export contre envelope.schema.json.

Vérifie que chaque ligne retournée par la vue respecte le contrat normalisé
templates/knowledge-base/envelope.schema.json.

Dépendances : stdlib uniquement (json, subprocess, sys, pathlib, re).
La connexion à Postgres se fait via `docker exec shared-postgres psql …`
ou via la variable d'env DATABASE_URL si psycopg2 est disponible.

Usage :
  python checks/check_kb_export.py                      # via docker exec (défaut)
  DATABASE_URL=postgresql://admin:...@host/db python checks/check_kb_export.py

Codes de sortie :
  0 — tous les checks OK
  1 — au moins un check KO
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ── Helpers ──────────────────────────────────────────────────────────────────

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  OK  {label}")
    else:
        fail += 1
        print(f"  KO  {label}{(' — ' + detail) if detail else ''}")


# ── Chargement du schéma ──────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[3]  # …/ai-vps-projects
SCHEMA_PATH = REPO_ROOT / "templates" / "knowledge-base" / "envelope.schema.json"

if not SCHEMA_PATH.exists():
    print(f"ERREUR : schéma introuvable : {SCHEMA_PATH}")
    sys.exit(1)

with SCHEMA_PATH.open() as f:
    SCHEMA = json.load(f)

REQUIRED_FIELDS: list[str] = SCHEMA.get("required", [])
PROPERTIES: dict = SCHEMA.get("properties", {})

# Valeurs enum connues du schéma
SOURCE_ENUM: list[str] = PROPERTIES.get("source", {}).get("enum", [])
VISIBILITY_ENUM: list[str] = PROPERTIES.get("visibility", {}).get("enum", [])

# Pattern doc_id (extrait du schéma)
DOC_ID_PATTERN: str = PROPERTIES.get("doc_id", {}).get("pattern", "")

# ── Récupération des lignes de la vue ─────────────────────────────────────────

SQL = "SELECT row_to_json(t) FROM knowledge_federation_export t;"

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    # Chemin psycopg2 (container ou CI avec dépendances)
    try:
        import psycopg2  # type: ignore
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(SQL)
        rows = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
    except ImportError:
        print("ERREUR : DATABASE_URL défini mais psycopg2 absent.")
        sys.exit(1)
else:
    # Chemin docker exec (défaut, aucune dépendance)
    cmd = [
        "docker", "exec", "shared-postgres",
        "psql", "-U", "admin", "-d", "db_assistant",
        "-t", "-A", "-c", SQL,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERREUR psql : {result.stderr.strip()}")
        sys.exit(1)

    raw_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    rows = []
    for line in raw_lines:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"ERREUR JSON sur la ligne : {line!r} — {exc}")
            sys.exit(1)

# ── Contrôle 1 : la vue existe et est requêtable ──────────────────────────────

print("1. La vue knowledge_federation_export est requêtable")
check("requête sans erreur (même sur table vide)", True)  # on est arrivé jusqu'ici

# ── Contrôle 2 : schema sur chaque ligne ─────────────────────────────────────

print(f"\n2. Validation de {len(rows)} ligne(s) contre envelope.schema.json")

if not rows:
    print("  (table vide — checks de contenu ignorés, mais la vue est valide)")
else:
    for i, row in enumerate(rows):
        label_prefix = f"ligne {i + 1} [{row.get('doc_id', '?')}]"

        # Champs obligatoires présents et non NULL
        for field in REQUIRED_FIELDS:
            check(
                f"{label_prefix} — champ obligatoire '{field}' présent",
                row.get(field) is not None,
                f"valeur : {row.get(field)!r}",
            )

        # doc_id : pattern {project}:{source}:{local_id}
        doc_id = row.get("doc_id", "")
        if DOC_ID_PATTERN:
            check(
                f"{label_prefix} — doc_id respecte le pattern",
                bool(re.match(DOC_ID_PATTERN, doc_id)),
                f"doc_id={doc_id!r}",
            )

        # source : valeur dans l'enum
        if SOURCE_ENUM:
            check(
                f"{label_prefix} — source dans l'enum",
                row.get("source") in SOURCE_ENUM,
                f"source={row.get('source')!r}",
            )

        # visibility : valeur dans l'enum
        if VISIBILITY_ENUM:
            check(
                f"{label_prefix} — visibility dans l'enum",
                row.get("visibility") in VISIBILITY_ENUM,
                f"visibility={row.get('visibility')!r}",
            )

        # tags : tableau (jamais null)
        tags = row.get("tags")
        check(
            f"{label_prefix} — tags est un tableau non null",
            isinstance(tags, list),
            f"tags={tags!r}",
        )

        # reliability : number 0..1
        rel = row.get("reliability")
        if rel is not None:
            check(
                f"{label_prefix} — reliability dans [0, 1]",
                isinstance(rel, (int, float)) and 0.0 <= float(rel) <= 1.0,
                f"reliability={rel!r}",
            )

        # content_hash : non vide
        ch = row.get("content_hash", "")
        check(
            f"{label_prefix} — content_hash non vide",
            bool(ch),
            f"content_hash={ch!r}",
        )

        # title : minLength 1
        title = row.get("title", "")
        check(
            f"{label_prefix} — title non vide",
            bool(title),
            f"title={title!r}",
        )

        # body : présent (string)
        body = row.get("body")
        check(
            f"{label_prefix} — body présent",
            isinstance(body, str) and len(body) > 0,
            f"body={str(body)[:40]!r}",
        )

        # created_at / updated_at : format date-time approximatif (présence de T ou espace + Z/+)
        for ts_field in ("created_at", "updated_at", "ingested_at"):
            ts = row.get(ts_field, "")
            check(
                f"{label_prefix} — {ts_field} ressemble à une date-time",
                bool(ts) and ("T" in ts or " " in ts),
                f"{ts_field}={ts!r}",
            )

        # Aucun champ hors-contrat ne doit fuiter dans les colonnes de l'enveloppe
        # (slack_ts, contexte, nature sont dans metadata — pas au niveau racine)
        for forbidden in ("slack_ts", "contexte", "nature"):
            check(
                f"{label_prefix} — champ hors-enveloppe '{forbidden}' absent au niveau racine",
                forbidden not in row,
                f"champ présent : {row.get(forbidden)!r}",
            )

# ── Contrôle 3 : idempotence de la vue (CREATE OR REPLACE) ───────────────────

print("\n3. Idempotence de la définition de la vue")
# La vue est déjà là (on a pu la requêter) — on vérifie qu'elle est une VIEW, pas une TABLE
cmd_type = [
    "docker", "exec", "shared-postgres",
    "psql", "-U", "admin", "-d", "db_assistant",
    "-t", "-A", "-c",
    "SELECT table_type FROM information_schema.tables "
    "WHERE table_name = 'knowledge_federation_export' AND table_schema = 'public';",
]
result_type = subprocess.run(cmd_type, capture_output=True, text=True)
obj_type = result_type.stdout.strip()
check(
    "knowledge_federation_export est une VIEW",
    "VIEW" in obj_type,
    f"type={obj_type!r}",
)

# ── Résumé ────────────────────────────────────────────────────────────────────

print(f"\n{'=' * 60}")
print(f"{ok} OK / {fail} KO")
sys.exit(1 if fail else 0)
