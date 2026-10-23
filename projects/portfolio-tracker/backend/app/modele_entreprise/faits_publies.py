"""Les FAITS PUBLIÉS — ce que le CODE établit à partir de la ventilation, jamais déclaré par le
modèle (lot M3 bis, roadmap V3 `13-lot-M3bis-structure.md` §2, cause ①). NOUVEAU, PUR : aucune IO.

CE QUI RESTE AU MODÈLE (arbitrage 09 §1.1/§2, inchangé) : l'axe du premier niveau, la maille à
laquelle il s'arrête (un membre publié peut rester un seul bloc sans ses enfants), les
REGROUPEMENTS (plusieurs membres publiés d'un même axe et d'un même niveau en un bloc), les
découpages plus fins que la publication (estimés), les programmes, extensions, blocs communs, les
variables.

CE QUE LE CODE ÉTABLIT (cause ① — le contrat laissait le modèle AFFIRMER deux faits qu'il connaît
déjà, et les contrôles les croyaient sur parole) :
  · la MAILLE d'un bloc — `publie` s'il cite une adresse (`RattachementPublie`), `estime` sinon
    (`poser_maille`) ;
  · l'EMBOÎTEMENT entre blocs PUBLIÉS — le parent d'un bloc publié est le bloc publié dont un
    membre est l'ANCÊTRE (sur le MÊME axe, dans la hiérarchie relevée de la ventilation) d'un des
    membres du bloc (`parent_publie_de`, `est_premier_niveau_publie`). Un bloc publié n'a donc
    JAMAIS de `RattachementParent` déclaré (le contrat ne lui en laisse pas la forme) — seul un
    bloc ESTIMÉ se rattache librement.

Détenteur unique (#46) de cette dérivation : `structure.py` ([S1]-[S3], [S7], [S10]) et
`architecte.py` (pose de l'en-tête) l'appellent tous, pour que « ce que le modèle a composé » et
« ce que le code établit » ne puissent jamais diverger.
"""
from __future__ import annotations

from typing import Optional

from app.contracts.modele_entreprise_schema import Bloc, BlocPropose, RattachementPublie

__all__ = [
    "poser_maille", "membres_du_bloc", "parent_de_membre", "parent_publie_de",
    "est_premier_niveau_publie", "motif_regroupement_incoherent", "axes_de_la_ventilation",
    "axes_sans_bloc_publie",
]


def membres_du_bloc(bloc) -> tuple[str, ...]:
    """Les membres XBRL d'un bloc PUBLIÉ (regroupement compris) ; `()` pour un bloc estimé."""
    if isinstance(bloc.rattachement, RattachementPublie):
        return tuple(bloc.rattachement.membres)
    return ()


def poser_maille(blocs_proposes: list[BlocPropose]) -> list[Bloc]:
    """Pose `Bloc.maille` sur chaque bloc proposé par le modèle : `publie` si son rattachement est
    `RattachementPublie`, `estime` sinon. DÉTENTEUR UNIQUE de cette dérivation (#46) — posée UNE
    fois, ici, en même temps que l'en-tête (§4.1 point 4 de la spec), jamais recopiée."""
    out: list[Bloc] = []
    for b in blocs_proposes:
        maille = "publie" if isinstance(b.rattachement, RattachementPublie) else "estime"
        out.append(Bloc(**b.model_dump(), maille=maille))
    return out


def parent_de_membre(ventilation_structure: Optional[dict], membre: str) -> Optional[str]:
    """Le parent XBRL d'UN membre, dans la hiérarchie DU DÉCOUPAGE qui le publie (lot P1 §3) : celle
    du découpage de référence de la vue servie (`cellules`) si le membre y figure, sinon celle du
    découpage antérieur (`cellules_anterieures`) — jamais une hiérarchie fusionnée entre dépôts.
    `None` si le membre est de premier niveau, ou si aucune ventilation n'existe
    (`secteur_unique`/`sans_ventilation`). DÉTENTEUR UNIQUE (#46)."""
    if ventilation_structure is None:
        return None
    for source in ("cellules", "cellules_anterieures"):
        cellules = [c for c in (ventilation_structure.get(source) or []) if c.get("membre") == membre]
        if cellules:
            return next((c["parent"] for c in cellules if c.get("parent")), None)
    return None


