"""Les CONTRÔLES DE STRUCTURE [S1]-[S11] — lot M3 (roadmap V3 `12-lot-M3-architecte.md` §5), étendus
par le lot M3 bis (`13-lot-M3bis-structure.md` §2/§5/§7) : [S10] (place des autres axes, cause ①),
[S11] (dimensions typées, cause ④). [S12] (maturité ≠ origine, cause ⑤) est un invariant d'UN SEUL
objet (#37) : il vit dans le contrat (`BlocPropose._s12_acquisition_jamais_en_developpement`),
jamais ici.

`valider_structure(arch, ref, matiere) -> list[str]` rend les SIGNAUX (ce que le comité verra) et lève
`ArchitectureRefusee` avec TOUS les motifs réunis — un par règle en défaut, code en tête — jamais au
premier refus (précédent #101). Ces contrôles portent sur la STRUCTURE et la ventilation publiée, JAMAIS
sur le sens (#68) : le raccord CHIFFRÉ (le détail estimé qui boucle avec son parent, l'agrégé qui boucle
avec les comptes) est M5, il faut des cellules — M3/M3bis ne contrôlent que ce qui se décide à la
signature.

CE QUI A CHANGÉ AU LOT M3 BIS (cause ①) : la maille et l'emboîtement entre blocs publiés ne sont plus
des AFFIRMATIONS du modèle crues sur parole — `app/modele_entreprise/faits_publies.py` les ÉTABLIT
depuis la hiérarchie relevée de la ventilation. « Premier niveau » se lit désormais par
`faits_publies.est_premier_niveau_publie`, jamais par un `RattachementParent` déclaré sur un bloc
publié (le contrat ne lui en laisse même plus la forme, §2 de la spec).
"""
from __future__ import annotations

import math
from typing import Optional

from app.contracts.formule_grammaire import FormuleInexecutable, noms_de_la_formule
from app.contracts.modele_entreprise_schema import (
    Architecture, Bloc, RattachementAgrege, RattachementPublie,
)
from app.modele_entreprise.dimensions import (
    DimensionIncoherente, UniteInfo, conversions_de, dimension_de, verifier_periode_ligne)
from app.knowledge.perimetre import ordre_des_periodes, premier_niveau_de
from app.modele_entreprise.faits_publies import (
    axes_sans_bloc_publie, est_premier_niveau_publie, motif_regroupement_incoherent,
)
from app.modele_entreprise.matiere import Matiere
from app.modele_entreprise.referentiel import ReferentielModele, _fiche_ou_propre

__all__ = ["ArchitectureRefusee", "valider_structure"]


class ArchitectureRefusee(Exception):
    """Un ou plusieurs contrôles [S1]-[S11] refusent — TOUS les motifs réunis, un par règle en
    défaut, code en tête (précédent #101 : jamais au premier refus)."""


def _ligne_somme(arch: Architecture, ref: ReferentielModele, bloc: Bloc) -> Optional[str]:
    """La ligne `somme_vers_ligne` visée par ce bloc, s'il retient une variable qui la porte — « bloc
    de chiffre d'affaires » au sens du §5 de la spec."""
    for vid in bloc.variables:
        fiche = _fiche_ou_propre(arch, ref, vid)
        if fiche is not None and getattr(fiche, "somme_vers_ligne", None):
            return fiche.somme_vers_ligne
    return None


def _cellules_vent(matiere: Matiere) -> list[dict]:
    return (matiere.ventilation_structure or {}).get("cellules") or []


def _membres_nouveaux(matiere: Matiere) -> list[dict]:
    return (matiere.ventilation_structure or {}).get("membres_nouveaux") or []


def _cellules_anterieures(matiere: Matiere) -> list[dict]:
    """Le découpage ANTÉRIEUR tel que publié (`perimetre.vue_servie`) — l'architecte peut le suivre
    (liberté de composition, 09 §1.1) ; [S3b] le signale au comité."""
    return (matiere.ventilation_structure or {}).get("cellules_anterieures") or []


def _chronique(matiere: Matiere, axe: str, ligne: str) -> Optional[dict]:
    return next((c for c in (matiere.ventilation_structure or {}).get("chroniques") or []
                 if c["axe"] == axe and c["ligne"] == ligne), None)


def _premier_niveau_par_periode(cellules: list[dict]) -> dict[str, set[str]]:
    """Le PREMIER NIVEAU publié à chaque période — détenteur unique `perimetre.premier_niveau_de`
    (#46), jamais recopié en dur ici (un enfant emboîté n'est pas un membre à couvrir isolément)."""
    presents: dict[str, dict[str, Optional[str]]] = {}
    for c in cellules:
        presents.setdefault(c["periode"], {})[c["membre"]] = c.get("parent")
    return {p: set(premier_niveau_de(parents.keys(), parents)) for p, parents in presents.items()}


def _cle_tri_periode(periode: str) -> tuple:
    """DÉLÉGUÉE au détenteur unique `perimetre.ordre_des_periodes` (lot P1, §2.5) — l'ancienne copie
    triait sur la PREMIÈRE date rencontrée (le DÉBUT d'un cumul) ; ce détenteur trie sur la FIN."""
    return ordre_des_periodes(periode)


