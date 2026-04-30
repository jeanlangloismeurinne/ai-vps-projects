import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class MercedesScraper(BaseScraper):
    MANUFACTURER_SLUG = "mercedes"
    MANUFACTURER_NAME = "Mercedes-Benz"
    MANUFACTURER_COUNTRY = "DE"
    MANUFACTURER_COLOR = "#00adef"
    WEBSITE_URL = "https://www.mercedes-benz.fr"

    MODELS = [
        ("EQA", "https://www.mercedes-benz.fr/passengercars/mercedes-benz-cars/car-models/eqa/overview.html"),
        ("EQB", "https://www.mercedes-benz.fr/passengercars/mercedes-benz-cars/car-models/eqb/overview.html"),
        ("EQE", "https://www.mercedes-benz.fr/passengercars/mercedes-benz-cars/car-models/eqe-saloon/overview.html"),
        ("EQE SUV", "https://www.mercedes-benz.fr/passengercars/mercedes-benz-cars/car-models/eqe-suv/overview.html"),
        ("EQS", "https://www.mercedes-benz.fr/passengercars/mercedes-benz-cars/car-models/eqs-saloon/overview.html"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Price']",
        "[class*='vehicle-price']",
        "[class*='starting-price']",
        "[data-component='price']",
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

        for block in soup.select("[class*='vehicle-tile'], [class*='model-variant'], [class*='trim-level'], [class*='equipment-line']"):
            name_el = block.select_one("[class*='title'], [class*='name'], [class*='variant-name'], h2, h3, h4")
            price_el = block.select_one("[class*='price'], [class*='Price']")
            if name_el and price_el:
                price = self.parse_price(price_el.get_text())
                if price:
                    variants.append(ScrapedVariant(model_name, name_el.get_text(strip=True), price))

        if not variants:
            for m in re.finditer(r'"variantName"\s*:\s*"([^"]+)".*?"grossPrice"\s*:\s*(\d+(?:\.\d+)?)', html, re.DOTALL):
                p = int(float(m.group(2)))
                if 30_000 <= p <= 300_000:
                    variants.append(ScrapedVariant(model_name, m.group(1), p))

        return variants
