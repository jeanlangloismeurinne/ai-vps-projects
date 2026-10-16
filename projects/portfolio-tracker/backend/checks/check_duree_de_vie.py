"""Check — la fraîcheur d'une réponse jugée dans la DURÉE DE VIE de ce que chaque pièce fonde
(règle de fraîcheur, arbitrages du 2026-10-16 — `roadmap/V3/06-regle-fraicheur.md`).

Dates copiées du dossier RVMD réel : 10-K clos le 31/12/2025, 10-Q clos le 30/06/2026 (publié le
05/08), approbation FDA du 26/08 (8.01), proxy de l'assemblée 2026 (avril). Ce que chaque section
éprouve :

  • §1 LE CAS QUI A OUVERT LA QUESTION (A4) — un historique cité depuis le rapport annuel ET complété
       du dernier trimestre est À JOUR ; sans la pièce du trimestre, il n'est « pas complété ».
       Témoin : sous l'ordre 0 (`durees=None`), la même réponse est PÉRIMÉE.
  • §2 UN CHIFFRE COURANT se juge pièce par pièce, contre la clôture de SA cadence (trimestrielle ou
       annuelle) — l'anti-blanchiment tient : une pièce récente à côté n'en rajeunit pas une vieille.
  • §3 UNE DESCRIPTION ANNUELLE couvre le dernier exercice publié ; celle de l'année d'avant cède.
  • §4 UN JUGEMENT n'a pas de durée propre : seul le fait qui rouvre la question le touche — et un
       fait LU (#103/#117) ne le touche plus. Un historique se COMPLÈTE face à un fait (acquisition).
  • §5 LA PRUDENCE AUX BORDS — pièce non rattachée = chiffre courant trimestriel ; exercice inconnu =
       dernière clôture ; aucune clôture = abstention (l'ordre 0 s'applique) ; flux injoignable ou
       pièce sans date = indéterminable, jamais « à jour ».
  • §6 LA PART « RÉSULTATS » d'un communiqué ne rouvre pas une question au titre d'un fait : elle
       passe par les cadences (arbitrage 3).
  • §7 LE POINT DE LECTURE EST BRANCHÉ (AST) — `parcours` passe à `servir_answer` le contexte produit
       par `contexte_durees`, et rien d'autre ; `contexte_durees` rend `None` quand l'interrupteur est
       coupé ; le référentiel réel l'a ACTIF.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte.
"""
from __future__ import annotations

import ast
import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, strip_code  # noqa: E402

from app.agents.v2.frameworks import load_frameworks, servir_answer  # noqa: E402
from app.contracts.framework_answer_schema import FrameworkAnswer  # noqa: E402
from app.knowledge.duree_de_vie import (  # noqa: E402
    Clotures, ContexteDurees, DureeIngredient, fait_qui_rouvre, juger_fondation)
from app.knowledge.evenements import RESULTATS, retirer_faits_lus  # noqa: E402
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup  # noqa: E402

b = Bilan()
APP = Path(__file__).resolve().parent.parent / "app"

K10 = date(2025, 12, 31)      # 10-K RVMD
Q2 = date(2026, 6, 30)        # 10-Q RVMD (publié le 05/08)
PROXY = date(2026, 4, 24)     # proxy de l'assemblée 2026
CLOT = Clotures(derniere=Q2, exercice=K10)

H_T = lambda i: DureeIngredient(i, "historique", "trimestrielle")      # noqa: E731
H_A = lambda i: DureeIngredient(i, "historique", "annuelle")           # noqa: E731
CC_T = lambda i: DureeIngredient(i, "chiffre_courant", "trimestrielle")  # noqa: E731
CC_A = lambda i: DureeIngredient(i, "chiffre_courant", "annuelle")     # noqa: E731
DA = lambda i: DureeIngredient(i, "description_annuelle")              # noqa: E731
J = lambda i: DureeIngredient(i, "jugement")                           # noqa: E731


def ev(d, items, acc, types=None, effet=None):
    return MaterialEvent(form="8-K", event_date=d, filing_date=d, items=tuple(items), accession=acc,
                         types=tuple(types or ()), date_d_effet=effet, periode_publiee=effet)


