"""Vérification de la règle « un verdict ne contredit jamais le chiffre qui le porte » (#139 ter).

Sans réseau, sans modèle, sans base : le modèle est remplacé, TOUT le reste est le vrai code. Les comptes
de RVMD sont reconstitués depuis l'inventaire RÉEL copié en fixture (jamais écrit à la main).

LE DÉFAUT MESURÉ (2026-10-18, RVMD reclassée « commerciale »). qf_3 et qf_5 : texte « non mesurable »,
verdict « croissance destructrice » / « en érosion » — et, à entrée identique, « croissance peu
capitalistique » au passage suivant. Six causes diagnostiquées ; les trois de FORME sont gardées ici :
le format imposait un verdict sans case « n.s. » ; aucune garde ne liait chiffre absent et verdict ; la
pente héritait « non établi » d'un rendement « non défini » (elle envoyait en collecte une propriété de
l'entreprise).

CE QUE FERAIT UN VRAI FONDS. Cellule « n.s. » (note : capitaux employés négatifs) ⟹ verdict « n.s. » ;
cellule vide ⟹ pas de verdict, on cherche ou on attend ; cellule chiffrée ⟹ un vrai verdict.

  • §1 L'ISSUE d'un chiffre absent (`ratios_maison.issue_du_motif`) : « non calculable » / « non défini »
       = non significatif ; « non établi » = manque ; la pente de RVMD est non significative.
  • §2 LE RÉFÉRENTIEL : qf_3 et qf_5 déclarent `sens_lu_sur` ; le contrat refuse un `sens_lu_sur` qui ne
       nomme pas un chiffre des comptes reconstitués, et le sens « non significatif » sans lui.
  • §3 LA LECTURE (`analyste.lecture_du_chiffre_du_verdict`) : RVMD qf_3/qf_5 non significatifs ; MSFT qf_5
       établi ; des comptes sans capital employé → manque.
  • §4 LES STATUTS : chiffre manquant ⟹ `repondu`/`approxime` fermés AVANT l'appel, la question reste
       posée (l'attente doit rester possible) ; « non significatif » n'est jamais montré au modèle.
  • §5 LE PASSAGE : RVMD qf_3/qf_5 écrits « n.s. » par le code, sans appel, et passent le pont ; le modèle
       ne les voit pas.
  • §6 LA GARDE (pont [S bis] + contrôleur ②, même détenteur) : chaque contradiction refusée, le cohérent
       passe ; la réponse fautive réelle (#1688) est rouverte à la LECTURE ; qf_1 (sans `sens_lu_sur`) libre.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte.
"""
import asyncio
import json
import sys
from pathlib import Path

from app.agents.v2 import analyste as A
from app.agents.v2 import manager as M
from app.agents.v2.frameworks import (
    FrameworkAnswerRefused, load_frameworks, motif_verdict_contredit_son_chiffre, question_profiles,
    valider_pont_framework_answer)
from app.contracts.framework_answer_schema import (
    ChiffreCle, Fondation, FrameworkAnswer, Reponse)
from app.contracts.framework_definition_schema import QuestionDefinition, SENS_NON_SIGNIFICATIF
from app.knowledge import ratios_maison as rm
from app.knowledge import socle_comptes as SC

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan  # noqa: E402

b = Bilan()
F = load_frameworks()
Q = {q.id: q for f in F.frameworks for q in f.questions}
FX = Path(__file__).resolve().parent / "fixtures" / "socle_comptes"
GAB = SC.charger_gabarit()


def socle(ticker):
    d = json.loads((FX / f"{ticker}.json").read_text(encoding="utf-8"))
    return SC.structure_du_socle(SC.reconstituer(d["faits"], GAB,
                                                 reclassements=SC.charger_reclassements(d["cik"], GAB)))


def entries_de(structure, nom):
    return {7: {"reliability_tier": "A", "nature": "mesure", "title": f"Socle des comptes — {nom}",
                "content": SC.rendre_socle(structure, GAB, raison_sociale=nom), "source_type": "edgar_official",
                "source_date": "2026-06-30", "date_du_document": "2026-08-05", "content_structured": structure}}


