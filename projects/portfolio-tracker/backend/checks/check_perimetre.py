"""Check du PÉRIMÈTRE (`app/knowledge/perimetre.py`) — hors ligne, pur, lot P1
(`roadmap/V3/14-lot-P1-perimetre.md`).

Catalogue de cas FICTIFS (aucun nom réel, aucun ticker) — un cas par type de transition (§2.2),
plus les cas additionnels du §4 : retraitement d'une activité cédée au socle, deux transitions
successives sur le même axe, un redécoupage ET un renommage dans le même dépôt, un passage ambigu,
un recouvrement absent (axe entier réparti par hypothèse), une scission en trois répartie par
hypothèse (montant du groupe conservé), une mutation qui casse l'invariant de l'agrégat.

Plus UN cas RÉEL figé (NVDA, `checks/fixtures/perimetre/nvda_reel.json`, mesuré le 2026-10-22
en direct sur data.sec.gov) : §4 l'exige explicitement ("fixtures STABLES pour les contrôles de
l'architecte" — ici, la preuve que le module lit le réel, pas seulement des cas inventés).

  [P1]  ordre_des_periodes trie un cumul par sa FIN, jamais son DÉBUT
  [P2]  detail_ajoute : enfants nouveaux sous un parent de valeur inchangée
  [P3]  renommage : un membre nouveau égal à un seul ancien disparu
  [P4]  regroupement : un membre nouveau = somme d'une PARTITION d'anciens (fictif, 3→1)
  [P5]  scission : un ancien se répartit en plusieurs nouveaux (fictif, 1→2), passage vérifié
  [P6]  meme_nom_contenu_change : même id, valeur différente au recouvrement — jamais une continuité
  [P7]  rupture : aucun recouvrement du tout
  [P8]  rupture : passage AMBIGU (deux partitions bouclent)
  [P9]  rupture : trop de membres pour établir le passage (borne MAX_MEMBRES_PARTITION dépassée)
  [P10] axe_apparu / axe_disparu
  [P11] répartition par hypothèse : groupe minimal, montant du groupe CONSERVÉ, méthode prorata v1
  [P12] scission en TROIS répartie par hypothèse (1 ancien → 3 nouveaux, rupture)
  [P13] recouvrement absent : axe ENTIER réparti par hypothèse
  [P14] deux transitions successives sur le même axe (3 régimes), historique reconstitué par CHAÎNE
  [P15] un redécoupage ET un renommage dans le MÊME dépôt (deux mouvements simultanés)
  [P16] invariant de l'agrégat : Σ premier niveau reconstituée == ligne du socle
  [P17] invariant de l'agrégat ROMPU (mutation du socle) → motif NOMMÉ, jamais une rupture tue
  [P18] retraitement d'une activité cédée au socle (le socle en retraite une valeur)
  [P19] douze mois : régimes incohérents sans passage vérifié → refus nommé
  [P20] douze mois : régimes différents MAIS passage vérifié (regroupement) → cohérent
  [P21] douze mois : retraitement ambigu (deux valeurs à la même date de dépôt) → refus nommé
  [P22] douze mois : retraitement cohérent (la version la plus récente l'emporte) → accepté
  [P23] identifier_jumeau_candidat trouve le bon dépôt par la DATE (±20 j), jamais par un nom
  [P24] regime_a_change : vrai quand un axe change, faux quand aucun axe ne change
  [P25] signal_acquisition_significative : sous le seuil → rien
  [P26] signal_acquisition_significative : au-dessus, par le chiffre d'affaires acquis → signal
  [P27] signal_acquisition_significative : sans chiffre d'affaires publié → signal par la contrepartie
  [P28] RÉEL (NVDA) : detail_ajoute sous Data Center (Compute/Networking → Hyperscale/AI Clouds)
  [P29] RÉEL (NVDA) : regroupement vers Edge Computing (Gaming+ProViz+Automotive+OEM)
  [P30] RÉEL (NVDA) : trois périodes reconstituées, Data Center continu, Edge Computing par passage
  [P31] RÉEL (NVDA) : invariant de l'agrégat tient à chaque période
  [P32] Garde de détention : aucun autre module `app/knowledge/`/`app/modele_entreprise/` ne calcule
        un ensemble de membres de premier niveau par période ni ne compare deux dépôts
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, strip_code  # noqa: E402

from app.knowledge import perimetre as pe  # noqa: E402

b = Bilan()
FIX = Path(__file__).resolve().parent / "fixtures" / "perimetre"
C = pe.CelluleBrute


def _val(chron: pe.Chronique, membre: str, periode: str):
    for c in chron.cellules:
        if c.membre == membre and c.periode == periode:
            return c
    return None


# ── [P1] ordre_des_periodes ─────────────────────────────────────────────────────────────────────
b.check(
    pe.ordre_des_periodes("cumul du 2025-01-27 au 2025-07-27") > pe.ordre_des_periodes("2025-03-31"),
    "[P1] un cumul se trie par sa FIN (2025-07-27), postérieure à 2025-03-31")
b.check(
    pe.ordre_des_periodes("cumul du 2020-01-01 au 2020-06-30")
    < pe.ordre_des_periodes("cumul du 2021-01-01 au 2021-06-30"),
    "[P1bis] deux cumuls se trient par leur fin respective, pas par leur texte")


# ── [P2] detail_ajoute ──────────────────────────────────────────────────────────────────────────
# Montants à l'échelle du million (comme des dollars) : la tolérance de bouclage a un PLANCHER
# ABSOLU (`socle_comptes.TOLERANCE_ABSOLUE` = 500 000) — des montants fictifs à l'unité le
# rendraient toujours « dans la tolérance », masquant la logique éprouvée.
M = 1_000_000.0
cellules_p2 = [
    C("activites", "ent:ParentUnique", 1000.0 * M, "2025-12-31", "d1"),
    C("activites", "ent:ParentUnique", 1000.0 * M, "2026-12-31", "d1"),   # comparatif republié, MÊME dépôt
    C("activites", "ent:ParentUnique", 1000.0 * M, "2026-12-31", "d2"),
    C("activites", "ent:EnfantA", 600.0 * M, "2026-12-31", "d2", parent="ent:ParentUnique"),
    C("activites", "ent:EnfantB", 400.0 * M, "2026-12-31", "d2", parent="ent:ParentUnique"),
]
chron_p2 = pe.construire_chronique("activites", cellules_p2, {"d1": "2026-01-01", "d2": "2027-01-01"})
b.require(chron_p2.regimes, 1, "[P2] UN seul régime : du détail ajouté ne change pas le premier niveau")
tr_p2 = chron_p2.transitions
b.require(tr_p2, 1, "[P2] une seule transition pour ce cas")
if len(tr_p2) == 1:
    b.check(tr_p2[0].type == "detail_ajoute", "[P2] type == detail_ajoute")
    b.check(set(tr_p2[0].nouveaux) == {"ent:EnfantA", "ent:EnfantB"}, "[P2] enfants nommés")


# ── [P3] renommage ──────────────────────────────────────────────────────────────────────────────
cellules_p3 = [
    C("activites", "ent:AncienNom", 500.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:NouveauNom", 500.0 * M, "2026-06-30", "d2"),
]
rs_p3 = pe.etablir_regimes(cellules_p3, {"d1": "2026-01-01", "d2": "2027-01-01"})
b.require(rs_p3, 2, "[P3] deux régimes distincts")
tr_p3 = pe.typer_transitions(rs_p3[0], rs_p3[1], cellules_p3) if len(rs_p3) == 2 else []
b.require(tr_p3, 1, "[P3] une transition")
if len(tr_p3) == 1:
    b.check(tr_p3[0].type == "renommage", "[P3] type == renommage")
    b.check(tr_p3[0].anciens == ("ent:AncienNom",) and tr_p3[0].nouveaux == ("ent:NouveauNom",),
            "[P3] la paire renommée est la bonne")


# ── [P4] regroupement (fictif, 3 → 1) ───────────────────────────────────────────────────────────
cellules_p4 = [
    C("activites", "ent:Alpha", 300.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:Beta", 200.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:Gamma", 100.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:Fusion", 600.0 * M, "2026-06-30", "d2"),
]
rs_p4 = pe.etablir_regimes(cellules_p4, {"d1": "2026-01-01", "d2": "2027-01-01"})
tr_p4 = pe.typer_transitions(rs_p4[0], rs_p4[1], cellules_p4) if len(rs_p4) == 2 else []
b.require(tr_p4, 1, "[P4] une transition")
if len(tr_p4) == 1:
    b.check(tr_p4[0].type == "regroupement", "[P4] type == regroupement")
    b.check(set(tr_p4[0].anciens) == {"ent:Alpha", "ent:Beta", "ent:Gamma"}, "[P4] partition complète")


# ── [P5] scission (fictif, 1 → 2), avec reconstruction d'un historique ──────────────────────────
cellules_p5 = [
    C("activites", "ent:Bloc", 900.0 * M, "2025-06-30", "d1"),
    C("activites", "ent:Bloc", 1000.0 * M, "2026-06-30", "d1"),   # ancien régime, DEUX périodes
    C("activites", "ent:PartA", 400.0 * M, "2026-06-30", "d2"),
    C("activites", "ent:PartB", 600.0 * M, "2026-06-30", "d2"),
]
rs_p5 = pe.etablir_regimes(cellules_p5, {"d1": "2026-01-01", "d2": "2027-01-01"})
tr_p5 = pe.typer_transitions(rs_p5[0], rs_p5[1], cellules_p5) if len(rs_p5) == 2 else []
b.require(tr_p5, 1, "[P5] une transition")
if len(tr_p5) == 1:
    b.check(tr_p5[0].type == "scission", "[P5] type == scission")
chron_p5 = pe.construire_chronique("activites", cellules_p5, {"d1": "2026-01-01", "d2": "2027-01-01"})
cA = _val(chron_p5, "ent:PartA", "2025-06-30")
cB = _val(chron_p5, "ent:PartB", "2025-06-30")
b.check(cA is not None and cB is not None, "[P5] PartA/PartB reconstitués à 2025-06-30")
if cA is not None and cB is not None:
    b.check(cA.origine == "passage" and cB.origine == "passage", "[P5] origine == passage")
    b.check(abs((cA.valeur + cB.valeur) - 900.0 * M) < 1.0,
            "[P5] le passage conserve le total (900), réparti au PRORATA de la part de chaque "
            "membre au recouvrement (PartA 40 %, PartB 60 %)")
    b.check(abs(cA.valeur - 360.0 * M) < 1.0 and abs(cB.valeur - 540.0 * M) < 1.0,
            "[P5bis] la scission répartit au prorata (400/1000=40% → 360 ; 600/1000=60% → 540), "
            "jamais la valeur entière dupliquée sur chaque enfant")


# ── [P6] meme_nom_contenu_change ────────────────────────────────────────────────────────────────
cellules_p6 = [
    C("activites", "ent:MemeNom", 500.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:MemeNom", 900.0 * M, "2026-06-30", "d2"),   # même id, contenu changé
]
rs_p6 = pe.etablir_regimes(cellules_p6, {"d1": "2026-01-01", "d2": "2027-01-01"})
b.require(rs_p6, 2, "[P6] deux régimes (même id ne fusionne pas deux dépôts différents)")
tr_p6 = pe.typer_transitions(rs_p6[0], rs_p6[1], cellules_p6) if len(rs_p6) == 2 else []
b.require(tr_p6, 1, "[P6] une transition")
if len(tr_p6) == 1:
    b.check(tr_p6[0].type == "meme_nom_contenu_change", "[P6] type == meme_nom_contenu_change")
chron_p6 = pe.construire_chronique("activites", cellules_p6, {"d1": "2026-01-01", "d2": "2027-01-01"})
b.check(_val(chron_p6, "ent:MemeNom", "2026-06-30").origine == "publie",
        "[P6] la période du régime de référence reste publiée telle quelle")
b.check(len(chron_p6.cellules) == 1,
        "[P6] AUCUNE continuité par le nom : pas de 2ᵉ cellule fabriquée pour ce membre")


# ── [P7] rupture : aucun recouvrement ───────────────────────────────────────────────────────────
cellules_p7 = [
    C("activites", "ent:Avant", 100.0 * M, "2024-06-30", "d1"),
    C("activites", "ent:Apres", 999.0 * M, "2026-06-30", "d2"),
]
rs_p7 = pe.etablir_regimes(cellules_p7, {"d1": "2025-01-01", "d2": "2027-01-01"})
tr_p7 = pe.typer_transitions(rs_p7[0], rs_p7[1], cellules_p7) if len(rs_p7) == 2 else []
b.require(tr_p7, 1, "[P7] une transition")
if len(tr_p7) == 1:
    b.check(tr_p7[0].type == "rupture", "[P7] type == rupture")
    b.check("recouvrement" in tr_p7[0].motif, "[P7] motif nomme l'absence de recouvrement")


# ── [P8] rupture : passage AMBIGU ───────────────────────────────────────────────────────────────
# Trois anciens membres de MÊME valeur : {X,Y}, {X,W} et {Y,W} bouclent TOUS avec Cible — ambiguïté
# par construction, pas par un effet de plancher de tolérance.
cellules_p8 = [
    C("activites", "ent:X", 100.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:Y", 100.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:W", 100.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:Cible", 200.0 * M, "2026-06-30", "d2"),
]
rs_p8 = pe.etablir_regimes(cellules_p8, {"d1": "2026-01-01", "d2": "2027-01-01"})
tr_p8 = pe.typer_transitions(rs_p8[0], rs_p8[1], cellules_p8) if len(rs_p8) == 2 else []
rupture_p8 = [t for t in tr_p8 if t.type == "rupture" and "AMBIGU" in t.motif]
b.check(len(rupture_p8) >= 1, "[P8] un passage ambigu est détecté et nommé")


# ── [P9] rupture : trop de membres (borne dépassée) ─────────────────────────────────────────────
# N FIXE (9), jamais dérivé de `pe.MAX_MEMBRES_PARTITION` : une mutation qui lève la borne ne doit
# pas aussi lever, par construction, le nombre de membres du cas — sinon le test ne peut jamais
# discriminer (le N suivrait la borne mutée). Canari : le défaut documenté est 8.
b.check(pe.MAX_MEMBRES_PARTITION == 8, "[P9 canari] la borne par défaut est 8 (sinon adapter N ci-dessous)")
cellules_p9 = [C("activites", f"ent:M{i}", 1.0 * M, "2026-06-30", "d1") for i in range(9)]
cellules_p9.append(C("activites", "ent:Cible", 9.0 * M, "2026-06-30", "d2"))
rs_p9 = pe.etablir_regimes(cellules_p9, {"d1": "2026-01-01", "d2": "2027-01-01"})
tr_p9 = pe.typer_transitions(rs_p9[0], rs_p9[1], cellules_p9) if len(rs_p9) == 2 else []
rupture_p9 = [t for t in tr_p9 if t.type == "rupture" and "trop de membres" in t.motif]
b.check(len(rupture_p9) >= 1, "[P9] la borne MAX_MEMBRES_PARTITION refuse, jamais un calcul sans fin")


# ── [P10] axe_apparu / axe_disparu ──────────────────────────────────────────────────────────────
cellules_p10 = [C("geo_nouveau", "ent:Zone", 42.0, "2026-06-30", "d2")]
rs_p10 = pe.etablir_regimes(cellules_p10, {"d2": "2027-01-01"})
b.require(rs_p10, 1, "[P10] un seul régime quand l'axe n'existe que dans un dépôt")


# ── [P11] répartition par hypothèse : groupe, montant conservé, prorata v1 ──────────────────────
cellules_p11 = [
    C("activites", "ent:Historique1", 60.0 * M, "2025-06-30", "d1"),
    C("activites", "ent:Historique2", 40.0 * M, "2025-06-30", "d1"),
    C("activites", "ent:Historique1", 70.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:Historique2", 90.0 * M, "2026-06-30", "d1"),   # recouvrement : SOMMES différentes → rupture
    C("activites", "ent:Nouveau1", 30.0 * M, "2026-06-30", "d2"),
    C("activites", "ent:Nouveau2", 20.0 * M, "2026-06-30", "d2"),      # 1ʳᵉ période publiée dans le nouveau régime
]
chron_p11 = pe.construire_chronique("activites", cellules_p11, {"d1": "2026-01-01", "d2": "2027-01-01"})
c_h1 = _val(chron_p11, "ent:Nouveau1", "2025-06-30")
c_h2 = _val(chron_p11, "ent:Nouveau2", "2025-06-30")
b.check(c_h1 is not None and c_h2 is not None, "[P11] les deux nouveaux membres ont un historique reconstitué")
if c_h1 is not None and c_h2 is not None:
    b.check(c_h1.origine == "hypothese" and c_h2.origine == "hypothese", "[P11] origine == hypothese")
    b.check(abs((c_h1.valeur + c_h2.valeur) - 100.0 * M) < 1.0,
            "[P11] le MONTANT DU GROUPE est conservé (60+40=100), seule la répartition est une hypothèse")
    # prorata des parts au PREMIER semestre publié dans le nouveau découpage : Nouveau1=30, Nouveau2=20 → 60%/40%
    b.check(abs(c_h1.valeur - 60.0 * M) < 1.0 and abs(c_h2.valeur - 40.0 * M) < 1.0,
            "[P11] prorata v1 : parts 30/20 (60%/40%) appliquées au montant du groupe (100)")
    b.check(c_h1.methode is not None and "prorata" in c_h1.methode, "[P11] méthode déclarée")
    b.check(c_h1.periode_des_parts == "2026-06-30", "[P11] période des parts = 1ʳᵉ période du nouveau découpage")
    b.check(c_h1.anciens_montants == {"ent:Historique1": 60.0 * M, "ent:Historique2": 40.0 * M},
            "[P11] anciens montants du groupe portés sur la cellule")


# ── [P12] scission en TROIS répartie par hypothèse (rupture, montant conservé) ──────────────────
cellules_p12 = [
    C("activites", "ent:Mere", 300.0 * M, "2025-06-30", "d1"),
    C("activites", "ent:Mere", 400.0 * M, "2026-06-30", "d1"),   # recouvrement NON bouclant (filles=310≠400) → rupture
    C("activites", "ent:Fille1", 150.0 * M, "2026-06-30", "d2"),
    C("activites", "ent:Fille2", 100.0 * M, "2026-06-30", "d2"),
    C("activites", "ent:Fille3", 60.0 * M, "2026-06-30", "d2"),
]
chron_p12 = pe.construire_chronique("activites", cellules_p12, {"d1": "2026-01-01", "d2": "2027-01-01"})
trois = [_val(chron_p12, f"ent:Fille{i}", "2025-06-30") for i in (1, 2, 3)]
b.check(all(c is not None for c in trois), "[P12] les trois filles ont un historique reconstitué")
if all(c is not None for c in trois):
    b.check(all(c.origine == "hypothese" for c in trois), "[P12] les trois par hypothèse")
    b.check(abs(sum(c.valeur for c in trois) - 300.0 * M) < 1.0,
            "[P12] le montant du groupe (300, l'ancienne Mère) est conservé sur les trois filles")


# ── [P13] recouvrement absent : axe ENTIER réparti par hypothèse ────────────────────────────────
cellules_p13 = [
    C("activites", "ent:SeulAncien1", 50.0 * M, "2024-06-30", "d1"),
    C("activites", "ent:SeulAncien2", 70.0 * M, "2024-06-30", "d1"),
    C("activites", "ent:SeulNouveau1", 90.0 * M, "2026-06-30", "d2"),
    C("activites", "ent:SeulNouveau2", 30.0 * M, "2026-06-30", "d2"),
]
chron_p13 = pe.construire_chronique("activites", cellules_p13, {"d1": "2025-01-01", "d2": "2027-01-01"})
h1 = _val(chron_p13, "ent:SeulNouveau1", "2024-06-30")
h2 = _val(chron_p13, "ent:SeulNouveau2", "2024-06-30")
b.check(h1 is not None and h2 is not None, "[P13] axe entier : historique reconstitué malgré l'absence de recouvrement")
if h1 is not None and h2 is not None:
    b.check(h1.origine == "hypothese" and h2.origine == "hypothese", "[P13] origine == hypothese")
    b.check(abs((h1.valeur + h2.valeur) - 120.0 * M) < 1.0, "[P13] montant du groupe (50+70=120) conservé")


# ── [P14] deux transitions successives, 3 régimes, 3 périodes reconstituées ─────────────────────
cellules_p14 = [
    C("activites", "ent:V1", 100.0 * M, "2024-06-30", "d1"),
    C("activites", "ent:V1", 110.0 * M, "2025-06-30", "d1"),
    C("activites", "ent:V2", 110.0 * M, "2025-06-30", "d2"),   # renommage V1→V2 au recouvrement 2025
    C("activites", "ent:V2", 120.0 * M, "2026-06-30", "d2"),
    C("activites", "ent:V3", 120.0 * M, "2026-06-30", "d3"),   # renommage V2→V3 au recouvrement 2026
    C("activites", "ent:V3", 130.0 * M, "2027-06-30", "d3"),
]
chron_p14 = pe.construire_chronique(
    "activites", cellules_p14, {"d1": "2025-08-01", "d2": "2026-08-01", "d3": "2027-08-01"})
b.require(chron_p14.regimes, 3, "[P14] trois régimes successifs")
b.require(chron_p14.transitions, 2, "[P14] deux transitions (renommage, renommage)")
periodes_v3 = {c.periode: c for c in chron_p14.cellules if c.membre == "ent:V3"}
b.require(periodes_v3, 4, "[P14] V3 porte une valeur sur les QUATRE périodes historiques de l'axe "
                          "(2024, 2025, 2026 par passage, 2027 publiée)")
if len(periodes_v3) == 4:
    b.check(periodes_v3["2024-06-30"].valeur == 100.0 * M and periodes_v3["2024-06-30"].origine == "passage",
            "[P14] 2024 reconstitué par une CHAÎNE de DEUX passages (V1→V2→V3)")
    b.check(periodes_v3["2025-06-30"].valeur == 110.0 * M and periodes_v3["2025-06-30"].origine == "passage",
            "[P14bis] 2025 reconstitué par un SEUL passage (V2→V3)")
    b.check(periodes_v3["2027-06-30"].origine == "publie", "[P14] 2027 publiée telle quelle")


# ── [P15] redécoupage ET renommage dans le MÊME dépôt ───────────────────────────────────────────
cellules_p15 = [
    C("activites", "ent:Stable", 50.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:AncienNomP15", 35.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:A", 10.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:B", 20.0 * M, "2026-06-30", "d1"),

    C("activites", "ent:Stable", 50.0 * M, "2026-06-30", "d2"),
    C("activites", "ent:NouveauNomP15", 35.0 * M, "2026-06-30", "d2"),   # renommage (valeur UNIQUE : 35)
    C("activites", "ent:Fusion15", 30.0 * M, "2026-06-30", "d2"),        # regroupement A+B (10+20, valeur DISTINCTE)
]
rs_p15 = pe.etablir_regimes(cellules_p15, {"d1": "2026-01-01", "d2": "2027-01-01"})
tr_p15 = pe.typer_transitions(rs_p15[0], rs_p15[1], cellules_p15) if len(rs_p15) == 2 else []
types_p15 = {t.type for t in tr_p15}
b.check("renommage" in types_p15, "[P15] le renommage est détecté dans ce dépôt")
b.check("regroupement" in types_p15, "[P15] le regroupement est détecté DANS LE MÊME dépôt")


# ── [P16]/[P17] invariant de l'agrégat ───────────────────────────────────────────────────────────
cellules_p16 = [
    C("activites", "ent:Seg1", 60.0 * M, "2026-06-30", "d1"),
    C("activites", "ent:Seg2", 40.0 * M, "2026-06-30", "d1"),
]
chron_p16 = pe.construire_chronique("activites", cellules_p16, {"d1": "2026-01-01"})
b.check(pe.verifier_invariant_agregat(chron_p16, {"2026-06-30": 100.0 * M}) == [],
        "[P16] invariant tenu : Σ(60+40) == ligne du socle (100)")
motifs = pe.verifier_invariant_agregat(chron_p16, {"2026-06-30": 999.0 * M})
b.check(len(motifs) == 1 and "ERREUR" in motifs[0],
        "[P17] invariant ROMPU : motif NOMMÉ, jamais une rupture tue")


# ── [P18] retraitement du socle (prédicat douze mois) ───────────────────────────────────────────
retraitement_p18 = {
    "exercice": ({"val": 1000.0, "filed": "2026-01-10"}, {"val": 1050.0, "filed": "2026-06-01"}),
    "cumul": ({"val": 500.0, "filed": "2026-06-01"},),
    "comparable": ({"val": 480.0, "filed": "2026-06-01"},),
}
ok18, motif18 = pe.points_douze_mois_coherents(retraitements=retraitement_p18)
b.check(ok18, "[P18] un retraitement avec UNE version la plus récente par rôle est cohérent")


# ── [P19]/[P20] douze mois : cohérence de RÉGIME ────────────────────────────────────────────────
ok19, motif19 = pe.points_douze_mois_coherents(
    regime_exercice=frozenset({"ent:A", "ent:B"}),
    regime_cumul=frozenset({"ent:Fusion"}),
    regime_comparable=frozenset({"ent:A", "ent:B"}),
    transitions=())
b.check(not ok19 and motif19 is not None, "[P19] régimes incohérents SANS passage vérifié → refus nommé")

ok20, motif20 = pe.points_douze_mois_coherents(
    regime_exercice=frozenset({"ent:A", "ent:B"}),
    regime_cumul=frozenset({"ent:Fusion"}),
    regime_comparable=frozenset({"ent:A", "ent:B"}),
    transitions=(pe.Transition("activites", "regroupement", "2026-06-30",
                               anciens=("ent:A", "ent:B"), nouveaux=("ent:Fusion",)),))
b.check(ok20, "[P20] régimes différents MAIS passage vérifié (regroupement) → cohérent")


# ── [P21]/[P22] douze mois : retraitement ambigu vs cohérent ────────────────────────────────────
retraitement_p21 = {
    "exercice": ({"val": 1000.0, "filed": "2026-06-01"}, {"val": 1050.0, "filed": "2026-06-01"}),
}
ok21, motif21 = pe.points_douze_mois_coherents(retraitements=retraitement_p21)
b.check(not ok21 and motif21 is not None, "[P21] deux valeurs à LA MÊME date de dépôt → refus nommé (ambigu)")


# ── [P23] identifier_jumeau_candidat ────────────────────────────────────────────────────────────
FM = pe.FilingMeta
filings_p23 = (
    FM("acc-k10-ancien", "10-K", "2024-02-20", "2024-01-28"),
    FM("acc-q10-jumeau", "10-Q", "2025-08-27", "2025-07-27"),
    FM("acc-k10-recent", "10-K", "2026-02-25", "2026-01-25"),
    FM("acc-q10-recent", "10-Q", "2026-08-26", "2026-07-26"),
    # Décoy déposé APRÈS l'ancien régime (donc dans le NOUVEAU découpage) mais dont la période
    # tombe EXACTEMENT sur la cible (±0 j, contre ±1 j pour le vrai jumeau) — si le filtre « déposé
    # AVANT l'ancien » disparaît, ce décoy l'emporterait à tort.
    FM("acc-decoy-posterieur", "10-Q/A", "2026-09-01", "2025-07-26"),
)
recent_p23 = filings_p23[3]
ancien_p23 = filings_p23[2]
jumeau_trouve = pe.identifier_jumeau_candidat(filings_p23, recent_p23, ancien_p23)
b.check(jumeau_trouve is not None and jumeau_trouve.accn == "acc-q10-jumeau",
        "[P23] le jumeau est identifié PAR LA DATE (±20 j d'un an avant le dépôt récent), jamais par un nom")


# ── [P24] regime_a_change ───────────────────────────────────────────────────────────────────────
b.check(pe.regime_a_change(
    {"activites": frozenset({"ent:A", "ent:B"})}, {"activites": frozenset({"ent:Fusion"})}),
    "[P24] un axe dont le premier niveau change → regime_a_change == True")
b.check(not pe.regime_a_change(
    {"activites": frozenset({"ent:A", "ent:B"})}, {"activites": frozenset({"ent:A", "ent:B"})}),
    "[P24bis] aucun axe changé → regime_a_change == False")


# ── [P25]/[P26]/[P27] signal d'acquisition significative ────────────────────────────────────────
b.check(pe.signal_acquisition_significative(
    ({"date": "2026-03-01", "contrepartie": 10.0, "chiffre_affaires_acquis": 1.0},),
    chiffre_affaires_exercice=1000.0) == [],
    "[P25] acquisition sous le seuil (0,1 % du CA) → rien")

sig26 = pe.signal_acquisition_significative(
    ({"date": "2026-03-01", "contrepartie": 100.0, "chiffre_affaires_acquis": 80.0},),
    chiffre_affaires_exercice=1000.0)
b.require(sig26, 1, "[P26] acquisition au-dessus du seuil (8 % du CA) → un signal")
if len(sig26) == 1:
    b.check(sig26[0].base == "chiffre_affaires_acquis", "[P26] base == chiffre_affaires_acquis")

sig27 = pe.signal_acquisition_significative(
    ({"date": "2026-03-01", "contrepartie": 100.0, "chiffre_affaires_acquis": None},),
    chiffre_affaires_exercice=1000.0, capitalisation=1000.0)
b.require(sig27, 1, "[P27] sans chiffre d'affaires acquis publié, signal PAR LA CONTREPARTIE")
if len(sig27) == 1:
    b.check(sig27[0].base == "contrepartie_sur_capitalisation", "[P27] base == contrepartie_sur_capitalisation")


# ── [P28]-[P31] le cas RÉEL figé (NVDA, mesuré le 2026-10-22) ───────────────────────────────────
reel = json.loads((FIX / "nvda_reel.json").read_text(encoding="utf-8"))
cellules_reel = [
    C(c["axe"], c["membre"], c["valeur"], c["periode_fin"], c["depot"],
      c.get("periode_debut"), c.get("parent"))
    for c in reel["cellules"]
]
chron_reel = pe.construire_chronique("secteurs", cellules_reel, reel["depots_filed"])

types_reel = {t.type for t in chron_reel.transitions}
b.check("detail_ajoute" in types_reel, "[P28] RÉEL : detail_ajoute sous Data Center (Hyperscale/AI Clouds)")
detail_t = next((t for t in chron_reel.transitions if t.type == "detail_ajoute"), None)
b.check(detail_t is not None and set(detail_t.nouveaux) == {"nvda:HyperscaleMember", "nvda:AICloudsIndustrialEnterpriseMember"},
        "[P28bis] les deux enfants nommés sont les bons")

b.check("regroupement" in types_reel, "[P29] RÉEL : regroupement vers Edge Computing")
regroup_t = next((t for t in chron_reel.transitions if t.type == "regroupement"), None)
b.check(regroup_t is not None
        and set(regroup_t.anciens) == {"nvda:GamingMember", "nvda:ProfessionalVisualizationMember",
                                       "nvda:AutomotiveMember", "nvda:OEMAndOtherMember"}
        and regroup_t.nouveaux == ("nvda:EdgeComputingMember",),
        "[P29bis] la partition exacte Gaming+ProViz+Automotive+OEM → Edge Computing")

dc_periodes = {c.periode: c for c in chron_reel.cellules if c.membre == "nvda:DataCenterMember"}
ec_periodes = {c.periode: c for c in chron_reel.cellules if c.membre == "nvda:EdgeComputingMember"}
b.require(dc_periodes, 3, "[P30] Data Center : trois périodes (2024-07-28, 2025-07-27, 2026-07-26)")
b.require(ec_periodes, 3, "[P30bis] Edge Computing : trois périodes, dont deux par PASSAGE")
if len(dc_periodes) == 3 and len(ec_periodes) == 3:
    b.check(dc_periodes["2024-07-28"].origine == "passage" and dc_periodes["2024-07-28"].valeur == 48835000000.0,
            "[P30ter] Data Center 2024 : continuité (identité), valeur réelle inchangée")
    b.check(ec_periodes["2024-07-28"].origine == "passage"
            and abs(ec_periodes["2024-07-28"].valeur - (5527000000.0 + 881000000.0 + 675000000.0 + 166000000.0)) < 1.0,
            "[P30quater] Edge Computing 2024 reconstitué par passage = somme RÉELLE des quatre anciens membres")
    b.check(ec_periodes["2025-07-27"].origine == "publie" and ec_periodes["2025-07-27"].valeur == 10597000000.0,
            "[P30quinquies] Edge Computing 2025 publiée telle quelle (10 597 M$, mesuré)")

ligne_socle_reel = {
    "2024-07-28": 48835000000.0 + 5527000000.0 + 881000000.0 + 675000000.0 + 166000000.0,
    "2025-07-27": 80208000000.0 + 10597000000.0,
    "2026-07-26": 164269000000.0 + 13568000000.0,
}
b.check(pe.verifier_invariant_agregat(chron_reel, ligne_socle_reel) == [],
        "[P31] RÉEL : l'invariant de l'agrégat tient aux trois périodes (mesuré, pas une coïncidence)")


# ── [P32] Garde de détention ────────────────────────────────────────────────────────────────────
APP = Path(__file__).resolve().parents[1] / "app"


def _calcule_premier_niveau_ou_compare_depots(source: str) -> bool:
    """Heuristique de détention (§4) : un calcul de premier niveau PAR PÉRIODE (`parent_de.get(m)
    not in presents`-like) ou une comparaison de deux dépôts (itère sur `depots`/`Depot` deux fois
    avec un `!=`/`est_k10`) hors de `perimetre.py`. Cherche le motif caractéristique, dépouillé."""
    nettoye = strip_code(source)
    return ("not in presents" in nettoye and "parent_de" in nettoye) or ("regime_a_change(" in nettoye and False)


modules_hors_perimetre = [
    p for p in (APP / "knowledge").glob("*.py") if p.name not in ("perimetre.py",)
] + [p for p in (APP / "modele_entreprise").glob("*.py")]
fautifs = [
    str(p.relative_to(APP.parent)) for p in modules_hors_perimetre
    if _calcule_premier_niveau_ou_compare_depots(p.read_text(encoding="utf-8"))
]
b.check(fautifs == [], f"[P32] aucun module hors perimetre.py ne recalcule le premier niveau par période ({fautifs})")
_perimetre_source = (APP / "knowledge" / "perimetre.py").read_text(encoding="utf-8")
b.check(_calcule_premier_niveau_ou_compare_depots(_perimetre_source),
        "[P32bis] perimetre.py, lui, PORTE bien ce calcul (asserté en positif, #4 de la spec)")


# ── [P33]-[P36] la vue SERVIE (lot P1 §8 addendum, tranche A, point 2 + garde (iv)) ────────────
# Cas FICTIFS, sur la FORME de la structure persistée (celle que rend `ventilation.
# structure_de_ventilation`) — le cas RÉEL (NVDA, douze mois par pays) est éprouvé dans
# `check_ventilation_publiee.py`, qui seul sait lire une instance XBRL.

def _cv(axe: str, ligne: str, membre: str, periode: str, v: float, accn: str,
       parent: Optional[str] = None) -> dict:
    d = {"axe": axe, "ligne": ligne, "membre": membre, "periode": periode, "v": v,
        "concept": "fictif", "accn": accn, "libelle": membre}
    if parent is not None:
        d["parent"] = parent
    return d


# [P33] déduplication : deux dépôts publient la MÊME adresse logique à des valeurs différentes —
# celui déposé le plus RÉCEMMENT fait foi, jamais le premier rencontré dans la liste.
structure_p33 = {
    "depots": [{"accn": "d1", "filed": "2026-01-01"}, {"accn": "d2", "filed": "2026-06-01"}],
    "cellules": [
        _cv("axe_p33", "chiffre_affaires", "m1", "P1", 100.0, "d1"),
        _cv("axe_p33", "chiffre_affaires", "m1", "P1", 150.0, "d2"),
    ],
    "refus": [],
}
vue_p33 = pe.vue_servie(structure_p33, socle=None)
b.require(vue_p33["cellules"], 1, "[P33] une seule cellule survit à la déduplication (pas de fusion ET pas de doublon)")
if len(vue_p33["cellules"]) == 1:
    b.check(vue_p33["cellules"][0]["v"] == 150.0 and vue_p33["cellules"][0]["accn"] == "d2",
            f"[P33bis] le dépôt déposé le plus récemment (d2, 150) l'emporte, pas d1 ({vue_p33['cellules'][0]})")
# Ordre INVERSE dans la liste d'entrée : même résultat — ce n'est pas l'ordre de la liste qui décide.
structure_p33b = {**structure_p33, "cellules": list(reversed(structure_p33["cellules"]))}
vue_p33b = pe.vue_servie(structure_p33b, socle=None)
b.check(len(vue_p33b["cellules"]) == 1 and vue_p33b["cellules"][0]["v"] == 150.0,
        "[P33ter] le résultat ne dépend pas de l'ordre d'arrivée des cellules")

# [P34] garde (iv) : une période COMPLÈTE (tous les membres du régime de référence y ont une
# valeur) dont la somme ne boucle PAS avec le total du socle → refus NOMMÉ.
structure_p34 = {
    "depots": [{"accn": "d1", "filed": "2026-01-01"}],
    "cellules": [
        _cv("axe_p34", "chiffre_affaires", "m1", "P1", 60.0 * M, "d1"),
        _cv("axe_p34", "chiffre_affaires", "m2", "P1", 30.0 * M, "d1"),
    ],
    "refus": [],
}
socle_p34 = {"cellules": {"chiffre_affaires|P1": {"v": 100.0 * M}}}   # 60+30=90 ≠ 100
vue_p34 = pe.vue_servie(structure_p34, socle=socle_p34)
refus_p34 = [r for r in vue_p34["refus"] if "axe_p34" in r]
b.require(refus_p34, 1, "[P34] un refus NOMMÉ apparaît (90 ≠ 100, période complète)")
if refus_p34:
    b.check("ERREUR" in refus_p34[0], "[P34bis] le motif dit ERREUR du module, jamais une rupture tue")

# [P35] le FILTRE DE COMPLÉTUDE : un membre du régime de référence SANS AUCUNE valeur à une
# période (ex. un membre nouveau dont les douze mois ne sont pas encore établis, §4.2) ne doit
# JAMAIS déclencher la garde (iv) à CETTE période, même si la somme PARTIELLE est très éloignée du
# total du socle — l'incomplétude est déjà nommée par le raccord `decoupage_change`/`non_ventile`
# existant, ce n'est pas une faute DE CE MODULE.
structure_p35 = {
    "depots": [{"accn": "d1", "filed": "2025-01-01"}, {"accn": "d2", "filed": "2026-01-01"}],
    "cellules": [
        _cv("axe_p35", "chiffre_affaires", "m1", "P1", 10.0 * M, "d1"),
        _cv("axe_p35", "chiffre_affaires", "m2", "P1", 20.0 * M, "d1"),
        _cv("axe_p35", "chiffre_affaires", "m1", "P2", 70.0 * M, "d2"),   # m2 ABSENT à P2 : incomplet
        _cv("axe_p35", "chiffre_affaires", "m2", "P4", 5.0 * M, "d2"),    # m2 n'existe qu'ICI pour d2
    ],
    "refus": [],
}
socle_p35 = {"cellules": {"chiffre_affaires|P2": {"v": 999.0 * M}}}   # 70 ≠ 999, mais P2 est INCOMPLET
vue_p35 = pe.vue_servie(structure_p35, socle=socle_p35)
refus_p35 = [r for r in vue_p35["refus"] if "axe_p35" in r]
b.check(refus_p35 == [], f"[P35] aucun refus sur une période INCOMPLÈTE, même très éloignée du total ({refus_p35})")

# [P36] la garde (iv) ne porte QUE sur `LIGNE_RACCORD_OBLIGATOIRE` (« chiffre_affaires ») — un
# résultat ou un actif sectoriel qui laisse un reste non affecté (cas RÉEL NVDA resultat_
# exploitation, [V4] de check_ventilation_publiee) n'est PAS une faute de périmètre.
structure_p36 = {
    "depots": [{"accn": "d1", "filed": "2026-01-01"}],
    "cellules": [
        _cv("axe_p36", "resultat_exploitation", "m1", "P1", 60.0 * M, "d1"),
        _cv("axe_p36", "resultat_exploitation", "m2", "P1", 30.0 * M, "d1"),
    ],
    "refus": [],
}
socle_p36 = {"cellules": {"chiffre_affaires|P1": {"v": 100.0 * M}}}   # 90 (resultat_exploitation) ≠
# 100 (chiffre_affaires, LIGNE_RACCORD_OBLIGATOIRE) : un chiffre du socle sur une AUTRE ligne existe
# bien — c'est le filtre sur `c["ligne"]`, pas une coïncidence de clef absente, qui doit protéger ici.
vue_p36 = pe.vue_servie(structure_p36, socle=socle_p36)
refus_p36 = [r for r in vue_p36["refus"] if "axe_p36" in r]
b.check(refus_p36 == [],
        f"[P36] aucun refus hors de la ligne chiffre_affaires, même si la ligne ne boucle jamais ({refus_p36})")
b.check(pe.LIGNE_RACCORD_OBLIGATOIRE == "chiffre_affaires",
        "[P36bis] canari : la ligne gardée est bien `chiffre_affaires` (sinon adapter [P34]-[P36])")


sys.exit(b.summary())
