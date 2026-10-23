"""Check de la VENTILATION PUBLIÉE (`app/knowledge/ventilation.py` + `ventilation_xbrl.py` +
`ventilation_publiee.yaml`) — hors ligne (lot M2, roadmap V3 `11-lot-M2-ventilation-publiee.md`).

Les fixtures sont COPIÉES DU RÉEL (`checks/fixtures/ventilation/*.xml.gz`, extraites par
`tools/extraire_fixture_ventilation.py` le 2026-10-21 : NVDA 10-K `0001045810-26-000021` et 10-Q
`0001045810-26-000075`, RVMD 10-K `0001193125-26-071563`, JPM 10-K `0001628280-26-008131`). Les
valeurs attendues ci-dessous ont été RELEVÉES contre les dépôts (regex directe sur l'instance XBRL
brute avant filtrage, cf. le rapport du lot) — jamais recalculées par le module qu'on éprouve.

  [V1] NVDA secteurs × chiffre_affaires FY2026 : deux membres, boucle ;
  [V2] NVDA activites : cinq membres de premier niveau (somme = total), emboîtement Data Center ;
  [V3] NVDA geographie : quatre membres, boucle, libellé « United States » ;
  [V4] NVDA secteurs × resultat_exploitation FY2026 : non_ventile, reste exact ;
  [V5] NVDA douze mois glissants (Data Center, activites) au 2026-07-26 ;
  [V6] NVDA clients : part du premier client, base = secteur C&N, aucun raccord ;
  [V7] RVMD : secteur_unique, aucune cellule ;
  [V8] JPM : trois métiers relevés (ÉCART documenté : la spec en annonçait quatre — voir §8bis) ;
  [V9] aucun zéro fabriqué (membre retiré d'une copie de la fixture) ;
  [V10] sous-détail JPM (provision CCB × portefeuille Apple Card) ;
  [V11] idempotence de l'empreinte ;
  [V12] réplicabilité : aucun ticker/CIK/membre propre dans le code et le référentiel livrés ;
  [V13] changement de découpage (activites) : lot P1 tranche B — la VUE SERVIE rend l'axe dans le
        découpage le PLUS RÉCENT (Data Center + Edge Computing), Edge Computing FY2024-FY2026 = Σ des
        quatre anciens marchés, « addition vérifiée » ; les douze mois bouclent (Σ = 302 970 M$) ;
  [V14] emboîtement RENDU (texte) : Compute/Networking indentés sous Data Center, pas au premier niveau ;
  [V15] membres nouveaux PORTENT leur valeur (Hyperscale, AI Clouds, Edge Computing) et l'emboîtement
        de Data Center boucle au cumul du 10-Q ; le relevé brut ne se rend jamais (seule la vue) ;
  [V16] conflits de hiérarchie filtrés aux membres EN USAGE (0 pour NVDA — le réel mesuré).
  [V17] la grandeur d'une part de concentration est celle déposée (créances clients ≠ chiffre d'affaires).
  [V18] signal d'acquisition significative (§4 bis, lot P1) : aucun signal chez NVDA (réel) ; un
        dépôt fictif de regroupement d'entreprises AU-DESSUS du seuil (5 % du CA) produit un signal
        rendu EN TEXTE ; un dépôt fictif SOUS le seuil n'en produit aucun.
  [V19] garde (iv) — l'invariant de l'agrégat SUR LA VUE SERVIE (lot P1 §8 addendum, tranche A),
        cas RÉEL NVDA : dépôt JUMEAU lu (10-Q du 2025-08-27, `tools/extraire_fixture_ventilation.sh
        NVDA 0001045810-25-000209`) ; la vue tient sur `geographie` (douze mois par pays, Σ =
        302 970 M$, la version RETRAITÉE) sans faux refus sur `activites` (Edge Computing au TTM
        : incomplet, pas une erreur). `negatif_ventilation_publiee.sh` rougit cette garde en
        mutant `appariement_feed._choisir_terme` vers la version d'ORIGINE (Σ = 323 559 M$).

Ces quatre assertions répondent à une revue par exécution du coordinateur (2026-10-21) sur
`montrer_ventilation.sh NVDA` : emboîtement non rendu (premier niveau/enfants au même niveau),
redécoupage NVDA (Data Center → Hyperscale/AI Clouds/Edge Computing, Gaming/ProViz/Auto/OEM absents
du 10-Q) lu comme un montant « non ventilé » plutôt qu'un changement de découpage nommé, membres
nouveaux comptés sans leur valeur, conflits de hiérarchie non filtrés (bruit sur des lignes de bilan).

§8bis — ÉCART MESURÉ À LA SPEC (#71 : jamais une panne tue). La spec M2 annonce « JPM : la fonction
pure relève les quatre métiers (CCB, CIB, AWM, Corporate) ». Mesuré sur l'instance XBRL réelle :
JPM ne tague QUE trois membres sur `us-gaap:StatementBusinessSegmentsAxis` (`ConsumerCommunityBanking`,
`CommercialAndInvestmentBank`, `AssetandWealthManagementSegment`) ; le quatrième poste du tableau,
« Corporate », est tagué SEUL sur `srt:ConsolidationItemsAxis = us-gaap:CorporateNonSegmentMember`,
SANS aucun membre de `StatementBusinessSegmentsAxis` — il n'entre donc jamais dans l'axe `secteurs`
du référentiel 1.0.0 (qui ne lit que `StatementBusinessSegmentsAxis`). [V8] teste donc TROIS métiers,
le réel mesuré — garder le chiffre inventé aurait été le défaut inverse de celui que cette spec corrige.
"""
from __future__ import annotations

import copy
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, imports_symbol, strip_code  # noqa: E402

from app.knowledge import ventilation as vt  # noqa: E402
from app.knowledge import ventilation_xbrl as vx  # noqa: E402
from app.knowledge import perimetre as pe  # noqa: E402
from app.knowledge.socle_comptes import (  # noqa: E402
    charger_gabarit, charger_reclassements, reconstituer, structure_du_socle,
)
from app.knowledge.ventilation_feed import publier_ventilation  # noqa: E402

import asyncio  # noqa: E402

