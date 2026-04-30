import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class MGScraper(BaseScraper):
    MANUFACTURER_SLUG = "mg"
    MANUFACTURER_NAME = "MG Motor"
    MANUFACTURER_COUNTRY = "CN"
    MANUFACTURER_COLOR = "#b5121b"
    WEBSITE_URL = "https://www.mgmotor.fr"

    MODELS = [
        ("MG4", "https://www.mgmotor.fr/models/mg4"),
        ("MG ZS EV", "https://www.mgmotor.fr/models/mg-zs-ev"),
        ("MG5 EV", "https://www.mgmotor.fr/models/mg5-ev"),
        ("Marvel R", "https://www.mgmotor.fr/models/marvel-r"),
        ("MG EHS", "https://www.mgmotor.fr/models/mg-ehs"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Price']",
        "[class*='variant']",
        "[class*='grade']",
        "[class*='trim']",
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

        for block in soup.select("[class*='grade'], [class*='trim'], [class*='variant'], [class*='version']"):
            name_el = block.select_one("[class*='name'], [class*='title'], h2, h3, h4")
            price_el = block.select_one("[class*='price'], [class*='Price']")
            if name_el and price_el:
                price = self.parse_price(price_el.get_text())
                if price:
                    variants.append(ScrapedVariant(model_name, name_el.get_text(strip=True), price))

        if not variants:
            for item in self.extract_jsonld(html):
                if item.get("@type") in ("Car", "Product"):
                    offers = item.get("offers", {})
                    if not isinstance(offers, list):
                        offers = [offers]
                    for offer in offers:
                        p = self.parse_price(str(offer.get("price", "")))
                        if p:
                            variants.append(ScrapedVariant(model_name, offer.get("name", model_name), p))

        return variants
