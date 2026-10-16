"""Check — la NOTE FLASH : lire un dépôt dont la forme ne dit pas la substance (V3 lot 7, maillon 2, #90).

Ce que la capacité garantit, et ce que chaque section éprouve :

  • §1 LE CONTRAT — une surprise dit sa cause ; une cause dite se cite, une cause non dite ne se cite
       pas ; un `surprise_*` direct est refusé (le code dérive le type) ; deux formes, jamais mêlées
       (lisible ⟹ ≥ 1 élément ; illisible ⟹ aucun élément et un motif).
  • §2 LE TYPE EST DÉRIVÉ PAR LE CODE — cause non dite ⟹ `surprise_concurrence` (arbitrage Q2).
  • §3 CE QU'ON LIT D'UN DÉPÔT — sur quatre soumissions EDGAR RÉELLES (fixtures copiées du réel,
       blobs XBRL/images retirés) : le formulaire et ses EX-99, jamais un acte juridique ni le XBRL ;
       ni l'en-tête XBRL masqué ni la page de garde ; la troncature est dite.
  • §4 CE QUE LE MODÈLE VOIT — le catalogue par identifiant et libellé, JAMAIS la portée ni ce que
       rouvre un type (aucun levier sur l'exigence, #59) ; `a_qualifier` et les `surprise_*` n'y sont
       pas proposés ; l'entreprise par sa raison sociale.
  • §5 LE PONT — une citation littérale passe (guillemets typographiques et espaces normalisés) ; une
       paraphrase, un type hors catalogue, un `a_qualifier` déguisé, une cause citée à faux sont
       refusés EN LES NOMMANT ; une note illisible devient `{a_qualifier}`.
  • §6 QUELS DÉPÔTS LIRE — les seuls `a_qualifier` non encore lus, depuis une date ; une ancre
       indisponible ne produit aucune lecture.
  • §7 LA RELECTURE — une note relue sous un référentiel qui ne connaît plus son type revient à
       `a_qualifier` (un type disparu ne devient jamais « ne rouvre rien ») ; le résumé cite le passage.
  • §8 LA RÉDACTION DE BOUT EN BOUT (faux modèle scripté) — une citation refusée est renvoyée UNE fois
       au modèle, puis la note est refusée ; un dépôt sans document lisible est refusé AVANT tout appel.
  • §9 LE RAPPEL (#125, ordre 1 débrayable) — sur le 8-K RÉEL du tirage RVMD (08/10) qui rappelle
       l'approbation du 26/08 : un rappel n'est ADMIS que si une note antérieure a annoncé ce type à
       cette date (sinon il compte comme nouveau) ; les types persistés restent ceux de l'ordre 0 ;
       interrupteur à True ⟹ le rappel admis ne rouvre rien, à False ⟹ l'ordre 0 exact ; une note faite
       que de rappels se lit `routine` ; une surprise n'est jamais un rappel.
  • §10 LE COMMUNIQUÉ DE RÉSULTATS (diagnostic §13) — phrases relevées, référence, date lue, vote.
  • §11 LA RÉVISION SANS CAUSE DITE (table des causes, catalogue 1.6.0, §14 de `06-regle-fraicheur.md`) —
       sur la vraie révision RVMD du 05/08 : le chiffre déclaré se VÉRIFIE dans la phrase, le sens dans les
       montants des deux prévisions ; vérifiés, ils resserrent sur les causes probables (allocation,
       exécution — jamais la concurrence) ; invérifiables, le côté prudent (tous les chiffres nommés, les
       deux sens, ou toute la table) ; un élément persisté avant la table garde la règle Q2.

Cible : pydantic v2 (container backend). Tester en container, **pas** le python hôte.
"""
import asyncio
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan  # noqa: E402

from app.agents.providers import ResolvedAgent  # noqa: E402
from app.agents.providers.base import AgentProvider, CompletionResult  # noqa: E402
from app.agents.v2.frameworks import load_frameworks  # noqa: E402
from app.agents.v2.note_flash import (  # noqa: E402
    NoteFlashImpossible, NoteFlashRefusee, contexte_note_flash, depots_a_lire, extraire_documents,
    NotePrecedente, precedentes_de, rediger_note_flash, relire_note, types_annonces,
    types_proposables, valider_note, verdict_rappel)
from app.contracts.note_flash_schema import NoteFlashSortie, type_derive  # noqa: E402
from app.knowledge.edgar_feed import IdentiteEmetteur  # noqa: E402
from app.knowledge.evenements import A_QUALIFIER, QualificationLue  # noqa: E402
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup  # noqa: E402

b = Bilan()
FIX = Path(__file__).resolve().parent / "fixtures" / "note_flash"
fichier = load_frameworks()
RVMD = IdentiteEmetteur(symbole="RVMD", cik=1628171, raison_sociale="Revolution Medicines, Inc.")


def replace_q(q, d):
    from dataclasses import replace
    return replace(q, date_evenement=d)


def soumission(acc):
    return (FIX / f"{acc}.txt").read_text(encoding="utf-8")


def sortie(**kw):
    try:
        return NoteFlashSortie.model_validate(kw)
    except Exception as e:  # noqa: BLE001 — un refus est une VALEUR, jamais la mort du script
        return f"REFUSÉ : {e}"


def refuse(obj, motif):
    return isinstance(obj, str) and obj.startswith("REFUSÉ") and motif in obj


PASS_FDA = ("On August 26, 2026, the U.S. Food and Drug Administration approved RASONQUE™ "
            "(daraxonrasib) for the treatment of adult patients")

print("§1 le contrat")
b.check(not isinstance(sortie(lisible=True, elements=[{"type": "reglementaire_favorable",
                                                        "passage": PASS_FDA}]), str),
        "une note lisible, un élément cité → acceptée")
b.check(refuse(sortie(lisible=True, elements=[{"type": "surprise", "passage": PASS_FDA}]),
               "dit sa cause"), "une surprise SANS cause est refusée")
b.check(refuse(sortie(lisible=True, elements=[{"type": "surprise", "passage": PASS_FDA,
                                                "cause": "secteur"}]), "passage_cause"),
        "une cause DITE sans passage qui la cite est refusée")
b.check(refuse(sortie(lisible=True, elements=[{"type": "surprise", "passage": PASS_FDA,
                                                "cause": "non_dite", "passage_cause": PASS_FDA}]),
               "ne se cite pas"), "une cause NON DITE qui se cite est refusée")
b.check(refuse(sortie(lisible=True, elements=[{"type": "surprise_secteur", "passage": PASS_FDA}]),
               "le type s'en déduit"), "un `surprise_*` direct est refusé (le code dérive le type)")
b.check(refuse(sortie(lisible=True, elements=[{"type": "resultats", "passage": PASS_FDA,
                                                "cause": "secteur", "passage_cause": PASS_FDA}]),
               "n'a de sens que"), "une cause hors surprise est refusée")