# ── [S1] ────────────────────────────────────────────────────────────────────────────────────────

def _s1(arch: Architecture, matiere: Matiere) -> Optional[str]:
    blocs_publies = [b for b in arch.blocs if isinstance(b.rattachement, RattachementPublie)]
    if matiere.ventilation_structure is None:
        if blocs_publies:
            return (f"[S1] la ventilation du titre n'a aucun axe (statut non ventilé) : aucun bloc "
                    f"publié n'est admis, {[b.id for b in blocs_publies]} en citent un")
        return None
    adresses = {(c["axe"], c["membre"]) for c in _cellules_vent(matiere) + _cellules_anterieures(matiere)}
    adresses |= {(m["axe"], m["membre"]) for m in _membres_nouveaux(matiere)}
    motifs: list[str] = []
    for b in blocs_publies:
        manquants = [m for m in b.rattachement.membres if (b.rattachement.axe, m) not in adresses]
        if manquants:
            motifs.append(
                f"le bloc `{b.id}` cite (axe={b.rattachement.axe}, membre(s)={manquants}), absent(s) "
                "de la ventilation du titre")
    for b in blocs_publies:
        motif_regroupement = motif_regroupement_incoherent(b, matiere.ventilation_structure)
        if motif_regroupement:
            motifs.append(motif_regroupement)
    if motifs:
        return "[S1] " + "; ".join(motifs)
    return None


# ── [S2]/[S3b] ──────────────────────────────────────────────────────────────────────────────────

def _s2_s3b(arch: Architecture, ref: ReferentielModele, matiere: Matiere,
           par_bloc: dict[str, Bloc]) -> tuple[Optional[str], list[str]]:
    """Rend `(refus, signaux)`. Couverture au PREMIER NIVEAU — l'emboîtement sous chaque bloc publié
    qui a des enfants-blocs n'est PAS rejoué ici (le raccord chiffré de l'emboîtement est M5).

    Lot P1 (§3, §7 bis) : la ventilation lue est la VUE SERVIE. Si les blocs suivent le découpage de
    RÉFÉRENCE (le plus récent publié), la période de référence est sa période ANNUELLE de référence
    (`chroniques[…].periode_annuelle_reference` : le dernier exercice complet, publié ou par addition
    vérifiée) — jamais un cumul ni des douze mois calculés. S'ils suivent un découpage ANTÉRIEUR (tel
    que publié), la période de référence est la plus récente de ce découpage qui les couvre, et
    [S3b] le signale au comité. Mêler les deux est un découpage mixte, refusé."""
    blocs_publies = [b for b in arch.blocs if isinstance(b.rattachement, RattachementPublie)]
    premier_niveau_publies = [
        b for b in blocs_publies if est_premier_niveau_publie(b, par_bloc, matiere.ventilation_structure)]
    if not premier_niveau_publies:
        return None, []
    axes = {b.rattachement.axe for b in premier_niveau_publies}
    if len(axes) != 1:
        return None, []  # [S3] le dira — [S2] ne peut pas choisir un axe de référence
    axe = next(iter(axes))
    membres_vises = {m for b in premier_niveau_publies for m in b.rattachement.membres}

    def _ca(cellules: list[dict]) -> list[dict]:
        return [c for c in cellules if c["axe"] == axe and c["ligne"] == "chiffre_affaires"]

    cellules_ref = _ca(_cellules_vent(matiere))
    cellules_ant = _ca(_cellules_anterieures(matiere))
    par_periode_ref = _premier_niveau_par_periode(cellules_ref)
    par_periode_ant = _premier_niveau_par_periode(cellules_ant)
    chron = _chronique(matiere, axe, "chiffre_affaires")

    couvrantes_ref = [p for p, ms in par_periode_ref.items() if membres_vises <= ms]
    couvrantes_ant = [p for p, ms in par_periode_ant.items() if membres_vises <= ms]
    signaux: list[str] = []
    if couvrantes_ref:
        cellules_ca, par_periode = cellules_ref, par_periode_ref
        annuelle = chron.get("periode_annuelle_reference") if chron else None
        reference = annuelle if annuelle in couvrantes_ref else max(couvrantes_ref, key=_cle_tri_periode)
    elif couvrantes_ant:
        cellules_ca, par_periode = cellules_ant, par_periode_ant
        reference = max(couvrantes_ant, key=_cle_tri_periode)
        recents = (chron or {}).get("regime_reference", {}).get("premier_niveau") or sorted(
            {m for ms in par_periode_ref.values() for m in ms})
        signaux.append(
            f"[S3b] l'architecture suit un découpage ANTÉRIEUR de l'axe `{axe}` (période de référence "
            f"`{reference}`, tel que publié), pas le découpage de référence — le plus récent publié : "
            f"{sorted(recents)} — le titre a redécoupé ; l'historique du découpage le plus récent est "
            "dans la ventilation (publié ou par addition vérifiée)")
    else:
        return (f"[S2] découpage mixte : aucune période de l'axe `{axe}` (ligne chiffre_affaires) ne "
                f"porte une cellule pour chacun des membres visés {sorted(membres_vises)}, ni dans le "
                f"découpage le plus récent ni dans un découpage antérieur"), []

    membres_hors_blocs = par_periode[reference] - membres_vises
    a_un_reste = any(
        isinstance(b.rattachement, RattachementAgrege) and _ligne_somme(arch, ref, b) is not None
        for b in arch.blocs)
    if membres_hors_blocs:
        montants = {m: next(c["v"] for c in cellules_ca
                            if c["periode"] == reference and c["membre"] == m)
                   for m in membres_hors_blocs}
        if not a_un_reste:
            total = sum(c["v"] for c in cellules_ca
                        if c["periode"] == reference and c["membre"] in par_periode[reference])
            part = sum(montants.values()) / total * 100 if total else 0.0
            return (f"[S2] à la période de référence `{reference}` (axe `{axe}`), les membres "
                    f"{sorted(membres_hors_blocs)} ({montants}) ne sont couverts par aucun bloc "
                    f"publié et aucun bloc estimé « reste » rattaché (agrege) n'existe — "
                    f"{part:.1f} % du total non couvert"), signaux
        signaux.append(
            f"[S2] le « reste » couvre les membres {sorted(membres_hors_blocs)} à `{reference}` "
            f"(axe `{axe}`), montants {montants}")
    return None, signaux