RV, MS = socle("RVMD"), socle("MSFT")
E_RV, E_MS = entries_de(RV, "Revolution Medicines, Inc."), entries_de(MS, "Microsoft Corporation")
SANS_CE = {**RV, "cellules": {k: v for k, v in RV["cellules"].items() if not k.startswith("capital_employe")}}
E_SANS_CE = entries_de(SANS_CE, "Revolution Medicines, Inc.")


def refuse(fn, motif, label):
    try:
        fn()
    except Exception as e:  # noqa: BLE001
        b.check(motif in str(e), f"{label} — refusé, mais pas pour la bonne raison : {e}")
        return
    b.check(False, f"{label} — ACCEPTÉ")


# ══ §1 L'ISSUE ═════════════════════════════════════════════════════════════════════════════════
print("[1] l'issue d'un chiffre absent")
b.check(rm.issue_du_motif("non calculable : aucun point de croissance") == rm.NON_SIGNIFICATIF
        and rm.issue_du_motif("non défini : capital moyen négatif") == rm.NON_SIGNIFICATIF,
        "§1 « non calculable » et « non défini » sont NON SIGNIFICATIFS (une propriété de l'entreprise)")
b.check(rm.issue_du_motif("non établi : pas de bilan d'ouverture") == rm.MANQUE
        and rm.issue_du_motif(None) == rm.MANQUE and rm.issue_du_motif("autre chose") == rm.MANQUE,
        "§1 « non établi », absent ou inconnu = MANQUE (dans le doute, on cherche)")
_v, _m = rm.ratio_du_socle(RV, "pente_du_rendement")
b.check(_v is None and rm.issue_du_motif(_m) == rm.NON_SIGNIFICATIF,
        f"§1 la pente de RVMD hérite du rendement NON DÉFINI : non significative ({_m[:60]})")

# ══ §2 LE RÉFÉRENTIEL ══════════════════════════════════════════════════════════════════════════
print("[2] le référentiel")
b.check(Q["qf_3"].sens_lu_sur == "capital_par_point_de_croissance" and Q["qf_5"].sens_lu_sur == "pente_du_rendement",
        "§2 qf_3 et qf_5 déclarent le chiffre qui porte leur verdict")
b.check(Q["qf_1"].sens_lu_sur is None and Q["qf_2"].sens_lu_sur is None,
        "§2 qf_1 et qf_2 n'en déclarent pas (leur verdict tient sur d'autres éléments)")
b.check(all((q.sens_lu_sur is not None) == (SENS_NON_SIGNIFICATIF in q.sens_admis) for q in Q.values()),
        "§2 le sens « non significatif » est au vocabulaire SI ET SEULEMENT SI la question déclare son chiffre")
_brut = Q["qf_5"].model_dump()
refuse(lambda: QuestionDefinition.model_validate({**_brut, "sens_lu_sur": "inconnu"}),
       "doit nommer un chiffre", "§2 un `sens_lu_sur` qui ne nomme aucun chiffre des comptes est refusé")
refuse(lambda: QuestionDefinition.model_validate({**_brut, "sens_lu_sur": None}),
       "va avec `sens_lu_sur`", "§2 le sens « non significatif » sans chiffre porteur est refusé")

# ══ §3 LA LECTURE ══════════════════════════════════════════════════════════════════════════════
print("[3] la lecture du chiffre du verdict")
l3, l5 = A.lecture_du_chiffre_du_verdict(Q["qf_3"], E_RV), A.lecture_du_chiffre_du_verdict(Q["qf_5"], E_RV)
b.check(l3 is not None and l3[0] == "non_significatif" and l3[2] == 7 and "croissance" in (l3[1] or ""),
        f"§3 RVMD qf_3 : non significatif, avec son motif et sa pièce (→ {l3})")
