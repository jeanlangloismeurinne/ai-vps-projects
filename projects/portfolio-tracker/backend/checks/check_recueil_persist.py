"""Le rangement EN BASE du module M2 « recueil » (tables de la migration 064) contre une VRAIE base
où elle est appliquée. Tout se joue dans UNE transaction annulée à la fin : zéro résidu. Société
fictive uniquement — réutilise le monde simulé de `checks/check_recueil.py` (Transport, Outils,
Moteur, les fiches fictives, le registre SEC fictif) : aucun réseau, aucun modèle, aucune dépense
réelle.

  [R0] la migration 064 est appliquée ICI (sinon : échec NOMMÉ, jamais un saut)
  [R1] les MÊMES gestes (collecter, traiter_les_travaux, evaluer_les_sources_rencontrees avec un
       évaluateur simulé, ranger_envoi) joués sur `DepotMemoire` et sur le dépôt base rendent le
       MÊME `lire_recueil` et la MÊME `vue_ecran` — comparés en entier, jamais un champ
  [R2] documents, contenus et réponses sont en ajout seul : la base refuse UPDATE et DELETE
  [R3] le même document rangé deux fois : une seule ligne, contenu identique octet pour octet
       (y compris un contenu binaire qui n'est pas de l'UTF-8 valide)
  [R4] une collecte interrompue puis reprise (B8) : ce qui est déjà rangé n'est pas recollecté
  [R5] une source rencontrée deux fois : ses adresses se fusionnent (dédupliquées, anciennes
       d'abord), le reste de son état est gardé ; `marquer_source` fusionne ce qu'on lui donne
  [R6] même résultat que la connexion ait ou non le codec JSON du service

Lancer : `bash checks/avec_base.sh check_recueil_persist` (VPS), ou sur une base locale/jetable où
063 PUIS 064 sont appliquées :
`CHECK_DB_URL=postgresql://… python3 checks/check_recueil_persist.py`.
"""
from __future__ import annotations

import asyncio
import hashlib
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

from app.modules.chef_de_dossier import automate as AU  # noqa: E402
from app.modules.chef_de_dossier import contrat as CD  # noqa: E402
from app.modules.emetteurs import contrat as E  # noqa: E402
from app.modules.recueil import contrat as R  # noqa: E402
import check_recueil as RC  # noqa: E402 — réutilise le monde simulé (Transport, Outils, Moteur, fiches…)

TABLES = ("recueil_documents", "recueil_contenus", "recueil_reponses",
          "recueil_travaux", "recueil_sources_rencontrees")
TABLES_AJOUT_SEUL = TABLES[:3]
DEMANDES_INTRO = [R.Demande("derniers_comptes_annuels", "FICTIVE-INTRO"),
                  R.Demande("annonces_importantes", "FICTIVE-INTRO", depuis="2026-01-01")]


def _evaluateur(oui: bool):
    """Un évaluateur simulé — même forme que celui de `check_recueil.py`, nommé ici pour ne pas
    dépendre d'une fonction locale à son `main()`."""
    questions = list(json.loads((BACKEND / "app/modules/emetteurs/referentiel.json").read_text())
                     ["evaluation_des_sources"]["questions"])

    async def ev(source, adresses):
        pubs = tuple(E.ExempleEvalue(f"https://{source}/p{i}", tuple(
            E.Reponse(q, oui or i > 0, "constaté") for q in questions)) for i in range(3))
        return (E.Evaluation(source=source, portee=E.PORTEE_GENERALE, natures=("interpretation",),
                             niveau="B", critere="presse_financiere", exemples=pubs),
                CD.Depense(modeles_usd=0.02))
    return ev


async def _refuse(conn, sql: str, *args) -> bool:
    """Vrai si la base refuse l'instruction (jouée sous un point de reprise : la transaction survit)."""
    try:
        async with conn.transaction():
            await conn.execute(sql, *args)
    except asyncpg.PostgresError:
        return True
    return False


