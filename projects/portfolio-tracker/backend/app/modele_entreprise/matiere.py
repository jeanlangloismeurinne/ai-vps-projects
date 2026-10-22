"""La MATIÈRE DE L'ARCHITECTE — lot M3, roadmap V3 `12-lot-M3-architecte.md` §3.3.

`charger_matiere(conn, ticker_id, *, publier)` est la SEULE moitié qui lit (et, avec `publier=True`,
publie la ventilation/le socle s'ils manquent) ; `rendre_matiere(m)` est PURE et déterministe — c'est
exactement ce que le modèle voit. Toute la matière est assemblée en texte à la LECTURE (`charger_matiere`),
jamais recalculée dans le rendu, qui ne fait qu'assembler des blocs déjà déterministes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

__all__ = ["MatiereRefusee", "Matiere", "charger_matiere", "rendre_matiere"]


class MatiereRefusee(Exception):
    """La matière ne peut pas être construite (famille sans gabarit, émetteur non classé…) — refus
    nommé, [P1] dirait la même chose plus tard contre une architecture qui aurait quand même été
    composée."""


@dataclass(frozen=True)
class Matiere:
    """Tout ce que l'architecte voit, DANS L'ORDRE DE RENDU (§3.3). `rendre_matiere` ne fait
    qu'assembler ces champs, déjà déterministes."""
    ticker_id: str
    raison_sociale: str
    cik: int
    date_du_jour: date
    derniere_cloture: Optional[date]
    derniere_cloture_annuelle: Optional[date]
    archetype: str
    classement_motif: str
    classement_date: date
    classement_declencheur: Optional[str]
    famille: str
    periodes_historiques: tuple[str, ...]
    periodes_projetees: tuple[str, ...]
    lignes_business_plan: tuple[str, ...]
    fiches_texte: str
    patron_texte: str
    socle_texte: str
    socle_piece_id: Optional[int]
    socle_structure: dict
    ventilation_texte: str
    ventilation_piece_id: Optional[int]
    # La structure de la ventilation (axes/cellules/raccords/membres_nouveaux, `structure_de_
    # ventilation`) — `None` si `secteur_unique`/`sans_ventilation` : [S1]-[S3] de `structure.py` la
    # lisent, le RENDU texte ne leur suffit pas (ils ont besoin de la hiérarchie des membres).
    ventilation_structure: Optional[dict]
    questions_texte: tuple[str, ...]          # une section par question, dans l'ordre de la porte
    notes_flash_texte: str
    pieces_citables: frozenset[int] = field(default_factory=frozenset)


def _ligne_lisible(ligne_id: str, gabarit) -> str:
    l = gabarit.lignes.get(ligne_id)
    return f"{ligne_id} ({l.libelle})" if l is not None else ligne_id


def _fiches_texte(fiches) -> str:
    out = []
    for v in fiches:
        somme = f" — somme_vers_ligne: {v.somme_vers_ligne}" if v.somme_vers_ligne else ""
        out.append(
            f"  · {v.id} ({v.libelle}) — unité {v.unite}, période {v.periode} ; origines admises "
            f"{v.origines_admises} ; questions sources {v.questions_sources}{somme}\n"
            f"    {v.definition}")
    return "\n".join(out) if out else "  (aucune fiche dans cette famille)"


def _patron_texte(patron) -> str:
    if patron is None:
        return "  (aucun patron de départ pour cet archétype — l'architecte compose entièrement)"
    out = []
    for bloc in patron.blocs:
        out.append(f"  · bloc {bloc.role} — variables suggérées : {', '.join(bloc.variables)}")
    return "\n".join(out)


def _reponse_retenue(reps):
    from app.agents.v2.parcours import reponse_tient
    tenant = next((r for r in reps if reponse_tient(r)), None)
    if tenant is not None:
        return tenant
    avec_date = [r for r in reps if r.cree_le is not None]
    if avec_date:
        return max(avec_date, key=lambda r: r.cree_le)
    return reps[0] if reps else None


