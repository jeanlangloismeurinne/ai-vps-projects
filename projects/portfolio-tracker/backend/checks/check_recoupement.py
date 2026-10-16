"""Vérification de « tout chiffre renvoie à une pièce » (#136, `app/agents/v2/recoupement.py`). Pur :
sans réseau, sans modèle, sans base. Fixture COPIÉE DU RÉEL (`fixtures/recoupement_reel.json`) : deux
réponses en vigueur au 2026-10-16 et le titre + contenu de leurs pièces citées.

  • §1 LE CAS RÉEL — NVDA me_6 #1371 : « 70 % » et « 4,5 Md$ » n'ont pas de pièce citée ; « 92,4 % » en
       a une (#1014, fiche rédigée en français) ; « 22 % », « 14 % », « 279 Md$ », la date et « FY2026 »
       ne sont pas signalés.
  • §2 LES REMÈDES — citer la pièce efface le chiffre ; un calcul MONTRÉ et juste aussi ; un calcul faux
       (terme absent de sa pièce, pièce non citée, formule qui ne nomme pas ses termes, exercice décalé)
       est ÉCARTÉ et nommé, et son chiffre reste sans pièce.
  • §3 CE QUI N'EST PAS UN CHIFFRE À SOURCER — l'encadré (RVMD qf_4 #1378 : 1 036,0 et 3 938,0), un
       libellé collé, le jour d'une date (l'année, si), le numéro d'une pièce citée, une hypothèse
       déclarée d'approximation.
  • §4 LE POINT DE LECTURE — `servir_answer` rend les chiffres sans pièce, recalculés.
  • §5 DÉTENTEUR UNIQUE — l'analyste, le point de lecture et l'outil lisent `recoupement.recouper`.
"""
import copy
import inspect
import json
from pathlib import Path

from checks._harness import Bilan

from app.agents.v2 import analyste as A
from app.agents.v2 import frameworks as FW
from app.agents.v2.recoupement import recouper, valeurs_du_texte
from app.knowledge.material_events import MaterialEventLookup

b = Bilan()
FIX = json.loads((Path(__file__).parent / "fixtures/recoupement_reel.json").read_text(encoding="utf-8"))
PIECES = {int(k): v for k, v in FIX["pieces"].items()}
ME6 = FIX["reponses"]["1371"]
QF4 = FIX["reponses"]["1378"]


def jetons(a, entries=PIECES):
    return sorted(c.jeton for c in recouper(a, entries).sans_piece)


def avec(a, **reponse):
    a = copy.deepcopy(a)
    a["reponse"].update(reponse)
    return a


def citant(a, *ids):
    a = copy.deepcopy(a)
    a["fondation"]["cited_entry_ids"] = list(a["fondation"]["cited_entry_ids"]) + list(ids)
    return a


# ── §1 le cas réel ──────────────────────────────────────────────────────────────────────────────
print("[1] NVDA me_6 #1371, telle qu'en base")
r = recouper(ME6, PIECES)
b.check(jetons(ME6) == ["4,5", "70"],
        f"seuls « 4,5 » (charge Chine) et « 70 » (comptes clients) sont sans pièce — obtenu {jetons(ME6)}")
b.check(92.4 in valeurs_du_texte(PIECES[1014]["content"]),
        "une fiche rédigée en français se lit en français : « 92,4 % » de #1014 est une valeur de la pièce")
b.check(all(c.extrait and c.jeton in c.extrait for c in r.sans_piece),
        "chaque chiffre sans pièce porte l'extrait où il figure (le comité lit la phrase, pas un nombre nu)")

# ── §2 les remèdes ──────────────────────────────────────────────────────────────────────────────
print("[2] citer, montrer le calcul — ou rester signalé")
b.check(jetons(citant(ME6, 1088), {**PIECES}) == ["4,5"],
        "citer une pièce qui porte « 70 » efface « 70 » (la garde vérifie la STRUCTURE, jamais le sens, #68)")
_PART = {"libelle": "part du Data Center", "formule": "data_center / total * 100",
         "termes": [{"nom": "data_center", "valeur": 164269, "entry_id": 1014},
                    {"nom": "total", "valeur": 177837, "entry_id": 1014}]}
_v = avec(ME6, verbatim=ME6["reponse"]["verbatim"].replace("92,4 %", "92,37 %"), calculs=[_PART])
b.check("92,37" not in jetons(_v) and recouper(_v, PIECES).n_calcul == 1,
        f"un calcul MONTRÉ et juste établit son chiffre (92,37 % = 164 269 / 177 837) — {jetons(_v)}")
_sans = avec(ME6, verbatim=ME6["reponse"]["verbatim"].replace("92,4 %", "92,37 %"))
b.check("92,37" in jetons(_sans), "… et sans le calcul, le même chiffre est sans pièce (témoin)")


def ecarte(calc, fragment, label):
    rr = recouper(avec(_sans, calculs=[calc]), PIECES)
    b.check("92,37" in [c.jeton for c in rr.sans_piece] and any(fragment in m for m in rr.calculs_refuses),
            f"{label} — motifs {rr.calculs_refuses}")


ecarte({**_PART, "termes": [{**_PART["termes"][0], "valeur": 164000}, _PART["termes"][1]]},
       "ne figure pas dans la pièce [1014]", "un terme ABSENT de sa pièce écarte le calcul")
