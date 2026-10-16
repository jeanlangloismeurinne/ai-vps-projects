"""Tout chiffre renvoie à une pièce (#136, inventaire avant comité 1.6, arbitrage du 2026-10-16).

CE QUE FAIT UN VRAI FONDS
-------------------------
Avant le comité, le contrôle de la note renvoie à l'analyste tout chiffre sans référence : l'analyste
cite sa source, ou montre son calcul, ou retire le chiffre. Personne ne pose la note de bas de page à
sa place — un chiffre qui figure dans plusieurs pièces (« 70 % » est dans quatre pièces de NVIDIA) ne
dit pas laquelle le fonde.

CE QUE LE MODULE JUGE, ET CE QU'IL NE JUGE PAS
---------------------------------------------
Pur, sans modèle ni base. Chaque nombre du texte RÉDIGÉ d'une réponse (le `verbatim`, l'effet de chaque
fait postérieur, la méthode d'une approximation) doit se retrouver :
  · dans une pièce CITÉE (titre + contenu, à l'arrondi de ses décimales écrites et à l'unité près) ;
  · ou dans l'ENCADRÉ de la réponse (établi par le code, depuis le socle ou par calcul — #101/#115) ;
  · ou comme résultat d'un CALCUL MONTRÉ valide (formule exécutable, chaque terme dans sa pièce citée
    ou dans l'encadré) ;
  · ou n'être pas un chiffre : un libellé collé à des lettres (« FY2025 », « 10-K », « 21 CFR »), le
    jour ou le mois d'une date, un entier < 10, le numéro d'une pièce citée.
Le reste est « sans pièce ». Les HYPOTHÈSES et la SENSIBILITÉ d'une approximation ne sont pas
contrôlées : ce sont des hypothèses déclarées comme telles, pas des faits à sourcer.

Le module vérifie que le chiffre EST dans une pièce citée, jamais qu'il y dit la même chose (#68) :
« 70 % » retrouvé dans une pièce citée passe même si la pièce parle d'autre chose. C'est la garde de
structure ; le sens reste à la lecture.

Détenteur unique, lu par l'analyste (la remarque renvoyée une fois), par le point de lecture
(`frameworks.servir_answer`, le signalement au comité) et par l'outil `tools/recouper_nombres.py`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from app.contracts.formule_grammaire import FormuleInexecutable, evaluer_formule, references_de_la_formule

_GROUPES = re.compile(r"\d{1,3}(?:[   ]\d{3}(?!\d))+(?:,\d+)?")
_SIMPLE = re.compile(r"\d+(?:[.,]\d+)*")
_FACTEURS = (1, 1e3, 1e-3, 1e6, 1e-6, 1e9, 1e-9)
_MOIS = ("janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|"
         "décembre|decembre|January|February|March|April|May|June|July|August|September|October|"
         "November|December")
# Le jour et le mois d'une date ne sont pas des chiffres ; l'ANNÉE, si (groupe nommé `annee`).
_DATES = re.compile(r"\b(?P<a1>\d{4})-\d{2}-\d{2}\b"
                    rf"|\b\d{{1,2}}(?:er)? (?:{_MOIS}) (?P<a2>\d{{4}})\b"
                    rf"|\b(?:{_MOIS}) \d{{1,2}}, (?P<a3>\d{{4}})\b")
# Le caractère COLLÉ compte, jamais un mot qui suit (« 302,97 Mds » est un chiffre).
_APRES_LIBELLE = re.compile(r"[A-Za-z]|-[A-Z]| CFR\b")


def _valeurs(jeton: str, francais: bool) -> list[tuple[float, int]]:
    """(valeur, nombre de décimales écrites) — plusieurs lectures si le séparateur est ambigu."""
    t = re.sub(r"[   ]", "", jeton)
    out: list[tuple[float, int]] = []
    if "," in t and "." in t:
        dec = "," if t.rfind(",") > t.rfind(".") else "."
        mil = "." if dec == "," else ","
        ent, _, fr = t.replace(mil, "").partition(dec)
        try:
            out.append((float(f"{ent}.{fr}"), len(fr)))
        except ValueError:
            pass
    elif "," in t or "." in t:
        sep = "," if "," in t else "."
        parts = t.split(sep)
        milliers = len(parts) > 1 and all(len(p) == 3 for p in parts[1:])
        if len(parts) == 2:
            # le séparateur décimal de la langue : virgule en français, point en anglais ;
            # l'autre ne sépare QUE des milliers (« 394,919 » anglais n'est jamais 394,919 décimal)
            if (sep == ",") == francais:
                out.append((float(f"{parts[0]}.{parts[1]}"), len(parts[1])))
            elif milliers:
                out.append((float("".join(parts)), 0))
        elif milliers:
            out.append((float("".join(parts)), 0))
    else:
        out.append((float(t), 0))
    return out


def nombres(texte: str, francais: bool) -> list[tuple[str, list[tuple[float, int]], int]]:
    """Les nombres de `texte`, dans l'ordre : (jeton, lectures, position). La position est rendue parce
    qu'un même jeton peut revenir — `find` désignerait toujours la première occurrence."""
    vus: list[tuple[int, str, list[tuple[float, int]]]] = []
    pris = [False] * len(texte)
    for rx in (_GROUPES, _SIMPLE):
        for m in rx.finditer(texte):
            if any(pris[m.start():m.end()]):
                continue
            jeton = m.group().rstrip(".,")  # un séparateur final (« 2026. ») n'appartient pas au nombre
            for i in range(m.start(), m.end()):
                pris[i] = True
            v = _valeurs(jeton, francais)
            if v:
                vus.append((m.start(), jeton, v))
    vus.sort(key=lambda t: t[0])
    return [(j, v, p) for p, j, v in vus]


