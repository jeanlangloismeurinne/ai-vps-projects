from datetime import datetime, timezone

_state: dict = {
    "active": False,
    "started_at": None,
    "trigger": None,
    "total": 0,
    "done": 0,
    "scrapers": {},
}


def get() -> dict:
    return _state


def start(scraper_classes: list, trigger: str = "manual") -> None:
    _state["active"] = True
    _state["started_at"] = datetime.now(timezone.utc).isoformat()
    _state["trigger"] = trigger
    _state["total"] = len(scraper_classes)
    _state["done"] = 0
    _state["scrapers"] = {
        cls.MANUFACTURER_SLUG: {
            "name": cls.MANUFACTURER_NAME,
            "status": "pending",
            "variants": 0,
            "error": "",
        }
        for cls in scraper_classes
    }


def set_running(slug: str) -> None:
    if slug in _state["scrapers"]:
        _state["scrapers"][slug]["status"] = "running"


def set_done(slug: str, result: dict) -> None:
    if slug not in _state["scrapers"]:
        return
    if result.get("status") == "ok":
        _state["scrapers"][slug]["status"] = "ok"
        _state["scrapers"][slug]["variants"] = result.get("variants", 0)
    else:
        _state["scrapers"][slug]["status"] = "error"
        _state["scrapers"][slug]["error"] = result.get("error", "")
    _state["done"] += 1
    if _state["done"] >= _state["total"]:
        _state["active"] = False
