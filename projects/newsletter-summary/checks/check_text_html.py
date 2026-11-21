#!/usr/bin/env python3
"""Version texte figée : le résumé doit porter sur ce que le lecteur voit (le HTML).

Payload (routeur Omeda) envoie depuis le 2026-11-02 une partie text/plain figée sur un vieux numéro
(« Neuraspace, Arcsec Team Up On Debris Tracking ») à côté d'un HTML correct : 20 digests ont résumé
le vieux numéro. Fixtures copiées du réel (URLs neutralisées) :
  293 — Payload, le cas figé le PLUS ressemblant à son HTML (0,40) ;
  324 — Payload Pro, autre liste du même routeur ;
  120 — La Matinale, le mail sain le MOINS ressemblant à son HTML (0,69) : il doit garder son texte.
"""
import json

import _harness  # noqa: F401  (chemin, logs)
from app.models import Email
from app.summarizer import _html2text, _to_plain

FX = _harness.GOLDEN / "text_html"


def load(i: int) -> Email:
    d = json.loads((FX / f"email_{i}.json").read_text())
    return Email(message_id=f"fx-{i}", text_body=d["text_body"], html_body=d["html_body"])


for i in (293, 324):
    plain = _to_plain(load(i))
    assert "Neuraspace" not in plain, f"T1 ({i}) : le résumé porterait sur la version texte figée (vieux numéro)"
    assert plain == _html2text.handle(load(i).html_body).strip(), f"T1 ({i}) : attendu le HTML converti"

sain = load(120)
assert _to_plain(sain) == sain.text_body.strip(), "T2 (120) : un mail sain doit garder sa version texte"

assert _to_plain(Email(message_id="t", text_body=" seul texte ", html_body="")) == "seul texte", "T3 : texte seul"
assert _to_plain(Email(message_id="h", text_body="", html_body="<p>seul HTML</p>")) == "seul HTML", "T3 : HTML seul"
assert _to_plain(Email(message_id="v", text_body="", html_body="")) == "", "T3 : mail vide"
print("OK — texte figé écarté (Payload, Payload Pro) ; texte sain conservé (pire cas réel 0,69) ; corps mono-partie inchangés")
