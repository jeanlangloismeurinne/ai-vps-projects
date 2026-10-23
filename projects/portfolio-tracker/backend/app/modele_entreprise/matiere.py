"""La MATIÈRE DE L'ARCHITECTE — lot M3, roadmap V3 `12-lot-M3-architecte.md` §3.3.

`charger_matiere(conn, ticker_id, *, publier)` est la SEULE moitié qui lit (et, avec `publier=True`,
publie la ventilation/le socle s'ils manquent) ; `rendre_matiere(m)` est PURE et déterministe — c'est
exactement ce que le modèle voit. Toute la matière est assemblée en texte à la LECTURE (`charger_matiere`),
jamais recalculée dans le rendu, qui ne fait qu'assembler des blocs déjà déterministes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

__all__ = ["MatiereRefusee", "Matiere", "charger_matiere", "rendre_matiere"]

# Un numéro de RÉPONSE change de forme dans la matière (`réponse R-1367`, jamais `#`) pour qu'aucun
# numéro de réponse ne ressemble à un numéro de PIÈCE (lot M3 ter, §2) — un numéro de pièce reste
# `#NNN`, jamais préfixé par le mot « réponse ».
_RE_REPONSE_DIESE = re.compile(r"réponse #(\d+)")


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
    # La VUE SERVIE de la ventilation (`perimetre.vue_servie` : série dans le découpage de référence,
    # découpage antérieur, chroniques, raccords) — `None` si `secteur_unique`/`sans_ventilation` :
    # [S1]-[S3b] de `structure.py` la lisent, le RENDU texte ne leur suffit pas (hiérarchie, régimes).
    ventilation_structure: Optional[dict]
    questions_texte: tuple[str, ...]          # une section par question, dans l'ordre de la porte
    notes_flash_texte: str
    pieces_citables: frozenset[int] = field(default_factory=frozenset)
    # Le rendu texte de `pieces_citables`, triée, avec titre — même liste que [S6] contrôle (un
    # seul détenteur, lot M3 ter §2). Précalculé ici (lecture) : `rendre_matiere` reste pur.
    pieces_citables_texte: str = ""
    # Le verbatim et le chiffre clé `nombre_de_programmes` de LA réponse retenue de `me_7` — lot
    # M3 ter §4 ([S14]/[S15]) : comparaison sur le TEXTE du dossier, jamais sur une liste écrite
    # dans le code. `None` si `me_7` n'a aucune réponse retenue, ou pas ce chiffre établi.
    me_7_verbatim: Optional[str] = None
    me_7_nombre_de_programmes: Optional[float] = None
    # #143 / diagnostic du 2026-10-23 — le second chiffre clé de `me_7` : ceux que l'émetteur compte
    # sans les nommer. Avec lui, [S15] exige un décompte EXACT ; sans lui, l'écart n'est qu'un signal.
    me_7_nombre_non_nommes: Optional[float] = None


def _ligne_lisible(ligne_id: str, gabarit) -> str:
    l = gabarit.lignes.get(ligne_id)
    return f"{ligne_id} ({l.libelle})" if l is not None else ligne_id


def _titre_court(titre: Optional[str]) -> str:
    """Titre tronqué à 120 caractères (lot M3 ter, §2) — `(sans titre)` si absent."""
    if not titre:
        return "(sans titre)"
    return titre if len(titre) <= 120 else titre[:120] + "…"


def _regle_periode(v) -> str:
    """Lot M3 ter, §5 : ce que le modèle doit faire de la période, dit au pied de CHAQUE fiche —
    pas seulement dans le `[P4]` de renvoi, trop tard et trop loin du catalogue (une valeur reprise
    d'un encadré pluriannuel unique est souvent lue, à tort, comme `sans_periode`)."""
    if v.periode == "sans_periode":
        return "une seule cellule, sans période."
    return ("une cellule par période listée (historiques et/ou projetées) ; une valeur reprise "
           "d'un encadré (chiffre unique) s'applique à CHAQUE exercice projeté.")


def _fiches_texte(fiches) -> str:
    out = []
    for v in fiches:
        somme = f" — somme_vers_ligne: {v.somme_vers_ligne}" if v.somme_vers_ligne else ""
        out.append(
            f"  · {v.id} ({v.libelle}) — unité {v.unite}, période {v.periode} ; origines admises "
            f"{v.origines_admises} ; questions sources {v.questions_sources}{somme}\n"
            f"    {v.definition}\n"
            f"    période attendue : {_regle_periode(v)}")
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


def _rendre_pieces(pieces: frozenset[int], piece_meta: dict[int, dict]) -> str:
    """`pièces : #867 (titre, date du fait) ; …` (lot M3 ter, §2) — même SET que `pieces_citables`
    y verse ; `date_du_fait` fait foi, `source_date` à défaut (#48)."""
    if not pieces:
        return ""
    morceaux = []
    for pid in sorted(pieces):
        meta = piece_meta.get(pid)
        if meta is None:
            morceaux.append(f"#{pid} (pièce publiée à l'écriture — non disponible à blanc)")
            continue
        dt = meta.get("date_du_fait") or meta.get("source_date")
        morceaux.append(f"#{pid} ({_titre_court(meta.get('title'))}, {dt.isoformat() if dt else '?'})")
    return "pièces : " + " ; ".join(morceaux)


def _texte_question(eq, etat, piece_meta: dict[int, dict]) -> tuple[str, frozenset[int], Optional[str], Optional[float], Optional[float]]:
    """Le bloc d'une question source. Rend `(texte, pieces_citées, verbatim, nombre_de_programmes,
    nombre_de_programmes_non_nommes)` — les trois derniers champs ne sont renseignés (non `None`) que pour `me_7` (lot M3 ter, §4 :
    [S14]/[S15] comparent au TEXTE du dossier, jamais à une liste écrite dans le code)."""
    reps = [r for r in etat.reponses
            if r.servie.framework_id == eq.framework_id and r.servie.question_id == eq.question_id]
    entete = f"— Question {eq.question_id} ({eq.framework_id}) — porte : " \
             f"{'ouvre' if eq.ouvre else 'ferme'} — {eq.raison}"
    r = _reponse_retenue(reps)
    if r is None:
        texte = _RE_REPONSE_DIESE.sub(r"réponse R-\1", f"{entete}\n  (aucune réponse instruite)")
        return texte, frozenset(), None, None, None

    lignes = [entete,
              f"  statut {r.servie.statut} ; écrite le "
              f"{r.cree_le.date().isoformat() if r.cree_le else '?'} ; verdict {r.verdict or '?'}"]
    if r.motif_revue:
        lignes.append(f"  motif du contrôle : {r.motif_revue}")
    pieces: set[int] = set()
    # Lot M3 ter, §6 (péremption au pied du verbatim) : LU dans la même source que la ligne de
    # porte (`fondation.actualite`/`motif_actualite`, posés par `etat_actualite_entry`) — pas de
    # second calcul. Posé AVANT le verbatim, pour qu'on ne le lise jamais sans cet avertissement.
    avertissement: Optional[str] = None
    if r.servie.fondation is not None:
        pieces |= set(r.servie.fondation.cited_entry_ids)
        if r.servie.fondation.actualite != "courante":
            avertissement = r.servie.fondation.motif_actualite
        else:
            lignes.append(f"  actualité {r.servie.fondation.actualite} — {r.servie.fondation.motif_actualite}")
    verbatim_texte: Optional[str] = None
    nombre_de_programmes: Optional[float] = None
    non_nommes: Optional[float] = None
    if r.servie.reponse is not None:
        verbatim_texte = r.servie.reponse.verbatim
        effets = [fp.effet for fp in r.servie.reponse.faits_posterieurs]
        if avertissement is not None:
            lignes.append(f"  ⚠ écrite avant un fait plus récent : {avertissement}"
                         + (f" ; le fait postérieur dit : {' ; '.join(effets)}" if effets else ""))
        lignes.append(f"  verbatim : {verbatim_texte}")
        for ligne_chiffre in r.servie.reponse.encadre_lisible():
            lignes.append(f"    chiffre : {ligne_chiffre}")
        if r.servie.reponse.sens:
            lignes.append(f"  sens : {r.servie.reponse.sens}")
        for fp in r.servie.reponse.faits_posterieurs:
            pieces |= set(fp.cited_entry_ids)
        nombre_de_programmes = next(
            (c.valeur for c in r.servie.reponse.chiffres_cles if c.id == "nombre_de_programmes"), None)
        non_nommes = next(
            (c.valeur for c in r.servie.reponse.chiffres_cles
             if c.id == "nombre_de_programmes_non_nommes"), None)
    elif avertissement is not None:
        lignes.append(f"  ⚠ écrite avant un fait plus récent : {avertissement}")
    pieces_frozen = frozenset(pieces)
    ligne_pieces = _rendre_pieces(pieces_frozen, piece_meta)
    if ligne_pieces:
        lignes.append(f"  {ligne_pieces}")
    texte = _RE_REPONSE_DIESE.sub(r"réponse R-\1", "\n".join(lignes))
    return texte, pieces_frozen, verbatim_texte, nombre_de_programmes, non_nommes


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
    from app.knowledge.perimetre import est_structure_courante, vue_servie
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
    # Une pièce publiée avant le lot P1 (cellules fusionnées, cumuls des seuls membres « nouveaux »)
    # ne porte pas la forme que lit la vue servie : elle se relève (à blanc) ou se republie
    # (`publier`), jamais servie amputée.
    if vent_piece is not None and not est_structure_courante(vent_piece["structure"]):
        vent_piece = None
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
            depots = await lire_depots(emetteur.cik, referentiel=ref_vent)
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
        ventilation_structure_pour_s = vue_servie(structure_vent, structure_socle)
        ventilation_texte = rendre_ventilation(
            ventilation_structure_pour_s, raison_sociale=emetteur.raison_sociale, avec_identifiants=True)
        if vent_id is None:
            ventilation_texte += "\n(pièce non encore publiée — ventilation relevée à blanc, pas écrite.)"

    # ── Les périodes du classeur ────────────────────────────────────────────────────────────────
    horizon = int(etat.fichier.parametres_du_fonds["horizon_de_projection"].valeur)
    periodes = periodes_du_classeur(structure_socle, horizon)

    # ── Les fiches et le patron ─────────────────────────────────────────────────────────────────
    fiches = variables_de_la_famille(ref, nom_famille)
    patron = ref.patrons.get(etat.archetype)

    # ── La porte, et les réponses des questions sources ────────────────────────────────────────
    # Métadonnées (titre, dates) de TOUTE pièce du dossier — pour le rendu « pièces : #N (titre,
    # date) » sous chaque réponse (§2) et pour `_piece_de_la_note` ci-dessous (mêmes lignes, plus
    # besoin d'une seconde requête). Un seul aller-retour, qu'il y ait ou non des notes flash.
    piece_rows = await conn.fetch(
        "SELECT id, title, source_url, date_du_fait, source_date FROM knowledge_entries "
        "WHERE ticker_id = $1", ticker_id)
    piece_meta: dict[int, dict] = {r["id"]: dict(r) for r in piece_rows}

    porte = porte_de_l_architecte(etat, ref)
    pieces_reponses: set[int] = set()
    questions_texte = []
    me_7_verbatim: Optional[str] = None
    me_7_nombre_de_programmes: Optional[float] = None
    me_7_nombre_non_nommes: Optional[float] = None
    for eq in porte.questions:
        texte, pieces, verbatim, n_prog, n_non_nommes = _texte_question(eq, etat, piece_meta)
        questions_texte.append(texte)
        pieces_reponses |= pieces
        if eq.question_id == "me_7":
            me_7_verbatim = verbatim
            me_7_nombre_de_programmes = n_prog
            me_7_nombre_non_nommes = n_non_nommes

    # ── Les notes flash depuis la dernière clôture annuelle ────────────────────────────────────
    notes_retenues = [
        (accn, q) for accn, q in notes.items()
        if q.date_evenement is not None
        and (derniere_cloture_annuelle is None or q.date_evenement > derniere_cloture_annuelle)
    ]
    pieces_notes: set[int] = set()
    if notes_retenues:
        rows_pieces = list(piece_meta.values())
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

    # Section finale « Pièces que tu peux citer » (§2) — la liste EXACTE de `pieces_citables`,
    # triée, avec titre : même liste que [S6] contrôle, un seul détenteur (`Matiere.pieces_citables`).
    if pieces_citables:
        pieces_citables_texte = "\n".join(
            f"  · #{pid} — {_titre_court((piece_meta.get(pid) or {}).get('title'))}"
            for pid in sorted(pieces_citables))
    else:
        pieces_citables_texte = "  (aucune pièce citable à blanc)"

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
        pieces_citables=pieces_citables, pieces_citables_texte=pieces_citables_texte,
        me_7_verbatim=me_7_verbatim, me_7_nombre_de_programmes=me_7_nombre_de_programmes,
        me_7_nombre_non_nommes=me_7_nombre_non_nommes,
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
    out.append("")
    out.append("Pièces que tu peux citer (cite UNIQUEMENT ces numéros, jamais un numéro de réponse) :")
    out.append(m.pieces_citables_texte)
    return "\n".join(out)
