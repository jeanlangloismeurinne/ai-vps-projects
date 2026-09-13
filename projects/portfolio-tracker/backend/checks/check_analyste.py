"""Vérification de l'ANALYSTE (chantier v3, lot 3 — `app/agents/v2/analyste.py`), MOITIÉ
DÉTERMINISTE seulement. Sans réseau ni modèle ni base.

Le modèle lit et répond ; mais ce qu'on lui MONTRE, ce qu'on lui LAISSE décider, et ce qu'on fait
de ce qu'il rend sont déterministes — et c'est là que se jouent les garanties. On les éprouve avant
toute dépense (`feedback_frontiere_gratuite_avant_depense_modele`). L'analyse elle-même (l'appel
modèle) est hors périmètre : son acceptation se fait contre le vrai modèle, séparément.

  • §1 LE HORS-SUJET EST ÉCRIT PAR LE CODE — `questions_sans_objet` est le COMPLÉMENT exact de
       `questions_applicables` (détenteur unique, #46), et la réponse `sans_objet` descend du
       `motif_gabarit` du référentiel, pas d'un jugement de modèle (§4.1.3, entry #190).
  • §2 LE CONTEXTE EST LEVER-FREE (#59) — ni `plancher_tier`, ni `nature_attendue`, ni le
       `reliability_tier` / la `nature` des entries. Montrer le tier, c'est demander au modèle de
       choisir son niveau de preuve ; le rang se DÉRIVE de ce qu'il a cité (règle transverse 7).
  • §3 LE PLANCHER EST STRUCTUREL — `corpus_citable` retire du contexte ce qui n'atteint pas le
       plancher : le modèle ne peut pas citer sous le plancher, il n'a pas à s'en abstenir.
  • §4 LE MODÈLE NE PEUT PAS ÉMETTRE CE QUI NE LUI APPARTIENT PAS — ni `sans_objet`/`non_fondable`,
       ni `rang_derive`/`nature_effective`, ni l'en-tête (#36/#53/#57).
  • §5 LES DEUX AXES SONT DÉRIVÉS — `assembler_answer` interroge les détenteurs de la règle
       (`_plus_faible`, `derive_synthesis_reliability`), et ne concède jamais la nature forte.
  • §6 [S] CONTRE LES PROFILS RÉELS — le `sens` appartient au vocabulaire fermé de la question. La
       fixture de `check_framework_contract` §8 ne porte `sens_admis` que sur une question ; c'est
       ici, sur `question_profiles()`, que [S] rencontre le corpus qu'il gardera en production.
  • §7 TROIS ÉTATS NOMMÉS, AUCUNE ÉVAPORATION (#25/#60) — chaque question sort en réponse OU en
       refus, et surtout : une omission d'agent ne devient JAMAIS un `gap`. Orchestration éprouvée
       hors-ligne en substituant `run_json_agent` (le modèle est le seul morceau qu'on n'éprouve pas
       ici ; tout ce qui l'entoure, si).

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte (v1).
"""
import ast
import asyncio
import inspect
import json
import sys
import textwrap
from typing import get_args

from pydantic import ValidationError

from app.agents.v2 import analyste as A
from app.agents.v2.common import TIER_ORDER
from app.agents.v2.frameworks import (
    FrameworkAnswerRefused,
    load_frameworks,
    question_profiles,
    valider_pont_framework_answer,
)
from app.agents.v2.traducteur import questions_applicables

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def leve(label, fn, motif_type):
    """L'appel DOIT lever le type nommé (pas un autre, pas un retour)."""
    global ok, fail
    try:
        fn()
        fail += 1
        print(f"  FAIL {label} → ACCEPTÉ alors qu'il devait être refusé")
    except motif_type:
        ok += 1
        print(f"  ok   {label}")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {label} → mauvaise exception {type(e).__name__}: {str(e)[:140]}")


F = load_frameworks()
FW = {f.id: f for f in F.frameworks}["qualite_financiere"]
Q = {q.id: q for q in FW.questions}
TICKER = "TEST"

# Corpus de test — trois entries, trois couples (tier, nature) distincts. Les tiers sont ceux de
# `common.TIER_ORDER` ; les natures celles de la migration 034.
ENTRIES = {
    1: {"reliability_tier": "A", "nature": "mesure", "title": "dépôt annuel",
        "content": "trésorerie 3 200 M$", "source_type": "edgar_official", "source_date": "2025-02-01"},
    2: {"reliability_tier": "B+", "nature": "interpretation", "title": "note de courtier",
        "content": "la charge de structure paraît maîtrisée", "source_type": "analyst_note",
        "source_date": "2025-03-01"},
    3: {"reliability_tier": "C", "nature": "mesure", "title": "billet de blog",
        "content": "consommation de trésorerie estimée à 180 M$/trimestre", "source_type": "blog",
        "source_date": "2025-04-01"},
    # Tier ABSENT : une entry dont on ne sait pas ce qu'elle vaut. Elle existe pour que « l'inconnu
    # compte pour le pire » soit MESURÉ et pas supposé.
    4: {"nature": "mesure", "title": "source non qualifiée", "content": "…"},
    # Tier A- : le CRAN JUSTE SOUS le plancher A. Mesuré, pas prévu — sans elle, assouplir le
    # plancher d'un cran laissait le check VERT : aucune entry ne tombait dans l'intervalle ouvert
    # par la mutation, donc la fixture ne discriminait rien (1ᵉʳ faux vert).
    5: {"reliability_tier": "A-", "nature": "mesure", "title": "dépôt trimestriel",
        "content": "charges de structure 48 M$", "source_type": "edgar_official",
        "source_date": "2025-05-01"},
}


