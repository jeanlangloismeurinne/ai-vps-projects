from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer
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
