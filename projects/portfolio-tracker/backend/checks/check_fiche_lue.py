"""L'ancien code lit la FICHE de l'émetteur (module M1) — acceptation A15 de `M1-fiche-emetteur.md`.

Remplace `check_source_registry.py` (capacité 2, convention #52) : le registre nominatif des sources
et les listes de domaines de `websearch` ont été repris dans la fiche et son journal des sources, et
`knowledge/fiche_emetteur.py` est le seul lecteur de la fiche dans l'ancien code. Ce que la capacité 2
garantissait doit TENIR à travers la fiche ; ce check le prouve sur les fiches RÉELLES (la reprise
importée en production, `_fiches_reprise`), sans base ni réseau ni modèle.

  [F1] ATTEIGNABILITÉ (#32) — une source admise pour la spécialité atteint le plancher B des trois
       champs desserrés, et la porte de complétude applique ce plancher (doctrine = porte).
  [F2] STANDING PAR COUPLE (source × nature) — une source admise pour l'interprétation ne gagne
       AUCUN standing sur une mesure, même si le modèle déclare une autre nature.
  [F3] SOURCE HORS FICHE — reste `web_search_generic`, 0,50 / C+.
  [F4] JAMAIS DE DÉMOTION (#33) — dépôts officiels, pages investisseurs, presse : intacts, et le
       plafond affiché est le même.
  [F5] PORTÉE — un émetteur sans la spécialité, ou sans fiche, n'hérite de rien ; un sous-domaine
       hérite de la source admise, un domaine qui la contient seulement, non.
  [F6] DÉTENTEUR UNIQUE (#46) — les deux sites qui qualifient une entrée appellent
       `fiche_emetteur.qualifier` ; seul cet adaptateur lit le module ; aucune liste de domaines ne
       survit dans l'ancien code.
  [F7] PLAFOND ≠ QUALIFICATION — le générique ignore une admission bornée à une nature, le plafond
       l'applique ; replier l'un dans l'autre ferait traverser la qualification sans condition de
       nature.
  [F8] TRADUCTION — chaque critère du référentiel et chaque genre de lieu se traduit en un
       `source_type` dont le tier est celui de l'admission ; un critère inconnu LÈVE.
"""
from __future__ import annotations

import inspect
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _fiches_reprise import fiche  # noqa: E402
from _harness import Bilan  # noqa: E402

from app.agents.v2 import worker as worker_mod  # noqa: E402
from app.agents.v2.common import FIELD_PROFILES  # noqa: E402
from app.agents.v2.curator import _plancher_for  # noqa: E402
from app.knowledge import fiche_emetteur as F  # noqa: E402
from app.knowledge import service as service_mod  # noqa: E402
from app.knowledge import websearch as websearch_mod  # noqa: E402
from app.knowledge.service import RELIABILITY_TABLE, compute_reliability  # noqa: E402
from app.modules.emetteurs import contrat as E  # noqa: E402

b = Bilan()
BACKEND = Path(__file__).resolve().parent.parent
_RANK = {t: i for i, t in enumerate(["C", "C+", "B-", "B", "B+", "A-", "A"])}
_URL_ADMISE = "https://endpts.com/revolution-medicines-rasonque-approval/"
RVMD, NVDA, AAPL = fiche("RVMD"), fiche("NVDA"), fiche("AAPL")


def _q(url, f, entry_type, declaree=None):
    """Le chemin de production : qualification générique, puis la fiche pour la nature de l'entrée."""
    return F.qualifier(source_type=F.source_type_generique(url, f), url=url, fiche=f,
                       entry_type=entry_type, nature_declaree=declaree)


print("[F1] atteignabilité (#32)")
_CHAMPS_DESSERRES = ("positionnement.moat_preuves", "positionnement.position_vs_pairs",
                     "marche.structure_5forces")
_DIM_PLANCHER = {"positionnement": "B+", "marche": "B+"}
specialite = [s for s in RVMD.sources if s.portee.startswith(E.PREFIXE_PORTEE_SPECIALITE)]
b.require(specialite, 4, "[F1] les quatre publications de biotechnologie valent pour RVMD")
st_admise = F.source_type_max(_URL_ADMISE, RVMD)
for champ in _CHAMPS_DESSERRES:
    doctrine = FIELD_PROFILES[champ]["plancher"]
    dim, nom = champ.split(".", 1)
    porte = _plancher_for(dim, nom, _DIM_PLANCHER[dim])
    b.check(doctrine == "B" and porte == doctrine,
            f"[F1] `{champ}` : la porte applique le desserrage à B (doctrine {doctrine}, porte {porte})")
    b.check(_RANK[RELIABILITY_TABLE[st_admise][0]] >= _RANK[doctrine],
            f"[F1] `{champ}` : une source admise atteint son plancher ({st_admise})")