async def _gestes(depot, ed) -> dict:
    """La même suite de gestes, jouée sur `depot` (mémoire ou base) : des collectes directes qui
    exercent l'amendement, la source non admise et la source inconnue, puis le chef de dossier
    sur une collecte suivie, interrompue par une panne de transport, puis reprise."""
    await RC.fiches(ed)
    t = RC.Transport(RC.monde())
    out = RC.Outils(t, RC.Moteur(RC.RESULTATS))

    await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-ANCIENNE"),
                      depot=depot, emetteurs_depot=ed, outils=out, le=RC.JOUR)
    await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-ANCIENNE"),      # ne recollecte pas
                      depot=depot, emetteurs_depot=ed, outils=out, le="2026-11-17")
    await R.collecter(R.Demande("comptes_intermediaires", "FICTIVE-ANCIENNE", depuis="2025-01-01"),
                      depot=depot, emetteurs_depot=ed, outils=out, le=RC.JOUR)         # source non admise
    await R.collecter(R.Demande("derniers_comptes_annuels", "FICTIVE-PRIVEE"),
                      depot=depot, emetteurs_depot=ed, outils=out, le=RC.JOUR)         # source inconnue

    async def passage(etat):
        envoi = R.Envoi()
        fiche = await E.lire_fiche(ed, "FICTIVE-INTRO")
        vue = await R.vue_travaux(depot, "FICTIVE-INTRO")
        etat = AU.avancer(etat, [E.pas_fiche(fiche),
                                 R.pas_collecte("collecte", DEMANDES_INTRO, vue, envoi, apres=(E.NOM_DU_PAS,))],
                          lecture_humaine=RC.SANS_LECTURE)
        await R.ranger_envoi(depot, envoi)
        return etat

    etat = await passage(CD.EtatDossier(dossier="FICTIVE-INTRO"))
    etat = await passage(etat)                                              # rien n'a encore répondu
    t.plante_sur.add(RC.u_soum(RC.INTRO, "0009000001-26-000009"))           # panne de transport simulée
    await R.traiter_les_travaux(depot=depot, emetteurs_depot=ed, outils=out, le=RC.JOUR)
    etat = await passage(etat)                                              # échec vu, relancé une fois
    t.plante_sur.clear()
    await R.traiter_les_travaux(depot=depot, emetteurs_depot=ed, outils=out, le=RC.JOUR)
    etat = await passage(etat)                                              # parcours terminé

    lignes1 = await R.evaluer_les_sources_rencontrees(depot=depot, emetteurs_depot=ed,
                                                       evaluateur=_evaluateur(True), le=RC.JOUR)
    lignes2 = await R.evaluer_les_sources_rencontrees(depot=depot, emetteurs_depot=ed,  # rien à rejuger
                                                       evaluateur=_evaluateur(True), le=RC.JOUR)
    return {"t": t, "etat_intro": etat, "lignes1": lignes1, "lignes2": lignes2}


async def _comparer(conn, etiquette: str) -> None:
    rd_mem, rd_base = R.DepotMemoire(), R.depot_base(conn)
    res_mem = await _gestes(rd_mem, E.DepotMemoire())
    res_base = await _gestes(rd_base, E.DepotMemoire())

    for emetteur in ("FICTIVE-ANCIENNE", "FICTIVE-PRIVEE", "FICTIVE-INTRO"):
        b.check((await R.lire_recueil(rd_mem, emetteur)) == (await R.lire_recueil(rd_base, emetteur)),
                f"[R1]{etiquette} {emetteur} : lire_recueil identique en base et en mémoire")
        b.check((await R.vue_ecran(rd_mem, emetteur)) == (await R.vue_ecran(rd_base, emetteur)),
                f"[R1]{etiquette} {emetteur} : vue_ecran identique en base et en mémoire")

    b.check(res_base["etat_intro"].arret is not None
            and res_base["etat_intro"].arret.motif == CD.ARRET_PARCOURS_TERMINE,
            f"[R4]{etiquette} en base : le dossier termine son parcours après la reprise",
            )
    b.check(res_base["t"].lectures.get(RC.u_doc(RC.INTRO, "0009000001-26-000002", "fint-prospectus.htm")) == 1,
            f"[R4]{etiquette} en base : la reprise ne recollecte pas ce qui est déjà rangé")
    nb: dict[str, int] = {}
    for r in await rd_base.reponses("FICTIVE-INTRO"):
        nb[r["demande"]["genre"]] = nb.get(r["demande"]["genre"], 0) + 1
    b.check(nb == {"derniers_comptes_annuels": 1, "annonces_importantes": 1},
            f"[R4]{etiquette} en base : une réponse par demande, pas plus, après la reprise")


async def _verifier_ajout_seul(conn, etiquette: str) -> None:
    for table in TABLES_AJOUT_SEUL:
        b.check(await _refuse(conn, f"UPDATE {table} SET enregistre_le = now()"),
                f"[R2]{etiquette} {table} : une modification est refusée")
        b.check(await _refuse(conn, f"DELETE FROM {table}"),
                f"[R2]{etiquette} {table} : une suppression est refusée")


async def _verifier_doublon_binaire(conn, etiquette: str) -> None:
    depot = R.depot_base(conn)
    contenu = bytes(range(256)) + b"\xff\xfe\x00\x80"          # binaire, pas de l'UTF-8 valide
    empreinte = hashlib.sha256(contenu).hexdigest()
    fiche_doc = {
        "empreinte": empreinte, "emetteur": "FICTIVE-BINAIRE", "genre": "derniers_comptes_annuels",
        "provenance": {"adaptateur": "test_binaire", "adresse": "https://bin.example/x", "registre": "",
                       "identifiant": "b-1", "partie": "p", "publie_le": "", "faits_au": "",
                       "remplace": "", "mention": ""},
        "type_media": "application/octet-stream", "taille": len(contenu),
        "qualification": {"admise": False, "niveau": "C", "motif": "test", "source": ""},
        "collecte_le": RC.JOUR, "version_contrat": R.VERSION_CONTRAT,
    }
    ok1 = await depot.ranger_document(fiche_doc, contenu)
    ok2 = await depot.ranger_document(fiche_doc, contenu)
    n_doc = await conn.fetchval("SELECT count(*) FROM recueil_documents WHERE empreinte = $1", empreinte)
    n_con = await conn.fetchval("SELECT count(*) FROM recueil_contenus WHERE empreinte = $1", empreinte)
    relu = await depot.contenu(empreinte)
    b.check(ok1 is True and ok2 is False,
            f"[R3]{etiquette} rangé deux fois : la seconde écriture est un doublon (False)")
    b.check(n_doc == 1 and n_con == 1, f"[R3]{etiquette} une seule ligne en base (document et contenu)")
    b.check(relu == contenu, f"[R3]{etiquette} le contenu relu est identique octet pour octet (binaire)")


