"""
La citation littérale — DÉTENTEUR UNIQUE de « ce passage figure-t-il mot pour mot dans ce texte ? » (#90, #126).

Deux lecteurs : la note flash (#90 — chaque type d'événement se cite par un passage du dépôt) et le
collecteur web (#126 — une fiche de lecture porte des extraits du document, vérifiés contre le texte que
les outils ont réellement rapporté). Une règle recopiée re-diverge au correctif suivant (#46) : la
normalisation vit ici, et seulement ici.

La normalisation est MINIMALE : forme Unicode, guillemets et tirets typographiques, espaces, casse,
et l'espace entre un symbole monétaire et son nombre (un tableau EDGAR converti en texte met « $ » et
« 198.89 » dans deux cellules, #132). Rien d'autre — une paraphrase, une traduction, un chiffre arrondi
ne doivent pas passer.

L'EXTRAIT COURT (C1 du plan avant comité, 2026-10-21). Un cours (« $198.89 ») ou un intitulé (« X
Director ») est court par nature ; le refuser d'office faisait tomber la seule fiche qui portait la
valeur (NVDA ma_3, ma_4, 2026-10-16). Un fonds cite la LIGNE du tableau, pas la cellule : le code
remplace donc l'extrait court par le passage du document qui le contient (sa ligne, sa phrase), copié
mot pour mot — à condition que ce passage soit UNIQUE dans le document. Un extrait court présent à
plusieurs endroits (« Revenue ») reste refusé : il ne désigne rien, c'est le cas que visait #126.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, Optional

_GUILLEMETS = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"',
                             "–": "-", "—": "-", " ": " "})

# Un extrait plus court ne prouve rien : « revenue » figure dans tout document financier. Le seuil
# exige au moins un bout de phrase — ce qui rend l'extrait discriminant sans exiger une phrase entière.
EXTRAIT_MIN_CARS = 20


# Un passage plus long que ceci est coupé autour de l'extrait court (une page HTML sans saut de ligne
# ferait sinon de la page entière « la ligne » de l'extrait) ; la coupe tombe sur un blanc.
CONTEXTE_MAX_CARS = 300
_FENETRE_CARS = 120

_DEVISES = "$€£¥"
_DEVISE_DETACHEE = re.compile(r"([" + re.escape(_DEVISES) + r"])\s+(?=\d)")


def _typographie(texte: str) -> str:
    """Forme Unicode et typographie seulement — la casse et les sauts de ligne restent (le passage
    d'un extrait court se découpe sur les lignes du texte d'origine)."""
    return unicodedata.normalize("NFKC", texte).translate(_GUILLEMETS)


def normaliser(texte: str) -> str:
    """Forme comparable d'un texte. Cf. docstring du module : rien au-delà de la typographie."""
    t = _DEVISE_DETACHEE.sub(r"\1", _typographie(texte))
    return re.sub(r"\s+", " ", t).strip().casefold()


def extrait_introuvable(extraits: Iterable[str], textes: Iterable[str]) -> Optional[str]:
    """Le PREMIER extrait qui ne figure mot pour mot dans aucun des `textes`, ou None si tous y sont.

    Rend l'extrait fautif, jamais un booléen : un refus qui ne dit pas sur quoi condamne le producteur
    à deviner (#63/#78). Sans texte de référence, tout extrait est introuvable — on ne vérifie pas
    contre rien.
    """
    corpus = [normaliser(t) for t in textes if t]
    for e in extraits:
        n = normaliser(e)
        if not any(n in c for c in corpus):
            return e
    return None


def _motif(extrait: str) -> re.Pattern[str]:
    """L'extrait en expression qui retrouve ses occurrences dans le texte d'ORIGINE avec la même
    tolérance que `normaliser` (blancs, casse, espace après un symbole monétaire) — et aucune autre."""
    n = normaliser(extrait)
    morceaux: list[str] = []
    for i, ch in enumerate(n):
        if ch == " ":
            morceaux.append(r"\s+")
            continue
        morceaux.append(re.escape(ch))
        if ch in _DEVISES and i + 1 < len(n) and n[i + 1].isdigit():
            morceaux.append(r"\s*")
    return re.compile("".join(morceaux), re.IGNORECASE)


