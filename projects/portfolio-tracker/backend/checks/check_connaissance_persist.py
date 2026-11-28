"""Le rangement EN BASE de la lecture (M3 « connaissance ») et du déclencheur (« etude ») — tables de
la migration 065 — contre une VRAIE base où 063, 064 et 065 sont appliquées. Tout se joue dans des
transactions annulées : zéro résidu. Société fictive uniquement — réutilise le monde simulé de
`checks/check_etude.py` (adaptateur, évaluateur) : aucun réseau, aucun modèle, aucune dépense.
Acceptation : `roadmap/archive/V3-M3-base-connaissance.md`, K5 et K10 « base ».

  [P0]  063, 064 et 065 appliquées ICI (sinon : échec NOMMÉ, jamais un saut) ; aucun résidu
  [P1]  le même parcours (mettre à l'étude, la tâche de fond jusqu'au bout, l'acte attendu) joué en
        mémoire et en base, TOUS les dépôts en base sur une connexion : même lecture des études, de la
        connaissance, de la collecte, même état du dossier — comparés en entier
  [P2]  un caractère nul dans un document collecté : la lecture se range en base et se retrouve
  [K5]  une pièce se range une fois (citée deux fois : une ligne) ; une autre période = une autre
        pièce ; les pièces relues en base = en mémoire
  [P3]  lectures, lignes, pièces, études, passages : la base refuse modification et suppression
  [P4]  rien n'entre sans origine, par la base elle-même : une lecture d'un document que la collecte
        n'a pas rangé, une pièce d'une lecture qui n'existe pas → refusées
  [K10] l'état du dossier et ce qu'il lance : ensemble ou pas du tout (un refus du rangement de l'état
        annule, par ROLLBACK, les demandes de collecte déjà écrites)
  [K10] deux passages simultanés (deux connexions) : le second ne fait rien ; le verrou rendu, le
        suivant avance ; une connexion morte ne laisse pas le dossier bloqué
  [P5]  même résultat que la connexion ait ou non le codec JSON du service

Lancer : `bash checks/avec_base.sh check_connaissance_persist` (VPS, une fois 065 appliquée), ou sur une
base jetable : `CHECK_DB_URL=postgresql://… python3 checks/check_connaissance_persist.py`.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _harness import Bilan, table_absente  # noqa: E402

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

b = Bilan()
_db_url = os.environ.get("CHECK_DB_URL", "")
if not _db_url or "@" not in _db_url:
    b.check(False, "§persistance non exécutée — CHECK_DB_URL absente ou factice ; l'état persisté "
                   "n'a PAS été mesuré")
    sys.exit(b.summary())

import asyncpg  # noqa: E402

from app.modules.chef_de_dossier import contrat as CD  # noqa: E402
from app.modules.connaissance import contrat as K  # noqa: E402
from app.modules.emetteurs import contrat as E  # noqa: E402
from app.modules.etude import contrat as T  # noqa: E402
from app.modules.recueil import contrat as R  # noqa: E402
import check_etude as CE  # noqa: E402 — réutilise le monde simulé (adaptateur, évaluateur, fiches)

TABLES_065 = ("connaissance_lectures", "connaissance_lignes", "connaissance_pieces",
              "etude_etudes", "etude_passages")
TABLES = ("chef_etats", "recueil_documents", "recueil_travaux") + TABLES_065
JOUR = CE.JOUR
EMETTEUR = CE.EMETTEUR

# Un caractère nul dans le rapport collecté (#P2) : le lecteur le lit « � », la base range.
CE.RAPPORT = CE.RAPPORT.replace(b"annual report.", b"annual\x00 report.")


async def _monde(conn=None, *, chef=None) -> tuple[T.Monde, CE.Simule]:
    """Le monde de `check_etude`, en mémoire (conn=None) ou TOUS les dépôts en base sur `conn`."""
    if conn is None:
        monde, simule = await CE.nouveau_monde(chef=chef)
        return monde, simule
    ed = E.depot_base(conn)
    for dossier, site in ((EMETTEUR, CE.SITE), (CE.AUTRE, CE.SITE_BIS)):
        await E.etablir_fiche(ed, dossier, raison_sociale=f"{dossier} Corp", auteur=E.UTILISATEUR,
                              motif="ouverture", le=JOUR, lieux=[("site", site)])
    simule = CE.Simule()
    monde = T.Monde(etude=T.depot_base(conn), chef=chef or CD.depot_base(conn), emetteurs=ed,
                    recueil=R.depot_base(conn), connaissance=K.depot_base(conn),
                    outils=CE.Outils([simule]), evaluateur=CE.Evaluateur(), transaction=conn.transaction)
    return monde, simule


async def _parcours(monde: T.Monde) -> list[str]:
    """Mettre à l'étude, puis la tâche de fond jusqu'au bout ; l'acte attendu est accompli."""
    await T.mettre_a_l_etude(monde, EMETTEUR, par="gerant", motif="initiation", le=JOUR)
    actes = []
    for _ in range(8):
        await T.traiter_les_dossiers(monde, le=JOUR)
        e = await CE.etat(monde)
        if e.arret and e.arret.motif == CD.ARRET_ACTE_HUMAIN:
            actes.append(e.arret.cle)
            await T.enregistrer_acte(monde, EMETTEUR, e.arret.cle, le=JOUR)
        if e.arret and e.arret.motif == CD.ARRET_PARCOURS_TERMINE:
            break
    return actes