def _texte_question(eq, etat) -> tuple[str, frozenset[int]]:
    """Le bloc d'une question source. Rend `(texte, pieces_citées)`."""
    reps = [r for r in etat.reponses
            if r.servie.framework_id == eq.framework_id and r.servie.question_id == eq.question_id]
    entete = f"— Question {eq.question_id} ({eq.framework_id}) — porte : " \
             f"{'ouvre' if eq.ouvre else 'ferme'} — {eq.raison}"
    r = _reponse_retenue(reps)
    if r is None:
        return f"{entete}\n  (aucune réponse instruite)", frozenset()

    lignes = [entete,
              f"  statut {r.servie.statut} ; écrite le "
              f"{r.cree_le.date().isoformat() if r.cree_le else '?'} ; verdict {r.verdict or '?'}"]
    if r.motif_revue:
        lignes.append(f"  motif du contrôle : {r.motif_revue}")
    pieces: set[int] = set()
    if r.servie.fondation is not None:
        lignes.append(f"  actualité {r.servie.fondation.actualite} — {r.servie.fondation.motif_actualite}")
        pieces |= set(r.servie.fondation.cited_entry_ids)
    if r.servie.reponse is not None:
        lignes.append(f"  verbatim : {r.servie.reponse.verbatim}")
        for ligne_chiffre in r.servie.reponse.encadre_lisible():
            lignes.append(f"    chiffre : {ligne_chiffre}")
        if r.servie.reponse.sens:
            lignes.append(f"  sens : {r.servie.reponse.sens}")
        for fp in r.servie.reponse.faits_posterieurs:
            pieces |= set(fp.cited_entry_ids)
    return "\n".join(lignes), frozenset(pieces)


def _piece_de_la_note(conn_rows: list[dict], accession: str) -> Optional[int]:
    nodash = accession.replace("-", "")
    candidats = [r["id"] for r in conn_rows if nodash in (r["source_url"] or "")]
    return min(candidats) if candidats else None


