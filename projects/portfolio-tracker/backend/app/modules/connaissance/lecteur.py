"""Le lecteur — un document brut devient des LIGNES numérotées, par le code, sans modèle.

Ce que ferait un vrai fonds : on met le document en lecture une fois pour toutes, lignes numérotées,
pour que chacun cite « ligne 4 512 » et que le comité retrouve la même ligne. Le même document lu
deux fois par la même version du lecteur donne donc les mêmes lignes, octet pour octet (K2).

Une ligne = un bloc (paragraphe, titre, élément de liste) ou une LIGNE DE TABLEAU, dont chaque
cellule s'ouvre sur une tabulation (#132 : la normalisation des citations ramène tout blanc à une
espace, la ligne du tableau se cite telle qu'imprimée, chiffres compris) ; un bloc DANS une cellule
n'y coupe pas la ligne. Ce qui est masqué (style display:none), les scripts, les styles et l'en-tête
des données structurées ne sont pas lus : un lecteur ne les voit pas.

Bibliothèque standard seulement ; tout ce qui décrit la façon de lire vient du référentiel.
"""
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Mapping

LUE = "lue"
IMPOSSIBLE = "impossible"
SANS_OBJET = "sans_objet"


@dataclass(frozen=True)
class Texte:
    """Ce que le lecteur rend : des lignes (statut « lue »), ou rien avec une raison."""
    statut: str
    lignes: tuple[str, ...] = ()
    raison: str = ""
    detail: str = ""


class _Lecteur(HTMLParser):
    def __init__(self, regles: Mapping[str, Any]) -> None:
        super().__init__(convert_charrefs=True)
        self._blocs = set(regles["blocs"])
        self._muets = set(regles["muets"])
        self._cellules = set(regles["cellules"])
        self._fins_tableau = set(regles["fins_de_ligne_de_tableau"])
        self._vides = set(regles["vides"])
        self._masques = tuple(m.replace(" ", "") for m in regles["masques"])
        self.morceaux: list[str] = []
        # Un élément muet ou masqué : (balise, profondeur de cette balise depuis son ouverture).
        self._cache: list | None = None
        self._dans_cellule = 0

    def _masque(self, attrs: list[tuple[str, str | None]]) -> bool:
        for nom, valeur in attrs:
            if nom == "style" and valeur:
                style = valeur.replace(" ", "").lower()
                if any(m in style for m in self._masques):
                    return True
        return False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._cache is not None:
            if tag == self._cache[0] and tag not in self._vides:
                self._cache[1] += 1
            return
        if tag not in self._vides and (tag in self._muets or self._masque(attrs)):
            self._cache = [tag, 1]
            return
        if tag in self._cellules:
            self._dans_cellule = 1
            self.morceaux.append("\t")
        elif tag in self._fins_tableau:
            self._dans_cellule = 0
            self.morceaux.append("\n")
        elif tag in self._blocs and not self._dans_cellule:
            self.morceaux.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # <br/> et consorts : un bloc vide, jamais un élément qui ouvre un masque.
        if self._cache is None and tag in self._blocs and not self._dans_cellule:
            self.morceaux.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._cache is not None:
            if tag == self._cache[0]:
                self._cache[1] -= 1
                if self._cache[1] == 0:
                    self._cache = None
            return
        if tag in self._fins_tableau:
            self._dans_cellule = 0
            self.morceaux.append("\n")
        elif tag in self._blocs and not self._dans_cellule:
            self.morceaux.append("\n")

    def handle_data(self, data: str) -> None:
        if self._cache is None:
            self.morceaux.append(data)


def _decoder(contenu: bytes, decodages: list[str]) -> str:
    """Le texte du document. Un caractère nul devient « \ufffd », comme le rend un navigateur (et comme
    `&#0;` l'est déjà) : la base refuse de ranger un texte qui en contient — sans ce remplacement, la
    lecture d'un tel document échouerait à chaque passage, sans fin (lecteur 1.1.0)."""
    for enc in decodages[:-1]:
        try:
            return contenu.decode(enc).replace("\x00", "\ufffd")
        except UnicodeDecodeError:
            continue
    return contenu.decode(decodages[-1], errors="replace").replace("\x00", "\ufffd")


_DEVISES = "$€£¥"
_OUVRANTS = "([" + _DEVISES


def _ligne(brute: str) -> str:
    """Les blancs d'une ligne ramenés à une espace, sauf la tabulation qui ouvre une cellule
    (plusieurs cellules vides de suite n'en font qu'une). Une cellule sans lettre ni chiffre se
    recolle comme elle est imprimée : un symbole monétaire ou une parenthèse ouvrante au nombre qui
    suit, le reste (« % », « ) ») à la cellule d'avant — relevé sur un 8-K réel : « 20 », « % » dans
    deux cellules."""
    cellules = [c for c in (" ".join(c.split()) for c in brute.split("\t")) if c]
    recollees: list[str] = []
    devant = ""
    for c in cellules:
        if not any(ch.isalnum() for ch in c):
            if all(ch in _OUVRANTS for ch in c):
                devant += c
            elif recollees:
                recollees[-1] += c
            else:
                devant += c
            continue
        recollees.append(devant + c)
        devant = ""
    if devant:
        recollees.append(devant)
    return "\t".join(recollees)


def _lignes(texte: str) -> tuple[str, ...]:
    return tuple(l for l in (_ligne(b) for b in texte.splitlines()) if l)


def lire(contenu: bytes, type_media: str, regles: Mapping[str, Any]) -> Texte:
    """Le texte d'un document, en lignes. `regles` : la section « lecteur » du référentiel."""
    tm = (type_media or "").split(";")[0].strip().lower()
    if tm in regles["formats_sans_objet"]:
        return Texte(SANS_OBJET, raison="sans_objet")
    if contenu[:5] == b"%PDF-":
        return Texte(IMPOSSIBLE, raison="format_non_lu", detail="document PDF")
    if tm in regles["formats_html"] or (not tm and b"<" in contenu[:2048]):
        p = _Lecteur(regles)
        try:
            p.feed(_decoder(contenu, regles["decodages"]))
            p.close()
        except Exception as exc:  # noqa: BLE001 — un HTML mal formé : on le dit, on ne range rien
            return Texte(IMPOSSIBLE, raison="format_non_lu", detail=f"HTML illisible : {exc}")
        lignes = _lignes("".join(p.morceaux))
    elif tm in regles["formats_texte"] or not tm:
        lignes = _lignes(_decoder(contenu, regles["decodages"]))
    else:
        return Texte(IMPOSSIBLE, raison="format_non_lu", detail=f"format {tm}")
    if not lignes:
        return Texte(IMPOSSIBLE, raison="vide")
    return Texte(LUE, lignes=lignes)