# ── §1 le hors-sujet est écrit par le code ────────────────────────────────────────────────────────
print("[1] `sans_objet` est un fait du RÉFÉRENTIEL, écrit par le code (§4.1.3)")
_hs = A.questions_sans_objet(F, "qualite_financiere", "pre_revenus")
_ap = questions_applicables(F, "qualite_financiere", "pre_revenus")
check("les deux moitiés partitionnent le framework (aucune question ni perdue ni comptée deux fois)",
      {q.id for q in _hs} | {q.id for q in _ap} == set(Q)
      and not ({q.id for q in _hs} & {q.id for q in _ap}),
      f"→ sans_objet {sorted(q.id for q in _hs)} / applicables {sorted(q.id for q in _ap)}")
check("`questions_sans_objet` se DÉRIVE de `questions_applicables` (pas de second filtre, #46)",
      "questions_applicables(" in inspect.getsource(A.questions_sans_objet)
      and 'mode' not in inspect.getsource(A.questions_sans_objet),
      "→ un second filtre divergerait, et des questions ne seraient ni planifiées ni répondues")

_entete = dict(ticker_id=TICKER, framework_id="qualite_financiere",
               framework_version=F.schema_version, analyste="analyste_1")
_so1 = A.reponse_sans_objet(Q["qf_1"], "pre_revenus", **_entete)
check("le motif est le `motif_gabarit` du référentiel, recopié tel quel (jamais un motif de modèle)",
      _so1.sans_objet.motif == Q["qf_1"].variables_par_archetype["pre_revenus"].motif_gabarit)
check("« pas de substitut » est DÉCLARÉ (qf_1 pré-revenus : c'est la réponse, §4.1.3)",
      _so1.sans_objet.aucun_substitut is True and _so1.sans_objet.substitut_applique is None)
_so2 = A.reponse_sans_objet(Q["qf_2"], "pre_revenus", **_entete)
check("… et un substitut déclaré descend du référentiel, sans `substitut_answer_id` inventé",
      _so2.sans_objet.substitut_applique == "qf_7" and _so2.sans_objet.substitut_answer_id is None
      and _so2.sans_objet.aucun_substitut is False,
      "→ l'id de ligne se résout à la persistance, pas à l'assemblage")
leve("déclarer sans objet une question APPLICABLE est refusé (elle disparaîtrait du dossier)",
     lambda: A.reponse_sans_objet(Q["qf_4"], "pre_revenus", **_entete), A.AnalysteInapplicable)
leve("un framework inconnu lève AVANT tout appel modèle (#40)",
     lambda: A.questions_sans_objet(F, "framework_bidon", "rentable"), Exception)


# ── §2 le contexte est lever-free ─────────────────────────────────────────────────────────────────
print("\n[2] ce que le modèle voit ne porte AUCUN levier d'exigence, ET aucune note de source (#59)")
CTX = A.contexte_analyste(F, "qualite_financiere", "pre_revenus", TICKER, ENTRIES)
_ser = json.dumps(CTX, ensure_ascii=False)
check("le contexte ne contient pas `plancher_tier` (le modèle ne fixe pas le niveau de preuve)",
      "plancher_tier" not in _ser)
check("le contexte ne contient pas `nature_attendue` (c'est la méthode qui le tient)",
      "nature_attendue" not in _ser)
check("le contexte ne montre pas le `reliability_tier` des entries citables",
      "reliability_tier" not in _ser and '"A"' not in _ser,
      "→ une entry montrée avec sa note invite à citer la note, pas ce qu'elle dit")
check("le contexte ne montre pas la `nature` des entries (l'axe se lit sur la source, #51)",
      '"nature"' not in _ser)
# ⚠️ On asserte sur les DONNÉES sérialisées, jamais sur le prompt : le prompt ÉNONCE l'interdit
# (« tu ne produis ni tier, ni score »), donc un grep sur sa prose lirait sa propre énonciation (#56).
check("chaque question montrée porte son vocabulaire de sens (sinon `sens` est indevinable)",
      all(len(q["sens_admis"]) >= 2 for q in CTX["questions"]) and CTX["questions"])
check("chaque question montrée porte ses ingrédients et sa variable d'archétype",
      all(q["ingredients"] and q["variable_archetype"] for q in CTX["questions"]))
check("le contexte nomme le ticker et la méthodologie",
      CTX["ticker"] == TICKER and len(CTX["framework"]["methodologie"]) > 20)
