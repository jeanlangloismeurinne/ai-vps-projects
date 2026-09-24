"""Le correctif #81 EN CONDITIONS RÉELLES — le fournisseur répond, et rien de non fini ne survit.

Pendant de `check_cours_cote.py`, qui prouve la RÈGLE hors ligne sur des séries fabriquées.
Celui-ci prouve le CHEMIN : un `refresh_m1` réel, contre le vrai fournisseur, à travers le vrai
`DataService`, jusqu'à la vraie écriture PostgreSQL. Un correctif de forme n'est pas acquis tant
qu'il n'a pas tourné contre le vrai fournisseur (`feedback_verifier_contre_api_reelle`) : c'était
exactement le cas ici, le défaut d'origine ne se voyait qu'à l'écriture, APRÈS que l'appel réseau
avait été payé.

Il sort du périmètre hors-ligne de `run_all.sh` (réseau ouvert + clé fournisseur + écriture DB
réelle), au même titre que `check_fetch_live` et `check_fetch_relevance` :

    docker exec portfolio-backend python /app/checks/check_cours_cote_live.py

TROIS ISSUES, JAMAIS DEUX. La garde « aucun non fini ne survit » est structurellement incapable de
distinguer « le filet a retenu quelque chose » de « il n'y avait rien à retenir » : dans les deux
cas elle est verte. Or ces deux mondes n'ont pas la même valeur de preuve — le second ne prouve
rien du correctif, il prouve seulement que le fournisseur allait bien ce jour-là. Quand le faux
positif est indiscernable structurellement, on change la FORME de la réponse plutôt que de muscler
la garde (`feedback_garde_structure_pas_sens`, #68). D'où trois issues nommées par titre :

  · ASSAINI          — des champs non finis SONT arrivés et le filet les a nommés et écartés.
                       C'est la seule issue qui prouve le correctif sur le chemin réel.
  · RIEN_A_ASSAINIR  — le fournisseur a rendu une charge propre. Le chemin est sain, le correctif
                       n'est PAS exercé. À dire, pas à taire.
  · FAIL             — un non fini a survécu au guichet, ou `refresh_m1` a levé. Régression.

Le bilan distingue donc `exercé` de `vert`. Un `RIEN_A_ASSAINIR` sur les trois titres sort en 0
(rien n'est cassé) mais l'annonce en clair : le jour où l'on s'appuie dessus pour dire « #81 est
prouvé en réel », la ligne de bilan contredit la phrase.

ANCRE NON CIRCULAIRE. Les trois titres sont ceux sur lesquels le défaut a été MESURÉ le
2026-09-23, avec la même forme sur les trois — donc le fournisseur, pas le titre. Ils ne sont pas
choisis pour être commodes (`feedback_fixture_copiee_du_reel`).

DÉGRADER, JAMAIS SAUTER. Sans clé fournisseur ou sans base, le script sort en ÉCHEC et ne saute
pas la section : une mesure incomplète ne doit jamais s'écrire comme un 0
(`feedback_check_degrade_en_sortant_a_zero`).
"""
import asyncio
import json
import logging
import math
import sys

TITRES = ("MSFT", "NVDA", "RVMD")


def _non_finis(prefixe, obj, out):
    """Recense les chemins portant un float non fini. Miroir indépendant de `_assainir_non_finis`.

    Volontairement réécrit ici plutôt qu'importé : une garde nourrie de la fonction qu'elle vérifie
    est verte par construction (`feedback_test_negatif_trois_faux_verts`).
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            _non_finis(f"{prefixe}.{k}", v, out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _non_finis(f"{prefixe}[{i}]", v, out)
    elif isinstance(obj, float) and not math.isfinite(obj):
        out.append(prefixe)


class _Mouchard(logging.Handler):
    """Capte les `logger.warning` de `_assainir_non_finis` — c'est lui qui NOMME ce qui est tombé."""

    def __init__(self):
        super().__init__(level=logging.WARNING)
        self.lignes = []

    def emit(self, record):
        if "non finis écartés" in record.getMessage():
            self.lignes.append(record.getMessage())


async def main():
    from app.config import settings
    from app.db.database import init_pool, close_pool
    from app.data_collection.data_cache import init_redis, close_redis
    from app.data_collection.data_service import DataService

    if not getattr(settings, "FMP_API_KEY", None):
        print("check_cours_cote_live : FMP_API_KEY absente — mesure IMPOSSIBLE, pas 0 vérification.")
        return 2

    mouchard = _Mouchard()
    logging.getLogger("app.data_collection.data_service").addHandler(mouchard)

    await init_pool(settings.DATABASE_URL)
    await init_redis(settings.REDIS_URL)

    svc = DataService()
    ok = fail = 0
    exerce = 0

    for t in TITRES:
        avant = len(mouchard.lignes)
        try:
            data = await svc.refresh_m1(t, settings.FMP_API_KEY, context="check_cours_cote_live")
        except Exception as e:
            print(f"  {t:<6} FAIL   refresh_m1 a levé : {type(e).__name__}: {e}")
            fail += 1
            continue

        survivants = []
        _non_finis("m1", data, survivants)

        # La preuve littérale de ce que PostgreSQL exigeait : `NaN` est un jeton JSON illégal.
        try:
            json.dumps(data, allow_nan=False)
            serialisable = True
        except ValueError:
            serialisable = False

        tombes = mouchard.lignes[avant:]

        if survivants or not serialisable:
            print(f"  {t:<6} FAIL   {len(survivants)} non fini(s) au guichet {survivants[:5]} "
                  f"| json_strict={'ok' if serialisable else 'REFUSÉ'}")
            fail += 1
            continue

        ok += 1
        px = (data or {}).get("price")
        if tombes:
            exerce += 1
            print(f"  {t:<6} ASSAINI          price={px!r} | {tombes[0]}")
        else:
            print(f"  {t:<6} RIEN_A_ASSAINIR  price={px!r} | charge fournisseur propre")

    await close_redis()
    await close_pool()

    print(f"\n  titres exercés (un non fini est réellement arrivé) : {exerce}/{len(TITRES)}")
    if fail == 0 and exerce == 0:
        print("  ⚠️  vert mais NON EXERCÉ — le fournisseur allait bien ; #81 n'est pas prouvé en réel aujourd'hui.")
    print(f"\ncheck_cours_cote_live : {ok} ok / {fail} FAIL")
    return 1 if fail else 0


sys.exit(asyncio.run(main()))
