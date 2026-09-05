import os
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

PROJECTS_BASE = Path(os.environ.get("PROJECTS_DIR", "/projects"))

# Deux états, pas plus (`CONTROL_SYSTEM.md` §1) : une roadmap naît en `brouillon` et ne devient
# `figée` — donc inscriptible — qu'après la conversation de raffinement au terminal.
STATUS_LABEL = {"brouillon": "Brouillon", "figée": "Figée"}
STATUS_COLOR = {"brouillon": "#ca8a04", "figée": "#2da862"}
FROZEN = "figée"

# ⚠️ `roadmap/` est un fourre-tout hétérogène : 13 vocabulaires de statut distincts y cohabitent
# (`carte-de-provenance`, `spec-ready`, `derivation`, `cadre-fondateur`…). Le sélecteur du Hub ne
# doit donc JAMAIS imposer sa liste : tout statut inconnu est présenté « inchangé » et n'est pas
# réécrit (`_render_saved_document` ne substitue que les valeurs de STATUS_LABEL). Sans ça, ouvrir
# puis sauvegarder un document de portfolio-tracker le repassait silencieusement en `draft`.
#
# ⚠️ Sentinel NON VIDE, et ce n'est pas cosmétique : FastAPI traite une valeur de `Form` vide
# comme un champ *absent* et renvoie 422. Avec `value=""`, choisir « inchangé » puis Sauvegarder
# perdait la sauvegarde entière (mesuré : 422 contre 303 sur la même requête).
KEEP_STATUS = "__inchange__"

REPRISE_NAME = "00-REPRISE.md"
# Le pointeur « roadmap active » du fichier de reprise — seul endroit où vit l'information
# (`CONTROL_SYSTEM.md` §2). Ancré sur `>` : les mentions en prose du même mot n'y répondent pas.
POINTER_RE = re.compile(r"^>\s*\*\*Roadmap active\s*:")

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


# ── Fichier de reprise ─────────────────────────────────────────────────────────

def _reprise_path(project: str) -> Optional[Path]:
    """Résolution imposée par `CONTROL_SYSTEM.md` §2 : racine du projet d'abord, `roadmap/**`
    ensuite. Le second cas n'est pas théorique — portfolio-tracker a le sien dans
    `roadmap/provenance-cards/`, et un Hub qui ne le trouverait pas en créerait un concurrent."""
    base = PROJECTS_BASE / project.split("~")[0]
    root = base / REPRISE_NAME
    if root.exists():
        return root
    # Le moins profond gagne, à défaut d'ordre alphabétique : déterministe dans tous les cas.
    found = sorted(base.glob(f"roadmap/**/{REPRISE_NAME}"), key=lambda p: (len(p.parts), str(p)))
    return found[0] if found else None


def _reprise_pointer(raw: str) -> str:
    """La ligne pointeur telle qu'écrite, ou "" si le fichier n'en porte pas encore."""
    for line in raw.split("\n"):
        if POINTER_RE.match(line):
            return line.strip()
    return ""


def _pointer_target(pointer: str) -> str:
    """Le chemin inscrit dans la ligne pointeur (`roadmap/{nom}.md`), ou "" — « aucune » compris."""
    m = re.search(r"`([^`]+\.md)`", pointer)
    return m.group(1) if m else ""


def _inscribe_roadmap(raw: str, target: str) -> str:
    """Écrit le pointeur « roadmap active » dans un fichier de reprise, et RIEN d'autre.

    Le fichier de reprise est de format libre : le Hub n'a donc le droit d'y toucher qu'une
    seule ligne. Substitution quand le pointeur existe, insertion juste après le frontmatter
    sinon (« en tête », §2). Idempotent par construction — inscrire deux fois rend le même
    fichier. Gardé par `checks/check_reprise_inscription.py`.
    """
    line = f"> **Roadmap active : `{target}`**"
    lines = raw.split("\n")
    for i, existing in enumerate(lines):
        if POINTER_RE.match(existing):
            lines[i] = line
            return "\n".join(lines)

    m = re.match(r"^---\n[\s\S]*?\n---\n", raw)
    head, rest = (raw[:m.end()], raw[m.end():]) if m else ("", raw)
    # Une seule ligne ajoutée quand le corps commence déjà par une ligne vide (le cas de tous
    # les fichiers de reprise du repo) : le diff git montre l'inscription, pas de l'espacement.
    sep = "" if rest.startswith("\n") else "\n"
    return f"{head}{line}\n{sep}{rest}"