check("AUCUNE question sans objet n'est montrée au modèle (on ne lui demande pas de la reconnaître)",
      not ({q["id"] for q in CTX["questions"]} & {q.id for q in _hs}),
      f"→ {sorted(q['id'] for q in CTX['questions'])}")
# ⚠️ Sur `ENTRIES` complet, les trois questions applicables ont toutes un corpus : l'assert y serait
# vrai quoi qu'on fasse. On mesure donc sur un corpus qui n'atteint le plancher QUE de `qf_6` (B+) —
# `qf_4` et `qf_7` (plancher A) doivent DISPARAÎTRE du contexte, et pas y figurer les mains vides.
CTX_PARTIEL = A.contexte_analyste(F, "qualite_financiere", "pre_revenus", TICKER, {2: ENTRIES[2]})
check("aucune question SANS corpus citable n'est montrée (on ne paie pas pour qu'il invente)",
      {q["id"] for q in CTX_PARTIEL["questions"]} == {"qf_6"}
      and all(q["corpus"] for q in CTX_PARTIEL["questions"]),
      f"→ {sorted(q['id'] for q in CTX_PARTIEL['questions'])}")


# ── §3 le plancher est structurel, pas une consigne ───────────────────────────────────────────────
print("\n[3] `corpus_citable` retire ce qui n'atteint pas le plancher — le modèle ne peut pas citer sous")
_c4 = A.corpus_citable(Q["qf_4"], ENTRIES)       # plancher A
_c6 = A.corpus_citable(Q["qf_6"], ENTRIES)       # plancher B+
check("une question à plancher A ne voit QUE les entries de tier A",
      set(_c4) == {1}, f"→ {sorted(_c4)}")
check("une question à plancher B+ voit A, A- et B+ (le plancher est un seuil, pas une égalité)",
      set(_c6) == {1, 2, 5}, f"→ {sorted(_c6)}")
check("… et le cran JUSTE sous le plancher est bien retiré (l'entry 5 est A-, la question est A)",
      5 not in _c4, "→ sans cet écart d'un cran, assouplir le plancher ne ferait rougir personne")
check("une entry de tier C est retirée des deux",
      3 not in _c4 and 3 not in _c6)
check("une entry SANS tier connu compte pour le pire, donc elle est retirée (jamais tolérée)",
      4 not in _c4 and 4 not in _c6,
      "→ une source dont on ne sait pas ce qu'elle vaut ne peut pas fonder au-dessus d'un plancher")
check("… et le contexte ne montre donc que des entries citables",
      all(e["entry_id"] in ENTRIES and e["entry_id"] not in (3, 4)
          for q in CTX["questions"] for e in q["corpus"]))


# ── §4 ce que le modèle ne peut pas émettre ───────────────────────────────────────────────────────
print("\n[4] le modèle produit des RÉPONSES ; les statuts du référentiel et les axes lui échappent")
_statuts = set(get_args(A.AnalysteReponse.model_fields["statut"].annotation))
check("le modèle ne peut émettre NI `sans_objet` NI `non_fondable`",
      not (_statuts & {"sans_objet", "non_fondable"}), f"→ {sorted(_statuts)}")
check("… mais il peut dire `sans_fondement` (la matière d'un gap, jamais le gap lui-même)",
      "sans_fondement" in _statuts)
_champs = set(A.AnalysteReponse.model_fields)
check("aucun champ `rang_derive`/`nature_effective` : les axes sont dérivés, pas déclarés",
      not (_champs & {"rang_derive", "nature_effective", "fondation", "gap"}), f"→ {sorted(_champs)}")
check("aucun champ d'en-tête (ticker/framework/version/analyste) : le code le pose (#36/#57)",
      not (_champs & {"ticker_id", "framework_id", "schema_version", "analyste"}))
check("`AnalysteSortie` n'a QUE `reponses`",
      set(A.AnalysteSortie.model_fields) == {"reponses"},
      f"→ {set(A.AnalysteSortie.model_fields)}")
leve("une réponse SANS citation est refusée à la construction (une réponse sans source est un avis)",
     lambda: A.AnalysteReponse(question_id="qf_4", statut="repondu", verbatim="x",
                               sens="aucune_contrainte"), ValidationError)
leve("une réponse sans `sens` est refusée (elle ne serait comparable à aucune autre)",
     lambda: A.AnalysteReponse(question_id="qf_4", statut="repondu", verbatim="x",
                               cited_entry_ids=[1]), ValidationError)
leve("un `sans_fondement` qui cite ses sources est refusé (c'est une réponse déguisée en manque)",
     lambda: A.AnalysteReponse(question_id="qf_4", statut="sans_fondement", verbatim="il manque x",
                               cited_entry_ids=[1]), ValidationError)
leve("un `approxime` sans bloc `approximation` est refusé (contrôle ③, §3.2)",
     lambda: A.AnalysteReponse(question_id="qf_4", statut="approxime", verbatim="~12 %",
                               sens="aucune_contrainte", cited_entry_ids=[1]), ValidationError)
