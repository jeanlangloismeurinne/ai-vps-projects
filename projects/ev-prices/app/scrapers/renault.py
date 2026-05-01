import json
import re
from bs4 import BeautifulSoup

from app.scrapers.base import BaseScraper, ScrapedVariant


class RenaultScraper(BaseScraper):
    MANUFACTURER_SLUG = "renault"
    MANUFACTURER_NAME = "Renault"
    MANUFACTURER_COUNTRY = "FR"
    MANUFACTURER_COLOR = "#efdf00"
    WEBSITE_URL = "https://www.renault.fr"

    MODELS = [
        ("Renault 5 E-Tech", "https://www.renault.fr/vehicules-electriques/r5-e-tech-electrique/pre-configurateur.html"),
        ("Mégane E-Tech", "https://www.renault.fr/vehicules-electriques/megane-e-tech-electrique/configurateur.html"),
        ("Scénic E-Tech", "https://www.renault.fr/vehicules-electriques/scenic-e-tech-electrique/configurateur.html"),
        ("Renault 4 E-Tech", "https://www.renault.fr/vehicules-electriques/r4-e-tech-electrique/pre-configurateur.html"),
        ("Twingo E-Tech", "https://www.renault.fr/vehicules-electriques/twingo-e-tech-electrique/pre-configurateur.html"),
    ]

    EXPECTED_SELECTORS = ["script"]

    async def scrape(self) -> list[ScrapedVariant]:
        results = []
        for model_name, url in self.MODELS:
            try:
                html = await self.fetch_with_playwright(url, wait_selector="body")
                results.extend(self._parse_model(model_name, html))
            except Exception:
                pass
        return results

    def _parse_model(self, model_name: str, html: str) -> list[ScrapedVariant]:
        soup = BeautifulSoup(html, "lxml")
        for script in soup.find_all("script"):
            txt = script.string or ""
            if "window.APP_STATE" not in txt:
                continue
            m = re.search(r'window\.APP_STATE=JSON\.parse\("(.*?)"\);', txt, re.DOTALL)
            if not m:
                continue
            try:
                raw = m.group(1).encode().decode("unicode_escape")
                data = json.loads(raw)
                grades = data["page"]["data"]["modelParams"]["data"]["grades"]
            except Exception:
                continue

            variants = []
            for grade in grades:
                label = grade.get("label", "").strip()
                price = grade.get("minPrice")
                if label and isinstance(price, (int, float)) and 5_000 <= price <= 500_000:
                    variants.append(ScrapedVariant(model_name, label, int(price)))
            return variants

        return []
