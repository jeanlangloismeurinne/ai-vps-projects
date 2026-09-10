"""Vérification de l'axe ACTUALITÉ (capacité 3, `02-spec-autorite-vs-actualite.md`).

Sans réseau ni modèle. L'axe est le seul des trois qui ne soit **pas** stocké, et c'est tout son
intérêt : le persister reproduirait la cause n°2 du diagnostic (un score figé à l'écriture, donc un
corpus qui ne vieillit jamais). Ce check existe pour que cette propriété ne puisse pas se perdre en
silence — un axe recalculé à la lecture ressemble beaucoup, dans un diff, à un axe qu'on aurait
oublié d'écrire.

  • §1  VOCABULAIRE FERMÉ ET ATTEIGNABLE (#32) — les trois états, chacun vérifié PAR SON NOM depuis
        une entrée réelle. Un état déclaré mais qu'aucune entrée n'atteint est un état mort ; et un
        état vérifié par un `in ETATS` ne prouverait rien du tout.
  • §2  L'ACCEPTATION DE LA CAPACITÉ — la MÊME entry, lue avant et après l'arrivée d'un 8-K
        postérieur, CHANGE d'état, sans qu'aucune écriture n'ait lieu et sans que la ligne lue soit
        mutée. C'est la démonstration que l'axe est une relation, pas une colonne.
  • §3  INDÉTERMINABLE N'EST PAS COURANTE (#44) — deux causes distinctes, chacune NOMMÉE dans le
        motif, et cumulables sans qu'aucune des deux ne soit tue.
  • §4  PROPAGATION DE LA PANNE (#49) — flux injoignable ⇒ `indeterminable`, même sur un fait
        parfaitement daté. Une panne réseau ne doit jamais se lire « rien n'a changé ».
  • §5  `none` ≠ `unavailable` (#25) — l'émetteur qui n'a rien publié est un état CONNU ; le
        confondre avec la panne, c'est produire la phrase la plus rassurante pour la pire raison.
  • §6  LA DATE DU FAIT, ET LA FRONTIÈRE — le seuil est le `reportDate`, jamais le `filingDate`
        (#42/#49) ; et un fait daté du jour même de l'événement est `courante`, pas `perimee`.
  • §7  DÉTENTEUR UNIQUE (#46) — `staleness` TRADUIT l'axe, il ne le ré-implémente pas. C'est la
        garde qui manquait à `_current_fact_ids` (#43) et à `_md` (#46).
  • §8  JAMAIS PERSISTÉ — garde par grep sur le source, comme `staleness.py`.
  • §9  F15, LA PARTITION DU RAPPORT — sur les trois branches, une entry tombe dans EXACTEMENT une
        classe. La section prouve d'abord que le défaut EXISTAIT (partition à deux prédicats
        indépendants), puis que l'axe le ferme : montrer le seul état correct ne prouverait pas
        qu'il y avait quelque chose à corriger (#37).
  • §10 LA CAPACITÉ 4 N'EST PAS FAITE ICI — l'axe ignore `actualite_bloquante`. Confronter dès
        maintenant l'état au profil du champ perturberait la ligne de base que le test central de
        la capacité 4 doit mesurer AVANT son lot (`feedback_ligne_de_base_est_une_mesure`).

⚠️ **Pas de §état persisté, et c'est le sujet même du fichier.** #43 exige de lire la base plutôt
que le diff — mais ici l'absence d'écriture EST la spécification. La section qui en tient lieu est
§8 (grep de source) doublée de §2 (la ligne lue n'est pas mutée) : la première dit qu'aucune
écriture n'est écrite, la seconde qu'aucune n'est nécessaire.
"""
import asyncio
import inspect
import re
import sys
from datetime import date

