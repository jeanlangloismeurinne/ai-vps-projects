#!/usr/bin/env python3
"""Test négatif rejouable : chaque garde du chantier alias est MUTÉE, le check qui la protège doit
virer au rouge — avec le bon message. Un check qui n'a jamais rougi ne prouve rien.

Pour chaque mutation : le fichier est modifié, le check lancé (checks/run.sh), puis le fichier est
RESTAURÉ quoi qu'il arrive (finally). Verdict : ROUGE-OK (échec ET message attendu), FAUX-VERT (le
check passe malgré la mutation : garde jamais atteinte), MAUVAIS-ROUGE (échec, mais pas pour la raison
attendue : la garde n'est pas celle qu'on croit).

Lancer (hôte) :  python3 projects/newsletter-summary/checks/mutations.py [filtre]
Sortie finale :  BILAN mutations : N/N rouges pour la bonne raison   (exit ≠ 0 sinon)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A, AD, P, U, K, D = "app/aliases.py", "app/alias_digest.py", "app/prompts.py", "app/urlfetch.py", "app/kb.py", "app/database.py"

# (nom, fichier, ancien, nouveau, check, message attendu dans la sortie)
MUTATIONS = [
    # ── réservation, cadences, regroupement ──
    ("réservation non atomique", AD, 'values(status="processing", claimed_at=_now())', 'values(claimed_at=_now())', "check_engine", "S4"),
    ("minute regroupée en lot", AD, 'if alias.frequency == "minute":\n            out.append', 'if False:\n            out.append', "check_engine", "S0"),
    ("cadences non isolées", AD, "Alias.frequency == frequency", "Alias.frequency.isnot(None)", "check_engine", "S1"),
    # ── admission et plafond ──
    ("admission au traitement supprimée", AD, "ok, reason = al.admit(alias, e.from_addr)", 'ok, reason = True, ""', "check_engine", "S3"),
    ("plafond quotidien supprimé", AD, "budget = None if alias.open_senders else await _budget_left(db)", "budget = None", "check_engine", "S0"),
    # ── échecs nommés, tentatives bornées, récupération ──
    ("échec LLM jamais notifié", AD, 'if alias.frequency == "minute" and retryable and (email.attempts or 0) + 1 < settings.ALIAS_MAX_ATTEMPTS:', 'if alias.frequency == "minute" and retryable:', "check_engine", "S5"),
    ("tentatives non bornées", AD, 'email.status = "failed" if email.attempts >= settings.ALIAS_MAX_ATTEMPTS else "new"', 'email.status = "new"', "check_engine", "S6"),
    ("orphelins jamais récupérés", AD, 'Email.status == "processing", Email.claimed_at < _now() - STUCK_AFTER', 'Email.status == "sans-objet", Email.claimed_at < _now() - STUCK_AFTER', "check_engine", "S8"),
    ("récents volés", AD, "Email.claimed_at < _now() - STUCK_AFTER", "Email.claimed_at < _now() + STUCK_AFTER", "check_engine", "S8 : un `processing` récent|S4 : doublons"),   # selon le calage des runs, le vol rougit S4 (doublons) ou S8
    ("récupération sans compter la tentative", AD, 'e.attempts = (e.attempts or 0) + 1\n        e.claimed_at = None\n        e.last_error = "traitement', 'e.claimed_at = None\n        e.last_error = "traitement', "check_engine", "S8"),
    # ── routage ──
    ("plus-tag replié sur l'alias de base", A, "if lp in by_local:\n            return by_local[lp]", 'if lp in by_local:\n            return by_local[lp]\n        if lp.split("+")[0] in by_local:\n            return by_local[lp.split("+")[0]]', "check_alias_routing", "ne doit PAS retomber"),
    ("casse d'expéditeur non normalisée", A, 'addr = parseaddr(from_addr or "")[1].strip().lower()', 'addr = parseaddr(from_addr or "")[1].strip()', "check_alias_routing", "expéditeur autorisé"),
    ("liste vide = tout le monde", A, "return bool(sender) and sender in {normalize_sender(s) for s in (alias.allowed_senders or [])}", "return not alias.allowed_senders or (bool(sender) and sender in {normalize_sender(s) for s in (alias.allowed_senders or [])})", "check_alias_routing", "liste blanche vide"),
    ("From vide refusé à la réception", A, "if not sender_known and not normalize_sender(from_addr):\n        return True, \"\"", "pass", "check_alias_routing", "From vide"),
    ("alias désactivé accepté", A, "if not alias.enabled:\n        return False", "if False:\n        return False", "check_alias_routing", "désactivé"),
    # ── portée des prompts ──
    ("création désactive TOUS les prompts", P, "update(PromptVersion).where(_scope(alias_id)).values(is_active=False))\n    row = PromptVersion(", "update(PromptVersion).values(is_active=False))\n    row = PromptVersion(", "check_prompt_scope", "désactivé par un autre alias"),
    ("activation inter-alias permise", P, "select(PromptVersion).where(PromptVersion.id == version_id, _scope(alias_id))", "select(PromptVersion).where(PromptVersion.id == version_id)", "check_prompt_scope", "AUTRE alias"),
    ("API sans alias_id ≠ newsletter", P, "return alias_id if alias_id is not None else await default_alias_id(db)", "return alias_id", "check_prompt_scope", "désactivé par un autre alias"),   # None doit valoir « alias par défaut » : sinon la v4 part sur un alias NULL
    # ── migration ──
    ("mails non rattachés", A, "update(Email).where(Email.alias_id.is_(None))", "update(Email).where(Email.alias_id == -1)", "check_migration", "non rattachés"),
    ("colonne attempts non ajoutée", D, '    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0",\n', "", "check_migration", "colonne manquante"),
    # ── KB ──
    ("tag d'alias absent de la KB", K, '"tags": [f"alias:{alias}"] if alias else [],', '"tags": [],', "check_kb_alias", "tag d'alias absent"),
    # ── SSRF ──
    ("IP non publique acceptée", U, "return ipaddress.ip_address(ip_text.split(\"%\", 1)[0]).is_global", "return True", "check_urlfetch", "AURAIT DÛ"),
    ("redirections non revalidées", U, "await validate_url(current)\n            try:", "if _hop == 0:\n                await validate_url(current)\n            try:", "check_urlfetch", "SUIVIE"),
    ("ports internes autorisés", U, "ALLOWED_PORTS = {80, 443}", "ALLOWED_PORTS = {80, 443, 8000, 8443, 5432}", "check_urlfetch", "mauvaise raison"),
    ("lecture non plafonnée", U, "del buf[MAX_BYTES:]     # plafond STRICT même si un seul chunk le dépasse\n                            break", "pass", "check_urlfetch", "plafond de 2 Mo"),
    ("« lien + texte » pris pour un lien seul", U, "_BARE_URL = re.compile(r\"^<?(https?://[^\\s<>]+)>?$\", re.IGNORECASE)", "_BARE_URL = re.compile(r\"^<?(https?://[^\\s<>]+)>?\", re.IGNORECASE)", "check_urlfetch", "à tort reconnu"),
]


def run_check(check: str) -> tuple[int, str]:
    p = subprocess.run(["checks/run.sh", f"checks/{check}.py"], cwd=ROOT, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout + p.stderr


def main() -> int:
    flt = sys.argv[1] if len(sys.argv) > 1 else ""
    rows, ok = [], 0
    todo = [m for m in MUTATIONS if flt in m[0] or flt in m[4]]
    for name, rel, old, new, check, expect in todo:
        path = ROOT / rel
        original = path.read_text()
        assert original.count(old) == 1, f"mutation « {name} » : motif trouvé {original.count(old)}× dans {rel} (1 attendu) — mutation à mettre à jour"
        try:
            path.write_text(original.replace(old, new))
            code, out = run_check(check)
        finally:
            path.write_text(original)
        if code == 0:
            verdict = "FAUX-VERT (la garde n'est jamais atteinte)"
        elif any(alt in out for alt in expect.split("|")):   # « a|b » : l'une des deux raisons légitimes
            verdict, ok = "ROUGE-OK", ok + 1
        else:
            verdict = f"MAUVAIS-ROUGE (attendu « {expect} »)"
        last = next((l for l in reversed(out.splitlines()) if "Error" in l or l.startswith("OK")), "")[:110]
        rows.append((verdict, name, check, last))
        print(f"{verdict:8s} | {name:42s} | {check:20s} | {last}", flush=True)
    # Contrôle final : tout restauré, la suite complète repasse au vert.
    print(f"BILAN mutations : {ok}/{len(todo)} rouges pour la bonne raison")
    return 0 if ok == len(todo) else 1


sys.exit(main())
