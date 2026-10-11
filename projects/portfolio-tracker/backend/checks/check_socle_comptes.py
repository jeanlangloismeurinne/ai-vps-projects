"""Check du SOCLE DES COMPTES (`app/knowledge/socle_comptes.py` + `socle_comptes.yaml`) — hors ligne.

Les fixtures sont COPIÉES DU RÉEL (`checks/fixtures/socle_comptes/*.json` : l'inventaire `companyfacts`
de RVMD, NVDA et MSFT téléchargé le 2026-10-04, restreint aux concepts du gabarit). Les valeurs
attendues ci-dessous ont été relues contre les dépôts — jamais recalculées par le module qu'on éprouve.

  §1 le gabarit se charge, et chaque incohérence relationnelle le fait REFUSER (pas dégrader) ;
  §2 RVMD (pré-revenus, 10-Q le plus récent) : périodes, douze mois glissants, convertibles, zéro écart ;
  §3 NVDA : la recette se choisit PÉRIODE PAR PÉRIODE (changement de concept des placements fin 2025) ;
      une charge que le gabarit ne nomme pas reste VISIBLE en « autres … par différence » ;
  §4 MSFT : dernier dépôt = 10-K ⟹ pas de colonne douze mois ; effet de change lu ; zéro écart ;
  §5 un écart de bouclage se PUBLIE, il ne s'absorbe pas (recette d'effet de change retirée) ;
  §6 jamais de zéro fabriqué : une ligne absente porte `compte_zero` / `non_depose`, valeur None ;
  §7 douze mois : un terme manquant n'est JAMAIS remplacé par l'exercice clos ;
  §8 déterminisme : l'ordre des points ne change rien ;
  §9 détenteurs uniques des règles de période, appelés et non recopiés ;
  §10 un reclassement d'analyste est PROPRE À L'ÉMETTEUR, motivé et sourcé (RVMD : Royalty Pharma) ;
  §11 la forme persistée : ce que relit le code (`valeur_du_socle`) et ce que lit l'analyste (le texte,
      tamponné `mesure` — un agrégat déterministe vaut relevé, #110) ;
  §12 gabarit 1.1.0 : le BILAN D'OUVERTURE, le CAPITAL EMPLOYÉ (convention maison) et les
      PARTICIPATIONS de NVDA reclassées (deux recettes, période par période) — valeurs à la main.
"""
from __future__ import annotations

import copy
import json
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, imports_symbol, strip_code  # noqa: E402

from app.knowledge import socle_comptes as sc  # noqa: E402
from app.knowledge.socle_comptes import (  # noqa: E402
    GabaritInvalide, charger_gabarit, charger_reclassements, periode_demandee, reconstituer, rendre_socle,
    structure_du_socle, valeur_du_socle,
)

b = Bilan()
FIX = Path(__file__).resolve().parent / "fixtures" / "socle_comptes"
M = 1e6


def faits(ticker: str) -> dict:
    return json.loads((FIX / f"{ticker}.json").read_text(encoding="utf-8"))["faits"]


def cellule(socle, ligne: str, periode: str):
    """Lecture TOLÉRANTE : une période absente est un FAIL nommé par l'assert qui la lit, jamais la
    mort du script avant son bilan (2ᵉ faux vert)."""
    return socle.cellules.get((ligne, periode)) or sc.Cellule(ligne, periode, "non_depose")


def proche(a, attendu, tol=0.06 * M) -> bool:
    return a is not None and abs(a - attendu) <= tol


def gabarit_texte() -> str:
    return sc.GABARIT_YAML.read_text(encoding="utf-8")


def charger_depuis(texte: str):
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(texte)
    return charger_gabarit(Path(f.name))


def refuse(label: str, texte: str, motif: str) -> None:
    try:
        charger_depuis(texte)
    except GabaritInvalide as e:
        b.check(motif in str(e), f"§1 {label} — refusé, mais pas pour la bonne raison : {e}")
        return
    except Exception as e:  # un refus par une autre règle est un FAIL nommé, jamais la mort du script
        b.check(False, f"§1 {label} — exception inattendue {type(e).__name__}: {e}")
        return
    b.check(False, f"§1 {label} — le gabarit incohérent a été ACCEPTÉ")


