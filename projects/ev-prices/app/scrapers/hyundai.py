import re
from bs4 import BeautifulSoup
from app.scrapers.base import BaseScraper, ScrapedVariant


class HyundaiScraper(BaseScraper):
    MANUFACTURER_SLUG = "hyundai"
    MANUFACTURER_NAME = "Hyundai"
    MANUFACTURER_COUNTRY = "KR"
    MANUFACTURER_COLOR = "#002c5f"
    WEBSITE_URL = "https://www.hyundai.com/fr"

    MODELS = [
        ("IONIQ 5", "https://www.hyundai.com/fr/voitures/ioniq5/highlights"),
        ("IONIQ 6", "https://www.hyundai.com/fr/voitures/ioniq6/highlights"),
        ("IONIQ 9", "https://www.hyundai.com/fr/voitures/ioniq9/highlights"),
        ("Kona Electric", "https://www.hyundai.com/fr/voitures/kona-electric/highlights"),
        ("INSTER", "https://www.hyundai.com/fr/voitures/inster/highlights"),
    ]

    EXPECTED_SELECTORS = [
        "[class*='price']",
        "[class*='Price']",
        "[class*='trim']",
        "[class*='Trim']",
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

        for block in soup.select("[class*='trim-item'], [class*='TrimItem'], [class*='grade-item'], [class*='GradeItem']"):
            name_el = block.select_one("[class*='trim-name'], [class*='grade-name'], [class*='title'], h2, h3, h4")
            price_el = block.select_one("[class*='price'], [class*='Price']")
            if name_el and price_el:
                price = self.parse_price(price_el.get_text())
                if price:
                    variants.append(ScrapedVariant(model_name, name_el.get_text(strip=True), price))

        if not variants:
            for m in re.finditer(r'"trimName"\s*:\s*"([^"]+)".*?"price"\s*:\s*(\d+)', html, re.DOTALL):
                p = int(m.group(2))
                if 20_000 <= p <= 200_000:
                    variants.append(ScrapedVariant(model_name, m.group(1), p))

        return variants