import app.knowledge.staleness as _st
from app.knowledge.actualite import CLASSE_RAPPORT, ETATS, Actualite, etat_actualite
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def axe(**kw):
    """Appelle l'axe, en transformant une exception en FAIL **nommé**.

    Mesuré, pas prévu : le cas négatif « propagation de la panne retirée » fait tomber
    `etat_actualite` sur son `assert ancre.event is not None` (le module échoue FERMÉ, ce qui est le
    bon comportement) — et le check mourait alors à la première section touchée, sans bilan et sans
    nommer l'assert qui aurait dû rougir. C'est le **deuxième des trois faux verts** d'un test
    négatif (`CHANTIER_OUTILLAGE_DEV.md` §24) : un script mort avant ses asserts ne prouve rien, il
    ne fait que ne pas contredire.

    L'état de repli porte un nom hors vocabulaire (`(exception)`), donc il ne peut satisfaire aucun
    assert d'état par accident : la section suivante rougit elle aussi, au lieu de passer au vert
    sur un objet complaisant.
    """
    global fail
    try:
        return etat_actualite(**kw)
    except Exception as e:  # noqa: BLE001 — c'est précisément le filet
        fail += 1
        print(f"  FAIL l'axe a LEVÉ au lieu de rendre un état ({type(e).__name__}: {e}) — {kw}")
        return Actualite(etat="(exception)", motif=f"{type(e).__name__}: {e}")


# ── Ancres, copiées du flux RVMD réel (cf. `check_material_events`) ───────────
# ⚠️ Une fixture se copie du RÉEL (`feedback_fixture_copiee_du_reel`) : l'écart de 6 jours entre
# l'événement du 27/08 et son dépôt du 01/09 est celui d'EDGAR, pas une valeur choisie pour que le
# test passe. C'est lui qui rend §6 discriminant.
FDA = MaterialEvent(form="8-K", event_date=date(2026, 8, 26), filing_date=date(2026, 8, 26),
                    items=("8.01",), accession="0001-26", url="https://sec.gov/fda")
ACCORD = MaterialEvent(form="8-K", event_date=date(2026, 8, 27), filing_date=date(2026, 9, 1),
                       items=("1.01", "2.03"), accession="0001-27", url="https://sec.gov/accord")

ANCRE_FDA = MaterialEventLookup(status="found", event=FDA, cik=1628171, recents=(FDA,))
ANCRE_ACCORD = MaterialEventLookup(status="found", event=ACCORD, cik=1628171,
                                   recents=(ACCORD, FDA))
ANCRE_AUCUNE = MaterialEventLookup(status="none", cik=1628171)
ANCRE_PANNE = MaterialEventLookup(status="unavailable", cik=1628171, raison="EDGAR 503")


print("\n1. vocabulaire fermé, et les trois états sont ATTEIGNABLES (#32)")
_atteints = {
    axe(source_date=date(2026, 2, 25), ancre=ANCRE_FDA).etat,
    axe(source_date=date(2026, 8, 26), ancre=ANCRE_FDA).etat,
    axe(source_date=None, ancre=ANCRE_FDA).etat,
}
for _etat in ("courante", "perimee", "indeterminable"):
    check(f"l'état `{_etat}` est déclaré au vocabulaire", _etat in ETATS, f"→ {sorted(ETATS)}")
    check(f"l'état `{_etat}` est atteint par une entrée réelle", _etat in _atteints,
          f"→ atteints : {sorted(_atteints)} — un état inatteignable est un état mort (#32)")
check("le vocabulaire ne contient QUE ces trois états", ETATS == {"courante", "perimee",
                                                                  "indeterminable"},
      f"→ {sorted(ETATS)} : un quatrième état (« probablement fraîche ») rouvrirait le scalaire")
check("chaque état du vocabulaire a une classe de rapport", set(CLASSE_RAPPORT) == ETATS,
      f"→ {sorted(set(CLASSE_RAPPORT) ^ ETATS)} sans traduction : le rapport serait muet dessus")


