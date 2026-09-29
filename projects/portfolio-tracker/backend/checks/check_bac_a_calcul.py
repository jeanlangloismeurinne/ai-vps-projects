"""Vérification de l'ATELIER DE VALORISATION — gabarits maison + bac à calcul (#96, roadmap 05 cap. 4 bis).

Sans réseau, sans modèle, sans base. Ce que ce check garde :

  • §1 LES GABARITS DONNENT LES VALEURS CALCULÉES À LA MAIN — et chaque valeur attendue est écrite en
       arithmétique brute dans ce fichier, JAMAIS en rappelant le gabarit (4ᵉ faux vert : un assert
       écrit depuis sa propre fonction est vert quoi qu'elle calcule). Les cas de référence sont ceux
       dont la réponse est connue sans calcul : une perpétuité de 10 à 10 % vaut 100.
  • §2 LES GABARITS REFUSENT LEUR HORS-DOMAINE, avec le motif attendu (pas « un refus quelconque »).
  • §3 DEUX MÉCANIQUES D'ENTREPRISE DIFFÉRENTES — somme des programmes pondérée (biotech, forme RVMD)
       et segments (forme NVDA) — s'exécutent dans le bac, rendent la valeur calculée à la main, et
       un changement d'hypothèse recalcule sans aucun appel au modèle. Au cours du jour, la marge de
       sécurité change sans que la fourchette bouge (option 1, acceptation de la capacité 4 bis).
       ⚠️ Les chiffres des deux fixtures sont FICTIFS : ils éprouvent la mécanique, pas les titres.
  • §4 LE TABLEAU SIGNÉ EST INTOUCHABLE — la mécanique ne réécrit une hypothèse ni par son nom, ni par
       un alias, ni par un gabarit qui recevrait l'objet (arbitrage : le comité juge le tableau).
  • §5 BATTERIE HOSTILE — chaque programme sort en `ErreurCalcul` nommée, JAMAIS en succès ni en une
       autre exception, et en temps borné. C'est la frontière de sécurité : la mécanique est écrite par
       un agent qui a lu du web.
  • §6 STRUCTURE — le bac n'importe que ce qu'il déclare et n'appelle ni `eval`, ni `exec`, ni
       `compile`, ni `__import__`, ni `getattr`, ni `open` (AST + code dépouillé, #56) ; le catalogue
       exposé EST l'ensemble des gabarits publics de `calculs.py`, dans les deux sens.

Cible : Python 3.12 (container). Tester en container, **pas** le python hôte.
"""
from __future__ import annotations

import ast
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _harness import Bilan, strip_code  # noqa: E402

from app.valorisation import calculs  # noqa: E402
from app.valorisation.bac_a_calcul import FONCTIONS, ErreurCalcul, executer  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
BAC = BACKEND / "app" / "valorisation" / "bac_a_calcul.py"
CALCULS = BACKEND / "app" / "valorisation" / "calculs.py"

b = Bilan()


def proche(a: object, attendu: float, tol: float = 1e-9) -> bool:
    return isinstance(a, (int, float)) and abs(a - attendu) <= tol * max(1.0, abs(attendu))


def refus(fn, *args, **kw) -> str:
    """Le motif du refus, ou une phrase qui NOMME l'absence de refus — jamais la mort du script."""
    try:
        r = fn(*args, **kw)
    except ErreurCalcul as e:
        return e.motif
    except Exception as e:  # noqa: BLE001 — une autre exception est précisément un FAIL à nommer
        return f"AUTRE EXCEPTION {type(e).__name__}: {e}"
    return f"PAS DE REFUS (rendu {r!r})"


def lancer(code: str, hypotheses: dict, **kw):
    """Le résultat, ou le motif du refus — un refus inattendu est un FAIL nommé, pas une mort."""
    try:
        return executer(code, hypotheses, **kw)
    except ErreurCalcul as e:
        return f"REFUSÉ : {e}"