async def _vues(monde: T.Monde) -> dict:
    return {
        # La base de production porte aussi les vraies études (NVDA dès le 2026-11-22) : on compare celle du
        # dossier fictif, jamais le registre entier.
        "etudes": [e for e in await T.lire_etudes(monde) if e.etude.dossier == EMETTEUR],
        "connaissance": await K.lire_connaissance(monde.connaissance, recueil_depot=monde.recueil,
                                                  emetteurs_depot=monde.emetteurs, emetteur=EMETTEUR),
        "ecran": await K.vue_ecran(monde.connaissance, recueil_depot=monde.recueil,
                                   emetteurs_depot=monde.emetteurs, emetteur=EMETTEUR),
        "recueil": await R.lire_recueil(monde.recueil, EMETTEUR),
        "dossier": (await CE.etat(monde)).vers_dict(),
    }


async def _citer(monde: T.Monde) -> dict:
    """Trois citations (une deux fois, une autre période) et un refus."""
    lu = next(l for l in (await K.lire_connaissance(monde.connaissance, recueil_depot=monde.recueil,
                                                    emetteurs_depot=monde.emetteurs, emetteur=EMETTEUR)).lectures
              if l.statut == K.LUE and l.adresse.startswith(f"https://{CE.SITE}/"))
    p1 = await K.citer(monde.connaissance, emetteur=EMETTEUR, empreinte=lu.empreinte,
                       extrait="Total revenue", auteur="comptes", le=JOUR, periode="exercice 2025")
    p2 = await K.citer(monde.connaissance, emetteur=EMETTEUR, empreinte=lu.empreinte,
                       extrait="Total revenue", auteur="comptes", le="2026-11-22", periode="exercice 2025")
    p3 = await K.citer(monde.connaissance, emetteur=EMETTEUR, empreinte=lu.empreinte,
                       extrait="Total revenue", auteur="comptes", le=JOUR, periode="exercice 2024")
    refus = ""
    try:
        await K.citer(monde.connaissance, emetteur=EMETTEUR, empreinte="0" * 64, extrait="Total revenue",
                      auteur="comptes", le=JOUR)
    except K.PieceRefusee as exc:
        refus = str(exc)
    return {"p1": p1, "p2": p2, "p3": p3, "refus": refus, "empreinte": lu.empreinte,
            "lues": (await K.lire_connaissance(monde.connaissance, recueil_depot=monde.recueil,
                                               emetteurs_depot=monde.emetteurs, emetteur=EMETTEUR)).pieces,
            "trouve": await K.chercher(monde.connaissance, emetteur=EMETTEUR, mots="annual report")}