ecarte({**_PART, "termes": [{**_PART["termes"][0], "entry_id": 1088}, _PART["termes"][1]]},
       "n'est pas citée", "un terme tiré d'une pièce NON CITÉE écarte le calcul")
ecarte({**_PART, "formule": "data_center / chiffre_total * 100"}, "la formule nomme",
       "une formule qui ne nomme pas exactement ses termes écarte le calcul")
ecarte({**_PART, "formule": "data_center / total[-1] * 100"}, "exercice décalé",
       "un exercice décalé écarte le calcul (chaque terme se cite avec SA valeur)")
ecarte({**_PART, "formule": "data_center / total ** 2"}, "ne s'exécute pas",
       "une formule hors grammaire écarte le calcul")

# ── §3 ce qui n'est pas un chiffre à sourcer ────────────────────────────────────────────────────
print("[3] encadré, libellés, dates, renvois, hypothèses")
r4 = recouper(QF4, PIECES)
b.check(r4.n_encadre >= 2 and not ({"1 036,0", "3 938,0"} & {c.jeton for c in r4.sans_piece}),
        f"RVMD qf_4 : la dette brute et la trésorerie de l'ENCADRÉ (établies par le code) ne sont pas sans "
        f"pièce — encadré {r4.n_encadre}, sans pièce {sorted(c.jeton for c in r4.sans_piece)}")
b.check("2 902,0" in {c.jeton for c in r4.sans_piece},
        "… mais la trésorerie nette écrite dans le texte (3 938,0 − 1 036,0), calcul non montré, l'est")
_net = {"libelle": "trésorerie nette", "formule": "tresorerie - dette",
        "termes": [{"nom": "tresorerie", "valeur": 3938.0, "entry_id": 876},
                   {"nom": "dette", "valeur": 1036.0, "entry_id": 876}]}
b.check("2 902,0" not in jetons(avec(QF4, calculs=[_net])),
        "… et le montrer suffit : un terme repris de l'encadré vaut sa pièce (le socle cité)")
_lib = avec(ME6, verbatim="Au 31 décembre 2019, FY2031 et le 10-K (pièce 1013) le disent.")
b.check(jetons(_lib) == ["2019"],
        f"le jour d'une date, un libellé collé et le numéro d'une pièce citée ne sont pas des chiffres ; "
        f"l'ANNÉE d'une date en est un — obtenu {jetons(_lib)}")
_hyp = avec(ME6, verbatim="Dépendance notable.")
_hyp["approximation"] = {"methode": "rapport des deux chiffres déposés", "ingredients_entry_ids": [1013],
                         "hypotheses_explicites": ["croissance de 37 % par an"], "sensibilite": "±12 points"}
b.check(jetons(_hyp) == [], f"une hypothèse DÉCLARÉE n'est pas un fait à sourcer — obtenu {jetons(_hyp)}")
_meth = copy.deepcopy(_hyp)
_meth["approximation"]["methode"] = "rapport sur 37 trimestres"
b.check(jetons(_meth) == ["37"], f"… mais la MÉTHODE l'est — obtenu {jetons(_meth)}")
_fait = avec(ME6, verbatim="Dépendance notable.", faits_posterieurs=[
    {"depot": "0001045810-26-000078", "effet": "acquisition de 13,7 Md$ sans effet", "cited_entry_ids": [1010]}])
b.check(jetons(_fait) == ["13,7"], f"l'effet d'un fait postérieur est contrôlé — obtenu {jetons(_fait)}")

# ── §4 le point de lecture ──────────────────────────────────────────────────────────────────────
print("[4] le comité voit les chiffres sans pièce, recalculés")
from app.contracts.framework_answer_schema import FrameworkAnswer  # noqa: E402

_ans = FrameworkAnswer.model_validate(ME6)
_serv = FW.servir_answer(_ans, ancre=MaterialEventLookup(status="unavailable", raison="hors ligne"),
                         entries=PIECES, durees=None)
b.check([s.split(" — ")[0] for s in _serv.chiffres_sans_piece] == ["70", "4,5"],
        f"`servir_answer` rend les chiffres sans pièce — obtenu {_serv.chiffres_sans_piece}")
_serv2 = FW.servir_answer(_ans, ancre=MaterialEventLookup(status="unavailable", raison="hors ligne"),
                          entries={**PIECES, 1013: {**PIECES[1013], "content": PIECES[1013]["content"] + " 70 %"}},
                          durees=None)
b.check([s.split(" — ")[0] for s in _serv2.chiffres_sans_piece] == ["4,5"],
        "… RECALCULÉS contre le dossier du moment, jamais lus dans la réponse stockée (#77)")

# ── §5 détenteur unique ─────────────────────────────────────────────────────────────────────────
print("[5] une règle, un détenteur")
_outil = (Path(__file__).parent.parent / "tools/recouper_nombres.py").read_text(encoding="utf-8")
b.check("from app.agents.v2.recoupement import" in _outil and "def retrouve" not in _outil
        and "def nombres" not in _outil, "l'outil lit le détenteur, il ne recopie pas la règle (#46)")
b.check("recouper(" in inspect.getsource(A.chiffres_a_renvoyer)
        and "recouper(" in inspect.getsource(FW.servir_answer),
        "l'analyste (la remarque) et le point de lecture (le signalement) appellent `recouper`")

raise SystemExit(b.summary())
