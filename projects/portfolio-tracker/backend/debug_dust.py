#!/usr/bin/env python3
"""
Debug offline du parser Dust.
Usage :
  # Copier la dernière réponse depuis le container
  docker cp portfoliobackend00000000-XXXXX:/tmp/dust_last_response.json /tmp/

  # Lancer le debug
  python3 debug_dust.py [/tmp/dust_last_response.json]
"""
import json
import sys
import re

RESPONSE_FILE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/dust_last_response.json"

with open(RESPONSE_FILE) as f:
    saved = json.load(f)

agent_id = saved.get("agent_id")
model_override = saved.get("model_override")
data = saved["data"]

conv_id = data.get("conversation", {}).get("sId", "?")
print(f"\n=== Dust response debug — conv {conv_id} (agent {agent_id}) ===\n")

# ── 1. Structure conversation ─────────────────────────────────────────────────
content_groups = data.get("conversation", {}).get("content", [])
print(f"Groupes dans conversation.content : {len(content_groups)}")
for i, group in enumerate(content_groups):
    msgs = [group] if isinstance(group, dict) else group
    for msg in msgs:
        if not isinstance(msg, dict):
            print(f"  [{i}] non-dict : {type(msg).__name__} → {repr(msg)[:80]}")
            continue
        mtype  = msg.get("type")
        status = msg.get("status", "-")
        print(f"  [{i}] type={mtype}  status={status}")
        if mtype == "agent_message":
            blocks = msg.get("content", [])
            print(f"       blocks ({len(blocks)}) :")
            for j, b in enumerate(blocks[:10]):
                if isinstance(b, str):
                    print(f"         [{j}] STRING  len={len(b)}  preview={repr(b[:120])}")
                elif isinstance(b, dict):
                    btype = b.get("type")
                    keys  = list(b.keys())
                    val   = b.get("value") or b.get("text") or ""
                    print(f"         [{j}] dict  type={btype}  keys={keys}  preview={repr(str(val)[:120])}")
                else:
                    print(f"         [{j}] {type(b).__name__}  {repr(b)[:80]}")
            usage = msg.get("usage", {})
            print(f"       usage: {usage}")

# ── 2. Extraction (logique actuelle) ─────────────────────────────────────────
print("\n=== Extraction (parser actuel) ===\n")

extracted = ""
for group in reversed(content_groups):
    msgs = [group] if isinstance(group, dict) else group
    for msg in msgs:
        if not isinstance(msg, dict):
            continue
        if msg.get("type") == "agent_message" and msg.get("status") == "succeeded":
            blocks = msg.get("content", [])
            parts = []
            for b in blocks:
                if isinstance(b, str):
                    parts.append(b)
                elif isinstance(b, dict) and b.get("type") == "text":
                    parts.append(b.get("value") or b.get("text") or "")
            extracted = "".join(parts)
            break

print(f"Contenu extrait : {len(extracted)} caractères")
if not extracted:
    print("⚠  VIDE — rien à parser")
    sys.exit(1)

print(f"Début : {repr(extracted[:200])}")
print(f"Fin   : {repr(extracted[-200:])}")

# ── 3. Parse JSON ─────────────────────────────────────────────────────────────
print("\n=== Parse JSON ===\n")

j = extracted.find("```json")
try:
    if j >= 0:
        end = extracted.find("```", j + 7)
        raw = extracted[j + 7:end].strip()
        print(f"Bloc ```json trouvé ({len(raw)} chars)")
        thesis = json.loads(raw)
    else:
        start = extracted.find("{")
        end   = extracted.rfind("}") + 1
        raw   = extracted[start:end]
        print(f"Pas de ```json, extraction accolades ({len(raw)} chars)")
        thesis = json.loads(raw)
    print(f"✅  JSON valide — clés : {list(thesis.keys())}")
    if "prequalification" in thesis:
        print(f"    prequalification = {thesis['prequalification']}")
    if "hypotheses" in thesis:
        print(f"    hypothèses : {len(thesis['hypotheses'])}")
    if "schema_json" in thesis:
        print(f"    schema_json présent : {list(thesis['schema_json'].keys()) if isinstance(thesis['schema_json'], dict) else type(thesis['schema_json']).__name__}")
except json.JSONDecodeError as e:
    print(f"❌  JSONDecodeError : {e}")
    print(f"    Extrait tenté : {repr(raw[:300])}")
