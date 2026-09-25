#!/usr/bin/env python3
"""Les pages Hub « Newsletter » existantes ne doivent pas changer quand on ajoute l'onglet Alias.

Le formulaire d'édition de prompt est factorisé pour servir aux alias ; ce check exige que le rendu
des deux pages d'aujourd'hui (`_page_kb`, `_page_prompt`) reste identique octet pour octet, hors
l'onglet ajouté (retiré de la comparaison, voir `_sans_onglet_alias`).

  --capture   fige le rendu ACTUEL (à faire AVANT de modifier newsletter.py, jamais après)
  (défaut)    compare au rendu figé

Lancer (image de prod, sans dépendance hôte) :
  docker run --rm -v $PWD:/w -w /w -e PYTHONDONTWRITEBYTECODE=1 \
    hub-homepage:latest python checks/check_newsletter_pages.py
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import newsletter as nl  # noqa: E402

GOLDEN = Path(__file__).resolve().parent / "golden" / "newsletter_pages.json"

# Forme réelle de la réponse `GET /api/prompt` (cf. newsletter-summary/app/main.py::api_prompt).
PROMPT_DATA = {
    "active_id": 3,
    "active_prompt": "Résume le CORPS d'une newsletter en HTML.\nEMAIL À RÉSUMER :\n{email}",
    "versions": [
        {"id": 3, "created_at": "2026-09-04T10:00:00", "note": "v3 — 600 mots max", "prompt": "p3", "is_active": True},
        {"id": 2, "created_at": "2026-09-02T09:30:00", "note": "", "prompt": "Prompt deux <b>", "is_active": False},
        {"id": 1, "created_at": "2026-09-01T08:00:00", "note": "Version initiale (défaut d'env) très longue note", "prompt": "p1", "is_active": False},
    ],
}
KB_DOCS = [{
    "title": "Migration Pact 2.0?", "created_at": "2026-09-25T04:30:50", "tags": ["a", "b<"],
    "body": "# Titre\n- point **fort**\n```\ncode\n```", "metadata": {"from_addr": "no-reply@newsletter.euractiv.com"},
    "uri": "resend:x",
}]


def _sans_onglet_alias(html: str) -> str:
    """Retire l'onglet ajouté par le chantier alias : seul écart légitime du rendu."""
    return re.sub(r'\s*<a class="tab[^"]*" href="/newsletter/aliases[^"]*">[^<]*</a>', "", html)


def render() -> dict:
    return {
        "kb": nl._page_kb(KB_DOCS),
        "kb_vide": nl._page_kb([]),
        "kb_erreur": nl._page_kb([], error="Service injoignable"),
        "prompt": nl._page_prompt(PROMPT_DATA),
        "prompt_saved": nl._page_prompt(PROMPT_DATA, flash="saved"),
        "prompt_err": nl._page_prompt({}, error="boom"),
    }


if "--capture" in sys.argv:
    GOLDEN.write_text(json.dumps(render(), ensure_ascii=False, indent=1) + "\n")
    print(f"figé : {GOLDEN} ({len(render())} pages)")
    sys.exit(0)

gold = json.loads(GOLDEN.read_text())
now = {k: _sans_onglet_alias(v) for k, v in render().items()}
bad = [k for k in gold if now.get(k) != _sans_onglet_alias(gold[k])]
assert not bad, f"pages Hub modifiées par le refactor : {bad}"
print(f"OK — {len(gold)} pages identiques à la ligne de base")
