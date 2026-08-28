import os
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

PROJECTS_BASE = Path(os.environ.get("PROJECTS_DIR", "/projects"))

STATUS_LABEL = {"draft": "Brouillon", "spec-ready": "Spec prête", "tickets-created": "Tickets créés", "en-cours": "En cours", "done": "Terminé"}
STATUS_COLOR = {"draft": "#6b7280", "spec-ready": "#ca8a04", "tickets-created": "#4f6ef7", "en-cours": "#0ea5e9", "done": "#2da862"}

router = APIRouter(prefix="/roadmap")


# ── Filesystem helpers ─────────────────────────────────────────────────────────

def _roadmap_dir(project: str) -> Path:
    base = project.split("~")[0]
    d = PROJECTS_BASE / base / "roadmap"
    d.mkdir(exist_ok=True)
    return d


def _item_path(project: str, item_id: str) -> Optional[Path]:
    rd = _roadmap_dir(project)
    # Doc libre référencé par son nom de fichier (stem)
    direct = rd / f"{item_id}.md"
    if direct.exists():
        return direct
    # Legacy : roadmap-{id}-{slug}.md, référencé par l'{id} numérique
    for f in rd.glob(f"roadmap-{item_id}-*.md"):
        return f
    # Filet : n'importe quel .md dont le stem correspond
    for f in rd.glob("*.md"):
        if f.stem == item_id:
            return f
    return None


def _parse_item(filepath: Path) -> dict:
    raw = filepath.read_text()
    fm: dict = {}
    m = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    body = raw
    if m:
        for line in m.group(1).split("\n"):
            if ": " in line:
                k, _, v = line.partition(": ")
                fm[k.strip()] = v.strip()
        body = raw[m.end():].strip()
    fm["body"] = body
    fm["file"] = filepath.name
    # L'id de routage = TOUJOURS le nom de fichier (stem). Il résout de façon fiable via
    # _item_path, qu'il y ait ou non un `id:` dans le front-matter (docs libres compris).
    fm["id"] = filepath.stem
    # Date de secours pour les docs libres sans front-matter : mtime du fichier.
    fm.setdefault("created", datetime.fromtimestamp(filepath.stat().st_mtime).isoformat())

    # Aperçu : section « Direction (utilisateur) » si présente (## ou ###), sinon 1re ligne utile.
    user_m = re.search(r"##+ Direction ?(?:/ Feature )?\(utilisateur\)\n([\s\S]*?)(?:\n##|\Z)", body)
    if user_m:
        fm["preview"] = user_m.group(1).strip()[:120]
    else:
        preview = ""
        for ln in body.split("\n"):
            s = ln.strip()
            if not s or s.startswith(("#", ">", "---", "```", "|")):
                continue
            preview = s
            break
        fm["preview"] = (preview or body.strip())[:120]

    # Tickets liés : compter les références #id où qu'elles soient (sprints inclus), format-agnostique.
    fm["tickets_count"] = len(set(re.findall(r"#(\d{6,})", body)))

    # Deux niveaux de document cohabitent dans roadmap/ : la ROADMAP (direction macro,
    # une par axe de développement, plusieurs par projet au fil de l'usage) et le
    # CHANTIER (décisions + sprints, la maille de pilotage quotidien).
    # Les fichiers antérieurs à cette distinction sont tous des chantiers : c'est le
    # défaut, pour qu'aucun document existant ne change de nature en silence.
    fm.setdefault("type", "chantier")
    # `roadmap:` porte la filiation chantier → roadmap. Absent = chantier orphelin,
    # affiché à part plutôt que masqué.
    fm.setdefault("roadmap", "")

    return fm