# ── §1 Le gabarit ──────────────────────────────────────────────────────────────────────────────────
print("§1 le gabarit maison")
gab = charger_gabarit()
b.check(gab.version == "1.1.0", f"§1 version du gabarit lue ({gab.version})")
b.require([e for e in gab.etats], 3, "§1 trois états (résultat, bilan, flux)")
b.check({e[0] for e in gab.etats} == {"compte_de_resultat", "bilan", "flux_de_tresorerie"},
        "§1 les trois états nommés")
t = gabarit_texte()
refuse("ligne inconnue dans une équation", t.replace("[+marge_brute, -recherche_developpement",
                                                     "[+marge_brut, -recherche_developpement"),
       "n'existe pas")
refuse("terme sans signe", t.replace("[+chiffre_affaires, -cout_des_ventes]",
                                     "[chiffre_affaires, -cout_des_ventes]"), "sans signe")
refuse("reste partagé par deux équations",
       t.replace("reste: +autres_elements_financiers", "reste: +autres_elements_apres_impot"),
       "est déjà le reste")
refuse("flux et instant mêlés",
       t.replace("composantes: [+fournisseurs, +dette_financiere_courante, +obligations_locatives_courantes]",
                 "composantes: [+fournisseurs, +dette_financiere_courante, +impot]"), "mêle un flux")
refuse("ligne toujours vide (ni recette, ni calcul, ni reste)",
       t.replace("reste: -autres_charges_exploitation\n", "\n"), "toujours vides")

# ── §2 RVMD ────────────────────────────────────────────────────────────────────────────────────────
print("§2 RVMD — pré-revenus, dernier dépôt 10-Q")
rv = reconstituer(faits("RVMD"))
ids = [p.id for p in rv.periodes]
b.check(ids == ["FY2021-12-31", "FY2022-12-31", "FY2023-12-31", "FY2024-12-31", "FY2025-12-31",
                "TTM2026-06-30", "B2020-12-31", "B2021-12-31", "B2022-12-31", "B2023-12-31",
                "B2024-12-31", "B2025-12-31", "B2026-06-30"], f"§2 périodes lues au dépôt : {ids}")
b.check([p.nature for p in rv.periodes if p.id == "B2020-12-31"] == ["ouverture"],
        "§2 le bilan qui précède le premier exercice est le BILAN D'OUVERTURE (nature `ouverture`)")
b.check(rv.ecarts() == [], f"§2 aucun écart de bouclage ({[c.equation for c in rv.ecarts()]})")
b.check(len(rv.controles) >= 15, f"§2 les bouclages sont réellement exercés ({len(rv.controles)})")
# Douze mois au 30/06/2026 : −1 223,03 M$ (pièce #787, relue au dépôt le 2026-10-04) — et non
# l'exercice 2025 (−897,7 M$), le chiffre que la lecture glissante existe pour corriger.
cfo = cellule(rv, "flux_exploitation", "TTM2026-06-30")
b.check(proche(cfo.valeur, -1223.03 * M, 0.01 * M), f"§2 flux d'exploitation sur douze mois = −1 223,03 M$ ({cfo.valeur})")
b.require(cfo.lectures, 3, "§2 douze mois : trois lectures déposées (exercice + cumul − comparable)")
b.check(cfo.etat == "depose", "§2 le flux sur douze mois est un relevé, pas un calcul")
b.check(proche(rv.valeur("dette_financiere_non_courante", "B2026-06-30"), 487.434 * M, 0.001 * M),
        "§2 convertibles au dernier bilan : 487,434 M$")
b.check(proche(rv.valeur("tresorerie", "B2026-06-30"), 815.4 * M) and
        proche(rv.valeur("placements_court_terme", "B2026-06-30"), 3122.5 * M),
        "§2 trésorerie 815,4 M$ et placements 3 122,5 M$ au 30/06/2026")
b.check(proche(rv.valeur("resultat_net", "FY2025-12-31"), -1131.301 * M, 0.001 * M),
        "§2 résultat net 2025 : −1 131,3 M$")
ac = cellule(rv, "autres_charges_exploitation", "FY2025-12-31")
b.check(ac.etat == "par_difference" and proche(ac.valeur, 0.0),
        f"§2 RVMD : R&D + frais généraux = toutes les charges d'exploitation (reste ≈ 0 : {ac.valeur})")
