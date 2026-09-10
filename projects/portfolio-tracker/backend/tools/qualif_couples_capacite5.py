"""Ligne de base de la capacité 5b — combien de couples du corpus sont VRAIMENT divergents ?

POURQUOI CET OUTIL EXISTE
-------------------------
`tools/mesure_conflits_capacite5.py` a établi, à coût de modèle nul, que la règle d'appariement par
`covers` propose **92 paires** sur les trois émetteurs. Il s'arrête là volontairement : juger deux
proses l'une contre l'autre demande un modèle, et l'anticiper en Python fabriquerait une ligne de
base que le code ne produit pas.

Cet outil est l'étage suivant, et il ne se lance qu'APRÈS le filtre gratuit :

  92 paires brutes
   -59  les deux entries viennent du MÊME document (`source_url` identique) — quatre facteurs de
        risque d'un même 10-Q ne sont pas deux sources qui se contredisent. La doctrine arbitrée
        parle de « deux sources » : un même document n'en est qu'une.
   - 4  documents distincts mais même `source_type` ET même `source_date` (même publication, même
        jour) — même raisonnement.
   ----
    29  couples opposant des sources réellement distinctes → soumis au jugement ci-dessous.

CE QU'IL MESURE
---------------
Pour chacun des 29 couples, un verdict en QUATRE états jamais recombinés (#44/#53) :

  divergence            les deux entries répondent à la MÊME question et ne disent pas la même
                        chose — c'est la seule matière de 5b.
  facettes              elles parlent du même champ sous deux angles complémentaires. Elles ne se
                        contredisent pas ; les additionner enrichit le dossier.
  meme_fait_deux_dates  la même assertion à deux moments. Ce n'est pas une contradiction, c'est de
                        la péremption — déjà traitée par la capacité 4 (le remède est un
                        rafraîchissement, pas un arbitrage).
  non_comparable        elles n'adressent pas la même question, malgré un `covers` commun.

Le quatrième état est celui qui compte le plus : la capacité 5a a été fondée hier sur un couple
(MSFT #97/#98) que la lecture a révélé `non_comparable` — un dépôt qui déclare NE PAS publier le
chiffre, face à un indicateur voisin de presse.

CE QU'IL NE FAIT PAS
--------------------
Aucune écriture, aucun `superseded_by`, aucun `UPDATE`. Il ne persiste pas son verdict : un
jugement rendu est une mesure de l'instant, pas un fait du corpus (#49). Il n'invente pas non plus
la règle d'appariement — il rejoue celle que la spec propose, pour en mesurer le rendement réel.

⚠️ Le verdict du modèle est une MESURE, pas une vérité : il sert à décider si 5b a de la matière.
Les couples `divergence` sont imprimés en entier pour être relus à la main.

Usage : `bash tools/qualif_couples.sh`
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.runner import run_json_agent
from app.db.database import close_pool, get_db_session, init_pool
from tools._corpus_archive import ENTRIES, bandeau

TICKERS = ["NVDA", "MSFT", "RVMD"]

_SQL_ACTIVES = f"""
    SELECT id, ticker_id, source_type, source_date, source_url, reliability_tier, nature,
           covers, title, content
      FROM {ENTRIES}
     WHERE superseded_by IS NULL AND is_deleted = FALSE AND ticker_id = ANY($1::text[])
     ORDER BY id
