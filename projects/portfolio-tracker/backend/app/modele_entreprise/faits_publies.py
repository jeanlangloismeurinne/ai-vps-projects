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

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from app.contracts.modele_entreprise_schema import Bloc, BlocPropose, RattachementPublie

__all__ = [
    "poser_maille", "membres_du_bloc", "parent_de_membre", "parent_publie_de",
    "est_premier_niveau_publie", "motif_regroupement_incoherent", "axes_de_la_ventilation",
    "axes_sans_bloc_publie", "MembreImpose", "PremierNiveau", "premier_niveau_impose", "id_de_bloc",
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


# ── Le PREMIER NIVEAU IMPOSÉ (plan « découpage » B4g, étape 1, arbitrage du 2026-10-23) ─────────────
# Ce que ferait un vrai fonds : les segments que l'entreprise publie sont la colonne vertébrale du
# modèle — c'est à leur maille que se lisent l'historique, la prévision de la direction et le
# consensus ; la rotation des produits vit DANS la croissance d'un segment ; seuls les paris qu'il
# faut chiffrer à part s'en détachent. Le code établit donc le premier niveau ; l'architecte ne décide
# plus que des exceptions. Le CHOIX de l'axe est une décision du fonds au référentiel
# (`axes_du_premier_niveau`, par priorité) : « ce qu'on saura projeter » — le chiffre d'affaires se
# projette par ce que l'entreprise VEND (marché × part × prix), donc l'axe des produits et services
# d'abord ; à défaut l'information sectorielle officielle.

@dataclass(frozen=True)
class MembreImpose:
    bloc_id: str          # identifiant posé par le CODE, que l'architecte recopie
    membre: str           # qname du membre publié
    libelle: str
    montant: float        # chiffre d'affaires publié à la période de référence, unité déposée ($)


@dataclass(frozen=True)
class PremierNiveau:
    """`membres` vide = RIEN d'imposé, et `axes_ecartes` dit pourquoi (l'architecte compose, le comité
    lit la raison) — c'est le cas d'un axe prioritaire PUBLIÉ mais inexploitable."""
    axe: Optional[str]
    periode: Optional[str]          # l'exercice annuel de référence du découpage le plus récent
    membres: tuple[MembreImpose, ...]
    axes_ecartes: tuple[tuple[str, str], ...] = ()   # (axe prioritaire non retenu, pourquoi)

    @property
    def impose(self) -> bool:
        return bool(self.membres)


def id_de_bloc(libelle: str) -> str:
    """Un identifiant de bloc lisible tiré du LIBELLÉ publié (jamais d'un nom écrit dans le code) :
    minuscules ASCII, chiffres, `_` simple — le format du contrat (`^[a-z][a-z0-9_]*$`, sans `__`)."""
    s = unicodedata.normalize("NFKD", libelle).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    s = re.sub(r"_+", "_", s)[:50]
    if not s or not s[0].isalpha():
        s = f"segment_{s}".rstrip("_")
    return s


def _ids_uniques(libelles: list[str]) -> list[str]:
    vus: dict[str, int] = {}
    out = []
    for lib in libelles:
        base = id_de_bloc(lib)
        n = vus.get(base, 0) + 1
        vus[base] = n
        out.append(base if n == 1 else f"{base}_{n}")
    return out


def _non_impose(ecartes: list[tuple[str, str]]) -> Optional[PremierNiveau]:
    """Un axe publié mais inexploitable : rien d'imposé, la raison dite."""
    return PremierNiveau(axe=None, periode=None, membres=(), axes_ecartes=tuple(ecartes))


def premier_niveau_impose(ventilation_structure: Optional[dict],
                          axes_par_priorite: list[str]) -> Optional[PremierNiveau]:
    """Le premier axe (dans l'ordre du référentiel) dont le découpage le plus récent publié a AU MOINS
    deux membres au premier niveau, un exercice annuel de référence établi (publié ou par addition
    vérifiée, `perimetre.py`), et dont la somme BOUCLE avec le chiffre d'affaires des comptes à cet
    exercice. On ne passe à l'axe SUIVANT que si l'émetteur ne publie PAS l'axe courant : un axe
    publié mais inexploitable arrête la descente — rien n'est imposé (`membres` vide) et la raison est
    dite. Mesuré le 2026-10-23 (frontière gratuite, `pn_temoins`) : Apple publie ses produits sur un axe
    qui porte DEUX découpages superposés (iPhone/Mac/… et Produits/Services) ; leur somme ne boucle pas,
    et descendre à l'axe suivant imposait ses secteurs GÉOGRAPHIQUES — inutilisables pour projeter.
    `None` si aucun axe n'est publié (secteur unique, ventilation absente) : l'architecte compose
    alors tout le classeur, comme avant. Pure."""
    if not ventilation_structure:
        return None
    ecartes: list[tuple[str, str]] = []
    chroniques = ventilation_structure.get("chroniques") or []
    for axe in axes_par_priorite:
        chron = next((c for c in chroniques if c["axe"] == axe and c["ligne"] == "chiffre_affaires"), None)
        if chron is None:
            ecartes.append((axe, "l'émetteur ne publie pas de chiffre d'affaires sur cet axe"))
            continue
        membres = list((chron.get("regime_reference") or {}).get("premier_niveau") or [])
        periode = chron.get("periode_annuelle_reference")
        if len(membres) < 2:
            # Une seule activité sur cet axe n'est pas un découpage : on passe à l'axe suivant.
            ecartes.append((axe, "un seul membre au premier niveau du découpage le plus récent"))
            continue
        if not periode:
            ecartes.append((axe, "aucun exercice annuel établi dans le découpage le plus récent"))
            return _non_impose(ecartes)
        raccord = next((r for r in ventilation_structure.get("raccords") or []
                        if r["axe"] == axe and r["ligne"] == "chiffre_affaires" and r["periode"] == periode
                        and r.get("niveau") == "total"), None)
        if raccord is None or raccord.get("statut") != "boucle":
            ecartes.append((axe, f"la somme du premier niveau ne boucle pas avec le chiffre d'affaires "
                                 f"des comptes à `{periode}`"))
            return _non_impose(ecartes)
        cellules = {c["membre"]: c for c in ventilation_structure.get("cellules") or []
                    if c["axe"] == axe and c["ligne"] == "chiffre_affaires" and c["periode"] == periode}
        if any(m not in cellules for m in membres):
            ecartes.append((axe, f"un membre du premier niveau n'a pas de chiffre d'affaires à `{periode}`"))
            return _non_impose(ecartes)
        ordonnes = sorted(membres, key=lambda m: (-cellules[m]["v"], m))
        libelles = [cellules[m].get("libelle") or m.split(":")[-1] for m in ordonnes]
        return PremierNiveau(
            axe=axe, periode=periode,
            membres=tuple(MembreImpose(bloc_id=i, membre=m, libelle=l, montant=cellules[m]["v"])
                          for i, m, l in zip(_ids_uniques(libelles), ordonnes, libelles)),
            axes_ecartes=tuple(ecartes))
    return None
