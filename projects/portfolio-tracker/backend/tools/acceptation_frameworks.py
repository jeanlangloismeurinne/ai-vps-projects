"""Acceptation du chantier v3 — les 8 critères T1-T8 de la spec §9.2, sur les trois tickers.

CE QU'IL EST, ET QUAND IL SERT
------------------------------
Il est écrit au **lot 0**, avant la première ligne de code de la capacité, et il **rougit sur les
8** — c'est sa seule façon d'être éprouvé (`feedback_test_negatif_obligatoire`). Un test
d'acceptation écrit après coup se rédige, sans qu'on s'en aperçoive, en fonction de ce que le code
fait déjà : il devient une description, pas une exigence.

Il vire au vert progressivement — T6/T7 au lot 3, T1/T4/T5 au lot 3-4, T3 au lot 4, T8 au lot 4,
T2 au lot 7. Le lot 7 exige les 8.

L'ADRESSE DE CE QUI N'EXISTE PAS ENCORE EST UN CONTRAT
------------------------------------------------------
Les frameworks n'existent pas au lot 0. Ce script ne s'en accommode pas par un `skip` : il déclare
l'API que le lot 2 doit fournir (`app.agents.v2.frameworks.load_frameworks`) et les tables que les
lots 3-4 doivent créer (`framework_answers`, `framework_mandates`), et chaque absence produit un
**FAIL NOMMÉ**. C'est l'ordre imposé du chantier — UX (contrat) → agent → données — rendu
exécutable : le contrat est asserté avant d'être implémenté.

⚠️ Un pré-requis manquant ne fait JAMAIS sauter une section (`feedback_check_degrade_en_sortant_a_
zero`). Un `import` ou une table absente est rattrapé et **compté en échec**, sans quoi le script
mourrait avant son bilan — le 2ᵉ des quatre faux verts.

CE QU'IL N'ÉCRIT PAS
--------------------
Rien. Aucun UPDATE, aucun INSERT, aucun appel modèle.

Usage : bash tools/acceptation_frameworks.sh
"""
from __future__ import annotations

import asyncio
import os
import sys
from typing import Any, Optional

from app.contracts.framework_answer_schema import COLONNES_DENORMALISEES
from app.db.database import close_pool, get_db_session, init_pool

from tools.reconcilier_vocabulaires import ALIAS, DERIVES, feuilles_memo

TICKERS = ["NVDA", "MSFT", "RVMD"]

# ── Adressage des colonnes PAR LEUR CHEMIN DE CONTRAT ──────────────────────────────────────────
# Ce script a été écrit au lot 0, AVANT le contrat, avec sa propre nomenclature devinée
# (`framework`, `rang_degrade`, `methode_approximation`, `ingredients`, `motif`). Le lot 1 a fixé le
# contrat, qui NICHE ces champs (`fondation.rang_derive`, `approximation.methode`, …). Deux
# nomenclatures d'accord restent deux nomenclatures (#46) : le jour où la migration 036 nommerait
# ses colonnes d'après le contrat, T3 et T4 liraient `None` pour toujours — donc resteraient rouges
# pour la MAUVAISE raison, ou pire virerait au vert sur zéro ligne (1ᵉʳ faux vert).
# Le détenteur unique de la correspondance est `COLONNES_DENORMALISEES`, dans le contrat ; ici on ne
# fait que l'inverser. `check_framework_contract.py` §6 vérifie que chaque chemin y résout.
_COLONNE_DE = {chemin: colonne for colonne, chemin in COLONNES_DENORMALISEES.items()}


def col(ligne: Any, chemin: str) -> Any:
    """Lit une colonne dénormalisée par le CHEMIN DU CONTRAT dont elle est la projection.

    Un chemin inconnu lève : mieux vaut un script qui meurt en nommant le chemin absent qu'un
    `None` silencieux qui ferait rougir T3/T4 pour la mauvaise raison.
    """
    return dict(ligne).get(_COLONNE_DE[chemin])