b.check(refuse(sortie(lisible=True, elements=[]), "au moins un type"),
        "une note lisible sans élément est refusée")
b.check(refuse(sortie(lisible=False, elements=[], motif=None), "dit pourquoi"),
        "une note illisible sans motif est refusée")
b.check(refuse(sortie(lisible=False, motif="texte coupé avant l'item",
                      elements=[{"type": "routine", "passage": PASS_FDA}]), "aucun élément"),
        "une note illisible qui range quand même est refusée")
b.check(refuse(sortie(lisible=True, elements=[{"type": "surprise", "passage": PASS_FDA,
                                                "cause": "non_dite", "rappel_du": "2026-08-26"}]),
               "jamais un rappel"), "un écart aux attentes n'est jamais un rappel (#125)")
b.check(refuse(sortie(lisible=True, elements=[{"type": "routine", "passage": "FDA approved"}]),
               "passage"), "une citation trop courte pour prouver quoi que ce soit est refusée")

print("§2 le type est dérivé par le code (Q2)")
nd = sortie(lisible=True, elements=[{"type": "surprise", "passage": PASS_FDA, "cause": "non_dite"}])
ex = sortie(lisible=True, elements=[{"type": "surprise", "passage": PASS_FDA, "cause": "execution",
                                     "passage_cause": PASS_FDA}])
b.check(not isinstance(nd, str) and type_derive(nd.elements[0]) == "surprise_concurrence",
        "cause non dite ⟹ `surprise_concurrence`")
b.check(not isinstance(ex, str) and type_derive(ex.elements[0]) == "surprise_execution",
        "cause exécution ⟹ `surprise_execution`")
b.check(type_derive(sortie(lisible=True, elements=[{"type": "perimetre", "passage": PASS_FDA}])
                    .elements[0]) == "perimetre", "hors surprise, le type traverse")

print("§3 ce qu'on lit d'un dépôt (soumissions EDGAR réelles)")
d_fda = extraire_documents(soumission("0001193125-26-366931"))
d_nvda = extraire_documents(soumission("0001045810-26-000078"))
d_msft = extraire_documents(soumission("0001193125-26-380280"))
d_fin = extraire_documents(soumission("0001193125-26-161800"))
b.require(d_fda, 1, "RVMD 26/08 : le seul formulaire (le XBRL n'est pas lu)")
b.check(d_fda and d_fda[0].type == "8-K" and d_fda[0].texte.startswith("Item 8.01")
        and "approved RASONQUE" in d_fda[0].texte,
        "RVMD 26/08 : le texte commence au premier item et porte l'approbation")
b.check(d_fda and "Check the appropriate box" not in d_fda[0].texte,
        "la page de garde du formulaire n'est pas lue")
b.check(d_nvda and "Hugging Face" in d_nvda[0].texte and "0001045810false" not in d_nvda[0].texte
        and "us-gaap" not in d_nvda[0].texte.lower()[:200],
        "NVDA 02/09 : l'en-tête XBRL masqué n'est pas du texte")
# Un 6-K ne porte JAMAIS d'item : la page de garde ne se coupe pas, et c'est l'en-tête XBRL masqué qui
# fuirait. Même soumission NVDA RÉELLE, présentée comme un 6-K sans item (seule transformation).
brut_nvda = soumission("0001045810-26-000078")
en_6k = brut_nvda.replace("<TYPE>8-K", "<TYPE>6-K").replace("Item", "Rubrique").replace("ITEM", "RUBRIQUE")
d_6k = extraire_documents(en_6k)
b.check(d_6k and d_6k[0].type == "6-K" and "Hugging Face" in d_6k[0].texte
        and "0001045810" not in d_6k[0].texte[:400],
        "un 6-K (sans item) : l'en-tête XBRL masqué n'est pas du texte")
b.check([d.type for d in d_msft] == ["8-K", "EX-99.1"],
        f"MSFT 02/09 : le formulaire et son communiqué EX-99.1 → {[d.type for d in d_msft]}")
# Budget desserré le 2026-10-16 (30 000 par pièce) : la présentation MSFT tient désormais ; la troncature
# s'éprouve sous un budget abaissé, sur la même soumission réelle.
import app.agents.v2.note_flash as _nf_mod  # noqa: E402
_budget = _nf_mod._MAX_PIECE
_nf_mod._MAX_PIECE = 5_000
try:
    _d_court = extraire_documents(soumission("0001193125-26-380280"))
finally:
    _nf_mod._MAX_PIECE = _budget
b.check(len(_d_court) == 2 and _d_court[1].tronque and _d_court[1].taille > len(_d_court[1].texte),
        "MSFT 02/09 : une pièce qui dépasse le budget est tronquée, et la troncature est DITE")
b.check([d.type for d in d_fin] == ["8-K"],
        f"RVMD 14/04 : l'avis juridique EX-5.1 et le XBRL ne sont pas lus → {[d.type for d in d_fin]}")
b.check(sum(len(d.texte) for d in d_msft) <= 45_000, "le budget total est tenu")
b.check(extraire_documents("") == [] and extraire_documents("<SEC-DOCUMENT></SEC-DOCUMENT>") == [],
        "une soumission vide ne produit aucun document (jamais une exception)")

print("§4 ce que le modèle voit")
EV_FDA = MaterialEvent(form="8-K", event_date=date(2026, 8, 26), filing_date=date(2026, 8, 26),
                       items=("8.01",), accession="0001193125-26-366931")
ctx = contexte_note_flash(EV_FDA, RVMD, d_fda, fichier, precedentes=[])
ids = [t["id"] for t in ctx["types_evenement"]]
b.check(A_QUALIFIER not in ids and not any(i.startswith("surprise_") for i in ids)
        and "surprise" in ids and "reglementaire_favorable" in ids and "routine" in ids,
        f"catalogue proposé : sans `a_qualifier` ni `surprise_*`, avec `surprise` → {ids}")
lib = {t["id"]: t["libelle"] for t in ctx["types_evenement"]}
b.check("FINANCIERS" in lib.get("surprise", "") and "clinique" in lib.get("surprise", "")
        and "FINANCIERS" in lib.get("resultats", "")
        and "essai clinique" in lib.get("reglementaire_favorable", ""),
        "les libellés séparent l'écart FINANCIER du résultat clinique (#69/#71 : énoncé seul, le "
        "sens se prouve à la lecture des notes)")
b.check(all(set(t) == {"id", "libelle"} for t in ctx["types_evenement"]),
        "chaque type n'est vu que par son identifiant et son libellé")
texte_ctx = repr(ctx)
b.check("portee" not in texte_ctx and "rouverte_par" not in texte_ctx
        and "questions_declarees" not in texte_ctx and "qf_" not in texte_ctx
        and "mo_" not in texte_ctx,
        "le modèle ne voit NI la portée NI ce que rouvre un type (aucun levier sur l'exigence)")
b.check(ctx["entreprise"]["raison_sociale"] == "Revolution Medicines, Inc.",
        "l'entreprise est nommée par sa raison sociale (#86)")