"""

_SYSTEM = (
    "Tu es analyste d'investissement. On te soumet DEUX extraits d'un dossier de connaissance qui "
    "documentent le MÊME champ d'analyse sur le même émetteur, issus de DEUX sources distinctes. "
    "Ta seule tâche est de qualifier leur relation. Tu ne réécris rien, tu ne tranches pas laquelle "
    "est vraie, tu ne recommandes rien.\n\n"
    "Quatre verdicts, mutuellement exclusifs :\n"
    "- `divergence` : les deux extraits répondent à la MÊME question et donnent des réponses "
    "incompatibles. Un lecteur devrait choisir. C'est le seul verdict qui engage un arbitrage.\n"
    "- `facettes` : ils éclairent le même champ sous deux angles complémentaires. Rien ne s'oppose ; "
    "un lecteur les lit tous les deux et en sait plus.\n"
    "- `meme_fait_deux_dates` : c'est la même assertion à deux moments (deux exercices, deux "
    "trimestres). L'un est simplement plus récent que l'autre.\n"
    "- `non_comparable` : malgré leur rattachement au même champ, ils n'adressent pas la même "
    "question — y compris le cas où l'un déclare qu'une donnée n'est PAS publiée et l'autre fournit "
    "un indicateur voisin.\n\n"
    "En cas d'hésitation entre `divergence` et `facettes`, choisis `facettes` : appeler divergence "
    "ce qui n'en est pas noierait un arbitrage réel sous du bruit."
)


class QualifCouple(BaseModel):
    """Le verdict porte sur la RELATION entre deux extraits, jamais sur leur véracité."""

    model_config = {"extra": "forbid"}

    verdict: Literal["divergence", "facettes", "meme_fait_deux_dates", "non_comparable"]
    # ⚠️ Plafond desserré de 400 à 900 après le 1er passage : un couple avait été REFUSÉ par le
    # contrat pour un motif trop long, et son texte tronqué contenait « contradiction directe ».
    # Une limite de forme qui écarte le seul couple potentiellement divergent fabriquerait un
    # zéro rassurant produit par la pire des raisons (#49). La mesure a été rejouée en entier.
    motif: str = Field(..., min_length=10, max_length=900)


def _paires_sources_distinctes(entries: list[dict[str, Any]]) -> list[tuple[dict, dict, str]]:
    """Les couples que 5b aurait à arbitrer : même champ, même émetteur, SOURCES distinctes.

    Le filtre gratuit est ici, et il est fidèle à la doctrine (« deux sources peuvent se
    contredire ») : deux extraits d'un même document ne sont pas deux sources.
    """
    par_champ: dict[tuple[str, str], list[dict]] = {}
    for e in entries:
        for champ in (e["covers"] or []):
            par_champ.setdefault((e["ticker_id"], champ), []).append(e)

    couples: list[tuple[dict, dict, str]] = []
    for (_ticker, champ), lot in sorted(par_champ.items()):
        for i, a in enumerate(lot):
            for b in lot[i + 1:]:
                if a["source_url"] == b["source_url"]:
                    continue  # même document → une seule source
                if a["source_type"] == b["source_type"] and a["source_date"] == b["source_date"]:
                    continue  # même publication le même jour
                couples.append((a, b, champ))
    return couples


def _extrait(e: dict[str, Any]) -> str:
    return (
        f"#{e['id']} — source : {e['source_type']} (rang {e['reliability_tier']}), "
        f"date : {e['source_date'] or 'non datée'}, nature : {e['nature']}\n"
        f"Titre : {e['title']}\n"
        f"Contenu : {e['content']}"
    )


async def _resoudre_agent() -> ResolvedAgent:
    """Réutilise le provider + modèle configurés en DB, avec un prompt système propre à la mesure
    (le prompt DB de l'agent est celui de sa tâche, il n'a rien à voir avec cette qualification)."""
    base = await get_agent_provider("ingestion-agent", "v2")
    return ResolvedAgent(
        agent_name="ingestion-agent", flow_version="v2",
        provider=base.provider, model=base.model, system_prompt=_SYSTEM,
    )


async def main() -> int:
    print(bandeau())
    # ⚠️ `get_agent_provider` lit sa config par `get_db_session()`, qui puise dans le pool créé par
    # `init_pool` — un `asyncpg.connect()` nu ne le remplirait pas, et la résolution de l'agent
    # mourrait sur un pool à None. On ouvre donc la connexion comme la production le fait.
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("FAIL — DATABASE_URL absente : la mesure refuse de tourner sans base.", file=sys.stderr)
        return 2
    await init_pool(url)
    try:
        async with get_db_session() as conn:
            rows = [dict(r) for r in await conn.fetch(_SQL_ACTIVES, TICKERS)]
        code = await _qualifier(rows)
    finally:
        await close_pool()
    return code


async def _qualifier(rows: list[dict[str, Any]]) -> int:
    couples = _paires_sources_distinctes(rows)
    print(f"=== Couples à qualifier : {len(couples)} (sources réellement distinctes) ===\n")

    agent = await _resoudre_agent()
    tally: dict[str, int] = {"divergence": 0, "facettes": 0,
                             "meme_fait_deux_dates": 0, "non_comparable": 0}
    erreurs = 0
    cout = 0.0
    divergences: list[str] = []

    for a, b, champ in couples:
        message = (
            f"Champ d'analyse : `{champ}` (émetteur {a['ticker_id']}).\n\n"
            f"EXTRAIT 1\n{_extrait(a)}\n\nEXTRAIT 2\n{_extrait(b)}\n\n"
            "Rends l'objet JSON {\"verdict\": ..., \"motif\": ...} et rien d'autre."
        )
        try:
            res = await run_json_agent(
                agent, [{"role": "user", "content": message}], QualifCouple,
                temperature=0.0, json_object=False,
            )
        except Exception as exc:  # noqa: BLE001 — une panne ne doit pas être lue comme un verdict
            erreurs += 1
            print(f"  ERREUR  {a['ticker_id']:5s} {champ:38s} #{a['id']}/#{b['id']} → {exc}")
            continue

        cout += float(getattr(res, "cost_usd", 0.0) or 0.0)
        v = res.parsed.verdict
        tally[v] += 1
        marque = "🔴" if v == "divergence" else "  "
        print(f"  {marque} {v:20s} {a['ticker_id']:5s} {champ:38s} "
              f"#{a['id']}({a['reliability_tier']}) / #{b['id']}({b['reliability_tier']})")
        print(f"       {res.parsed.motif}")
        if v == "divergence":
            divergences.append(
                f"\n--- {a['ticker_id']} · {champ}\n{_extrait(a)}\n\n{_extrait(b)}\n"
                f"\nMOTIF : {res.parsed.motif}\n"
            )

    if divergences:
        print("\n=== Les couples jugés DIVERGENTS, en entier, à relire à la main ===")
        for d in divergences:
            print(d)

    print(
        f"\nLIGNE DE BASE 5b — {tally['divergence']} divergence(s) · {tally['facettes']} facette(s) · "
        f"{tally['meme_fait_deux_dates']} péremption(s) · {tally['non_comparable']} non comparable(s) "
        f"· {erreurs} erreur(s) sur {len(couples)} couple(s) · coût ${cout:.4f}"
    )
    # Une erreur n'est pas un verdict : si le modèle n'a pas répondu, la mesure est incomplète et
    # le dit en sortant en échec, jamais en comptant un zéro (#49, feedback_check_degrade…).
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
