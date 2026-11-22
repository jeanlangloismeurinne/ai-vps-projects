"""K13 — contrôle de la base de connaissance (M3) par l'ancien système. LECTURE SEULE : rien n'est
écrit en base (les pièces d'essai sont établies dans un dépôt EN MÉMOIRE, par le même geste `citer`
que la production).

Les fiches de l'ancien système « à extraits littéraux vérifiés » (#126) qui citent un dépôt SEC ont
été vérifiées mot pour mot, à l'époque, contre le texte que le collecteur avait récupéré. On rejoue
chacun de leurs extraits contre la LECTURE que M3 a faite du même dépôt recollecté par M2 : un extrait
que `citer` refuserait aujourd'hui est un écart, listé avec son motif.

Classement de chaque fiche :
  · retrouvée            — tous ses extraits deviennent des pièces (lignes indiquées) ;
  · écart expliqué       — un extrait refusé par `citer`, pour une différence de lecture connue (cellules
                           de tableau que l'ancien lecteur collait, #132) : le même texte est cité à sa ligne ;
  · écart de lecture     — le dépôt est lu, au moins un extrait est refusé sans explication (motif de `citer`) ;
  · dépôt non recollecté — M2 ne l'a pas demandé (initialiser un dossier = le dernier rapport annuel,
                           M3 §4 question 2) ; avec `--en-memoire`, le document est relu ici, gratuitement,
                           par le même lecteur, et ses extraits rejoués de la même façon ;
  · autre société        — le dépôt est au registre sous un autre numéro que celui de la fiche de
                           l'émetteur (#87 : la pièce n'aurait pas dû entrer à son dossier).

    bash tools/controle_ancien_systeme.sh [EMETTEUR …] [--en-memoire] [--detail]

Le verdict est en dernière ligne, sous une forme fixe (« K13 : … ») ; un écart inexpliqué (ou aucune
fiche lue) fait sortir en code 1.
"""
from __future__ import annotations

import asyncio
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncpg  # noqa: E402

from app.modules.connaissance import contrat as C  # noqa: E402
from app.modules.emetteurs import contrat as E  # noqa: E402
from app.modules.recueil import contrat as R  # noqa: E402

PREFIXE_FICHE = "Extraits littéraux du document"  # celui de l'ancien worker (standard_collecte.PREFIXE_FICHE)
_EXTRAIT = re.compile(r"«\s*(.*?)\s*»", re.S)
# Une adresse d'archive du registre : /Archives/edgar/data/<numéro de l'émetteur>/<numéro du dépôt>/<fichier>
_ARCHIVE = re.compile(r"sec\.gov/Archives/edgar/data/(\d+)/(\d{18})/([^/?#]+)", re.I)
AUTEUR = "contrôle K13 (ancien système)"

RETROUVEE, ECART, ECART_EXPLIQUE = "retrouvée", "écart de lecture", "écart expliqué"
NON_RECOLLECTE, AUTRE_SOCIETE = "dépôt non recollecté", "autre société"


@dataclass
class Verdict:
    fiche: int
    emetteur: str
    adresse: str
    statut: str
    lu_en: str = ""          # « collecte » (lecture rangée par M3) ou « mémoire » (relu ici)
    meme_fichier: bool = True
    lignes: list[str] = field(default_factory=list)
    motif: str = ""


def extraits_de(contenu: str) -> list[str]:
    """Les extraits d'une fiche de l'ancien worker : le texte entre guillemets français, après l'en-tête."""
    corps = contenu.split(":", 1)[1] if contenu.startswith(PREFIXE_FICHE) and ":" in contenu else contenu
    return [e for e in _EXTRAIT.findall(corps) if e.strip()]


def _numero_registre(fiche: E.Fiche) -> str:
    for r in getattr(fiche, "references", ()):
        if r.registre.upper() in {"CIK", "SEC", "SEC_CIK"} or "CIK" in r.registre.upper():
            return r.valeur.lstrip("0")
    return ""


def _colle(texte: str) -> str:
    return re.sub(r"\s+", "", C.normaliser(texte))


