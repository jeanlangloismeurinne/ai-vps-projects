from datetime import datetime, date
from sqlalchemy import Integer, String, Text, DateTime, Date, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)  # FR, US, CN, DE, KR, JP
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    website_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    models: Mapped[list["VehicleModel"]] = relationship(back_populates="manufacturer", cascade="all, delete-orphan")
    health: Mapped["ScraperHealth"] = relationship(back_populates="manufacturer", uselist=False)


class VehicleModel(Base):
    __tablename__ = "vehicle_models"
    __table_args__ = (UniqueConstraint("manufacturer_id", "slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    manufacturer: Mapped["Manufacturer"] = relationship(back_populates="models")
    variants: Mapped[list["Variant"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class Variant(Base):
    __tablename__ = "variants"
    __table_args__ = (UniqueConstraint("model_id", "name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("vehicle_models.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    model: Mapped["VehicleModel"] = relationship(back_populates="variants")
    snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="variant", cascade="all, delete-orphan")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("variants.id"), nullable=False)
    price_euros: Mapped[int] = mapped_column(Integer, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    scrape_date: Mapped[date] = mapped_column(Date, server_default=func.current_date())

    variant: Mapped["Variant"] = relationship(back_populates="snapshots")


class ScraperHealth(Base):
    __tablename__ = "scraper_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"), unique=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    alert_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # ok | changed | error | never_run
    status: Mapped[str] = mapped_column(String(20), default="never_run")
    variants_found: Mapped[int] = mapped_column(Integer, default=0)

    manufacturer: Mapped["Manufacturer"] = relationship(back_populates="health")