def parent_publie_de(bloc: Bloc, par_bloc: dict[str, Bloc],
                     ventilation_structure: Optional[dict]) -> Optional[str]:
    """L'id du bloc PUBLIÉ qui est l'ANCÊTRE de `bloc` (un de ses membres est, sur le MÊME axe,
    l'ancêtre d'un des membres de `bloc` dans la hiérarchie relevée) — `None` si `bloc` n'a pas
    d'ancêtre publié dans l'architecture (bloc de premier niveau), ou si `bloc` n'est pas publié.

    Parcours BORNÉ (`range(len(par_bloc) + 1)`), jamais un `while` dont la seule garantie de
    terminaison serait un ensemble de visités — même précédent que `Architecture._coherence_interne`
    (#feedback_test_negatif_trois_faux_verts : un `while` affaibli bouclerait à l'infini)."""
    if not isinstance(bloc.rattachement, RattachementPublie):
        return None
    axe = bloc.rattachement.axe
    autres_membres_publies: dict[str, str] = {}
    for autre in par_bloc.values():
        if autre.id == bloc.id or not isinstance(autre.rattachement, RattachementPublie):
            continue
        if autre.rattachement.axe != axe:
            continue
        for m in autre.rattachement.membres:
            autres_membres_publies[m] = autre.id

    for depart in bloc.rattachement.membres:
        cur = parent_de_membre(ventilation_structure, depart)
        vus: set[str] = set()
        for _ in range(len(par_bloc) + 1):
            if cur is None:
                break
            if cur in autres_membres_publies:
                return autres_membres_publies[cur]
            if cur in vus:
                break
            vus.add(cur)
            cur = parent_de_membre(ventilation_structure, cur)
    return None


def est_premier_niveau_publie(bloc: Bloc, par_bloc: dict[str, Bloc],
                              ventilation_structure: Optional[dict]) -> bool:
    """`True` si `bloc` est de PREMIER NIVEAU : publié sans ancêtre publié dans l'architecture, ou
    estimé sans `RattachementParent` déclaré (`RattachementAgrege` — vocabulaire étendu de [S2]/[S3],
    qui ne porte en pratique que sur les blocs publiés)."""
    if not isinstance(bloc.rattachement, RattachementPublie):
        return bloc.rattachement.type != "parent"
    return parent_publie_de(bloc, par_bloc, ventilation_structure) is None


def motif_regroupement_incoherent(bloc: Bloc, ventilation_structure: Optional[dict]) -> Optional[str]:
    """`None` si le regroupement (`len(membres) > 1`) de `bloc` est cohérent — tous les membres du
    MÊME axe (garanti par le contrat, un seul `axe` par rattachement) et des MÊMES parents — un
    motif nommé sinon (1.2.0, cause ①, [S1])."""
    if not isinstance(bloc.rattachement, RattachementPublie) or len(bloc.rattachement.membres) <= 1:
        return None
    parents = {m: parent_de_membre(ventilation_structure, m) for m in bloc.rattachement.membres}
    if len(set(parents.values())) > 1:
        return (f"le bloc `{bloc.id}` regroupe les membres {sorted(bloc.rattachement.membres)}, de "
                f"parents différents ({parents}) — un regroupement publié est un ensemble de "
                "membres du MÊME axe ET des MÊMES parents, pas un bloc estimé")
    return None


def axes_de_la_ventilation(ventilation_structure: Optional[dict]) -> set[str]:
    """Les axes que porte la ventilation du titre — `set()` pour `secteur_unique`/`sans_ventilation`."""
    if ventilation_structure is None:
        return set()
    return set(ventilation_structure.get("axes") or [])


def axes_sans_bloc_publie(blocs: list[Bloc], ventilation_structure: Optional[dict]) -> set[str]:
    """Les axes de la ventilation qu'AUCUN bloc publié n'occupe — [S10] : chacun doit avoir son
    `usage` dans `Architecture.autres_axes`, sinon c'est un axe OUBLIÉ."""
    axes_couverts = {b.rattachement.axe for b in blocs if isinstance(b.rattachement, RattachementPublie)}
    return axes_de_la_ventilation(ventilation_structure) - axes_couverts
