import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class KiaScraper(BaseScraper):
    MANUFACTURER_SLUG = "kia"
    MANUFACTURER_NAME = "Kia"
    MANUFACTURER_COUNTRY = "KR"
    MANUFACTURER_COLOR = "#05141f"
    WEBSITE_URL = "https://www.kia.com/fr"

    MODELS = [
        ("EV3", "https://www.kia.com/fr/vehicules/ev3/"),
        ("EV6", "https://www.kia.com/fr/vehicules/ev6/"),
        ("EV9", "https://www.kia.com/fr/vehicules/ev9/"),
        ("Niro EV", "https://www.kia.com/fr/vehicules/niro-ev/"),
        ("EV5", "https://www.kia.com/fr/vehicules/ev5/"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Price']",
        "[class*='grade']",
        "[class*='trim']",
        "[class*='variant']",
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

        for block in soup.select("[class*='grade'], [class*='Grade'], [class*='trim'], [class*='Trim']"):
            name_el = block.select_one("[class*='name'], [class*='title'], [class*='label'], h2, h3, h4")
            price_el = block.select_one("[class*='price'], [class*='Price'], [class*='amount']")
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
