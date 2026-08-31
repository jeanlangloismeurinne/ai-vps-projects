"""Vérification du contrat d'analyse (bull/bear/research) — pur, sans réseau ni DB ni LLM.

Ce check existe à cause d'un mode de panne déjà constaté deux fois : un champ desserré **à chaud**
pour faire passer un run (`Optional[float] = None` sur le reverse-DCF, `extra='ignore'` sur
`Assumptions`) tient le temps du run et devient un trou silencieux ensuite. Rien ne le rattrapait :
les contrats n'avaient aucun check, la validation se faisait à la main dans un container jetable.

Ce qu'on éprouve ici :

  • `reverse_dcf.croissance_implicite_prix_actuel_pct` est REQUIS (le bear l'a laissé `null` aux
    deux rounds tout en écrivant « ~15% » dans sa prose : un manque ne doit pas ressembler à une
    valeur) ;
  • `Assumptions` est fermé aux 3 clés contractuelles (`extra='forbid'`) — le modèle avait inventé
    `taux_actualisation` ;
  • les deux hypothèses de croissance portent leur unité DANS LEUR NOM (`_pct`) : bull avait rendu
    `0.15` (fraction) et bear `8.0` (pourcent) pour la même grandeur, soit un facteur ~53 muet
    parce que les deux sont des `float` valides. Les anciens noms nus doivent désormais être
    REJETÉS, pas ignorés — sans quoi le renommage serait cosmétique ;
  • `multiple_sortie` reste sans suffixe : c'est un multiple (18 = 18×), pas un pourcentage ;
  • la copie runtime `app/contracts/` et le contrat figé `roadmap/provenance-cards/` déclarent les
    mêmes champs (règle #19). Le contrat figé n'est pas dans l'image (build context = ./backend) :
    il n'est comparé que s'il est monté sur /contract_frozen, et son absence est ANNONCÉE, jamais
    silencieuse.
"""
import sys
from pathlib import Path

from pydantic import ValidationError

from app.contracts.analysis_v2_schemas import Assumptions, ReverseDcf, ValorisationCote

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


def rejette(model, payload):
    """True si le modèle REFUSE le payload (c'est le comportement attendu du contrat)."""
    try:
        model(**payload)
        return False
    except ValidationError:
        return True


ASSUMPTIONS_OK = {"croissance_revenue_pct": 12.0, "expansion_marge_fcf_pct": 2.0,
                  "multiple_sortie": 18.0}

print("\n§1 — Assumptions : les unités sont dans le nom")
a = Assumptions(**ASSUMPTIONS_OK)
check("les 3 clés contractuelles sont acceptées", a.croissance_revenue_pct == 12.0)
check("expansion_marge_fcf_pct relu tel quel", a.expansion_marge_fcf_pct == 2.0)
check("multiple_sortie sans suffixe (c'est un multiple, pas un %)", a.multiple_sortie == 18.0)

# Le coeur de la dette B : l'ancien nom nu ne doit plus entrer, ni comme champ, ni comme extra.
check("ancien nom `croissance_revenue` REJETÉ",
      rejette(Assumptions, {"croissance_revenue": 12.0, "expansion_marge_fcf_pct": 2.0,
                            "multiple_sortie": 18.0}))
check("ancien nom `expansion_marge_fcf` REJETÉ",
      rejette(Assumptions, {"croissance_revenue_pct": 12.0, "expansion_marge_fcf": 2.0,
                            "multiple_sortie": 18.0}))
check("les deux anciens noms ensemble REJETÉS",
      rejette(Assumptions, {"croissance_revenue": 0.12, "expansion_marge_fcf": 0.02,
                            "multiple_sortie": 18.0}))

print("\n§2 — Assumptions : fermé (extra='forbid'), le taux d'actualisation va en prose")
check("`taux_actualisation` inventé REJETÉ",
      rejette(Assumptions, {**ASSUMPTIONS_OK, "taux_actualisation": 0.09}))
check("`wacc` inventé REJETÉ", rejette(Assumptions, {**ASSUMPTIONS_OK, "wacc": 9.0}))
check("champ manquant REJETÉ (pas de défaut silencieux)",
      rejette(Assumptions, {"croissance_revenue_pct": 12.0, "multiple_sortie": 18.0}))

print("\n§3 — Assumptions : les valeurs négatives restent licites")
neg = Assumptions(croissance_revenue_pct=-4.0, expansion_marge_fcf_pct=-2.0, multiple_sortie=11.0)
check("décroissance (-4.0 %/an) acceptée", neg.croissance_revenue_pct == -4.0)
check("compression de marge (-2.0 pts) acceptée", neg.expansion_marge_fcf_pct == -2.0)

print("\n§4 — ReverseDcf : la croissance implicite est REQUISE (jamais null/omise)")
check("champ omis REJETÉ", rejette(ReverseDcf, {"verdict": "le prix price déjà 22%/an"}))
check("champ null REJETÉ",
      rejette(ReverseDcf, {"croissance_implicite_prix_actuel_pct": None, "verdict": "…"}))
rd = ReverseDcf(croissance_implicite_prix_actuel_pct=22.0, verdict="…")
check("valeur chiffrée acceptée", rd.croissance_implicite_prix_actuel_pct == 22.0)

print("\n§5 — ValorisationCote : horizon long terme et assumptions imbriquées")
VALO_OK = {"horizon_ans": 5,
           "reverse_dcf": {"croissance_implicite_prix_actuel_pct": 22.0, "verdict": "…"},
           "scenarios": {"bear": 95.0, "base": 130.0, "bull": 165.0},
           "methode": "FCF normalisé + exit multiple ; actualisation à 9% (prose)",
           "assumptions": ASSUMPTIONS_OK}
v = ValorisationCote(**VALO_OK)
check("valorisation complète acceptée", v.assumptions.croissance_revenue_pct == 12.0)
check("horizon < 5 ans REJETÉ (A4)", rejette(ValorisationCote, {**VALO_OK, "horizon_ans": 3}))
check("assumptions à l'ancien nom REJETÉES à travers la valorisation",
      rejette(ValorisationCote, {**VALO_OK,
                                 "assumptions": {"croissance_revenue": 0.12,
                                                 "expansion_marge_fcf": 0.02,
                                                 "multiple_sortie": 18.0}}))

print("\n§6 — Règle #19 : contrat figé et copie runtime déclarent les mêmes champs")
FROZEN = Path("/contract_frozen/analysis_v2_schemas.py")
if FROZEN.exists():
    src = FROZEN.read_text(encoding="utf-8")
    for nom in ("croissance_revenue_pct", "expansion_marge_fcf_pct"):
        check(f"contrat figé porte `{nom}`", nom in src)
    for ancien in ("croissance_revenue:", "expansion_marge_fcf:"):
        check(f"contrat figé ne porte plus `{ancien.rstrip(':')}` nu", ancien not in src)
else:
    print("  ---- contrat figé non monté (/contract_frozen) : comparaison NON faite.")
    print("       monter avec -v <repo>/roadmap/provenance-cards:/contract_frozen:ro")

print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
