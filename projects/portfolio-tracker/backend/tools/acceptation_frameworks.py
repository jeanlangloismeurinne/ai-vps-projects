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

# L'ingrédient que T1bis exige de voir sortir NON SERVI et MANDATÉ. Il est nommé, et pas seulement
# compté : un critère qui exige qu'il MANQUE quelque chose est le plus facile à satisfaire par
# accident — n'importe quelle collecte incomplète rendrait « ≥ 1 » vrai (§9.2). Aucun poste EDGAR
# ne contient un coût du capital ; c'est le cas d'école de la ligne de plan `inobtenable` (§3.6).
INGREDIENT_TEMOIN = ("qualite_financiere", "qf_1", "cout_du_capital")

# Les natures d'entry qui ne FONDENT rien par elles-mêmes : une question dont tous les ingrédients
# servis viennent de là est fondée par des synthèses d'elle-même (T2). Lu sur le vocabulaire fermé
# de la 036 plutôt que recopié (#46) — `analysis` et `agent_synthesis` en sont deux jetons.
NATURES_NON_PRIMAIRES = frozenset({"agent_synthesis", "analysis"})

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
    """`({framework_id: FrameworkDefinition}, motif)` — le référentiel du lot 2a, ou son absence.

    ⚠️ Le lot 0 avait SUPPOSÉ un dict de dicts et lisait `.get("questions")`. Le lot 2a rend un
    `FrameworksFile` Pydantic : l'accès par `.get` levait un `AttributeError` qui tuait le script
    APRÈS §A et AVANT son bilan — un lanceur qui cherche une ligne de bilan n'aurait vu qu'un
    script mort (`feedback_bilan_par_sa_forme`). L'indexation par id se fait donc ici, une fois, et
    les critères lisent des ATTRIBUTS : un champ renommé LÈVE au lieu de rendre `None`, ce qui
    ferait rougir T1 pour la mauvaise raison — ou pire, le rendrait vert sur zéro ingrédient.
    """
    try:
        from app.agents.v2.frameworks import load_frameworks  # type: ignore[attr-defined]
    except Exception as exc:                                   # noqa: BLE001
        return None, f"`app.agents.v2.frameworks.load_frameworks` absent ({type(exc).__name__})"
    try:
        fichier = load_frameworks()
    except Exception as exc:                                   # noqa: BLE001
        return None, f"`load_frameworks()` a levé {type(exc).__name__}: {exc}"
    return {f.id: f for f in fichier.frameworks}, ""


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
            # ⚠️ Ni `covers` ni `is_deleted` : la 036 les a retirées. `covers` n'est pas remplacée
            # par une autre colonne — la couverture est une propriété de la RELATION entry ↔
            # ingrédient (#57), elle se lit dans `question_coverage` ci-dessous. `tags` entre au
            # SELECT parce que T4 doit montrer ce que le système produit aujourd'hui, et que c'est
            # par les tags que la production identifie un ratio dérivé (#43).
            entries = await conn.fetch("""
                SELECT id, ticker_id, entry_type, source_type, reliability_tier, tags, title
                  FROM knowledge_entries
                 WHERE superseded_by IS NULL AND ticker_id = ANY($1::text[])
            """, TICKERS)
            couverture, motif_cov = await lire(conn, "question_coverage", """
                SELECT qc.framework_id, qc.framework_version, qc.question_id, qc.ingredient_id,
                       qc.entry_id, e.ticker_id, e.entry_type
                  FROM question_coverage qc
                  JOIN knowledge_entries e ON e.id = qc.entry_id
                 WHERE e.superseded_by IS NULL AND e.ticker_id = ANY($1::text[])
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
            fw = frameworks.get(nom)
            ids = tuple(q.id for q in (fw.questions if fw else ()))
            check(f"[A] framework `{nom}` porte exactement ses questions de spec",
                  set(ids) == set(attendues),
                  f"→ manquantes {sorted(set(attendues) - set(ids))}, "
                  f"en trop {sorted(set(ids) - set(attendues))}")

    # ══════════════════════════════════════════════════════════════════════════
    # T1 / T1bis / T2 — RÉÉCRITS AU LOT 2b sur le §9.2 révisé du 2026-09-10.
    #
    # L'ancien T1 (« les orphelines tier A de NVDA sont rattachées ») n'a pas été re-seuillé : il a
    # été DISSOUS. Il faisait du corpus de test l'objectif de conception — le framework aurait été
    # déclaré bon parce qu'il absorbe ce que les recettes d'hier ont ramassé, et le seuil aurait été
    # imperdable (il suffisait d'élargir une question jusqu'à ce que les 16 entrent). La bonne
    # question n'était pas « quel seuil ? » mais « de quel droit le corpus est-il la cible ? ».
    # Le critère ne compte donc plus aucune orpheline : il part des INGRÉDIENTS que les questions
    # réclament, et regarde si chacun est servi ou nommé. L'ancien T2 (les 4 champs de moat
    # citables) lisait `covers`, colonne archivée par la 036 : il est remplacé par le critère
    # d'auto-fondation, qui est ce que la mesure du 2026-09-09 a réellement trouvé de fautif
    # (`produits.unit_economics` : 2 entries, 0 primaire).
    # ══════════════════════════════════════════════════════════════════════════
    def _essentiels() -> list[tuple[str, str, str]]:
        """`(framework_id, question_id, ingredient_id)` des ingrédients ESSENTIELS du référentiel.

        Lu sur `frameworks.yaml` via son chargeur, jamais recopié : c'est le référentiel qui dit ce
        dont une question a besoin, et un jumeau ici resterait vert le jour où il s'enrichit (#46).
        """
        out: list[tuple[str, str, str]] = []
        for fid, f in (frameworks or {}).items():
            for q in f.questions:
                for ing in q.ingredients_requis:
                    if ing.essentiel:
                        out.append((fid, q.id, ing.id))
        return out

    def _statut_question(ticker: str, framework: str, question: str) -> Optional[str]:
        """Le statut de la réponse, ou `None` si la question n'a pas encore été posée."""
        for r in (reponses or []):
            if (col(r, "ticker_id") == ticker and col(r, "framework_id") == framework
                    and col(r, "question_id") == question):
                return str(col(r, "statut"))
        return None

    essentiels = _essentiels()
    servis: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for c in (couverture or []):
        d = dict(c)
        cle = (d["ticker_id"], d["framework_id"], d["question_id"], d["ingredient_id"])
        servis.setdefault(cle, []).append(d)

    def _mandate_ouvert(ticker: str, question: str, ingredient: str) -> bool:
        """Un mandat OUVERT qui NOMME l'ingrédient. « Un mandat sur la question » ne suffit pas :
        il faut savoir lequel des ingrédients il va chercher, sinon il ne ferme rien."""
        for m in (mandats or []):
            d = dict(m)
            if (d.get("ticker_id") == ticker and d.get("question_id") == question
                    and d.get("ingredient_id") == ingredient
                    and d.get("statut") == "ouvert"):
                return True
        return False

    _t("T1", "tout ingrédient essentiel d'une question applicable est SERVI ou MANDATÉ")
    if not essentiels:
        check("T1 — zéro ingrédient essentiel ni servi ni mandaté", False,
              f"→ le référentiel ne rend aucun ingrédient essentiel ({motif_fw or 'liste vide'}) : "
              f"« 0 manquant » serait vrai sur zéro ligne, le 1ᵉʳ des faux verts")
    elif couverture is None:
        check("T1 — zéro ingrédient essentiel ni servi ni mandaté", False,
              f"→ {motif_cov} : rien ne peut être SERVI, donc rien n'est prouvé. La 036 crée "
              f"`question_coverage` ; son dispatch est le lot 2c")
    else:
        trous: list[str] = []
        applicables = 0
        for t in TICKERS:
            for fid, qid, ing in essentiels:
                # `sans_objet` retire la question du périmètre : T4 exige précisément que RVMD
                # puisse dire « cette question n'a pas de sens ici » sans que ça compte comme un
                # trou. Une question jamais posée reste APPLICABLE — l'absence de réponse n'est pas
                # une dispense (#54 : trois états, et « pas encore posée » n'est pas « sans objet »).
                if _statut_question(t, fid, qid) == "sans_objet":
                    continue
                applicables += 1
                if servis.get((t, fid, qid, ing)) or _mandate_ouvert(t, qid, ing):
                    continue
                trous.append(f"{t}/{fid}.{qid}.{ing}")
        print(f"  ingrédients essentiels × tickers applicables : {applicables}")
        print(f"  ni servis ni mandatés : {len(trous)}")
        for x in trous[:8]:
            print(f"      TROU  {x}")
        check("T1 — zéro ingrédient essentiel ni servi ni mandaté", not trous,
              f"→ {len(trous)}/{applicables} : {trous[:4]}…")

    # ══════════════════════════════════════════════════════════════════════════
    _t("T1bis", "au moins un ingrédient essentiel sort NON SERVI et MANDATÉ, "
                f"dont `{INGREDIENT_TEMOIN[1]}.{INGREDIENT_TEMOIN[2]}`")
    print("  Une couverture à 100 % FAIT ÉCHOUER le pilote : elle signerait un référentiel")
    print("  rétro-conçu depuis ce que la collecte sait déjà produire. Un framework qui ne")
    print("  réclame jamais rien qu'on n'ait pas ne challenge rien.")
    if couverture is None or mandats is None:
        check("T1bis — au moins un essentiel non servi ET mandaté, dont le témoin nommé", False,
              f"→ {motif_cov or motif_man} : ni la couverture ni les mandats n'ont d'émetteur, "
              f"l'absence de couverture ne prouve donc pas qu'un mandat la NOMME")
    else:
        fid_t, qid_t, ing_t = INGREDIENT_TEMOIN
        reclames = [f"{t}/{fid}.{qid}.{ing}" for t in TICKERS for fid, qid, ing in essentiels
                    if not servis.get((t, fid, qid, ing)) and _mandate_ouvert(t, qid, ing)]
        temoin = [t for t in TICKERS
                  if not servis.get((t, fid_t, qid_t, ing_t))
                  and _mandate_ouvert(t, qid_t, ing_t)]
        print(f"  essentiels non servis mais MANDATÉS : {len(reclames)}")
        print(f"  dont `{qid_t}.{ing_t}` : {temoin or 'AUCUN ticker'}")
        check("T1bis — au moins un essentiel non servi ET mandaté", bool(reclames),
              "→ 0 : couverture complète, ou des trous que personne ne réclame")
        check(f"T1bis — le témoin `{qid_t}.{ing_t}` est de ceux-là", bool(temoin),
              f"→ aucun ticker : « ≥ 1 » serait satisfait par n'importe quelle collecte "
              f"incomplète, sans que ce soit le manque qui compte")

    # ══════════════════════════════════════════════════════════════════════════
    _t("T2", "toute question `repondu` a au moins un ingrédient servi par une source PRIMAIRE")
    if reponses is None or couverture is None:
        check("T2 — zéro question auto-fondée", False,
              f"→ {motif_rep or motif_cov} : aucune question `repondu` à contrôler, "
              f"donc « 0 auto-fondée » serait vrai sur zéro ligne")
    else:
        repondues = [dict(r) for r in reponses if col(r, "statut") == "repondu"]
        auto_fondees: list[str] = []
        for r in repondues:
            t, fid, qid = col(r, "ticker_id"), col(r, "framework_id"), col(r, "question_id")
            liens = [d for cle, ds in servis.items() if cle[:3] == (t, fid, qid) for d in ds]
            primaires = [d for d in liens if d["entry_type"] not in NATURES_NON_PRIMAIRES]
            if not primaires:
                auto_fondees.append(f"{t}/{fid}.{qid} ({len(liens)} lien(s), 0 primaire)")
        print(f"  questions `repondu` : {len(repondues)} · auto-fondées : {len(auto_fondees)}")
        for x in auto_fondees[:6]:
            print(f"      AUTO-FONDÉE  {x}")
        check("T2 — zéro question auto-fondée",
              bool(repondues) and not auto_fondees,
              f"→ {len(auto_fondees)} sur {len(repondues)}"
              if repondues else "→ aucune question `repondu` : l'assert serait vrai sur zéro "
                                "ligne, il ne prouve rien")

    # ══════════════════════════════════════════════════════════════════════════
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
        # Par les TAGS et non par `covers` (archivée par la 036) : c'est déjà par eux que la
        # production identifie un ratio dérivé (`_current_tagged_entry_id`, #43), donc ce n'est pas
        # un pis-aller — c'est le porteur qui faisait foi de toute façon.
        if "roic" in (e["tags"] or []):
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
        # `chemin_indexation` et non `id` : c'est LUI que le mémo consomme, et ALIAS projette
        # des chemins. Comparer des `qf_1` à des `business_model.description` rendrait T6/T7
        # rouges par mésappariement de vocabulaire, pas par l'écart qu'ils mesurent.
        vocabulaire = {q.chemin_indexation for f in frameworks.values() for q in f.questions}
        origine = "framework_questions (chemin_indexation)"
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