FDA = ev(date(2026, 8, 26), ["8.01"], "acc-fda", ["reglementaire_favorable"])
RES = ev(date(2026, 8, 5), ["2.02", "9.01"], "acc-res", [RESULTATS], effet=Q2)
ACQ = ev(date(2026, 9, 2), ["8.01"], "acc-acq", ["perimetre"])


def lk(*evts):
    if not evts:
        return MaterialEventLookup(status="none", cik=1, recents=())
    evs = tuple(sorted(evts, key=lambda e: (e.seuil, e.event_date), reverse=True))
    return MaterialEventLookup(status="found", event=evs[0], cik=1, recents=evs)


def juge(cites, dates, ings, clot=CLOT, horloge=None, indispo=None):
    try:
        j = juger_fondation(cites, dates=dates, ingredients_des_pieces=ings, clotures=clot,
                            fait=fait_qui_rouvre(horloge or lk()), horloge_indisponible=indispo)
        return j
    except Exception as e:  # noqa: BLE001 — un refus inattendu est un FAIL nommé, pas la mort
        return f"LÈVE {e!r}"


def etat(j):
    return getattr(j, "etat", j)


print("§1 le cas A4 : un historique cité du rapport annuel et COMPLÉTÉ du trimestre")
ma3 = {1: [H_T("operations_sur_le_capital")], 2: [H_T("operations_sur_le_capital")]}
j1 = juge([1, 2], {1: K10, 2: Q2}, ma3)
b.check(etat(j1) == "courante", f"rapport annuel + 10-Q du 30/06 sur le même historique : À JOUR → {etat(j1)}")
j1b = juge([1], {1: K10}, {1: [H_T("operations_sur_le_capital")]})
b.check(etat(j1b) == "perimee" and "pas complété" in j1b.motif,
        f"le seul rapport annuel : « pas complété » de la clôture du 30/06 → {getattr(j1b, 'motif', j1b)}")
j1c = juge([1], {1: K10}, {1: [H_A("rendement_des_usages")]})
b.check(etat(j1c) == "courante",
        f"un historique ANNUEL au dernier exercice reste à jour après un trimestre → {etat(j1c)}")

print("§2 un chiffre courant, pièce par pièce, contre la clôture de sa cadence")
j2 = juge([1, 2], {1: K10, 2: Q2}, {1: [CC_T("tresorerie")], 2: [CC_T("tresorerie")]})
b.check(etat(j2) == "perimee" and "#1" in j2.motif,
        f"anti-blanchiment : une pièce au 30/06 ne rajeunit pas celle au 31/12 → {getattr(j2, 'motif', j2)}")
b.check(etat(juge([2], {2: Q2}, {2: [CC_T("tresorerie")]})) == "courante",
        "un chiffre courant au 30/06 est à jour")
b.check(etat(juge([1], {1: K10}, {1: [CC_A("resultat_net")]})) == "courante",
        "un chiffre courant ANNUEL au dernier exercice est à jour après un trimestre")
b.check(etat(juge([1], {1: date(2024, 12, 31)}, {1: [CC_A("resultat_net")]})) == "perimee",
        "un chiffre courant annuel d'un exercice dépassé est périmé")

b.check(etat(juge([1], {1: date(2025, 12, 31)}, {1: [H_A("rentabilite_des_acteurs")]},
                clot=Clotures(date(2026, 7, 26), date(2026, 1, 25)))) == "courante",
        "tolérance annuelle : les pairs clos au 31/12/2025 valent pour l'exercice NVDA clos le 25/01/2026")
b.check(etat(juge([1], {1: date(2024, 12, 31)}, {1: [H_A("rentabilite_des_acteurs")]},
                clot=Clotures(date(2026, 7, 26), date(2026, 1, 25)))) == "perimee",
        "…mais l'exercice d'AVANT (≈ 13 mois) reste périmé")
print("§3 une description annuelle couvre le dernier exercice")
b.check(etat(juge([3], {3: PROXY}, {3: [DA("independance_du_conseil")]})) == "courante",
        "le proxy 2026 (exercice 2025) est à jour")
b.check(etat(juge([3], {3: date(2025, 4, 25)}, {3: [DA("independance_du_conseil")]})) == "perimee",
        "le proxy 2025 cède au document de l'exercice suivant")
