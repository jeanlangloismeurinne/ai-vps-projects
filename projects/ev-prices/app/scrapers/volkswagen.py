import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class VolkswagenScraper(BaseScraper):
    MANUFACTURER_SLUG = "volkswagen"
    MANUFACTURER_NAME = "Volkswagen"
    MANUFACTURER_COUNTRY = "DE"
    MANUFACTURER_COLOR = "#001e50"
    WEBSITE_URL = "https://www.volkswagen.fr"

    MODELS = [
        ("ID.3", "https://www.volkswagen.fr/fr/modeles/id3.html"),
        ("ID.4", "https://www.volkswagen.fr/fr/modeles/id4.html"),
        ("ID.5", "https://www.volkswagen.fr/fr/modeles/id5.html"),
        ("ID.7", "https://www.volkswagen.fr/fr/modeles/id7.html"),
        ("ID.7 Tourer", "https://www.volkswagen.fr/fr/modeles/id7-tourer.html"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Price']",
        "[class*='grade']",
        "[class*='Grade']",
        "[class*='version']",
        "[data-testid*='price']",
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

        # VW uses data attributes and class patterns
        for block in soup.select("[class*='grade'], [class*='Grade'], [class*='trim'], [class*='version']"):
            name_el = block.select_one("[class*='name'], [class*='title'], h2, h3, h4")
            price_el = block.select_one("[class*='price'], [class*='Price']")
            if name_el and price_el:
                price = self.parse_price(price_el.get_text())
                if price:
                    variants.append(ScrapedVariant(model_name, name_el.get_text(strip=True), price))

        if not variants:
            # VW embeds data in JSON scripts
            for m in re.finditer(r'"gradeName"\s*:\s*"([^"]+)".*?"price"\s*:\s*\{[^}]*"value"\s*:\s*(\d+)', html, re.DOTALL):
                grade, price_str = m.group(1), m.group(2)
                p = int(price_str)
                if 20_000 <= p <= 200_000:
                    variants.append(ScrapedVariant(model_name, grade, p))

        return variants