def _diagnostic(extrait: str, lignes: tuple[str, ...]) -> str:
    """Pourquoi un extrait introuvable l'est, quand la cause est une différence de LECTURE connue :
    l'ancien lecteur collait les cellules d'un tableau (« Revenue$215,938$130,497 »), et un paragraphe
    au tableau qui le suit ; M3 sépare les cellules (#132) et met chaque bloc sur sa ligne. Le même
    texte, blancs ôtés des deux côtés, sur une ligne ou des lignes CONSÉCUTIVES de la lecture ⟹ écart
    expliqué, lignes citées — sauf si l'une de ces lignes n'a aucune lettre : une cellule seule sur sa
    ligne est un défaut du lecteur de M3, que ce contrôle doit faire rougir. Ce diagnostic n'établit aucune pièce : `citer` reste seul juge."""
    cible = _colle(extrait)
    if len(cible) < 12:
        return ""
    colles = [_colle(l) for l in lignes]
    debuts, pos = [], 0
    for c in colles:
        debuts.append(pos)
        pos += len(c)
    k = "".join(colles).find(cible)
    if k < 0:
        return ""
    i = max(j for j, d in enumerate(debuts) if d <= k)
    f = max(j for j, d in enumerate(debuts) if d < k + len(cible))
    isolees = [lignes[j] for j in range(i, f + 1) if not any(ch.isalpha() for ch in lignes[j])]
    if i != f and isolees:
        # Une ligne sans lettre au milieu du passage : une cellule détachée de sa rangée. C'est un défaut
        # du lecteur de M3 (une rangée de tableau doit se citer en une ligne, #132), jamais une excuse.
        return ""
    if i == f:
        return f"cellules de tableau collées par l'ancien lecteur ; M3 les lit en colonnes, ligne {i + 1} : {lignes[i][:120]!r}"
    return (f"blocs collés par l'ancien lecteur ; M3 met chacun sur sa ligne, lignes {i + 1}-{f + 1} : "
            f"{' ⏎ '.join(lignes[i:f + 1])[:160]!r}")