async def _refuse(conn, sql: str, *args) -> str:
    """Le motif si la base refuse l'instruction (jouée sous un point de reprise), sinon ''."""
    try:
        async with conn.transaction():
            await conn.execute(sql, *args)
    except asyncpg.PostgresError as exc:
        return f"{type(exc).__name__}: {exc}"
    return ""


async def _section_parcours(conn, etiquette: str) -> dict:
    mem, _ = await _monde()
    base, _ = await _monde(conn)
    actes_mem, actes_base = await _parcours(mem), await _parcours(base)
    b.check(actes_base == ["lecture:collecte"] and actes_base == actes_mem,
            f"[P1]{etiquette} en base : un seul arrêt, valider les documents collectés ({actes_base})")
    v_mem, v_base = await _vues(mem), await _vues(base)
    for cle in v_mem:
        b.check(v_mem[cle] == v_base[cle], f"[P1]{etiquette} {cle} : identique en base et en mémoire")
    fin = v_base["dossier"]
    b.check((fin.get("arret") or {}).get("motif") == CD.ARRET_PARCOURS_TERMINE,
            f"[P1]{etiquette} en base : le dossier va au bout de son parcours")
    lectures = v_base["connaissance"].lectures
    b.check(len(lectures) == 3 and not v_base["connaissance"].a_lire,
            f"[P1]{etiquette} en base : les trois documents collectés ont leur lecture")
    textes = [(await K.lire_lignes(mem.connaissance, l.empreinte, l.lecteur),
               await K.lire_lignes(base.connaissance, l.empreinte, l.lecteur)) for l in lectures if l.statut == K.LUE]
    b.check(textes and all(m == x and len(m) > 1 for m, x in textes),
            f"[P1]{etiquette} les lignes de chaque lecture : identiques en base et en mémoire, dans l'ordre")

    b.check(any("annual\ufffd report" in l for _, x in textes for l in x),
            f"[P2]{etiquette} un document collecté avec un caractère nul : sa lecture est rangée en base")
    c_mem, c_base = await _citer(mem), await _citer(base)
    b.check(any("annual� report" in p.texte for p in c_base["trouve"]),
            f"[P2]{etiquette} un caractère nul : le passage se retrouve par les mots")
    b.check(c_base["p2"] == c_base["p1"] and c_base["p3"].identifiant != c_base["p1"].identifiant,
            f"[K5]{etiquette} citée deux fois : la même pièce ; une autre période : une autre pièce")
    n = await conn.fetchval("SELECT count(*) FROM connaissance_pieces WHERE emetteur = $1", EMETTEUR)
    b.check(n == 2, f"[K5]{etiquette} deux lignes en base pour trois citations (dont une répétée) — {n}")
    b.check(c_base["lues"] == c_mem["lues"] and len(c_base["lues"]) == 2,
            f"[K5]{etiquette} les pièces lues par le contrat : identiques en base et en mémoire")
    b.check("rien n'entre sans document d'origine" in c_base["refus"],
            f"[P4]{etiquette} une citation d'un document inconnu est refusée (motif du module)")
    return {"vues": v_base, "empreinte": c_base["empreinte"]}


async def _section_ajout_seul(conn, etiquette: str) -> None:
    for table in TABLES_065:
        b.check(await _refuse(conn, f"UPDATE {table} SET {'lignes = lignes' if table == 'connaissance_lignes' else 'enregistre_le = now()'}"),
                f"[P3]{etiquette} {table} : une modification est refusée")
        b.check(await _refuse(conn, f"DELETE FROM {table}"), f"[P3]{etiquette} {table} : une suppression est refusée")


