"""L'EXEMPLE DE SORTIE D'UNE CONSIGNE SE VALIDE CONTRE LE CONTRAT (#121, 2026-10-13).

Un contrat d'entry a trois points de synchro (#19/#39) : le CHECK SQL, le schéma Pydantic, et
l'EXEMPLE JSON de la consigne en base. Le modèle recopie l'exemple ; la consigne elle-même dit
« aucune clef hors de l'exemple ». Deux fois déjà le troisième point a été oublié :

  · 2026-09-10 (migration 037) — `covers`/`question_status` retirés du contrat, encore dans l'exemple ;
  · 2026-09-23 → 2026-10-13 (#121) — `source_date` retiré du contrat par la 045 (#79), encore dans
    l'exemple des consignes `search-worker` et `ingestion-agent`. Le collecteur rendait l'ANCIEN
    format, le contrat le refusait (à juste titre), la collecte se perdait : 15 mandats
    `echec_collecte` depuis le 2026-09-25, dont NVDA qf_8 (mandats 2612/2613). Aucun check ne
    rougissait : les fixtures étaient déjà au nouveau format.

Ce check ferme la classe, pas le cas : chaque pièce de l'exemple de sortie est validée par
`ProducedEntry` — le contrat qui la jugera en production — à ses DEUX points de lecture :

  • §1 le FICHIER versionné (`provenance-cards/prompts/`, monté en `/contract_frozen`) ;
  • §2 le texte EN BASE (`agent_prompts`, flow v2) — celui que l'agent lit vraiment. Lecture seule.

Un pré-requis manquant (montage, `CHECK_DB_URL`) sort en ÉCHEC, jamais en saut de section
(`feedback_check_degrade_en_sortant_a_zero`).
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from _harness import Bilan  # noqa: E402

from pydantic import ValidationError  # noqa: E402

from app.contracts.worker_delegation_schema import ProducedEntry  # noqa: E402

b = Bilan()

# (fichier de consigne, agent en base) — les deux producteurs de pièces par modèle.
CONSIGNES = [("10-ingestion-agent.md", "ingestion-agent"), ("11-search-worker.md", "search-worker")]
PROMPTS = Path("/contract_frozen/prompts")


def entrees_de_l_exemple(texte: str) -> list:
    """Le tableau `"entries": [...]` de l'exemple de SORTIE, extrait par appariement de crochets
    (chaînes JSON respectées) puis parsé. Le reste du bloc porte des « … » non JSON : on ne parse
    que le tableau. Lève si absent ou illisible — un exemple introuvable n'est pas un exemple sain."""
    i = texte.find('"entries": [')
    if i < 0:
        raise ValueError("aucun `\"entries\": [` dans la consigne")
    debut = texte.index("[", i)
    prof, dans_chaine, echap = 0, False, False
    for j in range(debut, len(texte)):
        c = texte[j]
        if dans_chaine:
            if echap:
                echap = False
            elif c == "\\":
                echap = True
            elif c == '"':
                dans_chaine = False
        elif c == '"':
            dans_chaine = True
        elif c == "[":
            prof += 1
        elif c == "]":
            prof -= 1
            if prof == 0:
                return json.loads(texte[debut:j + 1])
    raise ValueError("tableau `entries` non refermé")


def eprouver(origine: str, texte: str) -> None:
    try:
        entrees = entrees_de_l_exemple(texte)
    except (ValueError, json.JSONDecodeError) as e:
        b.check(False, f"{origine} : exemple de sortie illisible ({e})")
        return
    b.check(len(entrees) >= 1, f"{origine} : l'exemple de sortie porte au moins une pièce "
                               f"(sinon il n'enseigne aucun format — `all()` sur vide)")
    for k, e in enumerate(entrees):
        try:
            ProducedEntry.model_validate(e)
            b.check(True, "")
        except ValidationError as err:
            champs = sorted({".".join(str(x) for x in d["loc"]) or "(objet)" for d in err.errors()})
            b.check(False, f"{origine} : la pièce n°{k} de l'exemple est REFUSÉE par le contrat "
                           f"(champs : {champs}) — le modèle recopie l'exemple")


# ── §1 le fichier versionné ──────────────────────────────────────────────────────────────────────
print("[1] l'exemple du FICHIER de consigne se valide contre le contrat")
if not PROMPTS.is_dir():
    b.check(False, f"{PROMPTS} absent — montage `/contract_frozen` manquant (run_all.sh)")
else:
    for fichier, _agent in CONSIGNES:
        p = PROMPTS / fichier
        if not b.check(p.is_file(), f"fichier de consigne {fichier} introuvable"):
            continue
        eprouver(f"fichier {fichier}", p.read_text(encoding="utf-8"))

# ── §2 le texte en base — le point de lecture de l'agent ─────────────────────────────────────────
print("\n[2] l'exemple de la consigne EN BASE se valide contre le contrat")
_DB = os.environ.get("CHECK_DB_URL") or ""
if not _DB:
    b.check(False, "CHECK_DB_URL absente — §2 n'a pas lu les consignes en base")
else:
    import asyncpg  # noqa: E402

    async def _lire() -> dict:
        conn = await asyncpg.connect(_DB.replace("postgresql+asyncpg://", "postgresql://"))
        try:
            rows = await conn.fetch(
                "SELECT agent_name, prompt_text FROM agent_prompts "
                "WHERE flow_version = 'v2' AND agent_name = ANY($1::text[])",
                [a for _, a in CONSIGNES])
            return {r["agent_name"]: r["prompt_text"] for r in rows}
        finally:
            await conn.close()

    try:
        en_base = asyncio.run(_lire())
    except Exception as e:  # noqa: BLE001 — une base injoignable est un échec NOMMÉ
        b.check(False, f"lecture des consignes en base impossible : {type(e).__name__}: {e}")
        en_base = None
    if en_base is not None:
        b.require(en_base, len(CONSIGNES), "consignes v2 trouvées en base")
        for _fichier, agent in CONSIGNES:
            if agent in en_base:
                eprouver(f"base {agent}", en_base[agent])

sys.exit(b.summary())
