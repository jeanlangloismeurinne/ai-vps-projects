"""Le rangement EN BASE des modules M1 (fiches, journal des sources) et M0 (état d'un dossier)
contre une VRAIE base où la migration 063 est appliquée — ligne A12 de l'acceptation
(`roadmap/V3/M1-fiche-emetteur.md` §2). Tout se joue dans UNE transaction annulée à la fin : zéro
résidu. Sociétés fictives uniquement.

  [B0] la migration 063 est appliquée ICI (sinon : échec NOMMÉ, jamais un saut)
  [B1] mêmes gestes en base et en mémoire → MÊME fiche, sources et révocations comprises
  [B2] les deux registres sont en ajout seul : ni modification ni suppression
  [B3] deux écritures sur le même rang : la seconde est refusée, rien n'est écrasé
  [B4] la base refuse d'elle-même ce que le contrat refuse (ligne incohérente, admission du
       système sans critère, révocation qui porte un niveau)
  [B5] l'état d'un dossier se range et se relit à l'identique ; un passage interrompu puis repris
       rend le même état qu'un passage d'une traite
  [B6] deux passages partis de la même lecture : le second est refusé
  [B7] même résultat que la connexion ait ou non un codec JSON (celui du service en a un)

Lancer : `bash checks/avec_base.sh check_emetteurs_persist` (VPS), ou sur une base locale :
`CHECK_DB_URL=postgresql://… python3 checks/check_emetteurs_persist.py`.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
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

from app.modules.chef_de_dossier import automate as A  # noqa: E402
from app.modules.chef_de_dossier import contrat as CD  # noqa: E402
from app.modules.emetteurs import contrat as C  # noqa: E402

E1, E2 = "FICTIVE-BASE-1", "FICTIVE-BASE-2"
SYSTEME = "systeme:evaluateur_de_sources"
TABLES = ("emetteurs_fiches", "emetteurs_sources_actes", "chef_etats")


async def _gestes(depot) -> None:
    """La même suite de gestes, jouée en base et en mémoire."""
    await C.etablir_fiche(depot, E1, raison_sociale="Fictive Base Un SA", auteur=C.UTILISATEUR,
                          motif="ouverture", le="2026-11-13", pays="FR", cotations=[("PLACE", "FB1")],
                          references=[("registre_fictif", "42")],
                          lieux=[("site", "fictive-base-un.example"),
                                 ("relations_investisseurs", "fictive-base-un.example/investisseurs")],
                          specialite="specialite_fictive")
    await C.etablir_fiche(depot, E2, raison_sociale="Fictive Base Deux", auteur=C.UTILISATEUR,
                          motif="ouverture", le="2026-11-13")
    await C.etablir_fiche(depot, E1, raison_sociale="Fictive Base Un SE", auteur=C.UTILISATEUR,
                          motif="changement de forme sociale — accents : é à ü", le="2026-12-01", pays="FR",
                          cotations=[("PLACE", "FB1")], references=[("registre_fictif", "42")],
                          lieux=[("site", "fictive-base-un.example")], specialite="specialite_fictive")
    await C.admettre_source(depot, source="autorite.example", portee=C.PORTEE_GENERALE,
                            natures=["mesure", "evenement", "interpretation"], niveau="A",
                            auteur=C.UTILISATEUR, motif="autorité fictive", le="2026-11-13")
    await C.admettre_source(depot, source="revue.example", portee="specialite:specialite_fictive",
                            natures=["interpretation"], niveau="B", auteur=SYSTEME,
                            motif="couverture de fond", le="2026-11-14", critere="redaction_specialisee")
    await C.admettre_source(depot, source="client.example", portee=f"emetteur:{E1}", natures=["evenement"],
                            niveau="B+", auteur=C.UTILISATEUR, motif="principal client", le="2026-11-15")
    await C.revoquer_source(depot, source="revue.example", portee="specialite:specialite_fictive",
                            auteur=C.UTILISATEUR, motif="information démentie", le="2026-12-02")


async def _refuse(conn, sql: str, *args) -> bool:
    """Vrai si la base refuse l'instruction (jouée sous un point de reprise : la transaction survit)."""
    try:
        async with conn.transaction():
            await conn.execute(sql, *args)
    except asyncpg.PostgresError:
        return True
    return False


