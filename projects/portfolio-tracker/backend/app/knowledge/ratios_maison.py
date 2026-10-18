"""Les RATIOS MAISON — lus dans le socle des comptes, par le code, jamais par le modèle.

POURQUOI IL EXISTE (roadmap 05, capacité 4 bis — prérequis de la qualité financière de NVDA)
--------------------------------------------------------------------------------------------
Le socle des comptes (#115) reconstitue résultat, bilan et flux au format maison. Un fonds ne s'arrête
pas là : le même modèle porte un onglet de RATIOS dont le directeur de la recherche a écrit les
définitions une fois pour toutes — capital employé, résultat d'exploitation après impôt, rendement du
capital, conversion du résultat en trésorerie, capital consommé par la croissance. Chaque analyste les
LIT ; aucun ne les recalcule à sa façon. Sans eux, la qualité financière d'un émetteur rentable (NVDA,
MSFT) demanderait au modèle de calculer un rendement du capital sur cinq exercices — exactement ce que
l'arbitrage du 2026-09-28 interdit (« le calcul n'est pas fait par le modèle »), et ce que #101 a mesuré
(la dette nette sortait à la valeur de l'exemple du prompt).

CE QUE CE MODULE FAIT
---------------------
Des fonctions PURES sur la forme PERSISTÉE du socle (`structure_du_socle`) : aucun réseau, aucune base,
aucun modèle. Les ratios ne sont PAS stockés — ils se recalculent à chaque lecture depuis les cellules
(#53 : ce qui se dérive se rejoue, une valeur figée ne peut pas signaler qu'elle a vieilli). Leur
VERSION, elle, entre dans l'empreinte du socle publié : changer une définition republie la pièce.

LES CONVENTIONS (écrites ici une fois — « ce n'est pas de niveau comité », arbitrage du 2026-10-04)
--------------------------------------------------------------------------------------------------
  · capital employé : la ligne `capital_employe` du gabarit (convention dans `socle_comptes.yaml`) ;
  · capital MOYEN de l'exercice = (ouverture + clôture) / 2 — un rendement rapporte le résultat d'une
    année au capital qui l'a porté pendant l'année, pas à celui du dernier jour ;
  · taux d'impôt retenu = impôt ÷ résultat avant impôt de l'exercice, borné à [0 ; 1] ; aucun impôt
    retenu sur un résultat avant impôt nul ou négatif (une perte ne crée pas de résultat après impôt
    supérieur au résultat d'exploitation) ;
  · résultat d'exploitation après impôt = résultat d'exploitation × (1 − taux retenu) — tel que DÉPOSÉ :
    la normalisation des éléments non récurrents reste le jugement de l'analyste (qf_6) ;
  · un capital moyen nul ou négatif ne porte AUCUN rendement (#104 : le quotient changerait de signe
    avec lui) — `non défini`, motivé, jamais un nombre ;
  · conversion en trésorerie = Σ flux d'exploitation ÷ Σ résultat net sur les trois derniers exercices
    (le rapport des sommes, pas la moyenne des rapports : une année au résultat presque nul ferait
    exploser une moyenne de rapports) ; résultat cumulé ≤ 0 ⟹ non calculable ;
  · capital par point de croissance = variation du capital employé entre la clôture du premier et du
    dernier exercice du socle ÷ croissance du chiffre d'affaires sur la même fenêtre, en points ;
    croissance nulle ou négative ⟹ non calculable (aucun point de croissance à financer) ;
  · pente du rendement = pente des moindres carrés des cinq rendements annuels, en points par an.

TROIS ISSUES, JAMAIS UN SILENCE (#25/#44) : établi (valeur + période) · non établi (une cellule manque —
NOMMÉE) · non calculable / non défini (une propriété de l'entreprise, dite). Jamais un zéro inventé.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

# Version des DÉFINITIONS ci-dessous. Entre dans l'empreinte du socle publié (`socle_comptes.empreinte`).
VERSION_RATIOS = "1.0.0"

NB_EXERCICES_RENDEMENT = 5
NB_EXERCICES_CONVERSION = 3


@dataclass(frozen=True)
class RatioMaison:
    id: str
    libelle: str
    unite: str
    definition: str


# Les ratios qu'un chiffre de l'encadré peut demander (`ChiffreDuSocle.ratio`). Vocabulaire FERMÉ : le
# pont du référentiel ([U]) refuse un identifiant absent et une unité différente de celle déclarée ici.
RATIOS: dict[str, RatioMaison] = {r.id: r for r in (
    RatioMaison("rendement_du_capital_employe_moyen", "Rendement du capital employé, moyenne des cinq exercices",
                "%", "moyenne des rendements annuels : résultat d'exploitation après impôt ÷ capital employé "
                     "moyen de l'exercice"),
    RatioMaison("pente_du_rendement", "Pente du rendement du capital employé sur cinq exercices", "points/an",
                "pente des moindres carrés des cinq rendements annuels"),
    RatioMaison("part_du_resultat_en_tresorerie", "Part du résultat net retrouvée en trésorerie d'exploitation, "
                "trois exercices", "%", "Σ flux de trésorerie d'exploitation ÷ Σ résultat net, trois derniers "
                "exercices"),
    RatioMaison("capital_par_point_de_croissance", "Capital employé supplémentaire par point de croissance du "
                "chiffre d'affaires", "M$", "variation du capital employé ÷ croissance du chiffre d'affaires en "
                "points, du premier au dernier exercice du socle"),
)}


@dataclass(frozen=True)
class Valeur:
    """Une valeur de ratio : établie (`valeur`), ou absente avec son `motif`. Jamais les deux."""
    valeur: Optional[float]
    motif: Optional[str] = None


def _cellule(structure: dict[str, Any], ligne: str, periode_id: str) -> Valeur:
    """La valeur d'une cellule du socle, en $. `compte_zero` vaut zéro (le gabarit le dit) ; une cellule
    absente ou non déposée rend une absence NOMMÉE (#25)."""
    c = (structure.get("cellules") or {}).get(f"{ligne}|{periode_id}")
    if c is None:
        return Valeur(None, f"{ligne} absent du socle au {periode_id[-10:]}")
    if c.get("e") == "compte_zero":
        return Valeur(0.0)
    if c.get("v") is None:
        return Valeur(None, f"{ligne} non déposé au {periode_id[-10:]}")
    return Valeur(float(c["v"]))


def exercices(structure: dict[str, Any]) -> list[dict[str, Any]]:
    """Les exercices clos du socle, du plus ancien au plus récent."""
    return sorted((p for p in structure.get("periodes") or []
                   if p["cadrage"] == "flux" and p["nature"] == "exercice"), key=lambda p: p["fin"])


def _bilans(structure: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Les bilans de clôture d'exercice (ouverture comprise), par date de fin."""
    return {p["fin"]: p for p in structure.get("periodes") or []
            if p["cadrage"] == "instant" and p["nature"] in ("exercice", "ouverture")}


@dataclass(frozen=True)
class LigneExercice:
    """Les ratios d'UN exercice. Montants en $, rendements et marges en %, rotation en fois."""
    fin: str
    taux_impot_retenu: Valeur
    resultat_exploitation_apres_impot: Valeur
    capital_employe_moyen: Valeur
    capital_employe_moyen_hors_ecarts: Valeur
    rendement_du_capital_employe: Valeur
    rendement_hors_ecarts_d_acquisition: Valeur
    marge_apres_impot: Valeur
    rotation_du_capital: Valeur


def _nombre(x: float, decimales: int = 1) -> str:
    """Un nombre au format du texte du socle (milliers séparés par une espace, point décimal)."""
    return f"{x:,.{decimales}f}".replace(",", " ")


def _quotient(num: Valeur, den: Valeur, *, facteur: float, sur: str, motif_den: str) -> Valeur:
    if num.valeur is None or den.valeur is None:
        return Valeur(None, "non établi : " + "; ".join(m for m in (num.motif, den.motif) if m))
    if den.valeur <= 0:
        return Valeur(None, f"non défini : {sur} nul ou négatif ({_nombre(den.valeur / 1e6)} M$) — {motif_den}")
    return Valeur(num.valeur / den.valeur * facteur)


def _moyenne(a: Valeur, b: Valeur) -> Valeur:
    if a.valeur is None or b.valeur is None:
        return Valeur(None, "non établi : " + "; ".join(m for m in (a.motif, b.motif) if m))
    return Valeur((a.valeur + b.valeur) / 2)


def ligne_de_l_exercice(structure: dict[str, Any], exercice: dict[str, Any]) -> LigneExercice:
    """Les ratios d'un exercice clos. Pur."""
    fy = exercice["id"]
    bilans = _bilans(structure)
    fins_avant = sorted(f for f in bilans if f < exercice["fin"])
    cloture = bilans.get(exercice["fin"])
    ouverture = bilans[fins_avant[-1]] if fins_avant else None

    rai, impot = _cellule(structure, "resultat_avant_impot", fy), _cellule(structure, "impot", fy)
    if rai.valeur is None or impot.valeur is None:
        taux = Valeur(None, "non établi : " + "; ".join(m for m in (rai.motif, impot.motif) if m))
    elif rai.valeur <= 0:
        taux = Valeur(0.0)
    else:
        taux = Valeur(min(max(impot.valeur / rai.valeur, 0.0), 1.0))
    ebit = _cellule(structure, "resultat_exploitation", fy)
    if ebit.valeur is None or taux.valeur is None:
        nopat = Valeur(None, "non établi : " + "; ".join(m for m in (ebit.motif, taux.motif) if m))
    else:
        nopat = Valeur(ebit.valeur * (1 - taux.valeur))

    def moyen(ligne: str) -> Valeur:
        if cloture is None or ouverture is None:
            return Valeur(None, f"non établi : pas de bilan d'ouverture ET de clôture pour l'exercice clos le "
                                f"{exercice['fin']}")
        return _moyenne(_cellule(structure, ligne, ouverture["id"]), _cellule(structure, ligne, cloture["id"]))

    ce, ce_hors = moyen("capital_employe"), moyen("capital_employe_hors_ecarts_d_acquisition")
    ca = _cellule(structure, "chiffre_affaires", fy)
    motif_ce = "un rendement rapporté à un capital négatif changerait de signe avec lui (#104)"
    return LigneExercice(
        fin=exercice["fin"],
        taux_impot_retenu=taux,
        resultat_exploitation_apres_impot=nopat,
        capital_employe_moyen=ce,
        capital_employe_moyen_hors_ecarts=ce_hors,
        rendement_du_capital_employe=_quotient(nopat, ce, facteur=100, sur="capital employé moyen",
                                               motif_den=motif_ce),
        rendement_hors_ecarts_d_acquisition=_quotient(nopat, ce_hors, facteur=100,
                                                      sur="capital employé moyen hors écarts d'acquisition",
                                                      motif_den=motif_ce),
        marge_apres_impot=_quotient(nopat, ca, facteur=100, sur="chiffre d'affaires",
                                    motif_den="aucune vente à laquelle rapporter le résultat"),
        rotation_du_capital=_quotient(ca, ce, facteur=1, sur="capital employé moyen", motif_den=motif_ce),
    )


def table_des_ratios(structure: dict[str, Any]) -> list[LigneExercice]:
    """Une ligne par exercice clos du socle, du plus ancien au plus récent. Pur."""
    return [ligne_de_l_exercice(structure, e) for e in exercices(structure)]


def _annees(fin: str, depuis: str) -> float:
    return (date.fromisoformat(fin) - date.fromisoformat(depuis)).days / 365.25


def _fenetre(structure: dict[str, Any], n: int) -> list[dict[str, Any]]:
    return exercices(structure)[-n:]


def _libelle_fenetre(exs: list[dict[str, Any]]) -> str:
    return f"exercices clos du {exs[0]['fin']} au {exs[-1]['fin']}"


# L'ISSUE d'un chiffre absent, lue sur le PRÉFIXE de son motif (les trois issues ci-dessus) — DÉTENTEUR
# UNIQUE (#139 ter). `manque` : une cellule manque, une collecte peut la ramener ; `non_significatif` : une
# propriété de l'entreprise (dénominateur négatif, aucune croissance) — aucune collecte ne la changera, et
# un verdict lu sur ce chiffre serait inventé (mesuré RVMD qf_3/qf_5, 2026-10-18).
MANQUE, NON_SIGNIFICATIF = "manque", "non_significatif"
_PREFIXES_NON_SIGNIFICATIF = ("non calculable", "non défini")


def issue_du_motif(motif: Optional[str]) -> str:
    """`non_significatif` si le motif dit une propriété de l'entreprise, sinon `manque` (prudent : dans le
    doute, on cherche — une absence non qualifiée reste une donnée à collecter)."""
    m = (motif or "").strip().lower()
    return NON_SIGNIFICATIF if m.startswith(_PREFIXES_NON_SIGNIFICATIF) else MANQUE


def ratio_du_socle(structure: dict[str, Any], ratio_id: str) -> tuple[Optional[float], str]:
    """Un ratio maison LU dans le socle : (valeur dans l'unité du ratio, période — ou motif d'absence).
    Pur. DÉTENTEUR UNIQUE, lu par l'encadré de l'analyste et par le pont qui le vérifie (#46)."""
    if ratio_id not in RATIOS:
        raise ValueError(f"ratio maison « {ratio_id} » inconnu ({sorted(RATIOS)})")
    r = RATIOS[ratio_id]
    source = f"socle des comptes, ratio maison : {r.definition}"

    if ratio_id in ("rendement_du_capital_employe_moyen", "pente_du_rendement"):
        exs = _fenetre(structure, NB_EXERCICES_RENDEMENT)
        if len(exs) < NB_EXERCICES_RENDEMENT:
            return None, (f"non établi : le socle ne porte que {len(exs)} exercice(s) clos, il en faut "
                          f"{NB_EXERCICES_RENDEMENT}")
        lignes = [ligne_de_l_exercice(structure, e) for e in exs]
        absents = [(l.fin, l.rendement_du_capital_employe.motif) for l in lignes
                   if l.rendement_du_capital_employe.valeur is None]
        if absents:
            detail = " ; ".join(f"l'exercice clos le {f} ({m})" for f, m in absents)
            # #139 ter — un rendement NON DÉFINI (capital moyen négatif) est une propriété de l'entreprise :
            # la série ne s'établira pas en collectant. Le dire « non établi » l'envoyait en collecte (RVMD
            # qf_5, 2026-10-18). Une seule année non définie suffit : la série de cinq ne peut pas exister.
            if any(issue_du_motif(m) == NON_SIGNIFICATIF for _f, m in absents):
                return None, "non défini : rendement non défini pour " + detail
            return None, "non établi : rendement absent pour " + detail
        rdts = [l.rendement_du_capital_employe.valeur for l in lignes]
        if ratio_id == "rendement_du_capital_employe_moyen":
            return sum(rdts) / len(rdts), f"moyenne des {_libelle_fenetre(exs)} — {source}"
        xs = [_annees(e["fin"], exs[0]["fin"]) for e in exs]
        mx, my = sum(xs) / len(xs), sum(rdts) / len(rdts)
        pente = sum((x - mx) * (y - my) for x, y in zip(xs, rdts)) / sum((x - mx) ** 2 for x in xs)
        return pente, f"{_libelle_fenetre(exs)} — {source}"

    if ratio_id == "part_du_resultat_en_tresorerie":
        exs = _fenetre(structure, NB_EXERCICES_CONVERSION)
        if len(exs) < NB_EXERCICES_CONVERSION:
            return None, (f"non établi : le socle ne porte que {len(exs)} exercice(s) clos, il en faut "
                          f"{NB_EXERCICES_CONVERSION}")
        cfo = [_cellule(structure, "flux_exploitation", e["id"]) for e in exs]
        rn = [_cellule(structure, "resultat_net", e["id"]) for e in exs]
        manquants = [v.motif for v in cfo + rn if v.valeur is None]
        if manquants:
            return None, "non établi : " + " ; ".join(manquants)
        s_rn = sum(v.valeur for v in rn)
        if s_rn <= 0:
            return None, (f"non calculable : résultat net cumulé nul ou négatif sur les {_libelle_fenetre(exs)} "
                          f"({_nombre(s_rn / 1e6)} M$) — une perte ne se convertit pas en trésorerie")
        return sum(v.valeur for v in cfo) / s_rn * 100, f"{_libelle_fenetre(exs)} — {source}"

    # capital_par_point_de_croissance
    exs = exercices(structure)
    if len(exs) < 2:
        return None, "non établi : il faut au moins deux exercices clos pour mesurer une croissance"
    premier, dernier = exs[0], exs[-1]
    bilans = _bilans(structure)
    ce = [(_cellule(structure, "capital_employe", bilans[e["fin"]]["id"]) if e["fin"] in bilans
           else Valeur(None, f"pas de bilan au {e['fin']}")) for e in (premier, dernier)]
    ca = [_cellule(structure, "chiffre_affaires", e["id"]) for e in (premier, dernier)]
    manquants = [v.motif for v in ce + ca if v.valeur is None]
    if manquants:
        return None, "non établi : " + " ; ".join(manquants)
    if ca[0].valeur <= 0:
        return None, (f"non calculable : aucun chiffre d'affaires à l'exercice clos le {premier['fin']} — une "
                      "croissance ne se mesure pas depuis zéro")
    points = (ca[1].valeur / ca[0].valeur - 1) * 100
    if points <= 0:
        return None, (f"non calculable : le chiffre d'affaires n'a pas crû sur les {_libelle_fenetre(exs)} "
                      f"({_nombre(points)} points) — aucun point de croissance à financer")
    return (ce[1].valeur - ce[0].valeur) / points / 1e6, f"{_libelle_fenetre(exs)} — {source}"


def _f(v: Valeur, fmt: str) -> str:
    return "n.d." if v.valeur is None else fmt.format(v.valeur).replace(",", " ")


def rendre_ratios(structure: dict[str, Any]) -> list[str]:
    """Les lignes de texte que lit l'ANALYSTE (ajoutées au texte du socle). Montants en M$ au dixième,
    rendements en % au dixième. Aucun marqueur de dérivation (#78) : un ratio maison sur des lignes
    déposées est un agrégat déterministe, il vaut relevé (#110). Pur."""
    table = table_des_ratios(structure)
    if not table:
        return []
    out = ["", f"Ratios maison (définitions {VERSION_RATIOS}, communes à toutes les sociétés) — "
               + " | ".join(f"Exercice clos le {l.fin}" for l in table)]
    m = lambda v: Valeur(None if v.valeur is None else v.valeur / 1e6, v.motif)  # noqa: E731
    for libelle, get, fmt in (
        ("Taux d'impôt retenu (%)", lambda l: Valeur(None if l.taux_impot_retenu.valeur is None
                                                      else l.taux_impot_retenu.valeur * 100), "{:,.1f}"),
        ("Résultat d'exploitation après impôt (M$)", lambda l: m(l.resultat_exploitation_apres_impot), "{:,.1f}"),
        ("Capital employé moyen de l'exercice (M$)", lambda l: m(l.capital_employe_moyen), "{:,.1f}"),
        ("Rendement du capital employé (%)", lambda l: l.rendement_du_capital_employe, "{:,.1f}"),
        ("Rendement hors écarts d'acquisition (%)", lambda l: l.rendement_hors_ecarts_d_acquisition, "{:,.1f}"),
        ("Marge d'exploitation après impôt (%)", lambda l: l.marge_apres_impot, "{:,.1f}"),
        ("Rotation du capital employé (fois)", lambda l: l.rotation_du_capital, "{:,.2f}"),
    ):
        out.append(f"  {libelle} : " + " | ".join(_f(get(l), fmt) for l in table))
    for r in RATIOS.values():
        v, periode = ratio_du_socle(structure, r.id)
        out.append(f"  {r.libelle} ({r.unite}) : "
                   + (periode if v is None else f"{_nombre(v)} — {periode}"))
    return out
