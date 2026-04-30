from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Manufacturer, VehicleModel, Variant, PriceSnapshot, ScraperHealth
from app.scrapers import ALL_SCRAPERS
from app.scheduler import run_all_scrapers

router = APIRouter(prefix="/api")


@router.get("/manufacturers")
async def list_manufacturers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Manufacturer).options(selectinload(Manufacturer.health)).order_by(Manufacturer.name)
    )
    manufacturers = result.scalars().all()
    return [
        {
            "slug": m.slug,
            "name": m.name,
            "country": m.country,
            "color": m.color,
            "status": m.health.status if m.health else "never_run",
            "last_success": m.health.last_success_at.isoformat() if m.health and m.health.last_success_at else None,
            "variants_found": m.health.variants_found if m.health else 0,
        }
        for m in manufacturers
    ]


@router.get("/data/{slug}")
async def get_chart_data(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Manufacturer).where(Manufacturer.slug == slug)
    )
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Constructeur introuvable")

    result = await db.execute(
        select(VehicleModel)
        .where(VehicleModel.manufacturer_id == m.id)
        .options(selectinload(VehicleModel.variants).selectinload(Variant.snapshots))
        .order_by(VehicleModel.name)
    )
    models = result.scalars().all()

    data = {}
    for model in models:
        data[model.name] = {}
        for variant in model.variants:
            snapshots = sorted(variant.snapshots, key=lambda s: s.scrape_date)
            data[model.name][variant.name] = [
                {"date": s.scrape_date.isoformat(), "price": s.price_euros}
                for s in snapshots
            ]

    return {
        "manufacturer": {"slug": m.slug, "name": m.name, "color": m.color},
        "models": data,
    }


@router.get("/health")
async def get_health(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScraperHealth).options(selectinload(ScraperHealth.manufacturer))
    )
    healths = result.scalars().all()
    return [
        {
            "manufacturer": h.manufacturer.name,
            "slug": h.manufacturer.slug,
            "status": h.status,
            "last_run": h.last_run_at.isoformat() if h.last_run_at else None,
            "last_success": h.last_success_at.isoformat() if h.last_success_at else None,
            "last_error": h.last_error,
            "variants_found": h.variants_found,
            "alert_sent": h.alert_sent_at.isoformat() if h.alert_sent_at else None,
        }
        for h in healths
    ]


@router.post("/scrape/run")
async def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_all_scrapers)
    return {"status": "started", "message": "Scraping lancé en arrière-plan"}


@router.post("/scrape/run/{slug}")
async def trigger_scrape_one(slug: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    scraper_class = next((s for s in ALL_SCRAPERS if s.MANUFACTURER_SLUG == slug), None)
    if not scraper_class:
        raise HTTPException(404, f"Scraper '{slug}' introuvable")

    async def _run():
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await scraper_class(session).run()

    background_tasks.add_task(_run)
    return {"status": "started", "manufacturer": slug}