async def _sections(conn, etiquette: str) -> None:
    depot = C.depot_base(conn)
    # La mémoire part de ce que la base contient DÉJÀ (fiches et journal réels) : la comparaison
    # vaut sur une base vide comme sur la base de production, sans rien supposer de son contenu.
    memoire = C.DepotMemoire()
    for e in await depot.emetteurs():
        for contenu in await depot.fiches(e):
            await memoire.ajouter_fiche(e, contenu["revision"], contenu)
    for a in await depot.actes():
        await memoire.ajouter_acte(a["rang"], a)
    fiches_avant = await conn.fetchval("SELECT count(*) FROM emetteurs_fiches")
    actes_avant = await conn.fetchval("SELECT count(*) FROM emetteurs_sources_actes")
    await _gestes(depot)
    await _gestes(memoire)

    for e in (E1, E2):
        en_base, en_memoire = await C.lire_fiche(depot, e), await C.lire_fiche(memoire, e)
        b.check(en_base == en_memoire, f"[B1]{etiquette} {e} : la fiche relue en base est celle de la mémoire")
    f1 = await C.lire_fiche(depot, E1)
    propres = {s_.source for s_ in f1.sources} & {"autorite.example", "client.example", "revue.example"}
    b.check(f1.revision == 2 and f1.motif.endswith("é à ü") and propres == {"autorite.example", "client.example"}
            and [r.natures for r in f1.revocations if r.source == "revue.example"] == [("interpretation",)],
            f"[B1]{etiquette} révision, accents, sources admises et révocation relus")
    b.check((await C.vue_ecran(depot, E1)) == (await C.vue_ecran(memoire, E1)),
            f"[B1]{etiquette} la vue de l'écran est la même en base et en mémoire")
    b.check(await conn.fetchval("SELECT count(*) FROM emetteurs_fiches") == fiches_avant + 3
            and await conn.fetchval("SELECT count(*) FROM emetteurs_sources_actes") == actes_avant + 4,
            f"[B1]{etiquette} trois révisions et quatre actes sont rangés")

    for table in TABLES[:2]:
        b.check(await _refuse(conn, f"UPDATE {table} SET enregistre_le = now()"),
                f"[B2]{etiquette} {table} : une modification est refusée")
        b.check(await _refuse(conn, f"DELETE FROM {table}"), f"[B2]{etiquette} {table} : une suppression est refusée")

    try:
        async with conn.transaction():
            await depot.ajouter_fiche(E1, 2, {**(await depot.fiches(E1))[-1], "raison_sociale": "Écrasée"})
        doublon = False
    except C.EcritureConcurrente:
        doublon = True
    except Exception:  # noqa: BLE001 — un refus brut de la base n'est pas le refus NOMMÉ attendu
        doublon = False
    b.check(doublon and (await C.lire_fiche(depot, E1)).raison_sociale == "Fictive Base Un SE",
            f"[B3]{etiquette} une révision déjà rangée ne s'écrase pas : `EcritureConcurrente`")
    try:
        async with conn.transaction():
            await depot.ajouter_acte(actes_avant + 4, {**(await depot.actes())[-1], "motif": "écrasé"})
        doublon = False
    except C.EcritureConcurrente:
        doublon = True
    except Exception:  # noqa: BLE001 — un refus brut de la base n'est pas le refus NOMMÉ attendu
        doublon = False
    b.check(doublon and (await depot.actes())[-1]["motif"] == "information démentie",
            f"[B3]{etiquette} un rang déjà pris au journal ne s'écrase pas : `EcritureConcurrente`")

    contenu = json.dumps({**(await depot.fiches(E2))[-1], "revision": 2})
    b.check(await _refuse(conn, "INSERT INTO emetteurs_fiches (emetteur, revision, contenu) "
                                "VALUES ($1, 2, $2::text::jsonb)", "AUTRE-NOM", contenu),
            f"[B4]{etiquette} une fiche rangée sous un autre identifiant que le sien est refusée par la base")
    b.check(await _refuse(conn, "INSERT INTO emetteurs_fiches (emetteur, revision, contenu) "
                                "VALUES ($1, 2, $2::text::jsonb)", E2,
                          json.dumps({**json.loads(contenu), "motif": " "})),
            f"[B4]{etiquette} une révision sans motif est refusée par la base")
    acte = ("INSERT INTO emetteurs_sources_actes (rang, acte, source, portee, natures, niveau, critere, "
            "auteur, motif, le) VALUES ((SELECT coalesce(max(rang), 0) + 1 FROM emetteurs_sources_actes), $1, 's.example', 'generale', $2::text::jsonb, $3, $4, $5, 'm', "
            "'2026-11-13')")
    b.check(await _refuse(conn, acte, "admettre", '["mesure"]', "B", "", SYSTEME),
            f"[B4]{etiquette} une admission du système sans critère est refusée par la base")
    b.check(await _refuse(conn, acte, "revoquer", "[]", "B", "", C.UTILISATEUR),
            f"[B4]{etiquette} une révocation qui porte un niveau est refusée par la base")
    b.check(await _refuse(conn, acte, "admettre", "[]", "B", "", C.UTILISATEUR),
            f"[B4]{etiquette} une admission sans nature est refusée par la base")
    b.check(not await _refuse(conn, acte, "admettre", '["mesure"]', "B", "", C.UTILISATEUR),
            f"[B4]{etiquette} témoin : la même ligne, conforme, est acceptée")


def _parcours(fiche):
    def simule(nom, cout):
        return CD.Pas(nom=nom, module="module_simule", apres=(C.NOM_DU_PAS,),
                      executer=lambda ctx: CD.Resultat(CD.FAIT, CD.Depense(modeles_usd=cout)),
                      cout_estime_usd=cout)
    return [C.pas_fiche(fiche), simule("pas_simule_1", 0.6), simule("pas_simule_2", 0.6),
            simule("pas_simule_3", 0.1)]


