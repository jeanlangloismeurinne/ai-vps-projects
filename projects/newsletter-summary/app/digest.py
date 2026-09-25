"""Rendu des e-mails de résumé : enveloppe HTML, cartes, corps texte, libellés.

L'orchestration (qui résumer, à qui envoyer, quand) vit dans `alias_digest.py` ; ce module ne
fait que produire le texte et le HTML. Le rendu de la newsletter d'origine y est conservé à
l'identique (fixture gelée `checks/golden/legacy_digest.json`).
"""
from __future__ import annotations

import html as html_mod
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

from app.models import Email

logger = logging.getLogger(__name__)

PARIS_TZ = timezone(timedelta(hours=1))  # Hiver ; géré via heure système Europe/Paris du container

# Conversion HTML → texte pour le corps *plain* (fallback clients sans HTML / lisible).
_html2text = None  # init paresseuse pour éviter un import lourd au chargement


def _summary_to_text(html_block: str) -> str:
    """Convertit un bloc de résumé HTML en texte brut lisible (pour le fallback email)."""
    global _html2text
    if not html_block:
        return ""
    if _html2text is None:
        import html2text
        _html2text = html2text.HTML2Text()
        _html2text.ignore_links = False
        _html2text.body_width = 0
    return _html2text.handle(html_block).strip()


def _esc(value: str) -> str:
    return html_mod.escape(value or "", quote=True)


# --- Coquille HTML minimale (enveloppe uniquement) : le contenu de chaque carte est
# --- généré par DeepSeek (bloc HTML autonome, cf. summarize_html). C'est l'« Option B » :
# --- le LLM pilote la mise en page de chaque carte, le code ne fournit que l'encadrement.
_ENVELOPPE_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#eef1f5;font-family:Helvetica,Arial,sans-serif;-webkit-text-size-adjust:100%;">
  <div style="max-width:640px;margin:0 auto;padding:0;">
    <div style="background:#1f2937;color:#ffffff;padding:18px 16px;">
      <h1 style="margin:0;font-size:20px;line-height:1.3;">📬 {title}</h1>
      <p style="margin:8px 0 0;font-size:13px;opacity:.85;">{date} — {count} {label}(s)</p>
    </div>
    <div style="background:#ffffff;padding:12px 0;">
{cards}
    </div>
    <p style="text-align:center;color:#9ca3af;font-size:11px;margin:16px 0 0;">
      {footer}
    </p>
  </div>
