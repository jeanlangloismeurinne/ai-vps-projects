"""Valeur du temps passé, version CAC 40 : les SOURCES seulement (sous-projet `00-REPRISE-CAC40.md`).

Aucune formule ici : plancher, caduc, décomposition et PER à terme restent dans `valeur.py`, détenteur unique.
Ce module dit seulement ce que valent, pour une société européenne, les trois ingrédients du calcul :
  bénéfice    = BPA dilué ANNUEL (les sociétés européennes publient par semestre ; l'ESEF ne porte que l'annuel),
                connu 4 mois après la clôture (délai légal du rapport financier annuel) ; ESEF d'abord (le
                chiffre publié à l'époque, via filings.xbrl.org), Yahoo `income_stmt` en repli ;
  inflation   = indice des prix harmonisé France (FRED CP0000FRM086NEST), décalé d'un mois de publication ;
  référence   = S&P 500 dividendes réinvestis converti en euros (^SP500TR ÷ EURUSD).
Les comptes ESEF commencent en 2020-2021 : seules les périodes 3 et 5 ans ont un sens (`valeur.MARKETS`).
"""
from __future__ import annotations

import asyncio
import io
import logging
import urllib.request
from datetime import datetime, timezone

import pandas as pd

from app.db.database import get_db_session
from app.nasdaq import valeur as V

logger = logging.getLogger(__name__)

MARKET = "cac40"
AVAIL_MONTHS = 4
GAP_WARN = 0.05
# Un facteur 10 entre deux chiffres d'un même exercice n'est pas une différence de comptabilité (IFRS 17, cession,
# normes : au plus ×2 au sondage) mais une erreur d'échelle du dépôt (TotalEnergies 2022 : tout le dépôt ÷ 100 ;
# Capgemini 2022 : 8 790 000 € par action).
SCALE = 10
# Une erreur d'échelle répétée par les dépôts suivants (Crédit Agricole : dépôts 2020 ET 2021 en millions, 804 000 €
# par action pour 2020) n'a pas de chiffre sain pour la démentir : elle se voit dans la série du titre. Seul le sens
# « trop grand » se juge — un bénéfice proche de zéro est réel (Safran 2021 : 0,10 €) ; plus forte variation réelle
# mesurée au sondage : ×13 la médiane (Renault 2025).
OUTLIER = 100
ESEF = "https://filings.xbrl.org"
# Premier concept présent dans le dépôt : Bouygues ne déclare que le BPA « des activités poursuivies ».
EPS_CONCEPTS = ("DilutedEarningsLossPerShare", "BasicEarningsLossPerShare",
                "DilutedEarningsLossPerShareFromContinuingOperations",
                "BasicEarningsLossPerShareFromContinuingOperations")

