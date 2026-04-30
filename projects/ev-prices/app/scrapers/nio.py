import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class NIOScraper(BaseScraper):
    MANUFACTURER_SLUG = "nio"
    MANUFACTURER_NAME = "NIO"
    MANUFACTURER_COUNTRY = "CN"
    MANUFACTURER_COLOR = "#00c8ff"
    WEBSITE_URL = "https://www.nio.com/fr"

    MODELS = [
        ("ET5", "https://www.nio.com/fr/et5"),
        ("ET5 Touring", "https://www.nio.com/fr/et5-touring"),
        ("ET7", "https://www.nio.com/fr/et7"),
        ("EL6", "https://www.nio.com/fr/el6"),
        ("EL7", "https://www.nio.com/fr/el7"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Price']",
        "[class*='config']",
        "[class*='Config']",
        "[class*='spec']",
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
        soup = BeautifulSoup(html, "lxml")
        variants = []

        for block in soup.select("[class*='config'], [class*='Config'], [class*='variant'], [class*='edition']"):
            name_el = block.select_one("[class*='name'], [class*='title'], [class*='label'], h2, h3, h4")
            price_el = block.select_one("[class*='price'], [class*='Price'], [class*='amount']")
            if name_el and price_el:
                price = self.parse_price(price_el.get_text())
                if price:
                    variants.append(ScrapedVariant(model_name, name_el.get_text(strip=True), price))

        if not variants:
            # NIO often uses Next.js with JSON in __NEXT_DATA__
            for m in re.finditer(r'"price"\s*:\s*\{[^}]*"amount"\s*:\s*(\d+)', html):
                p = int(m.group(1))
                if 30_000 <= p <= 200_000:
                    variants.append(ScrapedVariant(model_name, model_name, p))
                    break

        return variants