def _render_saved_document(raw: str, *, body: str, status: str) -> str:
    """Rend le contenu complet d'un document après une sauvegarde depuis le Hub.

    Isolé du handler HTTP pour être vérifiable : `checks/check_frontmatter_preserved.py`
    rejoue une sauvegarde à vide sur tous les documents du repo et exige un fichier
    identique octet pour octet.
    """
    # Le frontmatter n'est JAMAIS reconstruit : il est repris octet pour octet, et seule la
    # ligne `status:` y est substituée. Le reconstruire à plat en `clé: valeur` détruisait les
    # scalaires de bloc YAML (`role: >`, `downstream: >`) et promouvait toute ligne de
    # continuation contenant un « : » en clef parasite — silencieusement, sur 31 des 46
    # documents du repo. Le Hub n'édite que le corps ; il n'a aucune raison de savoir parser
    # du YAML. Gardé par `checks/check_frontmatter_preserved.py`.
    m = re.match(r"^---\n([\s\S]*?)\n---\n?", raw)
    fm_raw = m.group(1) if m else ""
    if status in STATUS_LABEL:
        fm_raw = _set_fm_status(fm_raw, status)

    # Les textarea HTML renvoient des fins de ligne CRLF (spec HTML). Sans cette
    # normalisation, la moindre sauvegarde réécrit TOUT le fichier en CRLF et
    # `git diff` affiche le document entier comme modifié : le vrai changement est
    # noyé, et le lecteur de diff de la boucle nocturne s'ancre sur du bruit.
    body = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    # Le "\n" final garantit la newline de fin de fichier, sinon chaque sauvegarde
    # produit un « \ No newline at end of file » dans le diff.
    if not m:
        return body + "\n"
    return f"---\n{fm_raw}\n---\n\n{body}\n"