# ── §1 Les gabarits donnent les valeurs calculées à la main ─────────────────────────────────────
print("§1 gabarits — valeurs à la main")
b.check(proche(calculs.valeur_sans_croissance(100, 0.08), 100 / 0.08), "valeur sans croissance = bénéfice / coût du capital")
b.check(proche(calculs.valeur_terminale(10, 0.08, 0.02), 10 * 1.02 / 0.06), "Gordon : 10 × 1,02 / 6 % = 170")
b.check(proche(calculs.actualiser([110], 0.1), 100.0), "110 dans un an à 10 % vaut 100")
b.check(proche(calculs.actualiser([121], 0.1, annee_depart=2), 100.0), "121 dans deux ans à 10 % vaut 100")
b.check(proche(calculs.dcf([10, 10], 0.1, 0.0), 100.0), "DCF d'une perpétuité de 10 à 10 % = 100")
b.check(proche(calculs.dcf([5, 5, 5], 0.05, 0.0), 100.0), "le nombre d'années explicites ne change pas une perpétuité")
fl = calculs.flux_en_croissance(100, 0.1, 2)
b.check(len(fl) == 2 and proche(fl[0], 110) and proche(fl[1], 121), f"flux en croissance : premier flux = initial × (1+g) ({fl})")
b.check(proche(calculs.croissance_implicite(100, 10, 0.1, 5, 0.0), 0.0, 1e-7) or abs(calculs.croissance_implicite(100, 10, 0.1, 5, 0.0)) < 1e-7,
        "un prix égal à la perpétuité sans croissance suppose une croissance nulle")
# Aller-retour : la valeur construite À LA MAIN (pas par `dcf`) à 7 % redonne 7 %.
r, g, gt, n = 0.09, 0.07, 0.02, 5
flux = [10 * (1 + g) ** k for k in range(1, n + 1)]
valeur_main = sum(f / (1 + r) ** (i + 1) for i, f in enumerate(flux)) + flux[-1] * (1 + gt) / (r - gt) / (1 + r) ** n
b.check(abs(calculs.croissance_implicite(valeur_main, 10, r, n, gt) - g) < 1e-7, "croissance implicite : l'aller-retour à 7 % redonne 7 %")
b.check(proche(calculs.valeur_ponderee(0.3, 1000, 50), 0.3 * 1000 - 50), "valeur pondérée = p × valeur si succès − coût restant")
b.check(proche(calculs.valeur_fonds_propres(500, -100), 600), "une trésorerie nette (dette nette négative) s'ajoute")
b.check(proche(calculs.dilution(90, 10), 0.1), "10 actions nouvelles sur 90 = 10 % du capital")
b.check(proche(calculs.valeur_par_action(1000, calculs.actions_diluees(90, 10)), 10), "par action DILUÉE : 1000 / 100")
b.check(proche(calculs.marge_de_securite(80, 100), 0.2), "prix 80 pour une valeur de 100 : 20 % de marge")
b.check(proche(calculs.marge_de_securite(120, 100), -0.2), "prix au-dessus de la valeur : marge négative, pas tronquée")
b.check(calculs.fourchette(1, 2, 3) == {"bas": 1.0, "central": 2.0, "haut": 3.0}, "fourchette ordonnée rendue telle quelle")

# ── §2 Hors-domaine refusé, avec son motif ──────────────────────────────────────────────────────
print("§2 gabarits — hors-domaine")
cas_refus = [
    ("croissance perpétuelle ≥ taux", lambda: calculs.valeur_terminale(10, 0.02, 0.02), "diverge"),
    ("coût du capital nul", lambda: calculs.valeur_sans_croissance(100, 0), "strictement positif"),
    ("probabilité > 1", lambda: calculs.valeur_ponderee(1.4, 100), "entre 0 et 1"),
    ("probabilité < 0", lambda: calculs.valeur_ponderee(-0.1, 100), "entre 0 et 1"),
    ("marge sur valeur nulle", lambda: calculs.marge_de_securite(80, 0), "valeur positive"),
    ("croissance implicite sans flux positif", lambda: calculs.croissance_implicite(100, -5, 0.1, 5, 0.0), "flux initial ≤ 0"),
    ("croissance implicite hors bornes", lambda: calculs.croissance_implicite(1e12, 10, 0.1, 5, 0.0), "hors de"),
    ("fourchette croisée", lambda: calculs.fourchette(3, 2, 1), "non ordonnée"),
    ("zéro année", lambda: calculs.flux_en_croissance(10, 0.1, 0), "entre 1 et 100"),
    ("flux vide", lambda: calculs.dcf([], 0.1, 0.0), "liste non vide"),
    ("booléen pris pour un nombre", lambda: calculs.valeur_sans_croissance(True, 0.1), "doit être un nombre"),
    ("nombre non fini", lambda: calculs.valeur_sans_croissance(float("nan"), 0.1), "fini"),
    ("zéro action", lambda: calculs.valeur_par_action(100, 0), "≤ 0"),
]
for label, fn, motif in cas_refus:
    m = refus(fn)
    b.check(motif in m, f"refus « {label} » — motif attendu « {motif} », obtenu « {m} »")