b.check(etat(juge([3], {3: PROXY}, {3: [DA("independance_du_conseil")]}, clot=Clotures(Q2, K10))) == "courante"
        and etat(juge([3], {3: PROXY}, {3: [DA("x")]}, horloge=lk(RES))) == "courante",
        "les résultats du trimestre ne touchent pas une description annuelle (arbitrage 3)")

print("§4 un jugement n'a que les faits ; un fait LU ne le touche plus ; un historique se complète")
b.check(etat(juge([4], {4: date(2024, 3, 1)}, {4: [J("mecanisme")]})) == "courante",
        "un jugement sans fait qui le rouvre reste à jour, quel que soit l'âge de sa pièce")
j4 = juge([4], {4: Q2}, {4: [J("mecanisme")]}, horloge=lk(FDA))
b.check(etat(j4) == "perimee" and "reglementaire_favorable" in j4.motif,
        f"l'approbation du 26/08 rouvre le jugement fondé au 30/06 → {getattr(j4, 'motif', j4)}")
lu = retirer_faits_lus(lk(FDA), {"acc-fda": "approbation lue : premier produit commercial"})
b.check(etat(juge([4], {4: Q2}, {4: [J("mecanisme")]}, horloge=lu)) == "courante",
        "le même fait LU et chiffré par l'analyste ne le touche plus (#117)")
acq = {1: [H_A("acquisitions_realisees")], 5: [H_A("acquisitions_realisees")]}
b.check(etat(juge([1], {1: K10}, {1: [H_A("acquisitions_realisees")]}, horloge=lk(ACQ))) == "perimee",
        "une acquisition annoncée : l'historique des acquisitions n'est pas complété")
b.check(etat(juge([1, 5], {1: K10, 5: date(2026, 9, 2)}, acq, horloge=lk(ACQ))) == "courante",
        "complété d'une pièce du 02/09, il est à jour (les pièces anciennes restent valables)")

print("§5 la prudence aux bords")
b.check(etat(juge([6], {6: K10}, {})) == "perimee",
        "une pièce non rattachée est un chiffre courant TRIMESTRIEL (la durée la plus courte)")
b.check(etat(juge([1], {1: K10}, {1: [CC_A("x")]}, clot=Clotures(Q2, None))) == "perimee",
        "exercice inconnu : la dernière clôture le remplace (plus exigeante, jamais devinée)")
b.check(juge([1], {1: K10}, {1: [CC_T("x")]}, clot=Clotures(None, None)) is None,
        "aucune clôture connue : la règle s'abstient (l'ordre 0 s'applique)")
b.check(etat(juge([1], {1: Q2}, {1: [J("x")]}, indispo="EDGAR muet")) == "indeterminable",
        "flux injoignable : indéterminable, jamais « à jour » (#49)")
b.check(etat(juge([1], {1: None}, {1: [CC_T("x")]})) == "indeterminable"
        and etat(juge([1], {1: None}, {1: [H_T("x")]})) == "indeterminable",
        "pièce sans date (chiffre courant ou historique) : indéterminable")
b.check(etat(juge([1, 2], {1: K10, 2: Q2}, {1: [H_T("x"), CC_T("y")], 2: [H_T("x")]})) == "perimee",
        "une pièce qui fonde un historique ET un chiffre courant se juge sur le plus exigeant")

print("§6 la part « résultats » d'un communiqué passe par les cadences, pas par les faits")
b.check(fait_qui_rouvre(lk(RES)) is None and fait_qui_rouvre(lk(RES, FDA)) == FDA,
        "fait_qui_rouvre ignore la part « résultats » et retient le fait au seuil le plus tardif")
b.check(etat(juge([4], {4: date(2024, 3, 1)}, {4: [J("x")]}, horloge=lk(RES))) == "courante",
        "des résultats publiés ne rouvrent pas un jugement qui ne s'appuie sur aucun chiffre du trimestre")


print("§7 servir_answer et le point de lecture")


def rep(cites):
    return FrameworkAnswer(
        framework_id="management_capital", framework_version="v3.0.0", question_id="ma_3",
        ticker_id="RVMD", analyste="a", statut="repondu",
        reponse={"verbatim": "rachats et émissions au bon prix", "faits_posterieurs": []},
        fondation={"cited_entry_ids": cites, "rang_derive": "A", "nature_effective": "mesure"})