print("\n2. ACCEPTATION — la même entry change d'état à l'arrivée d'un 8-K, sans aucune écriture")
# Une entry écrite le 2026-08-26 : le jour même de l'approbation FDA, donc courante face à elle.
LIGNE = {"id": 186, "source_date": date(2026, 8, 26), "content": "la FDA a approuvé RASONQUE"}
_avant_copie = dict(LIGNE)

av = axe(source_date=LIGNE["source_date"], ancre=ANCRE_FDA)
ap = axe(source_date=LIGNE["source_date"], ancre=ANCRE_ACCORD)

check("AVANT le 8-K suivant : la même entry est `courante`", av.etat == "courante", f"→ {av.etat}")
check("APRÈS le 8-K suivant : la même entry est `perimee`", ap.etat == "perimee", f"→ {ap.etat}")
check("l'état a donc CHANGÉ sans que la donnée bouge", av.etat != ap.etat,
      "→ si les deux coïncident, l'axe ne mesure pas une relation mais une propriété figée")
check("la ligne lue n'a pas été mutée", LIGNE == _avant_copie,
      f"→ {LIGNE} : un axe calculé à la lecture n'écrit pas, fût-ce en mémoire")
check("l'écart au seuil est rendu, et il est positif quand le fait précède",
      ap.jours_avant_evenement == 1, f"→ {ap.jours_avant_evenement}")
check("le motif du périmé dit que le fait reste EXACT à sa date",
      "périmé n'est pas faux" in ap.motif, f"→ {ap.motif}")
check("l'objet rendu est immuable (frozen)",
      type(av).__dataclass_params__.frozen,  # type: ignore[attr-defined]
      "→ un état d'actualité mutable finirait par être mis en cache, donc figé")
check("`su` distingue ce qu'on sait de ce qu'on ignore", av.su and ap.su
      and not axe(source_date=None, ancre=ANCRE_FDA).su)


print("\n3. `indeterminable` n'est pas `courante`, et ses deux causes sont NOMMÉES (#44)")
sans_date = axe(source_date=None, ancre=ANCRE_FDA)
check("entry sans `source_date` → indeterminable", sans_date.etat == "indeterminable",
      f"→ {sans_date.etat}")
check("… et la cause est nommée", "source_date" in sans_date.motif, f"→ {sans_date.motif}")
check("le motif interdit de la lire comme fraîche",
      "n'est pas courante" in sans_date.motif, f"→ {sans_date.motif}")
check("aucun écart n'est fabriqué depuis une date inconnue",
      sans_date.jours_avant_evenement is None, f"→ {sans_date.jours_avant_evenement}")

deux_causes = axe(source_date=None, ancre=ANCRE_PANNE)
check("les deux causes réunies restent indeterminable", deux_causes.etat == "indeterminable")
check("… et AUCUNE des deux n'est tue",
      "injoignable" in deux_causes.motif and "source_date" in deux_causes.motif,
      f"→ {deux_causes.motif} : un motif qui n'en nomme qu'une laisse corriger la mauvaise")


print("\n4. PROPAGATION — le flux injoignable rend indeterminable, même sur un fait bien daté")
panne = axe(source_date=date(2026, 2, 25), ancre=ANCRE_PANNE)
check("fait parfaitement daté + flux HS → indeterminable", panne.etat == "indeterminable",
      f"→ {panne.etat} : une panne réseau lue « rien n'a changé » est le défaut de #49")
check("le motif de la panne est reporté", "503" in panne.motif, f"→ {panne.motif}")
check("et il n'est surtout pas classé `perimee` non plus", panne.etat != "perimee",
      "→ on ne sait pas, ce n'est ni frais ni périmé")
check("aucun seuil n'est inventé en l'absence d'ancre", panne.seuil is None, f"→ {panne.seuil}")