leve("un `repondu` QUI PORTE une approximation est refusé (contrôle ④ : non-substitution)",
     lambda: A.AnalysteReponse(question_id="qf_4", statut="repondu", verbatim="12 %",
                               sens="aucune_contrainte", cited_entry_ids=[1],
                               approximation=dict(methode="règle de trois",
                                                  ingredients_entry_ids=[1],
                                                  hypotheses_explicites=["mix stable"],
                                                  sensibilite="±3 pts")), ValidationError)


# ── §5 les deux axes sont dérivés, par leurs détenteurs ───────────────────────────────────────────
print("\n[5] `rang_derive` et `nature_effective` sont CALCULÉS depuis les entries réellement citées")
_asm = dict(question=Q["qf_6"], entries=ENTRIES, **_entete)


def brute(**kw):
    base = dict(question_id="qf_6", statut="repondu", verbatim="12 %", sens="part_significative",
                cited_entry_ids=[1])
    return A.AnalysteReponse(**{**base, **kw})


_r1 = A.assembler_answer(brute(cited_entry_ids=[1, 2]), **_asm)
check("le rang d'une réponse directe est celui de la PLUS FAIBLE entry citée (A + B+ → B+)",
      _r1.fondation.rang_derive == "B+", f"→ {_r1.fondation.rang_derive}")
_r2 = A.assembler_answer(brute(statut="approxime", cited_entry_ids=[1],
                               approximation=dict(methode="règle de trois",
                                                  ingredients_entry_ids=[1],
                                                  hypotheses_explicites=["mix stable"],
                                                  sensibilite="±3 pts")), **_asm)
check("une approximation est rangée UN CRAN SOUS la plus faible citée (A → A-)",
      _r2.fondation.rang_derive == "A-", f"→ {_r2.fondation.rang_derive}")
check("… et sa nature est forcée à `interpretation` (une estimation n'est jamais une mesure, §1.5)",
      _r2.fondation.nature_effective == "interpretation")
check("la nature forte n'est concédée que si TOUTES les entries citées la portent",
      A.assembler_answer(brute(cited_entry_ids=[1]), **_asm).fondation.nature_effective == "mesure"
      and _r1.fondation.nature_effective == "interpretation",
      "→ une mesure citée à côté d'un commentaire est une lecture des deux, donc une interprétation")
check("les citations sont dédoublonnées sans changer le rang (un id répété n'est pas deux preuves)",
      A.assembler_answer(brute(cited_entry_ids=[1, 1, 2]),
                         **_asm).fondation.cited_entry_ids == [1, 2])
_src_asm = inspect.getsource(A.assembler_answer)
check("la règle du cran n'est pas recopiée : le code interroge son détenteur (#46)",
      "derive_synthesis_reliability" in _src_asm and "_NOTCH_BELOW" not in _src_asm)
check("la règle « la plus faible citée » non plus (elle vient du pont, détenteur unique)",
      "_plus_faible" in _src_asm and "max(" not in _src_asm)
# Une entry citée HORS corpus ne fait pas crasher l'assemblage : c'est le pont [B] qui la nomme.
_hors = A.assembler_answer(brute(cited_entry_ids=[1, 999]), **_asm)
check("une entry hors corpus ne fait pas crasher l'assemblage — le pont [B] la refuse, nommément",
      999 in _hors.fondation.cited_entry_ids)
check("… et son tier inconnu vaut le PIRE tier connu, jamais le meilleur",
      _hors.fondation.rang_derive == "C", f"→ {_hors.fondation.rang_derive}")
leve("… et le pont la refuse bien",
     lambda: valider_pont_framework_answer(_hors, questions=question_profiles(F), entries=ENTRIES),
     FrameworkAnswerRefused)


# ── §6 [S] contre les profils RÉELS ───────────────────────────────────────────────────────────────
print("\n[6] le `sens` appartient au vocabulaire FERMÉ de la question — éprouvé sur les profils réels")
PROFILS = question_profiles(F)
check("chaque profil réel porte un `sens_admis` non vide (sinon [S] se sauterait partout)",
      all(p.get("sens_admis") for p in PROFILS.values()))


# ⚠️ La fixture cite l'entry 2 (`interpretation`), et PAS l'entry 1 : `qf_6` attend une assertion de
# nature `interpretation`, donc citer une mesure ferait rougir [E] AVANT que [S] ne soit atteint. Une
# fixture qui déclenche deux contrôles ne dit pas lequel discrimine (1ᵉʳ faux vert) — mesuré ici, pas
# prévu : la première version de ce bloc passait au vert par [E].
def pont_sur(sens):
    rep_brute = brute(sens=sens, cited_entry_ids=[2])
    valider_pont_framework_answer(
        A.assembler_answer(rep_brute, question=Q["qf_6"], entries=ENTRIES, **_entete),
        questions=PROFILS, entries=ENTRIES)


def refus_s(label, sens):
    """Le pont doit refuser, ET PAR [S] — le motif est vérifié, pas seulement le type."""
    global ok, fail
    try:
        pont_sur(sens)
        fail += 1
        print(f"  FAIL {label} → ACCEPTÉ par le pont")
    except FrameworkAnswerRefused as e:
        if "hors du vocabulaire" in str(e):
            ok += 1
            print(f"  ok   {label}")
        else:
            fail += 1
            print(f"  FAIL {label} → refusé, mais PAS par [S] : {str(e)[:150]}")
    except Exception as e:  # noqa: BLE001
        fail += 1
        print(f"  FAIL {label} → mauvaise exception {type(e).__name__}: {str(e)[:140]}")