def valeurs_du_texte(texte: str) -> list[float]:
    """Toutes les valeurs lisibles d'un texte de pièce (index de recoupement), dans les DEUX conventions :
    un dépôt EDGAR écrit « 4.5 », une fiche du collecteur rédigée en français « 92,4 % » (#1014 — lue
    en anglais seulement, sa part de 92,4 % passait pour absente)."""
    return [v for fr in (False, True) for _, lect, _ in nombres(texte, fr) for v, _ in lect]


def _annee(v: float, d: int) -> bool:
    return d == 0 and 1900 <= v <= 2100


def retrouve(cible: Iterable[tuple[float, int]], candidats: Iterable[float]) -> bool:
    """Un nombre écrit avec d décimales est retrouvé si un candidat l'arrondit à ±½ unité de sa dernière
    décimale, à un facteur d'unité près (k, M, Md) ; une année se retrouve à l'identique."""
    cands = list(candidats)
    for x, d in cible:
        if _annee(x, d):
            if x in cands:
                return True
            continue
        demi = 0.5 * 10 ** (-d) + 1e-9
        for y in cands:
            for f in _FACTEURS:
                if abs(x - y * f) <= demi:
                    return True
    return False


def libelle(txt: str, debut: int, fin: int) -> bool:
    """Un nombre collé à des lettres (« FY2025 », « T2 », « 10-K », « 21 CFR ») est un libellé."""
    return (debut > 0 and txt[debut - 1].isalpha()) or bool(_APRES_LIBELLE.match(txt, fin))


def _jours_et_mois(txt: str) -> set[int]:
    """Les positions de début des jetons « jour » et « mois » des dates du texte (l'année est gardée)."""
    hors: set[int] = set()
    for m in _DATES.finditer(txt):
        annee = next(m.start(g) for g in ("a1", "a2", "a3") if m.group(g))
        for t in re.finditer(r"\d+", m.group()):
            p = m.start() + t.start()
            if p != annee:
                hors.add(p)
    return hors


def _decimales(v: float) -> int:
    s = repr(float(v))
    if "e" in s or "." not in s:
        return 0
    fr = s.split(".")[1].rstrip("0")
    return len(fr)


# ── ce que le texte rédigé d'une réponse avance ──────────────────────────────────────────────────

def _dict(answer: Any) -> dict[str, Any]:
    return answer.model_dump(mode="json") if hasattr(answer, "model_dump") else dict(answer)


def lieux_rediges(a: dict[str, Any]) -> list[tuple[str, str]]:
    """(lieu, texte) des passages rédigés soumis au contrôle — pas les hypothèses ni la sensibilité
    d'une approximation, qui sont DÉCLARÉES comme hypothèses."""
    r = a.get("reponse") or {}
    parts = [("verbatim", r.get("verbatim") or "")]
    for f in r.get("faits_posterieurs") or []:
        parts.append((f"fait {f.get('depot')}", f.get("effet") or ""))
    ap = a.get("approximation") or {}
    if ap.get("methode"):
        parts.append(("approximation.methode", str(ap["methode"])))
    return [p for p in parts if p[1]]


def pieces_citees(a: dict[str, Any]) -> list[int]:
    ids = list((a.get("fondation") or {}).get("cited_entry_ids") or [])
    for f in (a.get("reponse") or {}).get("faits_posterieurs") or []:
        ids += f.get("cited_entry_ids") or []
    ids += (a.get("approximation") or {}).get("ingredients_entry_ids") or []
    return sorted(set(ids))


def _encadre(a: dict[str, Any]) -> list[float]:
    return [c["valeur"] for c in (a.get("reponse") or {}).get("chiffres_cles") or []
            if isinstance(c, dict) and isinstance(c.get("valeur"), (int, float))]


def texte_de_piece(e: dict[str, Any]) -> str:
    return f"{e.get('title') or ''} {e.get('content') or ''}"


@dataclass(frozen=True)
class ChiffreSansPiece:
    lieu: str
    jeton: str
    extrait: str

    def lisible(self) -> str:
        return f"{self.jeton} — « …{self.extrait}… »"


