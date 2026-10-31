#!/usr/bin/env python3
"""Pilotage des règles de transfert Gmail : backend de bout en bout contre un FAUX script Apps Script.

Ce qui est réel : la base (jetable), le client signé, la validation, la réconciliation, les routes FastAPI
(via le vrai `app`), le journal, les alertes (gateway simulé). Ce qui est simulé : le script Apps Script et
Gmail — `FakeScript` ci-dessous rejoue le CONTRAT (docs/gmail-forward/SPEC.md) ; son comportement réel est
éprouvé séparément par apps-script/test/run.js. Un faux script ne prouve donc PAS que Gmail se comporte ainsi :
c'est la recette sur compte de test qui le prouve (docs/gmail-forward/RECETTE.md).

Scénarios G0… : chaque assert porte son numéro, que checks/mutations.py exige dans la sortie.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import time

import httpx

from _harness import Doubles, fresh_db, make_alias  # noqa: F401  (chemin + doublures)
from app import gmail_client, gmail_rules as gr
from app.config import settings
from app.database import AsyncSessionLocal
from app.main import app
from app.models import GmailAudit, GmailRule, GmailSetting
from sqlalchemy import select, text

SECRET = "a" * 64
URL = "https://script.google.com/macros/s/AKfycbx-URL-SECRETE/exec"
DEST = "veille@oozeenaru.resend.app"
DEST2 = "secteur@oozeenaru.resend.app"


class FakeScript:
    """Rejoue le contrat du script : signature, fenêtre, nonce, idempotence, create-puis-delete, not_managed."""

    def __init__(self):
        self.secret = SECRET
        self.filters: list[dict] = []
        self.managed: dict[str, str] = {}
        self.forwarding = [{"email": DEST, "status": "accepted"}, {"email": DEST2, "status": "accepted"},
                           {"email": "attente@oozeenaru.resend.app", "status": "pending"}]
        self.nonces: set[str] = set()
        self.calls: list[str] = []
        self.seq = 0
        self.fail_remove_once = False
        self.timeout_next = False       # la requête est traitée PUIS la réponse se perd
        self.forge_next = False         # la requête est traitée, la réponse est signée avec un autre secret
        self.refuse_next: str | None = None
        self.wrong_nonce_next = False
        self.down = False

    def sig(self, msg, secret=None):
        return hmac.new((secret or self.secret).encode(), msg.encode(), hashlib.sha256).hexdigest()

    def _out(self, nonce, ok, body, secret=None):
        if ok:
            s = json.dumps(body, separators=(",", ":"))
            return {"ok": True, "result": s, "nonce": nonce, "sig": self.sig(f"{nonce}.true.{s}", secret)}
        return {"ok": False, "error": {"code": body, "message": body}, "nonce": nonce,
                "sig": self.sig(f"{nonce}.false.{body}", secret)}

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("injoignable")
        req = json.loads(request.content)
        expected = self.sig(".".join([str(req["v"]), str(req["ts"]), req["nonce"], req["action"], req["payload"]]))
        if not hmac.compare_digest(expected, req.get("sig", "")):
            return httpx.Response(200, json={"ok": False, "error": {"code": "bad_signature", "message": "Signature invalide"}})
        nonce, action, p = req["nonce"], req["action"], json.loads(req["payload"] or "{}")
        if abs(time.time() - req["ts"]) > 60:
            return httpx.Response(200, json=self._out(nonce, False, "stale_timestamp"))
        if nonce in self.nonces:
            return httpx.Response(200, json=self._out(nonce, False, "replayed_nonce"))
        self.nonces.add(nonce)
        self.calls.append(action)
        if self.refuse_next:
            code, self.refuse_next = self.refuse_next, None
            return httpx.Response(200, json=self._out(nonce, False, code))
        try:
            result = getattr(self, "do_" + action)(p)
            body = self._out(nonce, True, result)
        except KeyError as exc:
            body = self._out(nonce, False, str(exc.args[0]))
        if self.timeout_next:
            self.timeout_next = False
            raise httpx.ReadTimeout("délai dépassé")
        if self.forge_next:
            self.forge_next = False
            body = self._out(nonce, True, json.loads(body["result"]) if body["ok"] else {}, secret="f" * 64) if body["ok"] \
                else self._out(nonce, False, json.loads(json.dumps(body["error"]["code"])), secret="f" * 64)
        if self.wrong_nonce_next:
            self.wrong_nonce_next = False
            body = {**body, "nonce": "0" * 16}   # signature légitime, mais d'un autre échange
        return httpx.Response(200, json=body)

    def do_ping(self, p):
        return {"version": "1.1.0", "time": "2026-10-31T10:00:00Z", "enabled": True}

    def do_list_forwarding_addresses(self, p):
        return self.forwarding

    def do_list_rules(self, p):
        return [{"id": f["id"], "managed": f["id"] in self.managed, "client_request_id": self.managed.get(f["id"]),
                 "criteria": f["criteria"], "action": f["action"]}
                for f in self.filters if f["id"] in self.managed or p.get("include_foreign")]

    def _insert(self, p, replacing=None):
        crid = p["client_request_id"]
        for fid, c in self.managed.items():
            if c == crid:
                return {"gmail_filter_id": fid, "replayed": True}
        dest = p["destination"]
        if not any(a["email"] == dest and a["status"] == "accepted" for a in self.forwarding):
            raise KeyError("destination_not_verified")
        self.seq += 1
        crit = {k: v for k, v in (("from", p.get("from")), ("subject", p.get("subject_contains"))) if v}
        f = {"id": f"F{self.seq}", "criteria": crit, "action": {"forward": dest}}
        if p.get("skip_inbox"):
            f["action"]["removeLabelIds"] = ["INBOX"]
        self.filters.append(f)
        self.managed[f["id"]] = crid
        return {"gmail_filter_id": f["id"]}

    def do_create_rule(self, p):
        return self._insert(p)

    def _remove(self, fid):
        if self.fail_remove_once:
            self.fail_remove_once = False
            raise KeyError("internal")
        self.filters = [f for f in self.filters if f["id"] != fid]
        self.managed.pop(fid, None)

    def do_replace_rule(self, p):
        old = p["gmail_filter_id"]
        if old not in self.managed:
            raise KeyError("not_managed")
        res = self._insert(p, old)
        self._remove(old)
        return res

    def do_delete_rule(self, p):
        if p["gmail_filter_id"] not in self.managed:
            raise KeyError("not_managed")
        self._remove(p["gmail_filter_id"])
        return {"deleted": True}

    def by_from(self, frm):
        return [f for f in self.filters if f["criteria"].get("from") == frm]


async def rules_by_from(frm=None):
    async with AsyncSessionLocal() as db:
        return [r for r in await gr.list_rules(db) if frm is None or r.from_addr == frm]


async def rule(rid):
    async with AsyncSessionLocal() as db:
        return await db.get(GmailRule, rid)


async def new(frm="news@exemple.com", **kw):
    async with AsyncSessionLocal() as db:
        data = {"name": "N", "from": frm, "destination": DEST, **kw}
        r, w = await gr.create_rule(db, data, confirm_broad=kw.pop("confirm_broad", False) if False else data.pop("confirm_broad", False))
        return r, w


def refused(code, tag):
    class Ctx:
        def __enter__(self):
            return self

        def __exit__(self, et, ev, tb):
            assert et is gr.RuleError, f"{tag} : refus {code} attendu, obtenu {et}"
            assert ev.code == code, f"{tag} : code {code} attendu, obtenu {ev.code}"
            return True
    return Ctx()


async def main():
    class Collect(logging.Handler):
        def __init__(self):
            super().__init__()
            self.lines = []

        def emit(self, rec):
            self.lines.append(rec.getMessage())

    logs = Collect()
    logging.disable(logging.NOTSET)
    logging.getLogger().addHandler(logs)
    logging.getLogger().setLevel(logging.INFO)

    d = Doubles().install()
    await fresh_db()
    await make_alias("veille", frequency="morning", allowed_senders="news@exemple.com")
    await make_alias("secteur", frequency="minute", open_senders=True)
    fake = FakeScript()
    gr._transport = httpx.MockTransport(fake.handle)
    settings.GMAIL_SCRIPT_URL, settings.GMAIL_SCRIPT_SECRET = URL, SECRET
    settings.DENY_FROM, settings.DEST_ALLOWED_DOMAINS = "banque.fr,cabinet.com", "oozeenaru.resend.app"

    # ── G0 : le format de signature est celui du script (vecteurs calculés avec le HMAC de Node, cf. apps-script) ──
    assert gmail_client.sign("a" * 64, 1, 1761900000, "9f3a1c0b5d7e2a48", "create_rule", '{"from":"é@x.fr"}') == \
        "d43a79cbc17965626fe04b6acde226fb4ee1272b51ebc87eb41c3ea9cd74a9e7", "G0 : signature de requête ≠ celle du script"
    assert gmail_client._response_sig("a" * 64, "9f3a1c0b5d7e2a48", True, '{"a":1}') == \
        "06265d66e5dbcea14dd7d0e28b51a484d57edbb5b5db2275a96127a40dee8b15", "G0 : signature de réponse ≠ celle du script"

    # ── G1 : refus de validation, AVANT tout appel au script ──
    n0 = len(fake.calls)
    async with AsyncSessionLocal() as db:
        for frm, kw, code, why in [
            ("*", {}, "criteria_too_broad", "joker"), ("@com", {}, "criteria_too_broad", "domaine nu"),
            ("@co.uk", {}, "criteria_too_broad", "suffixe public (@co.uk)"), ("@org.uk", {}, "criteria_too_broad", "suffixe public"),
            ("x@banque.fr", {}, "criteria_too_broad", "DENY_FROM"), ("@mail.banque.fr", {}, "criteria_too_broad", "sous-domaine de DENY_FROM"),
            ("pas une adresse", {}, "criteria_too_broad", "adresse mal formée"),
            ("", {"subject_contains": "court"}, "criteria_too_broad", "sujet de 5 caractères sans expéditeur"),
            ("", {}, "criteria_too_broad", "ni expéditeur ni sujet"),
            ("a@exemple.com", {"destination": "x@evil.example"}, "destination_not_allowed", "hors liste blanche de domaines"),
            ("a@exemple.com", {"subject_contains": "a<b"}, "invalid_field", "caractère interdit dans le sujet"),
            ("", {"subject_contains": "Newsletter hebdo"}, "confirmation_required", "règle large sans confirmation"),
        ]:
            with refused(code, f"G1 ({why})"):
                await gr.create_rule(db, {"name": "x", "from": frm, "destination": DEST, **kw})
    assert len(fake.calls) == n0 and not await rules_by_from(), "G1 : un refus de validation ne doit ni appeler le script ni écrire en base"
    ok_domain, _ = await new("@exemple.org")   # un domaine entier ordinaire est accepté
    assert ok_domain.sync_status == "synced" and len(fake.by_from("@exemple.org")) == 1, "G1 : domaine entier ordinaire refusé à tort"

    # ── G2 : création, état et journal ──
    r, warns = await new("news@exemple.com", skip_inbox=True)
    assert r.sync_status == "synced" and r.gmail_filter_id and r.pending_op is None, f"G2 : règle non synced après succès ({r.sync_status})"
    assert fake.filters[-1]["action"] == {"forward": DEST, "removeLabelIds": ["INBOX"]}, "G2 : filtre Gmail ≠ règle"
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(GmailAudit).where(GmailAudit.rule_id == r.id))).scalars().all()
    assert [a.action for a in rows] == ["create_rule"] and rows[0].ok and rows[0].payload_hash and len(rows[0].payload_hash) == 16, \
        "G2 : une ligne d'audit create_rule avec empreinte attendue"

    # ── G3 : doublon (triplet), plafonds ──
    with refused("duplicate", "G3 (doublon)"):
        async with AsyncSessionLocal() as db:
            await gr.create_rule(db, {"name": "bis", "from": "news@exemple.com", "destination": DEST})
    async with AsyncSessionLocal() as db:
        for i in range(gr.MAX_SENDERLESS):
            await gr.create_rule(db, {"name": f"l{i}", "from": "", "subject_contains": f"Sujet large {i}", "destination": DEST}, confirm_broad=True)
        with refused("rule_limit", "G3 (plafond sans expéditeur)"):
            await gr.create_rule(db, {"name": "l6", "from": "", "subject_contains": "Sujet large 6", "destination": DEST}, confirm_broad=True)
        for i in range(gr.MAX_RULES - len(await gr.list_rules(db))):
            await gr.create_rule(db, {"name": f"f{i}", "from": f"s{i}@filler.example", "destination": DEST})
        with refused("rule_limit", "G3 (plafond 50)"):
            await gr.create_rule(db, {"name": "51", "from": "de-trop@filler.example", "destination": DEST})
        # désactiver libère une place d'« active » : le plafond compte les règles ACTIVES
        extra = (await gr.list_rules(db))[0]
        await gr.set_enabled(db, extra.id, False)
        await gr.create_rule(db, {"name": "51", "from": "de-trop@filler.example", "destination": DEST})
        await gr.set_enabled(db, extra.id, False)
    # on fait de la place pour la suite : suppression de tout ce qui n'est pas nécessaire
    async with AsyncSessionLocal() as db:
        for x in await gr.list_rules(db):
            if x.id != r.id and x.from_addr != "@exemple.org":
                await gr.remove_rule(db, x.id)
    assert {x.id for x in await rules_by_from()} == {r.id, ok_domain.id}, "G3 : nettoyage incomplet"

    # ── G4 : réponse falsifiée → rien n'est cru ; le rejeu idempotent n'ajoute pas de second filtre ──
    fake.forge_next = True
    r2, _ = await new("forge@exemple.com")
    assert r2.sync_status == "pending" and r2.gmail_filter_id is None and "rejetée" in r2.last_error, \
        f"G4 : signature de réponse fausse mais règle {r2.sync_status}"
    assert len(fake.by_from("forge@exemple.com")) == 1, "G4 : (le faux script a bien créé le filtre, réponse perdue)"
    async with AsyncSessionLocal() as db:
        again = await gr.retry_rule(db, r2.id)
    assert again.sync_status == "synced" and len(fake.by_from("forge@exemple.com")) == 1 and again.gmail_filter_id == fake.by_from("forge@exemple.com")[0]["id"], \
        "G4 : « Réessayer » avec le même client_request_id doit retrouver le filtre, pas en créer un second"

    fake.wrong_nonce_next = True
    r2b, _ = await new("nonce@exemple.com")
    assert r2b.sync_status == "pending" and r2b.gmail_filter_id is None, f"G4 : réponse d'un autre échange (nonce ≠) crue : {r2b.sync_status}"
    async with AsyncSessionLocal() as db:
        r2b = await gr.retry_rule(db, r2b.id)
    assert r2b.sync_status == "synced" and len(fake.by_from("nonce@exemple.com")) == 1, "G4 : reprise après nonce inattendu"

    # ── G5 : script injoignable / délai → pending, jamais synced ; refus authentique → error ──
    fake.down = True
    r3, _ = await new("down@exemple.com")
    assert r3.sync_status == "pending" and "injoignable" in r3.last_error, f"G5 : script en panne mais règle {r3.sync_status}"
    fake.down = False
    fake.timeout_next = True
    r4, _ = await new("timeout@exemple.com")
    assert r4.sync_status == "pending", "G5 : délai dépassé → pending (l'écriture a peut-être eu lieu)"
    async with AsyncSessionLocal() as db:
        r4 = await gr.retry_rule(db, r4.id)
        r3 = await gr.retry_rule(db, r3.id)
    assert r3.sync_status == "synced" and r4.sync_status == "synced" and len(fake.by_from("timeout@exemple.com")) == 1, "G5 : reprise après panne"
    fake.forwarding[0]["status"] = "pending"            # l'adresse n'est plus validée côté Gmail
    r5, _ = await new("refus@exemple.com")
    assert r5.sync_status == "error" and "destination_not_verified" in r5.last_error, f"G5 : refus authentique → error ({r5.sync_status})"
    fake.forwarding[0]["status"] = "accepted"
    async with AsyncSessionLocal() as db:
        r5 = await gr.retry_rule(db, r5.id)
    assert r5.sync_status == "synced", "G5 : Réessayer après correction côté Gmail"

    # ── G6 : modification (replace), simple renommage sans appel, remplacement interrompu ──
    calls = len(fake.calls)
    async with AsyncSessionLocal() as db:
        await gr.update_rule(db, r.id, {"name": "Renommée", "from": "news@exemple.com", "destination": DEST, "skip_inbox": True})
    assert len(fake.calls) == calls, "G6 : un simple renommage ne doit pas appeler le script (replace à critères identiques = doublon côté Gmail)"
    old_id = (await rule(r.id)).gmail_filter_id
    async with AsyncSessionLocal() as db:
        u, _ = await gr.update_rule(db, r.id, {"name": "Renommée", "from": "news@exemple.com", "destination": DEST2, "skip_inbox": False})
    assert u.sync_status == "synced" and u.gmail_filter_id != old_id and len(fake.by_from("news@exemple.com")) == 1 \
        and fake.by_from("news@exemple.com")[0]["action"] == {"forward": DEST2}, "G6 : replace → un seul filtre, nouvelle destination"
    fake.fail_remove_once = True
    async with AsyncSessionLocal() as db:
        u, _ = await gr.update_rule(db, r.id, {"name": "Renommée", "from": "news@exemple.com", "destination": DEST, "skip_inbox": True})
    assert u.sync_status == "error" and len(fake.by_from("news@exemple.com")) == 2, \
        f"G6 : suppression de l'ancien filtre en panne → les DEUX filtres existent (jamais de fenêtre sans transfert) [{u.sync_status}, {len(fake.by_from('news@exemple.com'))}]"
    writes = [c for c in fake.calls if c in ("create_rule", "replace_rule", "delete_rule")]
    async with AsyncSessionLocal() as db:
        rep = await gr.sync(db)
    assert [x["kind"] for x in rep["drift"] if x["rule_id"] == r.id] == ["unrecorded"], f"G6 : drift attendu après replace interrompu : {rep['drift']}"
    assert (await rule(r.id)).sync_status == "drift", "G6 : la règle doit passer en drift"
    assert [c for c in fake.calls if c in ("create_rule", "replace_rule", "delete_rule")] == writes, "G6 : la synchronisation DÉTECTE seulement — aucune écriture"
    async with AsyncSessionLocal() as db:
        fixed = await gr.fix_rule(db, r.id)
    assert fixed.sync_status == "synced" and len(fake.by_from("news@exemple.com")) == 1 and fixed.gmail_filter_id == fake.by_from("news@exemple.com")[0]["id"], \
        "G6 : le correctif à la demande adopte le nouveau filtre et nettoie l'ancien"

    # ── G7 : désactiver / réactiver / supprimer ──
    async with AsyncSessionLocal() as db:
        off = await gr.set_enabled(db, r.id, False)
    assert off.sync_status == "synced" and off.gmail_filter_id is None and not fake.by_from("news@exemple.com"), "G7 : désactivée = pas de filtre"
    async with AsyncSessionLocal() as db:
        on = await gr.set_enabled(db, r.id, True)
    assert on.sync_status == "synced" and len(fake.by_from("news@exemple.com")) == 1, "G7 : réactivée = filtre recréé"
    fake.refuse_next = "rate_limited"
    async with AsyncSessionLocal() as db:
        res = await gr.remove_rule(db, r.id)
    assert res["deleted"] is False and await rule(r.id) is not None, "G7 : suppression refusée par le script → la règle reste (et le dit)"
    async with AsyncSessionLocal() as db:
        await gr.retry_rule(db, r.id)
    assert await rule(r.id) is None and not fake.by_from("news@exemple.com"), "G7 : suppression → filtre ET ligne disparus"
    async with AsyncSessionLocal() as db:
        actions = [a.action for a in await gr.audit_rows(db, rule_id=r.id)]
    assert "delete_rule" in actions and "create_rule" in actions, "G7 : l'historique reste dans le journal après suppression de la règle"

    # ── G8 : filtre supprimé à la main → drift, alerte une fois, correction à la demande seulement ──
    victim = (await new("main@exemple.com"))[0]
    fake.filters = [f for f in fake.filters if f["id"] != victim.gmail_filter_id]
    fake.managed.pop(victim.gmail_filter_id)
    writes = [c for c in fake.calls if c in ("create_rule", "replace_rule", "delete_rule")]
    res = await gr.daily_check()
    assert res["alerts"] == ["drift"] and len(d.gateway.sent) == 1, f"G8 : une alerte pour l'écart ({res}, {len(d.gateway.sent)})"
    assert "main@exemple.com" in d.gateway.sent[0]["body"] or "N" in d.gateway.sent[0]["body"], "G8 : l'alerte nomme la règle"
    assert (await rule(victim.id)).drift_kind == "missing" and [c for c in fake.calls if c in ("create_rule", "replace_rule", "delete_rule")] == writes, \
        "G8 : tâche quotidienne = détection seule"
    res = await gr.daily_check()
    assert res["alerts"] == [] and len(d.gateway.sent) == 1, "G8 : le même écart ne ré-alerte pas chaque jour"
    async with AsyncSessionLocal() as db:
        fx = await gr.fix_rule(db, victim.id)
    assert fx.sync_status == "synced" and len(fake.by_from("main@exemple.com")) == 1, "G8 : correction à la demande = recréation"

    # ── G9 : orphelins, filtres étrangers, jamais touchés ──
    fake.seq += 1
    fake.filters.append({"id": f"F{fake.seq}", "criteria": {"from": "orphelin@exemple.com"}, "action": {"forward": DEST}})
    fake.managed[f"F{fake.seq}"] = "crid-orphelin-0001"
    orphan_id = f"F{fake.seq}"
    fake.seq += 1
    fake.filters.append({"id": f"F{fake.seq}", "criteria": {"from": "manuel@exemple.com"}, "action": {"forward": "ami@exemple.com"}})
    foreign_id = f"F{fake.seq}"
    async with AsyncSessionLocal() as db:
        rep = await gr.sync(db)
    assert [o["id"] for o in rep["orphans"]] == [orphan_id], f"G9 : orphelin attendu, obtenu {rep['orphans']}"
    assert [f["id"] for f in rep["foreign"]] == [foreign_id], "G9 : filtre étranger listé (lecture seule)"
    from app.gmail_client import ScriptError
    try:
        async with AsyncSessionLocal() as db:
            await gr.delete_orphan(db, foreign_id)
    except ScriptError as exc:
        assert exc.code == "not_managed", exc.code
    else:
        raise AssertionError("G9 : supprimer un filtre étranger aurait dû être refusé (not_managed)")
    assert any(f["id"] == foreign_id for f in fake.filters), "G9 : le filtre manuel doit rester intact"
    async with AsyncSessionLocal() as db:
        adopted = await gr.adopt_orphan(db, orphan_id)
    assert adopted.sync_status == "synced" and adopted.from_addr == "orphelin@exemple.com" and adopted.gmail_filter_id == orphan_id, "G9 : adoption"
    async with AsyncSessionLocal() as db:
        rep = await gr.sync(db)
    assert not rep["orphans"] and not rep["drift"], f"G9 : après adoption plus d'écart : {rep['drift']} {rep['orphans']}"

    # ── G10 : échecs d'authentification : 3 de suite → une alerte ; un succès remet à zéro ──
    sent0 = len(d.gateway.sent)
    for _ in range(2):
        gr_secret = fake.secret
        fake.secret = "b" * 64        # le script a un autre secret : le VPS est désaccordé
        async with AsyncSessionLocal() as db:
            info = await gr.ping(db)
        assert not info["ok"] and "bad_signature" in info["error"], f"G10 : ping désaccordé : {info}"
        fake.secret = gr_secret
    assert len(d.gateway.sent) == sent0, "G10 : 2 échecs ne déclenchent pas d'alerte"
    async with AsyncSessionLocal() as db:
        assert (await gr.ping(db))["ok"]
        assert (await gr.status(db))["auth_failures"] == 0, "G10 : un succès remet le compteur à zéro"
    fake.secret = "b" * 64
    for _ in range(3):
        async with AsyncSessionLocal() as db:
            await gr.ping(db)
    fake.secret = gr_secret
    assert len(d.gateway.sent) == sent0 + 1 and "authentification" in d.gateway.sent[-1]["subject"], "G10 : 3 échecs consécutifs → 1 alerte"
    async with AsyncSessionLocal() as db:
        await gr.ping(db)
        await gr.ping(db)

    # ── G11 : rotation du secret ──
    async with AsyncSessionLocal() as db:
        nxt = await gr.rotate_start(db)
        with refused("rotation_not_effective", "G11 (secret non encore posé dans le script)"):
            await gr.rotate_confirm(db)             # le script n'a pas encore le nouveau secret
        assert (await gr.current_secret(db)) == SECRET, "G11 : confirmation refusée → l'ancien secret reste actif"
    fake.secret = nxt                                # l'utilisateur colle le nouveau secret dans le script
    async with AsyncSessionLocal() as db:
        await gr.rotate_confirm(db)
        assert (await gr.current_secret(db)) == nxt and (await gr.status(db))["secret_age_days"] == 0, "G11 : nouveau secret promu, âge remis à zéro"
        assert (await gr.ping(db))["ok"], "G11 : le VPS parle avec le nouveau secret"
    old_client = gmail_client.ScriptClient(URL, SECRET, transport=gr._transport)
    try:
        await old_client.call("ping")
    except ScriptError as exc:
        assert exc.code == "bad_signature", exc.code
    else:
        raise AssertionError("G11 : l'ancien secret doit être refusé par le script")

    # ── G12 : secret trop vieux → alerte hebdomadaire, une seule fois ──
    async with AsyncSessionLocal() as db:
        await gr.set_setting(db, "secret_rotated_at", "2026-01-01T00:00:00")
    sent0 = len(d.gateway.sent)
    res = await gr.daily_check()
    assert res["alerts"] == ["secret_age"] and len(d.gateway.sent) == sent0 + 1, f"G12 : secret > 6 mois → alerte ({res})"
    assert (await gr.daily_check())["alerts"] == [], "G12 : pas de ré-alerte la même semaine"
    async with AsyncSessionLocal() as db:
        await gr.set_setting(db, "secret_rotated_at", None)
        await gr.set_setting(db, "secret_first_seen", None)

    # ── G13 : adresses de transfert : cache, croisement avec les alias, non-validées non sélectionnables ──
    async with AsyncSessionLocal() as db:
        await gr.set_setting(db, "secret", None)
    fake.secret = SECRET
    gr._addr_cache.update(at=0.0, data=None)
    async with AsyncSessionLocal() as db:
        out = await gr.forwarding_addresses(db)
    by = {a["email"]: a for a in out["addresses"]}
    assert by[DEST]["selectable"] and by[DEST]["alias"]["frequency"] == "morning", "G13 : adresse acceptée = alias du moteur + fréquence"
    assert by[DEST2]["alias"]["frequency"] == "minute", "G13 : fréquence de l'autre alias"
    assert not by["attente@oozeenaru.resend.app"]["selectable"], "G13 : adresse non acceptée non sélectionnable"
    n = fake.calls.count("list_forwarding_addresses")
    async with AsyncSessionLocal() as db:
        await gr.forwarding_addresses(db)
    assert fake.calls.count("list_forwarding_addresses") == n, "G13 : cache de 5 minutes"
    fake.down = True
    async with AsyncSessionLocal() as db:
        out = await gr.forwarding_addresses(db, refresh=True)
    assert out["stale"] and out["addresses"], "G13 : script en panne → dernière liste connue, signalée périmée"
    fake.down = False

    # ── G14 : croisement destination ↔ alias du moteur ──
    async with AsyncSessionLocal() as db:
        w = await gr.engine_warnings(db, {"from_addr": "inconnu@exemple.com", "destination": DEST, "subject_contains": ""})
        assert w and "liste blanche" in w[0], f"G14 : expéditeur hors liste blanche de l'alias non signalé : {w}"
        assert not await gr.engine_warnings(db, {"from_addr": "news@exemple.com", "destination": DEST, "subject_contains": ""}), "G14 : expéditeur admis = pas d'avertissement"
        assert not await gr.engine_warnings(db, {"from_addr": "n@x.fr", "destination": DEST2, "subject_contains": ""}), "G14 : alias ouvert = pas d'avertissement"
        w = await gr.engine_warnings(db, {"from_addr": "n@x.fr", "destination": "nouveau@oozeenaru.resend.app", "subject_contains": ""})
        assert w and "alias par défaut" in w[0], f"G14 : destination sans alias non signalée : {w}"

    # ── G15 : routes — jeton exigé, erreurs nommées, aucun secret dans les réponses ──
    seen = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        h = {"X-Hub-Token": settings.HUB_API_TOKEN}
        assert (await c.get("/api/gmail/rules")).status_code == 401, "G15 : route sans jeton doit être refusée"
        assert (await c.post("/api/gmail/rules", json={})).status_code == 401, "G15 : écriture sans jeton refusée"
        saved = settings.HUB_API_TOKEN
        settings.HUB_API_TOKEN = ""
        assert (await c.get("/api/gmail/rules", headers=h)).status_code == 503, "G15 : sans HUB_API_TOKEN configuré, ces routes ne s'ouvrent JAMAIS"
        settings.HUB_API_TOKEN = saved
        r = await c.post("/api/gmail/rules", headers=h, json={"name": "api", "from": "api@exemple.com", "destination": DEST})
        assert r.status_code == 200 and r.json()["rule"]["sync_status"] == "synced" and r.json()["warnings"], r.text
        seen.append(r.text)
        r = await c.post("/api/gmail/rules", headers=h, json={"name": "x", "from": "*", "destination": DEST})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "criteria_too_broad", r.text
        r = await c.post("/api/gmail/preview", headers=h, json={"from": "x@banque.fr", "destination": DEST})
        assert r.status_code == 400, "G15 : l'aperçu refuse immédiatement un domaine interdit"
        for path in ("/api/gmail/status", "/api/gmail/rules", "/api/gmail/forwarding-addresses", "/api/gmail/audit", "/api/gmail/sync"):
            r = await (c.post(path, headers=h) if path.endswith("sync") else c.get(path, headers=h))
            assert r.status_code == 200, (path, r.text)
            seen.append(r.text)
        r = await c.post("/api/gmail/script/ping", headers=h)
        seen.append(r.text)
        fake.down = True
        r = await c.get("/api/gmail/forwarding-addresses?refresh=true", headers=h)
        assert r.status_code == 200 and r.json()["stale"], "G15 : panne du script → liste périmée, pas un 500"
        r = await c.post("/api/gmail/sync", headers=h)
        assert r.status_code == 502 and r.json()["detail"]["code"] == "script_unavailable", f"G15 : message clair en cas de panne : {r.text}"
        fake.down = False
        r = await c.post(f"/api/gmail/rules/{(await rules_by_from('api@exemple.com'))[0].id}/retry", headers=h)
        assert r.status_code == 409, "G15 : rien à réessayer sur une règle synchronisée"

    # ── G16 : le secret n'apparaît NULLE PART (réponses, journal, règles, logs) — ni l'URL du script ──
    async with AsyncSessionLocal() as db:
        dump = json.dumps([[a.action, a.error_code, a.payload_hash, a.detail, a.client_request_id] for a in await gr.audit_rows(db, limit=500)])
        dump += json.dumps([[x.name, x.last_error, x.client_request_id] for x in await gr.list_rules(db)])
    blob = "\n".join(seen) + dump + "\n".join(logs.lines)
    for secret in (SECRET, nxt):
        assert secret not in blob, "G16 : un secret fuit dans les réponses, le journal ou les logs"
    assert "AKfycbx-URL-SECRETE" not in blob, "G16 : l'URL du script fuit dans les logs/réponses (httpx la journalise en INFO)"
    assert not any("sig" in a.lower() and len(a) == 64 for a in dump.split('"')), "G16 : une signature fuit dans le journal"

    # ── G17 : l'index d'unicité tient aussi en base (pas seulement dans le code) ──
    try:
        async with AsyncSessionLocal() as db:
            for i in range(2):
                db.add(GmailRule(id=f"dup-{i}", from_addr="u@u.fr", subject_contains="", destination=DEST, sync_status="synced"))
            await db.commit()
    except Exception as exc:
        assert "ux_gmail_rules_triplet" in str(exc) or "unique" in str(exc).lower(), exc
    else:
        raise AssertionError("G17 : deux règles au même triplet acceptées par la base")

    print(f"OK — pilotage Gmail : {len(fake.calls)} appels au faux script, 18 scénarios (G0–G17)")


asyncio.run(main())
