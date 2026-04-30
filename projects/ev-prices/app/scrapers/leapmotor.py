import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class LeapmotorScraper(BaseScraper):
    MANUFACTURER_SLUG = "leapmotor"
    MANUFACTURER_NAME = "Leapmotor"
    MANUFACTURER_COUNTRY = "CN"
    MANUFACTURER_COLOR = "#ff6600"
    WEBSITE_URL = "https://www.leapmotor.fr"

    MODELS = [
        ("T03", "https://www.leapmotor.fr/t03"),
        ("C10", "https://www.leapmotor.fr/c10"),
        ("B10", "https://www.leapmotor.fr/b10"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Price']",
        "[class*='version']",
        "[class*='variant']",
        "[class*='grade']",
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

        for block in soup.select("[class*='version'], [class*='variant'], [class*='grade'], [class*='trim']"):
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

        if not variants:
            # Leapmotor FR — fallback regex
            for m in re.finditer(r'(\d{2}\s?\d{3})\s*€', html):
                p = self.parse_price(m.group(1))
                if p:
                    variants.append(ScrapedVariant(model_name, model_name, p))
                    break

        return variants