b = Bilan()
FIX = Path(__file__).resolve().parent / "fixtures" / "ventilation"
SOCLE_FIX = Path(__file__).resolve().parent / "fixtures" / "socle_comptes"
M = 1e6
GAB = charger_gabarit()
REF = vt.charger_referentiel()


def charger_depot(ticker: str, accn: str) -> vt.Depot:
    manifeste = json.loads((FIX / f"{ticker}_{accn}.json").read_text(encoding="utf-8"))
    inst = gzip.decompress((FIX / f"{ticker}_{accn}_inst.xml.gz").read_bytes())
    lab = gzip.decompress((FIX / f"{ticker}_{accn}_lab.xml.gz").read_bytes())
    defx = gzip.decompress((FIX / f"{ticker}_{accn}_def.xml.gz").read_bytes())
    faits = tuple(vx.lire_instance(inst))
    etiquettes = vx.lire_etiquettes(lab)
    hierarchie, conflits = vx.lire_hierarchie(defx)
    return vt.Depot(accn=accn, form=manifeste["form"], filed=manifeste["filed"], faits=faits,
                    etiquettes=etiquettes, hierarchie=hierarchie, conflits=conflits)


def socle_de(ticker: str, *, reclasse: bool = False):
    d = json.loads((SOCLE_FIX / f"{ticker}.json").read_text(encoding="utf-8"))
    reclassements = charger_reclassements(d["cik"], GAB) if reclasse else ()
    socle = reconstituer(d["faits"], GAB, reclassements=reclassements)
    return d["cik"], structure_du_socle(socle)


def cell(v: vt.Ventilation, axe: str, ligne: str, membre: str, periode: str):
    return next((c for c in v.cellules if c.axe == axe and c.ligne == ligne
                and c.membre == membre and c.periode == periode), None)


class _R:
    """Un raccord de la VUE SERVIE, lu comme un objet (les raccords n'existent qu'à la lecture,
    lot P1 §8 point 2 — le relevé brut n'en porte plus)."""
    def __init__(self, d: dict):
        self.__dict__.update({"parent": None, "membres_manquants": (), **d})

    def __repr__(self) -> str:
        return f"Raccord({self.__dict__})"


def vue_de(v: vt.Ventilation, socle: dict, depots) -> dict:
    return pe.vue_servie(vt.structure_de_ventilation(
        v, version_referentiel=REF.version, version_gabarit=GAB.version, depots=tuple(depots)), socle)


def raccord(vue: dict, axe: str, ligne: str, periode: str, *, niveau="total", parent=None):
    d = next((r for r in vue["raccords"] if r["axe"] == axe and r["ligne"] == ligne and r["periode"] == periode
              and r["niveau"] == niveau and r.get("parent") == parent), None)
    return _R(d) if d is not None else None


def vcell(vue: dict, axe: str, ligne: str, membre: str, periode: str, source: str = "cellules"):
    return next((c for c in vue[source] if c["axe"] == axe and c["ligne"] == ligne
                and c["membre"] == membre and c["periode"] == periode), None)


def proche(a, attendu, tol=0.51 * M) -> bool:
    return a is not None and abs(a - attendu) <= tol


# ── Chargement des dépôts NVDA (10-K + 10-Q), RVMD (10-K), JPM (10-K) ─────────────────────────────
nv10k = charger_depot("NVDA", "0001045810-26-000021")
nv10q = charger_depot("NVDA", "0001045810-26-000075")
rv10k = charger_depot("RVMD", "0001193125-26-071563")
jpm10k = charger_depot("JPM", "0001628280-26-008131")

cik_nv, socle_nv = socle_de("NVDA", reclasse=True)
cik_rv, socle_rv = socle_de("RVMD")
cik_jpm, socle_jpm = socle_de("JPM")

v_nv = vt.relever([nv10k, nv10q], GAB, REF, socle_nv)
v_rv = vt.relever([rv10k], GAB, REF, socle_rv)
v_jpm = vt.relever([jpm10k], GAB, REF, socle_jpm)
vue_nv = vue_de(v_nv, socle_nv, (nv10k, nv10q))

FY26 = "FY2026-01-25"

# ── [V1] NVDA secteurs × chiffre_affaires ────────────────────────────────────────────────────────
print("[V1] NVDA secteurs × chiffre_affaires FY2026")
c1 = cell(v_nv, "secteurs", "chiffre_affaires", "nvda:ComputeAndNetworkingSegmentMember", FY26)
c2 = cell(v_nv, "secteurs", "chiffre_affaires", "nvda:GraphicsSegmentMember", FY26)
b.check(proche(c1.valeur if c1 else None, 193479 * M, 1) and proche(c2.valeur if c2 else None, 22459 * M, 1),
        f"[V1] Compute & Networking 193 479 M$, Graphics 22 459 M$ ({c1 and c1.valeur}, {c2 and c2.valeur})")
r1 = raccord(vue_nv, "secteurs", "chiffre_affaires", FY26)
b.check(r1 is not None and r1.statut == "boucle" and proche(r1.total, 215938 * M, 1),
        f"[V1] le raccord secteurs boucle sur le total publié 215 938 M$ ({r1})")
from app.knowledge.ventilation_feed import _derniers_10k_10q  # noqa: E402
_payload_10kq = {"filings": {"recent": {
    "form": ["10-K", "10-K", "10-Q"],
    "accessionNumber": ["A-ANCIEN", "A-DERNIER", "A-10Q"],
    "filingDate": ["2025-02-20", "2026-02-25", "2026-08-26"],
    "reportDate": ["2025-01-26", "2026-01-25", "2026-07-26"],
}}}
_k10, _q10 = _derniers_10k_10q(_payload_10kq)
b.check(_k10 is not None and _k10["accn"] == "A-DERNIER" and _q10 is not None and _q10["accn"] == "A-10Q",
        f"[V1] le DERNIER 10-K est choisi, jamais un antérieur ({_k10}, {_q10})")