mb = cellule(rv, "marge_brute", "FY2025-12-31")
b.check(mb.etat == "par_somme" and mb.equation and "cout_des_ventes" in mb.equation,
        "§2 une marge brute non déposée est recomposée PAR SOMME, l'équation dite")
b.check(rv.dernier_depot and rv.dernier_depot["form"] == "10-Q",
        f"§2 dernier dépôt lu : le 10-Q ({rv.dernier_depot})")

# ── §3 NVDA ────────────────────────────────────────────────────────────────────────────────────────
print("§3 NVDA — recette choisie période par période")
nv = reconstituer(faits("NVDA"))
b.check(nv.ecarts() == [], f"§3 aucun écart ({[c.equation for c in nv.ecarts()]})")
pc25 = cellule(nv, "placements_court_terme", "B2025-01-26")
pc26 = cellule(nv, "placements_court_terme", "B2026-01-25")
b.check(proche(pc25.valeur, 34621 * M) and proche(pc26.valeur, 39065 * M),
        f"§3 placements : 34 621 puis 39 065 M$ ({pc25.valeur}, {pc26.valeur})")
b.check(pc26.lectures and pc26.lectures[0]["concept"] == "DebtSecuritiesCurrent",
        "§3 fin 2025 NVDA dépose ses placements sous un AUTRE concept, lu à cette période")
arm = cellule(nv, "autres_charges_exploitation", "FY2023-01-29")
b.check(proche(arm.valeur, 1353 * M),
        f"§3 la charge Arm (1 353 M$, exercice 2023) reste VISIBLE en autres charges ({arm.valeur})")
b.check(any(p.nature == "douze_mois" for p in nv.periodes), "§3 NVDA a une colonne douze mois")

# ── §4 MSFT ────────────────────────────────────────────────────────────────────────────────────────
print("§4 MSFT — dernier dépôt 10-K")
ms = reconstituer(faits("MSFT"))
b.check(not any(p.nature in ("douze_mois", "dernier_bilan") for p in ms.periodes),
        "§4 dernier dépôt annuel ⟹ ni douze mois ni dernier bilan distincts de l'exercice")
b.check(ms.ecarts() == [], f"§4 aucun écart ({[c.equation for c in ms.ecarts()]})")
b.check(proche(ms.valeur("effet_de_change", "FY2026-06-30"), -196 * M),
        "§4 l'effet de change de MSFT est lu (−196 M$)")

# ── §5 Un écart se publie ──────────────────────────────────────────────────────────────────────────
print("§5 un écart de bouclage se publie")
sans_fx = charger_depuis(t.replace(
    "          - [EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations]\n",
    ""))
ms2 = reconstituer(faits("MSFT"), sans_fx)
ec = [c for c in ms2.ecarts() if c.periode == "FY2026-06-30"]
b.require(ec, 1, "§5 recette d'effet de change retirée : UN écart sur l'exercice 2026")
b.check(bool(ec) and proche(ec[0].ecart, -196 * M) and "variation_de_tresorerie" in ec[0].equation,
        "§5 l'écart est publié avec son montant (−196 M$) sur l'équation de variation de trésorerie")
var = cellule(ms2, "variation_de_tresorerie", "FY2026-06-30")
b.check(var.etat == "depose" and proche(var.valeur, -9307 * M),
        "§5 l'écart n'est pas « réglé » en réécrivant une ligne déposée")
b.check(cellule(ms2, "effet_de_change", "FY2026-06-30").etat == "compte_zero",
        "§5 la ligne manquante reste « comptée zéro », jamais déduite par différence")

# ── §6 Jamais de zéro fabriqué ─────────────────────────────────────────────────────────────────────
print("§6 jamais de zéro fabriqué")
zero = [c for c in rv.cellules.values() if c.etat == "compte_zero"]
b.check(len(zero) > 0 and all(c.valeur is None for c in zero),
        f"§6 une ligne non déposée ne porte AUCUNE valeur publiée ({len(zero)} cellules)")
vide = reconstituer({}, gab)
b.check(vide.periodes == [] and vide.refus and "aucun exercice" in vide.refus[0],
        "§6 un inventaire vide n'est pas un socle à zéro : refus nommé")