print("[F2] standing par couple (source × nature)")
st_i, nat_i, _ = _q(_URL_ADMISE, RVMD, "analysis")
b.check(nat_i == "interpretation" and st_i == "web_search_reputable",
        f"[F2] source admise + interprétation → promue ({st_i}, {nat_i})")
st_m, nat_m, motif_m = _q(_URL_ADMISE, RVMD, "fact_financial")
b.check(nat_m == "mesure" and st_m == "web_search_generic",
        f"[F2] MÊME source + mesure → aucun standing gagné ({st_m}, {nat_m})")
b.check("pas pour mesure" in motif_m, f"[F2] le refus est DIT dans le motif ({motif_m})")
b.check(compute_reliability(st_m, entry_type="fact_financial")[:2] == (0.50, "C+"),
        "[F2] la mesure reste chiffrée à 0,50 / C+")
st_d, nat_d, _ = _q(_URL_ADMISE, RVMD, "fact_financial", declaree="interpretation")
b.check(nat_d == "mesure" and st_d == "web_search_generic",
        f"[F2] une nature déclarée par le modèle n'achète aucun standing ({st_d}, {nat_d})")

print("[F3] source hors fiche")
st_inc, _, _ = _q("https://un-blog-quelconque.example/analyse", RVMD, "analysis")
b.check(st_inc == "web_search_generic" and RELIABILITY_TABLE[st_inc] == ("C+", 0.50),
        f"[F3] domaine inconnu reste `web_search_generic` 0,50 ({st_inc})")

print("[F4] jamais de démotion (#33)")
for url, attendu, quoi in (
    ("https://www.sec.gov/Archives/edgar/data/x.htm", "edgar_official", "dépôt EDGAR"),
    ("https://ir.revmed.com/news/x", "company_ir_official", "pages investisseurs de l'émetteur"),
    ("https://revmed.com/investors/x", "company_ir_official", "pages investisseurs par chemin"),
    ("https://www.reuters.com/business/x", "financial_press", "presse financière"),
    ("https://www.amf-france.org/x", "regulator_filing_eu", "régulateur européen"),
    ("https://www.gartner.com/x", "web_search_reputable", "cabinet d'études"),
):
    st, _, _ = _q(url, RVMD, "fact_financial")
    b.check(st == attendu, f"[F4] {quoi} : {attendu} conservé ({st})")
    b.check(F.source_type_max(url, RVMD) == attendu, f"[F4] {quoi} : plafond affiché identique")
st_garde, _, _ = F.qualifier(source_type="edgar_official", url="https://blog.example/x", fiche=RVMD,
                             entry_type="fact_financial")
b.check(st_garde == "edgar_official",
        "[F4] une qualification déjà établie par un producteur n'est jamais touchée par la fiche")

print("[F5] portée")
b.check(_q(_URL_ADMISE, NVDA, "analysis")[0] == "web_search_generic",
        "[F5] un émetteur sans la spécialité n'hérite pas de ses sources")
b.check(_q(_URL_ADMISE, AAPL, "analysis")[0] == "web_search_generic"
        and F.source_type_generique("https://www.sec.gov/x", AAPL) == "web_search_generic",
        "[F5] un émetteur sans fiche n'a aucune source admise")
b.check(_q("https://news.endpts.com/x", RVMD, "analysis")[0] == "web_search_reputable",
        "[F5] un sous-domaine hérite de la source admise")
b.check(_q("https://endpts.com.phishing.example/x", RVMD, "analysis")[0] == "web_search_generic",
        "[F5] un domaine qui CONTIENT le nom admis n'hérite pas")
b.check(F.domaines_de_la_societe(RVMD) == ("revmed.com",),
        f"[F5] la recherche d'origine vise le site de la société ({F.domaines_de_la_societe(RVMD)})")

print("[F6] détenteur unique (#46)")
for mod, nom in ((worker_mod, "worker"), (service_mod, "service")):
    src = inspect.getsource(mod)
    b.check("qualifier(" in src, f"[F6] `{nom}` appelle `fiche_emetteur.qualifier`")