# ── §3 Deux mécaniques d'entreprise différentes ─────────────────────────────────────────────────
print("§3 mécaniques propres à l'entreprise")
MECANIQUE_PROGRAMMES = """
valeurs = {}
for nom in programmes:
    p = programmes[nom]
    flux = [p["ventes_pic"] * marge_nette for _ in range(p["duree_exclusivite"])]
    si_succes = actualiser(flux, cout_du_capital, p["annee_lancement"])
    valeurs[nom] = valeur_ponderee(p["probabilite"], si_succes, p["cout_restant"])
valeur_pipeline = sum([valeurs[n] for n in valeurs])
valeur_actionnaires = valeur_fonds_propres(valeur_pipeline, dette_nette)
par_action = valeur_par_action(valeur_actionnaires, actions_diluees(actions, actions_potentielles))
_intermediaire = 1
"""
HYP_PROGRAMMES = {
    "programmes": {
        "programme_a": {"probabilite": 0.5, "ventes_pic": 100, "duree_exclusivite": 2, "annee_lancement": 1, "cout_restant": 0},
        "programme_b": {"probabilite": 1.0, "ventes_pic": 50, "duree_exclusivite": 1, "annee_lancement": 2, "cout_restant": 5},
    },
    "marge_nette": 0.3, "cout_du_capital": 0.1, "dette_nette": -10, "actions": 10, "actions_potentielles": 0,
}
a_main = 0.5 * (30 / 1.1 + 30 / 1.1 ** 2)
b_main = 1.0 * (15 / 1.1 ** 2) - 5
res = lancer(MECANIQUE_PROGRAMMES, HYP_PROGRAMMES)
ok = b.check(not isinstance(res, str), f"somme des programmes : s'exécute ({res if isinstance(res, str) else 'ok'})")
if ok:
    s = res.sorties
    b.check(proche(s.get("valeurs", {}).get("programme_a"), a_main), "programme A = p × VA des ventes nettes")
    b.check(proche(s.get("valeur_pipeline"), a_main + b_main), "pipeline = somme des programmes")
    b.check(proche(s.get("par_action"), (a_main + b_main + 10) / 10), "par action, trésorerie nette ajoutée")
    b.check("_intermediaire" not in s, "un nom en `_` n'est pas une sortie")
    b.check("programmes" not in s and "marge_nette" not in s, "les hypothèses ne sont pas rendues comme sorties")
    b.check(res.operations > 0, "le nombre d'opérations est compté")
    b.check(HYP_PROGRAMMES["programmes"]["programme_a"]["probabilite"] == 0.5, "le tableau de l'appelant n'est pas modifié")
    # Changer UNE hypothèse recalcule — même mécanique, aucun modèle.
    hyp2 = {**HYP_PROGRAMMES, "programmes": {**HYP_PROGRAMMES["programmes"],
            "programme_a": {**HYP_PROGRAMMES["programmes"]["programme_a"], "probabilite": 0.8}}}
    res2 = lancer(MECANIQUE_PROGRAMMES, hyp2)
    b.check(not isinstance(res2, str) and proche(res2.sorties["valeur_pipeline"], 0.8 * (30 / 1.1 + 30 / 1.1 ** 2) + b_main),
            "probabilité de A passée à 0,8 : le pipeline se recalcule")
    b.check(executer(MECANIQUE_PROGRAMMES, HYP_PROGRAMMES).sorties == s, "même mécanique, mêmes hypothèses : même résultat")