# ── [V2] NVDA activites ──────────────────────────────────────────────────────────────────────────
print("[V2] NVDA activites — cinq membres de premier niveau, emboîtement Data Center")
# Lot P1 tranche B : sans le jumeau, aucun recouvrement entre le 10-K et le 10-Q récent → les cinq
# marchés du 10-K ne sont PAS dans la série de référence (Data Center + Edge Computing) ; ils restent
# tels que publiés dans le découpage ANTÉRIEUR, où leur somme boucle toujours avec le total.
ant_fy26 = [c for c in vue_nv["cellules_anterieures"] if c["axe"] == "activites"
            and c["ligne"] == "chiffre_affaires" and c["periode"] == FY26]
pn_ant = {c["membre"] for c in ant_fy26 if c.get("parent") not in {x["membre"] for x in ant_fy26}}
b.check(len(pn_ant) == 5 and proche(sum(c["v"] for c in ant_fy26 if c["membre"] in pn_ant), 215938 * M, 1),
        f"[V2] cinq membres de premier niveau (découpage antérieur, tel que publié), somme 215 938 M$ ({sorted(pn_ant)})")
dc = cell(v_nv, "activites", "chiffre_affaires", "nvda:DataCenterMember", FY26)
cp = cell(v_nv, "activites", "chiffre_affaires", "nvda:ComputeMember", FY26)
nw = cell(v_nv, "activites", "chiffre_affaires", "nvda:NetworkingMember", FY26)
b.check(bool(dc and cp and nw) and proche(dc.valeur, 193737 * M, 1)
        and proche(cp.valeur, 162361 * M, 1) and proche(nw.valeur, 31376 * M, 1),
        f"[V2] Data Center 193 737 = Compute 162 361 + Networking 31 376 M$")
vue_nv3_tot = None  # (renseignée plus bas, [V13] : la vue avec le jumeau)
emb = raccord(vue_de(v_nv, socle_nv, (nv10k,)), "activites", "chiffre_affaires", FY26, niveau="emboitement",
              parent="nvda:DataCenterMember")
b.check(emb is not None and emb.statut == "boucle", f"[V2] emboîtement Data Center boucle ({emb})")
# premier niveau = membres dont le parent n'est pas lui-même présent à cette période
presents = {c.membre for c in v_nv.cellules
            if c.axe == "activites" and c.ligne == "chiffre_affaires" and c.periode == FY26}
parents = {m: next((cc.parent for cc in v_nv.cellules if cc.membre == m), None) for m in presents}
premier_niveau = {m for m in presents if parents.get(m) not in presents}
b.check("nvda:ComputeMember" not in premier_niveau and "nvda:NetworkingMember" not in premier_niveau,
        f"[V2] Compute et Networking NE SONT PAS au premier niveau ({sorted(premier_niveau)})")

# ── [V3] NVDA geographie ─────────────────────────────────────────────────────────────────────────
print("[V3] NVDA geographie — quatre membres, boucle, libellé United States")
r3 = raccord(vue_nv, "geographie", "chiffre_affaires", FY26)
us = cell(v_nv, "geographie", "chiffre_affaires", "country:US", FY26)
b.require([c for c in v_nv.cellules if c.axe == "geographie" and c.periode == FY26], 4,
          "[V3] quatre membres géographiques")
b.check(r3 is not None and r3.statut == "boucle", f"[V3] boucle avec le total publié ({r3})")
b.check(bool(us) and us.libelle_membre == "United States", f"[V3] libellé « United States » ({us and us.libelle_membre})")

# ── [V4] NVDA secteurs × resultat_exploitation ──────────────────────────────────────────────────
print("[V4] NVDA secteurs × resultat_exploitation FY2026 — non_ventile")
rCN = cell(v_nv, "secteurs", "resultat_exploitation", "nvda:ComputeAndNetworkingSegmentMember", FY26)
rG = cell(v_nv, "secteurs", "resultat_exploitation", "nvda:GraphicsSegmentMember", FY26)
b.check(bool(rCN and rG) and proche(rCN.valeur, 130141 * M, 1) and proche(rG.valeur, 9156 * M, 1),
        f"[V4] 130 141 / 9 156 M$ ({rCN and rCN.valeur}, {rG and rG.valeur})")
r4 = raccord(vue_nv, "secteurs", "resultat_exploitation", FY26)
# total publié (socle, résultat d'exploitation NVDA FY2026) = 130 387 M$ ; 130 387 − 139 297 = −8 910 M$.
b.check(r4 is not None and r4.statut == "non_ventile" and proche(r4.reste, -8910 * M, 1),
        f"[V4] reste = total socle (130 387) − 139 297 = −8 910 M$ ({r4})")

# ── [V5] NVDA douze mois glissants ──────────────────────────────────────────────────────────────
print("[V5] NVDA activites — douze mois glissants au 2026-07-26 (Data Center)")
ttm_id = next(p["id"] for p in socle_nv["periodes"] if p.get("nature") == "douze_mois")
b.check(ttm_id == "TTM2026-07-26", f"[V5] période douze mois lue au socle ({ttm_id})")
# Lot P1 tranche B : les douze mois se calculent SUR LA SÉRIE du découpage de référence. Sans le
# jumeau, le 10-K et le 10-Q récent ne partagent aucune période : la continuité de Data Center n'est
# pas PROUVÉE, ses douze mois ne sont pas établis — refus NOMMÉ, jamais deux découpages mêlés (c'est
# exactement le trou §0.1 que le lot ferme). Avec le jumeau (production : `lire_depots` le lit dès
# que le premier niveau change), la continuité est prouvée au semestre 2025.
_ch_act_sans_j = next(c for c in vue_nv["chroniques"] if c["axe"] == "activites" and c["ligne"] == "chiffre_affaires")
b.check(vcell(vue_nv, "activites", "chiffre_affaires", "nvda:DataCenterMember", ttm_id) is None
        and "nvda:DataCenterMember" in {d["membre"] for d in _ch_act_sans_j["douze_mois_non_etablis"]},
        f"[V5bis] sans jumeau : douze mois de Data Center NON établis, et nommés ({_ch_act_sans_j['douze_mois_non_etablis']})")
_vue_j = vue_de(vt.relever([nv10k, nv10q, charger_depot("NVDA", "0001045810-25-000209")], GAB, REF, socle_nv),
                socle_nv, (nv10k, nv10q, charger_depot("NVDA", "0001045810-25-000209")))
