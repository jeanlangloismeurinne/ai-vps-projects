"""Check — ce qu'un événement ROUVRE : taxonomie par la forme et horloge PAR QUESTION (V3 lot 7, #89).

Ce que la capacité garantit, et ce que chaque section éprouve :

  • §1 LA FORME NE DÉCIDE QUE CE QU'ELLE DÉCIDE — `types_du_depot` rejoué sur les FORMES RÉELLES des
       dépôts RVMD / NVDA / MSFT (items relevés sur EDGAR le 2026-09-26, jamais inventés) : 2.03 est un
       financement, 8.01 est à qualifier, 9.01 seul est de la routine, 7.01 seul est à qualifier mais
       accessoire d'un item décidé, un 6-K sans item est à qualifier, un item inconnu aussi.
  • §2 CHAQUE QUESTION A SA PROPRE HORLOGE — sur le flux RVMD réel (26/08 FDA en 8.01, 27/08
       financement) et le référentiel RÉEL : qf_4 s'ancre au financement, mo_1 à l'approbation (à
       qualifier) — jamais au dernier fait venu.
  • §3 LE COUPLE DISCRIMINANT de l'arbitrage — pièces du 05/08, un seul fait postérieur :
       financement seul ⟹ mo_1 COURANTE et qf_4 PÉRIMÉE ; ajouter le 8.01 du 26/08 ⟹ mo_1 PÉRIMÉE.
       C'est la fausse fraîcheur de l'ancre unique, rendue exécutable.
  • §4 LES ÉTATS TRAVERSENT — `unavailable` et `none` ne se filtrent pas (#49) ; un flux dont aucun
       dépôt ne rouvre la question rend `none` AVEC une phrase qui le dit, et le motif d'actualité ne
       prétend pas que « l'émetteur n'a rien publié ».
  • §5 LE MOTIF DIT POURQUOI — le résumé du fait retenu nomme le type au titre duquel il rouvre.
  • §6 LE POINT DE LECTURE EST BRANCHÉ (AST) — l'assemblage du dossier sert chaque réponse et chaque
       position du comité contre l'ancre de SA question, produite par `ancre_de_la_question` nourrie
       de `types_qui_rouvrent` ; l'endpoint de décision du comité aussi. Un assert de comportement ne
       peut pas le tenir : sur un flux où le dernier fait rouvre tout, l'ancre unique donne le même
       verdict (fixture non discriminante) — la STRUCTURE le tient.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte.
"""
import ast
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, strip_code  # noqa: E402

from app.agents.v2.frameworks import load_frameworks, types_qui_rouvrent  # noqa: E402
from app.knowledge.actualite import etat_actualite  # noqa: E402
from app.knowledge.evenements import (  # noqa: E402
    A_QUALIFIER, ancre_de_la_question, types_du_depot)
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup  # noqa: E402

b = Bilan()
APP = Path(__file__).resolve().parent.parent / "app"


def ev(d, items, filed=None, acc=None):
    return MaterialEvent(form="8-K" if items else "6-K", event_date=date.fromisoformat(d),
                         filing_date=date.fromisoformat(filed or d), items=tuple(items),
                         accession=acc or f"acc-{d}-{'-'.join(items)}")


def flux(*events):
    evs = tuple(sorted(events, key=lambda e: (e.event_date, e.filing_date), reverse=True))
    return MaterialEventLookup(status="found", event=evs[0], cik=1628171, recents=evs)


def types(items):
    try:
        return sorted(types_du_depot(ev("2026-01-01", items)))
    except Exception as e:  # noqa: BLE001 — un refus inattendu est un FAIL nommé, pas la mort
        return f"LÈVE : {e!r}"


# ── Flux RÉEL de RVMD (relevé EDGAR du 2026-09-26, `reportDate` / `filingDate` / items) ──────────
FIN_27_08 = ev("2026-08-27", ["1.01", "2.03"], filed="2026-09-01")
FDA_26_08 = ev("2026-08-26", ["8.01"])
RES_05_08 = ev("2026-08-05", ["2.02", "9.01"])
GOUV_18_06 = ev("2026-06-18", ["5.02", "5.07"], filed="2026-06-22")

fichier = load_frameworks()


def ancre(lk, qid):
    try:
        return ancre_de_la_question(lk, rouvrent=types_qui_rouvrent(fichier, qid))
    except Exception as e:  # noqa: BLE001
        return MaterialEventLookup(status="unavailable", raison=f"LÈVE : {e!r}")


