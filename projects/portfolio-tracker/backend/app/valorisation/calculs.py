"""La BASE COMMUNE de calculs de valorisation — les gabarits maison du fonds (#96, roadmap 05 cap. 4 bis).

CE QUE FERAIT UN VRAI FONDS
---------------------------
Un fonds ne laisse pas chaque analyste réécrire l'actualisation ou la formule de Gordon : il tient des
gabarits maison, relus une fois, et c'est sur eux que s'assemble le modèle propre à chaque entreprise
(somme des programmes pour une biotech, segments pour NVDA). Ce module EST ces gabarits : des fonctions
pures, fermées, testées sur des valeurs calculées à la main (`checks/check_bac_a_calcul.py` §1).

Le modèle de langage ne calcule JAMAIS un de ces nombres lui-même (arbitrage du 2026-09-28) : il écrit
la mécanique propre à l'entreprise, qui APPELLE ces fonctions dans le bac à calcul
(`bac_a_calcul.py`). Un calcul fait « de tête » par le modèle varie d'un passage à l'autre — mesuré sur
ce projet (`feedback_jugement_modele_instable_entre_passages`) ; un calcul fait ici ne varie pas.

CHAQUE FONCTION REFUSE SON HORS-DOMAINE, ELLE NE LE CORRIGE PAS
---------------------------------------------------------------
Un coût du capital inférieur à la croissance terminale donne, par Gordon, une valeur négative ou
infinie d'apparence normale. Une probabilité de succès de 1,4 donne une valeur pondérée supérieure à
la valeur en cas de succès. Ces cas lèvent `ErreurCalcul` avec un motif lisible par le comité : un
nombre faux mais plausible est la pire issue d'un modèle de valorisation.

Module PUR : aucune IO, aucun import hors `math`. Cible : Python 3.12 (conteneur backend).
"""
from __future__ import annotations

import math


class ErreurCalcul(Exception):
    """Un calcul refusé — hors domaine, construction non admise, budget épuisé. `motif` est écrit pour
    être lu par l'analyste (et le comité) ; `ligne` situe l'erreur dans la mécanique de l'entreprise."""

    def __init__(self, motif: str, ligne: int | None = None) -> None:
        self.motif = motif
        self.ligne = ligne
        super().__init__(f"ligne {ligne} : {motif}" if ligne is not None else motif)


# Bornes de la recherche de croissance implicite : un prix qui suppose plus de +100 % l'an pendant
# tout l'horizon, ou moins de −50 %, n'est pas « ce que suppose le prix », c'est un modèle inadapté.
_CROISSANCE_MIN = -0.5
_CROISSANCE_MAX = 1.0
_ITERATIONS_BISSECTION = 200


