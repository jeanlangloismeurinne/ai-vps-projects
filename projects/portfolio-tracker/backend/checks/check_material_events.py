"""Vérification de la SECONDE horloge : événements matériels (8-K/6-K) + balayage de péremption.

Sans appel réseau ni modèle — les charges utiles EDGAR sont des copies conformes de la réponse
réelle de `data.sec.gov/submissions/CIK0001628171.json` pour RVMD au 2026-09-05 (⚠️ leçon §20 :
une fixture plus favorable que la production est un check aveugle qui passe au vert).

Ce qui est mis à l'épreuve :
  • l'ordre « dernier événement » quand date de DÉPÔT et date d'ÉVÉNEMENT se croisent (RVMD :
    événement du 27/08 déposé le 01/09, APRÈS un événement du 26/08 déposé le 26/08) ;
  • les TROIS états `found` / `none` / `unavailable`, jamais deux confondus (#25/#44) ;
  • le fait qu'un `materiel=None` (flux non consulté) produise le message PRUDENT, pas le
    rassurant — c'est le mode de panne de F12 transposé à son propre correctif ;
  • le balayage : un rapport, jamais une écriture ; et zéro suspecte sur panne s'ANNONCE.
"""
import asyncio
import inspect
import sys
from datetime import date

from app.agents.v2.worker import _build_user_message, _formuler_ancre_materielle
from app.contracts import OutputSchema, WorkerRequest
from app.knowledge import staleness as _st
from app.knowledge.material_events import (
    ITEM_LABELS,
    MATERIAL_FORMS,
    MaterialEvent,
    MaterialEventLookup,
    parse_material_events,
)

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


# Copie conforme de la réponse EDGAR réelle (RVMD, CIK 1628171, relevée le 2026-09-05).
# Les colonnes sont parallèles, comme chez EDGAR — et volontairement mélangées de formes non
# matérielles (4, 144, 10-Q, SCHEDULE 13G) : un filtre qui les laisserait passer daterait l'ancre
# sur un Form 4 d'initié, qui n'est pas un événement d'entreprise.
PAYLOAD = {
    "filings": {
        "recent": {
            "form": ["4", "8-K", "144", "8-K", "4", "10-Q", "8-K", "SCHEDULE 13G", "8-K", "10-K"],
            "filingDate": ["2026-09-02", "2026-09-01", "2026-08-31", "2026-08-26", "2026-08-25",
                           "2026-08-05", "2026-08-05", "2026-08-14", "2026-06-22", "2026-02-25"],
            "reportDate": ["", "2026-08-27", "", "2026-08-26", "", "2026-06-30", "2026-08-05",
                           "", "2026-06-18", "2025-12-31"],
            "items": ["", "1.01,2.03", "", "8.01", "", "", "2.02,9.01", "", "5.02,5.07", ""],
            "accessionNumber": ["0001193125-26-380277", "0001193125-26-377362",
                                "0001968582-26-000898", "0001193125-26-366931",
                                "0001610717-26-000388", "0001193125-26-335104",
                                "0001193125-26-335039", "0001104659-26-097049",
                                "0001193125-26-000001", "0001193125-26-100000"],
        }
    }
}

print("\n1. parse_material_events — ne retient que les formes matérielles")
evts = parse_material_events(PAYLOAD, 1628171)
formes = {e.form for e in evts}
check("aucune forme non matérielle retenue", formes <= set(MATERIAL_FORMS),
      f"→ formes retenues : {sorted(formes)}")
check("les 4 dépôts 8-K de la charge sont retenus", len(evts) == 4, f"→ {len(evts)} retenus")
check("un 10-K/10-Q n'est jamais un événement matériel",
      not any(e.form.startswith("10-") for e in evts))
check("un Form 4 (initié) n'est jamais un événement matériel",
      not any(e.form == "4" for e in evts))

print("\n2. l'ordre se fait sur la date d'ÉVÉNEMENT, pas de dépôt (elles se croisent)")
# Piège réel : EDGAR classe par filingDate → le 8-K déposé le 01/09 arrive en tête, mais son
# événement date du 27/08 ; celui déposé le 26/08 porte un événement du 26/08. Un tri par dépôt
# donnerait le bon gagnant ICI par accident — c'est l'écart d'un jour du SEUIL qui compte.
check("le dernier événement est celui du 2026-08-27", evts[0].event_date == date(2026, 8, 27),
      f"→ {evts[0].event_date}")
check("sa date de dépôt est distincte et conservée", evts[0].filing_date == date(2026, 9, 1),
      f"→ {evts[0].filing_date}")
check("le tri est strictement décroissant par date d'événement",
      all(evts[i].event_date >= evts[i + 1].event_date for i in range(len(evts) - 1)),
      f"→ {[e.event_date.isoformat() for e in evts]}")