# ── [S3] ────────────────────────────────────────────────────────────────────────────────────────

def _s3(arch: Architecture, matiere: Matiere, par_bloc: dict[str, Bloc]) -> Optional[str]:
    """Un seul axe pour les blocs PUBLIÉS de premier niveau. Le double compte entre un bloc publié
    et son propre sous-membre publié (Data Center / Compute côte à côte, sans lien de parenté) ne
    peut plus se présenter DÉCLARATIVEMENT depuis le lot M3 bis (cause ①) : l'emboîtement entre
    blocs publiés est DÉRIVÉ (`faits_publies.est_premier_niveau_publie`) — un membre descendant d'un
    autre bloc publié est automatiquement classé hors premier niveau, donc écarté de la somme [S7].
    Si le modèle le compte malgré tout dans une formule de passage, c'est [S7] qui le nomme (« en
    trop ») — pas ce contrôle, qui ne porte que sur l'AXE."""
    blocs_publies = [b for b in arch.blocs if isinstance(b.rattachement, RattachementPublie)]
    premier_niveau_publies = [
        b for b in blocs_publies if est_premier_niveau_publie(b, par_bloc, matiere.ventilation_structure)]
    axes = {b.rattachement.axe for b in premier_niveau_publies}
    if len(axes) > 1:
        return (f"[S3] les blocs publiés de premier niveau sont sur plusieurs axes {sorted(axes)} — "
                f"un seul axe au premier niveau")
    return None


# ── [S4] ────────────────────────────────────────────────────────────────────────────────────────

def _s4(arch: Architecture, ref: ReferentielModele) -> Optional[str]:
    par_bloc = {b.id: b for b in arch.blocs}
    for b in arch.blocs:
        if isinstance(b.rattachement, RattachementAgrege):
            famille = ref.familles_de_comptes.get(arch.famille)
            if famille is not None and b.rattachement.ligne not in famille.lignes_du_business_plan:
                return (f"[S4] le bloc `{b.id}` (agrege) vise `{b.rattachement.ligne}`, absente du "
                        f"business plan de la famille `{arch.famille}`")
        if b.rattachement.type == "parent":
            parent = par_bloc.get(b.rattachement.bloc)
            if parent is not None and parent.role == "commun":
                return (f"[S4] le bloc `{b.id}` est rattaché (parent) au bloc commun `{parent.id}` — "
                        "un découpage estimé ne se loge jamais dans les frais de structure")
    return None


# ── [S5] ────────────────────────────────────────────────────────────────────────────────────────

def _s5(arch: Architecture, matiere: Matiere) -> Optional[str]:
    if matiere.ventilation_structure is not None:
        return None
    fautifs = [b for b in arch.blocs if b.role != "commun" and b.maille != "estime"]
    if fautifs:
        return (f"[S5] ventilation `secteur_unique`/`sans_ventilation` : les blocs "
                f"{[b.id for b in fautifs]} ne sont pas `estime` — aucune maille publiée n'existe "
                "pour cet émetteur")
    return None


# ── [S6] ────────────────────────────────────────────────────────────────────────────────────────

def _s6(arch: Architecture, matiere: Matiere) -> Optional[str]:
    for b in arch.blocs:
        hors = [p for p in b.pieces if p not in matiere.pieces_citables]
        if hors:
            # Lot M3 ter, §2 : le motif RAPPELLE la liste des pièces citables — même liste que la
            # section « Pièces que tu peux citer » de la matière (un seul détenteur,
            # `Matiere.pieces_citables`) — pour que le renvoi puisse corriger sans redemander le dossier.
            return (f"[S6] le bloc `{b.id}` cite les pièces {hors}, hors de `pieces_citables` du "
                    "dossier (une justification sur une pièce hors du dossier) — pièces citables : "
                    f"{sorted(matiere.pieces_citables)}")
    return None


# ── [S7] ────────────────────────────────────────────────────────────────────────────────────────