</body>
</html>"""


# --- Carte : ouverture/fermeture DÉTERMINISTES côté code (le modèle ne produit
# --- QUE le corps du résumé). L'en-tête expéditeur/sujet est lui aussi rendu par le
# --- code — le modèle n'a donc plus à émettre le moindre <div> d'encadrement.
# --- Conséquence : une carte ne peut JAMAIS en avaler une autre, même si la sortie du
# --- modèle est malformée ou incomplète. Marges latérales nulles (plein écran mobile),
# --- padding interne conservé pour que le texte ne colle pas au bord.
_CARD_OPEN = (
    '<div style="background:#f6f8fa;border:1px solid #e5e7eb;border-radius:8px;'
    'padding:16px 18px;margin:0 0 16px;">'
)
_CARD_CLOSE = "</div>"


def _card_header(email: Email, from_line: str | None = None, subject_line: str | None = None) -> str:
    """En-tête de carte (expéditeur + sujet), rendu par le code — pas par le modèle.

    `from_line` / `subject_line` : surcharges d'affichage (mail réduit à un lien : l'URL et le titre
    de la page). Absentes = expéditeur et sujet du mail, comme avant.
    """
    frm = email.from_addr if from_line is None else from_line
    sub = email.subject if subject_line is None else subject_line
    return (
        f'<div style="font-size:12px;color:#6b7280;margin:0 0 2px;word-break:break-word;">'
        f'{_esc(frm or "")}</div>'
        f'<div style="font-weight:bold;font-size:16px;color:#111827;line-height:1.35;'
        f'margin:0 0 10px;">{_esc(sub or "(sans objet)")}</div>'
    )


def _fallback_inner(email: Email, error: str = "") -> str:
    """Corps de secours (sans carte ni en-tête : ajoutés par le code) si le résumé manque."""
    msg = "⚠ Résumé indisponible." if not error else f"⚠ Résumé en échec — {_esc(error)}"
    return f'<p style="margin:0;font-size:14px;color:#374151;">{msg}</p>'


def _sanitize_inner(raw: str) -> str:
    """Neutralise le corps produit par le modèle pour qu'il ne puisse PAS casser la carte.

    - retire un éventuel bloc de code Markdown (```html … ```) ;
    - si le modèle a malgré tout enveloppé son corps dans un <div> de carte, on le
      déballe (le cadre est fourni par le code) ;
    - coupe une balise finale non terminée (sortie tronquée) ;
    - ÉQUILIBRE les <div> : ajoute les fermetures manquantes / retire les fermetures en
      trop, pour que le corps soit strictement neutre et ne déborde jamais de la carte.
    """
    s = (raw or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    # Retire un <div> d'encadrement/carte en TÊTE (le cadre est fourni par le code) — même si
    # le bloc a été tronqué et n'a jamais refermé ce div (cas des anciens résumés « carte
    # autonome »). Le rééquilibrage plus bas retire alors la fermeture surnuméraire d'un
    # wrapper complet.
    s = re.sub(r"^<div\b[^>]*>\s*", "", s, count=1, flags=re.IGNORECASE).strip()
    # Coupe une balise ouverte non terminée en fin de chaîne (troncature).
    lt, gt = s.rfind("<"), s.rfind(">")
    if lt > gt:
        s = s[:lt].rstrip()
    # Équilibre les <div>.
    opens = len(re.findall(r"<div\b", s, re.IGNORECASE))
    closes = len(re.findall(r"</div\s*>", s, re.IGNORECASE))
    if opens > closes:
        s += "</div>" * (opens - closes)
    elif closes > opens:
        for _ in range(closes - opens):
            s = re.sub(r"</div\s*>\s*$", "", s, count=1).rstrip()
    return s


def _card_html(email: Email, from_line: str | None = None, subject_line: str | None = None) -> str:
    """Carte d'une newsletter : ouverture + en-tête + corps + fermeture, tout côté code.

    Le modèle ne fournit que le corps (`email.summary`), passé au sanitizer. Les balises de
    carte (`_CARD_OPEN`/`_CARD_CLOSE`) et l'en-tête sont déterministes : aucune sortie du
    modèle, même tronquée, ne peut faire déborder une carte sur la suivante.
    """
    s = email.summary or ""
    if s.strip():
        body = _sanitize_inner(s)
    else:
        error = getattr(email, "_summary_error", "") or ""
        body = _fallback_inner(email, error=error)
    return f"{_CARD_OPEN}{_card_header(email, from_line, subject_line)}{body}{_CARD_CLOSE}"


@dataclass
class Item:
    """Un mail à rendre, avec ses éventuelles surcharges d'en-tête (mail réduit à un lien)."""
    email: Email
    from_line: str | None = None
    subject_line: str | None = None


def today_label() -> str:
    return datetime.now(PARIS_TZ).strftime("%A %d %B %Y")


def render_html(items: list[Item], pres: dict, today: str) -> str:
    """E-mail HTML : enveloppe + une carte par mail (cadre et en-tête produits par le code)."""
    cards = "\n".join(_card_html(i.email, i.from_line, i.subject_line) for i in items)
    return _ENVELOPPE_HTML.format(
        date=_esc(today), count=len(items), cards=cards,
        title=_esc(pres["title"]), label=_esc(pres["label"]), footer=_esc(pres["footer"]),
    )


def render_text(items: list[Item], pres: dict, today: str) -> str:
    """Corps texte (fallback : clients non-HTML, lisibilité)."""
    lines = [
        f"{pres['title']} — {today}",
        pres["count_line"].format(count=len(items)),
        "",
    ]
    for it in items:
        email = it.email
        lines.append("─" * 40)
        lines.append(f"■ {email.from_addr if it.from_line is None else it.from_line} — "
                     f"{email.subject if it.subject_line is None else it.subject_line}")
        lines.append("")
        summary_text = _summary_to_text(email.summary) if email.summary else ""
        if summary_text:
            lines.append(summary_text)
        elif getattr(email, "_summary_error", ""):
            # Le motif nommé doit aussi arriver en texte brut (l'ancien rendu disait « (vide) »).
            lines.append(f"⚠ Résumé en échec — {email._summary_error}")
        elif not email.text_body and not email.html_body:
            lines.append("⚠ Corps non reçu — Resend n'a transmis que les métadonnées (pas de text/html).")
        else:
            lines.append("(vide)")
        lines.append("")
    return "\n".join(lines)


def render_subject(items: list[Item], pres: dict, today: str, single: bool) -> str:
    """Objet. `single` (cadence « chaque minute » : un e-mail par mail) → gabarit à l'unité."""
    tpl = pres["subject_single"] if single else pres["subject"]
    subject = items[0].email.subject if items else ""
    return tpl.format(count=len(items), date=today, subject=subject or "(sans objet)")
