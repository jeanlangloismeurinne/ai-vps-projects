from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class DaciaScraper(BaseScraper):
    MANUFACTURER_SLUG = "dacia"
    MANUFACTURER_NAME = "Dacia"
    MANUFACTURER_COUNTRY = "FR"
    MANUFACTURER_COLOR = "#005b99"
    WEBSITE_URL = "https://www.dacia.fr"

    MODELS = [
        ("Spring", "https://www.dacia.fr/nos-vehicules/spring.html"),
        ("Spring Adventure", "https://www.dacia.fr/nos-vehicules/spring.html"),
        ("Sandero E-Tech", "https://www.dacia.fr/nos-vehicules/sandero.html"),
        ("Jogger E-Tech", "https://www.dacia.fr/nos-vehicules/jogger.html"),
        ("Duster E-Tech", "https://www.dacia.fr/nos-vehicules/duster.html"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='version']",
        "[class*='finition']",
        "[class*='motorisation']",
    ]

    async def scrape(self) -> list[ScrapedVariant]:
        results = []
        seen_urls = set()
        for model_name, url in self.MODELS:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            try:
                html = await self.fetch_with_playwright(url, wait_selector="body")
                await self.run_with_change_detection(html)
                results.extend(self._parse_page(html, model_name))
            except Exception:
                pass
        return results

    def _parse_page(self, html: str, default_model: str) -> list[ScrapedVariant]:
        soup = BeautifulSoup(html, "lxml")
        variants = []

        for block in soup.select("[class*='version'], [class*='finition'], [class*='grade']"):
            name_el = block.select_one("h2, h3, h4, [class*='name'], [class*='title']")
            price_el = block.select_one("[class*='price'], [class*='Price'], [class*='tarif']")
            if name_el and price_el:
                price = self.parse_price(price_el.get_text())
                if price:
                    variants.append(ScrapedVariant(default_model, name_el.get_text(strip=True), price))

        if not variants:
            for item in self.extract_jsonld(html):
                if item.get("@type") in ("Car", "Product"):
                    offers = item.get("offers", {})
                    if not isinstance(offers, list):
                        offers = [offers]
                    for offer in offers:
                        p = self.parse_price(str(offer.get("price", "")))
                        if p:
                            variants.append(ScrapedVariant(default_model, offer.get("name", default_model), p))

        return variants