def _variable_somme_du_bloc(arch: Architecture, ref: ReferentielModele, bloc: Bloc,
                            ligne: str) -> Optional[str]:
    for vid in bloc.variables:
        fiche = _fiche_ou_propre(arch, ref, vid)
        if fiche is not None and getattr(fiche, "somme_vers_ligne", None) == ligne:
            return vid
    return None


def _s7(arch: Architecture, ref: ReferentielModele, matiere: Matiere) -> Optional[str]:
    par_bloc = {b.id: b for b in arch.blocs}
    lignes_visees = {l for b in arch.blocs if (l := _ligne_somme(arch, ref, b))}
    if not lignes_visees:
        return None
    for ligne in sorted(lignes_visees):
        blocs_premier_niveau = [
            b for b in arch.blocs
            if est_premier_niveau_publie(b, par_bloc, matiere.ventilation_structure)
            and b.statut != "extension_annoncee"
            and _variable_somme_du_bloc(arch, ref, b, ligne) is not None]
        attendus = {f"{b.id}__{_variable_somme_du_bloc(arch, ref, b, ligne)}"
                   for b in blocs_premier_niveau}
        passage = next((p for p in arch.passage_a_l_agrege if p.ligne == ligne), None)
        if passage is None:
            return (f"[S7] un bloc de chiffre d'affaires vise la ligne `{ligne}`, mais aucune "
                    "formule de passage ne la porte")
        noms = set(noms_de_la_formule(passage.formule))
        if noms != attendus:
            manquants = attendus - noms
            en_trop = noms - attendus
            return (f"[S7] la formule de passage `{ligne}` porte {sorted(noms)}, attendu exactement "
                    f"{sorted(attendus)} (manquants {sorted(manquants)}, en trop {sorted(en_trop)})")
    return None


# ── [S8] ────────────────────────────────────────────────────────────────────────────────────────

def _s8(arch: Architecture) -> Optional[str]:
    annonces = {b.id for b in arch.blocs if b.statut == "extension_annoncee"}
    if not annonces:
        return None
    for p in arch.passage_a_l_agrege:
        for nom in noms_de_la_formule(p.formule):
            bloc_id = nom.split("__", 1)[0]
            if bloc_id in annonces:
                return (f"[S8] la formule de passage `{p.ligne}` référence `{nom}`, dont le bloc "
                        f"`{bloc_id}` est `extension_annoncee` — une option ne se compte jamais dans "
                        "le central")
    return None


# ── [S9] ────────────────────────────────────────────────────────────────────────────────────────

def _s9(arch: Architecture, ref: ReferentielModele, matiere: Matiere) -> Optional[str]:
    periodes_classeur = set(matiere.periodes_historiques) | set(matiere.periodes_projetees) | {"sans_periode"}
    for c in arch.cellules_attendues:
        hors = [p for p in c.periodes if p not in periodes_classeur]
        if hors:
            return (f"[S9] la cellule attendue (`{c.bloc}`, `{c.variable}`) porte les périodes {hors}, "
                    "hors des périodes du classeur")

    attendues_par_bloc_var: dict[tuple[str, str], set[str]] = {}
    for c in arch.cellules_attendues:
        attendues_par_bloc_var.setdefault((c.bloc, c.variable), set()).update(c.periodes)

    for p in arch.passage_a_l_agrege:
        for nom in noms_de_la_formule(p.formule):
            bloc_id, _, var_id = nom.partition("__")
            fiche = _fiche_ou_propre(arch, ref, var_id)
            if fiche is None or fiche.periode == "sans_periode":
                continue
            couvertes = attendues_par_bloc_var.get((bloc_id, var_id), set())
            manquantes = set(matiere.periodes_projetees) - couvertes
            if manquantes:
                return (f"[S9] `{bloc_id}__{var_id}` (lue par la formule de passage `{p.ligne}`) n'a "
                        f"pas de cellule attendue pour les périodes projetées {sorted(manquantes)} — "
                        "une cellule lue par l'agrégé que personne n'est chargé d'écrire")
    return None


# ── [S10] (lot M3 bis, cause ①) ────────────────────────────────────────────────────────────────

def _s10(arch: Architecture, matiere: Matiere) -> Optional[str]:
    """Tout axe de la ventilation qu'aucun bloc publié n'occupe a son `usage` dans `autres_axes` —
    un axe oublié (ni bloc, ni usage) est refusé : c'est la case qui manquait pour le second
    découpage publié d'un émetteur (#69 : le rendu d'un inventaire est un producteur)."""
    sans_bloc = axes_sans_bloc_publie(arch.blocs, matiere.ventilation_structure)
    axes_avec_usage = {a.axe for a in arch.autres_axes}
    oublies = sans_bloc - axes_avec_usage
    if oublies:
        return (f"[S10] l'axe/les axes {sorted(oublies)} de la ventilation ne porte(nt) aucun bloc "
                "publié et n'a/ont aucun `usage` déclaré dans `autres_axes` — un axe oublié")
    # Signal (pas un refus) : un `usage` déclaré pour un axe qui, lui, PORTE bien un bloc publié —
    # redondant, mais pas une erreur de structure.
    return None