print("\n5. `none` ≠ `unavailable` — l'émetteur sans 8-K est un état CONNU (#25)")
aucun = axe(source_date=date(2020, 1, 1), ancre=ANCRE_AUCUNE)
check("aucun événement publié → courante", aucun.etat == "courante", f"→ {aucun.etat}")
check("… et c'est DIT, pas supposé", "aucun 8-K/6-K" in aucun.motif, f"→ {aucun.motif}")
check("la panne et l'absence d'événement ne rendent PAS le même état",
      aucun.etat != panne.etat,
      "→ les confondre produit la phrase la plus rassurante pour la pire des raisons")
check("un fait très ancien reste courant si rien ne l'a périmé", aucun.etat == "courante",
      "→ la vieillesse n'est pas la péremption : c'est l'ÉVÉNEMENT qui périme, pas l'horloge")


print("\n6. le seuil est la date du FAIT, et la frontière est inclusive (#42/#49)")
pile = axe(source_date=date(2026, 8, 27), ancre=ANCRE_ACCORD)
check("un fait daté du jour de l'événement est `courante`", pile.etat == "courante",
      f"→ {pile.etat} : il a pu en tenir compte")
check("… et son écart est nul", pile.jours_avant_evenement == 0, f"→ {pile.jours_avant_evenement}")
veille = axe(source_date=date(2026, 8, 26), ancre=ANCRE_ACCORD)
check("la veille est `perimee`", veille.etat == "perimee", f"→ {veille.etat}")
check("le seuil retenu est le reportDate (27/08), pas le filingDate (01/09)",
      veille.seuil == date(2026, 8, 27), f"→ {veille.seuil}")
# Discriminant : entre les deux dates, un fait daté du 29/08 serait `perimee` si le seuil était le
# dépôt, et `courante` avec le bon seuil. C'est le seul intervalle où les deux règles divergent.
entre = axe(source_date=date(2026, 8, 29), ancre=ANCRE_ACCORD)
check("un fait daté ENTRE l'événement et son dépôt est courant",
      entre.etat == "courante",
      f"→ {entre.etat} : trier sur le dépôt périmerait un fait postérieur à l'événement")


print("\n7. DÉTENTEUR UNIQUE (#46) — `staleness` traduit l'axe, il ne le ré-implémente pas")
_src_st = inspect.getsource(_st)
_corps_st = _src_st.split('"""', 2)[-1]      # docstring retirée : elle DÉCRIT la règle, sans l'être
check("staleness importe l'axe", "from app.knowledge.actualite import" in _src_st)
check("staleness appelle `etat_actualite`", "etat_actualite(" in _corps_st)
check("staleness ne compare plus lui-même une date à un seuil",
      "< seuil" not in _corps_st and "sd < " not in _corps_st,
      "→ une règle recopiée re-diverge au premier correctif (`feedback_correctif_regle_jumeaux`)")
check("staleness ne recalcule pas non plus l'écart en jours",
      ").days" not in _corps_st,
      "→ la soustraction est LUE sur l'axe ; deux sites = deux sites à corriger")
_src_ac = inspect.getsource(sys.modules["app.knowledge.actualite"])
# ⚠️ La docstring du module est RETIRÉE avant tout grep : elle énonce les interdits (« aucun
# `superseded_by` », « il ne lit pas `FIELD_PROFILES` »), donc la laisser ferait lire chaque
# prohibition comme sa propre violation. Même piège qu'au §8 de `check_monitoring_v2`, et il s'est
# déclenché ici à la première exécution — 4 FAIL sur du code parfaitement conforme.
_corps_ac = _src_ac.split('"""', 2)[-1]
check("la comparaison au seuil est bien DANS l'axe", "source_date < seuil" in _corps_ac)


print("\n8. JAMAIS PERSISTÉ — vérifié sur le source, pas sur l'intention")
for _verbe in ("UPDATE ", "INSERT ", "DELETE ", "execute(", "fetch("):
    check(f"aucun `{_verbe.strip()}` dans actualite.py", _verbe not in _corps_ac,
          "→ l'axe se recalcule à la lecture ; l'écrire reproduirait la cause n°2 du diagnostic")
