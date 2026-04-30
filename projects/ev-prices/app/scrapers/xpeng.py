import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class XpengScraper(BaseScraper):
    MANUFACTURER_SLUG = "xpeng"
    MANUFACTURER_NAME = "XPENG"
    MANUFACTURER_COUNTRY = "CN"
    MANUFACTURER_COLOR = "#00b4ff"
    WEBSITE_URL = "https://www.xpeng.com/fr"

    MODELS = [
        ("G6", "https://www.xpeng.com/fr/g6/"),
        ("G9", "https://www.xpeng.com/fr/g9/"),
        ("P7+", "https://www.xpeng.com/fr/p7plus/"),
        ("X9", "https://www.xpeng.com/fr/x9/"),
        ("MONA M03", "https://www.xpeng.com/fr/m03/"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Price']",
        "[class*='config']",
        "[class*='Config']",
        "[class*='variant']",
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

        # XPENG uses React — try config/variant blocks
        for block in soup.select("[class*='config'], [class*='Config'], [class*='variant'], [class*='version'], [class*='trim']"):
            name_el = block.select_one("[class*='name'], [class*='title'], [class*='label'], h2, h3, h4")
            price_el = block.select_one("[class*='price'], [class*='Price'], [class*='amount']")
            if name_el and price_el:
                price = self.parse_price(price_el.get_text())
                if price:
                    variants.append(ScrapedVariant(model_name, name_el.get_text(strip=True), price))

        # Fallback: JSON-LD
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

        # Fallback: inline JSON blobs (Next.js __NEXT_DATA__)
        if not variants:
            for m in re.finditer(r'"price"\s*:\s*["\']?([\d\s\xa0]+)["\']?', html):
                p = self.parse_price(m.group(1))
                if p:
                    variants.append(ScrapedVariant(model_name, model_name, p))
                    break

        return variants