refus_s("[S] un sens plausible mais hors vocabulaire est refusé (« plutot_bon » sur qf_6)",
        "plutot_bon")
refus_s("[S] le sens d'une AUTRE question est refusé aussi (le vocabulaire est par question)",
        "autonomie_longue")
try:
    pont_sur("part_significative")
    ok += 1
    print("  ok   [S] … et un sens admis passe (sinon les deux refus ci-dessus ne discriminent rien)")
except Exception as e:  # noqa: BLE001
    fail += 1
    print(f"  FAIL [S] un sens admis doit passer → {type(e).__name__}: {str(e)[:160]}")
check("les profils réels sont des COPIES (muter un `sens_admis` n'élargit pas le référentiel caché)",
      question_profiles(F)["qf_6"]["sens_admis"] is not PROFILS["qf_6"]["sens_admis"],
      "→ le référentiel est en `lru_cache` : une liste partagée s'assouplirait pour tout le process")


# ── §7 trois états nommés, aucune évaporation ─────────────────────────────────────────────────────
print("\n[7] chaque question sort en réponse OU en refus — et une omission d'agent n'est PAS un gap")
APX = dict(methode="rapport sur le trimestre annualisé", ingredients_entry_ids=[1],
           hypotheses_explicites=["rythme de dépense constant"], sensibilite="±2 trimestres")
NOMINAL = [
    dict(question_id="qf_4", statut="repondu", verbatim="aucune dette financière",
         sens="aucune_contrainte", cited_entry_ids=[1]),
    dict(question_id="qf_6", statut="approxime", verbatim="~15 % du résultat publié",
         sens="part_significative", cited_entry_ids=[1], approximation=APX),
    dict(question_id="qf_7", statut="sans_fondement",
         verbatim="la consommation de trésorerie des 4 derniers trimestres n'est dans aucune source"),
]


def passage(reponses):
    """Rejoue `repondre` hors-ligne : le modèle est remplacé, TOUT le reste est le vrai code.

    ⚠️ Une exception est RENDUE, pas propagée : un passage qui meurt doit faire rougir des asserts,
    pas tuer le script avant son bilan (2ᵉ faux vert, `feedback_test_negatif_trois_faux_verts`).
    """
    class _Run:
        def __init__(self, parsed):
            self.parsed = parsed

    async def _faux_run(agent, messages, modele, **kw):
        return _Run(modele(reponses=reponses))

    vrai_run, vrai_resolve = A.run_json_agent, A._resolve_analyste_agent
    A.run_json_agent = _faux_run
    A._resolve_analyste_agent = lambda: asyncio.sleep(0)
    try:
        return asyncio.get_event_loop().run_until_complete(
            A.repondre(TICKER, "qualite_financiere", "pre_revenus",
                       analyste="analyste_1", entries=ENTRIES, fichier=F))
    except Exception as exc:  # noqa: BLE001
        return exc
    finally:
        A.run_json_agent, A._resolve_analyste_agent = vrai_run, vrai_resolve


def _ans(r):
    return r.answers if isinstance(r, A.ResultatAnalyste) else []


def _ref(r):
    return r.refus if isinstance(r, A.ResultatAnalyste) else [("<passage mort>", repr(r))]


R = passage(NOMINAL)
_par_statut = {}
for a in _ans(R):
    _par_statut.setdefault(a.statut, []).append(a.question_id)
check("les 7 questions du framework sont traitées, sans doublon",
      sorted(a.question_id for a in _ans(R)) == sorted(Q),
      f"→ {sorted(a.question_id for a in _ans(R))} / refus {_ref(R)}")
check("les 4 hors-sujet de l'archétype sortent en `sans_objet`, écrits par le code",
      sorted(_par_statut.get("sans_objet", [])) == ["qf_1", "qf_2", "qf_3", "qf_5"],
      f"→ {_par_statut}")
check("la réponse directe et l'approximation sont acquittées par le pont",
      _par_statut.get("repondu") == ["qf_4"] and _par_statut.get("approxime") == ["qf_6"],
      f"→ {_par_statut}")
_nf = [a for a in _ans(R) if a.statut == "non_fondable"]
check("le `sans_fondement` du modèle devient un `non_fondable` PORTEUR DE SON GAP",
      _par_statut.get("non_fondable") == ["qf_7"] and _nf
      and _nf[0].gap.champs_cibles == ["qf_7"])
_gap = _nf[0].gap if _nf else None
check("… avec le remède `collecte`, jamais `rafraichissement` (#54)",
      _gap is not None and _gap.remede == "collecte",
      "→ l'actualité se calcule au point de lecture, elle ne se répare pas à l'écriture")
check("… et le manque est celui que l'analyste a NOMMÉ (pas un motif générique)",
      _gap is not None and "trésorerie" in _gap.manque)
check("un passage nominal ne produit AUCUN refus",
      _ref(R) == [], f"→ {_ref(R)}")

