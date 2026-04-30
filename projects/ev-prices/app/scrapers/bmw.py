import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class BMWScraper(BaseScraper):
    MANUFACTURER_SLUG = "bmw"
    MANUFACTURER_NAME = "BMW"
    MANUFACTURER_COUNTRY = "DE"
    MANUFACTURER_COLOR = "#1c69d4"
    WEBSITE_URL = "https://www.bmw.fr"

    MODELS = [
        ("iX1", "https://www.bmw.fr/fr/neufahrzeuge/ix1/suv/2022/bmw-ix1-inspire.html"),
        ("iX2", "https://www.bmw.fr/fr/neufahrzeuge/ix2/suv/2024/bmw-ix2-inspire.html"),
        ("i4", "https://www.bmw.fr/fr/neufahrzeuge/i4/berline/2021/bmw-i4-inspire.html"),
        ("i5", "https://www.bmw.fr/fr/neufahrzeuge/i5/berline/2023/bmw-i5-inspire.html"),
        ("iX", "https://www.bmw.fr/fr/neufahrzeuge/ix/suv/2021/bmw-ix-inspire.html"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Price']",
        "[class*='vehicle-price']",
        "[data-price]",
        "[class*='series-item']",
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

        # BMW uses a list of series/trims with prices
        for block in soup.select("[class*='series-item'], [class*='SeriesItem'], [class*='vehicle-tile'], [class*='VehicleTile']"):
            name_el = block.select_one("[class*='title'], [class*='name'], h2, h3, h4")
            price_el = block.select_one("[class*='price'], [class*='Price'], [data-price]")
            if name_el and price_el:
                price = self.parse_price(price_el.get_text() or price_el.get("data-price", ""))
                if price:
                    variants.append(ScrapedVariant(model_name, name_el.get_text(strip=True), price))

        if not variants:
            for m in re.finditer(r'"series[Nn]ame"\s*:\s*"([^"]+)".*?"price"\s*:\s*(\d+)', html, re.DOTALL):
                p = int(m.group(2))
                if 30_000 <= p <= 200_000:
                    variants.append(ScrapedVariant(model_name, m.group(1), p))

        return variants
