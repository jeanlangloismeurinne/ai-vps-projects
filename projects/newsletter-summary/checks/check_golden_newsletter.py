#!/usr/bin/env python3
"""TEST D'OR — le moteur générique reproduit l'e-mail de la newsletter d'origine, octet pour octet.

Contexte : la newsletter n'est plus un chemin à part, c'est l'alias `is_default`. Le risque du
chantier est de « réécrire un chemin qui marche ». La preuve : `checks/golden/legacy_digest.json`
est la sortie de l'ANCIEN `run_daily_digest` (capturée avant toute modification, sur des lignes
réelles de prod, `legacy_rows.json`). Le moteur générique doit produire le même destinataire, le
même objet, le même texte et le même HTML.

Les 5 lignes couvrent les 3 branches du rendu : carte normale (×3 vraies newsletters), corps jamais
rapatrié (carte « Corps non reçu »), résumé en échec (carte d'erreur).

Lancer :  projects/newsletter-summary/checks/run.sh checks/check_golden_newsletter.py
"""
import asyncio
import json

from _harness import ERROR_MARKER, GOLDEN, Doubles, alias_digest, add_email, fresh_db, get_email


async def main():
    rows = json.loads((GOLDEN / "legacy_rows.json").read_text())
    golden = json.loads((GOLDEN / "legacy_digest.json").read_text())
    d = Doubles().install()
    default = await fresh_db()
    ids = [await add_email(default.id, frm=r["from_addr"], to=r["to_addr"], subject=r["subject"],
                           body="corps présent" if r["has_body"] else "", received=r["received_at"],
                           message_id=f"golden-{i}") for i, r in enumerate(rows)]

    report = await alias_digest.run_alias_digests("morning")

    assert len(d.gateway.sent) == 1, f"un seul e-mail de lot attendu, reçu {len(d.gateway.sent)} — rapport {report}"
    got = d.gateway.sent[0]
    assert got["to"] == golden["to"], f"destinataire : {got['to']!r} ≠ {golden['to']!r}"
    assert got["subject"] == golden["subject"], f"objet : {got['subject']!r} ≠ {golden['subject']!r}"
    # Seul écart VOLONTAIRE avec le legacy : le corps texte d'une carte en échec nomme le motif au lieu de
    # « (vide) » (constaté en exécution réelle : un mail-lien refusé arrivait « (vide) » en texte brut).
    # L'écart est déclaré ici et auto-vérifié : il doit exister EXACTEMENT une fois dans la fixture.
    legacy_vide = f"Résumé en échec {ERROR_MARKER}\n\n(vide)"
    assert golden["body"].count(legacy_vide) == 1, "fixture : le bloc « (vide) » de la carte en échec est introuvable"
    expected_body = golden["body"].replace(legacy_vide, f"Résumé en échec {ERROR_MARKER}\n\n⚠ Résumé en échec — DeepInfra simulé indisponible")
    assert got["body"] == expected_body, "corps TEXTE différent du legacy (hors l'écart déclaré sur les cartes en échec)"
    assert got["html"] == golden["html"], "corps HTML différent du legacy"

    # Ce que la base retient est plus fidèle que l'ancien « tout summarized » : le corps absent et
    # le résumé en échec sont NOMMÉS (`failed` + `last_error`), leurs cartes ayant bien été envoyées.
    st = [(await get_email(i)).status for i in ids]
    assert st == ["summarized", "summarized", "summarized", "failed", "failed"], f"statuts : {st}"
    assert "corps du mail absent" in (await get_email(ids[3])).last_error
    assert "DeepInfra simulé indisponible" in (await get_email(ids[4])).last_error
    print(f"OK — e-mail identique au legacy ({len(got['html'])} car. HTML, {len(got['body'])} car. texte) ; statuts {st}")


asyncio.run(main())