b.check(l5 is not None and l5[0] == "non_significatif", f"§3 RVMD qf_5 : non significatif (→ {l5 and l5[0]})")
lm = A.lecture_du_chiffre_du_verdict(Q["qf_5"], E_MS)
b.check(lm is not None and lm[0] == "etabli", f"§3 MSFT qf_5 : établi (témoin) (→ {lm and lm[0]})")
ls = A.lecture_du_chiffre_du_verdict(Q["qf_5"], E_SANS_CE)
b.check(ls is not None and ls[0] == "manque", f"§3 comptes sans capital employé : MANQUE (→ {ls and ls[0]})")
b.check(A.lecture_du_chiffre_du_verdict(Q["qf_5"], {}) == ("manque", "les comptes reconstitués ne sont pas au dossier", None),
        "§3 sans comptes reconstitués au dossier : manque, dit")
b.check(A.lecture_du_chiffre_du_verdict(Q["qf_1"], E_RV) is None, "§3 qf_1 (sans chiffre porteur) : rien à lire")

# ══ §4 LES STATUTS ═════════════════════════════════════════════════════════════════════════════
print("[4] les statuts montrés")
_cit = A.corpus_citable(Q["qf_5"], E_SANS_CE)
_ouv, _ec = A.statuts_ouverts(Q["qf_5"], _cit, E_SANS_CE)
b.check("repondu" not in _ouv and "approxime" not in _ouv and "sans_fondement" in _ouv
        and any("pente_du_rendement" in e for e in _ec),
        f"§4 chiffre manquant : `repondu`/`approxime` FERMÉS avant l'appel, l'écart nommé (→ {_ouv})")
_ctx = A.contexte_analyste(F, "qualite_financiere", "rentable", "RVMD", E_SANS_CE)
_q5 = next((q for q in _ctx["questions"] if q["id"] == "qf_5"), None)
b.check(_q5 is not None and "pas_encore_observable" in _q5["statuts_admis"] and "repondu" not in _q5["statuts_admis"],
        "§4 … mais la question RESTE posée : l'attente (« pas encore observable ») doit rester possible")
_ctx_ms = A.contexte_analyste(F, "qualite_financiere", "rentable", "MSFT", E_MS)
_q5m = next((q for q in _ctx_ms["questions"] if q["id"] == "qf_5"), None)
b.check(_q5m is not None and "repondu" in _q5m["statuts_admis"]
        and SENS_NON_SIGNIFICATIF not in _q5m["sens_admis"],
        "§4 chiffre établi : `repondu` ouvert, et « non significatif » n'est JAMAIS montré au modèle")

# ══ §5 LE PASSAGE ══════════════════════════════════════════════════════════════════════════════
print("[5] le passage : le code écrit « n.s. », sans appel")
vus: list = []


def passage(entries):
    class _Run:
        def __init__(self, parsed):
            self.parsed = parsed

    async def _faux_run(agent, messages, modele, **kw):
        ctx = json.loads(messages[0]["content"].split("\n\n", 2)[1].split("\n", 1)[1].rsplit("\n\nProduis", 1)[0])
        ids = [q["id"] for q in ctx["questions"]]
        vus.append(ids)
        return _Run(modele(reponses=[A.AnalysteReponse(question_id=i, statut="sans_fondement",
                                                       verbatim="manque fictif du passage hors ligne")
                                     for i in ids]))

    vrai_run, vrai_resolve = A.run_json_agent, A._resolve_analyste_agent
    A.run_json_agent = _faux_run
    A._resolve_analyste_agent = lambda: asyncio.sleep(0)
    try:
        return asyncio.run(A.repondre("RVMD", "qualite_financiere", "rentable", analyste="analyste_1",
                                      entries=entries, fichier=F, chemises=()))
    except Exception as exc:  # noqa: BLE001
        return exc
    finally:
        A.run_json_agent, A._resolve_analyste_agent = vrai_run, vrai_resolve


r = passage(E_RV)
if isinstance(r, Exception):
    b.check(False, f"§5 le passage a LEVÉ : {type(r).__name__}: {r}")