CTX = ContexteDurees(clotures=CLOT, ingredients_des_pieces={"ma_3": ma3})
ENT = {1: {"source_date": K10}, 2: {"source_date": Q2}}
try:
    neuf = servir_answer(rep([1, 2]), ancre=lk(RES), entries=ENT, durees=CTX).fondation.actualite
    ancien = servir_answer(rep([1, 2]), ancre=lk(RES), entries=ENT, durees=None).fondation.actualite
except Exception as e:  # noqa: BLE001
    neuf = ancien = f"LÈVE {e!r}"
b.check(neuf == "courante", f"servir_answer, interrupteur actif : à jour → {neuf}")
b.check(ancien == "perimee", f"témoin ordre 0 (durees=None) : la même réponse PÉRIMÉE → {ancien}")

b.check(load_frameworks().fraicheur_par_duree_de_vie is True,
        "l'interrupteur du référentiel réel est ACTIF (ordre 1)")


class _Conn:
    async def fetch(self, *_a, **_k):
        return [{"question_id": "ma_3", "ingredient_id": "operations_sur_le_capital", "entry_id": 1}]


from app.agents.v2.parcours import contexte_durees  # noqa: E402
_F = load_frameworks()
_lk = lk(RES)
_on = asyncio.run(contexte_durees(_Conn(), fichier=_F, version="v3.0.0", ancre_titre=_lk, cites={1}))
_off = asyncio.run(contexte_durees(_Conn(), fichier=_F.model_copy(update={"fraicheur_par_duree_de_vie": False}),
                                   version="v3.0.0", ancre_titre=_lk, cites={1}))
b.check(_off is None, "interrupteur coupé : aucun contexte, l'ordre 0 s'applique")
b.check(_on is not None and _on.clotures.derniere == Q2
        and [i.duree_de_vie for i in _on.ingredients_des_pieces.get("ma_3", {}).get(1, [])] == ["historique"],
        f"interrupteur actif : clôture lue sur l'horloge du titre, durée lue au référentiel → {_on}")

class _ConnVoisine:
    """La pièce #7 a été collectée pour ma_1 (historique) ; ma_3 la cite (mesuré : RVMD ma_3 cite #1368)."""
    async def fetch(self, *_a, **_k):
        return [{"question_id": "ma_1", "ingredient_id": "repartition_des_usages", "entry_id": 7}]


_v = asyncio.run(contexte_durees(_ConnVoisine(), fichier=_F, version="v3.0.0", ancre_titre=_lk, cites={7}))
b.check([i.ingredient_id for i in _v.ingredients_des_pieces.get("ma_3", {}).get(7, [])] == ["repartition_des_usages"],
        "une pièce citée par ma_3 mais collectée pour ma_1 (même chapitre) prend la durée de vie de ce pour quoi "
        "elle a été collectée")
b.check(7 not in _v.ingredients_des_pieces.get("qf_1", {}),
        "…jamais celle d'un AUTRE chapitre (la pièce reste non rattachée pour qf_1 : durée la plus courte)")

src = strip_code((APP / "agents" / "v2" / "parcours.py").read_text(encoding="utf-8"))
arbre = ast.parse((APP / "agents" / "v2" / "parcours.py").read_text(encoding="utf-8"))
appels = [n for n in ast.walk(arbre) if isinstance(n, ast.Call)
          and getattr(n.func, "id", None) == "servir_answer"]
b.require(appels, 1, "parcours appelle servir_answer")
kw = {k.arg: k.value for c in appels for k in c.keywords}
b.check(isinstance(kw.get("durees"), ast.Name) and kw["durees"].id == "durees",
        "parcours passe `durees=durees` à servir_answer")
prod = [n for n in ast.walk(arbre) if isinstance(n, ast.Assign)
        and any(getattr(t, "id", None) == "durees" for t in n.targets)]
b.check(len(prod) == 1 and isinstance(prod[0].value, ast.Await)
        and getattr(prod[0].value.value.func, "id", None) == "contexte_durees",
        "`durees` est produit par `contexte_durees(...)` et par rien d'autre")

sys.exit(b.summary())