# ── §7 Douze mois : jamais de repli sur l'exercice ─────────────────────────────────────────────────
print("§7 douze mois : un terme manquant n'est pas remplacé")
f7 = copy.deepcopy(faits("RVMD"))
f7["ResearchAndDevelopmentExpense"] = [
    p for p in f7["ResearchAndDevelopmentExpense"]
    if not (p.get("start") == "2025-01-01" and p.get("end") == "2025-06-30")]
rv7 = reconstituer(f7)
rd = cellule(rv7, "recherche_developpement", "TTM2026-06-30")
b.check(rd.valeur is None and rd.etat == "compte_zero",
        f"§7 cumul comparable retiré : la R&D sur douze mois n'est PAS lue ({rd.etat}, {rd.valeur})")
b.check(rv7.valeur("recherche_developpement", "FY2025-12-31") != rd.valeur,
        "§7 l'exercice clos ne remplace pas la lecture glissante")
ac7 = cellule(rv7, "autres_charges_exploitation", "TTM2026-06-30")
b.check("recherche_developpement" in ac7.absorbe and proche(ac7.valeur, 1296.3 * M, 0.2 * M),
        f"§7 le reste ABSORBE la ligne manquante et le DIT ({ac7.absorbe}, {ac7.valeur})")

# ── §8 Déterminisme ────────────────────────────────────────────────────────────────────────────────
print("§8 déterminisme")
f8 = copy.deepcopy(faits("NVDA"))
rng = random.Random(4)
for pts in f8.values():
    rng.shuffle(pts)
f8 = dict(sorted(f8.items(), reverse=True))
nv8 = reconstituer(f8)
diff = [k for k in nv.cellules if nv.cellules[k].valeur != nv8.cellules[k].valeur]
b.check(diff == [], f"§8 l'ordre des points ne change aucune cellule ({diff[:3]})")

# ── §9 Détenteurs uniques ─────────────────────────────────────────────────────────────────────────
print("§9 détenteurs uniques")
src = Path(sc.__file__)
for sym in ("douze_mois_glissants", "serie_du_concept", "points_de_l_unite_retenue"):
    b.check(imports_symbol(src, sym, from_module="app.knowledge.appariement_feed"),
            f"§9 la période se lit par `{sym}` (importé, jamais recopié)")
b.check(imports_symbol(src, "point_pour_periode", from_module="app.knowledge.edgar_facts"),
        "§9 l'ancre d'une période se lit par `point_pour_periode`")
code = strip_code(src.read_text(encoding="utf-8"))
for interdit in ("is_annual_flow", "points_annuels", "_ANNUAL_FORMS", "365"):
    b.check(interdit not in code, f"§9 aucune règle de période recopiée (`{interdit}` absent du code)")

# ── §10 Reclassement propre à l'émetteur ───────────────────────────────────────────────────────────
print("§10 reclassement d'analyste propre à l'émetteur")
CIK_RVMD = json.loads((FIX / "RVMD.json").read_text(encoding="utf-8"))["cik"]
rec = charger_reclassements(CIK_RVMD, gab)
b.require(rec, 1, "§10 RVMD porte UN reclassement")
b.check(bool(rec) and rec[0].ligne == "financement_adosse_aux_redevances"
        and "AccruedRoyaltiesCurrentAndNoncurrent" in rec[0].concepts and rec[0].piece.startswith("https://"),
        "§10 le financement Royalty Pharma est reclassé en dette, pièce à l'appui")
rv10 = reconstituer(faits("RVMD"), reclassements=rec)
b.check(proche(rv10.valeur("financement_adosse_aux_redevances", "B2026-06-30"), 548.542 * M, 0.001 * M)
        and proche(rv10.valeur("financement_adosse_aux_redevances", "B2025-12-31"), 268.446 * M, 0.001 * M),
        "§10 la dette Royalty Pharma : 268,4 M$ fin 2025, 548,5 M$ au 30/06/2026")
b.check(proche(rv10.valeur("autres_passifs_non_courants", "B2026-06-30"), 189.3 * M, 0.1 * M)
        and rv10.ecarts() == [], "§10 le reclassement SORT du solde (737,8 → 189,3 M$) et le bilan boucle toujours")