# Les pannes d'agent. Chacune sort en REFUS, et surtout : aucune ne produit de `gap`.
_omis = passage([r for r in NOMINAL if r["question_id"] != "qf_4"])
check("une question OMISE par le modèle sort en refus, jamais en réponse",
      [q for q, _ in _ref(_omis)] == ["qf_4"]
      and "qf_4" not in [a.question_id for a in _ans(_omis)], f"→ {_ref(_omis)}")
check("⚠️ … et surtout PAS en `non_fondable` : une panne d'agent n'est pas un manque de données",
      not any(a.statut == "non_fondable" and a.question_id == "qf_4" for a in _ans(_omis)),
      "→ la convertir en gap enverrait la chaîne chercher dehors ce qui manquait dedans")
check("… le motif nomme la panne d'agent, pour qu'aucun lecteur ne la lise comme un trou de corpus",
      bool(_ref(_omis)) and "omise par l'analyste" in _ref(_omis)[0][1],
      f"→ {_ref(_omis)}")

_double = passage(NOMINAL + [NOMINAL[0]])
check("une DEUXIÈME réponse du même analyste à la même question sort en refus (§3.4)",
      [q for q, _ in _ref(_double)] == ["qf_4"]
      and sorted(a.question_id for a in _ans(_double)) == sorted(Q),
      f"→ {_ref(_double)}")

_intrus = passage(NOMINAL + [dict(question_id="qf_1", statut="repondu", verbatim="18 %",
                                  sens="cree_de_la_valeur", cited_entry_ids=[1])])
check("une réponse à une question SANS OBJET est refusée (elle écraserait le hors-sujet du référentiel)",
      [q for q, _ in _ref(_intrus)] == ["qf_1"]
      and [a.statut for a in _ans(_intrus) if a.question_id == "qf_1"] == ["sans_objet"],
      f"→ {_ref(_intrus)}")

_hors_voc = passage([{**NOMINAL[0], "sens": "plutot_bon"}] + NOMINAL[1:])
check("un refus du PONT reste à sa question et n'interrompt pas le passage",
      [q for q, _ in _ref(_hors_voc)] == ["qf_4"]
      and len(_ans(_hors_voc)) == len(Q) - 1, f"→ {_ref(_hors_voc)}")
check("… et ce refus ne produit lui non plus aucun `gap` (le corpus n'y est pour rien)",
      not any(a.question_id == "qf_4" for a in _ans(_hors_voc)))

# L'ÉVAPORATION, EXERCÉE et pas seulement relue dans le source. On sabote la moitié « hors-sujet »
# du partage : les 4 questions sans objet ne sortent plus nulle part. `repondre` doit LEVER —
# un dossier « complet » sur 3 questions au lieu de 7 est le faux vert que toute la v3 combat.
_vrai_hs = A.questions_sans_objet
A.questions_sans_objet = lambda *a, **k: []
try:
    _evap = passage(NOMINAL)
finally:
    A.questions_sans_objet = _vrai_hs
check("une question qui ne sort NI en réponse NI en refus fait LEVER `AnalysteEvaporation`",
      isinstance(_evap, A.AnalysteEvaporation),
      f"→ {type(_evap).__name__} : sans cette garde, 3 questions sur 7 se liraient « dossier complet »")
check("… et le motif NOMME les questions perdues (un refus qui ne dit pas quoi ne se rouvre pas)",
      isinstance(_evap, A.AnalysteEvaporation)
      and all(q in str(_evap) for q in ("qf_1", "qf_2", "qf_3", "qf_5")), f"→ {_evap}")


# ── §8 les statuts admissibles, calculés AVANT la dépense ─────────────────────────────────────────
print("\n[8] une exigence que le modèle ne peut ni voir ni satisfaire se refuse AVANT l'appel (#40)")

# Le défaut mesuré contre le VRAI modèle (NVDA + RVMD) : `nature_attendue` et l'interaction
# plancher × règle du cran ne vivaient que dans le pont, donc APRÈS la dépense. 3 questions sur 14
# sortaient en `refus` — donc sans mandat — alors que le corpus ne POUVAIT pas fonder la réponse.
_ouv_qf4, _ecart_qf4 = A.statuts_admissibles(Q["qf_4"], A.corpus_citable(Q["qf_4"], ENTRIES))
check("au plancher `A`, `approxime` est FERMÉ : le cran sous la meilleure source tombe sous le plancher",
      "approxime" not in _ouv_qf4,
      f"→ {_ouv_qf4} ; sans ce calcul, [D] refuse APRÈS l'appel et la question ne produit aucun mandat")
check("… et le motif dit les DEUX termes (meilleure source, cran obtenu), pas « refusé »",
      any("un cran sous" in m and "plancher" in m for m in _ecart_qf4), f"→ {_ecart_qf4}")

# La DISCRIMINATION : la même règle doit laisser `approxime` ouvert là où le plancher le permet,
# sinon l'assert précédent serait vrai d'une fonction qui ferme tout (fixture non discriminante).
_ouv_qf6, _ = A.statuts_admissibles(Q["qf_6"], A.corpus_citable(Q["qf_6"], ENTRIES))
check("au plancher `B+` avec une source `A`, `approxime` reste OUVERT (la règle discrimine)",
      "approxime" in _ouv_qf6, f"→ {_ouv_qf6}")

