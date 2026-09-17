"""Vérification de la PERSISTANCE et de la LECTURE de la carte d'appariement
(lot 3 maillon 4bis étape 2b — migration 042, `app/agents/v2/appariement_persist.py`).

Lit l'ÉTAT PERSISTABLE, pas seulement la règle : les fonctions écrivent vraiment, on relit, on
vérifie. Tout se passe dans une transaction ROLLBACK — **aucun résidu** en base
(`feedback_fixture_pollue_le_reel`).

Exige le réseau `coolify` + `CHECK_DB_URL` : sans elle, la moitié « état persisté » n'est pas
mesurée → SORT EN ÉCHEC, jamais un saut de section (`feedback_check_degrade_en_sortant_a_zero`).

  • §1 une carte s'écrit via UPSERT et se relit identiquement (les 3 états préservés) ;
  • §2 REVÉRIFICATION À LA LECTURE (#54) — un dépôt courant PLUS RÉCENT → carte traitée comme absente ;
  • §2bis un dépôt courant IDENTIQUE → carte VALIDE (on ne recalcule pas inutilement) ;
  • §3 un UPSERT sur la même clef (ticker × framework × version) ÉCRASE la carte, pas de doublon ;
  • §4 DERNIER REMPART — la base REFUSE des items JSON vides (garde `appariement_cartes_items_non_vide`)
       et un format de date invalide (garde `appariement_cartes_depot_format`).
"""
import asyncio
import json as _json
import os
import sys

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ok   {label}")
    else:
        fail += 1
        print(f"  FAIL {label} {detail}")


_db_url = os.environ.get("CHECK_DB_URL", "")
if not _db_url or "@" not in _db_url:
    print("  FAIL §persistance non exécutée — CHECK_DB_URL absente ou factice ; l'état persisté "
          "n'a PAS été mesuré")
    print("\n=== 0 ok / 1 FAIL ===\n0 vérifications OK, 1 échec(s)")
    sys.exit(1)

import asyncpg  # noqa: E402

from app.agents.v2.appariement_persist import lire_carte, persister_carte  # noqa: E402
from app.contracts.appariement_schema import AppariementCarte, AppariementItem  # noqa: E402


async def _rejette(conn, label, sql, *args):
    """La base DOIT refuser. Savepoint : l'échec n'abîme pas la transaction outer."""
    global ok, fail
    sp = conn.transaction()
    await sp.start()
    try:
        await conn.execute(sql, *args)
    except (asyncpg.exceptions.CheckViolationError, asyncpg.exceptions.NotNullViolationError):
        await sp.rollback()
        ok += 1
        print(f"  ok   {label}")
        return
    except Exception as e:  # noqa: BLE001
        await sp.rollback()
        fail += 1
        print(f"  FAIL {label} → mauvaise exception {type(e).__name__}: {e}")
        return
    await sp.rollback()
    fail += 1
    print(f"  FAIL {label} → la base a ACCEPTÉ la ligne interdite")


# Fixture minimale : une carte à trois ingrédients, un par statut.
_ITEM_EXACT = AppariementItem(
    question_id="qf_1",
    ingredient_id="resultat_net",
    statut="exact",
    concepts=["NetIncomeLoss"],
)
_ITEM_APPROX = AppariementItem(
    question_id="qf_2",
    ingredient_id="capital_employe",
    statut="approximation",
    concepts=["Assets", "LiabilitiesCurrent", "CashAndCashEquivalentsAtCarryingValue"],
    formule="Assets - LiabilitiesCurrent - CashAndCashEquivalentsAtCarryingValue",
    hypotheses=["Les actifs courants sont réduits des dettes courantes et de la trésorerie."],
    deterministe=True,
)
_ITEM_INDISPO = AppariementItem(
    question_id="qf_3",
    ingredient_id="couts_fixes_decaissables",
    statut="indisponible",
    motif="Aucun champ du dépôt EDGAR ne distingue les coûts fixes décaissables des coûts variables.",
)

