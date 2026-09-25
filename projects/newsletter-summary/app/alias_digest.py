"""Moteur de résumé : UN seul, pour tous les alias (la newsletter comprise).

Ce qui distingue un alias d'un autre tient à sa ligne en base (`Alias`), pas au code :
  - destinataire : l'expéditeur du mail (alias « à la demande ») ou une adresse fixe (newsletter) ;
  - expéditeurs : liste blanche ou tous ;
  - cadence : `morning` / `evening` = UN lot par destinataire ; `minute` = UN e-mail PAR mail reçu
    (jamais de concaténation) ;
  - habillage : titre, objet, pied (cf. `aliases.PRESENTATION_*`).

Invariant central — un mail n'est jamais bloqué ni perdu sans trace : chaque mail réservé finit en
`summarized`, `failed` (avec `last_error` NOMMÉE, et une carte d'erreur envoyée au destinataire
chaque fois que l'envoi est possible), `rejected` (avec la raison), ou revient en `new` pour une
nouvelle tentative bornée. Un run interrompu est récupéré par `_recover_stuck`.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import func, select, update

from app import aliases as al
from app import backfill, comms_client, digest, summarizer, urlfetch
from app.config import settings
from app.database import AsyncSessionLocal
from app.kb import store_email_summary
from app.models import Alias, Email
from app.prompts import get_active_html_prompt

logger = logging.getLogger(__name__)

# Au-delà, une ligne `processing` est jugée orpheline (run tué) — > au timeout d'un run (10 min).
STUCK_AFTER = timedelta(minutes=15)
RUN_TIMEOUT_S = 600


class _Transient(Exception):
    """Échec réessayable (corps pas encore rapatrié…)."""


def _reason(exc: Exception) -> str:
    """Motif d'échec destiné au DESTINATAIRE : court, sur une ligne, sans URL d'API ni lien de doc.

    L'exception brute de httpx (« Client error '401 Unauthorized' for url 'https://api…' For more
    information check: https://developer.mozilla.org/… ») a été constatée dans un vrai e-mail d'erreur :
    illisible, et bavard sur l'infrastructure. Le détail complet reste dans les logs.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return f"service de résumé en erreur (HTTP {exc.response.status_code})"
    return " ".join((str(exc) or type(exc).__name__).split())[:200]


def _now() -> datetime:
    return datetime.utcnow()


def _start_of_today_utc() -> datetime:
    paris = datetime.now(ZoneInfo("Europe/Paris")).replace(hour=0, minute=0, second=0, microsecond=0)
    return paris.astimezone(timezone.utc).replace(tzinfo=None)


# ── Réservation ──────────────────────────────────────────────────────────────────────────────

async def _recover_stuck(db) -> None:
    """Un run tué en plein vol laisse des lignes `processing` : on les rend (tentative comptée,
    sinon un mail qui fait planter le run le referait planter à l'infini)."""
    res = await db.execute(select(Email).where(Email.status == "processing", Email.claimed_at < _now() - STUCK_AFTER))
    for e in res.scalars().all():
        e.attempts = (e.attempts or 0) + 1
        e.claimed_at = None
        e.last_error = "traitement interrompu (run > 15 min)"
        e.status = "failed" if e.attempts >= settings.ALIAS_MAX_ATTEMPTS else "new"
        logger.error("Mail %s récupéré après run interrompu → %s", e.id, e.status)
    await db.commit()


async def _claim(db, alias: Alias) -> list[Email]:
    """Réserve les mails `new` de l'alias (UPDATE … RETURNING atomique, SKIP LOCKED) : deux runs qui
    se chevauchent ne peuvent pas envoyer deux fois le même mail."""
    ids_q = (
        select(Email.id).where(Email.alias_id == alias.id, Email.status == "new")
        .order_by(Email.received_at, Email.id).with_for_update(skip_locked=True)
    )
    res = await db.execute(
        update(Email).where(Email.id.in_(ids_q)).values(status="processing", claimed_at=_now()).returning(Email.id)
    )
    ids = [r[0] for r in res.all()]
    await db.commit()
    if not ids:
        return []
    res = await db.execute(select(Email).where(Email.id.in_(ids)).order_by(Email.received_at, Email.id))
    return list(res.scalars().all())


async def _budget_left(db) -> int:
    """Mails encore traitables aujourd'hui sur les alias à liste blanche (quota gateway partagé)."""
    used = (await db.execute(
        select(func.count()).select_from(Email).join(Alias, Alias.id == Email.alias_id)
        .where(Alias.open_senders.is_(False), Email.status.in_(("summarized", "failed")),
               Email.summarized_at >= _start_of_today_utc())
    )).scalar_one()
    return max(0, settings.ALIAS_MAX_PER_DAY - used)