async def charger_matiere(conn, ticker_id: str, *, publier: bool) -> Matiere:
    """La SEULE moitié qui lit. `publier=True` publie la ventilation/le socle s'ils manquent ;
    `publier=False` (à blanc) ne rien écrit : la ventilation/le socle sont relevés en MÉMOIRE,
    leur id de pièce est `None` (le rendu dit « pièce non encore publiée »)."""
    from app.agents.v2.parcours import charger_etat_dossier, horloge_du_titre
    from app.knowledge.edgar_facts import EdgarUnavailable, fetch_company_facts
    from app.knowledge.edgar_feed import EdgarFeedUnavailable, identite_de_l_emetteur
    from app.knowledge.evenements import derniere_cloture_annuelle_publiee, derniere_cloture_publiee
    from app.knowledge.socle_comptes import (
        charger_gabarit, charger_reclassements, reconstituer, rendre_socle, structure_du_socle,
    )
    from app.knowledge.socle_feed import SocleIndisponible, assurer_socle, socle_en_vigueur
    from app.knowledge.ventilation import charger_referentiel as charger_referentiel_ventilation
    from app.knowledge.ventilation import relever, rendre_ventilation, structure_de_ventilation
    from app.knowledge.ventilation_feed import (
        VentilationIndisponible, assurer_ventilation, lire_depots, ventilation_en_vigueur,
    )
    from app.modele_entreprise.periodes import periodes_du_classeur
    from app.modele_entreprise.porte import porte_de_l_architecte
    from app.modele_entreprise.referentiel import (
        load_referentiel, questions_sources_applicables, variables_de_la_famille,
    )

    etat = await charger_etat_dossier(conn, ticker_id)
    if etat.archetype is None or etat.classement is None:
        raise MatiereRefusee(f"`{ticker_id}` n'est pas classé : aucune matière ne peut être construite")

    ref = load_referentiel()
    nom_famille = ref.famille_par_archetype.get(etat.archetype)
    famille = ref.familles_de_comptes.get(nom_famille) if nom_famille else None
    if nom_famille is None or famille is None or famille.gabarit is None:
        motif = famille.motif_absence if famille is not None else (
            f"archétype `{etat.archetype}` sans famille déclarée")
        raise MatiereRefusee(f"famille sans gabarit : {motif}")

    emetteur = await identite_de_l_emetteur(conn, ticker_id)
    ancre, notes = await horloge_du_titre(conn, ticker_id, etat.fichier)
    derniere_cloture = derniere_cloture_publiee(ancre)
    derniere_cloture_annuelle = derniere_cloture_annuelle_publiee(ancre)

    gabarit = charger_gabarit()
    ref_vent = charger_referentiel_ventilation()

    # ── Le socle ────────────────────────────────────────────────────────────────────────────────
    socle_piece = await socle_en_vigueur(conn, ticker_id)
    if socle_piece is not None:
        structure_socle, socle_id = socle_piece["structure"], socle_piece["id"]
    elif publier:
        try:
            publie = await assurer_socle(conn, ticker_id)
        except SocleIndisponible as e:
            raise MatiereRefusee(f"socle des comptes indisponible : {e}") from e
        structure_socle, socle_id = publie.structure, publie.entry_id
    else:
        try:
            faits = await fetch_company_facts(emetteur.cik)
        except (EdgarUnavailable, EdgarFeedUnavailable) as e:
            raise MatiereRefusee(f"socle des comptes non calculable à blanc : {e}") from e
        socle = reconstituer(faits, gabarit, reclassements=charger_reclassements(emetteur.cik, gabarit))
        if not socle.periodes:
            raise MatiereRefusee(f"socle des comptes : {'; '.join(socle.refus) or 'aucune période'}")
        structure_socle, socle_id = structure_du_socle(socle), None

    socle_texte = rendre_socle(structure_socle, gabarit, raison_sociale=emetteur.raison_sociale)
    if socle_id is None:
        socle_texte += "\n(pièce non encore publiée — comptes calculés à blanc, pas écrits.)"

    # ── La ventilation ──────────────────────────────────────────────────────────────────────────
    vent_piece = await ventilation_en_vigueur(conn, ticker_id)
    if vent_piece is not None:
        structure_vent, vent_id = vent_piece["structure"], vent_piece["id"]
    elif publier:
        try:
            publie_v = await assurer_ventilation(conn, ticker_id)
        except VentilationIndisponible as e:
            raise MatiereRefusee(f"ventilation publiée indisponible : {e}") from e
        structure_vent, vent_id = publie_v.structure, publie_v.entry_id
    else:
        try:
            depots = await lire_depots(emetteur.cik)
        except VentilationIndisponible as e:
            raise MatiereRefusee(f"ventilation non relevable à blanc : {e}") from e
        v = relever(depots, gabarit, ref_vent, structure_socle)
        structure_vent = structure_de_ventilation(
            v, version_referentiel=ref_vent.version, version_gabarit=gabarit.version,
            depots=tuple(depots))
        vent_id = None

    statut_vent = structure_vent.get("statut")
    ventilation_structure_pour_s = None
    if statut_vent in ("secteur_unique", "sans_ventilation"):
        ventilation_texte = (
            f"L'émetteur ne publie qu'un secteur : tous les blocs seront estimés et se raccordent à "
            f"une ligne des comptes (statut `{statut_vent}`).")
    else:
        ventilation_structure_pour_s = structure_vent
        ventilation_texte = rendre_ventilation(
            structure_vent, raison_sociale=emetteur.raison_sociale, avec_identifiants=True)
        if vent_id is None:
            ventilation_texte += "\n(pièce non encore publiée — ventilation relevée à blanc, pas écrite.)"

    # ── Les périodes du classeur ────────────────────────────────────────────────────────────────
    horizon = int(etat.fichier.parametres_du_fonds["horizon_de_projection"].valeur)
    periodes = periodes_du_classeur(structure_socle, horizon)

    # ── Les fiches et le patron ─────────────────────────────────────────────────────────────────
    fiches = variables_de_la_famille(ref, nom_famille)
    patron = ref.patrons.get(etat.archetype)

    # ── La porte, et les réponses des questions sources ────────────────────────────────────────
    porte = porte_de_l_architecte(etat, ref)
    pieces_reponses: set[int] = set()
    questions_texte = []
    for eq in porte.questions:
        texte, pieces = _texte_question(eq, etat)
        questions_texte.append(texte)
        pieces_reponses |= pieces

    # ── Les notes flash depuis la dernière clôture annuelle ────────────────────────────────────
    notes_retenues = [
        (accn, q) for accn, q in notes.items()
        if q.date_evenement is not None
        and (derniere_cloture_annuelle is None or q.date_evenement > derniere_cloture_annuelle)
    ]
    pieces_notes: set[int] = set()
    if notes_retenues:
        rows_pieces = await conn.fetch(
            "SELECT id, source_url FROM knowledge_entries WHERE ticker_id = $1 AND source_url IS NOT NULL",
            ticker_id)
        rows_pieces = [dict(r) for r in rows_pieces]
        lignes_notes = []
        for accn, q in sorted(notes_retenues, key=lambda x: x[1].date_evenement or date.min):
            piece_id = _piece_de_la_note(rows_pieces, accn)
            if piece_id is not None:
                pieces_notes.add(piece_id)
            lignes_notes.append(
                f"  · {q.date_evenement.isoformat() if q.date_evenement else '?'} — types "
                f"{sorted(q.types)} — {q.resume} — accession {accn} — pièce "
                f"{'#' + str(piece_id) if piece_id is not None else 'non identifiée'}")
        notes_flash_texte = "\n".join(lignes_notes)
    else:
        notes_flash_texte = "  (aucune note flash depuis la dernière clôture annuelle)"

    pieces_citables = frozenset(
        {p for p in (socle_id, vent_id) if p is not None} | pieces_reponses | pieces_notes)

    return Matiere(
        ticker_id=ticker_id, raison_sociale=emetteur.raison_sociale, cik=emetteur.cik,
        date_du_jour=date.today(), derniere_cloture=derniere_cloture,
        derniere_cloture_annuelle=derniere_cloture_annuelle, archetype=etat.archetype,
        classement_motif=etat.classement.motif, classement_date=etat.classement.effective_from,
        classement_declencheur=etat.classement.declencheur_accession, famille=nom_famille,
        periodes_historiques=periodes.historiques, periodes_projetees=periodes.projetees,
        lignes_business_plan=tuple(_ligne_lisible(l, gabarit) for l in famille.lignes_du_business_plan),
        fiches_texte=_fiches_texte(fiches), patron_texte=_patron_texte(patron),
        socle_texte=socle_texte, socle_piece_id=socle_id, socle_structure=structure_socle,
        ventilation_texte=ventilation_texte, ventilation_piece_id=vent_id,
        ventilation_structure=ventilation_structure_pour_s,
        questions_texte=tuple(questions_texte), notes_flash_texte=notes_flash_texte,
        pieces_citables=pieces_citables,
    )