check("un dépôt sans reportDate retombe sur sa date de dépôt",
      all(e.event_date is not None for e in evts))

print("\n2bis. fixture qui DISCRIMINE réellement les deux tris")
# ⚠️ Écrite après un test négatif RATÉ : trier par `filingDate` au lieu de `reportDate` ne faisait
# virer AUCUNE assertion du §2 au rouge. Sur le flux RVMD réel les deux tris donnent le même
# gagnant — le §2 mesurait donc une propriété que le défaut ne pouvait pas violer. C'est le §20 du
# CHANTIER (« une fixture plus favorable que la production est un check aveugle »), rencontré dans
# sa variante « fixture non discriminante ».
#
# Cette charge-ci est CONSTRUITE, et il faut le dire : le croisement n'existe pas tel quel chez
# RVMD. Ses deux lignes sont en revanche des formes réelles — le 8-K/A du 2023-12-26 amendant un
# événement du 2023-11-08 est un dépôt RVMD authentique (accession 0001193125-23-302252). Un
# amendement déposé des semaines après le fait qu'il corrige est le cas structurel où les deux
# ordres divergent, et il tire le seuil de péremption VERS LE PASSÉ — donc vers moins de suspectes.
PAYLOAD_CROISE = {
    "filings": {
        "recent": {
            "form": ["8-K/A", "8-K"],
            "filingDate": ["2023-12-26", "2023-12-20"],
            "reportDate": ["2023-11-08", "2023-12-20"],
            "items": ["9.01", "8.01"],
            "accessionNumber": ["0001193125-23-302252", "0001193125-23-999999"],
        }
    }
}
croise = parse_material_events(PAYLOAD_CROISE, 1628171)
check("le dernier ÉVÉNEMENT gagne, pas le dernier DÉPÔT",
      croise[0].event_date == date(2023, 12, 20), f"→ {croise[0].event_date} (tri par dépôt ?)")
check("l'amendement tardif ne devient pas l'ancre",
      croise[0].form == "8-K", f"→ {croise[0].form}")
check("un tri par dépôt tirerait le seuil de 42 jours vers le passé",
      (croise[0].event_date - croise[1].event_date).days == 42,
      "→ la fixture a cessé de discriminer les deux tris")

print("\n3. items — libellés, et un item inconnu n'est JAMAIS silencieux")
check("les items sont éclatés, pas gardés en chaîne", evts[0].items == ("1.01", "2.03"),
      f"→ {evts[0].items}")
lib = evts[0].libelle_items()
check("le libellé nomme l'accord important", "accord important" in lib, f"→ {lib}")
check("le libellé nomme l'obligation financière", "obligation financière" in lib, f"→ {lib}")
inconnu = MaterialEvent(form="8-K", event_date=date(2026, 1, 1), filing_date=date(2026, 1, 1),
                        items=("9.99",))
check("un item hors table est rendu, marqué « non répertorié »",
      "9.99" in inconnu.libelle_items() and "non répertorié" in inconnu.libelle_items(),
      f"→ {inconnu.libelle_items()}")
check("l'item 8.01 (FDA / autre événement) est bien répertorié", "8.01" in ITEM_LABELS)
check("un item formel (9.01) ne compte pas comme motif de fond",
      "9.01" not in evts[2].items_substantiels and "9.01" in evts[2].items,
      f"→ {evts[2].items} / {evts[2].items_substantiels}")

print("\n4. aucun dépôt matériel → `none`, jamais une liste vide muette")
vide = parse_material_events({"filings": {"recent": {"form": ["4"], "filingDate": ["2026-01-01"],
                                                     "reportDate": [""], "items": [""],
                                                     "accessionNumber": ["x"]}}}, 1)
check("un émetteur sans 8-K rend une liste vide", vide == [])
check("`none` compte comme SU", MaterialEventLookup(status="none").connu)
check("`unavailable` ne compte PAS comme su",
      not MaterialEventLookup(status="unavailable", raison="EDGAR 503").connu)

print("\n5. le message au modèle — les trois états sont formulés DIFFÉREMMENT")
ancre = {"source_date": date(2026, 6, 30), "fiscal_period": "AU 2026-06-30",
         "source_url": "https://www.sec.gov/Archives/edgar/data/1628171/x-index.htm"}
found = MaterialEventLookup(status="found", event=evts[0], cik=1628171, recents=tuple(evts))
m_found = _formuler_ancre_materielle(found, ancre)
m_none = _formuler_ancre_materielle(MaterialEventLookup(status="none"), ancre)
m_unav = _formuler_ancre_materielle(
    MaterialEventLookup(status="unavailable", raison="EDGAR 503"), ancre)
