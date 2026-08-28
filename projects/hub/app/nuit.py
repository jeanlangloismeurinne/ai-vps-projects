"""Onglet « Nuit » — ce que la boucle autonome a produit, en LECTURE SEULE.

Pourquoi cet onglet existe : tant que la branche de la nuit n'est pas fusionnée,
son travail est invisible depuis le Hub. Le pilotage se faisait donc entièrement
depuis Claude Code, alors que le Hub est l'endroit où l'utilisateur regarde son
avancement. Cette vue rend la nuit lisible avant l'arbitrage.

Ce qu'elle n'est PAS : une surface de décision. Aucune route POST ici, aucun
bouton de fusion, aucune écriture. L'arbitrage reste dans `/revue-nuit`, où
l'agent peut confronter les rapports au diff réel — un bouton « fusionner »
dans le Hub donnerait l'illusion qu'on peut trancher sans avoir lu.

Source des données : `projects/{projet}/.nuits/{date}/`, dans le bind-mount
`/projects` que le Hub possède déjà. On ne monte **pas** `/srv/auto-loop` : le
conteneur tourne en root, il y lirait `.scratch-pw` (mot de passe de la base
scratch, 600 root). Et Coolify ne sait de toute façon pas monter en lecture
seule — `--volume` n'est pas dans la liste blanche de `convertDockerRunToCompose`.

C'est donc root qui publie, après la nuit, via `/srv/auto-loop/publish.sh`
(`ExecStartPost=`). La boucle n'a aucun accès à `/root/ai-vps-projects` et ne
peut pas publier elle-même : cette isolation est voulue et on ne la contourne
pas pour un onglet. Le dossier publié est autoportant — le conteneur n'a pas
`git` et ne pourrait pas reconstituer la branche.
"""
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.roadmap import _e, _base_road, PROJECTS_BASE

router = APIRouter(prefix="/nuit")

# Les segments d'URL servent à composer des noms de fichiers. On les valide par
# liste blanche plutôt que par assainissement : un `..` ou un `/` glissé dans
# `project` ferait lire hors du montage. Une regex qui n'autorise que
# [a-z0-9-] ne peut produire aucune traversée, quelle que soit la suite du code.
_PROJECT_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# L'ordre est imposé, et c'est le cœur de la vue.
#
# La lecture indépendante vient EN PREMIER parce que le rapport de la boucle est
# l'artefact le moins fiable du dispositif : il est écrit par le modèle qui a
# fait le travail, d'après son intention et non d'après le code produit. Lu en
# premier, il sert de grille de lecture à tout le reste et on relit la lecture
# indépendante à travers lui. L'ordre n'est donc pas une préférence de mise en
# page, c'est le mécanisme anti-ancrage lui-même.
SECTIONS = [
    ("lecture", "🔍 Lecture indépendante du diff", "lecture.md",
     "Écrite par un agent qui n'a lu que le code : ni le rapport de la boucle, "
     "ni les messages de commit. C'est le document de référence."),
    ("rapport", "🤖 Rapport de la boucle", "rapport.md",
     "Peu fiable par construction : écrit par le modèle qui a fait le travail, "
     "d'après son intention. À confronter au document ci-dessus, jamais à lire seul."),
    ("propositions", "🧭 Propositions pour la nuit suivante", "propositions.md",
     "Généré mécaniquement depuis le chantier sur disque — il existe toujours, "
     "même après un plantage en pleine nuit."),
]


def _safe(project: str, date: str = "") -> bool:
    return bool(_PROJECT_RE.match(project)) and (not date or bool(_DATE_RE.match(date)))


def _nuits_dir(project: str) -> Path:
    # `project` est déjà validé par _safe() en amont de tout appel : la
    # concaténation ne peut donc pas sortir de PROJECTS_BASE.
    return PROJECTS_BASE / project.split("~")[0] / ".nuits"


def _nights(project: str) -> list[str]:
    """Nuits publiées pour ce projet, plus récente d'abord."""
    d = _nuits_dir(project)
    if not d.is_dir():
        return []
    return sorted((f.name for f in d.iterdir()
                   if f.is_dir() and _DATE_RE.match(f.name)), reverse=True)


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


# ── Rendu Markdown minimal ─────────────────────────────────────────────────────