print("§1 la forme ne décide que ce qu'elle décide (formes réelles RVMD/NVDA/MSFT)")
for items, attendu, label in [
    (["1.01", "2.03"], ["financement"], "RVMD 27/08 — accord + obligation financière"),
    (["8.01"], [A_QUALIFIER], "RVMD 26/08 — approbation FDA publiée en « autre événement »"),
    (["2.02", "9.01"], ["resultats"], "RVMD 05/08 — résultats + pièces jointes"),
    (["5.02", "5.07"], ["gouvernance", "routine"], "RVMD 18/06 — dirigeants + vote d'AG"),
    (["1.01", "2.03", "8.01", "9.01"], [A_QUALIFIER, "financement"],
     "RVMD 14/04 — financement ACCOMPAGNÉ d'un 8.01 : dans le doute, à qualifier aussi"),
    (["1.01", "2.03", "7.01"], ["financement"], "NVDA 17/08 — 7.01 accessoire du financement"),
    (["7.01", "9.01"], [A_QUALIFIER], "MSFT 02/09 — 7.01 SEUL (peut être un avertissement)"),
    (["2.02", "7.01", "9.01"], ["resultats"], "MSFT 28/10/2025 — 7.01 accessoire des résultats"),
    (["9.01"], ["routine"], "9.01 seul — pure forme"),
    ([], [A_QUALIFIER], "6-K sans item — « sans item » n'est pas « sans substance »"),
    (["1.01"], [A_QUALIFIER], "1.01 SANS obligation ni émission — peut-être une licence"),
    (["9.99"], [A_QUALIFIER], "item inconnu — jamais ignoré"),
    (["1.05"], ["incident"], "MSFT 1.05 — cybersécurité"),
    (["4.02"], ["integrite_comptes"], "comptes antérieurs non fiables"),
    (["2.01"], ["perimetre"], "acquisition ou cession"),
]:
    b.check(types(items) == attendu, f"{label} → {attendu} (obtenu {types(items)})")


print("§2 chaque question a sa propre horloge (flux RVMD réel, référentiel réel)")
reel = flux(FIN_27_08, FDA_26_08, RES_05_08, GOUV_18_06)
a_qf4, a_mo1, a_qf6 = ancre(reel, "qf_4"), ancre(reel, "mo_1"), ancre(reel, "qf_6")
b.check(a_qf4.status == "found" and a_qf4.event.event_date == date(2026, 8, 27),
        f"qf_4 (financement) s'ancre au financement du 27/08 → {a_qf4.status} "
        f"{getattr(a_qf4.event, 'event_date', None)}")
b.check(a_mo1.status == "found" and a_mo1.event.event_date == date(2026, 8, 26),
        f"mo_1 (la barrière) s'ancre au 8.01 du 26/08, PAS au financement du 27/08 → "
        f"{a_mo1.status} {getattr(a_mo1.event, 'event_date', None)}")
b.check(a_qf6.status == "found" and a_qf6.event.event_date == date(2026, 8, 26),
        "qf_6 (choix comptables) : le financement ne la rouvre pas, le 8.01 à qualifier si "
        f"→ {getattr(a_qf6.event, 'event_date', None)}")
b.check(all(e.event_date != date(2026, 6, 18) for e in a_mo1.recents),
        "un dépôt de pure gouvernance + routine ne rouvre aucune question de défendabilité")


print("§3 le couple discriminant : la fausse fraîcheur de l'ancre unique")
PIECES = date(2026, 8, 5)   # date des pièces des réponses de défendabilité RVMD (#690-694)
sans_fda = flux(FIN_27_08, RES_05_08)
avec_fda = flux(FIN_27_08, FDA_26_08, RES_05_08)
e1 = etat_actualite(source_date=PIECES, ancre=ancre(sans_fda, "mo_1")).etat
e2 = etat_actualite(source_date=PIECES, ancre=ancre(sans_fda, "qf_4")).etat
e3 = etat_actualite(source_date=PIECES, ancre=ancre(avec_fda, "mo_1")).etat
b.check(e1 == "courante", f"financement seul : la barrière (mo_1) reste À JOUR → {e1}")
b.check(e2 == "perimee", f"financement seul : la structure de financement (qf_4) est PÉRIMÉE → {e2}")
b.check(e3 == "perimee", f"avec l'approbation du 26/08 : la barrière (mo_1) est PÉRIMÉE → {e3}")
b.check(etat_actualite(source_date=PIECES, ancre=sans_fda).etat == "perimee",
        "témoin : l'ANCRE UNIQUE (dernier fait venu) périmait mo_1 sur un simple financement")


