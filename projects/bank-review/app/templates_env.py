from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def _m_status(m: dict, is_income: bool) -> str:
    if m.get("is_future") or m.get("actual", 0) == 0:
        return ""
    v = m.get("variance", 0)
    budget = m.get("budget", 1) or 1
    if v >= 0:
        return "cell-green"
    if v >= -budget * 0.2:
        return "cell-yellow"
    return "cell-red"


templates.env.globals["m_status"] = _m_status