dc_ttm_d = vcell(_vue_j, "activites", "chiffre_affaires", "nvda:DataCenterMember", ttm_id)
dc_ttm = vt.CelluleVentilation("activites", "chiffre_affaires", "nvda:DataCenterMember", ttm_id,
                               dc_ttm_d["v"], dc_ttm_d["concept"], dc_ttm_d["accn"], "") if dc_ttm_d else None
# À la main, depuis les trois points de la fixture : exercice FY2026 193 737 + cumul 2026-01-26→
# 2026-07-26 164 269 − cumul comparable 2025-01-27→2025-07-27 80 208 = 277 798 M$.
b.check(dc_ttm is not None and proche(dc_ttm.valeur, 277798 * M, 1),
        f"[V5] Data Center douze mois = 193 737 + 164 269 − 80 208 = 277 798 M$ ({dc_ttm and dc_ttm.valeur})")

# ── [V6] NVDA clients ────────────────────────────────────────────────────────────────────────────
print("[V6] NVDA clients — premier client, base secteur C&N, aucun raccord")
c6 = next((c for c in v_nv.cellules if c.axe == "clients" and c.membre == "nvda:CustomerOneMember"
          and c.periode == "2026-01-25" and c.base and "StatementBusinessSegmentsAxis" in c.base), None)
b.check(c6 is not None and proche(c6.valeur, 0.22, 0.001),
        f"[V6] premier client = 22 % du CA du secteur C&N FY2026 ({c6 and c6.valeur})")
b.check(not [r for r in vue_nv["raccords"] if r["axe"] == "clients"], "[V6] aucun raccord sur l'axe `clients`")

# ── [V7] RVMD ────────────────────────────────────────────────────────────────────────────────────
print("[V7] RVMD — secteur_unique, aucune cellule")
b.check(v_rv.statut == "secteur_unique" and v_rv.cellules == [],
        f"[V7] RVMD ne publie rien par programme ({v_rv.statut}, {len(v_rv.cellules)} cellules)")

# ── [V8] JPM — trois métiers relevés (écart documenté, voir l'en-tête) ─────────────────────────────
print("[V8] JPM — trois métiers relevés, Corporate hors axe (écart documenté), refus bancaire")
membres_secteurs_jpm = sorted({c.membre for c in v_jpm.cellules if c.axe == "secteurs"})
b.check(membres_secteurs_jpm == sorted([
    "jpm:ConsumerCommunityBankingMember", "jpm:CommercialAndInvestmentBankMember",
    "jpm:AssetandWealthManagementSegmentMember"]),
    f"[V8] trois métiers sur `StatementBusinessSegmentsAxis` ({membres_secteurs_jpm})")
b.check(not any("CorporateNonSegment" in c.membre for c in v_jpm.cellules),
        "[V8] « Corporate » n'est jamais une cellule de l'axe secteurs (tagué hors `StatementBusinessSegmentsAxis`)")
ccb_ni = cell(v_jpm, "secteurs", "resultat_net", "jpm:ConsumerCommunityBankingMember", "FY2025-12-31")
cib_ni = cell(v_jpm, "secteurs", "resultat_net", "jpm:CommercialAndInvestmentBankMember", "FY2025-12-31")
awm_ni = cell(v_jpm, "secteurs", "resultat_net", "jpm:AssetandWealthManagementSegmentMember", "FY2025-12-31")
b.check(bool(ccb_ni and cib_ni and awm_ni)
        and proche(ccb_ni.valeur, 18245 * M, 1) and proche(cib_ni.valeur, 27761 * M, 1) and proche(awm_ni.valeur, 6522 * M, 1),
        f"[V8] résultat net par métier (gabarit industriel, concept NetIncomeLoss) : 18 245 / 27 761 / 6 522 M$")
ccb_actif = cell(v_jpm, "secteurs", "total_actif", "jpm:ConsumerCommunityBankingMember", "B2025-12-31")
b.check(ccb_actif is not None and proche(ccb_actif.valeur, 664669 * M, 1),
        f"[V8] total actif CCB = 664 669 M$ ({ccb_actif and ccb_actif.valeur})")
nr_concepts = {n.concept for n in v_jpm.non_rattaches if n.axe == "secteurs"}
b.check("us-gaap:RevenuesNetOfInterestExpense" in nr_concepts and "us-gaap:NoninterestExpense" in nr_concepts,
        f"[V8] les concepts bancaires sans recette du gabarit vont en `non_rattaches` ({sorted(nr_concepts)[:5]}…)")

try:
    pub_jpm = asyncio.run(publier_ventilation(
        None, "JPM", cik=cik_jpm, raison_sociale="JPMorgan Chase & Co.", famille=("bancaire", None),
        depots=[jpm10k], socle=socle_jpm, embed=False))
    refus_ok = pub_jpm.statut == "refus_famille" and pub_jpm.motif is not None and "bancaire" in pub_jpm.motif
except Exception as e:  # un refus retiré qui tente d'écrire sans `conn` doit FAIL nommé, pas mourir
    pub_jpm, refus_ok = e, False
b.check(refus_ok, f"[V8] `publier_ventilation` refuse NOMMÉ (famille bancaire) ({pub_jpm})")

# ── [V9] Aucun zéro fabriqué ────────────────────────────────────────────────────────────────────
print("[V9] aucun zéro fabriqué — un membre retiré d'une période")
faits_sans_auto = tuple(
    f for f in nv10k.faits
    if not (f.concept == "us-gaap:Revenues" and f.fin == "2026-01-25"
            and f.membres == (("srt:ProductOrServiceAxis", "nvda:AutomotiveMember"),)))
nv10k_sans_auto = vt.Depot(accn=nv10k.accn, form=nv10k.form, filed=nv10k.filed, faits=faits_sans_auto,
                           etiquettes=nv10k.etiquettes, hierarchie=nv10k.hierarchie, conflits=nv10k.conflits)
v9 = vt.relever([nv10k_sans_auto, nv10q], GAB, REF, socle_nv)
c9 = cell(v9, "activites", "chiffre_affaires", "nvda:AutomotiveMember", FY26)
b.check(c9 is None, f"[V9] le membre retiré ne porte AUCUNE cellule (jamais un zéro) ({c9})")
r9 = raccord(vue_de(v9, socle_nv, (nv10k_sans_auto,)), "activites", "chiffre_affaires", FY26)
b.check(r9 is not None and r9.statut == "non_ventile" and proche(r9.reste, 2349 * M, 1),
        f"[V9] le raccord devient `non_ventile`, reste = le montant retiré (2 349 M$) ({r9})")