b.check([i["item"] for i in ctx["depot"]["items"]] == ["8.01"]
        and ctx["depot"]["items"][0]["libelle"] == "autre événement important",
        "la forme du dépôt est donnée, libellée")

print("§5 le pont")


def pont(**kw):
    s = sortie(**kw)
    if isinstance(s, str):
        return s
    try:
        return valider_note(s, d_fda, fichier, event_date=EV_FDA.event_date, precedentes=[], cloture_publiee=None, reference_precedente=[], phrases=[])
    except NoteFlashRefusee as e:
        return f"REFUSÉ : {e}"


# Guillemets droits et espaces multiples : la citation doit rester reconnue.
cite_normalisee = ("the U.S.   Food and Drug Administration approved RASONQUE™ (daraxonrasib) for "
                   "the treatment of adult patients with metastatic pancreatic adenocarcinoma")
v = pont(lisible=True, elements=[{"type": "reglementaire_favorable", "passage": cite_normalisee}])
b.check(not isinstance(v, str) and v.types == ("reglementaire_favorable",) and v.lisible,
        f"une citation littérale (espaces normalisés) passe → {v if isinstance(v, str) else v.types}")
b.check(refuse(pont(lisible=True, elements=[{"type": "reglementaire_favorable",
                                             "passage": "The FDA has approved the company's drug "
                                                        "RASONQUE for pancreatic cancer"}]),
               "introuvable"), "une PARAPHRASE est refusée, en le nommant")
b.check(refuse(pont(lisible=True, elements=[{"type": "approbation_fda", "passage": cite_normalisee}]),
               "absent du catalogue"), "un type hors catalogue est refusé, en le nommant")
b.check(refuse(pont(lisible=True, elements=[{"type": A_QUALIFIER, "passage": cite_normalisee}]),
               "absent du catalogue"), "`a_qualifier` n'est pas un type qu'une note lisible range")
# #93 — les types d'origine EXTÉRIEURE (événement chez un concurrent) ne sont ni vus ni admis : la
# note lit un dépôt de l'émetteur. Liste lue dans le référentiel réel, et exigée non vide (un
# `all()`/intersection sur liste vide serait un faux vert).
_exterieurs = {t.id for t in fichier.types_evenement if t.origine == "exterieur"}
b.check(bool(_exterieurs) and not (_exterieurs & {t["id"] for t in ctx["types_evenement"]}),
        f"aucun type d'origine extérieure n'est proposé au modèle (#93) → {sorted(_exterieurs)}")
b.check(refuse(pont(lisible=True, elements=[{"type": "concurrent_offensive",
                                             "passage": cite_normalisee}]),
               "absent du catalogue"),
        "un dépôt de l'émetteur rangé en « offensive d'un concurrent » est refusé (#93)")
b.check(refuse(pont(lisible=True, elements=[{"type": "surprise", "passage": cite_normalisee,
                                             "cause": "secteur",
                                             "passage_cause": "demand weakened across the whole "
                                                              "industry this quarter"}]),
               "passage_cause"), "une cause citée à faux est refusée")
v2 = pont(lisible=True, elements=[{"type": "surprise", "passage": cite_normalisee, "cause": "non_dite"},
                                  {"type": "reglementaire_favorable", "passage": cite_normalisee}])
b.check(not isinstance(v2, str) and v2.types == ("reglementaire_defavorable", "reglementaire_favorable",
                                                 "surprise_allocation", "surprise_concurrence",
                                                 "surprise_execution", "surprise_secteur"),
        f"les types retenus sont ceux que le CODE dérive (révision sans cause ni chiffre déclaré : toute la "
        f"table, côté prudent) → {v2 if isinstance(v2, str) else v2.types}")
vi = pont(lisible=False, motif="le texte ne contient que la page de signature du dépôt")
b.check(not isinstance(vi, str) and vi.types == (A_QUALIFIER,) and not vi.lisible and vi.motif,
        "une note illisible devient `{a_qualifier}` avec son motif (rouvre tout, Q3)")
deux_defauts = pont(lisible=True, elements=[{"type": "approbation_fda", "passage": cite_normalisee},
                                            {"type": "routine", "passage": "une phrase qui n'est "
                                                                           "nulle part dans le dépôt"}])
b.check(refuse(deux_defauts, "élément 1") and refuse(deux_defauts, "élément 2"),
        "le refus nomme CHAQUE défaut, pas seulement le premier")

print("§6 quels dépôts lire")
FIN = MaterialEvent(form="8-K", event_date=date(2026, 8, 27), filing_date=date(2026, 9, 1),
                    items=("1.01", "2.03"), accession="acc-fin")
VIEUX = MaterialEvent(form="8-K", event_date=date(2024, 3, 1), filing_date=date(2024, 3, 1),
                      items=("8.01",), accession="acc-vieux")
MIXTE = MaterialEvent(form="8-K", event_date=date(2026, 4, 14), filing_date=date(2026, 4, 14),
                      items=("1.01", "2.03", "8.01", "9.01"), accession="acc-mixte")
lk = MaterialEventLookup(status="found", event=FIN, cik=1628171, recents=(FIN, EV_FDA, MIXTE, VIEUX))
a_lire = depots_a_lire(lk, {}, depuis=date(2025, 1, 1))
b.check([e.accession for e in a_lire] == [EV_FDA.accession, "acc-mixte"],
        f"les `a_qualifier` depuis la date, du plus récent au plus ancien → {[e.accession for e in a_lire]}")
deja = {EV_FDA.accession: QualificationLue(types=frozenset({A_QUALIFIER}), resume="illisible")}
b.check([e.accession for e in depots_a_lire(lk, deja, depuis=date(2025, 1, 1))] == ["acc-mixte"],
        "un dépôt déjà lu — même jugé illisible — n'est pas relu")
vieille = {EV_FDA.accession: QualificationLue(types=frozenset({"reglementaire_favorable"}),
                                             resume="lue sous 1.0.0", a_relire=True)}
b.check([e.accession for e in depots_a_lire(lk, vieille, depuis=date(2025, 1, 1))]
        == [EV_FDA.accession, "acc-mixte"],
        "une note écrite sous une AUTRE version du catalogue est relue (la grille a changé)")
b.check(depots_a_lire(MaterialEventLookup(status="unavailable", raison="503"), {},
                      depuis=date(2025, 1, 1)) == [], "une ancre indisponible ne produit aucune lecture")

print("§7 la relecture")
LE = datetime(2026, 9, 26, 10, tzinfo=timezone.utc)
CUR = fichier.types_evenement_version
lue = relire_note({"accession": "x", "catalogue_version": CUR, "lisible": True,
                   "types": ["reglementaire_favorable"],
                   "elements": [{"type": "reglementaire_favorable", "passage": PASS_FDA}],
                   "motif": None, "redigee_le": LE}, fichier)
