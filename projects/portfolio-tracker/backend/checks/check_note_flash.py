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
    rediger_note_flash, relire_note, types_proposables, valider_note)
from app.contracts.note_flash_schema import NoteFlashSortie, type_derive  # noqa: E402
from app.knowledge.edgar_feed import IdentiteEmetteur  # noqa: E402
from app.knowledge.evenements import A_QUALIFIER, QualificationLue  # noqa: E402
from app.knowledge.material_events import MaterialEvent, MaterialEventLookup  # noqa: E402

b = Bilan()
FIX = Path(__file__).resolve().parent / "fixtures" / "note_flash"
fichier = load_frameworks()
RVMD = IdentiteEmetteur(symbole="RVMD", cik=1628171, raison_sociale="Revolution Medicines, Inc.")


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
b.check(len(d_msft) == 2 and d_msft[1].tronque and d_msft[1].taille > len(d_msft[1].texte),
        "MSFT 02/09 : la présentation dépasse le budget, la troncature est DITE")
b.check([d.type for d in d_fin] == ["8-K"],
        f"RVMD 14/04 : l'avis juridique EX-5.1 et le XBRL ne sont pas lus → {[d.type for d in d_fin]}")
b.check(sum(len(d.texte) for d in d_msft) <= 45_000, "le budget total est tenu")
b.check(extraire_documents("") == [] and extraire_documents("<SEC-DOCUMENT></SEC-DOCUMENT>") == [],
        "une soumission vide ne produit aucun document (jamais une exception)")

print("§4 ce que le modèle voit")
EV_FDA = MaterialEvent(form="8-K", event_date=date(2026, 8, 26), filing_date=date(2026, 8, 26),
                       items=("8.01",), accession="0001193125-26-366931")
ctx = contexte_note_flash(EV_FDA, RVMD, d_fda, fichier)
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
        return valider_note(s, d_fda, fichier)
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
b.check(refuse(pont(lisible=True, elements=[{"type": "surprise", "passage": cite_normalisee,
                                             "cause": "secteur",
                                             "passage_cause": "demand weakened across the whole "
                                                              "industry this quarter"}]),
               "passage_cause"), "une cause citée à faux est refusée")
v2 = pont(lisible=True, elements=[{"type": "surprise", "passage": cite_normalisee, "cause": "non_dite"},
                                  {"type": "reglementaire_favorable", "passage": cite_normalisee}])
b.check(not isinstance(v2, str) and v2.types == ("reglementaire_favorable", "surprise_concurrence"),
        f"les types retenus sont ceux que le CODE dérive → {v2 if isinstance(v2, str) else v2.types}")
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
                                           fichier=fichier, agent=a, soumission=soum))
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

sys.exit(b.summary())