async def _section_origine(conn, etiquette: str, empreinte: str) -> None:
    kd = K.depot_base(conn)
    lec = {"empreinte": "f" * 64, "emetteur": EMETTEUR, "lecteur": "1.1.0", "statut": "lue"}
    motif = ""
    try:
        async with conn.transaction():
            await kd.ranger_lecture(lec, ["ligne"])
    except asyncpg.PostgresError as exc:
        motif = type(exc).__name__
    b.check(motif == "ForeignKeyViolationError",
            f"[P4]{etiquette} une lecture d'un document jamais collecté : refusée par la base ({motif or 'acceptée'})")
    piece = {"identifiant": "x" * 64, "emetteur": EMETTEUR, "empreinte": empreinte, "lecteur": "0.0.0-inexistant",
             "ligne_debut": 1, "ligne_fin": 1, "extrait": "Total revenue", "auteur": "comptes"}
    motif = ""
    try:
        async with conn.transaction():
            await kd.ranger_piece(piece)
    except asyncpg.PostgresError as exc:
        motif = type(exc).__name__
    b.check(motif == "ForeignKeyViolationError",
            f"[P4]{etiquette} une pièce d'une lecture qui n'existe pas : refusée par la base ({motif or 'acceptée'})")


async def _section_ordre(conn, etiquette: str) -> None:
    """Les études se lisent dans l'ordre de Python (octet par octet), pas dans celui de la langue de la
    base : « A-C » avant « AB » (en français ou en anglais, le tiret est ignoré et « AB » passe avant)."""
    mem, base = T.DepotMemoire(), T.depot_base(conn)
    for d in (mem, base):
        for dossier in ("AB", "A-C", "A-B-D"):
            await d.ajouter_etude({"dossier": dossier, "mise_le": JOUR, "par": "gerant", "motif": "ordre"})
    ordre_mem = [e["dossier"] for e in await mem.etudes()]
    ordre_base = [e["dossier"] for e in await base.etudes() if e["dossier"] in ("AB", "A-C", "A-B-D")]
    b.check(ordre_base == ordre_mem == ["A-B-D", "A-C", "AB"],
            f"[P1]{etiquette} les études se lisent dans le même ordre en base et en mémoire ({ordre_base})")


class _ChefQuiRefuse:
    """Le rangement en base de l'état des dossiers, qui refuse de ranger APRÈS que le passage a écrit
    ses demandes de collecte : seul le ROLLBACK de la base peut les retirer."""

    def __init__(self, conn) -> None:
        self._vrai = CD.depot_base(conn)

    async def ouvrir(self, dossier):
        return await self._vrai.ouvrir(dossier)

    async def refermer(self, dossier, depot):
        raise CD.EcritureConcurrente("un autre passage a rangé (simulé)")


async def _section_atomique(conn, etiquette: str) -> None:
    monde, simule = await _monde(conn, chef=_ChefQuiRefuse(conn))
    await T.mettre_a_l_etude(monde, EMETTEUR, par="gerant", motif="initiation", le=JOUR)
    p = await T.passer(monde, EMETTEUR, le=JOUR)
    travaux = await conn.fetchval("SELECT count(*) FROM recueil_travaux WHERE emetteur = $1", EMETTEUR)
    etats = await conn.fetchval("SELECT count(*) FROM chef_etats WHERE dossier = $1", EMETTEUR)
    b.check(travaux == 0 and etats == 0,
            f"[K10]{etiquette} état refusé : aucune demande de collecte en base (ROLLBACK) — {travaux} travaux, {etats} état")
    b.check("EcritureConcurrente" in p.detail, f"[K10]{etiquette} le refus se dit dans le passage")