b.check("derive_nature(" not in inspect.getsource(service_mod),
        "[F6] `service` ne dérive pas la nature en direct (il passe par `qualifier`)")
lecteurs = sorted(str(p.relative_to(BACKEND)) for p in (BACKEND / "app").rglob("*.py")
                  if "modules" not in p.parts and p.name != "fiche_emetteur.py"
                  and re.search(r"modules\.emetteurs(\.contrat)? import (?!Fiche\b)|modules\.emetteurs import contrat",
                                p.read_text(encoding="utf-8")))
b.check(lecteurs == ["app/api/emetteurs_v2.py"],
        f"[F6] hors l'écran, seul l'adaptateur appelle le module ({lecteurs})")
_LISTES = re.compile(r"\"(sec\.gov|reuters\.com|endpts\.com|gartner\.com|nvidia\.com|revmed\.com|microsoft\.com)\"")
for p in (BACKEND / "app" / "knowledge" / "websearch.py", BACKEND / "app" / "knowledge" / "fiche_emetteur.py",
          BACKEND / "app" / "agents" / "v2" / "worker.py", BACKEND / "app" / "knowledge" / "service.py"):
    trouves = _LISTES.findall(p.read_text(encoding="utf-8"))
    b.check(not trouves, f"[F6] `{p.name}` ne porte aucune liste de domaines ({trouves})")
b.check(not (BACKEND / "app" / "knowledge" / "source_registry.py").exists(),
        "[F6] l'ancien registre est supprimé")

print("[F7] plafond ≠ qualification")
b.check(F.source_type_generique(_URL_ADMISE, RVMD) == "web_search_generic",
        "[F7] le générique ignore une admission bornée à une nature")
b.check(F.source_type_max(_URL_ADMISE, RVMD) == "web_search_reputable",
        "[F7] le plafond applique l'admission (le modèle ne l'écarte pas avant lecture)")
b.check(websearch_mod.classify_source_type(_URL_ADMISE, RVMD) == "web_search_generic"
        and websearch_mod.source_type_max(_URL_ADMISE, RVMD) == "web_search_reputable",
        "[F7] `websearch` rend ces deux qualifications-là, sans rien recalculer")
b.check(F.source_type_generique(None, RVMD) == "llm_memory", "[F7] sans adresse → `llm_memory`")

print("[F8] traduction niveau → source_type")
referentiel = json.loads((BACKEND / "app" / "modules" / "emetteurs" / "referentiel.json").read_text())
for critere in referentiel["criteres"]:
    b.check(critere in F._PAR_CRITERE, f"[F8] le critère `{critere}` du référentiel se traduit")
for genre in referentiel["genres_de_lieu"]:
    b.check(F._PAR_GENRE.get(genre) is not None
            and RELIABILITY_TABLE[F._PAR_GENRE[genre]][0] == referentiel["genres_de_lieu"][genre]["niveau"],
            f"[F8] le lieu `{genre}` se traduit au tier de son niveau")
couples = [(f, s) for f in (RVMD, NVDA, fiche("MSFT")) for s in f.sources]
b.require({s.source for _, s in couples}, 45, "[F8] les sources réelles des trois fiches")
for f_, s in couples:
    q = E.qualifier(f_, "https://" + s.source + "/x", s.natures[0])
    if q.source != s.source:
        continue  # un lieu de la société couvre cette adresse : traduit par son genre (ci-dessus)
    st = F._source_type(f_, q, s.natures[0])
    b.check(RELIABILITY_TABLE[st][0] == s.niveau,
            f"[F8] `{s.source}` ({s.critere}) chez {f_.emetteur} : {st} au tier de l'admission {s.niveau}")
inconnu = E.Fiche(emetteur="ZZ", raison_sociale="Z", sources=(E.SourceAdmise(
    source="x.example", portee="generale", natures=("mesure",), niveau="B", auteur="systeme:essai",
    critere="critere_jamais_ecrit", motif="essai", le="2026-11-16", rang=1),))
try:
    F.source_type_max("https://x.example/y", inconnu)
    b.check(False, "[F8] un critère inconnu de la traduction LÈVE au lieu de prêter un score")
except F.CritereNonTraduit:
    b.check(True, "[F8] un critère inconnu de la traduction LÈVE au lieu de prêter un score")

sys.exit(b.summary())