def _md(raw: str) -> str:
    """Rendu volontairement pauvre, mais qui ne perd AUCUNE ligne.

    Le Hub n'embarque pas de bibliothèque Markdown et ce n'est pas la peine d'en
    ajouter une pour trois rapports. La contrainte retenue n'est pas la fidélité
    typographique mais la conservation : chaque ligne d'entrée produit une ligne
    de sortie. Un rendu approximatif se corrige à l'œil ; une ligne avalée par un
    parseur trop malin ne se voit pas, et c'est exactement ce qu'on ne peut pas
    se permettre sur l'artefact qui sert à détecter les écarts.

    Vérifié en comparant, sur tous les rapports existants, le flux de caractères
    d'entrée et de sortie marqueurs retirés : identiques. Seule exception, voulue :
    l'étiquette de langage d'une clôture de bloc (```bash), qui est une consigne
    de rendu et non du contenu.

    Tout est échappé d'abord : ces fichiers contiennent du diff et du code écrits
    par un modèle, donc du contenu non fiable qu'on n'injecte pas tel quel.
    """
    out, in_code = [], False
    for line in _e(raw).split("\n"):
        if line.startswith("```"):
            in_code = not in_code
            out.append('<div class="code">' if in_code else "</div>")
            continue
        if in_code:
            out.append(line if line.strip() else "&nbsp;")
            continue
        # `code`, **gras** — appliqués hors bloc de code uniquement.
        line = re.sub(r"`([^`]+)`", r'<code>\1</code>', line)
        line = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", line)
        if m := re.match(r"^(#{1,4})\s+(.*)$", line):
            lvl = len(m.group(1))
            size = {1: "1.05rem", 2: ".95rem", 3: ".88rem", 4: ".84rem"}[lvl]
            color = "#e8e8ea" if lvl <= 2 else "#a5b4fc"
            out.append(f'<div style="font-size:{size};font-weight:700;color:{color};'
                       f'margin:1.1rem 0 .4rem">{m.group(2)}</div>')
        elif line.startswith("&gt;"):
            out.append(f'<div class="quote">{line[4:].strip()}</div>')
        elif re.match(r"^[-*]\s+", line):
            out.append(f'<div class="li">{line[2:]}</div>')
        elif not line.strip():
            out.append('<div style="height:.5rem"></div>')
        else:
            out.append(f"<div>{line}</div>")
    if in_code:            # fence non refermée : on ne laisse pas de div ouverte
        out.append("</div>")
    return "\n".join(out)


_CSS = """
<style>
  .doc{background:#131620;border:1px solid #2a2d3a;border-radius:12px;padding:1.2rem 1.4rem;
       font-size:.84rem;line-height:1.65;color:#c8ccd6;overflow-wrap:anywhere}
  .doc code{background:#0f1117;border:1px solid #2a2d3a;border-radius:4px;padding:.05rem .3rem;
       font-family:ui-monospace,monospace;font-size:.92em;color:#a5b4fc}
  .doc .code{background:#0f1117;border:1px solid #2a2d3a;border-radius:8px;padding:.7rem .9rem;
       margin:.5rem 0;font-family:ui-monospace,monospace;font-size:.78rem;
       white-space:pre-wrap;color:#9aa2b1}
  .doc .code code{background:none;border:none;padding:0}
  .doc .quote{border-left:3px solid #4f6ef7;padding-left:.8rem;color:#8b93a3;margin:.3rem 0}
  .doc .li{padding-left:1.1rem;text-indent:-.7rem}
  .sec-head{display:flex;align-items:baseline;gap:.6rem;margin:2rem 0 .5rem;flex-wrap:wrap}
  .sec-title{font-size:1rem;font-weight:700}
  .sec-why{font-size:.78rem;color:#6b7280;margin-bottom:.7rem;line-height:1.5}
  .missing{color:#6b7280;font-size:.82rem;font-style:italic;padding:.8rem 0}
  .night-row{display:flex;justify-content:space-between;align-items:center;gap:1rem}
</style>
"""

_READONLY = (
    '<div class="alert" style="background:rgba(202,138,4,.1);border:1px solid rgba(202,138,4,.3);'
    'color:#ca8a04;font-size:.82rem">'
    '🔒 <strong>Lecture seule.</strong> Rien ne se fusionne depuis cette page. '
    'L\'arbitrage se fait dans Claude Code via <code>/revue-nuit {p}</code> — c\'est là que les '
    'rapports peuvent être confrontés au diff réel avant que quoi que ce soit n\'entre dans '
    '<code>main</code>.</div>'
)