b.check(lue.types == frozenset({"reglementaire_favorable"}) and "RASONQUE" in lue.resume
        and not lue.a_relire
        and "2026-09-26" in lue.resume, f"une note lisible se relit, passage et date → {lue.resume!r}")
disparu = relire_note({"accession": "x", "lisible": True, "types": ["type_retire_du_referentiel"],
                       "elements": [{"type": "type_retire_du_referentiel", "passage": PASS_FDA}],
                       "motif": None, "redigee_le": LE}, fichier)
b.check(disparu.types == frozenset({A_QUALIFIER}) and "type_retire_du_referentiel" in disparu.resume,
        "un type que le référentiel ne connaît plus ramène la note à `a_qualifier`, en le nommant")
ill = relire_note({"accession": "x", "catalogue_version": CUR, "lisible": False,
                   "types": [A_QUALIFIER], "elements": [],
                   "motif": "page de signature seule", "redigee_le": LE}, fichier)
b.check(ill.types == frozenset({A_QUALIFIER}) and "page de signature seule" in ill.resume
        and not ill.a_relire,
        "une note illisible se relit `a_qualifier`, motif à l'appui")
ancienne = relire_note({"accession": "x", "catalogue_version": "v3.0.0", "lisible": True,
                        "types": ["reglementaire_favorable"],
                        "elements": [{"type": "reglementaire_favorable", "passage": PASS_FDA}],
                        "motif": None, "redigee_le": LE}, fichier)
b.check(ancienne.a_relire and ancienne.types == frozenset({"reglementaire_favorable"})
        and "à relire" in ancienne.resume and "v3.0.0" in ancienne.resume,
        f"une note d'une ancienne version COMPTE encore, et se dit à relire → {ancienne.resume!r}")
long_ = relire_note({"accession": "x", "catalogue_version": CUR, "lisible": True, "types": ["routine"],
                     "elements": [{"type": "routine", "passage": "x" * 400}], "motif": None,
                     "redigee_le": LE}, fichier)
b.check(len(long_.resume) < 260 and long_.resume.endswith("… »"), "un passage long est abrégé, et le dit")

print("§8 la rédaction de bout en bout (faux modèle scripté)")


class _Scripte(AgentProvider):
    name = "fake"

    def __init__(self, contenus: list[str]) -> None:
        self._c = list(contenus)
        self.appels = 0

    async def complete(self, *, system: str, messages: list[dict[str, Any]], model: str,
                       tools=None, tool_choice=None, response_format: Optional[dict] = None,
                       temperature: float = 0.3, max_tokens=None, timeout: int = 720):
        self.appels += 1
        return CompletionResult(content=self._c.pop(0), model="fake-model", tokens_in=10,
                                tokens_out=5, cost_usd=0.0)

    async def stream(self, **kwargs: Any):  # type: ignore[override]
        raise NotImplementedError
        yield  # pragma: no cover


def agent(contenus):
    p = _Scripte(contenus)
    return p, ResolvedAgent(agent_name="ingestion-agent", flow_version="v2", provider=p,
                            model="fake-model", system_prompt="(check)")


BON = ('{"lisible": true, "elements": [{"type": "reglementaire_favorable", "passage": '
       '"the U.S. Food and Drug Administration approved RASONQUE™ (daraxonrasib) for the treatment"}]}')
PARAPHRASE = ('{"lisible": true, "elements": [{"type": "reglementaire_favorable", "passage": '
              '"The FDA has approved the company drug RASONQUE for pancreatic cancer"}]}')


def rediger(contenus, soum):
    p, a = agent(contenus)
    try:
        r = asyncio.run(rediger_note_flash(EV_FDA, ticker_id="RVMD", cik=1628171, emetteur=RVMD,
                                           fichier=fichier, agent=a, soumission=soum,
                                           precedentes=[], precedent_resultats=None))
        return p, r
    except (NoteFlashRefusee, NoteFlashImpossible) as e:
        return p, f"{type(e).__name__} : {e}"
    except Exception as e:  # noqa: BLE001
        return p, f"LÈVE : {e!r}"


p1, r1 = rediger([BON], soumission("0001193125-26-366931"))
b.check(not isinstance(r1, str) and r1.note.types == ("reglementaire_favorable",) and p1.appels == 1
        and r1.catalogue_version == fichier.types_evenement_version
        and r1.catalogue_version != fichier.schema_version and r1.modele == "fake-model"
        and r1.documents and r1.documents[0]["type"] == "8-K",
        f"une lecture juste : 1 appel, note validée, version du catalogue et documents lus notés → "
        f"{r1 if isinstance(r1, str) else r1.note.types}")
p2, r2 = rediger([PARAPHRASE, BON], soumission("0001193125-26-366931"))
b.check(not isinstance(r2, str) and p2.appels == 2 and len(r2.runs) == 2,
        "une citation refusée est renvoyée UNE fois au modèle, qui corrige")
p3, r3 = rediger([PARAPHRASE, PARAPHRASE], soumission("0001193125-26-366931"))
b.check(isinstance(r3, str) and r3.startswith("NoteFlashRefusee") and p3.appels == 2,
        f"deux refus ⟹ la note est refusée, rien n'est rendu → {str(r3)[:80]}")
p4, r4 = rediger([BON], "<SEC-DOCUMENT><DOCUMENT><TYPE>EX-101.SCH<TEXT>x</TEXT></DOCUMENT>")
b.check(isinstance(r4, str) and r4.startswith("NoteFlashImpossible") and p4.appels == 0,
        "un dépôt sans document lisible est refusé AVANT tout appel modèle")

print("§9 le rappel (#125)")
EV_TIRAGE = MaterialEvent(form="8-K", event_date=date(2026, 10, 8), filing_date=date(2026, 10, 13),
                          items=("2.03", "8.01"), accession="0001628171-26-000004")
d_tir = extraire_documents(soumission("0001628171-26-000004"))
b.require(d_tir, 1, "RVMD 08/10 (réel) : le seul formulaire est lu")
# La note RÉELLE de l'approbation du 26/08 (#504), telle que `qualifications_de_l_emetteur` la relit.
NOTE_FDA = {"accession": EV_FDA.accession, "catalogue_version": CUR, "lisible": True,
            "types": ["reglementaire_favorable"], "motif": None, "redigee_le": LE,
            "event_date": date(2026, 8, 26),
            "elements": [{"type": "reglementaire_favorable", "passage": PASS_FDA}]}
q_fda = relire_note(NOTE_FDA, fichier)
b.check(q_fda.date_evenement == date(2026, 8, 26)
        and q_fda.types_annonces == frozenset({"reglementaire_favorable"}),
        "une note relue porte la date de son événement et les types qu'elle ANNONCE")