# ── [S11] (lot M3 bis, cause ④) ────────────────────────────────────────────────────────────────

def _unites_et_periodes(arch: Architecture, ref: ReferentielModele,
                        bloc: Bloc) -> tuple[dict[str, UniteInfo], dict[str, Optional[str]]]:
    unites: dict[str, UniteInfo] = {}
    periodes: dict[str, Optional[str]] = {}
    for vid in bloc.variables:
        fiche = _fiche_ou_propre(arch, ref, vid)
        if fiche is None:
            continue
        info = ref.unites.get(fiche.unite)
        if info is None:
            continue
        unites[vid] = UniteInfo(dimension=(info.montant, info.quantite, info.temps), echelle=info.echelle)
        periodes[vid] = fiche.periode if fiche.periode in ("exercice", "instant") else None
    return unites, periodes


def _s11(arch: Architecture, ref: ReferentielModele) -> Optional[str]:
    """Les formules de passage à l'agrégé sont TYPÉES : dimension physique ET échelle en M$
    (montant^1, échelle 10⁶) pour toute ligne du business plan, et chaque terme additif respecte le
    cadrage (`flux`/`instant`) de sa ligne (`socle_comptes.yaml`, jamais une liste recopiée)."""
    from app.knowledge.socle_comptes import charger_gabarit
    gabarit = charger_gabarit()
    par_bloc = {b.id: b for b in arch.blocs}
    m_attendu = ref.unites.get("M$")
    if m_attendu is None:
        return None  # [R7] au chargement du référentiel aurait déjà refusé l'absence de `M$`
    dim_attendue = (m_attendu.montant, m_attendu.quantite, m_attendu.temps)
    conversions = conversions_de(u.echelle for u in ref.unites.values())
    for p in arch.passage_a_l_agrege:
        unites: dict[str, UniteInfo] = {}
        periodes: dict[str, Optional[str]] = {}
        for nom in noms_de_la_formule(p.formule):
            bloc_id, _, var_id = nom.partition("__")
            bloc = par_bloc.get(bloc_id)
            if bloc is None:
                continue
            u, per = _unites_et_periodes(arch, ref, bloc)
            unites.update(u)
            periodes.update(per)
        try:
            dim, echelle = dimension_de(p.formule, unites, conversions)
        except (DimensionIncoherente, FormuleInexecutable) as e:
            return f"[S11] la formule de passage `{p.ligne}` — {e}"
        if dim != dim_attendue or not math.isclose(echelle, m_attendu.echelle, rel_tol=1e-9):
            from app.modele_entreprise.dimensions import rendre_dimension
            return (f"[S11] la formule de passage `{p.ligne}` produit "
                    f"{rendre_dimension(dim)} (échelle {echelle}), attendu {rendre_dimension(dim_attendue)} "
                    f"(échelle {m_attendu.echelle}, M$) — une ligne du business plan est un montant en M$")
        ligne_gab = gabarit.lignes.get(p.ligne)
        if ligne_gab is not None:
            try:
                verifier_periode_ligne(p.formule, ligne_gab.cadrage, unites, periodes, ligne=p.ligne)
            except FormuleInexecutable as e:
                return f"[S11] {e}"
    return None


# ── [S14]/[S15] (lot M3 ter, §4 — une ligne par programme nommé) ─────────────────────────────────
# [S13] (un bloc non plateforme couvre UN SEUL programme) est un invariant d'UN SEUL objet (#37,
# même précédent que [S12]) : il vit dans le contrat (`BlocPropose._programmes_et_plateforme`),
# jamais ici. [S14]/[S15] exigent de connaître la MATIÈRE (le verbatim de `me_7`, son chiffre clé
# `nombre_de_programmes`) : ils vivent donc ici, comme tout contrôle qui compare DEUX objets.

_STATUT_ATTENDU_TRAITEMENT = {
    "bloc": "en_developpement", "rattache": "metier_actuel", "extension": "extension_annoncee",
}
# Ce que le renvoi dit au modèle quand le statut du bloc désigné ne va pas avec le traitement : la
# RÈGLE à appliquer, pas seulement le statut attendu — mesuré le 2026-10-23 (`mesures/2026-10-23/
# b4d-apres/`) : « attendu `metier_actuel` » seul a fait rattacher des programmes nommés à une
# plateforme, deux fois de suite, au lieu de leur donner leur ligne.
_REGLE_DU_TRAITEMENT = {
    "bloc": ("`bloc` = la ligne PROPRE d'un programme à réussite incertaine (un bloc `en_developpement` "
             "à lui) ; un produit déjà vendu n'est pas un programme : `rattache` vers son activité"),
    "rattache": ("`rattache` ne vaut que pour ce qui s'estime avec les HYPOTHÈSES DE MARCHÉ d'une activité "
                 "déjà vendue (génération suivante, nouveau segment de clients), vers le bloc `metier_actuel` "
                 "qui la porte ; ce qui demande ses propres données de marché et de concurrence (programme "
                 "nommé, extension d'indication) a SA ligne (traitement `bloc`) — une plateforme ne regroupe "
                 "que des programmes NON nommés (#143)"),
    "extension": "`extension` désigne le bloc `extension_annoncee` de l'activité annoncée",
}
_CONSIGNE_NOM_LITTERAL = (
    "recopie pour chacun un passage CONTINU du verbatim, mot pour mot : sans précision ajoutée (marque "
    "entre parenthèses…), sans article retiré, sans nom de regroupement inventé")


