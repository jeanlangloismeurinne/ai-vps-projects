#!/usr/bin/env python3
"""Comportement du moteur unique : cadences, lots, réservation, plafond, échecs nommés, mails-lien.

Gateway et LLM sont simulés (`_harness.py`) ; la base, la réservation SQL, le regroupement, les
tentatives et le rendu sont RÉELS. Chaque scénario porte l'exigence qu'il protège.

  S0  plafond quotidien          — le quota gateway (60/j) est partagé avec le digest newsletter
  S1  cadence `minute`           — UN e-mail PAR mail reçu, jamais de concaténation
  S2  cadences `morning`         — un lot par destinataire ; chaque cadence ne touche que les siens
  S3  admission au traitement    — un expéditeur non autorisé n'atteint ni le LLM ni la réponse
  S4  réservation concurrente    — deux runs qui se chevauchent n'envoient jamais deux fois un mail
  S5  échec LLM (minute)         — tentatives bornées PUIS carte d'erreur nommée envoyée ; jamais muet
  S6  échec d'envoi              — tentatives bornées PUIS `failed` nommé
  S7  corps absent (minute)      — on laisse à Resend le temps d'indexer, puis carte de repli tracée
  S8  run interrompu             — les `processing` orphelins sont récupérés, les récents laissés
  S9  mail réduit à un lien      — la page est résumée ; « phrase + lien » ne l'est PAS ; échec nommé
  S10 KB                         — chaque résumé est écrit avec le nom de l'alias
"""
import asyncio

from _harness import ERROR_MARKER, Doubles, add_email, alias_digest, fresh_db, get_email, make_alias, sql
from app import urlfetch
from app.config import settings

CARD = "border-radius:8px;padding:16px 18px"   # ouverture d'une carte (rendue par le code)
JEAN, MARIE = "jean@exemple.fr", "marie@exemple.fr"


async def statuses(ids):
    return [(await get_email(i)).status for i in ids]