else:
    par = {a.question_id: a for a in r.answers}
    for qid in ("qf_3", "qf_5"):
        a = par.get(qid)
        b.check(a is not None and a.statut == "repondu" and a.reponse.sens == SENS_NON_SIGNIFICATIF
                and a.fondation.cited_entry_ids == [7] and "Non significatif" in a.reponse.verbatim,
                f"§5 RVMD {qid} : écrit « non significatif » par le code, adossé aux comptes (→ "
                f"{a.statut if a else None}/{a.reponse.sens if a and a.reponse else None})")
    b.check(vus and not ({"qf_3", "qf_5"} & set(vus[0])),
            f"§5 le modèle ne les voit pas (questions envoyées : {vus[0] if vus else None})")
    b.check(not [x for x in r.refus if x[0] in ("qf_3", "qf_5")], f"§5 aucun refus sur qf_3/qf_5 ({r.refus})")

# ══ §5 bis LES FAITS POSTÉRIEURS ════════════════════════════════════════════════════════════════
print("[5 bis] le verdict « n.s. » lit les faits postérieurs qui ne touchent pas les comptes clos")
# Mesuré RVMD #1703/#1704 : nées périmées par le communiqué du 05/08 (écarts d'exécution et d'allocation).
# Copié du réel : la lecture du dépôt #1546 (adresse EDGAR du dépôt, tier A, mesure).
from app.knowledge.material_events import MaterialEvent  # noqa: E402
from datetime import date as _d  # noqa: E402
ACC_T2, ACC_RT = "0001193125-26-335039", "0001193125-26-999999"
E_FAITS = {**E_RV,
           1546: {"reliability_tier": "A", "nature": "mesure", "title": "Lecture du dépôt 8-K du 2026-08-05",
                  "content": "Item 2.02 Results of Operations", "source_type": "edgar_official",
                  "source_date": "2026-08-05", "date_du_document": "2026-08-05",
                  "source_url": "https://www.sec.gov/Archives/edgar/data/1628171/000119312526335039/x-index.htm"},
           1600: {"reliability_tier": "A", "nature": "mesure", "title": "Lecture du dépôt — retraitement",
                  "content": "Item 4.02 Non-reliance", "source_type": "edgar_official",
                  "source_date": "2026-09-01", "date_du_document": "2026-09-01",
                  "source_url": "https://www.sec.gov/Archives/edgar/data/1628171/000119312526999999/x-index.htm"}}
T2 = MaterialEvent(form="8-K", event_date=_d(2026, 8, 5), filing_date=_d(2026, 8, 5), items=("2.02",),
                   accession=ACC_T2, types=("surprise_allocation", "surprise_execution"))
RT = MaterialEvent(form="8-K", event_date=_d(2026, 9, 1), filing_date=_d(2026, 9, 1), items=("4.02",),
                   accession=ACC_RT, types=("integrite_comptes",))


def passage_faits(faits):
    class _Run:
        def __init__(self, parsed):
            self.parsed = parsed

    async def _faux_run(agent, messages, modele, **kw):
        ctx = json.loads(messages[0]["content"].split("\n\n", 2)[1].split("\n", 1)[1].rsplit("\n\nProduis", 1)[0])
        return _Run(modele(reponses=[A.AnalysteReponse(question_id=q["id"], statut="sans_fondement",
                                                       verbatim="manque fictif du passage hors ligne")
                                     for q in ctx["questions"]]))
    vrai_run, vrai_resolve = A.run_json_agent, A._resolve_analyste_agent
    A.run_json_agent, A._resolve_analyste_agent = _faux_run, (lambda: asyncio.sleep(0))
    try:
        return asyncio.run(A.repondre("RVMD", "qualite_financiere", "rentable", analyste="analyste_1",
                                      entries=E_FAITS, fichier=F, chemises=(), faits=faits))
    except Exception as exc:  # noqa: BLE001
        return exc
    finally:
        A.run_json_agent, A._resolve_analyste_agent = vrai_run, vrai_resolve


def ns(r, qid):
    return None if isinstance(r, Exception) else next((a for a in r.answers if a.question_id == qid), None)


_r1 = passage_faits({"qf_3": [T2], "qf_5": [T2]})
_a = ns(_r1, "qf_5")
_lus = [f.depot for f in (_a.reponse.faits_posterieurs if _a and _a.reponse else [])]
b.check(_a is not None and _lus == [ACC_T2] and "exercices clos" in _a.reponse.faits_posterieurs[0].effet,
        f"§5 bis un communiqué trimestriel (écarts) est LU : sans effet sur des exercices clos (→ {_lus or _r1})")