check("les trois formulations sont distinctes", len({m_found, m_none, m_unav}) == 3)
check("`found` porte la date de l'événement", "2026-08-27" in m_found, f"→ {m_found}")
check("`found` porte le délai de dépôt", "2026-09-01" in m_found)
check("`found` porte l'URL du dépôt", "sec.gov" in m_found)
check("`found` déclare la POSTÉRIORITÉ à l'ancre périodique",
      "POSTÉRIEUR" in m_found and "2026-06-30" in m_found, f"→ {m_found}")
# Le cœur du correctif : un fait périmé n'est pas un fait faux. Si le message ne le dit pas, le
# modèle qui trouve une entry tier A cohérente conclut qu'elle est bonne.
check("`found` distingue périmé et faux",
      "révolu" in m_found and "SANS ÊTRE FAUX" in m_found, f"→ {m_found}")
check("`none` affirme l'absence d'événement", "AUCUN" in m_none, f"→ {m_none}")
check("`none` ne parle pas de monde révolu", "révolu" not in m_none)
check("`unavailable` INTERDIT de conclure au calme plat",
      "PAS conclure" in m_unav and "rien passé" in m_unav, f"→ {m_unav}")
check("`unavailable` porte son motif", "503" in m_unav, f"→ {m_unav}")

print("\n6. un événement ANTÉRIEUR à l'ancre ne crie pas au loup")
vieux = MaterialEventLookup(
    status="found",
    event=MaterialEvent(form="8-K", event_date=date(2026, 5, 6), filing_date=date(2026, 5, 6),
                        items=("2.02",)))
m_vieux = _formuler_ancre_materielle(vieux, ancre)
check("un événement plus ancien que l'ancre n'est pas signalé POSTÉRIEUR",
      "POSTÉRIEUR" not in m_vieux, f"→ {m_vieux}")
check("il est quand même rendu (jamais tu)", "2026-05-06" in m_vieux, f"→ {m_vieux}")

print("\n7. le défaut de `materiel` est PRUDENT, pas rassurant")
# F12 avait été causé par un message MUET. Un correctif dont le défaut est silencieux reproduirait
# le défaut à l'identique chez le premier appelant qui oublie l'argument.
req = WorkerRequest(
    requester="knowledge-curator", worker="search-worker", ticker_id="RVMD",
    query="modèle d'affaires", output_schema=OutputSchema(
        entry_type="fact_qualitative", dimension="business_model",
        field_path="business_model.description"),
    reliability_min=0.60,
)
msg_defaut = _build_user_message(req, ancre)
check("sans argument `materiel`, le message parle quand même des événements matériels",
      "Événements matériels" in msg_defaut, "→ le message est MUET sur la seconde horloge")
check("et il tombe dans la branche prudente",
      "PAS conclure" in msg_defaut, f"→ branche rassurante prise par défaut")
msg_plein = _build_user_message(req, ancre, found)
check("avec l'argument, l'événement réel est transmis", "2026-08-27" in msg_plein)
check("l'ancre périodique de F12 survit à l'ajout", "2026-06-30" in msg_plein)
check("la date du jour de F12 survit à l'ajout", date.today().isoformat() in msg_plein)
_sig = inspect.signature(_build_user_message).parameters
check("`materiel` est bien un paramètre de _build_user_message", "materiel" in _sig,
      f"→ {list(_sig)}")

print("\n8. run_search_worker consulte réellement le flux (sinon tout ce qui précède est décoratif)")
_src = inspect.getsource(sys.modules["app.agents.v2.worker"].run_search_worker)
check("l'ancre matérielle est lue dans run_search_worker",
      "material_anchor_for_ticker" in _src, "→ le flux n'est jamais consulté en prod")
check("et elle est passée au message", "_build_user_message(req, ancre, materiel)" in _src,
      "→ lue puis jetée : un affichage, pas un garde-fou (§22)")


# ── balayage de péremption ───────────────────────────────────────────────────
class _FakeConn:
    """Connexion bouchonnée : rend les entries actives RVMD telles qu'en production."""

    def __init__(self, rows):
        self._rows = rows

    async def fetch(self, *_a, **_k):
        return self._rows

    async def fetchrow(self, *_a, **_k):
        return None

    async def fetchval(self, *_a, **_k):
        return None


def _row(i, d, covers, txt, tier="A"):
    return {"id": i, "title": f"e{i}", "content": txt, "covers": covers,
            "source_type": "edgar_official", "source_url": "https://sec.gov/x",
            "source_date": d, "fiscal_period": "FY2025", "reliability_tier": tier,
            "entry_type": "fact_qualitative", "requires_human_review": False}