print("§4 les états traversent ; un « aucun » filtré se DIT")
indispo = MaterialEventLookup(status="unavailable", raison="EDGAR 503")
rien = MaterialEventLookup(status="none", cik=1)
b.check(ancre(indispo, "mo_1").status == "unavailable", "`unavailable` traverse (#49)")
b.check(ancre(rien, "mo_1").status == "none" and ancre(rien, "mo_1").filtre is None,
        "`none` (rien publié) traverse, sans phrase de filtre")
seul_fin = ancre(flux(FIN_27_08), "mo_1")
b.check(seul_fin.status == "none" and bool(seul_fin.filtre)
        and "rouvre cette question" in (seul_fin.filtre or ""),
        f"aucun dépôt ne rouvre mo_1 → `none` + la phrase qui le dit → {seul_fin.filtre!r}")
motif = etat_actualite(source_date=PIECES, ancre=seul_fin).motif
b.check("aucun 8-K" not in motif and "rouvre" in motif,
        f"le motif ne prétend pas que l'émetteur n'a rien publié → {motif!r}")


print("§5 le motif dit POURQUOI le fait compte")
b.check("rouvre au titre de : financement" in a_qf4.event.resume(),
        f"le fait retenu pour qf_4 se nomme par son type → {a_qf4.event.resume()!r}")
b.check("rouvre au titre de" not in FIN_27_08.resume(),
        "un dépôt non rapporté à une question ne s'attribue aucun type")


print("§6 le point de lecture est branché (AST)")


def fonction(path, nom):
    arbre = ast.parse((APP / path).read_text(encoding="utf-8"))
    for n in ast.walk(arbre):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == nom:
            return n
    return None


def appels(noeud, nom):
    return [n for n in ast.walk(noeud) if isinstance(n, ast.Call)
            and ((isinstance(n.func, ast.Name) and n.func.id == nom)
                 or (isinstance(n.func, ast.Attribute) and n.func.attr == nom))]


def kw(call, nom):
    return next((k.value for k in call.keywords if k.arg == nom), None)


def est_appel(v, nom):
    return isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id == nom


charger = fonction("agents/v2/parcours.py", "charger_etat_dossier")
b.check(charger is not None, "`charger_etat_dossier` existe")
if charger is not None:
    serv = appels(charger, "servir_answer")
    b.require(serv, 1, "un seul appel à `servir_answer` dans l'assemblage")
    b.check(all(est_appel(kw(c, "ancre"), "ancre_de") for c in serv),
            "chaque réponse est servie contre l'ancre de SA question (`ancre=ancre_de(…)`)")
    pos = appels(charger, "position_du_comite")
    b.require(pos, 1, "un seul appel à `position_du_comite` dans l'assemblage")
    b.check(all(est_appel(kw(c, "ancre"), "ancre_de") for c in pos),
            "la position du comité se juge contre l'ancre de SA question (`ancre=ancre_de(…)`)")
    filtres = appels(charger, "ancre_de_la_question")
    b.require(filtres, 1, "un seul appel à `ancre_de_la_question` dans l'assemblage")
    b.check(all(est_appel(kw(c, "rouvrent"), "types_qui_rouvrent") for c in filtres),
            "l'ancre d'une question est filtrée par `types_qui_rouvrent` (détenteur unique)")
decider = fonction("api/parcours_v2.py", "_decider")
b.check(decider is not None and len(appels(decider, "ancre_de_la_question")) == 1
        and all(est_appel(kw(c, "rouvrent"), "types_qui_rouvrent")
                for c in appels(decider, "ancre_de_la_question")),
        "l'endpoint de décision du comité inscrit au PV l'ancre de SA question")
src = strip_code((APP / "knowledge/evenements.py").read_text(encoding="utf-8"))
b.check("async def" not in src and "await" not in src and "httpx" not in src,
        "le module de taxonomie est PUR : aucune IO (l'ancre se recalcule à la lecture, #53)")

sys.exit(b.summary())