def rendre_matiere(m: Matiere) -> str:
    """PURE, déterministe : c'est exactement ce que le modèle voit. Tri stable, aucun horodatage
    volatil (`date_du_jour` est une donnée métier — l'horloge, §3.3 point 2 — pas un horodatage de
    génération)."""
    out = [
        f"=== {m.raison_sociale} (CIK {m.cik}, ticker {m.ticker_id}) ===",
        f"Date du jour : {m.date_du_jour.isoformat()}. Dernière clôture publiée : "
        f"{m.derniere_cloture.isoformat() if m.derniere_cloture else 'inconnue'}. "
        f"Dernière clôture annuelle : "
        f"{m.derniere_cloture_annuelle.isoformat() if m.derniere_cloture_annuelle else 'inconnue'}.",
        f"Classement en vigueur : archétype `{m.archetype}` (famille `{m.famille}`) depuis "
        f"{m.classement_date.isoformat()} — {m.classement_motif}"
        + (f" (déclenché par le dépôt {m.classement_declencheur})" if m.classement_declencheur else ""),
        "",
        f"Périodes du classeur — historiques : {', '.join(m.periodes_historiques)} ; "
        f"projetées : {', '.join(m.periodes_projetees)}.",
        "",
        "Lignes du business plan (format agrégé) :",
        "\n".join(f"  · {l}" for l in m.lignes_business_plan) or "  (aucune)",
        "",
        "Fiches du catalogue de la famille :",
        m.fiches_texte,
        "",
        "Patron de départ de l'archétype (suggestion) :",
        m.patron_texte,
        "",
        "Comptes reconstitués :",
        m.socle_texte,
        "",
        "Ventilation publiée :",
        m.ventilation_texte,
        "",
        "Réponses des questions sources (ordre de la porte) :",
    ]
    out.extend(m.questions_texte)
    out.append("")
    out.append("Notes flash depuis la dernière clôture annuelle :")
    out.append(m.notes_flash_texte)
    return "\n".join(out)
