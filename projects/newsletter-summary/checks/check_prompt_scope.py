#!/usr/bin/env python3
"""Un prompt d'alias ne doit JAMAIS désactiver celui d'un autre alias.

Mode de panne visé : l'ancien `create_version` faisait `UPDATE prompt_versions SET is_active=false`
sans filtre. Avec un prompt par alias, enregistrer une version pour `summary` désactiverait le prompt
de la newsletter — qui retomberait SILENCIEUSEMENT sur le défaut d'env (aucune erreur, un digest
différent le lendemain matin).

Vérifie aussi la compatibilité de l'ancien Hub pendant un déploiement en deux temps : `GET /api/prompt`
sans `alias_id` = le prompt de la newsletter.
"""
import asyncio
import os

import httpx

from _harness import fresh_db, make_alias
from app.database import AsyncSessionLocal
from app.main import app
from app.prompts import activate_version, create_version, get_active_html_prompt, list_versions

HDR = {"x-hub-token": os.environ.get("HUB_API_TOKEN", "")}


async def main():
    default = await fresh_db()
    async with AsyncSessionLocal() as db:
        # ⚠️ Comme en production (v4 ≠ défaut d'env) : le prompt actif de la newsletter DIFFÈRE du défaut
        # d'env. Avec la v1 seedée (== défaut d'env), une désactivation silencieuse serait MASQUÉE par le
        # repli sur ce défaut : check aveugle (constaté par mutation, cf. mutations.py).
        await create_version(db, "PROMPT-NEWS-ACTIF-v4", note="v4", alias_id=None)
        news_before = await get_active_html_prompt(db)          # alias None = défaut
        assert news_before == "PROMPT-NEWS-ACTIF-v4"
        n_versions_news = len(await list_versions(db))
    summary = await make_alias("summary", frequency="minute", allowed_senders="jean@exemple.fr")

    async with AsyncSessionLocal() as db:
        assert await get_active_html_prompt(db, summary.id) == news_before, "prompt d'un alias neuf = copie du prompt newsletter"
        v2 = await create_version(db, "PROMPT-SUMMARY-2", note="test", alias_id=summary.id)
        assert await get_active_html_prompt(db, summary.id) == "PROMPT-SUMMARY-2"
        assert await get_active_html_prompt(db, default.id) == news_before, "le prompt de la newsletter a été désactivé par un autre alias"
        assert [v.is_active for v in await list_versions(db, None)].count(True) == 1, "la version active de la newsletter a été désactivée (masquée par le repli sur le défaut d'env)"
        assert await get_active_html_prompt(db, None) == news_before, "alias_id=None doit rester la newsletter"
        assert len(await list_versions(db, None)) == n_versions_news, "les versions d'un alias ne doivent pas apparaître chez la newsletter"
        assert len(await list_versions(db, summary.id)) == 2

        newsv = (await list_versions(db, None))[0]
        assert await activate_version(db, newsv.id, alias_id=summary.id) is None, "activer la version d'un AUTRE alias doit être refusé"
        assert await get_active_html_prompt(db, summary.id) == "PROMPT-SUMMARY-2", "un refus ne doit rien changer"
        # et l'inverse : éditer la newsletter ne touche pas summary
        await create_version(db, "PROMPT-NEWS-NOUVEAU", alias_id=None)
        assert await get_active_html_prompt(db, summary.id) == "PROMPT-SUMMARY-2", "éditer la newsletter a désactivé le prompt de summary"
        assert await get_active_html_prompt(db, None) == "PROMPT-NEWS-NOUVEAU"
        actives = [v for a in (None, summary.id) for v in await list_versions(db, a) if v.is_active]
        assert len(actives) == 2, f"exactement UNE version active par alias, trouvé {len(actives)}"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/prompt", headers=HDR)               # ancien Hub : pas d'alias_id
        assert r.json()["active_prompt"] == "PROMPT-NEWS-NOUVEAU", "GET /api/prompt sans alias_id doit servir la newsletter"
        r = await c.get(f"/api/prompt?alias_id={summary.id}", headers=HDR)
        assert r.json()["active_prompt"] == "PROMPT-SUMMARY-2"
        r = await c.post("/api/prompt/versions", json={"prompt": "VIA-API", "alias_id": summary.id}, headers=HDR)
        assert r.status_code == 200
        r = await c.get("/api/prompt", headers=HDR)
        assert r.json()["active_prompt"] == "PROMPT-NEWS-NOUVEAU", "POST avec alias_id a touché la newsletter"
    print("OK — une version active par alias ; aucune fuite d'un alias à l'autre ; API rétro-compatible")


asyncio.run(main())