async def _chef(conn) -> None:
    libre = {C.NOM_DU_MODULE: False, "module_simule": False}
    fiche = await C.lire_fiche(C.depot_base(conn), E1)
    parcours = _parcours(fiche)

    # D'une traite, en mémoire : la référence.
    ref_depot = CD.DepotMemoire()
    A.conduire(ref_depot, E1, parcours, lecture_humaine=libre)
    ref = CD.lire_etat(ref_depot, E1)
    b.check(ref.arret.motif == CD.ARRET_PAUSE_DEPENSE and C.NOM_DU_PAS in ref.faits,
            "[B5] témoin : le parcours simulé s'arrête à la pause de dépense, fiche faite")

    base = CD.depot_base(conn)
    d = await base.ouvrir(E1)
    b.check(CD.lire_etat(d, E1) == CD.EtatDossier(E1), "[B5] un dossier jamais rangé s'ouvre vierge")
    A.conduire(d, E1, parcours, lecture_humaine=libre)
    await base.refermer(E1, d)
    relu = CD.lire_etat(await CD.depot_base(conn).ouvrir(E1), E1)
    b.check(relu == ref, "[B5] l'état rangé en base se relit identique à celui de la mémoire")

    # Interrompu puis repris (pause levée) : en base, en deux ouvertures ; en mémoire, d'une traite.
    A.conduire(ref_depot, E1, parcours, lecture_humaine=libre)  # en pause : ne fait rien
    ref_depot.ranger(E1, A.lever_pause(CD.lire_etat(ref_depot, E1)).vers_dict())
    A.conduire(ref_depot, E1, parcours, lecture_humaine=libre)
    reprise = CD.depot_base(conn)
    d2 = await reprise.ouvrir(E1)
    d2.ranger(E1, A.lever_pause(CD.lire_etat(d2, E1)).vers_dict())
    await reprise.refermer(E1, d2)
    d3 = await reprise.ouvrir(E1)
    A.conduire(d3, E1, parcours, lecture_humaine=libre)
    await reprise.refermer(E1, d3)
    final = CD.lire_etat(await CD.depot_base(conn).ouvrir(E1), E1)
    b.check(final == CD.lire_etat(ref_depot, E1) and final.arret.motif == CD.ARRET_PARCOURS_TERMINE,
            "[B5] interrompu puis repris en base = le même état que d'une traite, parcours terminé")
    b.check(await conn.fetchval("SELECT revision FROM chef_etats WHERE dossier = $1", E1) == 3,
            "[B5] trois rangements = révision 3 (une ligne par dossier)")

    # Deux passages partis de la même lecture.
    for dossier, quoi in ((E2, "dossier neuf"), (E1, "dossier déjà rangé")):
        p1, p2 = CD.depot_base(conn), CD.depot_base(conn)
        m1, m2 = await p1.ouvrir(dossier), await p2.ouvrir(dossier)
        for m in (m1, m2):
            m.ranger(dossier, CD.EtatDossier(dossier, faits=("un_pas",)).vers_dict())
        await p1.refermer(dossier, m1)
        try:
            async with conn.transaction():
                await p2.refermer(dossier, m2)
            refuse = False
        except CD.EcritureConcurrente:
            refuse = True
        b.check(refuse, f"[B6] {quoi} : le second passage parti de la même lecture est refusé")
    b.check(await _refuse(conn, "DELETE FROM chef_etats"),
            "[B6] l'état d'un dossier ne se supprime pas (rôle du service)")
    b.check(await _refuse(conn, "INSERT INTO chef_etats (dossier, etat, revision) VALUES ('X', $1::text::jsonb, 1)",
                          json.dumps({"dossier": "Y", "version_contrat": "1.0.0"})),
            "[B6] un état rangé sous un autre dossier que le sien est refusé par la base")


async def main() -> None:
    url = _db_url.replace("+asyncpg", "")
    for avec_codec in (False, True):
        conn = await asyncpg.connect(url)
        etiquette = " (codec JSON)" if avec_codec else ""
        if avec_codec:
            await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
        absentes = [t for t in TABLES if await table_absente(conn, t)]
        if not b.check(not absentes, f"[B0]{etiquette} migration 063 appliquée sur cette base"
                                     + (f" — tables absentes : {', '.join(absentes)}" if absentes else "")):
            await conn.close()
            return
        avant = [await conn.fetchval(f"SELECT count(*) FROM {t}") for t in TABLES]
        tr = conn.transaction()
        await tr.start()
        try:
            await _sections(conn, etiquette)
            if avec_codec:
                b.check(True, "[B7] les mêmes sections passent avec le codec JSON du service")
            else:
                await _chef(conn)
        except Exception as exc:  # noqa: BLE001 — un plantage est un échec NOMMÉ, le bilan est atteint
            b.check(False, f"section interrompue{etiquette} — {type(exc).__name__}: {exc}")
        finally:
            await tr.rollback()
            apres = [await conn.fetchval(f"SELECT count(*) FROM {t}") for t in TABLES]
            b.check(apres == avant, f"[B0]{etiquette} aucun résidu : la transaction est annulée")
            await conn.close()


asyncio.run(main())
sys.exit(b.summary())