MECANIQUE_SEGMENTS = """
annees = 3
flux_total = [0.0 for _ in range(annees)]
for nom in segments:
    seg = segments[nom]
    flux_seg = flux_en_croissance(seg["ca"] * seg["marge_fcf"], seg["croissance"], annees)
    flux_total = [flux_total[i] + flux_seg[i] for i in range(annees)]
bas = dcf(flux_total, cout_du_capital + ecart_de_taux, croissance_terminale)
central = dcf(flux_total, cout_du_capital, croissance_terminale)
haut = dcf(flux_total, cout_du_capital - ecart_de_taux, croissance_terminale)
va_2 = fourchette(bas, central, haut)
va_6 = marge_de_securite(prix, central)
"""
HYP_SEGMENTS = {
    "segments": {"centres_de_donnees": {"ca": 100, "marge_fcf": 0.5, "croissance": 0.2},
                 "jeux": {"ca": 20, "marge_fcf": 0.25, "croissance": 0.0}},
    "cout_du_capital": 0.1, "ecart_de_taux": 0.01, "croissance_terminale": 0.03, "prix": 600,
}


def dcf_main(r: float) -> float:
    fl = [50 * 1.2 ** k + 5 for k in (1, 2, 3)]
    return sum(f / (1 + r) ** (i + 1) for i, f in enumerate(fl)) + fl[-1] * 1.03 / (r - 0.03) / (1 + r) ** 3


res = lancer(MECANIQUE_SEGMENTS, HYP_SEGMENTS)
ok = b.check(not isinstance(res, str), f"segments : s'exécute ({res if isinstance(res, str) else 'ok'})")
if ok:
    s = res.sorties
    b.check(proche(s.get("central"), dcf_main(0.1)), "segments : central = DCF des flux sommés, calculé à la main")
    b.check(s.get("va_2", {}).get("bas", 0) < s["central"] < s.get("va_2", {}).get("haut", 0), "segments : bas < central < haut")
    b.check(proche(s.get("va_6"), (dcf_main(0.1) - 600) / dcf_main(0.1)), "segments : marge de sécurité au prix du tableau")
    # Option 1 : au cours du jour, va_6 change, va_2 ne bouge pas.
    res_cours = lancer(MECANIQUE_SEGMENTS, {**HYP_SEGMENTS, "prix": 700})
    b.check(not isinstance(res_cours, str) and res_cours.sorties["va_2"] == s["va_2"], "nouveau cours : la fourchette ne bouge pas")
    b.check(not isinstance(res_cours, str) and not proche(res_cours.sorties["va_6"], s["va_6"]), "nouveau cours : la marge de sécurité change")
    # Les deux mécaniques sont réellement différentes : aucune n'accepte le tableau de l'autre.
    b.check(isinstance(lancer(MECANIQUE_SEGMENTS, HYP_PROGRAMMES), str), "la mécanique par segments refuse le tableau d'une biotech")

# ── §4 Le tableau signé est intouchable ─────────────────────────────────────────────────────────
print("§4 tableau signé")
signe = {"taux": 0.1, "marges": {"a": 0.2}, "liste": [1, 2]}
cas_signe = [
    ("réaffectation d'une hypothèse", "taux = 0.5", "tableau signé"),
    ("augmentation d'une hypothèse", "taux += 0.5", "tableau signé"),
    ("indice sur une hypothèse", 'marges["a"] = 0.9', "tableau signé"),
    ("alias d'un dictionnaire signé", 'x = marges\nx["a"] = 0.9', "tableau signé"),
    ("alias d'une liste signée", "x = liste\nx[0] = 9", "n'accepte pas"),
    ("variable de boucle sur une hypothèse", "for taux in [1]:\n    pass", "tableau signé"),
    ("variable de compréhension sur une hypothèse", "x = [1 for taux in [1]]", "tableau signé"),
    ("réaffectation d'un gabarit", "dcf = 3", "gabarit"),
]
for label, code, motif in cas_signe:
    r = lancer(code, signe)
    b.check(isinstance(r, str) and motif in r, f"{label} — refus attendu « {motif} », obtenu « {r if isinstance(r, str) else r.sorties} »")
