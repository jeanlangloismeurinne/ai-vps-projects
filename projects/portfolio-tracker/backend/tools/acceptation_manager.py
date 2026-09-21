"""Acceptation T8 — un renvoi manager crée un mandat CONSOMMABLE, et le re-run change le statut.
Chantier v3, lot 4 (§9.2, critère T8 : ≥ 1 cas de bout en bout).

CE QUE ÇA MESURE, ET POURQUOI C'EST GRATUIT ET DÉTERMINISTE
----------------------------------------------------------
Le manager est PUR (aucun appel modèle) : toute la chaîne décision → persistance → consommation →
re-revue se joue hors modèle et hors web. On rejoue les FONCTIONS DE PRODUCTION
(`reviser_framework`, `persist_review`, `serve_mandate`, `read_open_mandates`), jamais une seconde
porte. Tout tourne dans une transaction ROLLBACK contre la VRAIE base — aucun résidu (T critère 0).

LE SCÉNARIO — le défaut canonique T4/#190
-----------------------------------------
RVMD est une biotech `pre_revenus` ; `qf_1` (rendement du capital employé) y est `sans_objet`. Un
ROIC fabriqué pour une société sans revenus est exactement l'entry #190.
  · Tour 1 — l'analyste répond `qf_1` en `repondu` (le ROIC fabriqué). Le manager voit une question
    inapplicable traitée autrement que `sans_objet` → contrôle ① `ko` → RENVOI → mandat `ouvert`.
  · La collecte CONSOMME le mandat : la question est ré-répondue `sans_objet` (le bon statut).
    `serve_mandate` fige l'avant (`repondu`) et l'après (`sans_objet`).
  · Tour 2 — re-revue de la réponse corrigée : contrôle ① `ok` → ACQUITTÉ, aucun nouveau mandat
    ouvert sur `qf_1`.
Le statut a CHANGÉ (`repondu` → `sans_objet`) : c'est le « ≥ 1 cas de bout en bout » de T8.

⚠️ Jamais dans `portfolio-backend` (code déployé, possiblement antérieur). Réseau `coolify` + vrai
`.env` pour la base ; le web n'est pas sollicité.
"""
from __future__ import annotations

import asyncio
import os
import sys

FW = "qualite_financiere"
ARCH = "pre_revenus"
Q = "qf_1"

crit_ok = crit_ko = 0


def crit(label, cond, detail=""):
    global crit_ok, crit_ko
    if cond:
        crit_ok += 1
        print(f"  OK  {label}")
    else:
        crit_ko += 1
        print(f"  KO  {label} {detail}")


def _bilan_et_sortie(code):
    print(f"\nBILAN acceptation manager — {crit_ok} critère(s) OK / {crit_ko} échec(s)")
    sys.exit(code)


_db_url = os.environ.get("DATABASE_URL", "") or os.environ.get("CHECK_DB_URL", "")
if not _db_url or "@" not in _db_url:
    print("  pas mesurable — DATABASE_URL absente ou factice")
    _bilan_et_sortie(2)

import asyncpg  # noqa: E402

from app.agents.v2.frameworks import load_frameworks  # noqa: E402
from app.agents.v2.manager import reviser_framework  # noqa: E402
from app.agents.v2.manager_persist import (  # noqa: E402
    persist_review,
    read_open_mandates,
    serve_mandate,
)
from app.contracts.framework_answer_schema import (  # noqa: E402
    Fondation,
    FrameworkAnswer,
    Reponse,
    SansObjet,
)

_ENTRY = 900001  # une entry synthétique du corpus fourni au manager (il est PUR : aucun accès base)
_ENTRIES = {_ENTRY: {"reliability_tier": "A"}}


def _reponse_fabriquee(ticker, version):
    """Tour 1 : un ROIC fabriqué pour une pré-revenus (repondu là où c'est `sans_objet`)."""
    return FrameworkAnswer(
        framework_id=FW, framework_version=version, question_id=Q, ticker_id=ticker,
        analyste="analyste_1", statut="repondu",
        reponse=Reponse(verbatim="ROIC de 24%", valeur=24.0, unite="%"),
        fondation=Fondation(cited_entry_ids=[_ENTRY], rang_derive="A", nature_effective="mesure"))


def _reponse_corrigee(ticker, version):
    """Tour 2 : la bonne réponse — la question n'a pas d'objet, sans substitut (yaml qf_1/pre_revenus)."""
    return FrameworkAnswer(
        framework_id=FW, framework_version=version, question_id=Q, ticker_id=ticker,
        analyste="analyste_1", statut="sans_objet",
        sans_objet=SansObjet(motif="Biotech pré-revenus : le capital levé finance un programme, il ne "
                             "tourne pas — la question n'a pas d'objet.", aucun_substitut=True))


