"""Le cœur de la base de connaissance — l'intérieur du module (rien d'ici ne s'importe du dehors :
`contrat.py`).

Il met en lecture les documents que la collecte a rangés (le lecteur, sans modèle), établit les
pièces (vérification mot pour mot, détenteur unique `citation.py`), retrouve des passages par les
mots, et redemande à M1, à chaque lecture, ce que vaut la source de chaque pièce. Il ne connaît aucun
formulaire, aucun registre, aucune société.

Aucune horloge : la date est donnée par l'appelant.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from app.modules.chef_de_dossier.contrat import EN_COURS, FAIT, INDISPONIBLE, Contexte, Pas, Resultat
from app.modules.emetteurs import contrat as E
from app.modules.recueil import contrat as R

from . import citation as C
from . import lecteur as L
from .contrat import (
    NOM_DU_MODULE,
    Connaissance,
    Depot,
    Lecture,
    Passage,
    Piece,
    PieceLue,
    PieceRefusee,
    Valeur,
    VueLecture,
)


@lru_cache(maxsize=1)
def referentiel() -> Mapping[str, Any]:
    ref = json.loads(Path(__file__).with_name("referentiel.json").read_text(encoding="utf-8"))
    defauts = []
    lec = ref["lecteur"]
    for cle in ("formats_html", "formats_texte", "formats_sans_objet"):
        if set(lec[cle]) & {f for k in ("formats_html", "formats_texte", "formats_sans_objet")
                            if k != cle for f in lec[k]}:
            defauts.append(f"un format est rangé dans deux familles ({cle})")
    if set(lec["muets"]) & set(lec["blocs"]):
        defauts.append("un élément est à la fois muet et bloc")
    for raison in ("vide", "format_non_lu", "sans_objet"):
        if raison not in ref["raisons"]:
            defauts.append(f"raison « {raison} » sans libellé")
    if defauts:
        raise ValueError("référentiel de la base de connaissance incohérent : " + " ; ".join(defauts))
    return ref


def version_du_lecteur() -> str:
    return referentiel()["lecteur"]["version"]


# ── Ce que la collecte a rangé ───────────────────────────────────────────────────────────────

async def _documents_collectes(recueil_depot: Any, emetteur: str) -> list[R.Document]:
    """Les documents de la dernière réponse à chaque demande, une fois chacun, dans un ordre stable."""
    recueil = await R.lire_recueil(recueil_depot, emetteur)
    vus: dict[str, R.Document] = {}
    for rep in recueil.reponses:
        for d in rep.documents:
            vus.setdefault(d.empreinte, d)
    return [vus[k] for k in sorted(vus)]


async def _lectures_courantes(depot: Depot, emetteur: str) -> dict[str, Mapping[str, Any]]:
    v = version_du_lecteur()
    return {l["empreinte"]: l for l in await depot.lectures(emetteur) if l["lecteur"] == v}


# ── La tâche de fond : mettre en lecture ─────────────────────────────────────────────────────

async def lire_documents(depot: Depot, *, recueil_depot: Any, emetteur: str, le: str) -> list[dict[str, Any]]:
    deja = await _lectures_courantes(depot, emetteur)
    regles = referentiel()["lecteur"]
    lignes_rendues = []
    for d in await _documents_collectes(recueil_depot, emetteur):
        if d.empreinte in deja:
            continue
        contenu = await R.lire_contenu(recueil_depot, d.empreinte)
        texte = L.lire(contenu, d.type_media, regles)
        lecture = Lecture(
            empreinte=d.empreinte, emetteur=emetteur, genre=d.genre, lecteur=regles["version"],
            statut=texte.statut, nb_lignes=len(texte.lignes), raison=texte.raison, detail=texte.detail,
            adresse=d.provenance.adresse, publie_le=d.provenance.publie_le, faits_au=d.provenance.faits_au,
            lue_le=le)
        await depot.ranger_lecture(asdict(lecture), texte.lignes)
        lignes_rendues.append({"empreinte": d.empreinte, "statut": texte.statut, "lignes": len(texte.lignes),
                               "raison": texte.raison})
    return lignes_rendues


# ── Citer ────────────────────────────────────────────────────────────────────────────────────

def _identifiant(empreinte: str, lecteur: str, debut: int, fin: int, extrait: str, periode: str) -> str:
    cle = "|".join((empreinte, lecteur, str(debut), str(fin), C.normaliser(extrait), periode.strip()))
    return hashlib.sha256(cle.encode("utf-8")).hexdigest()


async def citer(depot: Depot, *, emetteur: str, empreinte: str, extrait: str, auteur: str, le: str,
                periode: str = "") -> Piece:
    if not auteur.strip():
        raise PieceRefusee("une pièce nomme celui qui la cite")
    lecture = (await _lectures_courantes(depot, emetteur)).get(empreinte)
    if lecture is None:
        raise PieceRefusee(f"document {empreinte} : inconnu pour {emetteur}, ou pas encore mis en lecture — "
                           "rien n'entre sans document d'origine")
    if lecture["statut"] != L.LUE:
        raise PieceRefusee(f"document {empreinte} : lecture {lecture['statut']} ({lecture['raison']}) — "
                           "aucune pièce ne peut en être tirée")
    lignes = await depot.lignes(empreinte, lecture["lecteur"])
    texte = "\n".join(lignes)
    etablis, motif = C.etablir_extraits([extrait], [texte])
    if motif:
        raise PieceRefusee(motif)
    t1, positions = C.localiser(etablis[0], texte)
    if not positions:
        raise PieceRefusee(f"extrait établi mais introuvable à sa place : {etablis[0][:160]!r}")
    debut, fin = positions[0]
    ligne_debut = t1.count("\n", 0, debut) + 1
    ligne_fin = t1.count("\n", 0, fin) + 1
    texte_du_document = t1[debut:fin]
    piece = Piece(
        identifiant=_identifiant(empreinte, lecture["lecteur"], ligne_debut, ligne_fin, texte_du_document, periode),
        emetteur=emetteur, empreinte=empreinte, lecteur=lecture["lecteur"], ligne_debut=ligne_debut,
        ligne_fin=ligne_fin, extrait=texte_du_document, auteur=auteur, periode=periode.strip(), cite_le=le,
        genre=lecture["genre"], adresse=lecture["adresse"], publie_le=lecture["publie_le"],
        faits_au=lecture["faits_au"],
        autres_lignes=tuple(sorted({t1.count("\n", 0, d) + 1 for d, _ in positions[1:]} - {ligne_debut})))
    if not await depot.ranger_piece(asdict(piece)):
        for p in await depot.pieces(emetteur):
            if p["identifiant"] == piece.identifiant:
                return _piece(p)
    return piece


def _piece(p: Mapping[str, Any]) -> Piece:
    return Piece(**{**p, "autres_lignes": tuple(p.get("autres_lignes") or ())})


# ── Ce que vaut une pièce, au jour de la lecture ─────────────────────────────────────────────

def _valeur(fiche: E.Fiche | None, piece: Piece, natures: Mapping[str, str]) -> Valeur:
    if fiche is None:
        return Valeur(admise=False, niveau="", motif="aucune fiche établie pour cet émetteur : la source "
                                                      "ne peut pas être qualifiée")
    nature = natures.get(piece.genre)
    if nature is None:
        return Valeur(admise=False, niveau="", motif=f"genre de document inconnu de la collecte : {piece.genre}")
    q = E.qualifier(fiche, piece.adresse, nature)
    signal = E.pieces_a_signaler(fiche, [E.Origine(piece=piece.identifiant, adresse=piece.adresse, nature=nature)])
    if signal:
        s = signal[0]
        return Valeur(admise=q.admise, niveau=q.niveau, motif=q.motif, source=s.source,
                      revoquee_le=s.revoquee_le, motif_revocation=s.motif)
    return Valeur(admise=q.admise, niveau=q.niveau, motif=q.motif, source=q.source)


async def lire_connaissance(depot: Depot, *, recueil_depot: Any, emetteurs_depot: Any,
                            emetteur: str) -> Connaissance:
    courantes = await _lectures_courantes(depot, emetteur)
    collectes = await _documents_collectes(recueil_depot, emetteur)
    try:
        fiche: E.Fiche | None = await E.lire_fiche(emetteurs_depot, emetteur)
    except E.FicheAbsente:
        fiche = None
    natures = {nom: g["nature"] for nom, g in R.genres().items()}
    pieces = sorted((_piece(p) for p in await depot.pieces(emetteur)),
                    key=lambda p: (p.cite_le, p.empreinte, p.ligne_debut, p.identifiant))
    return Connaissance(
        emetteur=emetteur,
        lectures=tuple(Lecture(**courantes[k]) for k in sorted(courantes)),
        a_lire=tuple(d.empreinte for d in collectes if d.empreinte not in courantes),
        pieces=tuple(PieceLue(p, _valeur(fiche, p, natures)) for p in pieces))


# ── Chercher par les mots ────────────────────────────────────────────────────────────────────

async def chercher(depot: Depot, *, emetteur: str, mots: str, genre: str = "") -> list[Passage]:
    demandes = C.normaliser(mots).split()
    if not demandes:
        return []
    trouves: list[Passage] = []
    for lec in (await _lectures_courantes(depot, emetteur)).values():
        if lec["statut"] != L.LUE or (genre and lec["genre"] != genre):
            continue
        for i, ligne in enumerate(await depot.lignes(lec["empreinte"], lec["lecteur"]), start=1):
            n = C.normaliser(ligne)
            if all(m in n for m in demandes):
                trouves.append(Passage(empreinte=lec["empreinte"], ligne=i, texte=ligne, genre=lec["genre"],
                                       adresse=lec["adresse"], publie_le=lec["publie_le"],
                                       occurrences=sum(n.count(m) for m in demandes)))
    trouves.sort(key=lambda p: (-p.occurrences, _inverse(p.publie_le), p.empreinte, p.ligne))
    return trouves[:referentiel()["recherche"]["resultats_max"]]


def _inverse(date_iso: str) -> tuple[int, ...]:
    """Clef de tri « la plus récente d'abord » ; une date absente passe après toutes les autres."""
    if not date_iso:
        return (1,)
    return (0,) + tuple(-int(x) for x in date_iso.split("-"))