# `repondu` fermé quand la nature attendue est ABSENTE du corpus citable — le cas RVMD qf_6.
_MESURES_SEULES = {i: e for i, e in ENTRIES.items() if e.get("nature") == "mesure"}
_ouv_nat, _ecart_nat = A.statuts_admissibles(
    Q["qf_6"], A.corpus_citable(Q["qf_6"], _MESURES_SEULES))
check("`repondu` est FERMÉ quand aucune entry citable ne porte la `nature_attendue` ([E], cas RVMD)",
      "repondu" not in _ouv_nat, f"→ {_ouv_nat}")
check("… et le motif nomme la nature manquante ET celles que le corpus porte (deux causes, deux remèdes)",
      any("interpretation" in m and "mesure" in m for m in _ecart_nat), f"→ {_ecart_nat}")
check("⚠️ le corpus n'est PAS filtré par nature pour autant : [E] veut la nature PRÉSENTE, pas SEULE",
      len(A.corpus_citable(Q["qf_6"], ENTRIES)) > 1
      and {str(e.get("nature")) for e in A.corpus_citable(Q["qf_6"], ENTRIES).values()} != {"interpretation"},
      "→ retirer les `mesure` d'une question d'interprétation la priverait des chiffres qui l'étayent")

check("`sans_fondement` reste ouvert dans TOUS les cas (on ne retire jamais la sortie honnête, #60)",
      all("sans_fondement" in o for o in (_ouv_qf4, _ouv_qf6, _ouv_nat)),
      "→ fermer les trois laisserait le choix entre mentir et se taire")
# ⚠️ Asserté sur la STRUCTURE, jamais sur le texte (#56). Un `"derive_synthesis_reliability" in
# source` serait satisfait par le commentaire qui la mentionne (faux vert), et un `"A-" not in
# source` rougirait sur la docstring qui explique précisément que le cran rend `A-` (faux rouge,
# `feedback_grep_interdit_lit_sa_propre_enonciation`). `code_seul` ne sert à rien ici : il retire
# TOUTES les chaînes, donc un `"A-"` recopié y deviendrait invisible.
_ast_stat = ast.parse(textwrap.dedent(inspect.getsource(A.statuts_admissibles)))
check("la règle du cran est réellement APPELÉE (#46) — un `Call`, pas une mention en prose",
      any(isinstance(n, ast.Call) and getattr(n.func, "id", None) == "derive_synthesis_reliability"
          for n in ast.walk(_ast_stat)),
      "→ recopier la table des crans ici la ferait diverger de son détenteur au premier ajustement")
check("… et aucun tier n'est écrit EN DUR dans la fonction (le vocabulaire vient de `TIER_ORDER`)",
      not [n.value for n in ast.walk(_ast_stat)
           if isinstance(n, ast.Constant) and n.value in TIER_ORDER],
      f"→ {[n.value for n in ast.walk(_ast_stat) if isinstance(n, ast.Constant) and n.value in TIER_ORDER]}")

# Le CONTEXTE : il porte le vocabulaire fermé, et reste lever-free. Asserté sur les DONNÉES
# sérialisées, jamais sur la prose du prompt (#56).
_qctx = {q["id"]: q for q in CTX["questions"]}
check("le contexte porte `statuts_admis` par question (vocabulaire fermé, même forme que `sens_admis`)",
      all("statuts_admis" in q and q["statuts_admis"] for q in CTX["questions"]),
      f"→ {[(i, q.get('statuts_admis')) for i, q in _qctx.items()]}")
check("… et il ne porte toujours NI `plancher_tier` NI `nature_attendue` (le levier reste hors de vue, #59)",
      not any(c in json.dumps(CTX, ensure_ascii=False)
              for c in ("plancher_tier", "nature_attendue")),
      "→ dire ce qui est ouvert n'est pas montrer combien de preuve suffit")

# LE CAS MORT : aucune réponse recevable possible. Corpus de `interpretation` tier A seulement, sur
# une question `mesure` au plancher `A` → `repondu` fermé (nature absente) ET `approxime` fermé
# (cran sous le plancher). La question doit sortir en `non_fondable` SANS aucun appel modèle.
_INTERPS_A = {9: {"reliability_tier": "A", "nature": "interpretation", "title": "commentaire",
                  "content": "la direction se dit confiante", "source_type": "edgar_official",
                  "source_date": "2025-06-01"}}
_ouv_mort, _ = A.statuts_admissibles(Q["qf_4"], A.corpus_citable(Q["qf_4"], _INTERPS_A))
check("un corpus qui atteint le plancher mais ne peut fonder AUCUNE réponse ne laisse que `sans_fondement`",
      _ouv_mort == ["sans_fondement"], f"→ {_ouv_mort}")