async def _verifier_fusion_sources(conn, etiquette: str) -> None:
    rd_mem, rd_base = R.DepotMemoire(), R.depot_base(conn)
    ligne1 = {"source": "fusion.example", "emetteur": "FICTIVE-FUSION", "nature": "mesure",
              "adresses": ["https://fusion.example/a", "https://fusion.example/b"],
              "vue_le": "2026-11-10", "statut": "a_evaluer", "travail": "cle-1", "essais": 0, "motif": ""}
    ligne2 = {**ligne1, "nature": "evenement", "vue_le": "2026-11-17", "travail": "cle-2",
              "adresses": ["https://fusion.example/b", "https://fusion.example/c"]}
    for rd in (rd_mem, rd_base):
        await rd.noter_source_rencontree(ligne1)
        await rd.noter_source_rencontree(ligne2)
    for rd, nom in ((rd_mem, "mémoire"), (rd_base, "base")):
        lignes = [s for s in await rd.sources_rencontrees() if s["source"] == "fusion.example"]
        if not b.require(lignes, 1, f"[R5]{etiquette} une seule ligne pour la source notée deux fois ({nom})"):
            continue
        s = lignes[0]
        b.check(s["adresses"] == ["https://fusion.example/a", "https://fusion.example/b",
                                  "https://fusion.example/c"],
                f"[R5]{etiquette} adresses fusionnées, dédupliquées, les anciennes d'abord ({nom})")
        b.check(s["nature"] == "mesure" and s["vue_le"] == "2026-11-10" and s["travail"] == "cle-1",
                f"[R5]{etiquette} une source déjà notée garde son état, seules ses adresses s'ajoutent ({nom})")
    await rd_mem.marquer_source("fusion.example", {"statut": "evaluee", "issue": "admise"})
    await rd_base.marquer_source("fusion.example", {"statut": "evaluee", "issue": "admise"})
    for rd, nom in ((rd_mem, "mémoire"), (rd_base, "base")):
        s = (await rd.sources_rencontrees())[0]
        b.check(s["statut"] == "evaluee" and s["issue"] == "admise" and s["nature"] == "mesure",
                f"[R5]{etiquette} marquer_source fusionne les champs donnés, garde le reste ({nom})")
    # Filtré à CETTE source : la base porte déjà celles d'autres sections de la même transaction
    # (`_comparer`) — comparer la table ENTIÈRE comparerait des univers différents, pas la garde.
    def _fusion(sources):
        return [s for s in sources if s["source"] == "fusion.example"]
    b.check(_fusion(await rd_mem.sources_rencontrees()) == _fusion(await rd_base.sources_rencontrees()),
            f"[R5]{etiquette} même résultat en base et en mémoire")


async def main() -> None:
    url = _db_url.replace("+asyncpg", "")
    precedent = None
    for avec_codec in (False, True):
        conn = await asyncpg.connect(url)
        etiquette = " (codec JSON)" if avec_codec else ""
        if avec_codec:
            await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")
        absentes = [t for t in TABLES if await table_absente(conn, t)]
        if not b.check(not absentes, f"[R0]{etiquette} migration 064 appliquée sur cette base"
                                     + (f" — tables absentes : {', '.join(absentes)}" if absentes else "")):
            await conn.close()
            return
        avant = [await conn.fetchval(f"SELECT count(*) FROM {t}") for t in TABLES]
        tr = conn.transaction()
        await tr.start()
        try:
            await _comparer(conn, etiquette)
            await _verifier_ajout_seul(conn, etiquette)
            await _verifier_doublon_binaire(conn, etiquette)
            await _verifier_fusion_sources(conn, etiquette)
            resultat = (await R.lire_recueil(R.depot_base(conn), "FICTIVE-INTRO"),
                       await R.vue_ecran(R.depot_base(conn), "FICTIVE-INTRO"))
            if precedent is not None:
                b.check(precedent == resultat, "[R6] même résultat avec et sans codec JSON sur la connexion")
            precedent = resultat
        except Exception as exc:  # noqa: BLE001 — un plantage est un échec NOMMÉ, le bilan est atteint
            b.check(False, f"section interrompue{etiquette} — {type(exc).__name__}: {exc}")
        finally:
            await tr.rollback()
            apres = [await conn.fetchval(f"SELECT count(*) FROM {t}") for t in TABLES]
            b.check(apres == avant, f"[R0]{etiquette} aucun résidu : la transaction est annulée")
            await conn.close()


asyncio.run(main())
sys.exit(b.summary())