def _passage(t: str, debut: int, fin: int) -> str:
    """La ligne qui contient [debut, fin[ ; trop courte, avec ses deux voisines ; trop longue, une
    fenêtre autour de l'extrait coupée sur des blancs. Blancs ramenés à une espace : le passage se
    vérifie encore mot pour mot par `normaliser`."""
    a = t.rfind("\n", 0, debut) + 1
    b = t.find("\n", fin)
    b = len(t) if b < 0 else b
    if len(re.sub(r"\s+", " ", t[a:b]).strip()) < EXTRAIT_MIN_CARS:  # mesurée telle que la fiche la portera
        a = t.rfind("\n", 0, max(a - 1, 0)) + 1
        b2 = t.find("\n", b + 1)
        b = len(t) if b2 < 0 or b >= len(t) else b2
    if b - a > CONTEXTE_MAX_CARS:
        ga, gb = max(a, debut - _FENETRE_CARS), min(b, fin + _FENETRE_CARS)
        blanc = re.search(r"\s", t[ga:debut])
        ga = ga + blanc.end() if ga > a and blanc else ga
        blancs = [m.start() for m in re.finditer(r"\s", t[fin:gb])]
        gb = fin + blancs[-1] if gb < b and blancs else gb
        a, b = ga, gb
    return re.sub(r"\s+", " ", t[a:b]).strip()


def etablir_extraits(extraits: Iterable[str], textes: Iterable[str]) -> tuple[list[str], Optional[str]]:
    """Les extraits tels que la fiche les portera, ou ([], motif) si UN seul ne peut pas l'être (la
    fiche entière tombe : elle dirait plus que son document, #126).

    - un extrait d'au moins `EXTRAIT_MIN_CARS` caractères est gardé tel quel s'il figure mot pour mot ;
    - un extrait plus court est remplacé par le passage du document qui le contient, s'il est UNIQUE
      dans chaque texte lu de cette adresse (plusieurs textes = plusieurs vues du même document :
      page entière, section cherchée, extrait de recherche ; on garde le passage du plus long) ;
      plusieurs passages distincts ⟹ refusé, non discriminant ; passage encore trop court ⟹ refusé.
    Sans texte de référence, rien n'est établi — on ne vérifie pas contre rien.
    """
    textes = [t for t in textes if t]
    etablis: list[str] = []
    for e in extraits:
        if len(e) >= EXTRAIT_MIN_CARS:
            if extrait_introuvable([e], textes) is not None:
                return [], f"extrait introuvable dans le texte rapporté : {e[:160]!r}"
            etablis.append(e)
            continue
        motif = _motif(e)
        retenu: Optional[tuple[int, str]] = None
        for t in textes:
            t1 = _typographie(t)
            passages = {}
            for m in motif.finditer(t1):
                p = _passage(t1, m.start(), m.end())
                passages.setdefault(normaliser(p), p)
            if len(passages) > 1:
                return [], (f"extrait court {e!r} non discriminant : {len(passages)} passages différents "
                            "du document le contiennent")
            if passages and (retenu is None or len(t) > retenu[0]):
                retenu = (len(t), next(iter(passages.values())))
        if retenu is None:
            return [], f"extrait introuvable dans le texte rapporté : {e[:160]!r}"
        if len(retenu[1]) < EXTRAIT_MIN_CARS:
            return [], (f"extrait court {e!r} non discriminant : son passage {retenu[1]!r} a moins de "
                        f"{EXTRAIT_MIN_CARS} caractères")
        etablis.append(retenu[1])
    return etablis, None