# Les 13 questions des deux pilotes (spec §4.1.1 et §4.2.1). Elles sont écrites ici parce que ce
# script est l'EXIGENCE : c'est la spec qui les fixe, pas le code qui les révélera. Le jour où le
# lot 2 les écrit comme données, §A vérifie qu'elles coïncident — un identifiant qui divergerait
# ferait rougir un assert nommé au lieu de faire passer T4/T5 sur une question voisine.
QUESTIONS_ATTENDUES: dict[str, tuple[str, ...]] = {
    "qualite_financiere": ("qf_1", "qf_2", "qf_3", "qf_4", "qf_5", "qf_6", "qf_7"),
    "defendabilite": ("mo_1", "mo_2", "mo_3", "mo_4", "mo_5", "mo_6"),
}

# Les 4 champs de sortie du framework moat (contrat `Moat`, hors `score` qui est dérivé).
CHAMPS_MOAT = ("moat.type", "moat.trend", "moat.durabilite_ans", "moat.preuves")

ok = fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def _t(n: str, titre: str) -> None:
    print(f"\n{'─'*72}\n{n} — {titre}\n{'─'*72}")


# ══════════════════════════════════════════════════════════════════════════════
# Accès aux artefacts que les lots suivants doivent produire. Chacun rend `None`
# plutôt que de lever : l'absence est une MESURE de l'avancement, pas un crash.
# ══════════════════════════════════════════════════════════════════════════════
def charger_frameworks() -> tuple[Optional[dict[str, Any]], str]:
    """`(frameworks, motif)` — le chargeur du lot 2, ou son absence, NOMMÉE."""
    try:
        from app.agents.v2.frameworks import load_frameworks  # type: ignore[attr-defined]
    except Exception as exc:                                   # noqa: BLE001
        return None, f"`app.agents.v2.frameworks.load_frameworks` absent ({type(exc).__name__})"
    try:
        return load_frameworks(), ""
    except Exception as exc:                                   # noqa: BLE001
        return None, f"`load_frameworks()` a levé {type(exc).__name__}: {exc}"


async def table_existe(conn, nom: str) -> bool:
    return await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"public.{nom}")


async def lire(conn, nom: str, sql: str, *args) -> tuple[Optional[list[Any]], str]:
    """Lit une table du chantier ; rend `(None, motif)` si elle n'existe pas encore."""
    if not await table_existe(conn, nom):
        return None, f"table `{nom}` absente"
    try:
        return list(await conn.fetch(sql, *args)), ""
    except Exception as exc:                                   # noqa: BLE001
        return None, f"lecture de `{nom}` : {type(exc).__name__}: {exc}"