r = lancer('y = marges["a"]\nz = sum(liste)', signe)
b.check(not isinstance(r, str) and r.sorties == {"y": 0.2, "z": 3}, "une hypothèse se LIT normalement")
b.check(signe == {"taux": 0.1, "marges": {"a": 0.2}, "liste": [1, 2]}, "le tableau de l'appelant est intact après les tentatives")
for nom in ("dcf", "1taux", "for", "sum"):
    b.check(isinstance(lancer("x = 1", {nom: 1}), str), f"nom d'hypothèse non admis refusé : {nom!r}")
b.check(isinstance(lancer("x = 1", {"objet": object()}), str), "une hypothèse porteuse de comportement est refusée")

# ── §5 Batterie hostile ─────────────────────────────────────────────────────────────────────────
print("§5 batterie hostile")
HOSTILES = {
    "import": "import os",
    "from import": "from os import system",
    "__import__": "x = __import__('os')",
    "attribut dunder": "x = ().__class__",
    "attribut simple": "x = (1).real",
    "méthode": "x = []\nx.append(1)",
    "def": "def f():\n    return 1",
    "lambda": "f = lambda: 1",
    "class": "class A:\n    pass",
    "while": "while True:\n    x = 1",
    "open": "x = open('/etc/passwd')",
    "eval": "x = eval('1')",
    "exec": "exec('x = 1')",
    "getattr": "x = getattr(1, 'real')",
    "globals": "x = globals()",
    "__builtins__": "x = __builtins__",
    "try": "try:\n    x = 1\nexcept Exception:\n    x = 2",
    "with": "with x:\n    pass",
    "global": "global x",
    "del": "x = 1\ndel x",
    "assert": "assert False",
    "annotation": "x: int = 1",
    "chaîne formatée": "x = f'{1}'",
    "concaténation de textes": "x = 'a' + 'b'",
    "répétition de liste": "x = [1] * 10",
    "fonction comme valeur": "x = sum",
    "étoile": "x = max(*[1, 2])",
    "double étoile": "x = fourchette(**{'bas': 1, 'central': 2, 'haut': 3})",
    # Ni gardé ni passé à une fonction : gardée, la liste serait refusée par le compte des sorties ;
    # passée à `len`, par le coût d'appel. Seul un indice ne coûte rien — c'est donc le seul cas où
    # le plafond de `range` décide. Et c'est lui qui protège la MÉMOIRE : le budget ne voit une
    # liste qu'une fois allouée (`range(10 ** 9)` = 8 Go sur un VPS de 3,8 Go).
    "range géant": "x = range(10 ** 6)[0]",
    "débordement flottant": "x = 1e308 * 10",
    "puissance géante": "x = 10 ** 10 ** 10",
    "littéral géant": "x = 1" + "0" * 400,
    "racine d'un négatif": "x = (-8) ** 0.5",
    "division par zéro": "x = 1 / 0",
    "modulo par zéro": "x = 1 % 0",
    "boucle qui épuise le budget": "x = 0\nfor i in range(1000):\n    for j in range(1000):\n        x += 1",
    "fuite de compréhension": "x = [y for y in range(3)]\nz = y",
    "nom inconnu": "x = inconnu + 1",
    "condition non booléenne": "if 1:\n    x = 1",
    "comparaison de structures": "a = [1]\nb2 = [1]\nc = a == b2",
    "structure qui se partage elle-même": "x = [1]\nfor i in range(40):\n    x = [x, x]",
    "imbrication profonde": "x = " + "(" * 5000 + "1" + ")" * 5000,
    "somme non numérique": "x = sum(5)",
    "appel mal formé": "x = dcf(1)",
    "croissance implicite en boucle": "x = 0\nfor i in range(100):\n    x = croissance_implicite(100, 10, 0.1, 5, 0.0)",
    "indice hors liste": "x = [1, 2][5]",
    "clé absente": "x = {'a': 1}['b']",
    "yield": "x = (yield 1)",
    "await": "x = await y",
    "walrus": "x = (y := 1)",
    "ensemble": "x = {1, 2}",
    "octets": "x = b'a'",
    "None": "x = None",
    "slice à pas": "x = [1, 2, 3][::-1]",
    "code non textuel": 12,
    "code trop long": "x = 1\n" * 5000,
    "syntaxe invalide": "x = = 1",
}
b.require(HOSTILES, 57, "batterie hostile complète")
for label, code in HOSTILES.items():
    t0 = time.monotonic()
    try:
        r = executer(code, {})  # type: ignore[arg-type]
        # Jamais le `repr` des sorties : une structure qui se partage elle-même serait exponentielle.
        issue = f"SUCCÈS (sorties : {sorted(r.sorties)})"
    except ErreurCalcul as e:
        issue = "refus"
        b.check(bool(e.motif), f"hostile « {label} » : le refus porte un motif")
    except Exception as e:  # noqa: BLE001
        issue = f"AUTRE EXCEPTION {type(e).__name__}: {e}"[:160]
    duree = time.monotonic() - t0
    b.check(issue == "refus", f"hostile « {label} » : ErreurCalcul attendue, obtenu {issue}")
    b.check(duree < 5.0, f"hostile « {label} » : borné dans le temps ({duree:.1f} s)")