@dataclass
class Recoupement:
    """Le verdict d'une réponse : ce qui manque, et le décompte de ce qui passe et pourquoi."""
    sans_piece: list[ChiffreSansPiece] = field(default_factory=list)
    calculs_refuses: list[str] = field(default_factory=list)
    n_recoupes: int = 0        # nombres soumis au contrôle
    n_encadre: int = 0         # repris de l'encadré
    n_calcul: int = 0          # résultats d'un calcul montré valide
    n_libelle: int = 0         # libellés et dates


def verifier_calcul(calc: dict[str, Any], *, cites: set[int], pieces: dict[int, list[float]],
                    encadre: list[float]) -> tuple[Optional[float], Optional[str]]:
    """La valeur d'un calcul montré, ou le motif qui l'écarte. Chaque terme doit être dans SA pièce,
    citée — ou dans l'encadré ; la formule s'exécute sur les noms des termes, sans décalage d'exercice."""
    nom = calc.get("libelle") or calc.get("formule")
    termes = {t["nom"]: t for t in calc.get("termes") or []}
    try:
        refs = references_de_la_formule(calc.get("formule") or "")
    except FormuleInexecutable as e:
        return None, f"le calcul « {nom} » ne s'exécute pas ({e})"
    noms = {n for n, _ in refs}
    if any(o != 0 for _, o in refs):
        return None, f"le calcul « {nom} » lit un exercice décalé : chaque terme se cite avec sa valeur"
    if noms != set(termes):
        return None, (f"le calcul « {nom} » : la formule nomme {sorted(noms)}, les termes sont "
                      f"{sorted(termes)}")
    for t in termes.values():
        lect = [(float(t["valeur"]), _decimales(t["valeur"]))]
        if t["entry_id"] not in cites:
            return None, f"le calcul « {nom} » : la pièce [{t['entry_id']}] du terme `{t['nom']}` n'est pas citée"
        if not (retrouve(lect, pieces.get(t["entry_id"], [])) or retrouve(lect, encadre)):
            return None, (f"le calcul « {nom} » : la valeur {t['valeur']:g} du terme `{t['nom']}` ne figure "
                          f"pas dans la pièce [{t['entry_id']}]")
    try:
        return evaluer_formule(calc["formule"], {(n, 0): float(t["valeur"]) for n, t in termes.items()}), None
    except (FormuleInexecutable, ZeroDivisionError) as e:
        return None, f"le calcul « {nom} » ne s'exécute pas ({e})"


def recouper(answer: Any, entries: dict[int, dict[str, Any]]) -> Recoupement:
    """Le contrôle « tout chiffre renvoie à une pièce » d'UNE réponse contre le dossier fourni. Pur."""
    a = _dict(answer)
    out = Recoupement()
    cites = pieces_citees(a)
    pieces = {i: valeurs_du_texte(texte_de_piece(entries[i])) for i in cites if i in entries}
    vals_cites = [v for vs in pieces.values() for v in vs]
    encadre = _encadre(a)
    resultats: list[float] = []
    for calc in (a.get("reponse") or {}).get("calculs") or []:
        v, motif = verifier_calcul(calc, cites=set(cites), pieces=pieces, encadre=encadre)
        if motif:
            out.calculs_refuses.append(motif)
        else:
            resultats += [v, v * 100]   # un rapport écrit en pourcentage
    for lieu, txt in lieux_rediges(a):
        hors = _jours_et_mois(txt)
        for jeton, lect, i0 in nombres(txt, francais=True):
            if i0 in hors:
                out.n_libelle += 1
                continue
            if not any(not (d == 0 and v < 10) for v, d in lect):
                continue
            if any(d == 0 and int(v) in cites for v, d in lect):
                continue
            out.n_recoupes += 1
            if retrouve(lect, vals_cites):
                continue
            if retrouve(lect, encadre):
                out.n_encadre += 1
                continue
            if resultats and retrouve(lect, resultats):
                out.n_calcul += 1
                continue
            if libelle(txt, i0, i0 + len(jeton)):
                out.n_libelle += 1
                continue
            ctx = txt[max(0, i0 - 50): i0 + len(jeton) + 30].replace("\n", " ")
            out.sans_piece.append(ChiffreSansPiece(lieu, jeton, ctx))
    return out


def pieces_qui_portent(jeton: str, entries: dict[int, dict[str, Any]], exclure: Iterable[int] = ()
                       ) -> list[int]:
    """Les pièces du dossier qui portent ce nombre (lecture seule, pour l'outil — jamais pour rattacher
    une citation : un nombre porté par plusieurs pièces ne dit pas laquelle fonde l'affirmation)."""
    lect = _valeurs(jeton, True)
    ex = set(exclure)
    return [i for i, e in entries.items() if i not in ex and retrouve(lect, valeurs_du_texte(texte_de_piece(e)))]