# ══════════════════════════════════════════════════════════════════════════════
async def main() -> int:
    url = os.environ.get("DATABASE_URL") or ""
    if not url:
        print("DATABASE_URL manquant — l'acceptation se MESURE sur le corpus réel.", file=sys.stderr)
        return 2

    frameworks, motif_fw = charger_frameworks()

    await init_pool(url)
    try:
        async with get_db_session() as conn:
            entries = await conn.fetch("""
                SELECT id, ticker_id, entry_type, source_type, reliability_tier, covers, title
                  FROM knowledge_entries
                 WHERE superseded_by IS NULL AND is_deleted = false AND ticker_id = ANY($1::text[])
            """, TICKERS)
            reponses, motif_rep = await lire(conn, "framework_answers", """
                SELECT * FROM framework_answers WHERE ticker_id = ANY($1::text[])
            """, TICKERS)
            mandats, motif_man = await lire(conn, "framework_mandates", """
                SELECT * FROM framework_mandates WHERE ticker_id = ANY($1::text[])
            """, TICKERS)
    finally:
        await close_pool()

    par_ticker: dict[str, list[Any]] = {t: [] for t in TICKERS}
    for e in entries:
        par_ticker[e["ticker_id"]].append(e)

    # ── §A — l'état d'avancement, mesuré et non supposé ──────────────────────────
    print(f"Corpus : {len(entries)} entries courantes sur {TICKERS}.")
    print(f"Frameworks  : {'chargés' if frameworks else 'ABSENTS — ' + motif_fw}")
    print(f"Réponses    : {len(reponses) if reponses is not None else 'ABSENTES — ' + motif_rep}")
    print(f"Mandats     : {len(mandats) if mandats is not None else 'ABSENTS — ' + motif_man}")
    check("[A] le corpus courant est non vide sur les trois tickers",
          all(par_ticker[t] for t in TICKERS),
          f"→ {[t for t in TICKERS if not par_ticker[t]]} : les critères seraient vrais sur "
          f"zéro ligne")

    if frameworks is not None:
        # Ne mord qu'une fois le lot 2 livré — mais il est écrit AVANT, sans quoi T4/T5 pourraient
        # passer sur une question voisine de `qf_1` / `qf_7` sans que personne ne le voie.
        for nom, attendues in QUESTIONS_ATTENDUES.items():
            recues = tuple((frameworks.get(nom) or {}).get("questions") or ())
            ids = tuple(q.get("id") if isinstance(q, dict) else getattr(q, "id", None)
                        for q in recues)
            check(f"[A] framework `{nom}` porte exactement ses questions de spec",
                  set(ids) == set(attendues),
                  f"→ manquantes {sorted(set(attendues) - set(ids))}, "
                  f"en trop {sorted(set(ids) - set(attendues))}")

    def _rattachements(ticker: str, framework: str) -> dict[int, str]:
        """`{entry_id: question_id}` pour ce couple. Vide tant que le lot 2 n'a rien produit."""
        if reponses is None:
            return {}
        out: dict[int, str] = {}
        for r in reponses:
            d = dict(r)
            if col(d, "ticker_id") != ticker or col(d, "framework_id") != framework:
                continue
            for eid in (col(d, "fondation.cited_entry_ids") or []):
                out[int(eid)] = str(col(d, "question_id"))
        return out

    # ══════════════════════════════════════════════════════════════════════════
    _t("T1", "les orphelines tier A de NVDA sont rattachées à une question de "
             "`qualite_financiere`")
    orph_nvda = [e for e in par_ticker["NVDA"] if not e["covers"]]
    orph_tierA = [e for e in orph_nvda if e["reliability_tier"] == "A"]
    rattachees = _rattachements("NVDA", "qualite_financiere")
    couvertes = [e for e in orph_tierA if e["id"] in rattachees]
    non_couvertes = [e for e in orph_tierA if e["id"] not in rattachees]
    print(f"  orphelines NVDA : {len(orph_nvda)} au total, dont {len(orph_tierA)} tier A")
    print(f"  rattachées à une question de `qualite_financiere` : {len(couvertes)}"
          f"/{len(orph_tierA)}")
    for e in non_couvertes:
        print(f"      NON RATTACHÉE  #{e['id']:<4} {(e['title'] or '')[:60]}")
    # ⚠️ SEUIL À ARBITRER — la spec §9.2 écrit « les 26 orphelines tier A … ≥ 24/26 », mais la
    # mesure sépare deux ensembles : 26 orphelines AU TOTAL et 16 tier A. Le seuil 24/26 n'est
    # applicable ni à l'un (10 des 26 sont des `Context pack` et des `llm_memory` « à vérifier »,
    # qui n'ont rien à faire dans un framework de qualité financière) ni à l'autre (16 < 24).
    # L'exigence retenue ici est la plus stricte des deux lectures défendables — TOUTES les tier A,
    # le reste NOMMÉ — et la divergence est remontée pour arbitrage avant le lot 2.
    check("T1 — toutes les orphelines tier A de NVDA sont rattachées, le reste nommé",
          bool(orph_tierA) and not non_couvertes,
          f"→ {len(non_couvertes)}/{len(orph_tierA)} non rattachées "
          f"(⚠️ seuil §9.2 « ≥24/26 » à arbitrer : 26 orphelines ≠ 16 tier A)")

    # ══════════════════════════════════════════════════════════════════════════
    _t("T2", "les 4 champs de moat ont au moins une entry citable, sur les trois tickers")
    for champ in CHAMPS_MOAT:
        chemin = ALIAS.get(champ)
        for t in TICKERS:
            n = len([e for e in par_ticker[t] if chemin and chemin in (e["covers"] or [])])
            statut = f"{n} entry(ies) via {chemin}" if chemin else "AUCUN chemin d'indexation"
            print(f"  {champ:24} {t:5} {statut}")
    manquants = [(champ, t) for champ in CHAMPS_MOAT for t in TICKERS
                 if not ALIAS.get(champ)
                 or not any(ALIAS[champ] in (e["covers"] or []) for e in par_ticker[t])]
    check("T2 — les 4 champs de moat sont citables sur les 3 tickers",
          not manquants,
          f"→ {len(manquants)}/{len(CHAMPS_MOAT)*len(TICKERS)} couples sans entry citable : "
          f"{[f'{c}@{t}' for c, t in manquants][:6]}…")

    # ══════════════════════════════════════════════════════════════════════════
    _t("T3", "aucune réponse `approxime` sans méthode, sans ingrédients, ou sans rang DÉGRADÉ")
    if reponses is None:
        check("T3 — zéro approximation non déclarée", False,
              f"→ {motif_rep} : rien à contrôler, donc RIEN N'EST PROUVÉ. "
              f"Un « 0 violation » sur zéro ligne est le 1er des quatre faux verts.")
    else:
        approx = [dict(r) for r in reponses if col(r, "statut") == "approxime"]
        viols = [r for r in approx
                 if not col(r, "approximation.methode")
                 or not (col(r, "approximation.ingredients_entry_ids")
                         or col(r, "fondation.cited_entry_ids"))
                 or not col(r, "fondation.rang_derive")]
        print(f"  réponses `approxime` : {len(approx)} · violations : {len(viols)}")
        check("T3 — zéro approximation non déclarée",
              bool(approx) and not viols,
              f"→ {len(viols)} violations sur {len(approx)} approximations"
              if approx else "→ aucune approximation dans le corpus : l'assert serait vrai sur "
                             "zéro ligne, il ne prouve rien")

    # ══════════════════════════════════════════════════════════════════════════
    _t("T4", "RVMD — `qf_1` sort `sans_objet` MOTIVÉ, jamais un ROIC fabriqué")
    print("  Ce que fait le système AUJOURD'HUI, et que T4 doit rendre impossible :")
    for e in par_ticker["RVMD"]:
        if "financials.roic_pct" in (e["covers"] or []):
            print(f"      #{e['id']:<4} {(e['title'] or '')[:64]}")
            print("            ↑ un ROIC pour une société sans chiffre d'affaires (spec §0.2)")
    r_qf1 = next((dict(r) for r in (reponses or [])
                  if col(r, "ticker_id") == "RVMD" and col(r, "question_id") == "qf_1"),
                 None)
    if r_qf1 is None:
        check("T4 — `qf_1` sur RVMD est `sans_objet` et motivé", False,
              f"→ aucune réponse `qf_1` pour RVMD ({motif_rep or 'question jamais posée'})")
    else:
        check("T4 — `qf_1` sur RVMD est `sans_objet` et motivé",
              col(r_qf1, "statut") == "sans_objet" and bool(col(r_qf1, "sans_objet.motif")),
              f"→ statut={col(r_qf1, 'statut')}, "
              f"motif={'oui' if col(r_qf1, 'sans_objet.motif') else 'NON'}")

    # ══════════════════════════════════════════════════════════════════════════
    _t("T5", "RVMD — `qf_7` (le runway) sort `repondu`")
    print("  `qf_7` (« combien de temps sans accès au marché des capitaux ? ») n'existait dans la")
    print("  grille de 19 sous AUCUNE forme — c'est la question qui manquait totalement à RVMD.")
    r_qf7 = next((dict(r) for r in (reponses or [])
                  if col(r, "ticker_id") == "RVMD" and col(r, "question_id") == "qf_7"),
                 None)
    if r_qf7 is None:
        check("T5 — `qf_7` sur RVMD est `repondu`", False,
              f"→ aucune réponse `qf_7` pour RVMD ({motif_rep or 'question jamais posée'})")
    else:
        check("T5 — `qf_7` sur RVMD est `repondu`", col(r_qf7, "statut") == "repondu",
              f"→ statut={col(r_qf7, 'statut')}")

    # ══════════════════════════════════════════════════════════════════════════
    _t("T6/T7", "un seul vocabulaire — zéro feuille de mémo sans question, zéro question "
                "jamais consommée")
    # Détenteur unique (#46) : la réconciliation vit dans `reconcilier_vocabulaires`, ce script la
    # CONSOMME. En tenir un jumeau ici les ferait diverger au premier correctif.
    memo = feuilles_memo()
    if frameworks is None:
        # Avant le lot 3, le vocabulaire cible est encore MVDD : on mesure l'écart contre lui, et
        # on le DIT — mesurer contre un vocabulaire qui n'existe pas rendrait 0 sur zéro question.
        from app.agents.v2.common import MVDD_FIELD_PATHS
        vocabulaire = set(MVDD_FIELD_PATHS)
        origine = "MVDD_FIELD_PATHS (le vocabulaire que le lot 3 remplace)"
    else:
        vocabulaire = {q.get("id") if isinstance(q, dict) else getattr(q, "id", None)
                       for f in frameworks.values() for q in (f.get("questions") or ())}
        origine = "framework_questions"
    sans_question = sorted(f for f in memo - DERIVES if ALIAS.get(f) not in vocabulaire)
    jamais_consommees = sorted(vocabulaire - {ALIAS[k] for k in ALIAS if k in memo})
    print(f"  vocabulaire de référence : {origine} ({len(vocabulaire)} entrées)")
    print(f"  feuilles de mémo sans question : {len(sans_question)}")
    print(f"  questions jamais consommées    : {len(jamais_consommees)}")
    check("T6 — zéro feuille de mémo sans question", not sans_question,
          f"→ {len(sans_question)} : {sans_question[:4]}…")
    check("T7 — zéro question jamais consommée", not jamais_consommees,
          f"→ {len(jamais_consommees)} : {jamais_consommees[:4]}…")

    # ══════════════════════════════════════════════════════════════════════════
    _t("T8", "un renvoi du manager crée un mandat CONSOMMABLE, et le re-run change le statut")
    if mandats is None:
        check("T8 — au moins un renvoi → mandat → re-run → changement de statut", False,
              f"→ {motif_man} : la boucle comité → collecte est l'Écart B de §0.5, "
              f"elle n'a aujourd'hui aucun émetteur")
    else:
        boucles = [dict(m) for m in mandats
                   if dict(m).get("consomme_at") and dict(m).get("statut_avant")
                   and dict(m).get("statut_apres")
                   and dict(m).get("statut_avant") != dict(m).get("statut_apres")]
        print(f"  mandats : {len(mandats)} · bouclés de bout en bout : {len(boucles)}")
        check("T8 — au moins un renvoi → mandat → re-run → changement de statut",
              bool(boucles),
              f"→ {len(mandats)} mandats, aucun consommé avec changement de statut : "
              f"un mandat qui ne change rien n'a pas fermé la boucle")

    print(f"\n{'═'*72}\n{ok} vérifications OK, {fail} échec(s)")
    if fail:
        print(f"\nROUGE ATTENDU au lot 0 : les 8 critères doivent échouer avant la première ligne\n"
              f"de code de la capacité. Ils virent au vert par lots — T6/T7 au lot 3, T1/T4/T5 aux\n"
              f"lots 3-4, T3 et T8 au lot 4, T2 au lot 7. Le lot 7 exige les 8.", file=sys.stderr)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