precs = precedentes_de({EV_FDA.accession: q_fda}, EV_TIRAGE)
b.require(precs, 1, "la note du 26/08 est une précédente du dépôt du 08/10")
b.check(precedentes_de({EV_FDA.accession: q_fda}, EV_FDA) == []
        and precedentes_de({"autre": replace_q(q_fda, date(2026, 10, 9))}, EV_TIRAGE) == [],
        "ni la note du dépôt lu ni une note POSTÉRIEURE ne sont des précédentes")
ctx_t = contexte_note_flash(EV_TIRAGE, RVMD, d_tir, fichier, precedentes=precs)
b.check([n["date_evenement"] for n in ctx_t["notes_precedentes"]] == ["2026-08-26"]
        and ctx_t["notes_precedentes"][0]["types"] == ["reglementaire_favorable"]
        and "RASONQUE" in ctx_t["notes_precedentes"][0]["note"],
        "le modèle VOIT les notes précédentes : date, types annoncés, extrait")
b.check("portee" not in repr(ctx_t["notes_precedentes"]),
        "les notes précédentes ne montrent pas la portée (aucun levier sur l'exigence)")

PASS_TIRAGE = ("the Lender advanced the Tranche A Loan in an aggregate principal amount of $250.0 "
               "million")
PASS_RAPPEL = ("in connection with the U.S. Food and Drug Administration’s (the “FDA”) approval of "
               "RASONQUE™ (daraxonrasib)")


def pont_t(elements, precedentes=precs):
    s_ = sortie(lisible=True, elements=elements)
    if isinstance(s_, str):
        return s_
    try:
        return valider_note(s_, d_tir, fichier, event_date=EV_TIRAGE.event_date, precedentes=precedentes, cloture_publiee=None, reference_precedente=[], phrases=[])
    except NoteFlashRefusee as e:
        return f"REFUSÉ : {e}"


FIN_EL = {"type": "financement", "passage": PASS_TIRAGE}
v_ok = pont_t([FIN_EL, {"type": "reglementaire_favorable", "passage": PASS_RAPPEL,
                        "rappel_du": "2026-08-26"}])
el_r = v_ok.elements[1] if not isinstance(v_ok, str) else {}
b.check(not isinstance(v_ok, str) and el_r.get("rappel_admis") is True,
        f"un rappel qui retrouve sa note (type ET date) est ADMIS → {v_ok if isinstance(v_ok, str) else el_r}")
b.check(not isinstance(v_ok, str) and v_ok.types == ("financement", "reglementaire_favorable"),
        "les types PERSISTÉS restent ceux de l'ordre 0 (le rappel y figure)")
for lab, el, motif in [
    ("une date sans note", {"rappel_du": "2026-08-25"}, "aucune note antérieure"),
    ("un autre type à la bonne date", {"type": "accord_commercial"}, "aucune note antérieure"),
    ("une date non antérieure", {"rappel_du": "2026-10-08"}, "pas antérieur"),
]:
    e_ = {"type": "reglementaire_favorable", "passage": PASS_RAPPEL, "rappel_du": "2026-08-26", **el}
    v_ = pont_t([FIN_EL, e_])
    r_ = v_.elements[1] if not isinstance(v_, str) else {}
    b.check(not isinstance(v_, str) and r_.get("rappel_admis") is False
            and motif in r_.get("rappel_motif", "") and "nouveau" in r_.get("rappel_motif", ""),
            f"rappel REFUSÉ ({lab}) : l'élément compte comme NOUVEAU, motif nommé → {r_}")
v_sans = pont_t([FIN_EL, {"type": "reglementaire_favorable", "passage": PASS_RAPPEL,
                          "rappel_du": "2026-08-26"}], precedentes=[])
b.check(not isinstance(v_sans, str) and v_sans.elements[1].get("rappel_admis") is False,
        "sans note précédente, aucun rappel n'est admis")
b.check(verdict_rappel("reglementaire_favorable", date(2026, 8, 26), event_date=date(2026, 10, 8),
                       precedentes=precs)[0] is True
        and verdict_rappel("reglementaire_favorable", date(2026, 8, 26), event_date=date(2026, 8, 26),
                           precedentes=precs)[0] is False,
        "le verdict du rappel : admis contre une note antérieure, refusé le jour même")


def note_de(v):
    return {"accession": EV_TIRAGE.accession, "catalogue_version": CUR, "lisible": True,
            "types": list(v.types), "elements": v.elements, "motif": None, "redigee_le": LE,
            "event_date": EV_TIRAGE.event_date}


ON = fichier
OFF = fichier.model_copy(update={"rappels_ecartes": False})
b.check(ON.rappels_ecartes is True, "l'interrupteur du référentiel réel est ACTIF (ordre 1)")
lu_on = relire_note(note_de(v_ok), ON)
lu_off = relire_note(note_de(v_ok), OFF)
b.check(lu_on.types == frozenset({"financement"}) and "rappel(s) écarté(s)" in lu_on.resume
        and "2026-08-26" in lu_on.resume,
        f"interrupteur ON : le rappel admis ne rouvre rien, et c'est DIT → {lu_on.types} {lu_on.resume!r}")
b.check(lu_off.types == frozenset({"financement", "reglementaire_favorable"})
        and "écarté" not in lu_off.resume,
        f"interrupteur OFF : l'ordre 0 EXACT, sans relecture → {lu_off.types}")
b.check(lu_on.types_annonces == lu_off.types_annonces == frozenset({"financement"}),
        "les types ANNONCÉS ne dépendent pas de l'interrupteur (ils servent à vérifier les rappels suivants)")
v_ref = pont_t([FIN_EL, {"type": "reglementaire_favorable", "passage": PASS_RAPPEL,
                         "rappel_du": "2026-08-25"}])
b.check(relire_note(note_de(v_ref), ON).types == frozenset({"financement", "reglementaire_favorable"}),
        "un rappel REFUSÉ rouvre comme un fait nouveau, même interrupteur ON (dans le doute on rouvre)")
v_seul = pont_t([{"type": "reglementaire_favorable", "passage": PASS_RAPPEL, "rappel_du": "2026-08-26"}])
b.check(relire_note(note_de(v_seul), ON).types == frozenset({"routine"})
        and relire_note(note_de(v_seul), OFF).types == frozenset({"reglementaire_favorable"}),
        "une note faite que de rappels se lit `routine` (ON), jamais un ensemble vide ; OFF : l'ordre 0")
b.check(types_annonces([{"type": "surprise", "cause": "non_dite", "passage": "x"}])
        == frozenset({"surprise_concurrence"}),
        "les types annoncés sont DÉRIVÉS par le détenteur unique (Q2 tient sur un élément persisté)")

# Interrupteur coupé : le modèle ne voit PAS l'historique (le voir peut faire omettre un type, #521).
_vus: list = []


async def _espion(agent_, messages, *a, **k):
    _vus.append(messages[0]["content"])
    raise NoteFlashRefusee("espion : on n'a besoin que du message")