# Composition relevée le 2026-11-22 (cotation Boursier du 06/11/2026) : inchangée depuis le 22/12/2025 (entrée
# d'Eiffage, sortie d'Edenred), revues de mars, juin et septembre 2026 sans changement. Prochaine revue Euronext :
# 10/12/2026, effet le 21/12/2026 — à relever alors, jamais à écrire de mémoire.
# (symbole Yahoo, nom, ISIN, LEI — le LEI, relevé au GLEIF par l'ISIN, identifie la société dans filings.xbrl.org ;
# le nom n'est pas stable. ArcelorMittal : LEI de la société mère, l'ISIN n'y est pas rattaché au GLEIF.)
CAC40_AS_OF = "2026-11-06"
CAC40 = (
    ("AC.PA", "Accor", "FR0000120404", "969500QZC2Q0TK11NV07"),
    ("AI.PA", "Air Liquide", "FR0000120073", "969500MMPQVHK671GT54"),
    ("AIR.PA", "Airbus", "NL0000235190", "MINO79WLOO247M1IL051"),
    ("MT.AS", "ArcelorMittal", "LU1598757687", "2EULGUTUI56JI9SAL165"),
    ("CS.PA", "AXA", "FR0000120628", "F5WCUMTUM4RKZ1MAIE39"),
    ("BNP.PA", "BNP Paribas", "FR0000131104", "R0MUWSFPU8MPRO8K5P83"),
    ("EN.PA", "Bouygues", "FR0000120503", "969500MOCLNQFNZN0D63"),
    ("BVI.PA", "Bureau Veritas", "FR0006174348", "969500TPU5T3HA5D1F11"),
    ("CAP.PA", "Capgemini", "FR0000125338", "96950077L0TN7BAROX36"),
    ("CA.PA", "Carrefour", "FR0000120172", "549300B8P6MUJ1YWTS08"),
    ("ACA.PA", "Crédit Agricole", "FR0000045072", "969500TJ5KRTCJQWXH05"),
    ("BN.PA", "Danone", "FR0000120644", "969500KMUQ2B6CBAF162"),
    ("DSY.PA", "Dassault Systèmes", "FR0014003TT8", "96950065LBWY0APQIM86"),
    ("FGR.PA", "Eiffage", "FR0000130452", "969500OQXKE5WDM9M994"),
    ("ENGI.PA", "Engie", "FR0010208488", "LAXUQCHT4FH58LRZDY46"),
    ("EL.PA", "EssilorLuxottica", "FR0000121667", "549300M3VH1A3ER1TB49"),
    ("ERF.PA", "Eurofins Scientific", "FR0014000MR3", "529900JEHFM47DYY3S57"),
    ("ENX.PA", "Euronext", "NL0006294274", "724500QJ4QSZ3H9QU415"),
    ("RMS.PA", "Hermès", "FR0000052292", "969500Y4IJGHJE2MTJ13"),
    ("KER.PA", "Kering", "FR0000121485", "549300VGEJKB7SVUZR78"),
    ("LR.PA", "Legrand", "FR0010307819", "969500XXRPGD7HCAFA90"),
    ("OR.PA", "L'Oréal", "FR0000120321", "529900JI1GG6F7RKVI53"),
    ("MC.PA", "LVMH", "FR0000121014", "IOG4E947OATN0KJYSD45"),
    ("ML.PA", "Michelin", "FR001400AJ45", "549300SOSI58J6VIW052"),
    ("ORA.PA", "Orange", "FR0000133308", "969500MCOONR8990S771"),
    ("RI.PA", "Pernod Ricard", "FR0000120693", "52990097YFPX9J0H5D87"),
    ("PUB.PA", "Publicis", "FR0000130577", "2138004KW8BV57III342"),
    ("RNO.PA", "Renault", "FR0000131906", "969500F7JLTX36OUI695"),
    ("SAF.PA", "Safran", "FR0000073272", "969500UIC89GT3UL7L24"),
    ("SGO.PA", "Saint-Gobain", "FR0000125007", "NFONVGN05Z0FMN5PEC35"),
    ("SAN.PA", "Sanofi", "FR0000120578", "549300E9PC51EN656011"),
    ("SU.PA", "Schneider Electric", "FR0000121972", "969500A1YF1XUYYXS284"),
    ("GLE.PA", "Société Générale", "FR0000130809", "O2RNE8IBXP4R0TD8PU41"),
    ("STLAP.PA", "Stellantis", "NL00150001Q9", "549300LKT9PW7ZIBDF31"),
    ("STMPA.PA", "STMicroelectronics", "NL0000226223", "213800Z8NOHIKRI42W10"),
    ("HO.PA", "Thales", "FR0000121329", "529900FNDVTQJOVVPZ19"),
    ("TTE.PA", "TotalEnergies", "FR0000120271", "529900S21EQ1BO4ESM68"),
    ("URW.PA", "Unibail-Rodamco-Westfield", "FR0013326246", "969500SHQITWXSIS7N89"),
    ("VIE.PA", "Veolia", "FR0000124141", "969500LENY69X51OOT31"),
    ("DG.PA", "Vinci", "FR0000125486", "213800WFQ334R8UXUG83"),
)
EXTRA = (
    ("MRN.PA", "Mersen", "FR0000039620", "OQXDLNM5DTBULYMF5U27"),
    ("PUM.DE", "Puma", "DE0006969603", "529900GRZ2BQY5ZM9N49"),  # aucun dépôt ESEF (Allemagne) : Yahoo seul
)
UNIVERSE = {s: (name, isin, lei) for s, name, isin, lei in CAC40 + EXTRA}