def _forme_comparable(texte: str) -> str:
    """Casse, espaces et apostrophes typographiques ne changent pas un nom : on compare sans eux.
    Rien d'autre n'est normalisé — l'ordre et les mots restent ceux du dossier."""
    texte = texte.replace("\u2019", "'").replace("\u2018", "'").replace("\u00a0", " ")
    return " ".join(texte.split()).casefold()


def _trouve_dans_pieces_ouvertes(nom_comparable: str, pieces_ouvertes_texte: dict[int, str]) -> Optional[int]:
    """Lot B4f, addendum du 2026-10-23 (§8) — la plus petite pièce OUVERTE dont le texte rendu
    contient littéralement ce nom (même comparaison que le verbatim de `me_7`, `_forme_comparable`),
    ou `None`. Détenteur unique de cette recherche — [S14] et [S15] l'appellent, aucun des deux ne la
    recopie."""
    for numero in sorted(pieces_ouvertes_texte):
        if nom_comparable and nom_comparable in _forme_comparable(pieces_ouvertes_texte[numero]):
            return numero
    return None


def _s14(arch: Architecture, matiere: Matiere) -> tuple[Optional[str], list[str]]:
    """Rend `(refus, signaux)`. Chaque nom de `programmes` et de `inventaire_des_programmes` figure
    LITTÉRALEMENT dans le verbatim de `me_7` OU dans une PIÈCE OUVERTE pendant le passage (lot B4f,
    addendum du 2026-10-23, §8 — sans quoi l'explorateur trouverait les programmes oubliés de `me_7`
    et ce contrôle les refuserait quand même) ; chaque entrée `bloc`/`rattache`/`extension` désigne un
    bloc EXISTANT du BON statut ; chaque bloc `en_developpement` non `plateforme` apparaît dans
    l'inventaire. Ce qui n'est PAS contrôlé (dit au comité) : qu'un programme ait été OUBLIÉ alors que
    ni `me_7` ni aucune pièce ouverte ne permet de le retrouver — hors de portée de ce lot."""
    par_bloc = {b.id: b for b in arch.blocs}
    motifs: list[str] = []
    signaux: list[str] = []

    noms_a_verifier: list[str] = [nom for b in arch.blocs for nom in b.programmes]
    noms_a_verifier += [item.programme for item in arch.inventaire_des_programmes]
    if noms_a_verifier:
        if matiere.me_7_verbatim is None and not matiere.pieces_ouvertes_texte:
            motifs.append(
                "[S14] un programme est nommé (`programmes` ou `inventaire_des_programmes`), mais "
                "aucun verbatim de `me_7` ni aucune pièce ouverte n'est disponible pour vérifier "
                "qu'il y figure littéralement")
        else:
            verbatim = _forme_comparable(matiere.me_7_verbatim) if matiere.me_7_verbatim else ""
            absents: list[str] = []
            for n in sorted(set(noms_a_verifier)):
                nc = _forme_comparable(n)
                if nc and nc in verbatim:
                    continue
                piece = _trouve_dans_pieces_ouvertes(nc, matiere.pieces_ouvertes_texte)
                if piece is not None:
                    signaux.append(
                        f"[S14] « {n} » absent de `me_7`, trouvé dans #{piece} — admis, "
                        "signalé au comité (mesure de l'instabilité possible de l'analyste de `me_7`)")
                    continue
                absents.append(n)
            if absents:
                motifs.append(f"[S14] les programmes {sorted(absents)} ne figurent pas LITTÉRALEMENT "
                              f"dans le verbatim de `me_7` ni dans aucune pièce ouverte — "
                              f"{_CONSIGNE_NOM_LITTERAL}")


    for item in arch.inventaire_des_programmes:
        if item.bloc is None:
            continue
        bloc = par_bloc.get(item.bloc)
        if bloc is None:
            motifs.append(f"[S14] l'entrée `{item.programme}` (traitement `{item.traitement}`) "
                          f"désigne le bloc `{item.bloc}`, absent de l'architecture")
            continue
        # Une ligne PROPRE est un bloc non plateforme qui porte CE nom — mesuré le 2026-10-23
        # (`mesures/2026-10-23/b4d-apres3/rvmd_1`) : six programmes nommés déclarés « ligne propre »
        # et tous pointés vers UNE plateforme, ce qui contournait [S13] (une plateforme n'a pas de nom).
        if item.traitement == "bloc" and (bloc.plateforme or [_forme_comparable(n) for n in bloc.programmes]
                                          != [_forme_comparable(item.programme)]):
            motifs.append(f"[S14] l'entrée `{item.programme}` (traitement `bloc`) désigne le bloc "
                          f"`{item.bloc}`, qui n'est pas SA ligne propre (plateforme : {bloc.plateforme}, "
                          f"programmes : {bloc.programmes}) — un programme nommé a un bloc à lui, dont "
                          "`programmes` porte son nom ; une plateforme ne regroupe que des programmes NON "
                          "nommés")
            continue
        attendu = _STATUT_ATTENDU_TRAITEMENT.get(item.traitement)
        if attendu is not None and bloc.statut != attendu:
            motifs.append(f"[S14] l'entrée `{item.programme}` (traitement `{item.traitement}`) "
                          f"désigne le bloc `{item.bloc}` de statut `{bloc.statut}`, attendu `{attendu}` — "
                          f"{_REGLE_DU_TRAITEMENT[item.traitement]}")

    couverts = {item.bloc for item in arch.inventaire_des_programmes if item.bloc is not None}
    for b in arch.blocs:
        if b.statut == "en_developpement" and not b.plateforme and b.id not in couverts:
            motifs.append(f"[S14] le bloc `{b.id}` (`en_developpement`, non `plateforme`) n'apparaît "
                          "dans aucune entrée de `inventaire_des_programmes`")

    return (" ; ".join(motifs) if motifs else None), signaux