r = lancer("x = 1\ny = x + 1", {})
b.check(not isinstance(r, str) and r.sorties == {"x": 1, "y": 2}, "un programme admis passe (la batterie ne refuse pas tout)")
# Le plafond de `range` refuse AVANT d'allouer. Toute liste rendue par une fonction est ensuite
# revalidée — mais une fois allouée : `range(10 ** 9)` aurait déjà pris 8 Go. Le motif distingue les
# deux (« range de N éléments » ≠ « plus de N éléments »), c'est ce qui rend le plafond éprouvable.
m = refus(FONCTIONS["range"], 10 ** 6)
b.check("range de 1000000 éléments" in m, f"le plafond de range refuse AVANT d'allouer ({m[:80]})")
r = lancer("x = 0\nfor i in range(100):\n    x += i", {}, budget=50)
b.check(isinstance(r, str) and "budget" in r, "le budget se règle par appel")
r = lancer("x = open('/etc/passwd')", {})
b.check(isinstance(r, str) and "fonction non admise : `open`" in r, f"une fonction hors liste est refusée en la NOMMANT ({r})")
r = lancer('x = marges\nx["a"] = 0.9', {"marges": {"a": 0.2}})
b.check(isinstance(r, str) and r.startswith("REFUSÉ : ligne 2"), f"un refus du tableau gelé est situé à sa ligne ({r})")
r = lancer("x = 1\ny = x / 0", {})
b.check(isinstance(r, str) and r.startswith("REFUSÉ : ligne 2"), f"le refus situe la ligne fautive ({r})")

# ── §6 Structure ────────────────────────────────────────────────────────────────────────────────
print("§6 structure")
source_bac = BAC.read_text(encoding="utf-8")
code_bac = strip_code(source_bac)
for interdit in ("eval(", "exec(", "compile(", "__import__", "getattr(", "setattr(", "open(", "globals(", "vars("):
    b.check(interdit not in code_bac, f"le bac n'emploie pas `{interdit}` (code dépouillé)")
b.check("eval" in source_bac and "exec" in source_bac, "la prose du bac NOMME l'interdit (miroir positif, #56)")


def modules_importes(path: Path) -> set[str]:
    mods: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            mods |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            mods.add(node.module or "")
    return mods


b.check(modules_importes(BAC) == {"__future__", "ast", "copy", "keyword", "math", "dataclasses", "typing", "app.valorisation.calculs"},
        f"le bac n'importe que sa liste déclarée ({sorted(modules_importes(BAC))})")
b.check(modules_importes(CALCULS) == {"__future__", "math"}, f"les gabarits sont purs ({sorted(modules_importes(CALCULS))})")

publics = {n.name for n in ast.parse(CALCULS.read_text(encoding="utf-8")).body
           if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")}
b.require(publics, 13, "gabarits publics de calculs.py")
b.check(set(calculs.CATALOGUE) == publics, f"catalogue = gabarits publics (écart : {sorted(set(calculs.CATALOGUE) ^ publics)})")
b.check(set(calculs.CATALOGUE) <= set(FONCTIONS), "tout gabarit du catalogue est appelable dans le bac")
b.check(all(FONCTIONS[n] is calculs.CATALOGUE[n] for n in calculs.CATALOGUE), "le bac expose les gabarits eux-mêmes, pas des copies")

sys.exit(b.summary())