def _parse_sprints(body: str) -> list[dict]:
    """Extrait les sprints d'un chantier : les `### …` sous la section `## Sprints`, avec leurs
    items de checklist. C'est la base de l'ordre de sprint généré pour Claude Code."""
    m = re.search(r"\n##\s+Sprints\s*\n(.*?)(?:\n##\s|\Z)", "\n" + body, re.S)
    if not m:
        return []
    section = m.group(1)
    sprints = []
    for part in re.split(r"\n###\s+", "\n" + section)[1:]:
        head, _, rest = part.partition("\n")
        items = [ln.rstrip() for ln in rest.split("\n") if re.match(r"\s*-\s*\[[ xX]\]", ln)]
        sprints.append({"name": head.strip(), "items": items})
    return sprints


def _generate_sprint_order(project: str, chantier_file: str, sprint: dict) -> str:
    """Ordre de sprint = document de passage Hub → Claude Code. Mince, jetable, écrasé à chaque
    génération. Le statut ne vit jamais ici : la source de vérité est le chantier."""
    proj = project.split("~")[0]
    lines = [
        f"# Ordre de sprint — {proj}",
        f"Chantier : roadmap/{chantier_file}",
        f"Sprint   : {sprint['name']}",
        "",
        "## Items",
        *(sprint["items"] or ["- [ ] (aucun item listé — voir le chantier)"]),
        "",
        f"> Déclencheur Claude Code : « exécute le sprint en cours pour {proj} »",
        "> Source de vérité = le chantier ci-dessus. Ce fichier est jetable (écrasé au prochain ordre).",
        "",
        "## Fin de sprint (Claude Code)",
        "Une fois les items cochés dans le chantier, **réécris ce fichier** sur le prochain sprint",
        "non terminé du chantier (même gabarit, **cette section comprise** : c'est elle qui fait",
        "durer l'enchaînement) — l'utilisateur ne repasse pas par le Hub. S'il reste",
        "des items sur CE sprint, garde-le en pointant les seuls items restants ; s'il n'y a plus de",
        "sprint, écris `Sprint : — (chantier terminé)` sans item. Puis conclus par :",
        "",
        "> Sprint {N} — {nom} : terminé. SESSION.md est actualisé pour lancer le Sprint {N+1} — {nom}.",
        "> Recommandation : {nouvelle conversation | poursuivre ici} — {justification en une ligne}.",
        "",
        "Détail du protocole : `CONTROL_SYSTEM.md` § Ré-armement automatique.",
        "",
    ]
    return "\n".join(lines)