# `conn` en mot ENTIER : le chercher en sous-chaîne le trouve dans « inconnue » — un grep trop
# large rougit sur du texte juste, et on finit par le desserrer au lieu de le préciser.
check("aucune connexion (`conn`) dans actualite.py", re.search(r"\bconn\b", _corps_ac) is None,
      "→ l'axe se recalcule à la lecture ; l'écrire reproduirait la cause n°2 du diagnostic")
check("le module n'importe aucune couche de base", "asyncpg" not in _corps_ac
      and "get_db_session" not in _corps_ac)
check("et ses fonctions sont synchrones (donc sans IO possible)",
      not inspect.iscoroutinefunction(etat_actualite),
      "→ une fonction `async` ici ouvrirait la porte à une lecture, puis à une écriture")


# ── §9 — F15 : la partition du rapport ───────────────────────────────────────
class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    async def fetch(self, *_a, **_k):
        return self._rows

    async def fetchrow(self, *_a, **_k):
        return None

    async def fetchval(self, *_a, **_k):
        return None


def _row(i, d, questions=()):
    """Une ligne telle que `_entries_actives` la rend depuis la 036.

    ⚠️ La clef était `covers` — une LISTE DE CHAMPS portée par l'entry — jusqu'au 2026-09-10. Elle
    est devenue `questions_couvertes`, une liste de couples `framework/question` obtenue par
    jointure sur `question_coverage` : ce qu'une entry couvre est une propriété de la RELATION, pas
    de la ligne (#57). Le défaut par défaut est la liste VIDE, et c'est l'état réel du corpus tant
    que le dispatch du lot 2c n'écrit rien — une fixture qui pré-remplirait les liens partout
    serait plus favorable que la production, donc aveugle (`feedback_fixture_copiee_du_reel`).
    """
    return {"id": i, "title": f"e{i}", "content": "x", "questions_couvertes": list(questions),
            "source_type": "edgar_official", "source_url": "https://sec.gov/x",
            "source_date": d, "fiscal_period": "FY2025", "reliability_tier": "A",
            "entry_type": "fact_qualitative", "requires_human_review": False}


ROWS = [_row(1, date(2026, 2, 25)), _row(2, date(2026, 8, 26)), _row(999, None)]

# Le MÊME corpus, mais avec des liens de couverture — le seul écart entre les deux jeux est la
# présence des liens, donc c'est bien eux que §9bis mesure et rien d'autre.
ROWS_LIEES = [_row(1, date(2026, 2, 25), ["mo_scale/qf_1"]),
              _row(2, date(2026, 8, 26), ["mo_scale/qf_1", "mo_moat/qf_3"]),
              _row(999, None, ["mo_moat/qf_9"])]


def _balayage(lookup, rows=None):
    """Rapport de péremption sur fixture — une exception devient un FAIL nommé, comme pour `axe`.

    Le balayage traverse l'axe : un axe qui lève tuerait §9 avant son bilan, donc au milieu du
    seul endroit qui prouve que F15 est fermé. Le rapport de repli a des clefs présentes mais
    volontairement fausses (`entries_actives=-1`) : aucun assert ne peut s'y satisfaire.
    """
    global fail

    async def _run():
        async def _fake_anchor(_conn, _tid):
            return lookup
        orig = _st.material_anchor_for_ticker
        _st.material_anchor_for_ticker = _fake_anchor
        try:
            return await _st.balayage_peremption(_FakeConn(rows if rows is not None else ROWS),
                                                 "RVMD")
        finally:
            _st.material_anchor_for_ticker = orig

    try:
        return asyncio.run(_run())
    except Exception as e:  # noqa: BLE001 — le filet, pas un masque
        fail += 1
        print(f"  FAIL le balayage a LEVÉ ({type(e).__name__}: {e}) — statut={lookup.status}")
        # `couverture_connue=None` et non `False` : §9bis asserte le booléen dans LES DEUX SENS,
        # donc un repli à `False` satisferait la moitié des asserts sans qu'aucun balayage n'ait
        # tourné. `None` n'est ni l'un ni l'autre — le repli ne peut rendre aucun assert vert.
        return {"statut": "(exception)", "entries_actives": -1, "suspectes": [],
                "posterieures": [], "non_datees": [], "avertissement": "",
                "questions_touchees": ["(exception)"], "couverture_connue": None}


