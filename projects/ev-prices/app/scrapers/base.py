import hashlib
import json
import re
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Manufacturer, VehicleModel, Variant, PriceSnapshot, ScraperHealth

logger = logging.getLogger(__name__)


class ScrapedVariant:
    def __init__(self, model_name: str, variant_name: str, price_euros: int):
        self.model_name = model_name
        self.variant_name = variant_name
        self.price_euros = price_euros


class BaseScraper(ABC):
    # Subclasses must define these
    MANUFACTURER_SLUG: str
    MANUFACTURER_NAME: str
    MANUFACTURER_COUNTRY: str  # FR, US, CN, DE, KR, JP
    MANUFACTURER_COLOR: str
    WEBSITE_URL: str

    # CSS selectors expected on the page — used for change detection
    # If fewer than SELECTOR_THRESHOLD_PCT % are present, alert is raised
    EXPECTED_SELECTORS: list[str] = []
    SELECTOR_THRESHOLD_PCT: float = 0.5

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Abstract ──────────────────────────────────────────────────────────────

    @abstractmethod
    async def scrape(self) -> list[ScrapedVariant]:
        """Fetch prices from manufacturer website. Return list of ScrapedVariant."""
        ...

    # ── Playwright helpers ────────────────────────────────────────────────────

    async def fetch_with_playwright(self, url: str, wait_selector: str | None = None) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            ctx = await browser.new_context(
                locale="fr-FR",
                extra_http_headers={"Accept-Language": "fr-FR,fr;q=0.9"},
            )
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            if wait_selector:
                await page.wait_for_selector(wait_selector, timeout=15_000)
            content = await page.content()
            await browser.close()
            return content

    async def fetch_with_httpx(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9",
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            return r.text

    # ── Parsing helpers ───────────────────────────────────────────────────────

    @staticmethod
    def parse_price(text: str) -> int | None:
        """Extract integer price in euros from French-format string like '29 900 €'."""
        cleaned = re.sub(r"[^\d]", "", text.replace("\xa0", "").replace(" ", ""))
        if cleaned and 5_000 <= int(cleaned) <= 500_000:
            return int(cleaned)
        return None

    @staticmethod
    def extract_prices_from_html(html: str) -> list[int]:
        """Fallback: regex scan entire page for price patterns."""
        prices = []
        for m in re.finditer(r"(\d[\d\s\xa0]{3,8})\s*[€£]", html):
            p = BaseScraper.parse_price(m.group(1))
            if p:
                prices.append(p)
        return sorted(set(prices))

    @staticmethod
    def extract_jsonld(html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(tag.string or "")
                if isinstance(data, list):
                    results.extend(data)
                else:
                    results.append(data)
            except json.JSONDecodeError:
                pass
        return results

    # ── Fingerprint & change detection ───────────────────────────────────────

    def compute_fingerprint(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        present = [sel for sel in self.EXPECTED_SELECTORS if soup.select(sel)]
        payload = json.dumps({"selectors": sorted(present), "count": len(present)})
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def detect_change(self, html: str, old_fingerprint: str | None) -> bool:
        if not self.EXPECTED_SELECTORS:
            return False
        soup = BeautifulSoup(html, "lxml")
        present = [sel for sel in self.EXPECTED_SELECTORS if soup.select(sel)]
        ratio = len(present) / len(self.EXPECTED_SELECTORS)
        if ratio < self.SELECTOR_THRESHOLD_PCT:
            return True
        if old_fingerprint is None:
            return False
        new_fp = self.compute_fingerprint(html)
        return new_fp != old_fingerprint

    # ── Slack alert ───────────────────────────────────────────────────────────

    async def send_slack_alert(self, message: str):
        from app.config import settings
        if not settings.SLACK_BOT_TOKEN:
            return
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
                    json={"channel": settings.SLACK_ALERT_CHANNEL, "text": message},
                )
        except Exception as e:
            logger.warning(f"Slack alert failed: {e}")

    # ── DB helpers ────────────────────────────────────────────────────────────

    async def _ensure_manufacturer(self) -> Manufacturer:
        result = await self.db.execute(
            select(Manufacturer).where(Manufacturer.slug == self.MANUFACTURER_SLUG)
        )
        m = result.scalar_one_or_none()
        if not m:
            m = Manufacturer(
                slug=self.MANUFACTURER_SLUG,
                name=self.MANUFACTURER_NAME,
                country=self.MANUFACTURER_COUNTRY,
                color=self.MANUFACTURER_COLOR,
                website_url=self.WEBSITE_URL,
            )
            self.db.add(m)
            await self.db.flush()
        return m

    async def _ensure_health(self, manufacturer: Manufacturer) -> ScraperHealth:
        result = await self.db.execute(
            select(ScraperHealth).where(ScraperHealth.manufacturer_id == manufacturer.id)
        )
        h = result.scalar_one_or_none()
        if not h:
            h = ScraperHealth(manufacturer_id=manufacturer.id)
            self.db.add(h)
            await self.db.flush()
        return h

    async def _upsert_variant(self, manufacturer: Manufacturer, sv: ScrapedVariant) -> Variant:
        model_slug = re.sub(r"[^a-z0-9]+", "-", sv.model_name.lower()).strip("-")

        result = await self.db.execute(
            select(VehicleModel).where(
                VehicleModel.manufacturer_id == manufacturer.id,
                VehicleModel.slug == model_slug,
            )
        )
        model = result.scalar_one_or_none()
        if not model:
            model = VehicleModel(
                manufacturer_id=manufacturer.id,
                slug=model_slug,
                name=sv.model_name,
            )
            self.db.add(model)
            await self.db.flush()

        result = await self.db.execute(
            select(Variant).where(
                Variant.model_id == model.id,
                Variant.name == sv.variant_name,
            )
        )
        variant = result.scalar_one_or_none()
        if not variant:
            variant = Variant(model_id=model.id, name=sv.variant_name)
            self.db.add(variant)
            await self.db.flush()

        return variant

    # ── Run (orchestrate) ─────────────────────────────────────────────────────

    async def run(self) -> dict:
        manufacturer = await self._ensure_manufacturer()
        health = await self._ensure_health(manufacturer)
        health.last_run_at = datetime.now(timezone.utc)

        try:
            scraped = await self.scrape()
        except Exception as e:
            logger.error(f"[{self.MANUFACTURER_SLUG}] scrape() raised: {e}")
            health.status = "error"
            health.last_error = str(e)
            await self.db.commit()
            await self.send_slack_alert(
                f":warning: *ev-prices* — scraper `{self.MANUFACTURER_SLUG}` en erreur :\n```{e}```"
            )
            return {"status": "error", "manufacturer": self.MANUFACTURER_SLUG, "error": str(e)}

        if not scraped:
            health.status = "error"
            health.last_error = "Aucun prix extrait"
            await self.db.commit()
            await self.send_slack_alert(
                f":warning: *ev-prices* — scraper `{self.MANUFACTURER_SLUG}` : aucun prix extrait. "
                f"Le site a peut-être changé de structure."
            )
            return {"status": "error", "manufacturer": self.MANUFACTURER_SLUG, "error": "no prices"}

        for sv in scraped:
            variant = await self._upsert_variant(manufacturer, sv)
            snapshot = PriceSnapshot(
                variant_id=variant.id,
                price_euros=sv.price_euros,
            )
            self.db.add(snapshot)

        health.last_success_at = datetime.now(timezone.utc)
        health.last_error = None
        health.variants_found = len(scraped)
        health.status = "ok"

        await self.db.commit()
        logger.info(f"[{self.MANUFACTURER_SLUG}] OK — {len(scraped)} variantes enregistrées")
        return {"status": "ok", "manufacturer": self.MANUFACTURER_SLUG, "variants": len(scraped)}

    async def run_with_change_detection(self, html: str) -> bool:
        """
        Call from scrape() after fetching HTML.
        Returns True if a structural change is detected (scraper may need update).
        Sends Slack alert and updates health record on first detection.
        """
        manufacturer = await self._ensure_manufacturer()
        health = await self._ensure_health(manufacturer)

        changed = self.detect_change(html, health.page_fingerprint)
        new_fp = self.compute_fingerprint(html)

        if changed and health.alert_sent_at is None:
            health.status = "changed"
            health.alert_sent_at = datetime.now(timezone.utc)
            health.page_fingerprint = new_fp
            await self.db.flush()
            await self.send_slack_alert(
                f":rotating_light: *ev-prices* — le site de `{self.MANUFACTURER_NAME}` "
                f"a changé de structure. Le scraper doit être mis à jour.\n"
                f"URL : {self.WEBSITE_URL}"
            )
        elif not changed:
            health.page_fingerprint = new_fp
            health.alert_sent_at = None
            await self.db.flush()

        return changed