def _page_index(project: str, nights: list[str]) -> str:
    if not nights:
        rows = (f'<p class="missing">Aucune nuit publiée pour « {_e(project)} ». '
                'La boucle autonome n\'a pas encore tourné sur ce projet, ou sa nuit '
                'n\'a pas été publiée.</p>')
    else:
        rows = ""
        for d in nights:
            docs = _nuits_dir(project) / d / "docs"
            n = len([f for f in docs.rglob("*.md") if f.name != "MANIFEST.md"]) if docs.is_dir() else 0
            try:
                label = datetime.fromisoformat(d).strftime("%d/%m/%Y")
            except ValueError:
                label = d
            rows += f"""
<a href="/nuit/{_e(project)}/{_e(d)}" style="display:block">
  <div class="item-card"><div class="night-row">
    <div>
      <div class="item-title">Nuit du {label}</div>
      <div class="item-preview">{n} document{"s" if n != 1 else ""} produit{"s" if n != 1 else ""}</div>
    </div>
    <span style="color:#4f6ef7">→</span>
  </div></div>
</a>"""

    body = f"""{_CSS}
<div class="page-header">
  <div class="page-title">🌙 Nuits — {_e(project)}</div>
  <a href="/roadmap/{_e(project)}" class="btn btn-secondary">← Roadmap</a>
</div>
{_READONLY.replace("{p}", _e(project))}
{rows}"""
    return _base_road(f"Nuits — {project}", body, project)


def _page_night(project: str, date: str) -> str:
    body = f"""{_CSS}
<div class="page-header">
  <div class="page-title">🌙 Nuit du {_e(date)} — {_e(project)}</div>
  <a href="/nuit/{_e(project)}" class="btn btn-secondary">← Toutes les nuits</a>
</div>
{_READONLY.replace("{p}", _e(project))}"""

    night = _nuits_dir(project) / date
    for _key, title, fname, why in SECTIONS:
        txt = _read(night / fname)
        body += f'<div class="sec-head"><div class="sec-title">{title}</div></div>'
        body += f'<div class="sec-why">{why}</div>'
        body += (f'<div class="doc">{_md(txt)}</div>' if txt
                 else '<p class="missing">Absent — la nuit ne l\'a pas produit.</p>')

    # Les documents eux-mêmes, en dernier : ils sont la matière, pas la grille de
    # lecture. Les placer avant les rapports inviterait à juger le travail sur sa
    # présentation plutôt que sur l'écart entre ce qui est annoncé et ce qui est fait.
    docs = night / "docs"
    body += ('<div class="sec-head"><div class="sec-title">📄 Documents produits</div></div>'
             '<div class="sec-why">Copie de fin de nuit, telle quelle. La source de vérité '
             'reste la branche git ; ceci en est une vitrine.</div>')
    if docs.is_dir():
        manifest = _read(docs / "MANIFEST.md")
        if manifest:
            body += f'<div class="doc" style="margin-bottom:1rem">{_md(manifest)}</div>'
        files = sorted(f for f in docs.rglob("*.md") if f.name != "MANIFEST.md")
        for f in files:
            rel = f.relative_to(docs)
            content = _read(f)
            body += (f'<div class="sec-head"><div class="sec-title" style="font-size:.85rem;'
                     f'color:#a5b4fc">{_e(str(rel))}</div></div>')
            body += (f'<div class="doc">{_md(content)}</div>' if content
                     else '<p class="missing">Illisible.</p>')
        if not files:
            body += '<p class="missing">Aucun document — la nuit n\'a rien écrit.</p>'
    else:
        body += '<p class="missing">Aucun instantané pour cette nuit.</p>'

    return _base_road(f"Nuit {date} — {project}", body, project)


# ── Routes (GET uniquement — voir l'en-tête du module) ─────────────────────────

@router.get("/{project}", response_class=HTMLResponse)
async def nuit_index(request: Request, project: str):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    if not _safe(project):
        return HTMLResponse("Projet invalide.", status_code=400)
    return HTMLResponse(_page_index(project, _nights(project)))


@router.get("/{project}/{date}", response_class=HTMLResponse)
async def nuit_detail(request: Request, project: str, date: str):
    from app.main import settings
    from app.roadmap import _require_auth
    if r := _require_auth(request, settings):
        return r
    if not _safe(project, date):
        return HTMLResponse("Projet ou date invalide.", status_code=400)
    return HTMLResponse(_page_night(project, date))