state: dict = {"running": False, "error": None, "done": 0, "total": 0, "finished_at": None}


# ───────────────────────────── fonctions pures ─────────────────────────────

def esef_eps(doc: dict | None) -> dict[str, list]:
    """{clôture : [BPA, devise]} d'un dépôt xBRL-JSON : premier concept de `EPS_CONCEPTS` présent, contexte sans
    dimension, durée d'un an. ⚠️ En xBRL-JSON la fin de période est EXCLUSIVE : « 2025-01-01 » clôt l'exercice 2024."""
    by: dict[str, dict] = {}
    for f in (doc or {}).get("facts", {}).values():
        dm = f.get("dimensions", {})
        c = dm.get("concept", "")
        name = c.split(":", 1)[-1]
        if not c.startswith("ifrs-full:") or name not in EPS_CONCEPTS:
            continue
        if set(dm) - {"concept", "entity", "period", "unit", "language"} or "/" not in dm.get("period", ""):
            continue
        a, b = dm["period"].split("/")
        if not 340 <= (pd.Timestamp(b) - pd.Timestamp(a)).days <= 380:
            continue
        try:
            v = float(f["value"])
        except (TypeError, ValueError, KeyError):
            continue
        end = (pd.Timestamp(b) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        cur = (dm.get("unit") or "").split("/")[0].replace("iso4217:", "")
        by.setdefault(name, {})[end] = [v, cur]
    return next((by[n] for n in EPS_CONCEPTS if n in by), {})


def avail_date(end: str) -> str:
    """Un exercice est connu à la fin du 4ᵉ mois après sa clôture, jamais à la clôture (ni à la date d'indexation
    de filings.xbrl.org, qui peut être très postérieure : rattrapages)."""
    return (pd.Period(end[:7], "M") + AVAIL_MONTHS).end_time.strftime("%Y-%m-%d")


def scale_error(a: float | None, b: float | None) -> bool:
    return bool(a and b) and not (1 / SCALE < abs(a / b) < SCALE)


def first_published(filings: list) -> list[dict]:
    """`filings` = [[clôture du dépôt, esef_eps(doc)], …]. Chaque exercice prend le chiffre du plus ancien dépôt qui le
    porte : celui de CET exercice (publié à l'époque — un dépôt antérieur ne peut pas le contenir), ou à défaut, pour le
    premier exercice, le comparatif du dépôt suivant.
    `filed` est la publication du DÉPÔT source : un comparatif est déjà retraité des divisions antérieures à son dépôt
    (Air Liquide 2023 n'existe qu'au dépôt 2024, déjà sur la base de l'attribution de juin 2024).
    Un chiffre en erreur d'échelle (`SCALE`) avec le dépôt suivant qui le répète cède devant ce dernier."""
    seen: dict[str, list[dict]] = {}
    for pe, eps in sorted(filings, key=lambda x: x[0]):
        for end, (v, cur) in eps.items():
            seen.setdefault(end, []).append({"end": end, "v": v, "cur": cur, "src": "esef",
                                             "own": end[:7] == pe[:7], "filed": avail_date(pe)})
    out = []
    for end, cands in sorted(seen.items()):
        pick = cands[0]
        later = [c for c in cands if c["filed"] > pick["filed"] and c["cur"] == pick["cur"]]
        if later and scale_error(pick["v"], later[0]["v"]):
            pick = {**later[0], "scale": pick["v"]}
        out.append(pick)
    return out


def adjust_esef(points: list[dict], splits: list) -> list[dict]:
    """Ramène chaque BPA ESEF au nombre d'actions d'aujourd'hui selon la date de publication de SON dépôt (`filed`,
    posé par `first_published` ; règle : `valeur.adjust_splits`). Yahoo, lui, retraite déjà ses BPA des divisions : il
    n'en subit aucune. Cas réel du sondage : Air Liquide 2022, 5,27 € publiés, 4,36 € chez Yahoo — les attributions
    gratuites de 2024 et 2026 (×1,1²)."""
    return V.adjust_splits(points, splits)


def yahoo_points(annual: dict, cur: str) -> list[dict]:
    return [{"end": e, "v": v, "cur": cur, "src": "yahoo"} for e, v in sorted(annual.items()) if v is not None and v == v]


def merge(esef: list[dict], yahoo: list[dict]) -> tuple[list[dict], list[str]]:
    """ESEF (déjà ajusté) d'abord, Yahoo comble les exercices absents (Puma, Kering après 2023). Sur un exercice
    commun, un écart de plus de 5 % se signale : on garde l'ESEF, l'écart se lit dans la note du titre — sauf erreur
    d'échelle (`SCALE`), où Yahoo remplace le chiffre du dépôt, et la note le dit."""
    by = {p["end"][:7]: p for p in esef}
    warn = [f"{p['end'][:4]} : ESEF {p['scale']:,.2f} écarté (erreur d'échelle), repris du dépôt suivant {p['v']:.2f}".replace(",", " ")
            for p in esef if "scale" in p]
    for y in yahoo:
        k = y["end"][:7]
        e = by.get(k)
        if e is None:
            by[k] = y
        elif e["cur"] == y["cur"] and scale_error(e["v"], y["v"]):
            by[k] = {**y, "scale": e["v"]}
            warn.append(f"{k[:4]} : ESEF {e['v']:,.2f} écarté (erreur d'échelle), Yahoo {y['v']:.2f}".replace(",", " "))
        elif e["cur"] == y["cur"] and abs(y["v"] - e["v"]) > GAP_WARN * max(abs(e["v"]), 1e-9):
            warn.append(f"{k[:4]} : ESEF {e['v']:.2f} / Yahoo {y['v']:.2f}")
    return [by[k] for k in sorted(by)], warn


def drop_outliers(points: list[dict]) -> tuple[list[dict], list[str]]:
    """Retire les BPA au moins `OUTLIER` fois plus grands (en valeur absolue) que la médiane de la série du titre."""
    vals = sorted(abs(p["v"]) for p in points)
    if len(vals) < 3 or not vals[len(vals) // 2]:
        return points, []
    med = vals[len(vals) // 2]
    out = [p for p in points if abs(p["v"]) < OUTLIER * med]
    warn = [f"{p['end'][:4]} : {p['v']:,.2f} écarté (hors d'échelle de la série)".replace(",", " ")
            for p in points if abs(p["v"]) >= OUTLIER * med]
    return out, warn


def cross_check(esef: list[dict], yahoo: list[dict]) -> dict:
    """Contrôle croisé sur le DERNIER exercice commun aux deux sources, même tolérance que le Nasdaq (`valeur.eps_check`).
    Pas contre le bénéfice des 12 derniers mois de Yahoo : un exercice annuel face à un cumul qui inclut le semestre
    suivant écarterait des titres sains (sondage : Accor 1,61 € contre 1,14 €, Sanofi 6,37 € contre 3,46 €).
    Sans exercice commun, le contrôle est impossible : `ok` vaut None (affiché, pas masqué)."""
    ys = {y["end"][:7]: y for y in yahoo}
    # une erreur d'échelle est déjà remplacée par Yahoo (`merge`) : ce n'est plus un exercice à contrôler
    common = [e for e in esef if e["end"][:7] in ys and e["cur"] == ys[e["end"][:7]]["cur"]
              and not scale_error(e["v"], ys[e["end"][:7]]["v"])]
    if not common:
        return {"ok": None}
    e = common[-1]
    y = ys[e["end"][:7]]
    return {"year": e["end"][:4], "ours": e["v"], "yahoo": y["v"], "currency": e["cur"], "ok": V.eps_check(e["v"], y["v"])}


def to_ttm(points: list[dict], fx) -> list[dict]:
    """Chaque exercice daté à sa disponibilité et converti en euros au change du mois de clôture. `fx(devise, mois)`
    → euros par unité, ou None : le point tombe plutôt que d'entrer dans une autre devise."""
    out = []
    for p in points:
        r = 1.0 if p["cur"] == "EUR" else fx(p["cur"], p["end"][:7])
        if r is not None:
            out.append({"end": p["end"], "avail": avail_date(p["end"]), "ttm": p["v"] * r})
    return out


# ───────────────────────────── collecte ─────────────────────────────

def _macro_eur_sync() -> dict:
    import yfinance as yf
    raw = urllib.request.urlopen("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CP0000FRM086NEST", timeout=30).read().decode()
    cpi = pd.read_csv(io.StringIO(raw))
    cpi.columns = ["d", "v"]
    cpi = cpi[pd.to_numeric(cpi.v, errors="coerce").notna()]
    # comme aux États-Unis : l'indice d'un mois n'est publié que le mois suivant
    cpi_m = pd.Series(cpi.v.astype(float).values, index=(pd.PeriodIndex(pd.to_datetime(cpi.d), freq="M") + 1).strftime("%Y-%m"))
    sp = V._monthly_last(yf.download("^SP500TR", start=V.START + "-01", auto_adjust=True, progress=False)["Close"].squeeze())
    eurusd = V._fx_monthly("EUR")
    sp_eur = (sp / eurusd.reindex(sp.index).ffill()).dropna()
    months = [x for x in sorted(set(sp_eur.index) | set(cpi_m.index)) if x >= V.START]
    cpi_f = cpi_m.reindex(months).ffill()
    return {"m": months, "cpi": [None if v != v else float(v) for v in cpi_f.values],
            "sp": [None if v != v else float(v) for v in sp_eur.reindex(months).values]}


def _esef_sync(lei: str, cached: dict | None) -> dict:
    """BPA de chaque dépôt annuel ; rien n'est retéléchargé tant que la liste des dépôts n'a pas changé. Un index
    injoignable n'est PAS « aucun dépôt » (il refuse sous charge, mesuré au sondage) : on garde le cache et on le dit."""
    idx = V._get_json(f"{ESEF}/api/entities/{lei}/filings?page[size]=100")
    if idx is None:
        return {**(cached or {"ids": [], "filings": []}), "error": "index ESEF injoignable"}
    last: dict[str, dict] = {}
    for f in sorted(idx.get("data", []), key=lambda f: f["attributes"].get("date_added") or ""):
        a = f["attributes"]
        if a.get("json_url") and a.get("period_end"):
            last[a["period_end"]] = a  # un dépôt par exercice : le dernier indexé (correction, autre langue)
    want = sorted(a["fxo_id"] for a in last.values())
    if cached and cached.get("ids") == want and not cached.get("error"):
        return cached
    ids, filings = [], []
    for pe, a in sorted(last.items()):
        doc = V._get_json(ESEF + a["json_url"])
        if doc is None:
            continue  # absent de `ids` : retenté au prochain passage
        filings.append([pe, esef_eps(doc)])
        ids.append(a["fxo_id"])
        del doc
    out = {"ids": sorted(ids), "filings": filings}
    if len(ids) < len(want):
        out["error"] = f"{len(want) - len(ids)} dépôt(s) ESEF illisible(s)"
    return out


def _yahoo_eu_sync(symbol: str) -> dict:
    """BPA dilué annuel (4 derniers exercices), bénéfice des 12 derniers mois et consensus à terme, dans leur devise."""
    import math
    import yfinance as yf
    tk = yf.Ticker(symbol)
    res: dict = {}
    try:
        inf = tk.info
        res["trailing_eps"], res["fin_cur"] = inf.get("trailingEps"), inf.get("financialCurrency") or "EUR"
    except Exception:  # noqa: BLE001
        pass
    try:
        ist = tk.income_stmt
        if ist is not None and "Diluted EPS" in ist.index:
            res["annual"] = {c.strftime("%Y-%m-%d"): float(v) for c, v in ist.loc["Diluted EPS"].items() if v == v}
    except Exception:  # noqa: BLE001
        pass
    try:
        ee = tk.earnings_estimate
        if ee is not None and "+1y" in ee.index:
            r = ee.loc["+1y"]
            res.update(fwd_eps=float(r["avg"]), fwd_lo=float(r["low"]), fwd_hi=float(r["high"]),
                       n_analysts=int(r["numberOfAnalysts"]), growth=float(r["growth"]),
                       currency=str(r.get("currency") or "EUR"))
            if "0y" in ee.index:
                res["cur_eps"] = float(ee.loc["0y", "avg"])
    except Exception:  # noqa: BLE001
        pass
    return {k: (None if isinstance(v, float) and not math.isfinite(v) else v) for k, v in res.items()}


class Fx:
    """Euros par unité d'une devise au mois donné (Yahoo publie des dollars par unité : `{cur}USD=X`)."""

    def __init__(self) -> None:
        self.usd_per: dict[str, pd.Series | None] = {"EUR": V._fx_monthly("EUR")}

    def __call__(self, cur: str, month: str) -> float | None:
        if cur == "EUR":
            return 1.0
        if cur != "USD" and cur not in self.usd_per:
            self.usd_per[cur] = V._fx_monthly(cur)
        num = 1.0 if cur == "USD" else self.usd_per.get(cur)
        den = self.usd_per.get("EUR")
        if num is None or den is None or not len(den) or month < den.index[0]:
            return None
        return (num if isinstance(num, float) else V._fx_at(num, month)) / V._fx_at(den, month)


def build(symbol: str, pr: dict | None, esef_cached: dict | None, fx: Fx) -> tuple[dict, str | None, dict]:
    """Tout le calcul d'un titre, sans base : → (payload, note, consensus en euros). Sert au rafraîchissement et au
    passage à blanc."""
    name, _isin, lei = UNIVERSE.get(symbol, (symbol, None, None))
    payload: dict = {"market": MARKET, "name": name}
    esef = _esef_sync(lei, esef_cached) if lei else {"ids": [], "filings": []}
    payload["esef"] = esef
    yh = _yahoo_eu_sync(symbol)
    es = adjust_esef(first_published(esef["filings"]), pr["splits"] if pr else [])
    ys = yahoo_points(yh.get("annual") or {}, yh.get("fin_cur") or "EUR")
    pts, warn = merge(es, ys)
    pts, warn_out = drop_outliers(pts)
    warn += warn_out
    ttm = to_ttm(pts, fx)
    note = None
    if not pr:
        note = "cours bruts indisponibles"
    elif not ttm:
        note = "pas de bénéfice par action (ni ESEF ni Yahoo)" + (f" ; {esef['error']}" if esef.get("error") else "")
    else:
        months = list(pr["p"].index)
        e = V.state_by_month(ttm, months)
        chk = cross_check(es, ys)
        payload.update(m=months, p=[float(x) for x in pr["p"].values],
                       tr=[None if x != x else float(x) for x in pr["tr"].values], e=e,
                       check={**chk, "trailing_yahoo": yh.get("trailing_eps")},
                       sources={"esef": sum(p["src"] == "esef" for p in pts), "yahoo": sum(p["src"] == "yahoo" for p in pts),
                                "last": pts[-1]["end"][:4]},
                       warn=warn)
        notes = []
        if chk["ok"] is False:
            notes.append(f"bénéfice {chk['year']} hors tolérance entre l'ESEF ({chk['ours']:.2f}) et Yahoo ({chk['yahoo']:.2f})")
        if warn:
            notes.append("écarts entre sources (" + " ; ".join(warn) + ")")
        if esef.get("error"):
            notes.append(esef["error"])
        note = " ; ".join(notes) or None
    if yh.get("fwd_eps") is not None and (yh.get("currency") or "EUR") != "EUR":
        r = fx(yh["currency"], pd.Timestamp.today().strftime("%Y-%m"))
        if r is None:
            yh["fwd_eps"] = None  # un consensus dans une autre devise donnerait un PER faux du taux de change
        else:
            for k in ("fwd_eps", "fwd_lo", "fwd_hi", "cur_eps"):
                if yh.get(k) is not None:
                    yh[k] = yh[k] * r
            yh["currency"] = "EUR"
    return payload, note, yh


async def refresh_eu(symbols: list[str] | None = None) -> dict:
    """Recalcule le CAC 40 et les valeurs suivies : comptes ESEF (en cache), BPA Yahoo, cours bruts, consensus."""
    if state["running"]:
        return {"status": "already_running"}
    state.update(running=True, error=None, done=0)
    loop = asyncio.get_running_loop()
    try:
        symbols = symbols or list(UNIVERSE)
        state["total"] = len(symbols)
        macro = await loop.run_in_executor(None, _macro_eur_sync)
        fx = await loop.run_in_executor(None, Fx)
        async with get_db_session() as conn:
            await conn.execute(
                """INSERT INTO nasdaq_macro (series, payload, updated_at) VALUES ($1, $2, now())
                   ON CONFLICT (series) DO UPDATE SET payload=EXCLUDED.payload, updated_at=now()""",
                V.MARKETS[MARKET]["macro"], macro)
            old = {r["ticker"]: r["payload"] for r in await conn.fetch(
                "SELECT ticker, payload FROM nasdaq_valeur_series WHERE ticker = ANY($1::text[])", symbols)}
        n_ok = 0
        for i in range(0, len(symbols), 20):
            chunk = symbols[i:i + 20]
            prices = await loop.run_in_executor(None, V._prices_sync, chunk)
            for s in chunk:
                try:
                    pr = prices.get(s)
                    payload, note, yh = await loop.run_in_executor(None, build, s, pr, (old.get(s) or {}).get("esef"), fx)
                    async with get_db_session() as conn:
                        async with conn.transaction():
                            await conn.execute(
                                """INSERT INTO nasdaq_valeur_series (ticker, payload, note, updated_at) VALUES ($1,$2,$3, now())
                                   ON CONFLICT (ticker) DO UPDATE SET payload=EXCLUDED.payload, note=EXCLUDED.note, updated_at=now()""",
                                s, payload, note)
                            await V.save_forward(conn, s, float(pr["p"].iloc[-1]) if pr else None, yh)
                    n_ok += "m" in payload
                except Exception:  # noqa: BLE001 — un titre raté n'arrête pas les autres
                    logger.exception("valeur europe %s", s)
                state["done"] += 1
            del prices
        state["finished_at"] = datetime.now(timezone.utc).isoformat()
        return {"status": "ok", "tickers": len(symbols), "with_data": n_ok}
    except Exception as ex:  # noqa: BLE001
        state["error"] = f"{type(ex).__name__}: {ex}"
        logger.exception("europe.refresh_eu")
        return {"status": "failed", "error": state["error"]}
    finally:
        state["running"] = False
