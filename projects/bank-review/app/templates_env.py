from fastapi.templating import Jinja2Templates
from urllib.parse import quote

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


def _m_cell_style(m: dict, is_income: bool) -> str:
    if m.get("is_future") or m.get("actual", 0) == 0:
        return ""
    v = m.get("variance", 0)
    budget = abs(m.get("budget", 1) or 1)
    if v >= 0:
        alpha = min(0.08 + (v / budget) * 0.50, 0.56)
        return f"background:rgba(var(--cell-green-rgb),{alpha:.2f})"
    elif v >= -budget * 0.2:
        ratio = abs(v) / (budget * 0.2)
        alpha = 0.08 + ratio * 0.18
        return f"background:rgba(var(--cell-yellow-rgb),{alpha:.2f})"
    else:
        over = (abs(v) / budget) - 0.2
        alpha = min(0.15 + over * 0.60, 0.65)
        return f"background:rgba(var(--cell-red-rgb),{alpha:.2f})"


def _fmtnum(v, decimals=0):
    try:
        v = float(v)
        s = f"{v:,.{decimals}f}"
        if decimals > 0:
            int_part, dec_part = s.rsplit(".", 1)
            return int_part.replace(",", "\u202f") + "," + dec_part
        return s.replace(",", "\u202f")
    except (TypeError, ValueError):
        return str(v)


templates.env.globals["m_status"] = _m_status
templates.env.globals["m_cell_style"] = _m_cell_style
templates.env.filters["fmtnum"] = _fmtnum
templates.env.filters["urlencode"] = lambda v: quote(str(v), safe="")