b.check(cellule(rv, "financement_adosse_aux_redevances", "B2026-06-30").etat == "compte_zero",
        "§10 sans reclassement, la ligne n'existe pas pour l'émetteur (comptée zéro, jamais devinée)")
b.check(charger_reclassements(789019, gab) == () and charger_reclassements(None, gab) == ()
        and "financement_adosse_aux_redevances" not in {r.ligne for r in charger_reclassements(1045810, gab)},
        "§10 un reclassement ne vaut que pour SON émetteur (ni MSFT ni NVDA n'héritent de celui de RVMD)")
with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as _f:
    _f.write('emetteurs:\n  "1": [{ligne: financement_adosse_aux_redevances, concepts: [X], motif: court, piece: x}]\n'
             '  "2": [{ligne: tresorerie, concepts: [X], motif: "un motif suffisamment long pour être lu comme écrit", '
             'piece: "https://x"}]\n')
for cik, motif in ((1, "sans motif écrit ni"), (2, "pas une ligne à recettes par émetteur")):
    try:
        charger_reclassements(cik, gab, Path(_f.name))
        b.check(False, f"§10 reclassement invalide ACCEPTÉ (émetteur {cik})")
    except GabaritInvalide as e:
        b.check(motif in str(e), f"§10 reclassement invalide refusé pour la bonne raison ({cik}) : {e}")

# ── §11 La forme persistée ─────────────────────────────────────────────────────────────────────────
print("§11 la forme persistée et sa lecture")
st = structure_du_socle(rv10)
b.check(periode_demandee(st, "douze_mois")["id"] == "TTM2026-06-30"
        and periode_demandee(st, "dernier_bilan")["id"] == "B2026-06-30"
        and periode_demandee(st, "dernier_exercice")["id"] == "FY2025-12-31",
        "§11 RVMD : douze mois glissants, dernier bilan au 30/06, dernier exercice 2025")
st_ms = structure_du_socle(ms)
b.check(periode_demandee(st_ms, "douze_mois")["id"] == "FY2026-06-30",
        "§11 MSFT (dernier dépôt annuel) : les douze derniers mois SONT l'exercice clos (#112)")
v, lib = valeur_du_socle(st, "dette_financiere_courante + dette_financiere_non_courante"
                             " + financement_adosse_aux_redevances", "dernier_bilan")
b.check(proche(v, 1035.976 * M, 0.001 * M) and "2026-06-30" in lib,
        f"§11 dette brute RVMD au 30/06/2026 = 487,434 + 548,542 = 1 035,976 M$ ({v}, {lib})")
v2, _ = valeur_du_socle(st, "-flux_de_tresorerie_disponible", "douze_mois")
b.check(proche(v2, 1232.131 * M, 0.001 * M), f"§11 consommation sur douze mois = 1 232,131 M$ ({v2})")
v3, motif3 = valeur_du_socle(st, "chiffre_affaires + stocks_inconnus", "douze_mois")
b.check(v3 is None and "stocks_inconnus" in motif3, f"§11 une ligne absente rend le chiffre NON ÉTABLI, nommée ({motif3})")
st_vide = {**st, "cellules": {k: v for k, v in st["cellules"].items() if not k.startswith("tresorerie|")}}
v4, motif4 = valeur_du_socle(st_vide, "tresorerie + placements_court_terme", "dernier_bilan")
b.check(v4 is None and "tresorerie" in motif4, "§11 une cellule manquante n'est jamais un zéro")
from app.agents.v2.common import derive_nature  # noqa: E402
texte = rendre_socle(st, gab, raison_sociale="Revolution Medicines, Inc.")
b.check(derive_nature(entry_type="fact_financial", source_type="edgar_official", content=texte)[0] == "mesure",
        "§11 le texte du socle est tamponné `mesure` (aucun marqueur de dérivation, #78/#110)")
b.check("1 296.3" in texte and "548.5" in texte and "Royalty Pharma" in texte,
        "§11 le texte montre les montants au dixième de million et le reclassement motivé")