def _message_vu(fich):
    import app.agents.v2.note_flash as _nf
    vrai = _nf.run_json_agent
    _nf.run_json_agent = _espion
    _vus.clear()
    try:
        asyncio.run(rediger_note_flash(EV_TIRAGE, ticker_id="RVMD", cik=1628171, emetteur=RVMD,
                                       fichier=fich, agent=agent([])[1],
                                       soumission=soumission("0001628171-26-000004"),
                                       precedentes=precs, precedent_resultats=None))
    except Exception:  # noqa: BLE001
        pass
    finally:
        _nf.run_json_agent = vrai
    return _vus[0] if _vus else ""


m_on, m_off = _message_vu(ON), _message_vu(OFF)
b.check("2026-08-26" in m_on and "2026-08-26" not in m_off and '"notes_precedentes": []' in m_off,
        "interrupteur OFF : le modèle ne voit PAS l'historique (ON : il le voit)")


print("§10 le communiqué de résultats : phrases relevées, référence, date lue, vote (diagnostic §13)")
import app.agents.v2.note_flash as NF  # noqa: E402
from app.knowledge.citation import normaliser as _norm  # noqa: E402

RES_AOUT = MaterialEvent(form="8-K", event_date=date(2026, 8, 5), filing_date=date(2026, 8, 5),
                         items=("2.02", "9.01"), accession="0001193125-26-335039",
                         periode_publiee=date(2026, 6, 30))
d_aout = extraire_documents(soumission("0001193125-26-335039"))
d_mai = extraire_documents(soumission("0001193125-26-208918"))
ph = NF.phrases_a_examiner(d_aout)
ref_mai = NF.extraits_de_prevision(d_mai)
b.check(any("In May 2026, the company received a $250.0 million payment" in p for p in ph)
        and any("updating its full year 2026 GAAP operating expense guidance" in p for p in ph),
        f"RVMD 05/08 : le CODE relève la tranche de mai et la révision de prévision ({len(ph)} phrases)")
N_ROY = next((i for i, p in enumerate(ph, 1) if "In May 2026, the company received" in p), 1)
N_GUI = next((i for i, p in enumerate(ph, 1) if "updating its full year 2026 GAAP operating expense" in p), 1)
N_COL = next((i for i, p in enumerate(ph, 1) if p.startswith("Clinical Collaborations")), 1)
REF = ("Revolution Medicines is updating its full year 2026 GAAP operating expenses guidance to a range of "
       "$1.7 to $1.8 billion")
b.check(_norm(REF) in _norm("\n".join(ref_mai)),
        "les prévisions du communiqué PRÉCÉDENT (06/05) portent la fourchette de mai (1,7-1,8 Md$)")
b.check(NF.date_du_passage("In May 2026, the company received") == date(2026, 5, 1)
        and NF.date_du_passage("On May 18, 2026, the Board approved, and in June 2026 it") == date(2026, 6, 1)
        and NF.date_du_passage("the company remains well capitalized") is None,
        "la date écrite dans une phrase se LIT (jour, mois, la plus tardive), sinon aucune")

ITEM = ("On August 5, 2026, Revolution Medicines, Inc. (the “Company”) announced its financial results "
        "for the quarter ended June 30, 2026.")


def examen(**surcharges):
    v = {n: {"n": n, "type": None} for n in range(1, len(ph) + 1)}
    for n, x in surcharges.items():
        v[int(n[1:])] = {"n": int(n[1:]), **x}
    return list(v.values())


def pont_r(ex, refs=None):
    try:
        s_ = NoteFlashSortie.model_validate({"lisible": True, "examen": ex,
                                             "elements": [{"type": "resultats", "passage": ITEM}]})
        return valider_note(s_, d_aout, fichier, event_date=RES_AOUT.event_date, precedentes=[],
                            cloture_publiee=RES_AOUT.periode_publiee,
                            reference_precedente=ref_mai if refs is None else refs, phrases=ph)
    except Exception as e:  # noqa: BLE001 — un refus est un FAIL nommé, pas la mort du script
        return f"REFUS {e}"


SUR = {"type": "surprise", "cause": "non_dite", "passage_reference": REF, "periode_prevue": "full year 2026",
       "chiffre_revise": "depenses_exploitation", "sens": "hausse"}
v_ok = pont_r(examen(**{f"n{N_ROY}": {"type": "financement"}, f"n{N_GUI}": SUR,
                        f"n{N_COL}": {"type": "accord_commercial"}}))
els = {e["passage"][:30]: e for e in getattr(v_ok, "elements", [])}
roy = next((e for e in getattr(v_ok, "elements", []) if "Royalty" in e["passage"]), {})
gui = next((e for e in getattr(v_ok, "elements", []) if "updating its full year" in e["passage"]), {})
col = next((e for e in getattr(v_ok, "elements", []) if e["passage"].startswith("Clinical Collab")), {})
b.check(not isinstance(v_ok, str) and roy.get("couvert_par_les_comptes") is True
        and roy.get("survenu_le") == "2026-05-01" and roy.get("survenu_le_source") == "lue dans la phrase",
        f"la tranche de MAI (date lue) est couverte par les comptes du 30/06 → {roy or v_ok}")
b.check(gui.get("survenu_le") == "2026-08-05" and not gui.get("couvert_par_les_comptes")
        and not gui.get("ecart_non_etabli"),
        f"la RÉVISION établie (référence de mai, même période) est datée du communiqué et compte → {gui}")
b.check(col.get("couvert_par_les_comptes") is True and col.get("survenu_le_source") == "récapitulatif de la période",
        f"un fait NON daté d'un communiqué de résultats appartient à la période publiée → {col}")
b.check(not isinstance(v_ok, str) and "surprise_concurrence" not in v_ok.types
        and NF.types_annonces(v_ok.elements) == frozenset({"resultats", "surprise_allocation", "surprise_execution"}),
        f"types annoncés : résultats + la révision de dépenses (causes probables allocation, exécution — "
        f"jamais la concurrence) → {getattr(v_ok, 'types', v_ok)}")

v_sans = pont_r(examen(**{f"n{N_GUI}": {k: v for k, v in SUR.items() if k != "passage_reference"}}))
g2 = next((e for e in getattr(v_sans, "elements", []) if "updating" in e["passage"]), {})
b.check("aucune référence" in (g2.get("ecart_non_etabli") or "")
        and not any(t.startswith("surprise_") for t in getattr(v_sans, "types", ("?",))),
        f"une prévision SANS référence n'est pas un écart : gardée, motif écrit, ne compte pas → {g2}")
v_per = pont_r(examen(**{f"n{N_GUI}": {**SUR, "periode_prevue": "second quarter of 2026"}}))
g3 = next((e for e in getattr(v_per, "elements", []) if "updating" in e["passage"]), {})
b.check("période visée" in (g3.get("ecart_non_etabli") or ""),
        f"deux prévisions de périodes différentes ne font pas une révision → {g3.get('ecart_non_etabli')}")