# Carte 1 : dépôt vu = 2025-10-26
_CARTE_1 = AppariementCarte(
    ticker_id="NVDA",
    framework_id="qualite_financiere",
    framework_version="v3.0.0",
    dernier_depot_vu="2025-10-26",
    items=[_ITEM_EXACT, _ITEM_APPROX, _ITEM_INDISPO],
)
# Carte 2 : dépôt plus récent, remplace la carte 1 (UPSERT)
_CARTE_2 = AppariementCarte(
    ticker_id="NVDA",
    framework_id="qualite_financiere",
    framework_version="v3.0.0",
    dernier_depot_vu="2026-01-15",
    items=[_ITEM_EXACT],
)


async def run():
    conn = await asyncpg.connect(_db_url.replace("postgresql+asyncpg://", "postgresql://"))
    await conn.set_type_codec("jsonb", encoder=_json.dumps, decoder=_json.loads,
                              schema="pg_catalog")

    ticker = await conn.fetchval("SELECT id FROM tickers WHERE id = 'NVDA'")
    if ticker is None:
        check("pré-requis : ticker NVDA présent", False,
              "→ ce check exige que NVDA soit dans la table tickers")
        print("\n=== 0 ok / 1 FAIL ===\n0 vérifications OK, 1 échec(s)")
        await conn.close()
        sys.exit(1)

    tr = conn.transaction()
    await tr.start()
    try:
        # ── §1 : écriture + lecture (les 3 états) ─────────────────────────────────
        print("[1] écriture + lecture — les 3 états (exact / approximation / indisponible)")
        row_id = await persister_carte(conn, _CARTE_1)
        check("§1 persister_carte rend un id entier positif",
              isinstance(row_id, int) and row_id > 0)

        nb = await conn.fetchval(
            "SELECT COUNT(*) FROM appariement_cartes "
            "WHERE ticker_id = 'NVDA' AND framework_id = 'qualite_financiere' "
            "AND framework_version = 'v3.0.0'")
        check("§1 exactement 1 ligne en base après persister_carte",
              nb == 1, f"→ {nb} ligne(s)")

        # Lecture avec la même date que le dépôt : carte valide.
        carte_lue = await lire_carte(
            conn, ticker_id="NVDA", framework_id="qualite_financiere",
            framework_version="v3.0.0", depot_courant="2025-10-26")
        check("§1 lire_carte retourne un AppariementCarte",
              isinstance(carte_lue, AppariementCarte))
        check("§1 dernier_depot_vu est conservé",
              carte_lue is not None and carte_lue.dernier_depot_vu == "2025-10-26")
        check("§1 les trois items sont conservés",
              carte_lue is not None and len(carte_lue.items) == 3,
              f"→ {len(carte_lue.items) if carte_lue else 0} item(s)")

        if carte_lue is not None:
            statuts = [it.statut for it in carte_lue.items]
            check("§1 les trois états sont préservés (exact/approximation/indisponible)",
                  statuts == ["exact", "approximation", "indisponible"], f"→ {statuts}")
            approx = next((it for it in carte_lue.items if it.statut == "approximation"), None)
            check("§1 approximation : formule préservée",
                  approx is not None and approx.formule is not None)
            check("§1 approximation : deterministe=True préservé",
                  approx is not None and approx.deterministe is True)
            check("§1 approximation : hypotheses préservées (1 phrase)",
                  approx is not None and len(approx.hypotheses) == 1)
        else:
            for _ in range(4):
                check("§1 item non vérifiable (carte non lue)", False)

        # ── §2 : REVÉRIFICATION À LA LECTURE (#54) ────────────────────────────────
        print("\n[2] revérification à la lecture — dépôt courant plus récent → carte périmée")
        # depot_vu=2025-10-26, depot_courant=2025-10-27 : depot_vu < depot_courant → None
        carte_perimee = await lire_carte(
            conn, ticker_id="NVDA", framework_id="qualite_financiere",
            framework_version="v3.0.0", depot_courant="2025-10-27")
        check("§2 depot_courant plus récent que depot_vu → None (carte périmée — #54)",
              carte_perimee is None,
              f"→ carte non None alors que depot_vu=2025-10-26 < depot_courant=2025-10-27")

        # ── §2bis : dépôt identique → carte VALIDE ────────────────────────────────
        print("\n[2bis] dépôt courant identique → carte VALIDE (pas de recalcul inutile)")
        carte_valide = await lire_carte(
            conn, ticker_id="NVDA", framework_id="qualite_financiere",
            framework_version="v3.0.0", depot_courant="2025-10-26")
        check("§2bis depot_courant == depot_vu → carte VALIDE (revérification strictement <)",
              isinstance(carte_valide, AppariementCarte))

        # ── §3 : UPSERT écrase, ne duplique pas ───────────────────────────────────
        print("\n[3] UPSERT sur même clef — écrasement, pas de doublon")
        row_id_2 = await persister_carte(conn, _CARTE_2)
        check("§3 second persister_carte sur même clef rend un id",
              isinstance(row_id_2, int) and row_id_2 > 0)

        nb_apres = await conn.fetchval(
            "SELECT COUNT(*) FROM appariement_cartes "
            "WHERE ticker_id = 'NVDA' AND framework_id = 'qualite_financiere' "
            "AND framework_version = 'v3.0.0'")
        check("§3 UPSERT : toujours exactement 1 ligne (pas de doublon)",
              nb_apres == 1, f"→ {nb_apres} ligne(s)")

        # Après UPSERT, la carte porte le nouveau dépôt.
        carte_apres = await lire_carte(
            conn, ticker_id="NVDA", framework_id="qualite_financiere",
            framework_version="v3.0.0", depot_courant="2026-01-15")
        check("§3 après UPSERT, la carte porte le nouveau dernier_depot_vu",
              carte_apres is not None and carte_apres.dernier_depot_vu == "2026-01-15",
              f"→ {carte_apres.dernier_depot_vu if carte_apres else None}")
        check("§3 après UPSERT, la carte porte le nouvel items (1 item)",
              carte_apres is not None and len(carte_apres.items) == 1,
              f"→ {len(carte_apres.items) if carte_apres else 0}")

        # L'ancienne date est maintenant < nouveau depot_vu : la carte (depot_vu=2026-01-15)
        # est VALIDE sur cet inventaire ancien (2025-10-26 < 2026-01-15, donc depot_vu > depot_courant,
        # donc la condition depot_vu < depot_courant est fausse → carte renvoyée).
        # Mais si on lit avec un dépôt ENCORE plus récent, la nouvelle carte devient périmée.
        carte_nouvelle_perimee = await lire_carte(
            conn, ticker_id="NVDA", framework_id="qualite_financiere",
            framework_version="v3.0.0", depot_courant="2026-02-01")
        check("§3 après UPSERT, un dépôt encore plus récent périme aussi la nouvelle carte",
              carte_nouvelle_perimee is None,
              f"→ carte non None alors que depot_vu=2026-01-15 < depot_courant=2026-02-01")

        # ── §4 : gardes SQL ────────────────────────────────────────────────────────
        print("\n[4] gardes SQL — la base redit les invariants du contrat")
        await _rejette(conn, "§4 base REFUSE items JSON vide (garde items_non_vide)",
                       "INSERT INTO appariement_cartes "
                       "(ticker_id, framework_id, framework_version, dernier_depot_vu, items) "
                       "VALUES ('NVDA', 'qualite_financiere', 'v9.9.9', '2025-01-01', '[]'::jsonb)")

        await _rejette(conn, "§4 base REFUSE dernier_depot_vu au mauvais format (garde depot_format)",
                       "INSERT INTO appariement_cartes "
                       "(ticker_id, framework_id, framework_version, dernier_depot_vu, items) "
                       "VALUES ('NVDA', 'qualite_financiere', 'v9.9.9', '20250101', "
                       "'[{\"question_id\":\"qf_1\",\"ingredient_id\":\"x\","
                       "\"statut\":\"exact\",\"concepts\":[\"NetIncomeLoss\"]}]'::jsonb)")

    finally:
        await tr.rollback()  # AUCUN résidu — la vérification ne pollue pas le réel

    await conn.close()


asyncio.run(run())
print(f"\n{'='*60}\n{ok} vérifications OK, {fail} échec(s)")
sys.exit(1 if fail else 0)