print("\n9. F15 — une entry tombe dans EXACTEMENT une classe, sur les trois branches")

# Le défaut TEL QU'IL ÉTAIT : deux prédicats indépendants, chacun juste, appliqués séparément.
# Le reproduire ici prouve qu'il y avait quelque chose à corriger — montrer le seul état correct
# n'établirait pas que la partition pouvait être fausse (#37, transposé).
_posterieures_ancien = [r["id"] for r in ROWS]                                   # « tout, faute
_non_datees_ancien = [r["id"] for r in ROWS if r["source_date"] is None]          # d'événement »
check("le défaut F15 est bien reproduit par l'ancienne partition",
      len(_posterieures_ancien) + len(_non_datees_ancien) > len(ROWS)
      and set(_posterieures_ancien) & set(_non_datees_ancien) == {999},
      f"→ {_posterieures_ancien} / {_non_datees_ancien} : sans ce doublon, §9 est non discriminant")

for _nom, _lookup, _attendu in (
    ("found", ANCRE_ACCORD, {"suspectes": {1, 2}, "posterieures": set(), "non_datees": {999}}),
    ("none", ANCRE_AUCUNE, {"suspectes": set(), "posterieures": {1, 2}, "non_datees": {999}}),
):
    rap = _balayage(_lookup)
    classes = {k: {e["id"] for e in rap[k]} for k in ("suspectes", "posterieures", "non_datees")}
    total = sum(len(v) for v in classes.values())
    check(f"branche `{_nom}` : les trois classes totalisent exactement les entries actives",
          total == rap["entries_actives"] == len(ROWS),
          f"→ {total} vs {rap['entries_actives']} — {classes}")
    check(f"branche `{_nom}` : aucune entry dans deux classes",
          not (classes["suspectes"] & classes["posterieures"])
          and not (classes["posterieures"] & classes["non_datees"])
          and not (classes["suspectes"] & classes["non_datees"]), f"→ {classes}")
    check(f"branche `{_nom}` : l'entry non datée n'est PAS rangée avec les fraîches",
          999 not in classes["posterieures"],
          f"→ {classes['posterieures']} : « posterieure » se lit « elle a pu en tenir compte »")
    check(f"branche `{_nom}` : la partition est celle attendue", classes == _attendu,
          f"→ {classes} vs {_attendu}")

rap_ko = _balayage(ANCRE_PANNE)
check("branche `unavailable` : aucune classe n'est peuplée, et le rapport le DIT",
      rap_ko["suspectes"] == [] and rap_ko["posterieures"] == [] and rap_ko["non_datees"] == []
      and "PAS que rien n'est périmé" in rap_ko["avertissement"],
      "→ échouer fermé est correct ; échouer fermé SANS le dire ne l'est pas")
check("… et les entries actives restent comptées (la base, elle, a répondu)",
      rap_ko["entries_actives"] == len(ROWS), f"→ {rap_ko['entries_actives']}")

rap = _balayage(ANCRE_ACCORD)
check("le rapport porte l'axe à côté de son propre vocabulaire",
      all(e["actualite"] == "perimee" for e in rap["suspectes"])
      and all(e["actualite"] == "indeterminable" for e in rap["non_datees"]),
      f"→ {[(e['id'], e['actualite']) for e in rap['suspectes'] + rap['non_datees']]}")
check("et le motif de l'axe voyage avec",
      all(e["motif_actualite"] for e in rap["suspectes"]))