def _xml_test(fait_xml: bytes) -> bytes:
    return (
        b'<?xml version="1.0"?>\n'
        b'<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
        b'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:us-gaap="http://fasb.org/us-gaap/2025" '
        b'xmlns:srt="http://fasb.org/srt/2025">\n'
        b'  <context id="c1"><entity><identifier scheme="http://www.sec.gov/CIK">0000000000</identifier>'
        b'<segment><xbrldi:explicitMember dimension="srt:ProductOrServiceAxis">us-gaap:Test</xbrldi:explicitMember>'
        b'</segment></entity><period><startDate>2026-01-01</startDate><endDate>2026-12-31</endDate></period></context>\n'
        b'  <unit id="usd"><measure>iso4217:USD</measure></unit>\n'
        + fait_xml +
        b"\n</xbrl>"
    )


faits_nil = vx.lire_instance(_xml_test(
    b'  <us-gaap:Revenues contextRef="c1" unitRef="usd" decimals="-6" xsi:nil="true"/>'))
faits_vide = vx.lire_instance(_xml_test(
    b'  <us-gaap:Revenues contextRef="c1" unitRef="usd" decimals="-6"/>'))
b.check(faits_nil == [] and faits_vide == [],
        f"[V9] un fait `xsi:nil` ou sans texte n'est JAMAIS lu comme zéro ({faits_nil}, {faits_vide})")

# ── [V10] Sous-détail JPM ────────────────────────────────────────────────────────────────────────
print("[V10] sous-détail JPM — provision CCB × portefeuille Apple Card")
sd = [s for s in v_jpm.sous_details if any(m == "jpm:AppleCreditCardPortfolioMember" for _a, m in s.membres)]
b.require(sd, 1, "[V10] UN sous-détail CCB × Apple Card")
b.check(bool(sd) and proche(sd[0].valeur, 2200 * M, 1) and sd[0].concept == "us-gaap:ProvisionForLoanLeaseAndOtherLosses",
        f"[V10] provision 2 200 M$ ({sd[0].valeur if sd else None})")
b.check(not any(c.membre == "jpm:AppleCreditCardPortfolioMember" for c in v_jpm.cellules),
        "[V10] le sous-détail n'est jamais une cellule (`AppleCreditCardPortfolioMember` absent des cellules)")

# ── [V11] Idempotence de l'empreinte ────────────────────────────────────────────────────────────
print("[V11] idempotence de l'empreinte")
st1 = vt.structure_de_ventilation(v_nv, version_referentiel=REF.version, version_gabarit=GAB.version,
                                  depots=(nv10k, nv10q))
st2 = vt.structure_de_ventilation(v_nv, version_referentiel=REF.version, version_gabarit=GAB.version,
                                  depots=(nv10k, nv10q))
b.check(vt.empreinte(st1) == vt.empreinte(st2), "[V11] deux relevés identiques → même empreinte")
v9_structure = vt.structure_de_ventilation(v9, version_referentiel=REF.version, version_gabarit=GAB.version,
                                           depots=(nv10k_sans_auto, nv10q))
b.check(vt.empreinte(st1) != vt.empreinte(v9_structure), "[V11] une cellule changée → une autre empreinte")

# ── [V12] Réplicabilité ──────────────────────────────────────────────────────────────────────────
print("[V12] réplicabilité — aucun ticker/CIK/membre propre dans le code et le référentiel livrés")
SRC_LIVRES = [
    Path(vt.__file__), Path(vx.__file__),
    Path(__file__).resolve().parent.parent / "app" / "contracts" / "ventilation_schema.py",
    Path(__file__).resolve().parent.parent / "app" / "knowledge" / "ventilation_feed.py",
]
INTERDITS = ("nvda:", "jpm:", "rvmd:", "NVIDIA", "JPMorgan", "Revolution Medicines",
            "Data Center", "Compute", "Networking", "1045810", "1628171", "19617")
def _lire_pour_grep(p: Path) -> str:
    """Le texte d'UN fichier livré, DÉPOUILLÉ de ses commentaires/docstrings — jamais la prose
    brute, qui nomme les tickers/membres interdits EN EXEMPLE (mémoire « un grep d'interdit lit sa
    propre énonciation »)."""
    return strip_code(p.read_text(encoding="utf-8"))


code_depouille = " ".join(_lire_pour_grep(p) for p in SRC_LIVRES)
yaml_texte = vt.REFERENTIEL_YAML.read_text(encoding="utf-8")
yaml_sans_commentaires = "\n".join(l.split("#", 1)[0] for l in yaml_texte.splitlines())
trouves = [t for t in INTERDITS if t in code_depouille or t in yaml_sans_commentaires]
b.check(trouves == [], f"[V12] aucun ticker/CIK/membre propre dans le code+YAML livrés ({trouves})")
fixture_texte = (FIX / "NVDA_0001045810-26-000021.json").read_text(encoding="utf-8")
b.check("NVDA" in fixture_texte, "[V12] … et le grep N'EST PAS aveugle : il trouve bien `NVDA` dans la fixture")

# ── [V13] Changement de découpage (activites) — lot P1 tranche B, cas RÉEL avec le jumeau ───────
print("[V13] NVDA activites — l'historique dans le découpage le plus récent, par addition vérifiée")
nv_jumeau = charger_depot("NVDA", "0001045810-25-000209")
v_nv3 = vt.relever([nv10k, nv10q, nv_jumeau], GAB, REF, socle_nv)
vue_nv3 = vue_de(v_nv3, socle_nv, (nv10k, nv10q, nv_jumeau))
EDGE, DC = "nvda:EdgeComputingMember", "nvda:DataCenterMember"
quatre = {"FY2024-01-28": 1091 + 10447 + 306 + 1553, "FY2025-01-26": 1694 + 11350 + 389 + 1878,
          FY26: 2349 + 16042 + 619 + 3191}