_r2 = passage_faits({"qf_3": [RT], "qf_5": [RT]})
_b = ns(_r2, "qf_5")
b.check(_b is not None and _b.reponse is not None and _b.reponse.sens == SENS_NON_SIGNIFICATIF
        and not _b.reponse.faits_posterieurs,
        "§5 bis un RETRAITEMENT des comptes n'est jamais déclaré lu par le code : la réponse reste périmée")

# ══ §6 LA GARDE ════════════════════════════════════════════════════════════════════════════════
print("[6] la garde : pont [S bis] et contrôleur, même détenteur")


def reponse(qid, sens, ligne):
    return FrameworkAnswer(framework_id="qualite_financiere", framework_version=F.schema_version,
                           question_id=qid, ticker_id="RVMD", analyste="analyste_1", statut="repondu",
                           reponse=Reponse(verbatim="texte", sens=sens, chiffres_cles=[ligne]),
                           fondation=Fondation(cited_entry_ids=[7], rang_derive="A", nature_effective="mesure"))


NS = ChiffreCle(id="pente_du_rendement", unite="points/an",
                motif_absence="non défini : rendement non défini pour l'exercice clos le 2024-12-31")
MQ = ChiffreCle(id="pente_du_rendement", unite="points/an",
                motif_absence="non établi : pas de bilan d'ouverture pour l'exercice clos le 2024")
OK = ChiffreCle(id="pente_du_rendement", unite="points/an", valeur=-2.5, date_ou_periode="cinq exercices")
P = question_profiles(F)
cas = [("en_erosion", NS, "NON SIGNIFICATIF", "verdict sur un chiffre non significatif (le cas #1688)"),
       ("en_erosion", MQ, "n'est pas établi", "verdict sur un chiffre qui manque"),
       (SENS_NON_SIGNIFICATIF, OK, "est établi", "« non significatif » sur un chiffre établi")]
for sens, ligne, motif, label in cas:
    a = reponse("qf_5", sens, ligne)
    m = motif_verdict_contredit_son_chiffre(a, "pente_du_rendement")
    b.check(m is not None and motif in m, f"§6 détenteur : {label} → contradiction nommée")
    refuse(lambda a=a: valider_pont_framework_answer(a, questions=P, entries=E_RV), "[S bis]",
           f"§6 pont : {label} refusé")
    c, mc = M.controles_de_la_reponse(a, applicable=True, entries=E_RV, sens_lu_sur="pente_du_rendement")
    b.check(c.fondation == "ko" and motif in mc, f"§6 contrôleur (à la lecture) : {label} → fondation ko")
for sens, ligne, label in ((SENS_NON_SIGNIFICATIF, NS, "« n.s. » sur un chiffre non significatif"),
                           ("en_erosion", OK, "un vrai verdict sur un chiffre établi")):
    a = reponse("qf_5", sens, ligne)
    b.check(motif_verdict_contredit_son_chiffre(a, "pente_du_rendement") is None,
            f"§6 cohérent : {label} passe (témoin)")
_q1 = FrameworkAnswer(framework_id="qualite_financiere", framework_version=F.schema_version, question_id="qf_1",
                      ticker_id="RVMD", analyste="analyste_1", statut="repondu",
                      reponse=Reponse(verbatim="pertes", sens="detruit_de_la_valeur", chiffres_cles=[]),
                      fondation=Fondation(cited_entry_ids=[7], rang_derive="A", nature_effective="mesure"))
b.check(motif_verdict_contredit_son_chiffre(_q1, None) is None,
        "§6 qf_1, sans chiffre porteur : son verdict reste un jugement libre")
_rev = M.reviser_framework([reponse("qf_5", "en_erosion", NS)], fichier=F, framework_id="qualite_financiere",
                           archetype="rentable", ticker_id="RVMD", entries=E_RV)
_d = next(iter(_rev.decisions.values()), None)
b.check(_d is not None and _d.controles.fondation == "ko",
        "§6 la revue du chapitre passe `sens_lu_sur` au contrôleur : la réponse fautive se rouvre à la lecture")

sys.exit(b.summary())