print("\n9bis. « aucune question touchée » n'est pas « on ne sait pas » (migration 036)")
# Ex-`champs_touches`, agrégé depuis `covers`. Le rapport en tient désormais DEUX clefs, parce
# qu'il y a trois états (#44/#54) : des questions touchées · aucune · **on ne sait pas encore**.
# Une seule clef les écraserait en une liste vide, qui se lit « ce périmé ne fonde rien » — la
# phrase rassurante produite par la pire des raisons (#49), et elle est FAUSSE aujourd'hui :
# `question_coverage` est vide faute d'émetteur, pas faute d'impact.
rap_sans = _balayage(ANCRE_ACCORD)
check("corpus SANS lien : `couverture_connue` est FALSE",
      rap_sans["couverture_connue"] is False,
      f"→ {rap_sans['couverture_connue']} : la table de liens est vide, ce n'est pas une absence d'impact")
check("corpus SANS lien : `questions_touchees` est vide, et c'est la clef qui l'accompagne qui le qualifie",
      rap_sans["questions_touchees"] == [], f"→ {rap_sans['questions_touchees']}")

rap_liee = _balayage(ANCRE_ACCORD, ROWS_LIEES)
check("corpus AVEC liens : `couverture_connue` est TRUE",
      rap_liee["couverture_connue"] is True, f"→ {rap_liee['couverture_connue']}")
check("… et `questions_touchees` n'agrège que les entries SUSPECTES, pas tout le corpus",
      rap_liee["questions_touchees"] == ["mo_moat/qf_3", "mo_scale/qf_1"],
      f"→ {rap_liee['questions_touchees']} : `mo_moat/qf_9` porte l'entry NON DATÉE (#999), qui est "
      "`indeterminable` et non `perimee` — l'inclure ferait chercher une source plus récente là où "
      "il faut une source datable (#53)")
check("… le couple est bien `framework/question`, jamais un chemin MVDD",
      all("/" in q and "." not in q for q in rap_liee["questions_touchees"]),
      f"→ {rap_liee['questions_touchees']} : un `dimension.champ` ici serait #57 réintroduit")
check("les deux jeux ne diffèrent QUE par les liens (sinon §9bis ne mesure pas les liens)",
      [(r["id"], r["source_date"]) for r in ROWS] == [(r["id"], r["source_date"]) for r in ROWS_LIEES]
      and {e["id"] for e in rap_sans["suspectes"]} == {e["id"] for e in rap_liee["suspectes"]},
      "→ une fixture qui déplace deux variables ne dit pas laquelle discrimine")


print("\n10. la capacité 4 n'est PAS faite ici — l'axe ignore le profil du champ")
check("l'axe ne lit pas `actualite_bloquante`", "actualite_bloquante" not in _corps_ac,
      "→ confronter l'état au profil est le travail de la PORTE (capacité 4)")
check("l'axe ne lit pas `FIELD_PROFILES`", "FIELD_PROFILES" not in _corps_ac,
      "→ l'anticiper perturberait la ligne de base que le test central de la capacité 4 mesure")
check("l'axe ne prononce aucun verdict de couverture",
      "couvert" not in _corps_ac and "readiness" not in _corps_ac,
      "→ hors périmètre de la capacité 3")
check("l'axe n'écrit jamais de `superseded_by`", "superseded_by" not in _corps_ac,
      "→ décider qu'un fait est remplacé est un jugement humain (#29/#49)")
# La docstring, elle, DOIT porter ces interdits : c'est là que vit le « pourquoi », et un garde-fou
# dont la raison n'est écrite nulle part se fait desserrer à la première gêne.
_doc_ac = _src_ac.split('"""')[1]
check("… et la docstring, elle, DIT pourquoi (le grep ci-dessus la retire à dessein)",
      "superseded_by" in _doc_ac and "capacité 4" in _doc_ac,
      "→ un interdit sans motif écrit se desserre à la première gêne")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