# ── L'écran ──────────────────────────────────────────────────────────────────────────────────

async def vue_ecran(depot: Depot, *, recueil_depot: Any, emetteurs_depot: Any, emetteur: str) -> dict[str, Any]:
    c = await lire_connaissance(depot, recueil_depot=recueil_depot, emetteurs_depot=emetteurs_depot,
                                emetteur=emetteur)
    return {
        "version_contrat": c.version_contrat,
        "emetteur": emetteur,
        "lecteur": version_du_lecteur(),
        "lectures": [asdict(l) for l in c.lectures],
        "a_lire": list(c.a_lire),
        "pieces": [{**asdict(p.piece), "valeur": asdict(p.valeur)} for p in c.pieces],
        "raisons": dict(referentiel()["raisons"]),
    }


# ── Le pas du chef de dossier ────────────────────────────────────────────────────────────────

async def vue_lecture(depot: Depot, *, recueil_depot: Any, emetteur: str) -> VueLecture:
    collectes = await _documents_collectes(recueil_depot, emetteur)
    courantes = await _lectures_courantes(depot, emetteur)
    return VueLecture(documents=tuple(d.empreinte for d in collectes),
                      lus=frozenset(k for k in courantes))


def pas_lecture(nom: str, vue: VueLecture, *, apres: tuple[str, ...]) -> Pas:
    if not apres:
        raise ValueError("le pas de lecture vient après la collecte qu'il lit")

    def suivre(ctx: Contexte) -> Resultat:
        if not vue.documents:
            return Resultat(issue=INDISPONIBLE, motif="aucun document collecté à mettre en lecture")
        restants = [e for e in vue.documents if e not in vue.lus]
        if restants:
            return Resultat(issue=EN_COURS, motif=f"lecture : {len(vue.documents) - len(restants)}/"
                                                  f"{len(vue.documents)} documents lus")
        return Resultat(issue=FAIT)

    return Pas(nom=nom, module=NOM_DU_MODULE, apres=tuple(apres), executer=suivre, suivre=suivre,
               cout_estime_usd=0.0)
