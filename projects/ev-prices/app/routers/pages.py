from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import check_session, redirect_to_login
from app.config import settings
from app.database import get_db
from app.models import Manufacturer, ScraperHealth, VehicleModel, Variant

router = APIRouter()

STATUS_COLOR = {"ok": "#2da862", "changed": "#f59e0b", "error": "#ef4444", "never_run": "#555"}
STATUS_LABEL = {"ok": "OK", "changed": "⚠ Changé", "error": "✗ Erreur", "never_run": "—"}
FLAG = {"FR": "🇫🇷", "US": "🇺🇸", "CN": "🇨🇳", "DE": "🇩🇪", "KR": "🇰🇷", "JP": "🇯🇵"}


# ── Base layout ───────────────────────────────────────────────────────────────

def _base(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — EV Prices</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#0f1117;color:#e8e8ea;min-height:100vh}}
a{{color:inherit;text-decoration:none}}
</style>
</head>
<body>
{body}
</body>
</html>"""


# ── Auth shortcut ─────────────────────────────────────────────────────────────

def _auth(request: Request):
    if not check_session(request, settings.SESSION_SECRET):
        return redirect_to_login(str(request.url))
    return None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request, db: AsyncSession = Depends(get_db)):
    if (r := _auth(request)):
        return r

    result = await db.execute(
        select(Manufacturer)
        .options(selectinload(Manufacturer.health))
        .order_by(Manufacturer.country, Manufacturer.name)
    )
    manufacturers = result.scalars().all()

    cards_eu = cards_cn = cards_us = ""
    for m in manufacturers:
        h = m.health
        status = h.status if h else "never_run"
        last_ok = h.last_success_at.strftime("%d/%m/%Y") if h and h.last_success_at else "jamais"
        variants = h.variants_found if h else 0
        badge_color = STATUS_COLOR.get(status, "#555")
        badge_label = STATUS_LABEL.get(status, "—")
        flag = FLAG.get(m.country, "")
        card = f"""
        <a href="/{m.slug}" class="mfr-card" style="--accent:{m.color}">
          <div class="mfr-top">
            <span class="mfr-flag">{flag}</span>
            <span class="mfr-name">{m.name}</span>
            <span class="mfr-badge" style="background:{badge_color}20;color:{badge_color};border:1px solid {badge_color}40">{badge_label}</span>
          </div>
          <div class="mfr-meta">{variants} variantes · dernier scraping {last_ok}</div>
        </a>"""
        if m.country == "CN":
            cards_cn += card
        elif m.country == "US":
            cards_us += card
        else:
            cards_eu += card

    body = f"""
<style>
header{{padding:1.25rem 1.5rem;border-bottom:1px solid #1e2130;display:flex;align-items:center}}
header h1{{font-size:1.1rem;font-weight:600;color:#aaa;flex:1}}
.hub-link{{color:#555;font-size:.8rem;margin-right:1rem}}
.hub-link:hover{{color:#e8e8ea}}
.content{{max-width:1100px;margin:0 auto;padding:2rem 1.5rem}}
h2.section{{font-size:.75rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#555;margin:2rem 0 .75rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:.75rem;margin-bottom:1rem}}
.mfr-card{{background:#1a1d27;border:1px solid #2a2d3a;border-top:3px solid var(--accent);border-radius:12px;
  padding:1rem 1.25rem;transition:border-color .15s,transform .15s;cursor:pointer}}
.mfr-card:hover{{border-color:var(--accent);transform:translateY(-2px)}}
.mfr-top{{display:flex;align-items:center;gap:.5rem;margin-bottom:.35rem}}
.mfr-flag{{font-size:1.1rem}}
.mfr-name{{font-size:.95rem;font-weight:600;flex:1}}
.mfr-badge{{font-size:.7rem;font-weight:600;padding:.15rem .5rem;border-radius:20px}}
.mfr-meta{{font-size:.75rem;color:#666}}
</style>
<header>
  <h1>⚡ EV Prices</h1>
  <a href="/admin" class="hub-link">Admin</a>
  <a href="https://jlmvpscode.duckdns.org" class="hub-link">← Hub</a>
</header>
<div class="content">
  <h2 class="section">🇪🇺 Constructeurs européens</h2>
  <div class="grid">{cards_eu}</div>
  <h2 class="section">🇨🇳 Constructeurs chinois</h2>
  <div class="grid">{cards_cn}</div>
  <h2 class="section">🇺🇸 Constructeurs américains</h2>
  <div class="grid">{cards_us}</div>
</div>"""
    return HTMLResponse(_base("Accueil", body))


@router.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, db: AsyncSession = Depends(get_db)):
    if (r := _auth(request)):
        return r

    result = await db.execute(
        select(ScraperHealth)
        .options(selectinload(ScraperHealth.manufacturer))
        .order_by(ScraperHealth.status)
    )
    healths = result.scalars().all()

    rows = ""
    for h in healths:
        m = h.manufacturer
        status = h.status
        badge_color = STATUS_COLOR.get(status, "#555")
        badge_label = STATUS_LABEL.get(status, "—")
        last_run = h.last_run_at.strftime("%d/%m/%Y %H:%M") if h.last_run_at else "—"
        last_ok = h.last_success_at.strftime("%d/%m/%Y %H:%M") if h.last_success_at else "—"
        error = h.last_error or ""
        rows += f"""
        <tr>
          <td><a href="/{m.slug}" style="color:{m.color};font-weight:600">{FLAG.get(m.country,'')} {m.name}</a></td>
          <td><span style="background:{badge_color}20;color:{badge_color};border:1px solid {badge_color}40;
            font-size:.7rem;padding:.15rem .5rem;border-radius:20px;font-weight:600">{badge_label}</span></td>
          <td>{h.variants_found}</td>
          <td style="color:#888;font-size:.8rem">{last_run}</td>
          <td style="color:#888;font-size:.8rem">{last_ok}</td>
          <td style="color:#ef4444;font-size:.75rem;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="{error}">{error}</td>
          <td>
            <button class="run-btn" data-slug="{m.slug}" style="background:#1e2130;border:1px solid #2a2d3a;
              color:#aaa;padding:.3rem .7rem;border-radius:6px;cursor:pointer;font-size:.75rem">▶ Run</button>
          </td>
        </tr>"""

    body = f"""
<style>
header{{padding:1.25rem 1.5rem;border-bottom:1px solid #1e2130;display:flex;align-items:center;gap:1rem}}
header h1{{font-size:1rem;font-weight:600;color:#aaa;flex:1}}
.content{{max-width:1100px;margin:0 auto;padding:2rem 1.5rem}}
.run-all{{background:#4f6ef7;color:#fff;border:none;padding:.6rem 1.2rem;border-radius:8px;cursor:pointer;font-size:.85rem;font-weight:600;margin-bottom:1.5rem}}
.run-all:hover{{background:#3a57d4}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}}
th{{text-align:left;color:#555;font-size:.7rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;padding:.5rem .75rem;border-bottom:1px solid #1e2130}}
td{{padding:.6rem .75rem;border-bottom:1px solid #1a1d27}}
tr:hover td{{background:#1a1d27}}
#toast{{position:fixed;bottom:1.5rem;right:1.5rem;background:#2da862;color:#fff;padding:.75rem 1.25rem;border-radius:8px;font-size:.85rem;display:none}}
</style>
<header>
  <a href="/" style="color:#555;font-size:.85rem">← Retour</a>
  <h1>Admin — Scrapers</h1>
  <a href="https://jlmvpscode.duckdns.org" style="color:#555;font-size:.8rem">Hub</a>
</header>
<div class="content">
  <button class="run-all" id="run-all-btn">▶ Lancer tous les scrapers</button>
  <table>
    <thead><tr>
      <th>Constructeur</th><th>Statut</th><th>Variantes</th>
      <th>Dernier run</th><th>Dernier succès</th><th>Erreur</th><th></th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>
<div id="toast"></div>
<script>
async function runScraper(slug) {{
  const url = slug ? `/api/scrape/run/${{slug}}` : '/api/scrape/run';
  await fetch(url, {{method:'POST'}});
  const t = document.getElementById('toast');
  t.textContent = slug ? `✓ ${{slug}} lancé` : '✓ Tous les scrapers lancés';
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 3000);
}}
document.getElementById('run-all-btn').addEventListener('click', () => runScraper(null));
document.querySelectorAll('.run-btn').forEach(btn => {{
  btn.addEventListener('click', () => runScraper(btn.dataset.slug));
}});
</script>"""
    return HTMLResponse(_base("Admin", body))


@router.get("/{slug}", response_class=HTMLResponse)
async def manufacturer_page(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    if (r := _auth(request)):
        return r

    result = await db.execute(
        select(Manufacturer).where(Manufacturer.slug == slug)
    )
    m = result.scalar_one_or_none()
    if not m:
        return HTMLResponse("<h1>Constructeur introuvable</h1>", status_code=404)

    result = await db.execute(
        select(VehicleModel)
        .where(VehicleModel.manufacturer_id == m.id)
        .options(selectinload(VehicleModel.variants).selectinload(Variant.snapshots))
        .order_by(VehicleModel.name)
    )
    models = result.scalars().all()

    flag = FLAG.get(m.country, "")

    body = f"""
<style>
header{{padding:1.25rem 1.5rem;border-bottom:1px solid #1e2130;display:flex;align-items:center;gap:1rem}}
header h1{{font-size:1rem;font-weight:600;color:#e8e8ea;flex:1}}
.content{{max-width:1100px;margin:0 auto;padding:2rem 1.5rem}}
.chart-wrap{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:14px;padding:1.5rem;margin-bottom:1.5rem}}
.filters{{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1.25rem}}
.filter-group{{background:#0f1117;border:1px solid #2a2d3a;border-radius:10px;padding:.75rem 1rem;min-width:160px}}
.filter-group h3{{font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#555;margin-bottom:.5rem}}
.filter-group label{{display:flex;align-items:center;gap:.4rem;font-size:.8rem;color:#aaa;cursor:pointer;margin-bottom:.3rem;
  border-left:3px solid transparent;padding-left:.35rem}}
.filter-group label:hover{{color:#e8e8ea}}
canvas{{max-height:440px}}
.no-data{{text-align:center;color:#555;padding:3rem;font-size:.9rem}}
.toggle-all{{font-size:.7rem;color:#555;cursor:pointer;margin-bottom:.4rem;display:block}}
.toggle-all:hover{{color:#aaa}}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<header>
  <a href="/" style="color:#555;font-size:.85rem">← Retour</a>
  <h1>{flag} {m.name}</h1>
  <a href="https://jlmvpscode.duckdns.org" style="color:#555;font-size:.8rem">Hub</a>
</header>
<div class="content">
  <div class="chart-wrap">
    <div class="filters" id="filters"></div>
    <div id="no-data" class="no-data" style="display:none">
      Aucune donnée — lancez un scraping depuis <a href="/admin" style="color:#f59e0b">l'admin</a>.
    </div>
    <canvas id="chart"></canvas>
  </div>
</div>
<script>
const BASE_COLOR = "{m.color}";

function hslFromIndex(index, total) {{
  const base = parseInt(BASE_COLOR.replace('#',''), 16);
  const r = (base >> 16) & 0xff, g = (base >> 8) & 0xff, b = base & 0xff;
  const h0 = (Math.atan2(Math.sqrt(3)*(g-b), 2*r-g-b) * 180/Math.PI + 360) % 360;
  const hue = (h0 + index * (360 / Math.max(total, 1))) % 360;
  const lum = 45 + (index % 4) * 8;
  return `hsl(${{hue.toFixed(0)}}, 65%, ${{lum}}%)`;
}}

async function loadData() {{
  const resp = await fetch('/api/data/{slug}');
  if (!resp.ok) return;
  const json = await resp.json();
  const models = json.models;

  const filterEl = document.getElementById('filters');
  filterEl.innerHTML = '';

  const allDatasets = [];
  const allDates = new Set();
  let dsIndex = 0;
  const totalVariants = Object.values(models).reduce((a, m) => a + Object.keys(m).length, 0);

  for (const [modelName, variants] of Object.entries(models)) {{
    const group = document.createElement('div');
    group.className = 'filter-group';

    const toggleAll = document.createElement('span');
    toggleAll.className = 'toggle-all';
    toggleAll.textContent = modelName;
    let allVisible = true;
    toggleAll.addEventListener('click', () => {{
      allVisible = !allVisible;
      group.querySelectorAll('input[type=checkbox]').forEach(cb => {{
        cb.checked = allVisible;
        toggleDataset(Number(cb.dataset.i), allVisible);
      }});
    }});
    group.appendChild(toggleAll);

    for (const [variantName, snapshots] of Object.entries(variants)) {{
      snapshots.forEach(s => allDates.add(s.date));
      const color = hslFromIndex(dsIndex, totalVariants);
      allDatasets.push({{
        label: variantName,
        _dates: Object.fromEntries(snapshots.map(s => [s.date, s.price])),
        borderColor: color,
        backgroundColor: color.replace(')', ', 0.12)').replace('hsl(', 'hsla('),
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.3,
        fill: false,
        spanGaps: false,
      }});

      const lbl = document.createElement('label');
      lbl.style.borderLeftColor = color;
      const cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = true;
      cb.dataset.i = dsIndex;
      cb.style.accentColor = color;
      cb.addEventListener('change', () => toggleDataset(dsIndex, cb.checked));
      lbl.append(cb, ' ' + variantName);
      group.appendChild(lbl);
      dsIndex++;
    }}
    filterEl.appendChild(group);
  }}

  const sortedDates = [...allDates].sort();
  if (!sortedDates.length) {{
    document.getElementById('no-data').style.display = 'block';
    document.getElementById('chart').style.display = 'none';
    return;
  }}

  const datasets = allDatasets.map(ds => ({{
    ...ds,
    data: sortedDates.map(d => ds._dates[d] ?? null),
  }}));

  const ctx = document.getElementById('chart').getContext('2d');
  window._chart = new Chart(ctx, {{
    type: 'line',
    data: {{ labels: sortedDates, datasets }},
    options: {{
      responsive: true,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          backgroundColor: '#1a1d27',
          borderColor: '#2a2d3a',
          borderWidth: 1,
          titleColor: '#e8e8ea',
          bodyColor: '#aaa',
          padding: 10,
          callbacks: {{
            label: ctx => ctx.parsed.y == null ? null
              : ` ${{ctx.dataset.label}}: ${{ctx.parsed.y.toLocaleString('fr-FR')}} €`,
          }},
        }},
      }},
      scales: {{
        x: {{ grid: {{ color: '#1e2130' }}, ticks: {{ color: '#555', maxTicksLimit: 12 }} }},
        y: {{
          grid: {{ color: '#1e2130' }},
          ticks: {{ color: '#555', callback: v => v.toLocaleString('fr-FR') + ' €' }},
        }},
      }},
    }},
  }});
}}

function toggleDataset(i, visible) {{
  if (!window._chart) return;
  window._chart.data.datasets[i].hidden = !visible;
  window._chart.update('none');
}}

loadData();
</script>"""
    return HTMLResponse(_base(m.name, body))