def passage_corpus(reponses, entries):
    """Comme `passage`, sur un corpus choisi — et en COMPTANT les appels modèle.

    Le nombre d'appels EST la mesure de #40 : une question infondable qui part quand même au modèle
    coûte un appel pour apprendre ce qu'une lecture du référentiel disait déjà.
    """
    class _Run:
        def __init__(self, parsed):
            self.parsed = parsed

    appels = []

    async def _faux_run(agent, messages, modele, **kw):
        appels.append(messages)
        return _Run(modele(reponses=reponses))

    vrai_run, vrai_resolve = A.run_json_agent, A._resolve_analyste_agent
    A.run_json_agent = _faux_run
    A._resolve_analyste_agent = lambda: asyncio.sleep(0)
    try:
        return asyncio.get_event_loop().run_until_complete(
            A.repondre(TICKER, "qualite_financiere", "pre_revenus",
                       analyste="analyste_1", entries=entries, fichier=F)), appels
    except Exception as exc:  # noqa: BLE001
        return exc, appels
    finally:
        A.run_json_agent, A._resolve_analyste_agent = vrai_run, vrai_resolve


# Sur `pre_revenus`, seules qf_4/qf_6/qf_7 sont applicables. Corpus : une entry `B+`/`mesure`, qui
# tue les trois par DEUX chemins différents — qf_4/qf_7 (plancher A) n'ont aucune source citable
# (branche 2a), qf_6 (plancher B+) en a une mais aucune réponse recevable (branche 2b).
_BPLUS_MESURE = {7: {"reliability_tier": "B+", "nature": "mesure", "title": "note sectorielle",
                     "content": "charges de structure estimées", "source_type": "analyst_note",
                     "source_date": "2025-07-01"}}
_Rm, _appels = passage_corpus([], _BPLUS_MESURE)
_morts = [a for a in _ans(_Rm) if a.statut == "non_fondable"]
_nf_morts = sorted(a.question_id for a in _morts)
check("les questions infondables sortent en `non_fondable`, SANS aucun appel modèle (#40)",
      _nf_morts == ["qf_4", "qf_6", "qf_7"] and _appels == [],
      f"→ non_fondable {_nf_morts} / {len(_appels)} appel(s) modèle")
# ⚠️ `_morts` est exigé NON VIDE : la 1ʳᵉ version de ces trois asserts était un `all(...)` sur une
# liste vide — donc VERTE sur rien. C'est le faux vert que le FAIL ci-dessus a fait apparaître.
check("… et c'est bien un MANQUE DE DONNÉES : chacune porte son gap en `collecte` (donc un mandat)",
      len(_morts) == 3 and all(a.gap is not None and a.gap.remede == "collecte" for a in _morts),
      "→ c'est l'erreur symétrique de l'en-tête : imputer à l'agent un corpus qui ne pouvait pas "
      "fonder condamnerait la question au silence, faute de mandat")
# Le CONTEXTE ne montre pas une question morte. ⚠️ L'assert discrimine les DEUX portes : qf_6 a un
# corpus citable NON VIDE (donc la porte « pas de corpus » ne l'aurait pas retirée) et sort quand
# même du contexte — c'est bien la porte des statuts qui l'a fermée.
_CTX_MORT = A.contexte_analyste(F, "qualite_financiere", "pre_revenus", TICKER, _BPLUS_MESURE)
check("une question dont AUCUN statut n'est ouvert n'est pas montrée au modèle (elle a pourtant un corpus)",
      [q["id"] for q in _CTX_MORT["questions"]] == []
      and len(A.corpus_citable(Q["qf_6"], _BPLUS_MESURE)) > 0,
      f"→ contexte {[q['id'] for q in _CTX_MORT['questions']]} / "
      f"citables qf_6 {len(A.corpus_citable(Q['qf_6'], _BPLUS_MESURE))}")

_manques = {a.question_id: a.gap.manque for a in _morts}
check("… et les DEUX causes ont DEUX motifs distincts (aucune source ≠ aucune réponse recevable)",
      len(_morts) == 3
      and "aucune source fournie ne fonde" in _manques.get("qf_4", "")
      and "aucune réponse recevable" in _manques.get("qf_6", ""),
      f"→ {_manques}")

# La faute SYMÉTRIQUE : le modèle sort du vocabulaire fermé qu'on lui a montré. C'est une panne
# d'agent — refus nommé, et surtout AUCUN gap.
_hors_statut = passage([{**NOMINAL[0], "statut": "approxime", "approximation": APX}] + NOMINAL[1:])
check("un statut HORS `statuts_admis` sort en refus nommé (le vocabulaire était fermé et montré)",
      [q for q, _ in _ref(_hors_statut)] == ["qf_4"]
      and "hors des statuts ouverts" in (_ref(_hors_statut)[0][1] if _ref(_hors_statut) else ""),
      f"→ {_ref(_hors_statut)}")
check("⚠️ … et ce refus ne produit AUCUN gap : désobéir au vocabulaire n'est pas manquer de données",
      not any(a.question_id == "qf_4" and a.statut == "non_fondable" for a in _ans(_hors_statut)),
      "→ les deux sens comptent : ni blanchir une panne d'agent, ni imputer à l'agent un corpus muet")


print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