def _reject(email: Email, reason: str) -> None:
    email.status = "rejected"
    email.last_error = reason
    email.claimed_at = None
    logger.info("Mail %s rejeté (%s)", email.id, reason)


async def _admit(db, alias: Alias, claimed: list[Email]) -> list[Email]:
    """Contrôle d'admission À L'INSTANT DU TRAITEMENT (le webhook a pu recevoir un `From` vide) :
    c'est cette porte qui fait foi. Refusés → `rejected` : ni LLM, ni réponse."""
    budget = None if alias.open_senders else await _budget_left(db)
    kept: list[Email] = []
    for e in claimed:
        ok, reason = al.admit(alias, e.from_addr)
        if not ok:
            _reject(e, reason)
        elif budget is not None and budget <= 0:
            _reject(e, f"plafond quotidien atteint ({settings.ALIAS_MAX_PER_DAY} mails/jour)")
        else:
            kept.append(e)
            if budget is not None:
                budget -= 1
    await db.commit()
    return kept


# ── Traitement ───────────────────────────────────────────────────────────────────────────────

class _Prepared:
    def __init__(self, plain=None, from_line=None, subject_line=None, source_url=None):
        self.plain, self.from_line, self.subject_line, self.source_url = plain, from_line, subject_line, source_url


async def _prepare(db, alias: Alias, email: Email) -> _Prepared:
    """Contenu à résumer : corps du mail (rapatrié si absent) ou, si le mail n'est qu'un lien, la page."""
    if not (email.text_body or email.html_body) and email.email_id:
        try:
            await backfill.backfill_body(email.id, email.email_id)
            await db.refresh(email)
        except Exception:
            logger.exception("Re-essai de rapatriement du corps en erreur (mail %s)", email.id)
    plain = summarizer._to_plain(email)

    if not plain and alias.frequency == "minute" and (email.attempts or 0) + 1 < settings.ALIAS_MAX_ATTEMPTS:
        # Cadence rapide : le corps arrive presque toujours dans la minute — on repasse au tour suivant.
        raise _Transient("corps du mail pas encore disponible chez Resend")

    url = urlfetch.sole_url(plain)
    if not url:
        return _Prepared()
    page = await urlfetch.fetch_page(url)   # UrlFetchError nommée, classée permanente / transitoire
    logger.info("Mail %s = un lien seul → page récupérée (%d car.) : %s", email.id, len(page.text), page.url)
    return _Prepared(plain=page.text, from_line=page.url, subject_line=page.title or email.subject,
                     source_url=page.url)


def _group(alias: Alias, mails: list[Email]) -> list[tuple[str, list[Email]]]:
    """Regroupe par destinataire. Cadence `minute` : un groupe PAR mail (une réponse par mail reçu)."""
    groups: dict[str, list[Email]] = {}
    out: list[tuple[str, list[Email]]] = []
    for e in mails:
        recipient = alias.recipient or al.normalize_sender(e.from_addr)
        if not recipient:
            e.status, e.last_error, e.claimed_at = "failed", "expéditeur illisible : pas d'adresse de réponse", None
            logger.error("Mail %s : %s", e.id, e.last_error)
            continue
        if alias.frequency == "minute":
            out.append((recipient, [e]))
        else:
            groups.setdefault(recipient, []).append(e)
    out.extend(groups.items())
    return out


def _release(email: Email, reason: str) -> None:
    """Remet le mail en file pour une nouvelle tentative, ou l'échoue une fois les tentatives épuisées."""
    email.attempts = (email.attempts or 0) + 1
    email.last_error = reason
    email.claimed_at = None
    email.status = "failed" if email.attempts >= settings.ALIAS_MAX_ATTEMPTS else "new"


