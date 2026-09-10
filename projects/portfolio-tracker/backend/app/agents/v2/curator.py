"""
knowledge-curator (V2) — le GATE GO/NO-GO. Produit `readiness_report_json` (§7) et, seulement si
`ready`, le `context_pack` front-loadé (§5.3). C'est le péage AVANT toute dépense Opus/DeepSeek lourde.

Discipline de déterminisme (readiness = « derived, cheap ») : le LLM ne sert qu'au JUGEMENT sémantique
de couverture (quels champs la KB fonde, gaps, rationale) ; le code RECOMPUTE tout ce qui est
arithmétique — `entries_par_tier` (SQL), `ok`/`bloc_ok` (dérivés de champs_non_fondables), `verdict`
(compute_verdict) — et Pydantic verrouille la cohérence (bijection gaps↔manques, ready⇒context_pack).

Le contexte (préambule + rôle) est figé en tête (cache) ; les entries + la tâche du tour en fin.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from app.agents.providers import ResolvedAgent, get_agent_provider
from app.agents.v2.common import (
    FIELD_PROFILES, MVDD_SPEC, TIER_ORDER, count_tiers, format_entries_for_prompt,
)
from app.agents.v2.runner import extract_json
from app.contracts import ContextPack, ReadinessReport, compute_cause_non_ready
from app.db.database import get_db_session
from app.knowledge import get_current_entries, store_knowledge
from app.knowledge.actualite import etat_actualite_entry
from app.knowledge.material_events import (
    MaterialEventLookup, ancre_substantielle, material_anchor_for_ticker,
)

logger = logging.getLogger(__name__)

_TIER_RANK = {t: i for i, t in enumerate(TIER_ORDER)}  # 0 = meilleur (A) … plus grand = plus faible

# ⚠️ `FIELD_PLANCHER_OVERRIDES` A ÉTÉ RETIRÉ (capacité 4, 2026-09-08) — ne pas le réintroduire.
#
# Il portait un seul champ (`marche.croissance_marche_historique: B`) et vivait à côté de
# `FIELD_PROFILES`, qui porte le plancher des 19 champs depuis la capacité 0. Deux tables pour une
# seule règle : c'est le motif de #46, et l'écart était déjà nommé dans `_DESSERRAGE_NON_CABLE`
# (`check_source_registry.py` §1bis). Sa conséquence était mesurable — le desserrage B+ → B de #50
# sur `positionnement.moat_preuves`, `positionnement.position_vs_pairs` et
# `marche.structure_5forces` vivait dans la doctrine sans jamais atteindre la porte : une entry B
# admise par le registre nominatif (#52) était **encore refusée** ici. La porte lit désormais
# `FIELD_PROFILES`, détenteur unique, et le desserrage prend effet — ce que la capacité 2 avait
# préparé et que seule la capacité 4 pouvait câbler.

# Champs requis GÉNUINEMENT introuvables (aucune source accessible à aucun tier — ni KB, ni web même
# dégradé, ni synthèse) : ils NE bloquent PAS `ready` mais sont portés comme LACUNE DÉCLARÉE
# (incertitude investissable « non quantifiée »). Décision méthodo 2026-08-26 : mieux vaut une thèse
# ready avec un trou VISIBLE et assumé qu'un blocage indéfini sur une donnée qui n'existe pas.
#
# ⚠️ Une dispense est PAR ÉMETTEUR, jamais globale. Constaté sur le 2ᵉ ticker (MSFT, 2026-08-30) :
# les deux dispenses ci-dessous étaient des constantes globales, donc MSFT héritait en silence d'un
# passe-droit sur `business_model.recurrence_pct` justifié par « NVIDIA est un business hardware-
# dominant » — alors que Microsoft publie précisément cette donnée (Microsoft Cloud, RPO). Pire, le
# libellé NVDA partait tel quel dans les `incertitudes_investissables` de MSFT. Une dispense énonce
# un fait sur UN émetteur : elle se clef sur lui. Défaut = AUCUNE dispense, donc le champ BLOQUE —
# le sens sûr : on refuse un `ready` de trop, on n'en accorde pas un par héritage.
#
# RETRAIT 2026-08-31 — `NVDA / marche.croissance_marche_historique`. La dispense affirmait « aucune
# source primaire/presse accessible à un tier suffisant » : c'était vrai de la TABLE DE DOMAINES, pas
# du monde. La convention #32 a classé les cabinets d'études en `web_search_reputable` (plafond B),
# ce qui rend enfin le champ atteignable à son plancher B (`FIELD_PLANCHER_OVERRIDES`) — les deux
# garde-fous, réglés séparément, se contredisaient. Retiré sur PREUVE et non sur intuition : un
# mandat NVDA a rendu 3 entries tier B (Omdia 0.630, IDC 0.605, TechInsights 0.602 — entries
# 117-119), là où MSFT en avait déjà 3 (Synergy/Canalys, 109-111). Une dispense se retire quand on a
# montré que le champ se fonde, jamais quand on estime qu'il devrait se fonder.
DECLARED_NONBLOCKING_GAPS: dict[str, dict[str, str]] = {
    "NVDA": {
        "business_model.recurrence_pct":
            "Part des revenus récurrents (logiciels/abonnements) — non chiffrée dans les sources "
            "primaires disponibles. NVIDIA est un business hardware-dominant (quasi-totalité du CA "
            "= vente de GPU/plateformes, one-time) ; NVIDIA AI Enterprise est en croissance mais sa "
            "contribution relative n'est pas disclosée séparément à un tier accessible. "
            "Lacune déclarée, non bloquante.",
    },
}


def nonblocking_gaps_for(ticker_id: Optional[str]) -> dict[str, str]:
    """Dispenses applicables à CET émetteur. Ticker inconnu → dict vide : tous les champs requis
    bloquent tant qu'une dispense n'a pas été écrite pour lui, en connaissance de son cas."""
    return DECLARED_NONBLOCKING_GAPS.get((ticker_id or "").strip().upper(), {})


def _plancher_for(dimension: str, champ: str, dim_plancher: str) -> str:
    """Plancher effectif d'un champ : celui de `FIELD_PROFILES` (#50), sinon celui de la dimension.

    Un champ hors table retombe sur le plancher de dimension plutôt que de lever : le modèle peut
    RESSERRER `champs_requis` en ajoutant un champ (cf. `_exigences`), et un ajout légitime ne doit
    pas faire tomber le rapport. Il n'obtient aucune faveur pour autant — il hérite du plancher le
    plus strict qui lui soit applicable.
    """
    return FIELD_PROFILES.get(f"{dimension}.{champ}", {}).get("plancher") or dim_plancher


def _tier_ge(tier: Optional[str], plancher: str) -> bool:
    """tier ≥ plancher (A=meilleur). tier inconnu/None ne satisfait jamais un plancher."""
    if tier not in _TIER_RANK:
        return False
    return _TIER_RANK[tier] <= _TIER_RANK.get(plancher, len(TIER_ORDER))


def _best_tier(tiers: list[str]) -> Optional[str]:
    valides = [t for t in tiers if t in _TIER_RANK]
    return min(valides, key=lambda t: _TIER_RANK[t]) if valides else None


_MVDD_BY_DIM = {s["dimension"]: s for s in MVDD_SPEC}


def _exigences(dimension: Optional[str], d: dict[str, Any]) -> tuple[list[str], str]:
    """Champs requis + tier plancher d'une dimension : le LLM peut RESSERRER, jamais DESSERRER.

    Le cadre MVDD est le plancher d'exigence (`common.MVDD_SPEC`) ; l'agent peut l'affiner au cas
    d'espèce — ajouter un champ requis, relever le plancher. Mais une fois la couverture pilotée par
    l'index, `champs_requis` et `tier_plancher` sont le DERNIER levier du modèle sur le verdict :
    retirer `recurrence_pct` des requis, ou passer un plancher de A à B, ferait passer la dimension
    sans qu'aucune entry ne bouge. On prend donc l'union des champs et le plus STRICT des planchers.
    """
    spec = _MVDD_BY_DIM.get(dimension or "", {})
    socle: list[str] = list(spec.get("champs_requis") or [])
    proposes = [c for c in (d.get("champs_requis") or []) if isinstance(c, str)]
    requis = socle + sorted(set(proposes) - set(socle))   # ordre stable : socle MVDD, puis ajouts

    candidats = [t for t in (spec.get("tier_plancher"), d.get("tier_plancher")) if t in _TIER_RANK]
    plancher = min(candidats, key=lambda t: _TIER_RANK[t]) if candidats else "B"
    return (requis or ["description"]), plancher


class CouvertureSansEmetteur(RuntimeError):
    """L'index de couverture n'a AUCUN émetteur — la porte ne peut pas prononcer.

    Levée, jamais rattrapée en verdict. C'est la forme de #40 appliquée à la porte : une
    pré-condition d'ÉTAT se refuse AVANT l'appel au modèle, elle ne se déguise pas en résultat.
    """


# ⚠️ `_covers_index()` A ÉTÉ SUPPRIMÉ le 2026-09-10 (migration 036) — ne pas le réintroduire.
#
# Il bâtissait `dimension.champ` → [(entry_id, tier)] depuis `knowledge_entries.covers`. La colonne
# est archivée : ce qu'une entry couvre est une propriété de la RELATION entry ↔ question, elle vit
# dans `question_coverage` (#57). Le laisser en place aurait produit le pire des trois états — il
# aurait rendu `{}` sans erreur, donc TOUS les champs seraient tombés en `non_couvert`, donc la cause
# dérivée aurait été `lacune` et le remède `collecte` : la porte aurait prescrit d'aller chercher
# 19 champs que la base contient déjà. Un verdict faux se corrige ; un REMÈDE faux fait dépenser.
#
# L'index n'a plus d'émetteur tant que le dispatch du lot 2c n'écrit pas `question_coverage`, et il
# n'est pas reconstructible ici : aucune correspondance ne relie les 19 chemins MVDD aux couples
# `question/ingredient`, et en relire une à la main serait « une correspondance construite pour
# tomber juste sur les données d'hier » — ce que l'en-tête de la 036 refuse explicitement, parce
# qu'elle rendrait T1 bon PAR CONSTRUCTION et le défaut indétectable (spec §5.3).
#
# D'où la forme retenue : l'index est un ARGUMENT REQUIS de `recompute_coverage`, et `None` y déclare
# « aucun émetteur » — la porte lève alors au lieu de prononcer. L'écart est réel entre le lot 2b et
# le lot 2c, il est DÉCLARÉ (`check_readiness_recompute.py`, `_INDEX_SANS_EMETTEUR`) sur la forme de
# #52 : un écart inscrit dans le check du lot qui l'a créé, et qui vire au vert de lui-même le jour
# du câblage, plutôt qu'un `TODO` que personne ne relit.

MOTIF_SANS_EMETTEUR = (
    "l'index de couverture n'a aucun émetteur : `knowledge_entries.covers` est archivée "
    "(migration 036) et le dispatch qui écrit `question_coverage` n'existe pas encore (lot 2c). "
    "La porte ne peut pas dire ce que le corpus fonde — elle refuse de prononcer plutôt que de "
    "rendre `lacune` sur des champs dont la matière est déjà en base."
)


def index_couverture_pour(ticker_id: Optional[str]) -> Optional[dict[str, list[tuple[int, str]]]]:
    """L'index de couverture de cet émetteur, ou `None` s'il n'a **aucun émetteur**.

    Détenteur unique de cette réponse (#46) : la porte, l'écran et les outils de mesure la posent au
    même endroit, sinon le jour du câblage il faudrait se souvenir des trois. Rend `None` aujourd'hui,
    pour tous les tickers — ce n'est pas « ce ticker n'a rien », c'est « personne n'écrit encore les
    liens ». Le lot 2c remplacera ce corps par la lecture de `question_coverage`, et ce sera la seule
    ligne à changer.
    """
    return None


def exiger_index_couverture(index: Optional[dict[str, list[tuple[int, str]]]]) -> None:
    """Refuse AVANT toute dépense si l'index n'a pas d'émetteur (#40). Détenteur unique du motif."""
    if index is None:
        raise CouvertureSansEmetteur(MOTIF_SANS_EMETTEUR)


def recompute_coverage(
    coverage: dict[str, Any],
    entries: list[dict[str, Any]],
    *,
    ancre: MaterialEventLookup,
    index_couverture: Optional[dict[str, list[tuple[int, str]]]],
    ticker_id: Optional[str] = None,
    motifs_out: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Recompute déterministe de la couverture — depuis un INDEX, pas depuis le LLM (029).

    Chaque champ requis est fondé si et seulement si l'INDEX rattache au chemin `dimension.champ`
    ≥1 entry courante à un tier RÉEL ≥ plancher DU CHAMP **et** qui tient l'actualité que le champ
    exige. Le LLM n'intervient plus du tout : ni pour proposer, ni pour omettre.

    ⚠️ `index_couverture` est un argument REQUIS, et `None` y signifie « **aucun émetteur** » — pas
    « aucun lien ». Les deux se ressemblent et se lisent à l'opposé : sans émetteur, on ne SAIT pas
    ce que le corpus fonde ; avec un émetteur qui rend zéro lien, on sait qu'il ne fonde rien. Rendre
    le premier cas comme le second ferait tomber les 19 champs en `non_couvert`, donc dériver la
    cause `lacune`, donc envoyer 19 mandats de COLLECTE sur une base qui contient déjà la matière —
    la phrase rassurante (« il suffit de collecter ») produite par la pire des raisons (#49), et un
    remède faux se paie en tokens. D'où `CouvertureSansEmetteur` : la porte lève au lieu de
    prononcer. Même raison que pour `ancre` ci-dessous, un cran plus haut — là, l'oubli d'un appelant
    est une `TypeError` ; ici, l'absence d'émetteur est une exception NOMMÉE.

    Ce que ça corrige (mesuré sur NVDA, corpus STRICTEMENT figé) : l'ancienne version filtrait les
    `entry_ids` que le LLM avait CITÉS — un véto sur la citation, pas un index. Elle fermait le trou
    de SUR-crédit (entry hors-sujet) mais pas celui de SOUS-crédit : une entry adéquate NON citée
    créait un faux creux, et le rattachement par-champ n'étant pas déterministe, le verdict oscillait
    `not_ready` ↔ `thin_qualitative` sur des données identiques (rapports #11/#13/#14).

    LES TROIS AXES, CONSOMMÉS SANS ÊTRE RECOMBINÉS (capacité 4, #50)
    ----------------------------------------------------------------
    La porte lit un TRIPLET, jamais un score : la **fiabilité** (le tier stocké, contre le plancher
    du champ), la **nature** (stockée, migration 034 — elle décide quel axe fait autorité) et
    l'**actualité** (calculée ICI, à la lecture, jamais persistée — #53). Trois états en sortent, et
    la valeur de la capacité tient à ce qu'ils ne se confondent jamais :

      couvert         ≥1 entry au plancher ET (le champ ne bloque pas sur l'actualité OU ≥1 entry
                      est `courante`). Seules les entries fondantes entrent dans `fondations` ;
      couvert_perime  des entries au plancher, mais aucune `courante`. Le champ A de la matière —
                      elle est datée d'avant le dernier événement matériel. Remède : RAFRAÎCHIR ;
      non_couvert     aucune entry au plancher. Remède : COLLECTER.

    ⚠️ `ancre` est un argument REQUIS, sans défaut, et c'est délibéré. Un défaut à « aucun
    événement » rendrait la porte silencieusement laxiste sur tout appelant qui l'oublie, et un
    défaut à « flux injoignable » la rendrait silencieusement bloquante. Une porte de complétude ne
    doit pas pouvoir être appelée sans qu'on ait dit contre quoi elle mesure : l'oubli est une
    `TypeError` au site d'appel, jamais un verdict.

    ⚠️ Une entry `indeterminable` ne fonde PAS un champ où l'actualité bloque — elle n'est pas
    `courante` (#53). Le champ tombe alors en `couvert_perime` et le motif nomme la cause réelle
    (non datable, ou flux injoignable), qui n'est pas la péremption. Conséquence assumée : une panne
    EDGAR fait basculer tous les champs bloquants. C'est bruyant, et c'est le sens sûr — l'inverse
    ferait lire une panne réseau « rien n'a changé », la phrase la plus rassurante produite par la
    pire des raisons (#49).

    `fondations` est RÉÉCRIT depuis l'index : le rapport montre ce qui fonde réellement chaque champ,
    et non ce que le modèle a bien voulu citer. Pur, sans IO — l'ancre est passée par l'appelant.

    `motifs_out`, si fourni, reçoit `dimension.champ` → motif de péremption (la cause nommée entry
    par entry). Il sort par ce canal et non dans `coverage`, qui est un contrat `extra='forbid'` :
    y ajouter une clef de prose le ferait échouer à la validation. Un accumulateur passé par
    l'appelant plutôt qu'un cache de module — un état global survivrait d'un ticker au suivant et
    ferait lire les motifs de NVDA dans le rapport de MSFT (#31 transposé à la mémoire du process).
    """
    exiger_index_couverture(index_couverture)
    index = index_couverture or {}
    corpus = {e["id"]: e for e in entries}
    dispenses = nonblocking_gaps_for(ticker_id)
    for bloc_name in ("structuree", "qualitative_marche"):
        bloc = coverage.get(bloc_name) or {}
        for d in bloc.get("dimensions") or []:
            if not isinstance(d, dict):
                continue
            dim = d.get("dimension")
            requis, dim_plancher = _exigences(dim, d)
            d["champs_requis"] = requis
            d["tier_plancher"] = dim_plancher
            non_fondables: list[str] = []
            perimes: list[str] = []
            fondations: list[dict[str, Any]] = []
            tiers_retenus: list[str] = []
            for champ in requis:
                # Lacune déclarée non-bloquante : ni fondée, ni comptée comme manque (portée en
                # incertitude investissable par _apply_deterministic_overrides).
                path = f"{dim}.{champ}"
                if path in dispenses:
                    continue
                plancher = _plancher_for(dim, champ, dim_plancher)
                # Seules comptent les entries qui PORTENT le champ ET tiennent son plancher. Une
                # entry sous plancher n'est pas une fondation partielle : elle ne compte pas du tout.
                retenues = [(i, t) for i, t in index.get(path, []) if _tier_ge(t, plancher)]
                if not retenues:
                    non_fondables.append(champ)
                    continue

                fondantes, motif = _fondantes_apres_actualite(path, retenues, corpus, ancre)
                if fondantes:
                    fondations.append({"champ": champ, "entry_ids": [i for i, _ in fondantes]})
                    tiers_retenus.extend(t for _, t in fondantes)
                else:
                    non_fondables.append(champ)
                    perimes.append(champ)
                    if motifs_out is not None:
                        motifs_out[path] = motif
            d["fondations"] = fondations
            d["champs_non_fondables"] = non_fondables
            d["champs_perimes"] = perimes
            # tier_atteint = le meilleur tier parmi ce qui fonde VRAIMENT la dimension (une entry
            # écartée — sous plancher OU périmée — ne peut pas rehausser le tier affiché : ce serait
            # un tier de façade).
            d["tier_atteint"] = _best_tier(tiers_retenus)
            d["ok"] = len(non_fondables) == 0
        bloc["bloc_ok"] = bool(bloc.get("dimensions")) and all(x["ok"] for x in bloc["dimensions"])
        coverage[bloc_name] = bloc
    return coverage


def _fondantes_apres_actualite(
    path: str,
    retenues: list[tuple[int, str]],
    corpus: dict[int, dict[str, Any]],
    ancre: MaterialEventLookup,
) -> tuple[list[tuple[int, str]], str]:
    """Parmi les entries au plancher, celles qui fondent VRAIMENT le champ. Rend aussi le motif.

    Le profil du champ décide si l'actualité bloque (#50, capacité 0) — c'est une propriété du
    CHAMP, pas de la source : un cours se périme en jours, une structure concurrentielle en années.
    Un champ hors profil ne bloque pas : la doctrine ne s'invente pas pour un champ que le modèle
    vient d'ajouter aux requis (#31 — pas de traitement « au mieux » sans règle écrite).
    """
    if not FIELD_PROFILES.get(path, {}).get("actualite_bloquante"):
        return retenues, ""

    etats = {i: etat_actualite_entry(corpus.get(i, {}), ancre=ancre, corpus=corpus)
             for i, _ in retenues}
    fondantes = [(i, t) for i, t in retenues if etats[i].etat == "courante"]
    if fondantes:
        return fondantes, ""

    # Aucune ne fonde : le motif nomme la CAUSE entry par entry. `perimee` et `indeterminable` sont
    # deux ignorances différentes et le remède ne se pilote bien qu'en les distinguant.
    detail = " · ".join(f"#{i} {etats[i].etat} — {etats[i].motif}" for i, _ in retenues)
    return [], detail


def reconcile_gaps(
    report: dict[str, Any],
    coverage: dict[str, Any],
    *,
    motifs: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Rebâtit `gaps` pour la bijection stricte champs_non_fondables ↔ gaps (contrat) après recompute,
    et porte sur chacun son REMÈDE. Pur.

    Deux manques, deux gestes (capacité 4) : un champ que rien ne fonde se **collecte** ; un champ
    fondé par une matière antérieure au dernier événement matériel se **rafraîchit**. Les confondre
    enverrait un mandat de recherche chercher ce que la base contient déjà, et laisserait le vrai
    défaut — l'âge — non traité.

    ⚠️ Les gaps du LLM sont rabotés aux champs à **collecter** uniquement. Le modèle décrit une
    absence : il a énuméré ses `queries_suggerees` en croyant le champ vide. Lui laisser porter un
    champ périmé ferait passer un libellé « aucune source ne documente X » sur un champ dont la base
    a trois entries au plancher — juste dans sa forme, faux dans ce qu'il affirme (#42/#45). Les gaps
    de rafraîchissement sont donc TOUJOURS synthétisés par le code, avec le motif nommant l'entry et
    sa cause, qui est ce qu'un humain lira.
    """
    dims = {d["dimension"]: d
            for b in (coverage["structuree"], coverage["qualitative_marche"])
            for d in b["dimensions"]}
    kept: list[dict[str, Any]] = []
    covered: dict[str, set[str]] = {}
    for g in report.get("gaps") or []:
        if not isinstance(g, dict):
            continue
        dim = g.get("dimension")
        if dim not in dims:
            continue
        a_collecter = set(dims[dim]["champs_non_fondables"]) - set(dims[dim].get("champs_perimes") or [])
        cibles = [c for c in (g.get("champs_cibles") or []) if c in a_collecter]
        if not cibles:
            continue
        g["champs_cibles"] = cibles
        g["remede"] = "collecte"
        kept.append(g)
        covered.setdefault(dim, set()).update(cibles)
    for dim, d in dims.items():
        perimes = set(d.get("champs_perimes") or [])
        manquants = [c for c in d["champs_non_fondables"]
                     if c not in covered.get(dim, set()) and c not in perimes]
        if manquants:
            kept.append({
                "dimension": dim,
                "champs_cibles": manquants,
                "manque": f"Aucune entry au tier plancher ne fonde : {', '.join(manquants)}.",
                "queries_suggerees": [],
                "priorite": "moyenne",
                "coverage_actuelle": d.get("tier_atteint") or "aucune",
                "origine": "curator",
                "remede": "collecte",
            })
        a_rafraichir = [c for c in d["champs_non_fondables"] if c in perimes]
        if a_rafraichir:
            detail = " ; ".join(f"{c} — {(motifs or {}).get(f'{dim}.{c}', 'cause non relevée')}"
                                for c in a_rafraichir)
            kept.append({
                "dimension": dim,
                "champs_cibles": a_rafraichir,
                "manque": (f"La base FONDE ces champs au tier plancher, mais aucune entry ne tient "
                           f"l'actualité exigée : {detail}. À RAFRAÎCHIR — la matière existe, elle "
                           f"est antérieure au dernier événement matériel de l'émetteur."),
                "queries_suggerees": [],
                "priorite": "haute",
                # PAS `tier_atteint` : il ne compte que ce qui fonde vraiment, donc il vaudrait
                # « aucune » sur une dimension entièrement périmée — un gap de rafraîchissement
                # annonçant une couverture nulle se lirait comme un gap de collecte.
                "coverage_actuelle": "matière au tier plancher, hors actualité",
                "origine": "curator",
                "remede": "rafraichissement",
            })
    report["gaps"] = kept
    return report


# Vocabulaire FERMÉ des verdicts (ReadinessVerdict). Motifs ordonnés du plus long au plus court :
# `ready` est une sous-chaîne de `not_ready`, il ne se cherche qu'après masquage des composés.
_VERDICT_MOTIFS: tuple[tuple[str, str], ...] = (
    ("not_ready", r"not[_\s]ready"),
    ("thin_qualitative", r"thin[_\s]qualitative"),
    ("too_hard", r"too[_\s]hard"),
    ("researching", r"researching"),
    ("ready", r"\bready\b"),
)
# Fins de phrase ET sauts de ligne : le rationale est souvent une prose à puces.
_DECOUPE_PHRASE = re.compile(r"(?<=[.!?…])\s+|\n+")


def verdicts_nommes(fragment: str) -> set[str]:
    """Verdicts du vocabulaire fermé cités dans un fragment de prose. Pur.

    Chaque motif trouvé est masqué avant d'essayer les suivants, sinon `not_ready` compterait
    aussi comme une mention de `ready`."""
    reste = fragment.lower()
    trouves: set[str] = set()
    for nom, motif in _VERDICT_MOTIFS:
        reste, n = re.subn(motif, " ", reste)
        if n:
            trouves.add(nom)
    return trouves


def constrain_rationale(report: dict[str, Any], coverage: dict[str, Any]) -> dict[str, Any]:
    """Empêche la NARRATION de contredire le verdict — c'est elle que l'humain lit. Pur.

    `_verdict_contraint` protège le GO/NO-GO machine, mais rien ne tenait la prose : rapport NVDA
    #24, verdict `ready`, rationale écrivant « bloc qualitatif-marché incomplet … (tier A-), sous le
    plancher B+ requis … → thin_qualitative » — un autre verdict narré, sur un ordre de tiers inversé
    (A- 0.85 est AU-DESSUS de B+ 0.75). Le tir suivant, à corpus identique, rendait une prose
    correcte : le récit varie là où le verdict ne varie pas.

    Deux mesures, dans l'esprit de #24/#29 (ce qui est dérivable est écrit par le code) :
      1. une ligne d'en-tête FACTUELLE, dérivée des booléens recomputés — l'humain lit le verdict et
         son motif avant toute prose ;
      2. toute phrase du curator nommant un verdict AUTRE que celui recomputé est retirée, et le
         retrait est déclaré (jamais silencieux). On retire à la phrase, pas au rapport : le reste
         de la lecture d'ensemble a de la valeur.
    """
    verdict = report.get("verdict")
    s_ok = coverage["structuree"]["bloc_ok"]
    q_ok = coverage["qualitative_marche"]["bloc_ok"]
    non_fondes = [f"{d['dimension']}.{c}"
                  for b in (coverage["structuree"], coverage["qualitative_marche"])
                  for d in b["dimensions"] for c in d["champs_non_fondables"]]
    perimes = [f"{d['dimension']}.{c}"
               for b in (coverage["structuree"], coverage["qualitative_marche"])
               for d in b["dimensions"] for c in (d.get("champs_perimes") or [])]

    gardees: list[str] = []
    retirees = 0
    for phrase in _DECOUPE_PHRASE.split(report.get("rationale") or ""):
        phrase = phrase.strip()
        if not phrase:
            continue
        if verdicts_nommes(phrase) - {verdict}:
            retirees += 1
            continue
        gardees.append(phrase)

    # La CAUSE est nommée dans l'en-tête, et elle décide du geste : « 9 champs non fondés » envoie
    # chercher de la donnée que la base contient déjà quand ces 9 champs sont en réalité périmés.
    # Elle est dérivée par le détenteur unique du contrat, jamais recomptée ici (#46).
    cause = compute_cause_non_ready(coverage) if isinstance(coverage, dict) else None
    manque = f"{len(non_fondes)} champ(s) non fondé(s)"
    if non_fondes:
        manque += " : " + ", ".join(non_fondes)
    if perimes:
        manque += (f" — dont {len(perimes)} PÉRIMÉ(S) (matière présente au plancher, antérieure au "
                   f"dernier événement matériel ; remède : rafraîchir) : " + ", ".join(perimes))
    entete = (f"[Verdict recomputé : {verdict}"
              f"{f' (cause : {cause})' if cause else ''} — bloc structuré "
              f"{'fondé' if s_ok else 'incomplet'}, bloc qualitatif-marché "
              f"{'fondé' if q_ok else 'incomplet'} ; {manque}. Ligne écrite par le code depuis "
              f"l'index de couverture ; la lecture ci-dessous est celle du curator.")
    if retirees:
        entete += (f" {retirees} phrase(s) du curator retirée(s) : elles nommaient un autre "
                   f"verdict que {verdict}.")
    entete += "]"

    report["rationale"] = entete + ("\n\n" + " ".join(gardees) if gardees else "")
    return report


def _libelle_ancre(ancre: MaterialEventLookup) -> str:
    """L'ancre matérielle en une phrase, pour le prompt. Les trois états sont DITS, jamais confondus
    (#49/#53) : une panne de flux ne doit pas se lire « il ne s'est rien passé »."""
    if ancre.status == "found" and ancre.event is not None:
        e = ancre.event
        items = f", items {'/'.join(e.items)}" if e.items else ""
        return (f"dernier événement matériel : {e.form} du {e.event_date} (date de l'ÉVÉNEMENT"
                f"{items}). Toute assertion antérieure à cette date est présumée périmée.")
    if ancre.status == "none":
        return ("aucun événement matériel publié par l'émetteur — état CONNU, rien ne périme le "
                "corpus aujourd'hui.")
    return (f"flux d'événements matériels INJOIGNABLE ({ancre.raison or 'raison non précisée'}) — "
            f"l'actualité du corpus est indéterminable, ce qui n'est pas « rien n'a changé ».")


def _readiness_task_message(ticker_id: str, entries: list[dict[str, Any]], *,
                            ancre: MaterialEventLookup) -> str:
    spec = json.dumps(MVDD_SPEC, ensure_ascii=False, indent=2)
    listing = format_entries_for_prompt(entries)
    return (
        f"[mode: readiness]\n\n"
        f"Ticker : {ticker_id}\n\n"
        f"Cadre MVDD (8 dimensions, 2 blocs jamais fusionnés — champs requis & tier plancher indicatifs) :\n"
        f"{spec}\n\n"
        f"knowledge_entries COURANTES de la KB ({len(entries)}) — cite-les par entry_id :\n"
        f"{listing}\n\n"
        f"Produis le readiness_report_json (contrat ReadinessReport, JSON strict).\n\n"
        f"Ancre temporelle du dossier — {_libelle_ancre(ancre)}\n\n"
        f"⚠️ La COUVERTURE ne t'appartient pas. Le backend la recompute en Python depuis l'index "
        f"de couverture de la base (quelles entries fondent quel champ, à quel tier réel) : `fondations`, "
        f"`champs_non_fondables`, `champs_perimes`, `tier_atteint`, `ok`, `bloc_ok`, les gaps, le "
        f"verdict et sa `cause_non_ready` sont DÉRIVÉS et écraseront ce que tu écris. Tu ne peux ni "
        f"faire passer un champ, ni en creuser un : laisse `fondations` à [] et ne cherche pas à "
        f"deviner ce qui est fondé.\n\n"
        f"⚠️ La PÉREMPTION ne t'appartient pas non plus. Un champ dont la base porte de la matière "
        f"au tier plancher mais ANTÉRIEURE à l'ancre ci-dessus est classé `couvert_perime` par le "
        f"code, et son remède est un RAFRAÎCHISSEMENT, pas une collecte. N'écris donc pas de gap "
        f"disant qu'une donnée « manque » ou qu'« aucune source ne la documente » sans avoir lu les "
        f"entries : si elle existe et qu'elle est vieille, ton libellé serait faux et il sera "
        f"écarté. Tes gaps ne portent que ce que la base ne contient PAS.\n\n"
        f"Ce qui est VRAIMENT attendu de toi, et que le code ne sait pas produire : le `rationale` "
        f"(lecture d'ensemble du dossier), les `gaps` (ce qui manque, avec des `queries_suggerees` "
        f"actionnables), les `incertitudes_investissables` et `qualite_info`. Reprends les 8 "
        f"dimensions du cadre MVDD ci-dessus avec leurs `champs_requis` et `tier_plancher` (tu peux "
        f"les RESSERRER si le cas d'espèce l'exige — ajouter un champ requis, relever un plancher — "
        f"jamais les assouplir). conviction/marge_securite = null, pas de context_pack_entry_id.\n\n"
        f"⚠️ Dans le `rationale`, ne NOMME aucun verdict (`ready`, `not_ready`, `thin_qualitative`, "
        f"`too_hard`, `researching`) : il est recomputé et affiché par le code, et toute phrase qui "
        f"en nomme un autre sera RETIRÉE. Décris ce que le dossier contient et ce qui lui manque, "
        f"pas la décision. Rappel de l'ordre des tiers, du meilleur au moins bon : "
        f"A > A- > B+ > B > C+ > C — un tier A- (0,85) est AU-DESSUS d'un plancher B+ (0,75)."
    )


def _declare_nonblocking_gaps(
    report: dict[str, Any], coverage: dict[str, Any], ticker_id: Optional[str] = None
) -> dict[str, Any]:
    """Porte chaque lacune déclarée (champ requis introuvable, non bloquant) comme incertitude
    investissable VISIBLE — jamais un trou caché. Dedup par question. Pur.

    Les dispenses sont celles de CET émetteur : un libellé qui parle de NVIDIA n'a rien à faire dans
    les incertitudes de Microsoft."""
    requis_par_dim = {d["dimension"]: set(d.get("champs_requis") or [])
                      for b in (coverage["structuree"], coverage["qualitative_marche"])
                      for d in b["dimensions"]}
    existantes = {u.get("question") for u in (report.get("incertitudes_investissables") or [])}
    ajouts: list[dict[str, str]] = []
    for full, libelle in nonblocking_gaps_for(ticker_id).items():
        dim, champ = full.split(".", 1)
        if champ in requis_par_dim.get(dim, set()) and libelle not in existantes:
            ajouts.append({"question": libelle, "fourchette": "non quantifiée — source indisponible"})
    if ajouts:
        report["incertitudes_investissables"] = (report.get("incertitudes_investissables") or []) + ajouts
    return report


def _apply_deterministic_overrides(
    report: dict[str, Any],
    entries: list[dict[str, Any]],
    *,
    ancre: MaterialEventLookup,
    index_couverture: Optional[dict[str, list[tuple[int, str]]]],
    ticker_id: Optional[str] = None,
) -> dict[str, Any]:
    """Recompute en Python ce qui est dérivé (comptes, couverture, gaps, ok/bloc_ok, verdict, cause)
    — jamais confié au LLM. La couverture par champ est recalculée depuis l'INDEX de couverture
    (recompute_coverage) confronté à l'ancre matérielle (capacité 4), puis les gaps sont reconciliés
    pour tenir la bijection du contrat (reconcile_gaps). Le verdict devient donc une FONCTION du
    corpus ET du moment : à corpus figé, il ne bouge plus tant que l'ancre ne bouge pas.

    ⚠️ `ancre` et `index_couverture` sont requis ici pour la même raison : un défaut ferait d'un
    oubli d'appelant un verdict silencieux au lieu d'une `TypeError`. `index_couverture=None` fait
    lever `CouvertureSansEmetteur` — cette fonction ne rattrape pas : elle est la moitié déterministe
    de la porte, pas sa politique d'erreur, et chaque appelant a la sienne (le POST refuse avant
    toute dépense, le GET sert la ligne persistée en DÉCLARANT qu'elle n'a pas été réévaluée)."""
    report["entries_par_tier"] = count_tiers(entries)

    motifs: dict[str, str] = {}
    coverage = recompute_coverage(report.get("coverage") or {}, entries, ancre=ancre,
                                  index_couverture=index_couverture, ticker_id=ticker_id,
                                  motifs_out=motifs)
    report["coverage"] = coverage
    report["cause_non_ready"] = compute_cause_non_ready(coverage)
    reconcile_gaps(report, coverage, motifs=motifs)
    _declare_nonblocking_gaps(report, coverage, ticker_id)

    # A3 : pas de conviction/marge_securite au readiness
    ind = report.get("indicateurs") or {}
    ind["conviction"] = None
    ind["marge_securite"] = None
    report["indicateurs"] = ind

    # verdict CONTRAINT (G2) sauf décisions non dérivées (too_hard/researching gardés du LLM).
    # Même règle que compute_verdict, appliquée aux booléens recalculés (défense en profondeur :
    # le verdict validé par Pydantic sera de toute façon revérifié contre compute_verdict).
    if report.get("verdict") not in ("too_hard", "researching"):
        s_ok = coverage["structuree"]["bloc_ok"]
        q_ok = coverage["qualitative_marche"]["bloc_ok"]
        report["verdict"] = "ready" if (s_ok and q_ok) else ("thin_qualitative" if s_ok else "not_ready")

    # APRÈS le verdict : la narration se contraint sur le verdict FINAL, pas sur celui du LLM.
    constrain_rationale(report, coverage)
    return report


async def _call_json(agent: ResolvedAgent, task_message: str, *, max_repair: int = 1) -> tuple[dict, int, int, float]:
    """Appel JSON + extraction, avec réparation légère (retourne dict + tokens/coût cumulés).

    ⚠️ PAS de response_format=json_object : mesuré 2026-08-26, DeepSeek-V4-Flash y est NON FIABLE (il
    collapse sur `{}` ou emballe la sortie dans une clé parasite `{"/mnt/data/…json": "<json échappé>"}`
    — cette 2ᵉ pathologie a fait échouer la 1ère production réelle du context_pack). En prompt-only +
    extract_json, le JSON sort propre. Même correctif que run_json_agent(json_object=False)."""
    convo: list[dict[str, Any]] = [{"role": "user", "content": task_message}]
    t_in = t_out = 0
    cost = 0.0
    last_err: Optional[str] = None
    for attempt in range(max_repair + 1):
        res = await agent.complete(convo, temperature=0.2)
        t_in += res.tokens_in
        t_out += res.tokens_out
        cost += res.cost_usd
        try:
            return extract_json(res.content), t_in, t_out, cost
        except json.JSONDecodeError as e:
            last_err = str(e)
            convo += [
                {"role": "assistant", "content": res.content},
                {"role": "user", "content": "Sortie non-JSON. Renvoie UNIQUEMENT l'objet JSON du contrat."},
            ]
    raise RuntimeError(f"curator: JSON illisible après réparation ({last_err})")


async def run_readiness(ticker_id: str) -> dict[str, Any]:
    """Exécute le mode readiness pour un ticker. Persiste dans knowledge_curator_reports.
    Renvoie {report_id, verdict, report_json, context_pack_entry_id}."""
    async with get_db_session() as conn:
        entries = await get_current_entries(conn, ticker_id, min_reliability=0.0, limit=500)

        # ⚠️ Le refus vient AVANT l'appel au modèle, et c'est tout l'intérêt (#40) : une pré-condition
        # d'ÉTAT dit que la question n'avait pas lieu d'être posée. La placer après ferait payer un
        # readiness complet pour apprendre ce qu'on savait avant de commencer. Depuis la 036, l'index
        # n'a aucun émetteur (cf. le commentaire en tête de module) : on passe `None` explicitement
        # plutôt que de laisser un défaut le décider, et `recompute_coverage` lève.
        index_couverture = index_couverture_pour(ticker_id)
        exiger_index_couverture(index_couverture)

        # L'ancre matérielle est lue AVANT toute dépense de tokens (#40) : elle fait partie de la
        # question posée, pas de la mise en forme de la réponse. `ancre_substantielle` écarte les
        # dépôts purement formels (item 9.01 seul) — détenteur unique de « quel événement périme »
        # (#46), le même que celui de l'outil de mesure.
        ancre = ancre_substantielle(await material_anchor_for_ticker(conn, ticker_id))
        agent = await get_agent_provider("knowledge-curator", "v2")

        raw, t_in, t_out, cost = await _call_json(
            agent, _readiness_task_message(ticker_id, entries, ancre=ancre))
        raw.pop("context_pack_entry_id", None)
        report = _apply_deterministic_overrides(raw, entries, ancre=ancre,
                                                index_couverture=index_couverture,
                                                ticker_id=ticker_id)

        context_pack_entry_id: Optional[int] = None

        # Si le verdict recomputé est `ready`, produire le context_pack AVANT la validation : le
        # contrat ReadinessReport exige `context_pack_entry_id` dès que verdict=ready, donc valider
        # d'abord échouerait (bug jamais atteint tant qu'aucun ticker n'était `ready` — le 1er ready
        # réel l'a révélé, 2026-08-26). On se fie au verdict déterministe (compute_verdict), pas au LLM.
        if report.get("verdict") == "ready":
            context_pack_entry_id = await _produce_context_pack(conn, agent, ticker_id, entries)
            report["context_pack_entry_id"] = context_pack_entry_id

        # validation avec réparation Pydantic (une passe) ------------------------------------------
        validated = _validate_or_repair_readiness(report)

        data = validated.model_dump(mode="json")
        row = await conn.fetchrow(
            """
            INSERT INTO knowledge_curator_reports
                (ticker_id, report_type, report_json, verdict,
                 coverage_structuree, coverage_qualitative, context_pack_entry_id)
            VALUES ($1,'readiness',$2,$3,$4,$5,$6)
            RETURNING id
            """,
            ticker_id, data, data["verdict"],
            data["coverage"]["structuree"], data["coverage"]["qualitative_marche"],
            context_pack_entry_id,
        )
        logger.info("curator.readiness %s → %s (report #%s, %d tok_out, $%.4f)",
                    ticker_id, data["verdict"], row["id"], t_out, cost)
        return {
            "report_id": row["id"],
            "verdict": data["verdict"],
            "report_json": data,
            "context_pack_entry_id": context_pack_entry_id,
            "cost_usd": cost,
        }


def _validate_or_repair_readiness(report: dict[str, Any]) -> ReadinessReport:
    """Valide le ReadinessReport ; en cas d'échec on lève une erreur claire (les incohérences de
    couverture LLM sont rares après overrides déterministes ; l'appelant peut relancer run_readiness)."""
    try:
        return ReadinessReport.model_validate(report)
    except Exception as e:  # noqa: BLE001
        logger.error("curator.readiness: ReadinessReport invalide: %s", e)
        raise RuntimeError(f"curator: readiness non conforme au contrat — {e}") from e


async def _produce_context_pack(
    conn, agent: ResolvedAgent, ticker_id: str, entries: list[dict[str, Any]]
) -> int:
    """Génère le context_pack (ready-only), le valide (ContextPack) et le persiste comme
    knowledge_entry source_type='agent_synthesis'. Renvoie l'entry_id."""
    listing = format_entries_for_prompt(entries)
    msg = (
        f"[mode: context_pack]\n\nTicker : {ticker_id}\n\n"
        f"Le readiness est READY. Distille l'état des connaissances en un context_pack (contrat "
        f"ContextPack, JSON strict) : EXACTEMENT les 8 dimensions MVDD dans l'ordre canonique "
        f"(structuree: business_model, financials, valorisation ; puis qualitative_marche: produits, "
        f"positionnement, marche, management_allocation, risques). Chaque dimension : synthèse Markdown "
        f"condensée + tier_atteint + source_entry_refs NON VIDES (triées par entry_id puis version). "
        f"readiness_verdict='ready'. Aucun champ volatil.\n\nknowledge_entries :\n{listing}"
    )
    raw, *_ = await _call_json(agent, msg)
    raw.setdefault("schema_version", "v2.0.0")
    raw["ticker_id"] = ticker_id
    raw["readiness_verdict"] = "ready"
    raw["readiness_report_id"] = raw.get("readiness_report_id") or 0  # rétro-rempli après insertion du report si besoin
    pack = ContextPack.model_validate(raw)
    data = pack.model_dump(mode="json")

    synthese_md = "\n\n".join(
        f"### {d['bloc']} · {d['dimension']} ({d['tier_atteint']})\n{d['synthese']}"
        for d in data["dimensions"]
    )
    stored = await store_knowledge(
        conn,
        ticker_id=ticker_id,
        entry_type="agent_synthesis",
        content=f"# Context pack {ticker_id} (curator, ready)\n\n{synthese_md}",
        content_structured=data,
        source_type="agent_synthesis",
        title=f"Context pack — {ticker_id}",
        tags=["context_pack", "curator"],
    )
    return stored["id"]
