"""Alias de réception : adresses, politique d'expéditeurs, habillage, amorçage de la newsletter.

Un mail entrant est rattaché à l'alias dont la partie locale correspond EXACTEMENT à l'adresse
destinataire (`aaa+bbb` est un alias à part entière : pas de repli « +tag → alias de base », qui
ferait couvrir un espace d'adresses illimité par la liste blanche d'un seul alias). Toute adresse
sans alias va à l'alias par défaut — le catch-all d'avant l'introduction des alias.
"""
from __future__ import annotations

import logging
import re
from email.utils import getaddresses, parseaddr

from sqlalchemy import select, update

from app.config import settings
from app.models import Alias, Email, PromptVersion

logger = logging.getLogger(__name__)

FREQUENCIES = ("morning", "evening", "minute")

# Partie locale : lettres/chiffres/`_`/`+`/`-`, points seulement entre deux segments (ni en tête,
# ni en fin, ni doublés) — le sous-ensemble courant des règles d'adresse (RFC 5322 atext).
_LOCAL_RE = re.compile(r"^[a-z0-9_+-]+(?:\.[a-z0-9_+-]+)*$")
_EMAIL_RE = re.compile(r"^[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+$")

# ── Habillage ────────────────────────────────────────────────────────────────────────────────
# Chaînes du digest newsletter d'origine : reproduites TELLES QUELLES (le test d'or exige le
# même e-mail octet pour octet). Persistées sur la ligne de l'alias par défaut.
PRESENTATION_NEWSLETTER = {
    "title": "Résumé quotidien des newsletters",
    "label": "newsletter",
    "count_line": "{count} newsletter(s) reçue(s).",
    "footer": "Newsletter Summary · généré automatiquement chaque matin",
    "subject": "📬 Résumé hebdo-news — {count} newsletter(s) — {date}",
    "subject_single": "📬 Résumé hebdo-news — {count} newsletter(s) — {date}",
}
# Défauts d'un alias « à la demande » (réponse à l'expéditeur).
PRESENTATION_REPLY = {
    "title": "Résumé de vos mails",
    "label": "mail",
    "count_line": "{count} mail(s) reçu(s).",
    "footer": "Newsletter Summary · résumé à la demande",
    "subject": "📬 Résumé — {count} mail(s) — {date}",
    "subject_single": "📬 Résumé : {subject}",
}


def presentation(alias: Alias) -> dict:
    return {**PRESENTATION_REPLY, **(alias.presentation or {})}


# ── Adresses ─────────────────────────────────────────────────────────────────────────────────

def validate_local_part(raw: str) -> str:
    lp = (raw or "").strip().lower()
    if not lp:
        raise ValueError("nom d'alias vide")
    if len(lp) > 64:
        raise ValueError("nom d'alias trop long (64 caractères maximum)")
    if not _LOCAL_RE.match(lp):
        raise ValueError(
            "nom d'alias invalide : lettres, chiffres et _ + - ; le point n'est admis qu'entre deux segments"
        )
    return lp


def normalize_sender(from_addr: str) -> str:
    """`"Jean <A@X.fr>"` → `a@x.fr`. Vide si illisible."""
    addr = parseaddr(from_addr or "")[1].strip().lower()
    return addr if _EMAIL_RE.match(addr) else ""


def parse_allowed_senders(value) -> list[str]:
    """Liste (ou texte, un par ligne / séparé par `,` `;`) → adresses normalisées, dédupliquées.

    Lève ValueError sur une entrée qui n'est pas une adresse : une faute de frappe dans une liste
    blanche doit se voir à la saisie, pas se traduire par « personne n'est autorisé » en silence.
    """
    if value is None:
        return []
    items = re.split(r"[\n,;]+", value) if isinstance(value, str) else list(value)
    out: list[str] = []
    for item in items:
        item = (item or "").strip()
        if not item:
            continue
        addr = normalize_sender(item)
        if not addr:
            raise ValueError(f"adresse d'expéditeur invalide : {item!r}")
        if addr not in out:
            out.append(addr)
    return out


def recipient_local_parts(to_addr: str) -> list[str]:
    """Parties locales (minuscules) des destinataires d'un champ `to` (`a@b, "N, M" <c@d>`)."""
    out = []
    for _name, addr in getaddresses([to_addr or ""]):
        if "@" in addr:
            out.append(addr.rsplit("@", 1)[0].strip().lower())
    return out


def match_alias(aliases: list[Alias], to_addr: str) -> Alias | None:
    """Alias dont la partie locale correspond EXACTEMENT à un destinataire ; sinon le défaut.

    La correspondance ignore le domaine : le jour où un domaine d'envoi/réception vérifié
    s'ajoute à `*.resend.app`, `summary@…` continue d'atteindre le même alias.
    """
    by_local = {a.local_part: a for a in aliases}
    for lp in recipient_local_parts(to_addr):
        if lp in by_local:
            return by_local[lp]
    return next((a for a in aliases if a.is_default), None)