for per, attendu in quatre.items():
    e = vcell(vue_nv3, "activites", "chiffre_affaires", EDGE, per)
    b.check(e is not None and e["origine"] == "passage" and proche(e["v"], attendu * M, 1)
            and set(e["passage_de"]) == {"nvda:GamingMember", "nvda:ProfessionalVisualizationMember",
                                          "nvda:AutomotiveMember", "nvda:OEMAndOtherMember"},
            f"[V13] Edge Computing {per} = Σ des quatre anciens marchés = {attendu} M$, « addition vérifiée » ({e and e['v']})")
    d = vcell(vue_nv3, "activites", "chiffre_affaires", DC, per)
    b.check(d is not None and d["origine"] == "publie",
            f"[V13bis] Data Center {per} : continu, PUBLIÉ (pas reconstitué) ({d and d['origine']})")
r13 = raccord(vue_nv3, "activites", "chiffre_affaires", "TTM2026-07-26")
b.check(r13 is not None and r13.statut == "boucle" and proche(r13.somme, 302970 * M, 1),
        f"[V13ter] douze mois par marché SUR LA SÉRIE : Data Center 277 798 + Edge 25 172 = 302 970 M$ — "
        f"le découpage n'est plus mêlé ({r13})")
e_ttm = vcell(vue_nv3, "activites", "chiffre_affaires", EDGE, "TTM2026-07-26")
b.check(e_ttm is not None and proche(e_ttm["v"], (22201 + 13568 - 10597) * M, 1) and e_ttm["origine"] == "passage",
        f"[V13quater] Edge Computing douze mois = 22 201 + 13 568 − 10 597 = 25 172 M$, marqué « passage » ({e_ttm})")
ch_act = next(c for c in vue_nv3["chroniques"] if c["axe"] == "activites" and c["ligne"] == "chiffre_affaires")
b.check(ch_act["periode_annuelle_reference"] == FY26 and ch_act["point_de_depart_manquant"] == [],
        f"[V13quinquies] période annuelle de référence FY2026, point de départ présent ({ch_act['periode_annuelle_reference']})")

# ── [V13b] Le RENDU dit les découpages et le passage, en phrases ; l'ancien découpage à part ─────
print("[V13b] rendu des axes — découpages successifs, addition vérifiée, ancien découpage tel que publié")
texte_ids = vt.rendre_ventilation(vue_nv3, raison_sociale="NVIDIA Corporation", avec_identifiants=True)
bloc_act_ids = texte_ids.split("— Axe « activites » —", 1)[1].split("— Axe «", 1)[0]
b.check("Découpages successifs publiés" in bloc_act_ids
        and "« Edge Computing » = Automotive, Gaming, OEM and Other, Professional Visualization" in bloc_act_ids,
        "[V13b] le rendu nomme les deux découpages et le passage, en phrases d'analyste")
ligne_edge_fy24 = next((l for l in bloc_act_ids.split("chiffre_affaires — FY2024-01-28 :", 1)[1].splitlines()
                        if "Edge Computing" in l), "")
b.check("addition vérifiée" in ligne_edge_fy24 and "13 397.0" in ligne_edge_fy24,
        f"[V13b] Edge Computing FY2024 (13 397 M$) est marqué « addition vérifiée » dans le rendu ({ligne_edge_fy24.strip()!r})")
b.check("Découpage antérieur, tel que publié" in bloc_act_ids and "membre=nvda:GamingMember" in bloc_act_ids,
        "[V13b] l'ancien découpage reste visible, tel que publié, avec ses adresses citables")
try:
    vt.rendre_ventilation(vt.structure_de_ventilation(v_nv3, version_referentiel=REF.version,
                          version_gabarit=GAB.version, depots=(nv10k, nv10q, nv_jumeau)), raison_sociale="x")
    rendu_brut = "rendu"
except ValueError as e:
    rendu_brut = str(e)
b.check("VUE SERVIE" in rendu_brut, f"[V13c] le relevé BRUT ne se rend jamais — seule la vue servie ({rendu_brut[:80]})")

# ── [V13d] Axe PAYS : ré-attribution (même nom, contenu changé), RIEN de reconstitué ──────────────
print("[V13d] NVDA pays — contenu changé au semestre 2025 : rupture nommée, aucun chiffre fabriqué")
ch_geo = next(c for c in vue_nv3["chroniques"] if c["axe"] == "geographie" and c["ligne"] == "chiffre_affaires")
types_geo = {t["type"] for t in ch_geo["transitions"]}
b.check("meme_nom_contenu_change" in types_geo,
        f"[V13d] États-Unis 44 209 → 58 582 M$ sur le même semestre : « même nom, contenu changé » ({sorted(types_geo)})")
b.check(not [c for c in vue_nv3["cellules"] if c["axe"] == "geographie" and c.get("origine") == "passage"],
        "[V13d] aucun pays reconstitué — la ré-attribution n'a pas de passage vérifiable")
us_s24 = vcell(vue_nv3, "geographie", "chiffre_affaires", "country:US", "cumul du 2024-01-29 au 2024-07-28")
us_s24_ant = vcell(vue_nv3, "geographie", "chiffre_affaires", "country:US", "cumul du 2024-01-29 au 2024-07-28",
                   "cellules_anterieures")
b.check(us_s24 is None and us_s24_ant is not None and proche(us_s24_ant["v"], 26518 * M, 1),
        f"[V13d] le semestre 2024 (ancien critère) reste ANTÉRIEUR, tel que publié (26 518 M$) ({us_s24}, {us_s24_ant and us_s24_ant['v']})")
b.check(ch_geo["comparable_depuis"] == "FY2024-01-28" and ch_geo["point_de_depart_manquant"] == [],
        f"[V13d] l'émetteur a republié ses exercices : série comparable depuis FY2024 ({ch_geo['comparable_depuis']})")

