from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class CitroenScraper(BaseScraper):
    MANUFACTURER_SLUG = "citroen"
    MANUFACTURER_NAME = "Citroën"
    MANUFACTURER_COUNTRY = "FR"
    MANUFACTURER_COLOR = "#c5002b"
    WEBSITE_URL = "https://www.citroen.fr"

    MODELS = [
        ("ë-C3", "https://www.citroen.fr/voitures/nouvelle-citroen-e-c3.html"),
        ("ë-C3 Aircross", "https://www.citroen.fr/voitures/nouvelle-citroen-e-c3-aircross.html"),
        ("ë-Berlingo", "https://www.citroen.fr/voitures/citroen-e-berlingo.html"),
        ("ë-C4", "https://www.citroen.fr/voitures/citroen-e-c4.html"),
        ("ë-SpaceTourer", "https://www.citroen.fr/voitures/citroen-e-spacetourer.html"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='version']",
        "[class*='finition']",
        "[class*='motorisation']",
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

        # Stellantis shared CMS — same pattern as Peugeot
        for block in soup.select("[class*='version-item'], [class*='VersionItem'], [class*='finition-item'], [class*='grade-item']"):
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