ROWS = [
    _row(176, date(2026, 2, 25), ["business_model.description"],
         "aucun produit approuvé pour la vente commerciale"),
    _row(177, date(2026, 2, 25), ["business_model.drivers_revenus"],
         "les seules entrées de trésorerie proviennent de financements"),
    _row(182, date(2026, 8, 5), ["risques.risques_cles"],
         "la société ne peut être certaine d'obtenir une approbation"),
    _row(186, date(2026, 8, 26), ["marche.croissance_marche_historique"],
         "la FDA a approuvé RASONQUE le 2026-08-26"),
    _row(999, None, ["produits.description"], "entry sans date de source"),
]


async def _balayage(lookup):
    async def _fake_anchor(_conn, _tid):
        return lookup
    orig = _st.material_anchor_for_ticker
    _st.material_anchor_for_ticker = _fake_anchor
    try:
        return await _st.balayage_peremption(_FakeConn(ROWS), "RVMD")
    finally:
        _st.material_anchor_for_ticker = orig


print("\n9. balayage — le seuil est l'événement, et les trois classes sont peuplées")
rap = asyncio.run(_balayage(found))
ids_susp = {e["id"] for e in rap["suspectes"]}
check("statut = balayé", rap["statut"] == "balaye", f"→ {rap['statut']}")
check("le seuil est la date d'ÉVÉNEMENT (27/08), pas de dépôt (01/09)",
      rap["seuil"] == "2026-08-27", f"→ {rap['seuil']}")
check("les 4 entries antérieures sont suspectes", ids_susp == {176, 177, 182, 186},
      f"→ {sorted(ids_susp)}")
# L'entry 186 EST la FDA — et elle reste suspecte, car un second événement lui est postérieur.
# C'est le point qui distingue un balayage d'un « on a déjà traité la FDA ».
check("l'entry qui rapporte la FDA reste suspecte (un événement lui est postérieur)",
      186 in ids_susp)
check("l'entry non datée n'est PAS rangée avec les fraîches",
      {e["id"] for e in rap["non_datees"]} == {999},
      f"→ {[e['id'] for e in rap['non_datees']]}")
check("elle n'est pas non plus comptée suspecte", 999 not in ids_susp)
check("les trois classes couvrent exactement les entries actives",
      len(rap["suspectes"]) + len(rap["posterieures"]) + len(rap["non_datees"])
      == rap["entries_actives"] == len(ROWS),
      f"→ {len(rap['suspectes'])}+{len(rap['posterieures'])}+{len(rap['non_datees'])}"
      f" vs {rap['entries_actives']}")
check("la plus ancienne vient en tête",
      rap["suspectes"][0]["jours_avant_evenement"] == 183,
      f"→ {rap['suspectes'][0]['jours_avant_evenement']}")
check("les champs MVDD touchés sont agrégés",
      "business_model.description" in rap["champs_touches"]
      and "risques.risques_cles" in rap["champs_touches"], f"→ {rap['champs_touches']}")
check("le motif nomme l'événement et ses items",
      "2026-08-27" in rap["motif"] and "obligation financière" in rap["motif"], f"→ {rap['motif']}")
check("le rapport dit qu'il n'écrit rien", rap["ecrit_en_base"] is False)
check("le motif dit « re-vérifier », jamais « supprimer »",
      "re-vérifier" in rap["motif"] and "pas à supprimer" in rap["motif"])

print("\n10. balayage — une panne rend ZÉRO suspecte, et le DIT (leçon §13)")
rap_ko = asyncio.run(_balayage(MaterialEventLookup(status="unavailable", raison="EDGAR 503")))
check("statut = indéterminable, pas « balayé »", rap_ko["statut"] == "indeterminable",
      f"→ {rap_ko['statut']}")
check("zéro suspecte", rap_ko["suspectes"] == [])
check("mais l'avertissement interdit de le lire comme « rien à signaler »",
      "PAS que rien n'est périmé" in rap_ko["avertissement"], f"→ {rap_ko['avertissement']}")
check("le motif de la panne est rapporté", "503" in (rap_ko["raison"] or ""))
check("les entries actives restent comptées (la base, elle, a répondu)",
      rap_ko["entries_actives"] == len(ROWS))

print("\n11. balayage — émetteur sans aucun événement matériel")
rap_none = asyncio.run(_balayage(MaterialEventLookup(status="none")))
check("statut distinct de la panne", rap_none["statut"] == "aucun_evenement",
      f"→ {rap_none['statut']}")
check("aucune suspecte, et c'est un fait, pas une panne", rap_none["suspectes"] == []
      and "aucun 8-K" in rap_none["avertissement"], f"→ {rap_none['avertissement']}")

print("\n12. le module de balayage n'écrit RIEN — vérifié sur le source, pas sur l'intention")
_src_st = inspect.getsource(_st)
for _verbe in ("UPDATE ", "INSERT ", "DELETE ", "execute("):
    check(f"aucun `{_verbe.strip()}` dans staleness.py", _verbe not in _src_st,
          f"→ le balayage doit rester un rapport (#29)")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