# ── [V14] Emboîtement RENDU (texte) — Compute/Networking indentés sous Data Center ────────────────
print("[V14] rendu NVDA FY2026 — Compute et Networking indentés, pas au premier niveau")
texte_nv = vt.rendre_ventilation(vue_nv3, raison_sociale="NVIDIA Corporation")
# Le bloc de l'axe `activites` (il précède `clients`/`geographie`/`secteurs`), puis SON sous-bloc
# FY2026 précisément (« Compute »/« Networking » réapparaissent aussi en FY2024/FY2025).
bloc_activites = texte_nv.split("— Axe « activites » —", 1)[1].split("— Axe «", 1)[0]
sous_blocs = bloc_activites.split("  chiffre_affaires — ")
bloc_2026 = next((sb for sb in sous_blocs if sb.startswith("FY2026-01-25 :")), "")
b.check(bool(bloc_2026), "[V14] le sous-bloc FY2026 de `activites` est trouvé dans le rendu")
lignes_act = bloc_2026.splitlines()
l_dc = next((i for i, l in enumerate(lignes_act) if "Data Center :" in l), None)
l_compute = next((i for i, l in enumerate(lignes_act) if "Compute :" in l), None)
l_networking = next((i for i, l in enumerate(lignes_act) if "Networking :" in l), None)
b.check(l_dc is not None and not lignes_act[l_dc].lstrip().startswith("↳"),
        f"[V14] Data Center n'est PAS indenté (premier niveau) ({lignes_act[l_dc] if l_dc is not None else None!r})")
b.check(l_compute is not None and "↳" in lignes_act[l_compute],
        f"[V14] Compute EST indenté (« ↳ »), enfant de Data Center ({lignes_act[l_compute] if l_compute is not None else None!r})")
b.check(l_networking is not None and "↳" in lignes_act[l_networking],
        f"[V14] Networking EST indenté (« ↳ »), enfant de Data Center ({lignes_act[l_networking] if l_networking is not None else None!r})")
b.check("premier niveau boucle avec le total publié" in bloc_2026,
        "[V14] la ligne de raccord se dit explicitement PREMIER NIVEAU")

# ── [V15] Membres nouveaux PORTENT leur valeur ─────────────────────────────────────────────────────
print("[V15] NVDA activites — Hyperscale/AI Clouds/Edge Computing relevés avec leur valeur")
CUMUL_H1 = "cumul du 2026-01-26 au 2026-07-26"
hyperscale = cell(v_nv, "activites", "chiffre_affaires", "nvda:HyperscaleMember", CUMUL_H1)
ai_clouds = cell(v_nv, "activites", "chiffre_affaires", "nvda:AICloudsIndustrialEnterpriseMember", CUMUL_H1)
edge = cell(v_nv, "activites", "chiffre_affaires", "nvda:EdgeComputingMember", CUMUL_H1)
# Data Center est désormais relevé DIRECTEMENT au cumul (tous les membres le sont, lot P1 §8 point 3),
# plus « rattrapé » comme parent d'un membre nouveau.
dc_cumul = cell(v_nv, "activites", "chiffre_affaires", "nvda:DataCenterMember", CUMUL_H1)
b.check(bool(hyperscale) and proche(hyperscale.valeur, 91761 * M, 1), f"[V15] Hyperscale = 91 761 M$ ({hyperscale and hyperscale.valeur})")
b.check(bool(ai_clouds) and proche(ai_clouds.valeur, 72508 * M, 1), f"[V15] AI Clouds/Industrial/Enterprise = 72 508 M$ ({ai_clouds and ai_clouds.valeur})")
b.check(bool(edge) and proche(edge.valeur, 13568 * M, 1), f"[V15] Edge Computing = 13 568 M$ ({edge and edge.valeur})")
b.check(bool(dc_cumul) and proche(dc_cumul.valeur, 164269 * M, 1),
        f"[V15] Data Center (préexistant) est relevé au même cumul = 164 269 M$ ({dc_cumul and dc_cumul.valeur})")
emb_dc_cumul = raccord(vue_nv, "activites", "chiffre_affaires", CUMUL_H1, niveau="emboitement", parent="nvda:DataCenterMember")
r_cumul_h1 = raccord(vue_nv3, "activites", "chiffre_affaires", CUMUL_H1)
b.check(r_cumul_h1 is not None and r_cumul_h1.statut == "boucle" and proche(r_cumul_h1.total, 177837 * M, 1),
        f"[V15ter] au cumul du 10-Q, Data Center + Edge Computing (premier niveau seul) bouclent avec le total "
        f"publié 177 837 M$ — les enfants de Data Center ne sont pas comptés deux fois ({r_cumul_h1})")
b.check(emb_dc_cumul is not None and emb_dc_cumul.statut == "boucle",
        f"[V15] Hyperscale + AI Clouds (91 761 + 72 508 = 164 269) bouclent avec Data Center ({emb_dc_cumul})")
b.check({m["membre"] for m in vue_nv3["membres_nouveaux"] if m["axe"] == "activites"} == {
    "nvda:HyperscaleMember", "nvda:AICloudsIndustrialEnterpriseMember", "nvda:EdgeComputingMember"},
    f"[V15] les trois sont listés en `membres_nouveaux` de la vue, et eux seuls sur `activites` "
    f"({vue_nv3['membres_nouveaux']})")

# ── [V16] Conflits filtrés aux membres EN USAGE ────────────────────────────────────────────────────
print("[V16] NVDA — conflits de hiérarchie filtrés (0, le réel mesuré)")
b.check(v_nv.conflits == [],
        f"[V16] aucun conflit sur un membre réellement en usage pour NVDA ({v_nv.conflits})")

# ── [V17] La GRANDEUR d'une part de concentration — créances ≠ chiffre d'affaires ───────────────
# NVDA 10-Q : « A/R Customer A » = 22 % des CRÉANCES clients (benchmark AccountsReceivableMember) ;
# le rendu disait « 22 % du chiffre d'affaires » — tous les nombres justes, le fait faux.
print("[V17] NVDA — une part des créances clients n'est pas rendue comme une part des ventes")
bloc_clients = texte_nv.split("— Axe « clients » —", 1)[1].split("— Axe «", 1)[0]
ligne_ar = next((l for l in bloc_clients.splitlines() if "« A/R Customer A »" in l), "")
b.check("22 % des créances clients" in ligne_ar,
        f"[V17] « A/R Customer A » rendu comme part des créances clients ({ligne_ar.strip()!r})")
