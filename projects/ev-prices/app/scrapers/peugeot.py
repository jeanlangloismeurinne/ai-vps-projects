from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class PeugeotScraper(BaseScraper):
    MANUFACTURER_SLUG = "peugeot"
    MANUFACTURER_NAME = "Peugeot"
    MANUFACTURER_COUNTRY = "FR"
    MANUFACTURER_COLOR = "#003189"
    WEBSITE_URL = "https://www.peugeot.fr"

    MODELS = [
        ("e-208", "https://www.peugeot.fr/voitures/nouvelle-e-208.html"),
        ("e-2008", "https://www.peugeot.fr/voitures/nouveau-e-2008.html"),
        ("e-308", "https://www.peugeot.fr/voitures/nouvelle-e-308.html"),
        ("e-308 SW", "https://www.peugeot.fr/voitures/nouvelle-e-308-sw.html"),
        ("e-408", "https://www.peugeot.fr/voitures/e-408.html"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='version']",
        "[class*='finition']",
        "[data-model-version]",
        ".vehiclePrice",
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

        # Stellantis/Peugeot common structure: version block with name + price
        selectors = [
            "[class*='version-item']",
            "[class*='VersionItem']",
            "[class*='finition-item']",
            "[class*='grade-item']",
            "[class*='model-version']",
        ]
        for sel in selectors:
            for block in soup.select(sel):
                name_el = block.select_one("h2, h3, h4, [class*='name'], [class*='title']")
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