async def main():
    d = Doubles().install()
    default = await fresh_db()
    both = f"{JEAN}\n{MARIE}"

    # ── S0 plafond : exécuté EN PREMIER (le compteur du jour est global aux alias à liste blanche) ──
    settings.ALIAS_MAX_PER_DAY = 2
    cap = await make_alias("plafond", frequency="minute", allowed_senders=JEAN)
    ids = [await add_email(cap.id, frm=JEAN, subject=f"P{i}") for i in range(4)]
    await alias_digest.run_alias_digests("minute")
    st = await statuses(ids)
    assert st == ["summarized", "summarized", "rejected", "rejected"], f"S0 plafond de 2/jour : {st}"
    assert "plafond" in (await get_email(ids[2])).last_error, "S0 : le refus doit nommer le plafond"
    assert len(d.gateway.sent) == 2, f"S0 : {len(d.gateway.sent)} envois (2 attendus)"
    settings.ALIAS_MAX_PER_DAY = 40
    d.gateway.sent.clear()

    # ── S1 minute : 1 mail = 1 e-mail ──
    summary = await make_alias("summary", frequency="minute", allowed_senders=both)
    ids = [await add_email(summary.id, frm=JEAN, subject=f"S1-{i}") for i in range(3)]
    ids.append(await add_email(summary.id, frm=f"Marie <{MARIE.upper()}>", subject="S1-marie"))
    # mails d'autres cadences, présents en même temps : ils ne doivent pas être touchés par `minute`
    daily = await make_alias("daily", frequency="morning", allowed_senders=both)
    later = [await add_email(daily.id, frm=JEAN, subject=f"D{i}") for i in range(3)]
    later.append(await add_email(daily.id, frm=MARIE, subject="D-marie"))
    soir = await make_alias("soir", frequency="evening", allowed_senders=JEAN)
    evening = [await add_email(soir.id, frm=JEAN, subject="E0")]

    await alias_digest.run_alias_digests("minute")
    sent = d.gateway.sent
    assert len(sent) == 4, f"S1 : 4 mails → 4 e-mails séparés, reçu {len(sent)} (concaténation ?)"
    assert sorted(m["to"] for m in sent) == [JEAN, JEAN, JEAN, MARIE], f"S1 : réponse à l'expéditeur : {[m['to'] for m in sent]}"
    for m in sent:
        assert m["html"].count(CARD) == 1, f"S1 : {m['subject']} contient {m['html'].count(CARD)} cartes (1 attendue)"
    assert {m["subject"] for m in sent} == {f"📬 Résumé : S1-{i}" for i in range(3)} | {"📬 Résumé : S1-marie"}, [m["subject"] for m in sent]
    assert await statuses(ids) == ["summarized"] * 4
    assert await statuses(later + evening) == ["new"] * 5, "S1 : la cadence `minute` a touché des mails matin/soir"
    d.gateway.sent.clear()

    # ── S2 morning : un lot par destinataire ; `evening` ne touche pas au matin ──
    await alias_digest.run_alias_digests("evening")
    assert len(d.gateway.sent) == 1 and await statuses(later) == ["new"] * 4, "S2 : le run du soir a touché des mails du matin"
    d.gateway.sent.clear()
    await alias_digest.run_alias_digests("morning")
    by_to = {m["to"]: m for m in d.gateway.sent}
    assert len(d.gateway.sent) == 2 and set(by_to) == {JEAN, MARIE}, f"S2 : un lot par destinataire attendu, reçu {[m['to'] for m in d.gateway.sent]}"
    assert by_to[JEAN]["html"].count(CARD) == 3 and by_to[MARIE]["html"].count(CARD) == 1, "S2 : cartes par lot"
    assert by_to[JEAN]["subject"] == "📬 Résumé — 3 mail(s) — Friday 25 September 2026", by_to[JEAN]["subject"]
    assert await statuses(later) == ["summarized"] * 4
    d.gateway.sent.clear()

    # ── S3 admission au traitement (webhook : From vide, rapatrié plus tard) ──
    calls = d.summarize_calls
    stranger = await add_email(summary.id, frm="intrus@spam.example", subject="S3")
    await alias_digest.run_alias_digests("minute")
    e = await get_email(stranger)
    assert e.status == "rejected" and "non autorisé" in e.last_error, f"S3 : {(e.status, e.last_error)}"
    assert d.summarize_calls == calls and not d.gateway.sent, "S3 : un expéditeur refusé a atteint le LLM ou reçu une réponse"

    # ── S4 réservation concurrente ──
    race = await make_alias("course", frequency="minute", allowed_senders=JEAN)
    ids = [await add_email(race.id, frm=JEAN, subject=f"R{i}") for i in range(5)]
    d.gateway.delay = 0.05
    await asyncio.gather(alias_digest.run_alias_digests("minute"), alias_digest.run_alias_digests("minute"))
    d.gateway.delay = 0
    subs = sorted(m["subject"] for m in d.gateway.sent)
    assert subs == sorted(f"📬 Résumé : R{i}" for i in range(5)), f"S4 : doublons ou pertes entre runs concurrents : {subs}"
    d.gateway.sent.clear()

    # ── S5 échec LLM en cadence minute : tentatives bornées, puis carte d'erreur NOMMÉE ──
    flaky = await make_alias("fragile", frequency="minute", allowed_senders=JEAN)
    i5 = await add_email(flaky.id, frm=JEAN, subject=f"S5 {ERROR_MARKER}")
    for tour in (1, 2):
        await alias_digest.run_alias_digests("minute")
        e = await get_email(i5)
        assert (e.status, e.attempts) == ("new", tour) and not d.gateway.sent, f"S5 tour {tour} : {(e.status, e.attempts)}, envois {len(d.gateway.sent)}"
    await alias_digest.run_alias_digests("minute")
    e = await get_email(i5)
    assert e.status == "failed" and "DeepInfra simulé indisponible" in e.last_error, f"S5 : {(e.status, e.last_error)}"
    assert len(d.gateway.sent) == 1 and "⚠ Résumé en échec — DeepInfra simulé indisponible" in d.gateway.sent[0]["html"], \
        "S5 : à l'épuisement des tentatives l'expéditeur doit recevoir une carte d'erreur NOMMÉE (jamais le silence)"
    d.gateway.sent.clear()

    # ── S6 échec d'envoi : tentatives bornées puis `failed` nommé ──
    sf = await make_alias("panne", frequency="minute", allowed_senders=JEAN)
    i6 = await add_email(sf.id, frm=JEAN, subject="S6")
    d.gateway.fail = True
    for tour in (1, 2, 3):
        await alias_digest.run_alias_digests("minute")
    e = await get_email(i6)
    assert e.status == "failed" and e.last_error.startswith("envoi :") and "gateway simulé indisponible" in e.last_error, f"S6 : {(e.status, e.last_error)}"
    d.gateway.fail = False
    await alias_digest.run_alias_digests("minute")
    assert not d.gateway.sent and (await get_email(i6)).status == "failed", "S6 : un mail `failed` ne doit pas repartir en boucle"

    # ── S7 corps absent en cadence minute ──
    nb = await make_alias("tot", frequency="minute", allowed_senders=JEAN)
    i7 = await add_email(nb.id, frm=JEAN, subject="S7", body="")
    for tour in (1, 2):
        await alias_digest.run_alias_digests("minute")
        assert (await get_email(i7)).status == "new" and not d.gateway.sent, f"S7 tour {tour} : doit attendre le corps"
    await alias_digest.run_alias_digests("minute")
    e = await get_email(i7)
    assert e.status == "failed" and "corps du mail absent" in e.last_error and len(d.gateway.sent) == 1, f"S7 : {(e.status, e.last_error)}"
    assert "Corps non reçu" in d.gateway.sent[0]["body"], "S7 : la carte de repli d'origine doit partir, pas le silence"
    d.gateway.sent.clear()

    # ── S8 run interrompu ──
    orphan = await add_email(summary.id, frm=JEAN, subject="S8-orphelin", status="processing")
    fresh = await add_email(summary.id, frm=JEAN, subject="S8-en-cours", status="processing")
    await sql("update emails set claimed_at = now() at time zone 'utc' - interval '20 minutes' where id = :i", i=orphan)
    await sql("update emails set claimed_at = now() at time zone 'utc' - interval '1 minute' where id = :i", i=fresh)
    await alias_digest.run_alias_digests("minute")
    assert (await get_email(orphan)).status == "summarized", "S8 : un `processing` orphelin doit être récupéré puis traité"
    assert (await get_email(fresh)).status == "processing", "S8 : un `processing` récent (autre run en cours) ne doit pas être volé"
    assert (await get_email(orphan)).attempts == 1, "S8 : la récupération doit compter une tentative (mail empoisonné)"
    d.gateway.sent.clear()

    # ── S9 mail réduit à un lien ──
    real_fetch = urlfetch.fetch_page
    fetched: list[str] = []

    async def fake_fetch(url, **kw):
        fetched.append(url)
        if "bloque" in url:
            raise urlfetch.UrlFetchError("page bloquée (403)")
        if "lent" in url:
            raise urlfetch.UrlFetchError("délai dépassé en récupérant la page", permanent=False)
        return urlfetch.FetchedPage(url=url, title="Titre de la page", text="Contenu de l'article. " * 20)

    urlfetch.fetch_page = fake_fetch
    lk = await make_alias("lien", frequency="minute", allowed_senders=JEAN)
    i_url = await add_email(lk.id, frm=JEAN, subject="Fwd", body="  https://exemple.org/article  \n")
    i_txt = await add_email(lk.id, frm=JEAN, subject="Avec du texte", body="Regarde ça https://exemple.org/autre")
    i_403 = await add_email(lk.id, frm=JEAN, subject="Bloquée", body="https://exemple.org/bloque")
    await alias_digest.run_alias_digests("minute")
    assert fetched == ["https://exemple.org/article", "https://exemple.org/bloque"], f"S9 : pages récupérées {fetched} (« phrase + lien » ne doit PAS l'être)"
    assert d.seen_plain[i_url].startswith("Contenu de l'article."), "S9 : le LLM doit recevoir le texte de la PAGE"
    assert d.seen_plain[i_txt] == "Regarde ça https://exemple.org/autre", "S9 : un mail avec du texte est résumé tel quel"
    by_sub = {m["subject"]: m for m in d.gateway.sent}
    card = next(m for m in d.gateway.sent if "Titre de la page" in m["html"])
    assert "https://exemple.org/article" in card["html"], "S9 : l'en-tête de carte doit afficher l'URL"
    err = next(m for m in d.gateway.sent if "page bloquée (403)" in m["html"])
    assert "⚠ Résumé en échec — page bloquée (403)" in err["html"], "S9 : échec permanent = carte d'erreur immédiate, raison nommée"
    e = await get_email(i_403)
    assert e.status == "failed" and e.last_error == "page bloquée (403)" and e.attempts == 0, f"S9 : {(e.status, e.last_error, e.attempts)}"
    d.gateway.sent.clear()
    i_lent = await add_email(lk.id, frm=JEAN, subject="Lente", body="https://exemple.org/lent")
    await alias_digest.run_alias_digests("minute")
    e = await get_email(i_lent)
    assert (e.status, e.attempts) == ("new", 1) and not d.gateway.sent, "S9 : échec transitoire de page → nouvelle tentative, pas d'erreur définitive"
    urlfetch.fetch_page = real_fetch

    # ── S10 KB : le nom de l'alias est noté ──
    kb = {(k["alias"], k["source_url"]) for k in d.kb}
    assert ("summary", None) in kb and ("lien", "https://exemple.org/article") in kb, f"S10 : écritures KB {sorted(kb, key=str)}"
    assert all(k["alias"] for k in d.kb), "S10 : une écriture KB sans nom d'alias"
    print("OK — S0-S10 : cadences, lots, réservation, plafond, échecs nommés, récupération, mails-lien, KB")


asyncio.run(main())
