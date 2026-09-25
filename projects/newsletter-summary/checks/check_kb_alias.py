#!/usr/bin/env python3
"""KB : un résumé d'alias porte le nom de l'alias ; sans alias l'enveloppe reste celle d'avant.

Deux exigences en tension : (1) « écrire en KB les mails des alias en notant l'alias concerné » ;
(2) ne pas changer l'enveloppe KNOWLEDGE_ARCHITECTURE §3 déjà écrite pour la newsletter — l'export
fédéré `GET /api/kb` en dépend. Le contrôle (2) fige la forme d'avant sur une ligne réelle.
"""
from datetime import datetime

import _harness  # noqa: F401
from app.kb import build_envelope
from app.models import Email

E = Email(message_id="<20260905060003.6b8c170fa12e871b@newsletter.euractiv.com>", email_id="77257e8f-7fe2-4dd2-a0d9-0f2fb0a64662",
          from_addr="no-reply@newsletter.euractiv.com", subject="It’s (not) the economy, dummkopf!",
          summary="<h3>Titre</h3><p>Corps</p>", received_at=datetime(2026, 9, 5, 6, 0, 3))

old = build_envelope(E)
assert old["tags"] == [] and old["uri"] == "resend:77257e8f-7fe2-4dd2-a0d9-0f2fb0a64662", "enveloppe sans alias modifiée (uri/tags)"
assert set(old["metadata_"]) == {"message_id", "email_id", "from_addr"}, f"clés metadata d'avant modifiées : {set(old['metadata_'])}"

new = build_envelope(E, alias="summary")
assert new["tags"] == ["alias:summary"], f"tag d'alias absent : {new['tags']}"
assert new["metadata_"]["alias"] == "summary" and new["uri"] == old["uri"], "alias : metadata.alias + uri inchangée"

link = build_envelope(E, alias="lien", source_url="https://exemple.org/article")
assert link["uri"] == "https://exemple.org/article" and link["metadata_"]["source_url"] == "https://exemple.org/article", "mail-lien : l'URL devient l'uri canonique"
assert link["doc_id"] == old["doc_id"] and link["content_hash"] == old["content_hash"], "doc_id/hash ne doivent dépendre ni de l'alias ni de l'URL"
print("OK — enveloppe d'avant inchangée ; tag alias:<nom> ; URL source en uri pour un mail-lien")