v_gen = pont_r(examen(**{f"n{N_GUI}": {**SUR, "periode_prevue": "the company"}}))
g5 = next((e for e in getattr(v_gen, "elements", []) if "updating" in e["passage"]), {})
b.check("non datée" in (g5.get("ecart_non_etabli") or ""),
        f"une période GÉNÉRIQUE (sans année) n'établit rien — MSFT #580 passait avec « the quarter » → "
        f"{g5.get('ecart_non_etabli')}")
v_ref = pont_r(examen(**{f"n{N_GUI}": SUR}), refs=[])
g4 = next((e for e in getattr(v_ref, "elements", []) if "updating" in e["passage"]), {})
b.check("introuvable" in (g4.get("ecart_non_etabli") or ""),
        "une référence absente du dépôt ET des prévisions précédentes n'établit rien (jamais la mémoire du modèle)")
v_manque = pont_r(examen()[:-2])
b.check(isinstance(v_manque, str) and "aucun verdict" in v_manque,
        f"une phrase relevée SANS verdict fait refuser la note (aucune omission possible) → {str(v_manque)[:120]}")
v_dbl = pont_r(examen() + [{"n": 1, "type": None}])
b.check(isinstance(v_dbl, str) and "double" in v_dbl, "une phrase jugée deux fois fait refuser la note")

# Marqueur d'après-clôture (forme minimale construite : la règle, pas un dépôt)
DOC_M = [NF.DocumentDepot(type="EX-99.1", nom="x", texte=(
    "Subsequent to quarter end, the company entered into a definitive agreement to acquire Example Corp. "
    "The company remains focused on its pipeline."), taille=0, tronque=False)]
ph_m = NF.phrases_a_examiner(DOC_M)
try:
    v_m = valider_note(NoteFlashSortie.model_validate({"lisible": True, "elements": [
        {"type": "resultats", "passage": "Subsequent to quarter end, the company entered into a definitive agreement"}],
        "examen": [{"n": 1, "type": "perimetre"}]}), DOC_M, fichier, event_date=date(2026, 8, 5),
        precedentes=[], cloture_publiee=date(2026, 6, 30), reference_precedente=[], phrases=ph_m)
    e_m = next(e for e in v_m.elements if e["type"] == "perimetre")
except Exception as e:  # noqa: BLE001
    e_m = {"erreur": repr(e)}
b.check(len(ph_m) == 1 and e_m.get("survenu_le") == "2026-08-05" and not e_m.get("couvert_par_les_comptes")
        and e_m.get("survenu_le_source") == "marqueur d'après-clôture",
        f"« subsequent to quarter end » : le fait est postérieur à la clôture, il compte → {e_m}")

# Le vote
def _nv(types_):
    return NF.NoteValidee(lisible=True, types=tuple(sorted(types_)), motif=None,
                          elements=[{"type": t, "passage": "x" * 30} for t in types_])
lect = [_nv({"resultats"}), _nv({"resultats", "financement"}), _nv({"resultats", "financement"})]
choisie, vote = NF.voter_lectures(lect)
b.check(set(choisie.types) == {"resultats", "financement"} and "2/3" in vote and "n°2" in vote,
        f"le vote garde la PREMIÈRE lecture dont les types sont la majorité → {vote}")
choisie2, vote2 = NF.voter_lectures([_nv({"resultats", "perimetre"}), _nv({"resultats", "financement"}),
                                      _nv({"resultats", "gouvernance"})])
b.check(set(choisie2.types) == {"resultats", "perimetre"} and "0/3" in vote2 and "n°1" in vote2,
        f"sans lecture exactement majoritaire, celle qui s'en écarte le moins, la première à égalité → {vote2}")
choisie3, vote3 = NF.voter_lectures([_nv({"resultats"}), _nv({"resultats"}), _nv({"resultats", "perimetre"})])
b.check(set(choisie3.types) == {"resultats"} and "n°1" in vote3,
        f"un type annoncé par UNE lecture sur trois ne passe pas : majorité stricte, jamais l'union → {vote3}")
b.check(NF.LECTURES_PAR_COMMUNIQUE_DE_RESULTATS == 3, "trois lectures par communiqué de résultats")

# La relecture : le fait couvert est écarté sous l'interrupteur, compté sans lui
row = {"types": ["financement", "resultats"], "lisible": True, "event_date": date(2026, 8, 5),
       "redigee_le": datetime(2026, 10, 16, tzinfo=timezone.utc), "catalogue_version": fichier.types_evenement_version,
       "elements": [{"type": "resultats", "passage": ITEM},
                    {"type": "financement", "passage": "In May 2026, the company received a $250.0 million payment",
                     "survenu_le": "2026-05-01", "couvert_par_les_comptes": True}]}
lu_on = NF.relire_note(row, fichier)
lu_off = NF.relire_note(row, fichier.model_copy(update={"fraicheur_par_duree_de_vie": False}))
b.check(lu_on.types == frozenset({"resultats"}) and "couvert(s) par les comptes" in lu_on.resume,
        f"relue (interrupteur actif) : la tranche de mai est écartée, et c'est DIT → {lu_on.types} {lu_on.resume[-80:]}")
b.check(lu_off.types == frozenset({"financement", "resultats"}),
        f"interrupteur coupé : ordre 0, tout type cité compte → {lu_off.types}")


print("§11 la révision sans cause dite : ses causes probables (table, catalogue 1.6.0)")
from app.contracts.note_flash_schema import ElementNoteFlash, types_de_l_element  # noqa: E402

PH_GUI = ph[N_GUI - 1] if len(ph) >= N_GUI else ""   # accès TOLÉRANT : sous mutation, un FAIL nommé
b.check("operating expense guidance" in PH_GUI and "$2.1 to $2.2 billion" in PH_GUI,
        f"la phrase RÉELLE de la révision RVMD du 05/08 (2,1-2,2 Md$) → « {PH_GUI[:120]}… »")


def rev(**kw):
    """`causes_de_la_revision` sur un élément ; un refus du contrat est une VALEUR (FAIL nommé)."""
    try:
        el = ElementNoteFlash.model_validate({"type": "surprise", "cause": "non_dite", **kw})
        return NF.causes_de_la_revision(el, fichier)
    except Exception as e:  # noqa: BLE001
        return (("REFUS",), (), repr(e))


# Toute la table, dans le sens VÉRIFIÉ (hausse : la décision réglementaire ne s'y ajoute pas).
TOUTE = ("surprise_allocation", "surprise_concurrence", "surprise_execution", "surprise_secteur")
r_ok = rev(passage=PH_GUI, passage_reference=REF, periode_prevue="full year 2026",
           chiffre_revise="depenses_exploitation", sens="hausse")
b.check(r_ok[0] == ("surprise_allocation", "surprise_execution") and r_ok[1] == ("allocation", "execution")
        and "lu dans la phrase" in r_ok[2] and "vérifié dans les montants" in r_ok[2],
        f"RVMD 05/08 : dépenses (lues dans la phrase) en HAUSSE (1,75 → 2,15 Md$, vérifiée) ⟹ allocation + "
        f"exécution, PAS la concurrence → {r_ok}")