ligne_rev = next((l for l in bloc_clients.splitlines() if "« Revenue Customer 1 »" in l), "")
b.check("du chiffre d'affaires" in ligne_rev and "créances" not in ligne_rev,
        f"[V17] « Revenue Customer 1 » rendu comme part du chiffre d'affaires ({ligne_rev.strip()!r})")
b.check(not any("créances" in l and "chiffre d'affaires" in l for l in bloc_clients.splitlines()),
        "[V17] aucune ligne ne mêle créances et chiffre d'affaires")

# ── [V18] signal d'acquisition significative (§4 bis, lot P1) ──────────────────────────────────
print("[V18] signal d'acquisition significative — aucun chez NVDA (réel), un signal sur dépôt fictif")
b.check(v_nv.signaux_acquisition == [],
        f"[V18] NVDA (réel) ne dépose aucun fait de regroupement d'entreprises — aucun signal ({v_nv.signaux_acquisition})")


def _xml_regroupement(contrepartie: float, ca_acquis: float) -> bytes:
    texte = (
        '<?xml version="1.0"?>\n'
        '<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:us-gaap="http://fasb.org/us-gaap/2025">\n'
        '  <context id="cI"><entity><identifier scheme="http://www.sec.gov/CIK">0000000000</identifier>'
        '</entity><period><instant>2026-03-01</instant></period></context>\n'
        '  <unit id="usd"><measure>iso4217:USD</measure></unit>\n'
        f'  <us-gaap:BusinessCombinationConsiderationTransferred1 contextRef="cI" unitRef="usd" '
        f'decimals="-6">{contrepartie}</us-gaap:BusinessCombinationConsiderationTransferred1>\n'
        f'  <us-gaap:BusinessCombinationsRecognizedIdentifiableAssetsAcquiredAndLiabilitiesAssumedRevenueOfAcquiree1 '
        f'contextRef="cI" unitRef="usd" decimals="-6">{ca_acquis}'
        f'</us-gaap:BusinessCombinationsRecognizedIdentifiableAssetsAcquiredAndLiabilitiesAssumedRevenueOfAcquiree1>\n'
        '</xbrl>'
    )
    return texte.encode()


# NVDA FY2026 chiffre_affaires = 215 938 M$ (V1) ; 20 000 M$ de CA acquis ≈ 9,26 % > seuil 5 %.
faits_acq_dessus = tuple(vx.lire_instance(_xml_regroupement(5000 * M, 20000 * M)))
depot_acq_dessus = vt.Depot(accn="FICTIF-DESSUS-0000000001", form="8-K", filed="2026-03-05", faits=faits_acq_dessus)
v18 = vt.relever([nv10k, nv10q, depot_acq_dessus], GAB, REF, socle_nv)
b.require(v18.signaux_acquisition, 1, "[V18bis] une acquisition fictive au-dessus du seuil (5 % du CA) produit un signal")
if len(v18.signaux_acquisition) == 1:
    s18 = v18.signaux_acquisition[0]
    b.check(s18.base == "chiffre_affaires_acquis" and proche(s18.part_estimee, 20000 * M / (215938 * M), 0.001),
            f"[V18ter] base == chiffre_affaires_acquis, part ≈ 9,26 % ({s18.base}, {s18.part_estimee})")
    structure_v18 = vt.structure_de_ventilation(
        v18, version_referentiel=REF.version, version_gabarit=GAB.version,
        depots=(nv10k, nv10q, depot_acq_dessus))
    texte_v18 = vt.rendre_ventilation(pe.vue_servie(structure_v18, socle_nv), raison_sociale="NVIDIA Corporation")
    b.check("croissance qui inclut une acquisition" in texte_v18
            and "5 000.0 M$ de contrepartie" in texte_v18
            and "du chiffre d'affaires acquis publié" in texte_v18,
            f"[V18quater] le signal est rendu EN TEXTE (montrer_ventilation / matière de l'architecte) "
            f"({[l for l in texte_v18.splitlines() if 'acquisition' in l]})")

# Sous le seuil (500 M$ de CA acquis ≈ 0,23 %) : rien.
faits_acq_dessous = tuple(vx.lire_instance(_xml_regroupement(100 * M, 500 * M)))
depot_acq_dessous = vt.Depot(accn="FICTIF-DESSOUS-0000000001", form="8-K", filed="2026-03-05", faits=faits_acq_dessous)
v18b = vt.relever([nv10k, nv10q, depot_acq_dessous], GAB, REF, socle_nv)
b.check(v18b.signaux_acquisition == [],
        f"[V18quinquies] une acquisition fictive SOUS le seuil ne produit aucun signal ({v18b.signaux_acquisition})")

# ── [V19] garde (iv) — l'invariant de l'agrégat SUR LA VUE SERVIE, cas RÉEL NVDA ───────────────
print("[V19] NVDA — dépôt jumeau lu, invariant par pays et par marché sur la vue servie (garde iv, lot P1)")
refus_geo = [r for r in vue_nv3["refus"] if "geographie" in r]
b.check(refus_geo == [],
        f"[V19] avec le jumeau lu, l'invariant par pays tient — la version RETRAITÉE est prise ({refus_geo})")
refus_act = [r for r in vue_nv3["refus"] if "activites" in r]
b.check(refus_act == [], f"[V19bis] aucun refus sur « activites » : la série boucle partout ({refus_act})")
cellules_geo_ttm = [c for c in vue_nv3["cellules"]
                   if c["axe"] == "geographie" and c["ligne"] == "chiffre_affaires"
                   and c["periode"] == "TTM2026-07-26"]
b.require(cellules_geo_ttm, 4, "[V19ter] les quatre pays ont une cellule à la période TTM, sur la vue")
somme_geo_ttm = sum(c["v"] for c in cellules_geo_ttm)
b.check(proche(somme_geo_ttm, 302970 * M, 1),
        f"[V19quater] Σ pays (vue) = 302 970 M$ — la version RETRAITÉE (mesuré, cas réel) ({somme_geo_ttm})")
b.check(not any(ch.get("periodes_incompletes") for ch in vue_nv3["chroniques"] if ch["ligne"] == "chiffre_affaires"),
        "[V19quinquies] aucune période incomplète sur le chiffre d'affaires NVDA (mesuré)")

sys.exit(b.summary())