def _nombre(v: object, nom: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ErreurCalcul(f"`{nom}` doit être un nombre (reçu : {type(v).__name__})")
    if not math.isfinite(v):
        raise ErreurCalcul(f"`{nom}` n'est pas un nombre fini")
    return float(v)


def _taux(v: object, nom: str) -> float:
    t = _nombre(v, nom)
    if t <= -1.0:
        raise ErreurCalcul(f"`{nom}` = {t} : un taux ≤ −100 % n'a pas de sens")
    return t


def _flux(flux: object, nom: str = "flux") -> list[float]:
    if not isinstance(flux, (list, tuple)) or not flux:
        raise ErreurCalcul(f"`{nom}` doit être une liste non vide de nombres")
    return [_nombre(f, f"{nom}[{i}]") for i, f in enumerate(flux)]


def valeur_sans_croissance(benefice_normalise: float, cout_du_capital: float) -> float:
    """Valeur de la rentabilité actuelle (Greenwald, EPV) : le bénéfice distribuable normalisé,
    supposé constant à perpétuité, actualisé au coût du capital. AUCUNE croissance n'y entre."""
    b = _nombre(benefice_normalise, "benefice_normalise")
    r = _nombre(cout_du_capital, "cout_du_capital")
    if r <= 0:
        raise ErreurCalcul(f"coût du capital = {r} : il doit être strictement positif")
    return b / r


def actualiser(flux: list[float], taux: float, annee_depart: int = 1) -> float:
    """Valeur actuelle d'une série de flux annuels, le premier reçu à l'année `annee_depart`."""
    fs = _flux(flux)
    r = _taux(taux, "taux")
    a = _nombre(annee_depart, "annee_depart")
    return sum(f / (1.0 + r) ** (a + i) for i, f in enumerate(fs))


def valeur_terminale(flux_final: float, taux: float, croissance: float) -> float:
    """Valeur, à la date du dernier flux explicite, de la suite perpétuelle croissant au taux
    `croissance` (Gordon). Exige taux > croissance — sinon la perpétuité ne converge pas."""
    f = _nombre(flux_final, "flux_final")
    r = _taux(taux, "taux")
    g = _taux(croissance, "croissance")
    if r <= g:
        raise ErreurCalcul(
            f"taux d'actualisation ({r}) ≤ croissance perpétuelle ({g}) : la valeur terminale "
            "diverge — aucune entreprise ne croît plus vite que son coût du capital à perpétuité"
        )
    return f * (1.0 + g) / (r - g)


def dcf(flux: list[float], taux: float, croissance_terminale: float) -> float:
    """Flux explicites actualisés + valeur terminale de Gordon actualisée depuis le dernier flux."""
    fs = _flux(flux)
    r = _taux(taux, "taux")
    vt = valeur_terminale(fs[-1], r, croissance_terminale)
    return actualiser(fs, r) + vt / (1.0 + r) ** len(fs)


def flux_en_croissance(flux_initial: float, croissance: float, annees: int) -> list[float]:
    """Les `annees` flux qui suivent `flux_initial`, chacun croissant de `croissance` l'an."""
    f0 = _nombre(flux_initial, "flux_initial")
    g = _taux(croissance, "croissance")
    n = _nombre(annees, "annees")
    if n != int(n) or not 1 <= n <= 100:
        raise ErreurCalcul(f"annees = {annees} : un entier entre 1 et 100 est attendu")
    return [f0 * (1.0 + g) ** k for k in range(1, int(n) + 1)]


def croissance_implicite(
    valeur_cible: float, flux_initial: float, taux: float, annees: int, croissance_terminale: float
) -> float:
    """Ce que suppose le prix (DCF inversé, Mauboussin) : la croissance annuelle des flux sur
    `annees` qui, suivie de la croissance terminale, redonne exactement `valeur_cible`.

    Résolue par bissection — fermée, déterministe, sans appel au modèle. Exige un flux initial
    positif (sinon la valeur n'est pas monotone en la croissance, et la réponse ne serait pas unique).
    """
    v = _nombre(valeur_cible, "valeur_cible")
    f0 = _nombre(flux_initial, "flux_initial")
    if f0 <= 0:
        raise ErreurCalcul(
            "flux initial ≤ 0 : la croissance implicite n'est pas définie (une entreprise sans flux "
            "positif se lit par ce que suppose le prix sur un autre agrégat, pas par ce calcul)"
        )

    def valeur(g: float) -> float:
        return dcf(flux_en_croissance(f0, g, annees), taux, croissance_terminale)

    bas, haut = _CROISSANCE_MIN, _CROISSANCE_MAX
    if not valeur(bas) <= v <= valeur(haut):
        raise ErreurCalcul(
            f"le prix suppose une croissance hors de [{_CROISSANCE_MIN:.0%}, {_CROISSANCE_MAX:.0%}] "
            "l'an : le gabarit ne s'applique pas à ce titre"
        )
    for _ in range(_ITERATIONS_BISSECTION):
        milieu = (bas + haut) / 2.0
        if valeur(milieu) < v:
            bas = milieu
        else:
            haut = milieu
    return (bas + haut) / 2.0


def valeur_ponderee(probabilite_de_succes: float, valeur_si_succes: float, cout_restant: float = 0.0) -> float:
    """Valeur d'un programme (molécule, projet) pondérée par sa probabilité de succès, nette du coût
    restant à engager pour y parvenir (rNPV simplifiée : la somme des programmes d'une biotech)."""
    p = _nombre(probabilite_de_succes, "probabilite_de_succes")
    if not 0.0 <= p <= 1.0:
        raise ErreurCalcul(f"probabilité de succès = {p} : elle doit être entre 0 et 1")
    return p * _nombre(valeur_si_succes, "valeur_si_succes") - _nombre(cout_restant, "cout_restant")


def valeur_fonds_propres(valeur_entreprise: float, dette_nette: float) -> float:
    """Passage de la valeur de l'entreprise à celle des actionnaires (une trésorerie nette est une
    dette nette négative)."""
    return _nombre(valeur_entreprise, "valeur_entreprise") - _nombre(dette_nette, "dette_nette")


def actions_diluees(actions_en_circulation: float, actions_potentielles: float) -> float:
    """Nombre d'actions après exercice de tout ce qui peut en créer (options, convertibles, émissions
    annoncées) — la valeur PAR ACTION se divise par lui, jamais par le seul nombre en circulation."""
    a = _nombre(actions_en_circulation, "actions_en_circulation")
    p = _nombre(actions_potentielles, "actions_potentielles")
    if a <= 0 or p < 0:
        raise ErreurCalcul("actions en circulation > 0 et actions potentielles ≥ 0 sont attendues")
    return a + p


def dilution(actions_en_circulation: float, actions_nouvelles: float) -> float:
    """Part du capital que représentent les actions nouvelles une fois émises."""
    total = actions_diluees(actions_en_circulation, actions_nouvelles)
    return _nombre(actions_nouvelles, "actions_nouvelles") / total


def valeur_par_action(valeur_fonds_propres: float, nombre_actions: float) -> float:
    n = _nombre(nombre_actions, "nombre_actions")
    if n <= 0:
        raise ErreurCalcul("nombre d'actions ≤ 0")
    return _nombre(valeur_fonds_propres, "valeur_fonds_propres") / n


def marge_de_securite(prix: float, valeur: float) -> float:
    """Écart entre la valeur estimée et le prix, rapporté à la valeur (Graham) : positif = décote."""
    v = _nombre(valeur, "valeur")
    if v <= 0:
        raise ErreurCalcul(f"valeur = {v} : une marge de sécurité ne se mesure que sur une valeur positive")
    return (v - _nombre(prix, "prix")) / v


def fourchette(bas: float, central: float, haut: float) -> dict[str, float]:
    """Une fourchette, jamais un point (spec 03 §4.6) : trois scénarios ORDONNÉS. Un scénario bas
    au-dessus du central dit que les hypothèses ont été croisées — refusé, pas réordonné."""
    b, c, h = _nombre(bas, "bas"), _nombre(central, "central"), _nombre(haut, "haut")
    if not b <= c <= h:
        raise ErreurCalcul(f"fourchette non ordonnée : bas {b}, central {c}, haut {h}")
    return {"bas": b, "central": c, "haut": h}


# Le catalogue exposé au bac à calcul — DÉTENTEUR UNIQUE de ce que la mécanique d'une entreprise peut
# appeler (#46). Ajouter un gabarit maison = une fonction ici + ses valeurs à la main dans le check.
CATALOGUE = {
    f.__name__: f
    for f in (
        valeur_sans_croissance, actualiser, valeur_terminale, dcf, flux_en_croissance,
        croissance_implicite, valeur_ponderee, valeur_fonds_propres, actions_diluees, dilution,
        valeur_par_action, marge_de_securite, fourchette,
    )
}
