"""Check des RATIOS MAISON (`app/knowledge/ratios_maison.py`) — hors ligne.

Les socles éprouvés sont reconstitués depuis les fixtures `companyfacts` COPIÉES DU RÉEL
(`checks/fixtures/socle_comptes/`, `tools/fixtures_socle.sh`). Les valeurs attendues sont écrites à la
main depuis les lignes déposées — jamais relues dans le module qu'on éprouve ; la pente est confrontée
à `statistics.linear_regression`, un autre algorithme que celui du module.

  §1 NVDA : un exercice entier à la main (taux d'impôt, résultat après impôt, capital MOYEN, rendement) ;
      un impôt négatif ne gonfle jamais le résultat après impôt (taux borné à zéro) ;
  §2 MSFT : moyenne cinq ans, pente (autre algorithme), conversion en trésorerie (rapport des SOMMES),
      capital par point de croissance — à la main ;
  §3 RVMD : un capital moyen négatif ne porte AUCUN rendement ; une perte cumulée ne se convertit pas ;
      une croissance depuis zéro ne se mesure pas — trois absences MOTIVÉES, jamais un nombre ;
  §4 jamais de zéro fabriqué : un socle d'avant le gabarit 1.1.0 (sans capital employé) rend des ratios
      NON ÉTABLIS qui nomment la ligne ; moins de cinq exercices ⟹ non établi ;
  §5 l'encadré : `completer_encadre` établit les chiffres de qf_1/qf_2/qf_3/qf_5 par le ratio (détenteur
      unique), dans l'unité déclarée ;
  §6 la forme persistée : la version des définitions entre dans l'empreinte (en changer republie) ; le
      texte que lit l'analyste montre les ratios sans marqueur de dérivation (#78/#110) ;
  §7 détenteurs : la lecture du socle par l'encadré appelle `ratio_du_socle` (AST, jamais recopié).
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, imports_symbol  # noqa: E402

from app.knowledge import ratios_maison as rm  # noqa: E402
from app.knowledge.ratios_maison import (  # noqa: E402
    RATIOS, VERSION_RATIOS, ratio_du_socle, rendre_ratios, table_des_ratios,
)
from app.knowledge.socle_comptes import (  # noqa: E402
    charger_gabarit, charger_reclassements, empreinte, reconstituer, rendre_socle, structure_du_socle,
)

b = Bilan()
FIX = Path(__file__).resolve().parent / "fixtures" / "socle_comptes"
M = 1e6
GAB = charger_gabarit()


def structure(ticker: str) -> dict:
    d = json.loads((FIX / f"{ticker}.json").read_text(encoding="utf-8"))
    return structure_du_socle(reconstituer(d["faits"], reclassements=charger_reclassements(d["cik"], GAB)))


def proche(a, attendu, tol=0.05) -> bool:
    return a is not None and abs(a - attendu) <= tol


def ligne(table, fin):
    """Lecture TOLÉRANTE : un exercice absent est un FAIL nommé, jamais la mort du script."""
    return next((l for l in table if l.fin == fin), None)


def val(v):
    return None if v is None else v.valeur


def ratio(st, rid):
    """`ratio_du_socle` sans exception : une levée inattendue devient un FAIL nommé (2ᵉ faux vert)."""
    try:
        return ratio_du_socle(st, rid)
    except Exception as e:  # noqa: BLE001
        return None, f"EXCEPTION {type(e).__name__}: {e}"


NV, MS, RV = structure("NVDA"), structure("MSFT"), structure("RVMD")

# ── §1 NVDA — un exercice à la main ─────────────────────────────────────────────────────────────────
print("§1 NVDA — l'exercice clos le 25/01/2026, à la main")
t_nv = table_des_ratios(NV)
b.require(t_nv, 5, "§1 NVDA : cinq exercices dans la table des ratios")
l26 = ligne(t_nv, "2026-01-25")
taux26 = 21383 / 141450                       # impôt ÷ résultat avant impôt déposés
nopat26 = 130387 * (1 - taux26)               # résultat d'exploitation déposé × (1 − taux)
ce_moyen26 = (45452 + 88337) / 2              # capital employé au 26/01/2025 et au 25/01/2026 (cf. check_socle §12)
b.check(l26 is not None and proche(val(l26.taux_impot_retenu), taux26, 1e-9),
        f"§1 taux d'impôt retenu = 21 383 ÷ 141 450 ({val(l26.taux_impot_retenu) if l26 else None})")
b.check(l26 is not None and proche(val(l26.resultat_exploitation_apres_impot), nopat26 * M, 0.01 * M),
        f"§1 résultat d'exploitation après impôt ≈ 110 676 M$ ({val(l26.resultat_exploitation_apres_impot) if l26 else None})")
b.check(l26 is not None and proche(val(l26.capital_employe_moyen), ce_moyen26 * M, 0.01 * M),
        "§1 capital employé MOYEN de l'exercice = (45 452 + 88 337) ÷ 2 — pas celui du seul jour de clôture")
b.check(l26 is not None and proche(val(l26.rendement_du_capital_employe), nopat26 / ce_moyen26 * 100, 0.001),
        f"§1 rendement du capital employé ≈ 165,4 % ({val(l26.rendement_du_capital_employe) if l26 else None})")
b.check(l26 is not None and proche(val(l26.rendement_hors_ecarts_d_acquisition),
                                   nopat26 / ((45452 - 5188 + 88337 - 20832) / 2) * 100, 0.001),
        "§1 rendement hors écarts d'acquisition : même résultat, capital moyen sans les écarts d'acquisition")
b.check(l26 is not None and proche(val(l26.marge_apres_impot), nopat26 / 215938 * 100, 0.001)
        and proche(val(l26.rotation_du_capital), 215938 / ce_moyen26, 0.0001),
        "§1 décomposition : marge après impôt × rotation du capital")
l23 = ligne(t_nv, "2023-01-29")
b.check(l23 is not None and val(l23.taux_impot_retenu) == 0.0
        and proche(val(l23.resultat_exploitation_apres_impot), 4224 * M, 0.01 * M),
        "§1 exercice 2023 : impôt NÉGATIF (−187 M$) ⟹ taux borné à zéro, le résultat après impôt n'excède "
        "pas le résultat d'exploitation (4 224 M$)")

# ── §2 MSFT — les agrégats ─────────────────────────────────────────────────────────────────────────
print("§2 MSFT — moyenne, pente, conversion, capital par point de croissance")
t_ms = table_des_ratios(MS)
b.require(t_ms, 5, "§2 MSFT : cinq exercices")
rdts = [val(l.rendement_du_capital_employe) for l in t_ms]
moy, per = ratio(MS, "rendement_du_capital_employe_moyen")
b.check(None not in rdts and proche(moy, sum(rdts) / 5, 1e-9) and "2022-06-30" in per and "2026-06-30" in per,
        f"§2 rendement moyen = moyenne des cinq rendements annuels, fenêtre dite ({moy}, {per[:60]})")
# Le rendement 2026 à la main : 155 237 × (1 − 32 185 ÷ 165 934) ÷ ((345 991 + 461 410) ÷ 2).
b.check(proche(rdts[-1], 155237 * (1 - 32185 / 165934) / ((345991 + 461410) / 2) * 100, 0.001),
        f"§2 MSFT 2026 : rendement ≈ 31,0 % ({rdts[-1]})")
xs = [(rm.date.fromisoformat(l.fin) - rm.date.fromisoformat(t_ms[0].fin)).days / 365.25 for l in t_ms]
pente_ref = statistics.linear_regression(xs, rdts).slope if None not in rdts else None
pente, _ = ratio(MS, "pente_du_rendement")
b.check(pente_ref is not None and proche(pente, pente_ref, 1e-9) and pente < 0,
        f"§2 pente = régression linéaire (autre algorithme) : {pente} points/an — le rendement s'ÉRODE")
conv, per_c = ratio(MS, "part_du_resultat_en_tresorerie")
b.check(proche(conv, (118548 + 136162 + 182935) / (88136 + 101832 + 133749) * 100, 1e-6)
        and "2024-06-30" in per_c,
        f"§2 conversion = Σ flux d'exploitation ÷ Σ résultat net sur TROIS exercices ({conv})")
cpp, _ = ratio(MS, "capital_par_point_de_croissance")
b.check(proche(cpp, (461410 - 147711) / ((331839 / 198270 - 1) * 100), 0.01),
        f"§2 capital par point de croissance ≈ 4 657 M$ ({cpp})")

# ── §3 RVMD — trois absences motivées ──────────────────────────────────────────────────────────────
print("§3 RVMD — un capital négatif, une perte, une croissance depuis zéro")
t_rv = table_des_ratios(RV)
l24 = ligne(t_rv, "2024-12-31")
b.check(l24 is not None and val(l24.capital_employe_moyen) is not None and val(l24.capital_employe_moyen) < 0
        and l24.rendement_du_capital_employe.valeur is None
        and "non défini" in (l24.rendement_du_capital_employe.motif or ""),
        "§3 capital employé moyen négatif ⟹ rendement NON DÉFINI, motivé — jamais un nombre de signe inversé")
v, motif = ratio(RV, "rendement_du_capital_employe_moyen")
b.check(v is None and "2024-12-31" in motif and "2025-12-31" in motif,
        f"§3 la moyenne cinq ans n'est pas établie et NOMME les exercices sans rendement ({motif[:90]})")
v, motif = ratio(RV, "pente_du_rendement")
b.check(v is None and motif.startswith("non établi"), "§3 pas de pente sans les cinq rendements")
v, motif = ratio(RV, "part_du_resultat_en_tresorerie")
b.check(v is None and "non calculable" in motif and "perte" in motif,
        f"§3 une perte cumulée ne se convertit pas en trésorerie ({motif[:80]})")
v, motif = ratio(RV, "capital_par_point_de_croissance")
b.check(v is None and "non calculable" in motif, f"§3 aucune croissance à financer ({motif[:80]})")

# ── §4 Jamais de zéro fabriqué ─────────────────────────────────────────────────────────────────────
print("§4 un socle incomplet rend des ratios non établis, nommés")
ancien = {**MS, "cellules": {k: v for k, v in MS["cellules"].items() if not k.startswith("capital_employe")}}
v, motif = ratio(ancien, "rendement_du_capital_employe_moyen")
b.check(v is None and "capital_employe" in motif,
        f"§4 socle sans capital employé (gabarit 1.0.0) : non établi, la ligne NOMMÉE ({motif[:80]})")
v, motif = ratio(ancien, "capital_par_point_de_croissance")
b.check(v is None and "capital_employe" in motif, "§4 idem pour le capital par point de croissance")
court = {**MS, "periodes": [p for p in MS["periodes"] if not (p["cadrage"] == "flux" and p["fin"] < "2024-01-01")]}
v, motif = ratio(court, "rendement_du_capital_employe_moyen")
b.check(v is None and "il en faut 5" in motif, f"§4 moins de cinq exercices ⟹ non établi ({motif})")
sans_ouv = {**MS, "periodes": [p for p in MS["periodes"] if p["nature"] != "ouverture"]}
l_prem = ligne(table_des_ratios(sans_ouv), "2022-06-30")
b.check(l_prem is not None and l_prem.rendement_du_capital_employe.valeur is None
        and "ouverture" in (l_prem.capital_employe_moyen.motif or ""),
        "§4 sans bilan d'ouverture, le premier exercice n'a pas de capital moyen — jamais celui de clôture")
try:
    ratio_du_socle(MS, "rendement_invente")
    b.check(False, "§4 un ratio inconnu est REFUSÉ (pas un None silencieux)")
except ValueError as e:
    b.check("inconnu" in str(e), f"§4 un ratio inconnu est refusé ({e})")

# ── §5 L'encadré ───────────────────────────────────────────────────────────────────────────────────
print("§5 l'encadré de qf_1/qf_2/qf_3/qf_5 lit les ratios")
from app.agents.v2.frameworks import completer_encadre, load_frameworks  # noqa: E402
qf = {q.id: q for f in load_frameworks().frameworks if f.id == "qualite_financiere" for q in f.questions}
attendus = {("qf_1", "rendement_du_capital_employe"): "rendement_du_capital_employe_moyen",
            ("qf_2", "part_du_resultat_en_tresorerie"): "part_du_resultat_en_tresorerie",
            ("qf_3", "capital_par_point_de_croissance"): "capital_par_point_de_croissance",
            ("qf_5", "pente_du_rendement"): "pente_du_rendement"}
lus = {(qid, c.id): c.socle.ratio for qid, q in qf.items() for c in q.chiffres_cles if c.socle and c.socle.ratio}
b.check(lus == attendus, f"§5 les quatre chiffres de l'encadré sont déclarés « ratio maison » ({lus})")
for (qid, cid), rid in attendus.items():
    q = qf.get(qid)
    try:
        enc = {c.id: c for c in completer_encadre(list(q.chiffres_cles), [], socle=MS)} if q else {}
    except Exception as e:  # noqa: BLE001
        enc = {}
        b.check(False, f"§5 {qid} : completer_encadre a LEVÉ ({type(e).__name__}: {e})")
    c = enc.get(cid)
    v, _ = ratio(MS, rid)
    b.check(c is not None and c.valeur is not None and proche(c.valeur, round(v, 6), 1e-6)
            and c.unite == RATIOS[rid].unite and "ratio maison" in (c.date_ou_periode or ""),
            f"§5 MSFT {qid}.{cid} = {c.valeur if c else None} {c.unite if c else ''}, lu par le ratio")
q1 = qf.get("qf_1")
enc_rv = {c.id: c for c in completer_encadre(list(q1.chiffres_cles), [], socle=RV)} if q1 else {}
c = enc_rv.get("rendement_du_capital_employe")
b.check(c is not None and c.valeur is None and "non établi" in (c.motif_absence or ""),
        "§5 RVMD qf_1 : le chiffre n'est pas établi et le DIT (jamais un zéro)")

# ── §6 Forme persistée et texte ────────────────────────────────────────────────────────────────────
print("§6 la version des définitions, le texte de l'analyste")
b.check(NV.get("version_ratios") == VERSION_RATIOS, "§6 la structure persistée porte la version des ratios")
b.check(empreinte(NV) != empreinte({**NV, "version_ratios": "0.9.0"}),
        "§6 changer la version des définitions change l'empreinte (la pièce se republie)")
b.check(not any(k.startswith("rendement") for k in NV["cellules"]),
        "§6 les ratios ne sont PAS stockés dans les cellules : ils se recalculent à la lecture")
from app.agents.v2.common import derive_nature  # noqa: E402
texte = rendre_socle(MS, GAB, raison_sociale="Microsoft Corporation")
b.check("Ratios maison" in texte and "31.0" in texte and "41.0" in texte,
        "§6 le texte du socle montre la table des ratios (rendement 2026 31,0 %, moyenne 41,0 %)")
b.check(derive_nature(entry_type="fact_financial", source_type="edgar_official", content=texte)[0] == "mesure",
        "§6 le texte reste tamponné `mesure` : aucun marqueur de dérivation (#78/#110)")
b.check(rendre_ratios({"periodes": [], "cellules": {}}) == [], "§6 un socle sans exercice ne rend aucune ligne de ratios")

# ── §7 Détenteurs ──────────────────────────────────────────────────────────────────────────────────
print("§7 détenteurs uniques")
fw = Path(__file__).resolve().parent.parent / "app" / "agents" / "v2" / "frameworks.py"
b.check(imports_symbol(fw, "ratio_du_socle", from_module="app.knowledge.ratios_maison"),
        "§7 l'encadré lit un ratio par `ratio_du_socle` (importé, jamais recopié)")
b.check(imports_symbol(Path(rm.__file__).parent / "socle_comptes.py", "rendre_ratios",
                       from_module="app.knowledge.ratios_maison"),
        "§7 le texte du socle rend les ratios par `rendre_ratios`")

sys.exit(b.summary())