def _set_fm_status(fm_raw: str, status: str) -> str:
    """Substitue la valeur de `status:` dans un frontmatter brut, sans toucher au reste.

    Ne considère que les clefs de PREMIER NIVEAU : une ligne indentée `  status: …` appartient
    à une structure imbriquée et ne doit pas être capturée. Si la clef est absente, elle est
    ajoutée en fin de frontmatter plutôt qu'en tête, pour ne pas déplacer les lignes existantes.
    """
    lines = fm_raw.split("\n")
    for i, line in enumerate(lines):
        if re.match(r"^status\s*:", line):
            lines[i] = f"status: {status}"
            return "\n".join(lines)
    return "\n".join(lines + [f"status: {status}"]) if fm_raw else f"status: {status}"


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

    # Avancement : la checklist EST le statut (`CONTROL_SYSTEM.md` §1.3). C'est elle que lit le
    # Hub, jamais un compteur de tickets — un ticket n'est plus une unité de découpage (§7).
    boxes = re.findall(r"^\s*-\s*\[([ xX])\]", body, re.M)
    fm["done"] = sum(1 for b in boxes if b.lower() == "x")
    fm["total"] = len(boxes)

    # `roadmap/` est un fourre-tout : spec, audit, benchmark, constitution y cohabitent avec les
    # vraies roadmaps. Seul `type: roadmap` désigne une roadmap ; tout le reste est un DOCUMENT,
    # affiché mais jamais inscriptible. L'ancien défaut `chantier` nommait une maille de pilotage
    # supprimée le 2026-09-05 : il faisait passer 15 documents hétérogènes pour des chantiers.
    fm.setdefault("type", "document")

    return fm


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
    """Dépose une INTENTION BRUTE, en `brouillon` — jamais une roadmap implémentable.

    Le Hub garde la création (arbitrage du 2026-09-05) : c'est le geste naturel pour capter une
    intention quand elle arrive. Mais une intention déposée sans raffinement produit des capacités
    qu'aucun agent ne peut exécuter, d'où l'état `brouillon` et la vanne du §1 : le passage à
    `figée` se constate au terminal, capacité par capacité, et lui seul ouvre l'inscription.

    Le gabarit écrit ci-dessous est celui de `CONTROL_SYSTEM.md` §1 — ordre imposé, test
    d'acceptation par capacité, checklist — pour que la conversation de raffinement remplisse
    une structure au lieu d'en inventer une à chaque fois.
    """
    rd = _roadmap_dir(project)
    item_id = int(time.time() * 1000)
    slug = re.sub(r"[^a-z0-9-]", "", re.sub(r"\s+", "-", title[:40].lower()))
    filename = f"roadmap-{item_id}-{slug}.md"

    lines = [
        "---",
        f"id: roadmap-{item_id}",
        "type: roadmap",
        "status: brouillon",
        f"created: {datetime.now().isoformat()}",
        f"project: {project.split('~')[0]}",
        "---",
        "",
        f"# {title}",
        "",
        "> **Brouillon.** Cette roadmap n'est pas inscriptible en l'état. Elle le devient après une",
        "> conversation de raffinement au terminal, quand chaque capacité porte un ordre justifié,",
        "> un test d'acceptation observable et sa checklist (`CONTROL_SYSTEM.md` §1).",
        "",
        "## Direction (utilisateur)",
        direction.strip() or "_Aucune description_",
        "",
        "## Principe directeur",
        "*(Le cadre : ce qui est vrai quoi qu'il arrive, et ce qu'on refuse de faire.)*",
        "",
        "## Capacités (ordre imposé)",
        "*(À écrire au raffinement. L'ordre est une décision — « la doctrine avant le code »,",
        "« UX avant agent avant données » — pas une mise en page.)*",
        "",
        "### 1. {capacité} · contexte partagé : {fichiers / modèle mental}",
        "- [ ] {ce qu'il faut faire}",
        "- **Acceptation** : {fait observable qui prouve que c'est livré — pas « ça marche »}",
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

def _progress(item: dict) -> str:
    """L'avancement lu dans la checklist — la seule mesure d'état qui existe (§1.3)."""
    total = item.get("total", 0)
    if not total:
        return ""
    done = item.get("done", 0)
    color = "#2da862" if done == total else "#818cf8"
    return (f'<span class="tag" style="background:{color}22;color:{color}">'
            f'{done}/{total} capacité{"s" if total != 1 else ""}</span>')


def _card(project: str, item: dict, active: str = "") -> str:
    iid = item.get("id", "")
    preview = _e(item.get("preview", "")[:100])
    date = _fmt_date(item.get("created", ""))
    title = _e(item.get("body", "").split(chr(10))[0].lstrip("# ") or iid)
    is_active = active and active == f"roadmap/{item.get('file', '')}"
    active_html = ('<span class="tag" style="background:rgba(45,168,98,.15);color:#2da862">'
                   '★ inscrite</span>') if is_active else ""
    border = "border-color:#2da862" if is_active else ""
    return f"""
<a href="/roadmap/{_e(project)}/{_e(iid)}/edit" style="display:block">
  <div class="item-card" style="{border}">
    <div class="item-title">{title}</div>
    <div class="item-preview">{preview}</div>
    <div class="item-meta">
      {_status_badge(item.get("status", ""))}
      {active_html}
      {_progress(item)}
      <span class="item-date">{date}</span>
    </div>
  </div>
</a>"""


def _reprise_panel(project: str) -> str:
    """Le fichier de reprise en tête de page : c'est LUI qui dit où on en est, pas la liste.

    Le Hub ne le crée jamais de sa propre initiative (`CONTROL_SYSTEM.md` §2 : généré à la
    première utilisation, jamais par décret — un fichier de reprise vide se lit comme un projet
    à l'arrêt). Quand il n'existe pas, on le dit, et c'est tout.
    """
    path = _reprise_path(project)
    if not path:
        return ('<div class="section"><div class="section-title">Fichier de reprise</div>'
                f'<p class="empty">Aucun <code>{REPRISE_NAME}</code> pour ce projet. Il sera créé '
                'à la première inscription d\'une roadmap — pas avant.</p></div>')

    raw = path.read_text()
    pointer = _reprise_pointer(raw)
    rel = str(path).replace(str(PROJECTS_BASE) + "/", "")
    if pointer:
        # La ligne est du Markdown (`> **… : `x.md`**`) : on la rend en texte, gras et
        # citation retirés, plutôt que d'afficher ses marqueurs à l'écran.
        plain = re.sub(r"^>\s*", "", pointer).replace("**", "").replace("`", "")
        pointer_html = f'<div style="font-size:.9rem;color:#e8e8ea">{_e(plain)}</div>'
    else:
        pointer_html = ('<div style="font-size:.85rem;color:#888">Aucun pointeur '
                        '« Roadmap active » — rien n\'est inscrit.</div>')
    return f"""
<div class="section">
  <div class="section-title">Fichier de reprise</div>
  {pointer_html}
  <div class="item-meta" style="margin-top:.7rem">
    <span class="item-date"><code>{_e(rel)}</code></span>
    <a href="/roadmap/{_e(project)}/reprise" class="btn btn-secondary btn-sm">Lire le fichier</a>
  </div>
</div>"""


def _page_list(project: str, items: list) -> str:
    """Deux blocs, pas une hiérarchie : les ROADMAPS, puis les autres documents de `roadmap/`.

    La hiérarchie axe → chantiers qui vivait ici s'appuyait sur une filiation `roadmap:` que
    **aucun fichier du repo ne porte** (vérifié : 0 occurrence sur 15 documents) — elle mettait
    donc en scène une structure vide. Ce qui compte pour reprendre un projet est ailleurs : dans
    le pointeur du fichier de reprise, affiché en tête.
    """
    display = project.replace("~", " / ")

    reprise = _reprise_path(project)
    active = _pointer_target(_reprise_pointer(reprise.read_text())) if reprise else ""

    roadmaps = [i for i in items if i.get("type") == "roadmap"]
    others = [i for i in items if i.get("type") != "roadmap"]

    sections = ""
    if roadmaps:
        sections += ('<h3 style="font-size:.85rem;color:#818cf8;margin:1.5rem 0 .6rem;'
                     'text-transform:uppercase;letter-spacing:.05em">🗺 Roadmaps</h3>')
        sections += "".join(_card(project, r, active) for r in
                            sorted(roadmaps, key=lambda x: x.get("created", ""), reverse=True))
    if others:
        # Jamais masqués : un document qui disparaît de la vue est un document perdu.
        sections += ('<h3 style="font-size:.85rem;color:#888;margin:1.5rem 0 .6rem;'
                     'text-transform:uppercase;letter-spacing:.05em">Autres documents</h3>')
        sections += "".join(_card(project, c, active) for c in
                            sorted(others, key=lambda x: x.get("created", ""), reverse=True))
    if not items:
        sections = '<p class="empty">Aucun document dans <code>roadmap/</code> pour ce projet.</p>'

    body = f"""
<div class="page-header">
  <div class="page-title">🗺 Roadmap — {_e(display)}</div>
  <div style="display:flex;gap:.5rem">
    <a href="/tickets/{_e(project)}" class="btn btn-secondary">← Tickets</a>
    <a href="/nuit/{_e(project)}" class="btn btn-secondary">🌙 Nuits</a>
    <a href="/roadmap/{_e(project)}/new-roadmap" class="btn btn-primary">+ Roadmap</a>
  </div>
</div>
{_reprise_panel(project)}
<div class="alert" style="background:rgba(79,110,247,.08);border:1px solid rgba(79,110,247,.2);color:#818cf8;font-size:.82rem;margin-bottom:1.25rem">
  💡 Une roadmap déposée ici reste un <strong>brouillon</strong> : elle n'est pas inscriptible
  tant qu'elle n'a pas été raffinée au terminal. Une fois <strong>figée</strong>, l'inscrire
  écrit le pointeur « Roadmap active » dans le fichier de reprise — c'est ce pointeur, et rien
  d'autre, que lit « reprends le projet {_e(project.split("~")[0])} à partir du fichier de reprise ».
</div>
{sections}"""
    return _base_road(f"Roadmap — {display}", body, project)


def _page_reprise(project: str, path: Path) -> str:
    """Lecture seule. Le fichier de reprise est de format libre et s'édite au terminal : lui
    ouvrir un formulaire dans le Hub inviterait à le remplir hors de la conversation qui sait."""
    rel = str(path).replace(str(PROJECTS_BASE) + "/", "")
    body = f"""
<div class="page-header">
  <div class="page-title">📌 {_e(rel)}</div>
  <a href="/roadmap/{_e(project)}" class="btn btn-secondary">← Roadmap</a>
</div>
<div class="hint" style="margin-bottom:1rem">Lecture seule — ce fichier s'actualise en fin de
conversation, au terminal. Seule la ligne « Roadmap active » est écrite par le Hub.</div>
<pre>{_e(path.read_text())}</pre>"""
    return _base_road(rel, body, project)


def _page_new_roadmap(project: str, error: str = "") -> str:
    err_html = (f'<div class="alert" style="background:rgba(220,38,38,.12);'
                f'border:1px solid rgba(220,38,38,.3);color:#f87171">{_e(error)}</div>') if error else ""
    body = f"""
<div class="page-header">
  <div class="page-title">Nouvelle roadmap (brouillon)</div>
  <a href="/roadmap/{_e(project)}" class="btn btn-secondary">← Retour</a>
</div>
{err_html}
<div class="alert" style="background:rgba(202,138,4,.08);border:1px solid rgba(202,138,4,.25);color:#ca8a04;font-size:.82rem;margin-bottom:1.25rem">
  Dépose ici une <strong>intention brute</strong> : ce que tu veux obtenir, et pourquoi.
  Elle sera enregistrée en <strong>brouillon</strong>, donc non inscriptible — une intention
  non raffinée produit des capacités qu'aucun agent ne peut exécuter. Le découpage, l'ordre et
  les tests d'acceptation s'écrivent ensuite, avec Claude Code au terminal.
</div>
<form method="POST" action="/roadmap/{_e(project)}/new-roadmap">
  <div class="section">
    <div class="form-group">
      <label>Titre</label>
      <input type="text" name="title" placeholder="ex: Collecte et synthèse de veille" required>
    </div>
    <div class="form-group">
      <label>Direction</label>
      <textarea name="direction" rows="8"
        placeholder="Ce que tu veux obtenir, et pourquoi. Pas comment."></textarea>
      <div class="hint">Pas besoin d'être précis ni complet : c'est le raffinement au terminal
      qui rend la roadmap implémentable, et qui la fait passer en « figée ».</div>
    </div>
    <button type="submit" class="btn btn-primary">Créer le brouillon</button>
  </div>
</form>"""
    return _base_road("Nouvelle roadmap", body, project)


def _inscription_block(project: str, item: dict) -> str:
    """La vanne du §3.2, rendue visible : on montre le bouton fermé ET son motif.

    Un bouton absent se lit comme une fonctionnalité manquante et pousse à contourner ; un bouton
    fermé avec sa raison enseigne la règle. Ce qui la ferme est mécanique — `status: figée` — et
    ce statut se constate au terminal, jamais depuis cette page.
    """
    iid = item.get("id", "")
    target = f"roadmap/{item.get('file', '')}"
    reprise = _reprise_path(project)
    active = _pointer_target(_reprise_pointer(reprise.read_text())) if reprise else ""
    proj = project.split("~")[0]

    if active == target:
        state = ('<div class="alert alert-success" style="margin:0">★ Cette roadmap est '
                 f'<strong>inscrite</strong>. Dans Claude Code : <strong>« reprends le projet '
                 f'{_e(proj)} à partir du fichier de reprise »</strong>.</div>')
    elif item.get("status") != FROZEN:
        state = ('<button class="btn btn-secondary" disabled style="opacity:.5;cursor:not-allowed">'
                 '🔒 Inscrire dans le fichier de reprise</button>'
                 '<div class="hint" style="margin-top:.5rem">Fermé : à raffiner au terminal avant '
                 'inscription. Une roadmap devient <strong>figée</strong> quand chaque capacité '
                 'porte un ordre justifié, un test d\'acceptation observable et sa checklist.</div>')
    elif item.get("type") != "roadmap":
        state = ('<button class="btn btn-secondary" disabled style="opacity:.5;cursor:not-allowed">'
                 '🔒 Inscrire dans le fichier de reprise</button>'
                 '<div class="hint" style="margin-top:.5rem">Fermé : ce document n\'est pas une '
                 'roadmap (<code>type: roadmap</code> absent du frontmatter).</div>')
    else:
        replaces = (f'<div class="hint" style="margin-top:.5rem">Remplacera le pointeur actuel : '
                    f'<code>{_e(active)}</code>.</div>') if active else ""
        state = (f'<form method="POST" action="/roadmap/{_e(project)}/{_e(iid)}/inscrire" '
                 f'style="margin:0"><button type="submit" class="btn btn-primary">'
                 f'★ Inscrire dans le fichier de reprise</button></form>{replaces}')

    return (f'<div class="section"><div class="section-title">Roadmap active</div>{state}</div>')


def _page_edit(project: str, item: dict, flash: str = "") -> str:
    iid    = item.get("id", "")
    status = item.get("status", "")
    body_md = item.get("body", "")

    if flash == "saved":
        flash_html = '<div class="alert alert-success">✓ Sauvegardé.</div>'
    elif flash == "inscribed":
        flash_html = ('<div class="alert alert-success">✓ Inscrite : le pointeur « Roadmap active »'
                      ' du fichier de reprise pointe désormais ce document.</div>')
    else:
        flash_html = ""

    # L'option « inchangé » est PREMIÈRE et sélectionnée dès que le statut courant n'appartient pas
    # au vocabulaire du Hub : c'est ce qui empêche une simple sauvegarde de réécrire en silence le
    # `status:` des 13 vocabulaires qui vivent dans `roadmap/` (cf. KEEP_STATUS).
    known = status in STATUS_LABEL
    keep_label = f"— inchangé ({status}) —" if status else "— sans statut —"
    status_opts = f'<option value="{KEEP_STATUS}" {"" if known else "selected"}>{_e(keep_label)}</option>'
    status_opts += "".join(
        f'<option value="{_e(s)}" {"selected" if s == status else ""}>{STATUS_LABEL[s]}</option>'
        for s in STATUS_LABEL
    )
    title_line = body_md.split("\n")[0].lstrip("# ").strip() if body_md else iid
    done, total = item.get("done", 0), item.get("total", 0)
    progress_hint = (f'<div class="hint" style="margin-bottom:.75rem">Avancement lu dans la '
                     f'checklist : <strong>{done}/{total}</strong> capacité(s) cochée(s). '
                     f'C\'est cette checklist — et elle seule — qui porte l\'état.</div>'
                     ) if total else ""

    body = f"""
{flash_html}
<div class="page-header">
  <div style="display:flex;align-items:center;gap:.75rem;flex-wrap:wrap">
    <div class="page-title">{_e(title_line)}</div>
    {_status_badge(status)}
  </div>
  <a href="/roadmap/{_e(project)}" class="btn btn-secondary">← Roadmap</a>
</div>

{_inscription_block(project, item)}

<form method="POST" action="/roadmap/{_e(project)}/{_e(iid)}/edit">
  <div class="section">
    <div class="section-title">Statut</div>
    <div class="form-group" style="max-width:280px">
      <select name="status">{status_opts}</select>
    </div>
    <div class="hint">Le passage en « figée » se constate au terminal, capacité par capacité.
    Le forcer ici ouvrirait l'inscription sur une liste de vœux.</div>
  </div>
  <div class="section">
    <div class="section-title">Contenu (Markdown)</div>
    {progress_hint}
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
      onsubmit="return confirm('Supprimer ce document ?')">
  <button type="submit" class="btn btn-danger btn-sm">Supprimer ce document</button>
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


# Les routes littérales (`/new-roadmap`, `/reprise`) doivent précéder `/{item_id}/…`,
# sinon FastAPI les capture comme un item_id et la page devient un 404.
@router.get("/{project}/reprise", response_class=HTMLResponse)
async def roadmap_reprise(request: Request, project: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _reprise_path(project)
    if not path:
        return HTMLResponse(f"Aucun {REPRISE_NAME} pour {_e(project)}.", status_code=404)
    return HTMLResponse(_page_reprise(project, path))


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
    status: str = Form(default=KEEP_STATUS), body: str = Form(default=""),
):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if not path:
        return HTMLResponse(f"Item introuvable : {_e(item_id)}", status_code=404)

    path.write_text(_render_saved_document(path.read_text(), body=body, status=status))
    return RedirectResponse(f"/roadmap/{project}/{item_id}/edit?flash=saved", status_code=303)


@router.post("/{project}/{item_id}/inscrire")
async def roadmap_inscribe(request: Request, project: str, item_id: str):
    """L'activation EST l'inscription (`CONTROL_SYSTEM.md` §2) : cette route est le seul endroit
    où le Hub écrit hors de `roadmap/`, et elle n'y écrit qu'une ligne."""
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if not path:
        return HTMLResponse(f"Item introuvable : {_e(item_id)}", status_code=404)

    item = _parse_item(path)
    # La vanne est re-vérifiée ICI, pas seulement dans la vue : un bouton désactivé côté HTML
    # n'empêche personne de poster l'URL, et inscrire un brouillon lancerait un agent sur une
    # liste de vœux.
    if item.get("type") != "roadmap" or item.get("status") != FROZEN:
        return HTMLResponse(
            f"Inscription refusée : « {_e(path.name)} » n'est pas une roadmap figée "
            f"(type={_e(item.get('type', ''))}, status={_e(item.get('status', ''))}). "
            f"Le passage en « figée » se constate au terminal.", status_code=400)

    reprise = _reprise_path(project)
    if reprise:
        reprise.write_text(_inscribe_roadmap(reprise.read_text(), f"roadmap/{path.name}"))
    else:
        # Première utilisation : c'est le seul cas où le Hub crée un fichier de reprise, et il
        # n'y met que ce qu'il sait (§2 — un fichier de reprise vide se lit comme un projet à
        # l'arrêt, donc pas de sections creuses à remplir « plus tard »).
        proj = project.split("~")[0]
        reprise = PROJECTS_BASE / proj / REPRISE_NAME
        reprise.write_text(f"# Reprise — {proj}\n\n> **Roadmap active : `roadmap/{path.name}`**\n")
    return RedirectResponse(f"/roadmap/{project}/{item_id}/edit?flash=inscribed", status_code=303)


@router.post("/{project}/{item_id}/delete")
async def roadmap_delete(request: Request, project: str, item_id: str):
    from app.main import settings
    if r := _require_auth(request, settings): return r
    path = _item_path(project, item_id)
    if path and path.exists():
        path.unlink()
    return RedirectResponse(f"/roadmap/{project}", status_code=303)
