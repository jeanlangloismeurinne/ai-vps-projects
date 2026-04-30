import re
import json
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class TeslaScraper(BaseScraper):
    MANUFACTURER_SLUG = "tesla"
    MANUFACTURER_NAME = "Tesla"
    MANUFACTURER_COUNTRY = "US"
    MANUFACTURER_COLOR = "#e31937"
    WEBSITE_URL = "https://www.tesla.com/fr_FR"

    # Tesla embeds prices in inline JS/JSON — use API endpoint
    MODELS = [
        ("Model 3", "https://www.tesla.com/fr_FR/model3/design#overview"),
        ("Model Y", "https://www.tesla.com/fr_FR/modely/design#overview"),
        ("Model S", "https://www.tesla.com/fr_FR/models/design#overview"),
        ("Model X", "https://www.tesla.com/fr_FR/modelx/design#overview"),
        ("Cybertruck", "https://www.tesla.com/fr_FR/cybertruck/design#overview"),
    ]

    # Tesla uses React — no stable CSS selectors, we use JSON extraction
    EXPECTED_SELECTORS = [
        "[data-id='payment-container']",
        ".group--options_block",
        "[class*='options-block']",
        "script[type='application/ld+json']",
    ]

    async def scrape(self) -> list[ScrapedVariant]:
        results = []
        for model_name, url in self.MODELS:
            try:
                html = await self.fetch_with_playwright(url, wait_selector="body")
                await self.run_with_change_detection(html)
                results.extend(self._parse_model(model_name, html))
            except Exception:
                pass
        return results

    def _parse_model(self, model_name: str, html: str) -> list[ScrapedVariant]:
        variants = []

        # Tesla embeds window.__INITIAL_STATE__ or similar JSON blobs
        patterns = [
            r'"basePrice"\s*:\s*(\d+)',
            r'"price"\s*:\s*(\d+)',
            r'"totalPrice"\s*:\s*(\d+)',
            r'"startingPrice"\s*:\s*(\d+)',
        ]
        prices_found = set()
        for pat in patterns:
            for m in re.finditer(pat, html):
                p = int(m.group(1))
                if 20_000 <= p <= 300_000:
                    prices_found.add(p)

        # Try to extract trim names from inline JSON
        trim_pattern = re.finditer(r'"trimName"\s*:\s*"([^"]+)".*?"price"\s*:\s*(\d+)', html, re.DOTALL)
        for m in trim_pattern:
            trim, price_str = m.group(1), m.group(2)
            p = int(price_str)
            if 20_000 <= p <= 300_000:
                variants.append(ScrapedVariant(model_name, trim, p))
                prices_found.discard(p)

        # Remaining prices without trim name → use model name as variant
        for p in sorted(prices_found):
            if not any(v.price_euros == p for v in variants):
                variants.append(ScrapedVariant(model_name, model_name, p))

        # Fallback: visible price elements
        if not variants:
            soup = BeautifulSoup(html, "lxml")
            for el in soup.select("[class*='price'], [data-testid*='price']"):
                p = self.parse_price(el.get_text())
                if p:
                    variants.append(ScrapedVariant(model_name, model_name, p))
                    break

        return variants