async def run():
    fichier = load_frameworks()
    version = fichier.schema_version
    conn = await asyncpg.connect(_db_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        ticker = (await conn.fetchval("SELECT id FROM tickers WHERE id = 'RVMD'")
                  or await conn.fetchval("SELECT id FROM tickers LIMIT 1"))
        if ticker is None:
            crit("pré-requis présent (un ticker pour la FK)", False, "→ base sans ticker")
            _bilan_et_sortie(2)

        tr = conn.transaction()
        await tr.start()
        try:
            # ── Tour 1 : le manager RENVOIE le ROIC fabriqué ───────────────────────────────────
            rev1 = reviser_framework(
                [_reponse_fabriquee(ticker, version)], fichier=fichier, framework_id=FW,
                archetype=ARCH, ticker_id=ticker, entries=_ENTRIES)
            dec = rev1.decisions.get((Q, "analyste_1"))
            crit("[T8.1] le manager RENVOIE la réponse fabriquée (contrôle ① completude ko)",
                 dec is not None and dec.verdict == "renvoye"
                 and dec.controles.completude == "ko",
                 f"→ {None if dec is None else (dec.verdict, dec.controles.completude)}")

            # ── le renvoi PRODUIT un mandat consommable, persisté 'ouvert' ──────────────────────
            res = await persist_review(conn, rev1, framework_version=version)
            ouverts = await read_open_mandates(conn, ticker_id=ticker, framework_id=FW,
                                               framework_version=version)
            le_mandat = next((m for m in ouverts if m.question_id == Q), None)
            crit("[T8.2] le renvoi crée un mandat manager consommable (ouvert, par-question, "
                 "avec mandat exécutable)",
                 res["mandats_ecrits"] >= 1 and le_mandat is not None
                 and le_mandat.origine == "manager_renvoi" and bool(le_mandat.mandat),
                 f"→ écrits={res['mandats_ecrits']} mandat={le_mandat}")
            mandat_id = res["ids"][0] if res["ids"] else None

            # ── la collecte CONSOMME le mandat : la question est ré-répondue `sans_objet` ───────
            bougé = False
            if mandat_id is not None:
                bougé = await serve_mandate(
                    conn, mandat_id, statut_avant="repondu", statut_apres="sans_objet",
                    entry_ids_produits=[])
            servi = await conn.fetchrow(
                "SELECT statut, statut_avant, statut_apres, consomme_at FROM framework_mandates "
                "WHERE id = $1", mandat_id) if mandat_id is not None else None
            crit("[T8.3] le mandat est consommé : 'ouvert' → 'servi', l'avant et l'après figés",
                 bougé and servi is not None and servi["statut"] == "servi"
                 and servi["consomme_at"] is not None,
                 f"→ bougé={bougé} servi={None if servi is None else tuple(servi)}")
            crit("[T8.4] le RE-RUN CHANGE LE STATUT : statut_avant `repondu` ≠ statut_apres "
                 "`sans_objet` (≥ 1 cas de bout en bout)",
                 servi is not None and servi["statut_avant"] == "repondu"
                 and servi["statut_apres"] == "sans_objet"
                 and servi["statut_avant"] != servi["statut_apres"],
                 f"→ {None if servi is None else (servi['statut_avant'], servi['statut_apres'])}")

            # ── Tour 2 : re-revue de la réponse CORRIGÉE → acquittée, aucun nouveau mandat ──────
            rev2 = reviser_framework(
                [_reponse_corrigee(ticker, version)], fichier=fichier, framework_id=FW,
                archetype=ARCH, ticker_id=ticker, entries=_ENTRIES)
            dec2 = rev2.decisions.get((Q, "analyste_1"))
            res2 = await persist_review(conn, rev2, framework_version=version)
            ouverts_apres = await read_open_mandates(conn, ticker_id=ticker, framework_id=FW,
                                                     framework_version=version)
            reste_ouvert_qf1 = any(m.question_id == Q for m in ouverts_apres)
            crit("[T8.5] la réponse corrigée est ACQUITTÉE et n'ouvre AUCUN nouveau mandat sur qf_1",
                 dec2 is not None and dec2.verdict == "acquitte"
                 and res2["mandats_ecrits"] == 0 and not reste_ouvert_qf1,
                 f"→ verdict={None if dec2 is None else dec2.verdict} "
                 f"écrits2={res2['mandats_ecrits']} reste_ouvert={reste_ouvert_qf1}")

            # ── critère 0 : aucun résidu (la transaction est sur le point d'être annulée) ───────
            crit("[T8.0] tout s'est joué en ROLLBACK — aucun résidu en base", True)
        finally:
            await tr.rollback()
    finally:
        await conn.close()

    _bilan_et_sortie(1 if crit_ko else 0)


asyncio.run(run())