def sender_allowed(alias: Alias, from_addr: str) -> bool:
    if alias.open_senders:
        return True
    sender = normalize_sender(from_addr)
    return bool(sender) and sender in {normalize_sender(s) for s in (alias.allowed_senders or [])}


def admit(alias: Alias | None, from_addr: str, *, sender_known: bool = True) -> tuple[bool, str]:
    """(admis, raison du refus). `sender_known=False` : l'expéditeur n'est pas encore rapatrié,
    on ne refuse pas sur une adresse vide — le moteur re-contrôle, et c'est LUI qui fait foi."""
    if alias is None:
        return False, "aucun alias (ni défaut) configuré"
    if not alias.enabled:
        return False, f"alias {alias.local_part} désactivé"
    if alias.open_senders:
        return True, ""
    if not sender_known and not normalize_sender(from_addr):
        return True, ""
    if sender_allowed(alias, from_addr):
        return True, ""
    return False, f"expéditeur non autorisé : {normalize_sender(from_addr) or from_addr or '(inconnu)'}"


def full_address(alias: Alias) -> str:
    return f"{alias.local_part}@{settings.INBOUND_DOMAIN}"


# ── Accès base ───────────────────────────────────────────────────────────────────────────────

async def list_aliases(db) -> list[Alias]:
    res = await db.execute(select(Alias).order_by(Alias.is_default.desc(), Alias.id.asc()))
    return list(res.scalars().all())


async def get_alias(db, alias_id: int) -> Alias | None:
    return await db.get(Alias, alias_id)


async def create_alias(db, local_part: str, *, frequency: str = "minute", allowed_senders=None,
                       open_senders: bool = False, enabled: bool = True) -> Alias:
    """Crée un alias et lui donne un prompt v1 = copie du prompt actif de la newsletter."""
    from app import prompts  # import tardif : prompts n'a pas besoin d'aliases

    lp = validate_local_part(local_part)
    if frequency not in FREQUENCIES:
        raise ValueError(f"fréquence invalide : {frequency!r} (attendu : {', '.join(FREQUENCIES)})")
    allowed = parse_allowed_senders(allowed_senders)
    exists = await db.execute(select(Alias.id).where(Alias.local_part == lp))
    if exists.scalars().first() is not None:
        raise ValueError(f"l'alias {lp!r} existe déjà")
    alias = Alias(local_part=lp, frequency=frequency, allowed_senders=allowed,
                  open_senders=bool(open_senders), enabled=bool(enabled), is_default=False)
    db.add(alias)
    await db.commit()
    await db.refresh(alias)
    base = await prompts.get_active_html_prompt(db)  # prompt actif de l'alias par défaut
    await prompts.create_version(db, base, note="Copie du prompt newsletter à la création", alias_id=alias.id)
    return alias


async def update_alias(db, alias_id: int, *, frequency=None, allowed_senders=None,
                       open_senders=None, enabled=None) -> Alias | None:
    """Met à jour la politique d'un alias. La partie locale est IMMUABLE (changer l'adresse
    orphelinerait les mails et les versions de prompt déjà rattachés)."""
    alias = await db.get(Alias, alias_id)
    if alias is None:
        return None
    if frequency is not None:
        if frequency not in FREQUENCIES:
            raise ValueError(f"fréquence invalide : {frequency!r} (attendu : {', '.join(FREQUENCIES)})")
        alias.frequency = frequency
    if allowed_senders is not None:
        alias.allowed_senders = parse_allowed_senders(allowed_senders)
    if open_senders is not None:
        alias.open_senders = bool(open_senders)
    if enabled is not None:
        alias.enabled = bool(enabled)
    await db.commit()
    await db.refresh(alias)
    return alias


async def seed_default_alias(db) -> Alias:
    """Au démarrage (idempotent) : garantit l'alias par défaut `newsletter` et y rattache les
    mails et versions de prompt d'avant les alias.

    Le rattachement (`WHERE alias_id IS NULL`) est rejoué à chaque démarrage : après un rollback
    vers l'ancien code, ses lignes sans alias sont recollées à la newsletter au redémarrage.
    """
    res = await db.execute(select(Alias).where(Alias.is_default.is_(True)))
    alias = res.scalars().first()
    if alias is None:
        alias = Alias(
            local_part="newsletter", is_default=True, enabled=True, frequency="morning",
            recipient=settings.RECIPIENT_EMAIL, open_senders=True, allowed_senders=[],
            presentation=dict(PRESENTATION_NEWSLETTER),
        )
        db.add(alias)
        await db.commit()
        await db.refresh(alias)
        logger.info("Alias par défaut « newsletter » créé (destinataire %s).", settings.RECIPIENT_EMAIL)
    r1 = await db.execute(update(Email).where(Email.alias_id.is_(None)).values(alias_id=alias.id))
    r2 = await db.execute(update(PromptVersion).where(PromptVersion.alias_id.is_(None)).values(alias_id=alias.id))
    await db.commit()
    if r1.rowcount or r2.rowcount:
        logger.info("Rattachés à l'alias newsletter : %d mail(s), %d version(s) de prompt.", r1.rowcount, r2.rowcount)
    return alias
