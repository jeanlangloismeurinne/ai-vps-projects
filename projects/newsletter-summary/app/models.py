from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer, Numeric, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Email(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Identifiant unique du mail propre à Resend — sert de clé de déduplication.
    message_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    # Identifiant Resend du mail reçu (email_id) — sert à rapatrier le corps via l'API.
    email_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    from_addr: Mapped[str] = mapped_column(String(512))
    to_addr: Mapped[str] = mapped_column(String(512), default="")
    subject: Mapped[str] = mapped_column(Text, default="")
    text_body: Mapped[str] = mapped_column(Text, default="")
    html_body: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    # Résumé généré (valeur structurée produite par le LLM).
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # new = pas encore résumé/envoyé dans un digest ; summarized = inclus dans un digest.
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    summarized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Alias qui a reçu le mail (aliases.id). Toujours renseigné : une adresse inconnue du domaine
    # est rattachée à l'alias par défaut (la newsletter), comme avant l'introduction des alias.
    alias_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    # Nombre de tentatives de traitement et dernière erreur NOMMÉE : un mail ne reste jamais
    # bloqué ou perdu sans trace (statuts new → processing → summarized | failed | rejected).
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Instant de la réservation (status='processing') : sert à récupérer un run interrompu.
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Alias(Base):
    """Adresse de réception (`<local_part>@<domaine>`) et sa politique de traitement.

    La newsletter n'est PAS un cas à part : c'est l'alias `is_default` (catch-all du domaine,
    tous expéditeurs, digest à adresse fixe). Un alias « à la demande » répond à l'expéditeur.
    Les seules différences entre les deux tiennent dans ces colonnes — pas dans le code.
    """
    __tablename__ = "aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Partie locale, minuscule, unique. `aaa+bbb` est un alias à part entière (correspondance exacte).
    local_part: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # morning | evening | minute. `minute` = un e-mail de réponse PAR mail reçu (jamais de lot).
    frequency: Mapped[str] = mapped_column(String(16), default="morning")
    # Un seul alias par défaut : reçoit toute adresse du domaine qui ne correspond à aucun alias.
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    # NULL = répondre à l'expéditeur ; sinon adresse fixe (la newsletter → RECIPIENT_EMAIL).
    recipient: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # False (défaut sûr) : seuls `allowed_senders` sont acceptés — liste vide = personne.
    open_senders: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_senders: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Surcharges d'habillage (titre, objet, pied…) ; clés absentes → défauts de aliases.py.
    presentation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PromptVersion(Base):
    """Historique des versions du prompt de résumé (HTML) envoyé à DeepInfra.

    La version active (is_active=True, une seule à la fois) est celle que le digest lit
    à chaque exécution. Éditée/re-versionnée via le Hub (/newsletter/prompt), qui appelle
    /api/prompt/*. Chaque enregistrement crée une nouvelle version (append-only) pour
    pouvoir revenir à une version antérieure (menu déroulant).
    """
    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    prompt: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # Alias auquel appartient la version (une version active PAR alias).
    alias_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)


class KbDocument(Base):
    """Enveloppe document commune — KNOWLEDGE_ARCHITECTURE.md §3 (contrat à la fédération).

    Chaque mail résumé est stocké ici sous forme d'enveloppe normalisée : pivot Markdown
    (`body`) + métadonnées. Exportable tel quel en JSON (GET /api/kb) ; prêt pour une
    ingestion future dans l'index fédéré (pgvector) sans transformation.
    """
    __tablename__ = "kb_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    project: Mapped[str] = mapped_column(String(128), default="newsletter-summary", index=True)
    source: Mapped[str] = mapped_column(String(32), default="mailbox")
    uri: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(Text, default="")
    body: Mapped[str] = mapped_column(Text, default="")          # Markdown (pivot humain)
    lang: Mapped[str] = mapped_column(String(8), default="fr")
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    entities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reliability: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    reliability_tier: Mapped[str | None] = mapped_column(String(8), nullable=True)
    visibility: Mapped[str] = mapped_column(String(16), default="private")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # « metadata » est réservé sur la base déclarative → attribut metadata_ (colonne « metadata »).
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
