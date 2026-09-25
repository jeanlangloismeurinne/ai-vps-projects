#!/usr/bin/env python3
"""La migration additive tient sur le VRAI schéma d'avant les alias, et ne perd rien.

`checks/golden/schema_before_aliases.sql` est le `pg_dump -s` des tables `emails` et
`prompt_versions` de PRODUCTION, pris avant le chantier (pas un schéma inventé : `create_all` ne
touche jamais une table existante, seul un vrai ancien schéma révèle un ALTER manquant).

Exigé : les colonnes s'ajoutent, les lignes existantes sont rattachées à la newsletter, le prompt
actif de la newsletter reste actif, le tout est idempotent (redémarrer deux fois = un démarrage).
"""
import asyncio
import re
from pathlib import Path

from sqlalchemy import text

import _harness  # noqa: F401  (chemin)
from app import aliases as al
from app.database import AsyncSessionLocal, engine, init_db
from app.models import Alias
from app.prompts import get_active_html_prompt, seed_default

DDL = (Path(__file__).resolve().parent / "golden" / "schema_before_aliases.sql").read_text()


async def main():
    async with engine.begin() as conn:                        # ancien schéma, tel qu'en prod
        for stmt in [s.strip() for s in DDL.split(";\n") if s.strip()]:
            await conn.exec_driver_sql(stmt)
        await conn.exec_driver_sql(
            "INSERT INTO emails (message_id, from_addr, to_addr, subject, text_body, html_body, received_at, status) "
            "VALUES ('m1','a@x.fr','newsletter@oozeenaru.resend.app','s','t','', now(), 'summarized'),"
            "('m2','b@x.fr','newsletter@oozeenaru.resend.app','s','t','', now(), 'new')")
        await conn.exec_driver_sql(
            "INSERT INTO prompt_versions (created_at, prompt, note, is_active) VALUES "
            "(now(),'ANCIEN-INACTIF','',false),(now(),'ANCIEN-ACTIF','v4',true)")
    async with engine.connect() as conn:
        cols = {r[0] for r in (await conn.exec_driver_sql(
            "select column_name from information_schema.columns where table_name='emails'")).all()}
    assert not ({"alias_id", "attempts", "last_error", "claimed_at"} & cols), "le schéma de départ n'est pas l'ancien"

    for tour in (1, 2):                                       # 2ᵉ tour = redémarrage : idempotence
        await init_db()
        async with AsyncSessionLocal() as db:
            default = await al.seed_default_alias(db)
            await seed_default(db)
        async with engine.connect() as conn:
            cols = {r[0] for r in (await conn.exec_driver_sql(
                "select column_name from information_schema.columns where table_name='emails'")).all()}
            assert {"alias_id", "attempts", "last_error", "claimed_at"} <= cols, f"colonne manquante après migration : {cols}"
            rows = (await conn.exec_driver_sql("select alias_id, attempts, status from emails order by id")).all()
            assert all(r[0] == default.id for r in rows), f"mails non rattachés à la newsletter : {rows}"
            assert [r[1] for r in rows] == [0, 0], "attempts doit valoir 0 sur les lignes existantes"
            assert [r[2] for r in rows] == ["summarized", "new"], "statuts modifiés par la migration"
            pv = (await conn.exec_driver_sql("select prompt, alias_id, is_active from prompt_versions order by id")).all()
            assert all(r[1] == default.id for r in pv), f"versions de prompt non rattachées : {pv}"
            assert [r[2] for r in pv] == [False, True], "le prompt actif doit rester actif"
            n_alias = (await conn.exec_driver_sql("select count(*) from aliases")).scalar_one()
            assert n_alias == 1, f"tour {tour} : {n_alias} alias (le démarrage doit être idempotent)"
        async with AsyncSessionLocal() as db:
            assert await get_active_html_prompt(db) == "ANCIEN-ACTIF", "le prompt de la newsletter a changé à la migration"
            assert default.recipient and default.open_senders and default.is_default and default.frequency == "morning"
    print("OK — migration sur le schéma réel de prod : colonnes ajoutées, lignes rattachées, prompt actif conservé, idempotente")


asyncio.run(main())