async def _rejouer(emetteur: str, lecture: dict, lignes: tuple[str, ...], extraits: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Chaque extrait rejoué par `citer` dans un dépôt en mémoire qui ne contient que cette lecture.
    Rend (lignes des pièces établies, écarts expliqués, écarts inexpliqués)."""
    memo = C.DepotMemoire()
    await memo.ranger_lecture({**lecture, "emetteur": emetteur}, lignes)
    lieux, expliques, inexpliques = [], [], []
    for e in extraits:
        try:
            p = await C.citer(memo, emetteur=emetteur, empreinte=lecture["empreinte"], extrait=e,
                              auteur=AUTEUR, le=date.today().isoformat())
        except C.PieceRefusee as exc:
            diag = _diagnostic(e, lignes) if "introuvable dans le texte" in str(exc) else ""
            (expliques if diag else inexpliques).append(f"{exc}" + (f" — {diag}" if diag else ""))
            continue
        lieux.append(f"{p.ligne_debut}" + (f"-{p.ligne_fin}" if p.ligne_fin != p.ligne_debut else ""))
    return lieux, expliques, inexpliques


def _classer(v: "Verdict", lieux: list[str], expliques: list[str], inexpliques: list[str]) -> None:
    v.lignes = lieux
    v.motif = " | ".join(inexpliques + expliques)
    v.statut = ECART if inexpliques else ECART_EXPLIQUE if expliques else RETROUVEE


def _version_courante() -> str:
    from app.modules.connaissance import coeur
    return coeur.version_du_lecteur()


async def _lire_en_memoire(adresse: str) -> tuple[dict | None, tuple[str, ...], str]:
    """Le document relu ici, par le transport de production ; rien n'est rangé."""
    from app.modules.recueil.adaptateurs.transport import TransportReel
    global _TRANSPORT
    _TRANSPORT = _TRANSPORT or TransportReel()
    lu = await _TRANSPORT.lire(adresse)
    if lu.statut != 200 or not lu.contenu:
        return None, (), f"lecture réseau impossible (statut {lu.statut})"
    return await _lire_octets(lu.contenu, lu.type_media, adresse)


async def _lire_octets(contenu: bytes, type_media: str, adresse: str) -> tuple[dict | None, tuple[str, ...], str]:
    """Des octets lus par le lecteur COURANT de production, en mémoire ; rien n'est rangé."""
    from app.modules.connaissance import coeur, lecteur as L
    regles = coeur.referentiel()["lecteur"]
    texte = await asyncio.to_thread(L.lire, contenu, type_media, regles)
    if texte.statut != C.LUE:
        return None, (), f"lecture {texte.statut} ({texte.raison} {texte.detail})".strip()
    lecture = {"empreinte": f"memoire:{adresse}", "lecteur": regles["version"], "statut": C.LUE,
               "raison": "", "detail": "", "genre": "", "adresse": adresse, "publie_le": "", "faits_au": "",
               "nb_lignes": len(texte.lignes), "lue_le": date.today().isoformat()}
    return lecture, texte.lignes, ""


_TRANSPORT = None
_DOCUMENTS: dict[str, dict] = {}


async def _documents(conn, emetteur: str) -> dict:
    """Les documents que la collecte a rangés pour l'émetteur, par empreinte (contrat de M2)."""
    if emetteur not in _DOCUMENTS:
        recueil = await R.lire_recueil(R.depot_base(conn), emetteur)
        _DOCUMENTS[emetteur] = {d.empreinte: d for rep in recueil.reponses for d in rep.documents}
    return _DOCUMENTS[emetteur]


async def controler(conn, emetteurs: list[str], en_memoire: bool) -> list[Verdict]:
    rows = await conn.fetch(
        "SELECT id, ticker_id, source_url, content FROM knowledge_entries "
        "WHERE content LIKE $1 AND source_url ILIKE '%sec.gov/Archives/%' "
        "AND ($2::text[] IS NULL OR ticker_id = ANY($2)) ORDER BY ticker_id, id",
        PREFIXE_FICHE + "%", emetteurs or None)
    depot = C.depot_base(conn)
    fiches = {}
    lectures_par_depot: dict[str, dict[str, list[dict]]] = {}
    verdicts = []
    for r in rows:
        em = r["ticker_id"]
        if em not in fiches:
            fiches[em] = await E.lire_fiche(E.depot_base(conn), em)
            par_depot: dict[str, list[dict]] = {}
            # La lecture la plus récente d'abord : un lecteur amélioré range la sienne à côté.
            for l in sorted(await depot.lectures(em), key=lambda x: str(x["lue_le"]), reverse=True):
                m = _ARCHIVE.search(l["adresse"] or "")
                if m and l["statut"] == C.LUE:
                    par_depot.setdefault(m.group(2), []).append(dict(l))
            lectures_par_depot[em] = par_depot
        adresse = r["source_url"]
        m = _ARCHIVE.search(adresse)
        v = Verdict(fiche=r["id"], emetteur=em, adresse=adresse, statut="")
        extraits = extraits_de(r["content"])
        cik = _numero_registre(fiches[em])
        if not extraits:
            v.statut, v.motif = ECART, "aucun extrait lisible dans la fiche"
        elif cik and m.group(1).lstrip("0") != cik:
            v.statut, v.motif = AUTRE_SOCIETE, f"dépôt du numéro {m.group(1)}, fiche de l'émetteur : {cik}"
        elif m.group(2) in lectures_par_depot[em]:
            lecture = lectures_par_depot[em][m.group(2)][0]
            v.meme_fichier = lecture["adresse"].rsplit("/", 1)[-1] == m.group(3)
            if lecture["lecteur"] == _version_courante():
                v.lu_en = "collecte"
                lignes = tuple(await C.lire_lignes(depot, lecture["empreinte"], lecture["lecteur"]))
            else:
                # Rangée par un lecteur plus ancien : le document COLLECTÉ est relu ici par le lecteur
                # courant (la tâche de fond rangera cette lecture-là à côté de l'ancienne, K2).
                v.lu_en = f"collecte, relue en {_version_courante()}"
                doc = (await _documents(conn, em))[lecture["empreinte"]]
                lecture, lignes, echec = await _lire_octets(
                    await R.lire_contenu(R.depot_base(conn), doc.empreinte), doc.type_media, lecture["adresse"])
                if lecture is None:
                    v.statut, v.motif = ECART, echec
                    verdicts.append(v)
                    continue
            _classer(v, *await _rejouer(em, lecture, lignes, extraits))
        elif en_memoire:
            lecture, lignes, echec = await _lire_en_memoire(adresse)
            v.lu_en = "mémoire"
            if lecture is None:
                v.statut, v.motif = ECART, echec
            else:
                _classer(v, *await _rejouer(em, lecture, lignes, extraits))
        else:
            v.statut, v.motif = NON_RECOLLECTE, f"dépôt {m.group(2)} ({m.group(3)}) non demandé par la collecte"
        verdicts.append(v)
    return verdicts


def imprimer(verdicts: list[Verdict], detail: bool) -> int:
    for v in verdicts:
        if detail or v.statut != RETROUVEE:
            ou = f" [{v.lu_en}{'' if v.meme_fichier else ', autre fichier du même dépôt'}]" if v.lu_en else ""
            lignes = f" lignes {', '.join(v.lignes)}" if v.lignes else ""
            print(f"#{v.fiche:<5} {v.emetteur:<6} {v.statut}{ou}{lignes} — {v.adresse.rsplit('/', 2)[-2]}/"
                  f"{v.adresse.rsplit('/', 1)[-1]}" + (f"\n        {v.motif[:700]}" if v.motif else ""))
    par = Counter((v.emetteur, v.statut) for v in verdicts)
    for (em, st), n in sorted(par.items()):
        print(f"  {em:<6} {st:<22} {n}")
    tot = Counter(v.statut for v in verdicts)
    print(f"K13 : {len(verdicts)} fiches — {tot[RETROUVEE]} retrouvées, {tot[ECART_EXPLIQUE]} écarts expliqués, "
          f"{tot[ECART]} écarts inexpliqués, {tot[NON_RECOLLECTE]} dépôts non recollectés, "
          f"{tot[AUTRE_SOCIETE]} d'une autre société")
    return 1 if tot[ECART] or not verdicts else 0


async def main(argv: list[str]) -> int:
    url = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
    if "@" not in url:
        print("DATABASE_URL absente", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(url)
    try:
        async with conn.transaction(readonly=True):
            verdicts = await controler(conn, [a for a in argv if not a.startswith("--")],
                                       "--en-memoire" in argv)
    finally:
        await conn.close()
    return imprimer(verdicts, "--detail" in argv)


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
