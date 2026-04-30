import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class BYDScraper(BaseScraper):
    MANUFACTURER_SLUG = "byd"
    MANUFACTURER_NAME = "BYD"
    MANUFACTURER_COUNTRY = "CN"
    MANUFACTURER_COLOR = "#1db954"
    WEBSITE_URL = "https://www.byd.com/fr"

    MODELS = [
        ("Atto 3", "https://www.byd.com/fr/car/atto3.html"),
        ("Seal", "https://www.byd.com/fr/car/seal.html"),
        ("Dolphin", "https://www.byd.com/fr/car/dolphin.html"),
        ("Seal U", "https://www.byd.com/fr/car/seal-u.html"),
        ("Han", "https://www.byd.com/fr/car/han.html"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Price']",
        "[class*='variant']",
        "[class*='version']",
        "[class*='config']",
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

        # BYD FR site structure
        for block in soup.select("[class*='version'], [class*='Version'], [class*='config'], [class*='variant']"):
            name_el = block.select_one("[class*='name'], [class*='title'], [class*='label'], h2, h3, h4")
            price_el = block.select_one("[class*='price'], [class*='Price'], [class*='amount']")
            if name_el and price_el:
                price = self.parse_price(price_el.get_text())
                if price:
                    variants.append(ScrapedVariant(model_name, name_el.get_text(strip=True), price))

        if not variants:
            # BYD embeds prices in JSON blobs or data attributes
            for el in soup.select("[data-price]"):
                p = self.parse_price(el.get("data-price", ""))
                label = el.get("data-name", model_name)
                if p:
                    variants.append(ScrapedVariant(model_name, label, p))

        if not variants:
            for m in re.finditer(r'"price"\s*:\s*["\']?([\d\s]+)["\']?', html):
                p = self.parse_price(m.group(1))
                if p:
                    variants.append(ScrapedVariant(model_name, model_name, p))
                    break

        return variants