r_cnd = rev(passage=PH_GUI, passage_reference=REF, periode_prevue="full year 2026",
            chiffre_revise="chiffre_affaires", sens="hausse")
b.check(r_cnd[0] == TOUTE and "introuvable dans la phrase" in r_cnd[2],
        f"un chiffre déclaré que la phrase ne NOMME pas (chiffre d'affaires sur une phrase de dépenses) ⟹ toute "
        f"la table → {r_cnd[0]} / {r_cnd[2][:90]}")
r_abs = rev(passage=PH_GUI, passage_reference=REF, periode_prevue="full year 2026", sens="hausse")
b.check(r_abs[0] == TOUTE and "non déclaré" in r_abs[2],
        f"un chiffre NON déclaré ⟹ toute la table (côté prudent) → {r_abs[0]}")
r_hors = rev(passage=PH_GUI, passage_reference=REF, periode_prevue="full year 2026",
             chiffre_revise="carnet_de_commandes", sens="hausse")
b.check(r_hors[0] == TOUTE and "hors de la table" in r_hors[2],
        f"un chiffre HORS de la table ⟹ toute la table → {r_hors[0]}")

# Le sens : une forme minimale construite (la règle, pas un dépôt) — sur le chiffre d'affaires, le seul
# chiffre de la table dont les deux sens ne rouvrent pas la même chose.
CA_NEUF = "The company now expects full year 2026 revenue of $900 million to $950 million."
CA_ANCIEN = "The company expects full year 2026 revenue of $1.0 billion to $1.1 billion."
CA_HAUT = "The company now expects full year 2026 revenue of $1.2 billion to $1.3 billion."
r_b = rev(passage=CA_NEUF, passage_reference=CA_ANCIEN, periode_prevue="full year 2026",
          chiffre_revise="chiffre_affaires", sens="baisse")
r_h = rev(passage=CA_HAUT, passage_reference=CA_ANCIEN, periode_prevue="full year 2026",
          chiffre_revise="chiffre_affaires", sens="hausse")
r_x = rev(passage=CA_NEUF, passage_reference=CA_ANCIEN, periode_prevue="full year 2026",
          chiffre_revise="chiffre_affaires", sens="hausse")
r_n = rev(passage=CA_HAUT, chiffre_revise="chiffre_affaires", sens="hausse")
b.check("reglementaire_defavorable" in r_b[0] and "vérifié" in r_b[2],
        f"chiffre d'affaires en BAISSE vérifiée (1,05 Md$ → 925 M$) ⟹ la décision réglementaire s'ajoute → {r_b}")
b.check(r_h[0] == ("surprise_concurrence", "surprise_execution", "surprise_secteur") and "vérifié" in r_h[2],
        f"chiffre d'affaires en HAUSSE vérifiée ⟹ secteur, concurrence, exécution, sans le réglementaire → {r_h}")
b.check("reglementaire_defavorable" in r_x[0] and "contredit" in r_x[2],
        f"un sens déclaré que les montants CONTREDISENT ⟹ les deux sens (côté prudent) → {r_x[2][:120]}")
b.check("reglementaire_defavorable" in r_n[0] and "invérifiable" in r_n[2],
        f"sans prévision précédente citée (un 8-K d'avertissement), le sens ne se vérifie pas ⟹ les deux sens → "
        f"{r_n[2][:120]}")
b.check(NF.sens_lu(PH_GUI, "guidance to a range of $1.7 to $1.8", "full year 2026")[0] is None,
        "deux montants d'échelles différentes (Md$ contre un nombre nu) ne se comparent pas")
DEUX = ("The company now expects full year 2026 revenue of $1.2 billion and operating expenses of "
        "$800 million.")
r_2 = rev(passage=DEUX, passage_reference=CA_ANCIEN, periode_prevue="full year 2026",
          chiffre_revise="chiffre_affaires", sens="hausse")
b.check(set(r_2[1]) == {"allocation", "concurrence", "execution", "secteur"} and "nomme aussi" in r_2[2],
        f"une phrase qui nomme DEUX chiffres : leurs causes s'ajoutent → {r_2[1]} / {r_2[2][:100]}")

_noms = lambda t: [c.id for c in NF.chiffres_nommes(t, fichier)]  # noqa: E731
b.check(_noms("We expect to reach profitability in 2027.") == []
        and _noms("Net losses widened; R&D expenses rose.") == ["depenses_exploitation", "resultat"],
        f"un terme se lit en MOT ENTIER (« profitability » n'est pas « profit »), pluriel admis → "
        f"{_noms('We expect to reach profitability in 2027.')} / {_noms('Net losses widened; R&D expenses rose.')}")

# Ce que la note PERSISTE, et ce qu'un élément persisté rouvre.
b.check(gui.get("types_derives") == ["surprise_allocation", "surprise_execution"]
        and gui.get("causes_probables") == ["allocation", "execution"] and gui.get("revision_motif"),
        f"l'élément PERSISTÉ porte les types dérivés, les causes et le motif écrit → {gui.get('revision_motif')}")
b.check(types_de_l_element({"type": "surprise", "cause": "non_dite"}) == frozenset({"surprise_concurrence"}),
        "un élément persisté AVANT la table (sans types dérivés) garde la règle Q2 jusqu'à sa relecture")
b.check(types_de_l_element({"type": "surprise", "cause": "allocation"}) == frozenset({"surprise_allocation"}),
        "une cause DITE `allocation` ⟹ `surprise_allocation`")
b.check(refuse(sortie(lisible=True, elements=[{"type": "resultats", "passage": PASS_FDA,
                                                "chiffre_revise": "marge"}]), "n'ont de sens que"),
        "un chiffre révisé hors d'un écart aux attentes est refusé")
b.check(refuse(sortie(lisible=True, elements=[{"type": "surprise", "passage": PASS_FDA,
                                                "cause": "allocation"}]), "passage_cause"),
        "une cause `allocation` DITE se prouve par le passage qui la dit")

# Ce que le modèle voit de la table : les chiffres, jamais leurs causes (#59).
_ctx11 = contexte_note_flash(RES_AOUT, RVMD, d_aout, fichier, precedentes=[])
_vus11 = _ctx11.get("chiffres_revisables", [])
b.check(len(_vus11) == len(fichier.revisions_de_prevision) and all(set(c) == {"id", "libelle"} for c in _vus11),
        f"le modèle voit les chiffres révisables par identifiant et libellé, JAMAIS leurs causes ni leurs termes → "
        f"{[c.get('id') for c in _vus11]}")
_sur = next((t for t in _ctx11["types_evenement"] if t["id"] == "surprise"), {})
b.check("`allocation`" in _sur.get("libelle", "") and "`chiffre_revise`" in _sur.get("libelle", ""),
        "le libellé de l'écart propose la cause `allocation` et demande le chiffre révisé")

sys.exit(b.summary())