async def _process_group(db, alias: Alias, recipient: str, mails: list[Email], prompt: str, pres: dict, stats: dict) -> None:
    items: list[digest.Item] = []
    finals: dict[int, tuple[str, str | None]] = {}   # id → (statut final, last_error)
    sources: dict[int, str | None] = {}

    for email in mails:
        prep = _Prepared()
        try:
            prep = await _prepare(db, alias, email)
            email.summary = await summarizer.summarize_html(email, prompt=prompt, plain=prep.plain)
            if (email.summary or "").strip():
                finals[email.id] = ("summarized", None)
            else:  # carte de repli d'origine (« Corps non reçu » / « Résumé indisponible ») — mais tracée
                finals[email.id] = ("failed", "résumé vide (corps du mail absent ?)")
        except Exception as exc:
            if isinstance(exc, urlfetch.UrlFetchError):
                reason, retryable = exc.reason, not exc.permanent
                logger.warning("Mail %s : %s", email.id, reason)
            elif isinstance(exc, _Transient):
                reason, retryable = str(exc), True
                logger.warning("Mail %s : %s", email.id, reason)
            else:
                reason, retryable = _reason(exc), True
                logger.exception("Résumé échoué pour le mail %s", email.id)
            if alias.frequency == "minute" and retryable and (email.attempts or 0) + 1 < settings.ALIAS_MAX_ATTEMPTS:
                _release(email, reason)
                stats["released"] += 1
                continue
            email.summary = None
            email._summary_error = reason  # type: ignore[attr-defined]
            finals[email.id] = ("failed", reason)
        sources[email.id] = prep.source_url
        items.append(digest.Item(email, prep.from_line, prep.subject_line))

    await db.commit()   # résumés + mails remis en file : acquis avant l'envoi (comme l'ancien digest)
    if not items:
        return

    # KB (enveloppe §3) avec le nom de l'alias — au mieux : un échec d'écriture ne bloque pas l'envoi.
    for it in items:
        if it.email.summary:
            try:
                await store_email_summary(it.email, alias=alias.local_part, source_url=sources.get(it.email.id))
            except Exception:
                logger.exception("Écriture KB échouée pour le mail %s", it.email.id)

    today = digest.today_label()
    single = alias.frequency == "minute"
    try:
        await comms_client.get_client().send_email(
            to=recipient,
            subject=digest.render_subject(items, pres, today, single),
            body=digest.render_text(items, pres, today),
            html=digest.render_html(items, pres, today),
        )
    except Exception as exc:
        logger.exception("Envoi à %s échoué (%d mail(s))", recipient, len(items))
        for it in items:
            _release(it.email, f"envoi : {exc}")
        stats["released"] += len(items)
        await db.commit()
        return

    for it in items:
        status, err = finals[it.email.id]
        it.email.status, it.email.last_error = status, err
        it.email.summarized_at, it.email.claimed_at = _now(), None
        stats["failed" if status == "failed" else "summarized"] += 1
    stats["sent"] += 1
    await db.commit()
    logger.info("Alias %s : e-mail envoyé à %s (%d mail(s)).", alias.local_part, recipient, len(items))


async def _run_alias(alias: Alias) -> dict:
    stats = {"claimed": 0, "rejected": 0, "sent": 0, "summarized": 0, "failed": 0, "released": 0}
    async with AsyncSessionLocal() as db:
        claimed = await _claim(db, alias)
        stats["claimed"] = len(claimed)
        if not claimed:
            return stats
        admitted = await _admit(db, alias, claimed)
        stats["rejected"] = len(claimed) - len(admitted)
        prompt = await get_active_html_prompt(db, alias.id)
        pres = al.presentation(alias)
        groups = _group(alias, admitted)
        await db.commit()
        for recipient, mails in groups:
            try:
                await _process_group(db, alias, recipient, mails, prompt, pres, stats)
            except Exception as exc:  # un groupe qui explose ne bloque ni les autres ni l'alias suivant
                logger.exception("Alias %s : groupe %s en échec", alias.local_part, recipient)
                await db.rollback()
                for m in mails:
                    await db.refresh(m)
                    if m.status == "processing":
                        _release(m, f"erreur interne : {exc}")
                await db.commit()
    return stats


async def run_alias_digests(frequency: str) -> dict:
    """Traite les mails en attente de tous les alias actifs de cette cadence."""
    async with AsyncSessionLocal() as db:
        await _recover_stuck(db)
        res = await db.execute(
            select(Alias).where(Alias.enabled.is_(True), Alias.frequency == frequency)
            .order_by(Alias.is_default.desc(), Alias.id)
        )
        alias_list = list(res.scalars().all())
    report: dict = {}
    for alias in alias_list:
        try:
            report[alias.local_part] = await _run_alias(alias)
        except Exception:
            logger.exception("Alias %s : run en échec (les autres alias continuent)", alias.local_part)
            report[alias.local_part] = {"error": True}
    if any(v.get("claimed") for v in report.values() if isinstance(v, dict)):
        logger.info("Digest %s : %s", frequency, report)
    return report


async def run_frequency(frequency: str) -> dict | None:
    """Point d'entrée du scheduler : le run est BORNÉ — un appel réseau suspendu ne doit pas figer
    silencieusement toute la cadence (max_instances=1 ferait sauter chaque tour suivant)."""
    try:
        return await asyncio.wait_for(run_alias_digests(frequency), timeout=RUN_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.error("Digest %s interrompu après %ds — les mails réservés seront récupérés (_recover_stuck).",
                     frequency, RUN_TIMEOUT_S)
        return None