# ── §12 Gabarit 1.1.0 : ouverture, capital employé, participations ──────────────────────────────────
print("§12 bilan d'ouverture, capital employé, participations")
CIK_NVDA = json.loads((FIX / "NVDA.json").read_text(encoding="utf-8"))["cik"]
rec_nv = charger_reclassements(CIK_NVDA, gab)
b.check({r.ligne for r in rec_nv} == {"participations", "participations_courantes"},
        f"§12 NVDA porte DEUX reclassements de participations ({[r.ligne for r in rec_nv]})")
nv12 = reconstituer(faits("NVDA"), reclassements=rec_nv)
b.check(nv12.ecarts() == [], f"§12 NVDA boucle toujours avec ses participations ({[c.equation for c in nv12.ecarts()]})")
b.check(proche(nv12.valeur("participations", "B2026-07-26"), 47898 * M)
        and proche(nv12.valeur("participations", "B2026-01-25"), 22251 * M)
        and proche(nv12.valeur("participations", "B2024-01-28"), 1321 * M)
        and cellule(nv12, "participations", "B2022-01-30").etat == "compte_zero",
        "§12 participations non cotées : 1 321 (2024) · 22 251 · 47 898 M$ ; comptées zéro avant 2023")
b.check(proche(nv12.valeur("participations_courantes", "B2026-07-26"), 42783 * M)
        and cellule(nv12, "participations_courantes", "B2025-01-26").etat == "compte_zero",
        "§12 participations cotées : 42 783 M$ au 26/07/2026, comptées zéro avant leur premier dépôt")
# Capital employé au 25/01/2026, à la main : actif 206 803 − trésorerie 10 605 − placements 39 065
# − participations 12 886 + 22 251 − droits d'utilisation 2 867 − fournisseurs 9 812 − autres passifs
# courants (32 163 − 9 812 − 999 − loyers à un an 372 = 20 980) = 88 337 M$.
ce26 = cellule(nv12, "capital_employe", "B2026-01-25")
b.check(ce26.etat == "calcule" and proche(ce26.valeur, 88337 * M),
        f"§12 capital employé NVDA au 25/01/2026 = 88 337 M$ ({ce26.valeur})")
b.check(proche(nv12.valeur("capital_employe_hors_ecarts_d_acquisition", "B2026-01-25"), (88337 - 20832) * M),
        "§12 hors écarts d'acquisition : 88 337 − 20 832 = 67 505 M$")
b.check(proche(nv12.valeur("obligations_locatives_courantes", "B2026-01-25"), 372 * M)
        and proche(nv12.valeur("autres_passifs_courants", "B2026-01-25"), 20980 * M),
        "§12 les loyers à un an SORTENT du solde des autres passifs courants (372 M$)")
nv_sans = reconstituer(faits("NVDA"))
b.check(proche(nv_sans.valeur("capital_employe", "B2026-01-25"), (88337 + 12886 + 22251) * M),
        "§12 sans reclassement, les participations restent DANS le capital employé (la convention ne devine pas)")
ouv = [p for p in nv12.periodes if p.nature == "ouverture"]
b.check([p.id for p in ouv] == ["B2021-01-31"] and proche(nv12.valeur("total_actif", "B2021-01-31"), 28791 * M),
        f"§12 NVDA : bilan d'ouverture au 31/01/2021, total de l'actif 28 791 M$ ({[p.id for p in ouv]})")
ms12 = reconstituer(faits("MSFT"))
# MSFT au 30/06/2026 : 758 376 − 20 935 − 55 908 − 36 348 − 24 177 − 42 416 − 117 182 = 461 410 M$.
b.check(proche(ms12.valeur("capital_employe", "B2026-06-30"), 461410 * M),
        f"§12 capital employé MSFT au 30/06/2026 = 461 410 M$ ({ms12.valeur('capital_employe', 'B2026-06-30')})")
b.check([p.id for p in ms12.periodes if p.nature == "ouverture"] == ["B2021-06-30"],
        "§12 MSFT : bilan d'ouverture au 30/06/2021")
fx = dict(faits("RVMD"))
fx = {c: [p for p in pts if (p.get("end") or "") >= "2021-06-01"] for c, pts in fx.items()}
b.check(not any(p.nature == "ouverture" for p in reconstituer(fx).periodes),
        "§12 sans exercice antérieur déposé, pas de bilan d'ouverture inventé")

sys.exit(b.summary())