def _s15(arch: Architecture, matiere: Matiere) -> tuple[Optional[str], list[str]]:
    """Le décompte de l'inventaire contre les DEUX chiffres clés de `me_7` : `nombre_de_programmes`
    (tous les éléments) et `nombre_de_programmes_non_nommes` (ceux que l'émetteur compte sans les
    nommer). Les deux établis → l'inventaire nomme EXACTEMENT la différence et les plateformes
    portent EXACTEMENT les non nommés — SIGNAL sinon (refus jusqu'au 2026-10-23, étape 0 du plan
    « découpage » : un contrôle ne connaît pas le nombre de programmes, c'est ce qu'on estime). Le second absent → l'écart est un SIGNAL, jamais
    un refus : mesuré le 2026-10-23 (`mesures/2026-10-23/banc-modeles/`), un refus adossé au seul
    total a été satisfait en INVENTANT une plateforme (RVMD : 8 comptés pour 7 nommés, un « 8ᵉ »
    fabriqué) ou en REMPLAÇANT un programme nommé par une plateforme (NVDA anonymisé : la génération
    suivante omise, un « cinquième, non détaillé » à sa place) — et a refusé la bonne architecture."""
    attendu = matiere.me_7_nombre_de_programmes
    declares_non_nommes = matiere.me_7_nombre_non_nommes
    verbatim = _forme_comparable(matiere.me_7_verbatim) if matiere.me_7_verbatim else ""
    # Lot B4f, addendum du 2026-10-23 (§8) — une entrée dont le nom est ABSENT de `me_7` mais trouvé
    # dans une pièce ouverte (admise par [S14]) s'ajoute au décompte SANS le fausser : elle est
    # retirée de la comparaison exacte contre `me_7` (`nommes_dans_me7`), et SIGNALÉE séparément —
    # c'est aussi le moyen de voir l'instabilité possible de l'analyste de `me_7`.
    items_hors_me7 = [
        item for item in arch.inventaire_des_programmes
        if not (_forme_comparable(item.programme) and _forme_comparable(item.programme) in verbatim)
    ]
    nommes = len(arch.inventaire_des_programmes)
    nommes_dans_me7 = nommes - len(items_hors_me7)
    en_plateforme = sum(b.nombre_de_programmes_non_nommes or 0 for b in arch.blocs if b.plateforme)
    signaux_hors_me7 = [
        f"[S15] « {item.programme} » absent de `me_7`, trouvé dans #"
        f"{_trouve_dans_pieces_ouvertes(_forme_comparable(item.programme), matiere.pieces_ouvertes_texte)} "
        "— ajouté au décompte attendu, ne le fausse pas"
        for item in items_hors_me7
    ]
    if attendu is None:
        return None, ["[S15] inventaire non chiffré : `me_7` n'établit pas le chiffre clé "
                     "`nombre_de_programmes`"] + signaux_hors_me7
    total = int(attendu)
    if declares_non_nommes is not None:
        d = int(declares_non_nommes)
        motifs = []
        if nommes_dans_me7 != total - d:
            motifs.append(
                f"l'inventaire nomme {nommes_dans_me7} élément(s) PRÉSENT(S) DANS `me_7`, `me_7` en "
                f"NOMME {total - d} (`nombre_de_programmes` = {total}, dont "
                f"`nombre_de_programmes_non_nommes` = {d}) — chaque élément nommé par `me_7` a SON "
                "entrée, sous son nom, même celui que tu rattaches ou mets hors modèle")
        if en_plateforme != d:
            motifs.append(
                f"les plateformes portent {en_plateforme} programme(s) non nommé(s), `me_7` en compte {d} "
                "— une plateforme ne porte QUE les programmes que le dossier dit non nommés, jamais un "
                "élément nommé qui manquerait à l'inventaire")
        # Étape 0 du plan « découpage » (2026-10-23, arbitrage de l'utilisateur) : un SIGNAL, plus un
        # refus. Le décompte de `me_7` est lui-même une estimation de l'analyste — instable (RVMD : 8
        # puis 5 sur les mêmes pièces) et à une autre unité que #143 (molécule ≠ indication) : refuser
        # sur lui a rejeté la meilleure architecture RVMD (`b4f-explorateur/`) et accepté une pire.
        signaux_ecart = (["[S15] décompte à lire au comité : " + " ; ".join(motifs)] if motifs else [])
        return None, signaux_ecart + signaux_hors_me7
    signaux = list(signaux_hors_me7)
    if nommes_dans_me7 + en_plateforme != total:
        signaux.append(
            f"[S15] écart non expliqué : `me_7` compte {total} programme(s), l'inventaire en nomme "
            f"{nommes_dans_me7} (présents dans `me_7`) et les plateformes en portent {en_plateforme} — "
            "le dossier ne dit pas combien il en compte sans les nommer : à lire au comité")
    if en_plateforme:
        signaux.append(
            f"[S15] plateforme de {en_plateforme} programme(s) non nommé(s) sans chiffre du dossier "
            "(`nombre_de_programmes_non_nommes` absent de `me_7`) : à lire au comité")
    return None, signaux