async def _section_verrou(conn, url: str, etiquette: str) -> None:
    monde, simule = await _monde(conn)
    await T.mettre_a_l_etude(monde, EMETTEUR, par="gerant", motif="initiation", le=JOUR)
    await T.passer(monde, EMETTEUR, le=JOUR)                 # la collecte est lancée
    autre = await asyncpg.connect(url)
    try:
        b.check(await T.depot_base(autre).prendre(EMETTEUR),
                f"[K10]{etiquette} un passage sur une autre connexion tient le dossier")
        p2 = await T.passer(monde, EMETTEUR, le=JOUR)
        b.check(p2.issue == T.DEJA_EN_COURS and not simule.appels,
                f"[K10]{etiquette} deux passages simultanés : le second ne relève rien ({p2.issue}, {simule.appels})")
    finally:
        await autre.close()                                  # le passage « meurt » : la base relâche
    p3 = await T.passer(monde, EMETTEUR, le=JOUR)
    b.check(p3.issue == T.AVANCE and len(simule.appels) == 2,
            f"[K10]{etiquette} la connexion qui tenait le dossier morte, le passage suivant avance ({p3.issue})")
    tenus = await conn.fetchval("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND pid = pg_backend_pid()")
    b.check(tenus == 0, f"[K10]{etiquette} le passage fini, il ne tient plus aucun verrou ({tenus})")
    b.check(await monde.etude.prendre(EMETTEUR) and not await monde.etude.prendre(EMETTEUR),
            f"[K10]{etiquette} une même connexion ne reprend pas un dossier qu'elle tient déjà")
    await monde.etude.rendre(EMETTEUR)


async def _sous_transaction(conn, section, *args):
    """Une section dans sa transaction, annulée à la fin : les sections ne se voient pas."""
    tr = conn.transaction()
    await tr.start()
    try:
        return await section(conn, *args)
    finally:
        await tr.rollback()


async def main() -> None:
    url = _db_url.replace("+asyncpg", "")
    precedent = None
    for avec_codec in (False, True):
        etiquette = " (codec JSON)" if avec_codec else ""
        conn = await asyncpg.connect(url)
        if avec_codec:
            await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
        absentes = [t for t in TABLES if await table_absente(conn, t)]
        if not b.check(not absentes, f"[P0]{etiquette} migrations 063, 064 et 065 appliquées sur cette base"
                                     + (f" — tables absentes : {', '.join(absentes)}" if absentes else "")):
            await conn.close()
            return
        avant = [await conn.fetchval(f"SELECT count(*) FROM {t}") for t in TABLES]
        try:
            tr = conn.transaction()
            await tr.start()
            try:
                r = await _section_parcours(conn, etiquette)
                await _section_ajout_seul(conn, etiquette)
                await _section_origine(conn, etiquette, r["empreinte"])
            finally:
                await tr.rollback()
            await _sous_transaction(conn, _section_ordre, etiquette)
            await _sous_transaction(conn, _section_atomique, etiquette)
            await _sous_transaction(conn, _section_verrou, url, etiquette)
            vues = {k: (v if k != "etudes" else [asdict(e) for e in v]) for k, v in r["vues"].items()}
            if precedent is not None:
                b.check(precedent == vues, "[P5] même résultat avec et sans codec JSON sur la connexion")
            precedent = vues
        except Exception as exc:  # noqa: BLE001 — un plantage est un échec NOMMÉ, le bilan est atteint
            b.check(False, f"section interrompue{etiquette} — {type(exc).__name__}: {exc}")
        finally:
            apres = [await conn.fetchval(f"SELECT count(*) FROM {t}") for t in TABLES]
            b.check(apres == avant, f"[P0]{etiquette} aucun résidu : les transactions sont annulées")
            await conn.close()


# Le geste en base se prouve sur un arrêt : la collecte relue le temps du contrôle, quelle que soit la
# valeur en vigueur (débrayée le 2026-11-22).
with CE.relecture(recueil=True):
    asyncio.run(main())
sys.exit(b.summary())