def _list_items(project: str) -> list[dict]:
    rd = _roadmap_dir(project)
    items = []
    # Tout fichier .md du dossier roadmap est un item (docs libres compris), plus récent en tête.
    for f in sorted(rd.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            items.append(_parse_item(f))
        except Exception:
            pass
    return items


def _create_roadmap(project: str, title: str, direction: str) -> str:
    """Crée une ROADMAP : un axe de développement, en amont des chantiers.

    Une roadmap n'a pas de sprints et ne s'exécute pas. Elle porte une direction et,
    une fois cadrée, la carte des chantiers qui en découlent. On en ouvre une
    nouvelle quand un axe apparaît à l'usage du produit — elles coexistent, c'est
    l'utilisateur qui choisit celle sur laquelle il avance.
    """
    rd = _roadmap_dir(project)
    item_id = int(time.time() * 1000)
    slug = re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", title[:40].lower()))
    filename = f"roadmap-{item_id}-{slug}.md"

    lines = [
        "---",
        f"id: roadmap-{item_id}",
        "type: roadmap",
        "status: draft",
        f"created: {datetime.now().isoformat()}",
        f"project: {project.split('~')[0]}",
        "---",
        "",
        f"# Roadmap — {title}",
        "",
        "## Direction (utilisateur)",
        direction.strip() or "_Aucune description_",
        "",
        "## Carte des chantiers",
        "*(Généré au cadrage : les chantiers qui découlent de cette direction, leur ordre",
        "et leurs dépendances. Un chantier par contexte technique cohérent — pas par",
        "fonctionnalité, sinon ils se chevauchent tous.)*",
        "",
        "## Décisions de cadrage",
        "*(Ce qui a été tranché au niveau de l'axe, et ce qui reste ouvert.)*",
        "",
    ]
    (rd / filename).write_text("\n".join(lines))
    return str(item_id)


def _create_item(project: str, title: str, description: str, constraints: str,
                 roadmap_id: str = "") -> str:
    rd = _roadmap_dir(project)
    item_id = int(time.time() * 1000)
    slug = re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", title[:40].lower()))
    filename = f"roadmap-{item_id}-{slug}.md"

    lines = [
        "---",
        f"id: roadmap-{item_id}",
        "type: chantier",
        "status: draft",
        f"created: {datetime.now().isoformat()}",
        f"project: {project.split('~')[0]}",
        f"roadmap: {roadmap_id}",
        "---",
        "",
        f"# Chantier — {title}",
        "",
        "## Direction (utilisateur)",
        description.strip() or "_Aucune description_",
        "",
    ]
    if constraints.strip():
        lines += ["## Contraintes connues", constraints.strip(), ""]
    lines += [
        "## Décisions",
        "*(Claude Code : ce qui est tranché ET ce qui reste à trancher — surface de validation, courte)*",
        "",
        "## Sprints",
        "*(Claude Code : sprints segmentés par contexte partagé ; la checklist EST le statut)*",
        "",
        "### Sprint 1 — {nom} · contexte partagé : {quoi}",
        "- [ ] {item} → #{ticket_id si délégué}",
        "",
        "## Annexe — contrats / specs détaillés",
        "*(le contrat exhaustif vit ici, pas dans la surface de validation)*",
        "",
    ]
    (rd / filename).write_text("\n".join(lines))
    return str(item_id)


# ── HTML helpers ───────────────────────────────────────────────────────────────

def _e(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def _base_road(title: str, body: str, project: str, breadcrumbs: str = "") -> str:
    display = project.replace("~", " / ")
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — Roadmap</title>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:system-ui,-apple-system,sans-serif;background:#0f1117;color:#e8e8ea;min-height:100vh;font-size:14px}}
  a{{color:inherit;text-decoration:none}}
  header{{padding:1rem 1.5rem;border-bottom:1px solid #1e2130;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}}
  .logo{{color:#888;font-size:.9rem}}
  .logo a:hover{{color:#e8e8ea}}
  .sep{{color:#444}}
  .breadcrumb{{color:#888;font-size:.9rem}}
  .container{{max-width:860px;margin:0 auto;padding:2rem 1.5rem}}
  .btn{{display:inline-flex;align-items:center;gap:.4rem;padding:.5rem 1rem;border-radius:8px;
        border:none;cursor:pointer;font-size:.85rem;font-weight:500;transition:opacity .15s;white-space:nowrap}}
  .btn:hover{{opacity:.85}}
  .btn-primary{{background:#4f6ef7;color:#fff}}
  .btn-secondary{{background:#1e2130;color:#e8e8ea;border:1px solid #2a2d3a}}
  .btn-danger{{background:#dc2626;color:#fff}}
  .btn-sm{{padding:.3rem .65rem;font-size:.78rem}}
  .tag{{display:inline-block;padding:.2rem .55rem;border-radius:20px;font-size:.75rem;font-weight:600}}
  .page-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.5rem;flex-wrap:wrap;gap:.75rem}}
  .page-title{{font-size:1.2rem;font-weight:700}}
  .item-card{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:1rem 1.25rem;
              margin-bottom:.75rem;transition:border-color .15s}}
  .item-card:hover{{border-color:#4f6ef7}}
  .item-title{{font-size:.95rem;font-weight:600;margin-bottom:.35rem}}
  .item-preview{{font-size:.82rem;color:#888;margin-bottom:.5rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
  .item-meta{{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap}}
  .item-date{{font-size:.72rem;color:#555}}
  label{{display:block;font-size:.75rem;color:#888;margin-bottom:.35rem;text-transform:uppercase;letter-spacing:.04em}}
  input[type=text],select,textarea{{width:100%;background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;
    padding:.65rem .9rem;color:#e8e8ea;font-size:.9rem;outline:none;font-family:inherit}}
  input:focus,select:focus,textarea:focus{{border-color:#4f6ef7}}
  select option{{background:#1a1d27}}
  textarea{{resize:vertical;font-family:ui-monospace,monospace;font-size:.82rem;line-height:1.6}}
  .form-group{{margin-bottom:1.1rem}}
  .section{{background:#1a1d27;border:1px solid #2a2d3a;border-radius:12px;padding:1.2rem;margin-bottom:1.1rem}}
  .section-title{{font-size:.78rem;font-weight:600;color:#888;margin-bottom:.9rem;text-transform:uppercase;letter-spacing:.06em}}
  .empty{{color:#555;font-size:.82rem;font-style:italic}}
  .alert{{padding:.7rem 1rem;border-radius:8px;margin-bottom:1rem;font-size:.85rem}}
  .alert-success{{background:rgba(45,168,98,.12);border:1px solid rgba(45,168,98,.3);color:#2da862}}
  .divider{{border:none;border-top:1px solid #1e2130;margin:1.25rem 0}}
  pre{{background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;padding:1rem;
       font-size:.78rem;line-height:1.6;overflow-x:auto;white-space:pre-wrap;color:#bbb}}
  .hint{{font-size:.78rem;color:#555;margin-top:.4rem}}
</style>
</head>
<body>
<header>
  <div class="logo">
    <a href="/">JLM VPS</a> <span class="sep">/</span>
    <a href="/tickets">Tickets</a> <span class="sep">/</span>
    <a href="/tickets/{_e(project)}">{_e(display)}</a> <span class="sep">/</span>
    <span class="breadcrumb">Roadmap</span>
  </div>
  {breadcrumbs}
</header>
<div class="container">{body}</div>
</body>
</html>"""


def _status_badge(status: str) -> str:
    color = STATUS_COLOR.get(status, "#6b7280")
    label = STATUS_LABEL.get(status, status)
    return f'<span class="tag" style="background:{color}22;color:{color}">{_e(label)}</span>'


def _fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except Exception:
        return iso


# ── Pages ──────────────────────────────────────────────────────────────────────

def _card(project: str, item: dict, indent: bool = False) -> str:
    iid = item.get("id", "")
    preview = _e(item.get("preview", "")[:100])
    date = _fmt_date(item.get("created", ""))
    tc = item.get("tickets_count", 0)
    tc_html = (f'<span class="tag" style="background:rgba(79,110,247,.12);color:#818cf8">'
               f'{tc} ticket{"s" if tc != 1 else ""}</span>') if tc else ""
    title = _e(item.get("body", "").split(chr(10))[0].lstrip("# ") or iid)
    pad = 'margin-left:1.5rem;border-left:2px solid rgba(129,140,248,.25);padding-left:.75rem' if indent else ""
    return f"""
<a href="/roadmap/{_e(project)}/{_e(iid)}/edit" style="display:block;{pad}">
  <div class="item-card">
    <div class="item-title">{title}</div>
    <div class="item-preview">{preview}</div>
    <div class="item-meta">
      {_status_badge(item.get("status", "draft"))}
      {tc_html}
      <span class="item-date">{date}</span>
    </div>
  </div>
</a>"""


def _page_list(project: str, items: list) -> str:
    """Affiche la hiérarchie roadmap → chantiers, et non un tas plat trié par statut.

    Le tri par statut répondait à « qu'est-ce qui est en cours ? » ; la question de
    pilotage est « sur quel axe suis-je, et quels chantiers en découlent ? ».
    """
    display = project.replace("~", " / ")

    roadmaps = [i for i in items if i.get("type") == "roadmap"]
    chantiers = [i for i in items if i.get("type") != "roadmap"]

    # La filiation `roadmap:` d'un chantier porte le STEM du fichier roadmap, pas
    # l'`id:` du front-matter : _parse_item force `fm["id"] = filepath.stem`, et
    # c'est ce stem qui sert aussi de clé de routage dans _item_path. Utiliser
    # l'autre donnerait des liens morts.
    # Les chantiers antérieurs à la distinction n'ont pas de filiation : ils sont
    # affichés à part, jamais masqués — un document qui disparaît de la vue est un
    # document perdu.
    known = {r.get("id", "") for r in roadmaps}
    by_roadmap: dict = {}
    orphans = []
    for c in chantiers:
        key = c.get("roadmap", "")
        if key in known:
            by_roadmap.setdefault(key, []).append(c)
        else:
            orphans.append(c)

    sections = ""
    for r in sorted(roadmaps, key=lambda x: x.get("created", ""), reverse=True):
        kids = by_roadmap.get(r.get("id", ""), [])
        n = len(kids)
        sections += (
            f'<h3 style="font-size:.85rem;color:#818cf8;margin:1.5rem 0 .6rem;'
            f'text-transform:uppercase;letter-spacing:.05em">🗺 Axe · '
            f'{n} chantier{"s" if n != 1 else ""}</h3>'
        )
        sections += _card(project, r)
        sections += "".join(_card(project, c, indent=True) for c in
                            sorted(kids, key=lambda x: x.get("created", "")))
        if not kids:
            sections += ('<p style="margin-left:1.5rem;color:#666;font-size:.8rem;'
                         'padding:.5rem 0">Aucun chantier — la roadmap n\'est pas encore cadrée.</p>')

    if orphans:
        sections += ('<h3 style="font-size:.85rem;color:#888;margin:1.5rem 0 .6rem;'
                     'text-transform:uppercase;letter-spacing:.05em">Chantiers hors roadmap</h3>')
        sections += "".join(_card(project, c) for c in
                            sorted(orphans, key=lambda x: x.get("created", ""), reverse=True))

    if not items:
        sections = '<p class="empty">Aucune roadmap ni chantier pour ce projet.</p>'

    body = f"""
<div class="page-header">
  <div class="page-title">🗺 Roadmap — {_e(display)}</div>
  <div style="display:flex;gap:.5rem">
    <a href="/tickets/{_e(project)}" class="btn btn-secondary">← Tickets</a>
    <a href="/roadmap/{_e(project)}/new-roadmap" class="btn btn-secondary">+ Axe</a>
    <a href="/roadmap/{_e(project)}/new" class="btn btn-primary">+ Chantier</a>
  </div>
</div>
<div class="alert" style="background:rgba(79,110,247,.08);border:1px solid rgba(79,110,247,.2);color:#818cf8;font-size:.82rem;margin-bottom:1.25rem">
  💡 Un <strong>axe</strong> (roadmap) porte une direction ; il se cadre en
  <strong>chantiers</strong>, qui se découpent en <strong>sprints</strong>. Tu interviens sur
  l'axe et le chantier ; les sprints et les tickets sont de la mécanique.
  Ouvre un chantier pour générer l'ordre du sprint à exécuter.
</div>
{sections}"""
    return _base_road(f"Roadmap — {display}", body, project)


def _page_new_roadmap(project: str, error: str = "") -> str:
    err_html = (f'<div class="alert" style="background:rgba(220,38,38,.12);'
                f'border:1px solid rgba(220,38,38,.3);color:#f87171">{_e(error)}</div>') if error else ""
    body = f"""
<div class="page-header">
  <div class="page-title">Nouvel axe de développement</div>
  <a href="/roadmap/{_e(project)}" class="btn btn-secondary">← Retour</a>
</div>
{err_html}
<div class="alert" style="background:rgba(202,138,4,.08);border:1px solid rgba(202,138,4,.25);color:#ca8a04;font-size:.82rem;margin-bottom:1.25rem">
  Un axe est plus large qu'un chantier : c'est une direction dont découleront
  <em>plusieurs</em> chantiers. Ouvre-en un nouveau quand l'usage du produit fait
  apparaître un front de travail qui n'entre dans aucun axe existant. Les axes
  coexistent — c'est toi qui choisis celui sur lequel tu avances.
</div>
<form method="POST" action="/roadmap/{_e(project)}/new-roadmap">
  <div class="section">
    <div class="form-group">
      <label>Titre de l'axe</label>
      <input type="text" name="title" placeholder="ex: Collecte et synthèse de veille" required>
    </div>
    <div class="form-group">
      <label>Direction</label>
      <textarea name="direction" rows="8"
        placeholder="Ce que tu veux obtenir, et pourquoi. Pas comment."></textarea>
      <div class="hint">Le cadrage (carte des chantiers) est produit ensuite — tu le relis et l'amendes.</div>
    </div>
    <button type="submit" class="btn btn-primary">Créer l'axe</button>
  </div>
</form>"""
    return _base_road("Nouvel axe", body, project)


def _page_new(project: str, error: str = "", roadmaps: list | None = None) -> str:
    err_html = f'<div class="alert" style="background:rgba(220,38,38,.12);border:1px solid rgba(220,38,38,.3);color:#f87171">{_e(error)}</div>' if error else ""
    opts = "".join(
        f'<option value="{_e(r.get("id",""))}">'
        f'{_e(r.get("body","").split(chr(10))[0].lstrip("# ") or r.get("id",""))}</option>'
        for r in (roadmaps or [])
    )
    roadmap_field = f"""
    <div class="form-group">
      <label>Rattacher à un axe</label>
      <select name="roadmap_id">
        <option value="">— aucun (chantier isolé) —</option>
        {opts}
      </select>
      <div class="hint">Un chantier sans axe reste visible, dans « Chantiers hors roadmap ».</div>
    </div>""" if opts else ""
    body = f"""
<div class="page-header">
  <div class="page-title">Nouveau chantier</div>
  <a href="/roadmap/{_e(project)}" class="btn btn-secondary">← Retour</a>
</div>
{err_html}
<form method="POST" action="/roadmap/{_e(project)}/new">
  <div class="section">
    <div class="form-group">
      <label>Titre</label>
      <input type="text" name="title" placeholder="ex: Refonte UX page budget — mobile + graphiques" required>
    </div>
    <div class="form-group">
      <label>Direction / Description</label>
      <textarea name="description" rows="6"
        placeholder="Décris ce que tu veux obtenir. Claude se chargera de définir comment.&#10;&#10;ex: Je veux que la page budget soit utilisable sur mobile avec des graphiques d'évolution mensuelle et une comparaison N/N-1."></textarea>
      <div class="hint">Pas besoin d'être précis — Claude analysera le code existant et proposera une spec détaillée.</div>
    </div>
    <div class="form-group">
      <label>Contraintes connues (optionnel)</label>
      <textarea name="constraints" rows="3"
        placeholder="ex: Pas de migration DB. Garder la compatibilité avec l'export Excel."></textarea>
    </div>{roadmap_field}
    <button type="submit" class="btn btn-primary">Créer</button>
  </div>
</form>"""
    return _base_road("Nouvelle direction", body, project)


def _page_edit(project: str, item: dict, flash: str = "") -> str:
    iid    = item.get("id", "")
    status = item.get("status", "draft")
    body_md = item.get("body", "")
    proj = project.split("~")[0]

    if flash == "saved":
        flash_html = '<div class="alert alert-success">✓ Sauvegardé.</div>'
    elif flash == "order":
        flash_html = (f'<div class="alert alert-success">✓ <code>SESSION.md</code> généré. '
                      f'Dans Claude Code : <strong>« exécute le sprint en cours pour {_e(proj)} »</strong>'
                      f'<br><span style="opacity:.8">À la fin du sprint, Claude ré-arme lui-même '
                      f'l\'ordre sur le sprint suivant : inutile de revenir ici, sauf pour repartir '
                      f'sur un autre sprint.</span></div>')
    else:
        flash_html = ""

    sprints = _parse_sprints(body_md)
    if sprints:
        rows = ""
        for s in sprints:
            n = len(s["items"])
            rows += f"""
<div style="display:flex;align-items:center;gap:.75rem;padding:.6rem .75rem;background:#0f1117;
     border:1px solid #2a2d3a;border-radius:8px;margin-bottom:.4rem">
  <div style="flex:1;min-width:0">
    <div style="font-size:.88rem;font-weight:600">{_e(s['name'])}</div>
    <div style="font-size:.75rem;color:#666">{n} item{'s' if n!=1 else ''}</div>
  </div>
  <form method="POST" action="/roadmap/{_e(project)}/{_e(iid)}/sprint-order" style="margin:0">
    <input type="hidden" name="sprint" value="{_e(s['name'])}">
    <button type="submit" class="btn btn-primary btn-sm">⚡ Générer l'ordre</button>
  </form>
</div>"""
        sprints_html = (f'<div class="section"><div class="section-title">'
                        f"Sprints — générer l'ordre (SESSION.md)</div>{rows}"
                        f'<div class="hint">Un seul clic suffit pour lancer le chantier : à la fin '
                        f"de chaque sprint, Claude Code réécrit <code>SESSION.md</code> sur le sprint "
                        f"suivant. Revenir ici sert à <strong>sortir de la séquence</strong> "
                        f"(reprendre un sprint antérieur, en sauter un).</div></div>")
    else:
        sprints_html = ('<div class="section"><div class="section-title">Sprints</div>'
                        '<p class="empty">Pas encore de sprints. Claude les ajoute dans la section '
                        '<code>## Sprints</code> du chantier.</p></div>')

    status_opts = "".join(
        f'<option value="{s}" {"selected" if s==status else ""}>{STATUS_LABEL[s]}</option>'
        for s in STATUS_LABEL
    )
    title_line = body_md.split("\n")[0].lstrip("# ").strip() if body_md else iid

    body = f"""
{flash_html}
<div class="page-header">
  <div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">
    <div class="page-title">{_e(title_line)}</div>
    {_status_badge(status)}
  </div>
  <a href="/roadmap/{_e(project)}" class="btn btn-secondary">← Roadmap</a>
</div>

{sprints_html}

<form method="POST" action="/roadmap/{_e(project)}/{_e(iid)}/edit">
  <div class="section">
    <div class="section-title">Statut</div>
    <div class="form-group" style="max-width:220px">
      <select name="status">{status_opts}</select>
    </div>
  </div>
  <div class="section">
    <div class="section-title">Contenu (Markdown)</div>
    <div class="hint" style="margin-bottom:.75rem">
      La section <code>### Spec générée</code> est remplie par Claude Code.
      La section <code>### Tickets créés</code> liste les tickets générés.
    </div>
    <div class="form-group">
      <textarea name="body" rows="28">{_e(body_md)}</textarea>
    </div>
  </div>
  <div style="display:flex;gap:.75rem;flex-wrap:wrap">
    <button type="submit" class="btn btn-primary">💾 Sauvegarder</button>
  </div>
</form>

<hr class="divider">
<form method="POST" action="/roadmap/{_e(project)}/{_e(iid)}/delete"
      onsubmit="return confirm('Supprimer cet item de roadmap ?')">
  <button type="submit" class="btn btn-danger btn-sm">Supprimer cet item</button>
</form>"""
    return _base_road(title_line, body, project)


# ── Auth helper ────────────────────────────────────────────────────────────────

def _require_auth(request: Request, settings):
    from app.auth import get_session, redirect_to_login
    if not get_session(request, settings.SESSION_SECRET):
        return redirect_to_login(str(request.url.path))
    return None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/{project}", response_class=HTMLResponse)
async def roadmap_list(request: Request, project: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    return HTMLResponse(_page_list(project, _list_items(project)))


def _roadmaps_of(project: str) -> list[dict]:
    return [i for i in _list_items(project) if i.get("type") == "roadmap"]


# Les routes littérales (`/new`, `/new-roadmap`) doivent précéder `/{item_id}/…`,
# sinon FastAPI les capture comme un item_id et la page de création devient un 404.
@router.get("/{project}/new", response_class=HTMLResponse)
async def roadmap_new_get(request: Request, project: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    return HTMLResponse(_page_new(project, roadmaps=_roadmaps_of(project)))


@router.post("/{project}/new")
async def roadmap_new_post(
    request: Request, project: str,
    title: str = Form(...),
    description: str = Form(default=""),
    constraints: str = Form(default=""),
    roadmap_id: str = Form(default=""),
):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    if not title.strip():
        return HTMLResponse(_page_new(project, "Le titre est obligatoire.",
                                      roadmaps=_roadmaps_of(project)), status_code=400)
    iid = _create_item(project, title.strip(), description.strip(), constraints.strip(),
                       roadmap_id.strip())
    return RedirectResponse(f"/roadmap/{project}/{iid}/edit?flash=saved", status_code=303)


@router.get("/{project}/new-roadmap", response_class=HTMLResponse)
async def roadmap_new_axis_get(request: Request, project: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    return HTMLResponse(_page_new_roadmap(project))


@router.post("/{project}/new-roadmap")
async def roadmap_new_axis_post(
    request: Request, project: str,
    title: str = Form(...),
    direction: str = Form(default=""),
):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    if not title.strip():
        return HTMLResponse(_page_new_roadmap(project, "Le titre est obligatoire."), status_code=400)
    iid = _create_roadmap(project, title.strip(), direction.strip())
    return RedirectResponse(f"/roadmap/{project}/{iid}/edit?flash=saved", status_code=303)


@router.get("/{project}/{item_id}/edit", response_class=HTMLResponse)
async def roadmap_edit_get(request: Request, project: str, item_id: str, flash: str = ""):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if not path:
        return HTMLResponse(f"Item introuvable : {_e(item_id)}", status_code=404)
    return HTMLResponse(_page_edit(project, _parse_item(path), flash))


@router.post("/{project}/{item_id}/edit")
async def roadmap_edit_post(
    request: Request, project: str, item_id: str,
    status: str = Form(...), body: str = Form(default=""),
):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if not path:
        return HTMLResponse(f"Item introuvable : {_e(item_id)}", status_code=404)

    raw = path.read_text()
    fm: dict = {}
    m = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    if m:
        for line in m.group(1).split("\n"):
            if ": " in line:
                k, _, v = line.partition(": ")
                fm[k.strip()] = v.strip()

    fm["status"] = status if status in STATUS_LABEL else fm.get("status", "draft")

    # Les textarea HTML renvoient des fins de ligne CRLF (spec HTML). Sans cette
    # normalisation, la moindre sauvegarde réécrit TOUT le fichier en CRLF et
    # `git diff` affiche le document entier comme modifié : le vrai changement est
    # noyé, et le lecteur de diff de la boucle nocturne s'ancre sur du bruit.
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    # Le "" final garantit la newline de fin de fichier, sinon chaque sauvegarde
    # produit un « \ No newline at end of file » dans le diff.
    fm_lines = ["---"] + [f"{k}: {v}" for k, v in fm.items()] + ["---", "", body.strip(), ""]
    path.write_text("\n".join(fm_lines))
    return RedirectResponse(f"/roadmap/{project}/{item_id}/edit?flash=saved", status_code=303)


@router.post("/{project}/{item_id}/sprint-order")
async def roadmap_sprint_order(request: Request, project: str, item_id: str, sprint: str = Form(...)):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if not path:
        return HTMLResponse(f"Item introuvable : {_e(item_id)}", status_code=404)
    item = _parse_item(path)
    match = next((s for s in _parse_sprints(item.get("body", "")) if s["name"] == sprint), None)
    if not match:
        return HTMLResponse(f"Sprint introuvable : {_e(sprint)}", status_code=404)
    content = _generate_sprint_order(project, path.name, match)
    (PROJECTS_BASE / project.split("~")[0] / "SESSION.md").write_text(content)
    return RedirectResponse(f"/roadmap/{project}/{item_id}/edit?flash=order", status_code=303)


@router.post("/{project}/{item_id}/delete")
async def roadmap_delete(request: Request, project: str, item_id: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if path and path.exists():
        path.unlink()
    return RedirectResponse(f"/roadmap/{project}", status_code=303)