# ── [S16] (étape 0 du plan « découpage », 2026-10-23) ──────────────────────────────────────────

def _s16(arch: Architecture) -> Optional[str]:
    """Une même grandeur ne se compte qu'UNE fois dans un même total. Pour chaque équation du gabarit
    des comptes (`total = Σ composantes + reste`, détenteur unique : `socle_comptes.yaml`), un terme
    additif NU `bloc__variable` (seul, au signe près, sans coefficient) ne figure que dans UNE des lignes
    sœurs. Avec un coefficient (`commun__couts_communs * 0.6` ici, `* 0.4` là) c'est une RÉPARTITION,
    admise ; un sous-total (`marge_brute`) n'est pas la sœur de ses composantes. Mesuré : RVMD
    `apres-143/` — `commun__couts_communs` entier dans `recherche_developpement` ET dans
    `frais_commerciaux_administratifs`, accepté par [S1]-[S15]."""
    import ast
    from app.contracts.formule_grammaire import analyser_formule
    from app.knowledge.socle_comptes import charger_gabarit
    from app.modele_entreprise.dimensions import _termes_additifs
    nus_par_ligne: dict[str, set[str]] = {}
    for p in arch.passage_a_l_agrege:
        try:
            termes = _termes_additifs(analyser_formule(p.formule).body)
        except FormuleInexecutable:
            continue  # [S11] le dit
        nus_par_ligne.setdefault(p.ligne, set()).update(t.id for t in termes if isinstance(t, ast.Name))
    motifs: list[str] = []
    for eq in charger_gabarit().equations:
        soeurs = [t.ligne for t in eq.composantes] + ([eq.reste.ligne] if eq.reste else [])
        lignes_par_nom: dict[str, list[str]] = {}
        for ligne in soeurs:
            for nom in sorted(nus_par_ligne.get(ligne, ())):
                lignes_par_nom.setdefault(nom, []).append(ligne)
        for nom, lignes in sorted(lignes_par_nom.items()):
            if len(lignes) > 1:
                motifs.append(
                    f"`{nom}` est compté ENTIER dans {lignes}, qui s'additionnent dans `{eq.total}` — "
                    "double comptage : une grandeur va dans UNE ligne, ou se RÉPARTIT entre elles par "
                    "des coefficients dont la somme fait 1")
    return ("[S16] " + " ; ".join(motifs)) if motifs else None


def valider_structure(arch: Architecture, ref: ReferentielModele, matiere: Matiere) -> list[str]:
    """[S1]-[S11]. Rend les SIGNAUX ; lève `ArchitectureRefusee` avec TOUS les motifs réunis."""
    par_bloc = {b.id: b for b in arch.blocs}
    refus: list[str] = []
    signaux: list[str] = []

    for fn in (_s1,):
        m = fn(arch, matiere)
        if m:
            refus.append(m)

    m2, sig2 = _s2_s3b(arch, ref, matiere, par_bloc)
    if m2:
        refus.append(m2)
    signaux.extend(sig2)

    m3 = _s3(arch, matiere, par_bloc)
    if m3:
        refus.append(m3)

    m4 = _s4(arch, ref)
    if m4:
        refus.append(m4)

    m5 = _s5(arch, matiere)
    if m5:
        refus.append(m5)

    m6 = _s6(arch, matiere)
    if m6:
        refus.append(m6)

    m7 = _s7(arch, ref, matiere)
    if m7:
        refus.append(m7)

    m8 = _s8(arch)
    if m8:
        refus.append(m8)

    m9 = _s9(arch, ref, matiere)
    if m9:
        refus.append(m9)

    m10 = _s10(arch, matiere)
    if m10:
        refus.append(m10)

    m11 = _s11(arch, ref)
    if m11:
        refus.append(m11)

    m14, sig14 = _s14(arch, matiere)
    if m14:
        refus.append(m14)
    signaux.extend(sig14)

    m15, sig15 = _s15(arch, matiere)
    if m15:
        refus.append(m15)
    signaux.extend(sig15)

    m16 = _s16(arch)
    if m16:
        refus.append(m16)

    if refus:
        raise ArchitectureRefusee(" | ".join(refus))
    return signaux
