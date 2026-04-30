import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class RenaultScraper(BaseScraper):
    MANUFACTURER_SLUG = "renault"
    MANUFACTURER_NAME = "Renault"
    MANUFACTURER_COUNTRY = "FR"
    MANUFACTURER_COLOR = "#efdf00"
    WEBSITE_URL = "https://www.renault.fr"

    # Top 5 modèles électriques Renault France
    MODELS = [
        ("Renault 5 E-Tech", "https://www.renault.fr/voitures/nouvelle-renault-5-e-tech-electric.html"),
        ("Mégane E-Tech", "https://www.renault.fr/voitures/megane-e-tech-electric.html"),
        ("Scenic E-Tech", "https://www.renault.fr/voitures/scenic-e-tech-electric.html"),
        ("Renault 4 E-Tech", "https://www.renault.fr/voitures/nouvelle-renault-4-e-tech-electric.html"),
        ("Twingo E-Tech", "https://www.renault.fr/voitures/nouvelle-twingo-e-tech.html"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Prix']",
        "[data-testid*='price']",
        ".vehiclePrice",
        "[class*='version']",
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

        # Renault uses data-testid or class-based price containers
        for block in soup.select("[class*='version'], [class*='Version'], [class*='finition'], [class*='motorisation']"):
            name_el = block.select_one("[class*='name'], [class*='Name'], [class*='title'], h2, h3, h4")
            price_el = block.select_one("[class*='price'], [class*='Price'], [data-testid*='price']")
            if name_el and price_el:
                price = self.parse_price(price_el.get_text())
                if price:
                    variants.append(ScrapedVariant(model_name, name_el.get_text(strip=True), price))

        # Fallback: JSON-LD
        if not variants:
            for item in self.extract_jsonld(html):
                if item.get("@type") in ("Car", "Product") and item.get("offers"):
                    offers = item["offers"]
                    if not isinstance(offers, list):
                        offers = [offers]
                    for offer in offers:
                        price_str = str(offer.get("price", ""))
                        price = self.parse_price(price_str)
                        name = item.get("name", model_name)
                        variant_name = offer.get("name", name)
                        if price:
                            variants.append(ScrapedVariant(model_name, variant_name, price))

        return variants
