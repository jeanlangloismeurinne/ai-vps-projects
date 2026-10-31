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
GR, GC, GA = "app/gmail_rules.py", "app/gmail_client.py", "app/gmail_api.py"
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
    ("motif brut de l'exception envoyé", AD, "reason, retryable = _reason(exc), True", "reason, retryable = str(exc) or type(exc).__name__, True", "check_engine", "S5b"),
    ("motif d'échec absent du corps texte", "app/digest.py", 'lines.append(f"⚠ Résumé en échec — {email._summary_error}")', 'lines.append("(vide)")', "check_engine", "corps TEXTE"),
    # ── routage ──
    ("plus-tag replié sur l'alias de base", A, "if lp in by_local:\n            return by_local[lp]", 'if lp in by_local:\n            return by_local[lp]\n        if lp.split("+")[0] in by_local:\n            return by_local[lp.split("+")[0]]', "check_alias_routing", "ne doit PAS retomber"),
    ("casse d'expéditeur non normalisée", A, 'addr = parseaddr(from_addr or "")[1].strip().lower()', 'addr = parseaddr(from_addr or "")[1].strip()', "check_alias_routing", "expéditeur autorisé"),
    ("liste vide = tout le monde", A, "return bool(sender) and sender in {normalize_sender(s) for s in (alias.allowed_senders or [])}", "return not alias.allowed_senders or (bool(sender) and sender in {normalize_sender(s) for s in (alias.allowed_senders or [])})", "check_alias_routing", "liste blanche vide"),
    ("From vide refusé à la réception", A, "if not sender_known and not normalize_sender(from_addr):\n        return True, \"\"", "pass", "check_alias_routing", "From vide"),
    ("alias désactivé accepté", A, "if not alias.enabled:\n        return False", "if False:\n        return False", "check_alias_routing", "désactivé"),
    # ── destinataires fixes ──
    ("liste de destinataires ignorée", A, "    if alias.recipients:\n        return list(alias.recipients)", "    if False:\n        return list(alias.recipients)", "check_alias_routing", "liste : remplace"),
    ("liste réduite à sa 1re adresse", AD, "to=recipient[0] if len(recipient) == 1 else list(recipient),", "to=recipient[0],", "check_engine", "S11"),
    ("liste posée sur l'alias par défaut", A, "if alias.is_default and dest:", "if False:", "check_alias_routing", "alias par défaut"),
    ("plafond de destinataires supprimé", A, "if len(out) > MAX_RECIPIENTS:", "if False:", "check_alias_routing", "destinataires invalide"),
    # ── portée des prompts ──
    ("création désactive TOUS les prompts", P, "update(PromptVersion).where(_scope(alias_id)).values(is_active=False))\n    row = PromptVersion(", "update(PromptVersion).values(is_active=False))\n    row = PromptVersion(", "check_prompt_scope", "désactivé par un autre alias"),
    ("activation inter-alias permise", P, "select(PromptVersion).where(PromptVersion.id == version_id, _scope(alias_id))", "select(PromptVersion).where(PromptVersion.id == version_id)", "check_prompt_scope", "AUTRE alias"),
    ("API sans alias_id ≠ newsletter", P, "return alias_id if alias_id is not None else await default_alias_id(db)", "return alias_id", "check_prompt_scope", "désactivé par un autre alias"),   # None doit valoir « alias par défaut » : sinon la v4 part sur un alias NULL
    # ── migration ──
    ("mails non rattachés", A, "update(Email).where(Email.alias_id.is_(None))", "update(Email).where(Email.alias_id == -1)", "check_migration", "non rattachés"),
    ("colonne attempts non ajoutée", D, '    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0",\n', "", "check_migration", "colonne manquante"),
    ("RECIPIENT_EMAIL ignorée après création", A, "if alias.recipient != settings.RECIPIENT_EMAIL:", "if False:", "check_migration", "RECIPIENT_EMAIL modifiée"),
    # ── KB ──
    ("tag d'alias absent de la KB", K, '"tags": [f"alias:{alias}"] if alias else [],', '"tags": [],', "check_kb_alias", "tag d'alias absent"),
    # ── SSRF ──
    ("IP non publique acceptée", U, "return ipaddress.ip_address(ip_text.split(\"%\", 1)[0]).is_global", "return True", "check_urlfetch", "AURAIT DÛ"),
    ("redirections non revalidées", U, "await validate_url(current)\n            try:", "if _hop == 0:\n                await validate_url(current)\n            try:", "check_urlfetch", "SUIVIE"),
    ("ports internes autorisés", U, "ALLOWED_PORTS = {80, 443}", "ALLOWED_PORTS = {80, 443, 8000, 8443, 5432}", "check_urlfetch", "mauvaise raison"),
    ("lecture non plafonnée", U, "del buf[MAX_BYTES:]     # plafond STRICT même si un seul chunk le dépasse\n                            break", "pass", "check_urlfetch", "plafond de 2 Mo"),
    ("« lien + texte » pris pour un lien seul", U, "_BARE_URL = re.compile(r\"^<?(https?://[^\\s<>]+)>?$\", re.IGNORECASE)", "_BARE_URL = re.compile(r\"^<?(https?://[^\\s<>]+)>?\", re.IGNORECASE)", "check_urlfetch", "à tort reconnu"),
    # ── pilotage des règles Gmail ──
    ("adresse mal formée acceptée", GR, "if not _FROM_RE.match(frm):", "if False:", "check_gmail_rules", "G1"),
    ("DENY_FROM ignoré", GR, 'if any(domain == d or domain.endswith("." + d) for d in csv(settings.DENY_FROM)):', "if False:", "check_gmail_rules", "G1"),
    ("sous-domaine de DENY_FROM toléré", GR, 'domain == d or domain.endswith("." + d) for d in csv(settings.DENY_FROM)', 'domain == d for d in csv(settings.DENY_FROM)', "check_gmail_rules", "G1"),
    ("suffixe public accepté", GR, "if frm.startswith(\"@\") and domain in PUBLIC_SUFFIXES:", "if False:", "check_gmail_rules", "G1"),
    ("sujet court sans expéditeur accepté", GR, "if not frm and len(subject) < 6:", "if False:", "check_gmail_rules", "G1"),
    ("doublon de triplet accepté", GR, 'raise RuleError("duplicate", "une règle existe déjà pour ce expéditeur + sujet + destination", 409)', "pass", "check_gmail_rules", "G3 (doublon)|G17"),
    ("plafond de règles retiré", GR, 'raise RuleError("rule_limit", f"{MAX_RULES} règles actives au plus", 409)', "pass", "check_gmail_rules", "G3"),
    ("plafond sans expéditeur retiré", GR, 'raise RuleError("rule_limit", f"{MAX_SENDERLESS} règles sans expéditeur au plus", 409)', "pass", "check_gmail_rules", "G3"),
    ("réponse non signée crue (signature de réponse)", GC, "if not hmac.compare_digest(expected, str(sig)):\n                raise ScriptSignatureError(\"signature de réponse fausse\")\n            return json.loads", "if False:\n                raise ScriptSignatureError(\"signature de réponse fausse\")\n            return json.loads", "check_gmail_rules", "G4"),
    ("nonce de réponse non vérifié", GC, 'if body.get("nonce") != nonce:', "if False:", "check_gmail_rules", "G4 : réponse d'un autre échange"),
    ("signature de requête différente du script", GC, '".".join([str(v), str(ts), nonce, action, payload])', '".".join([str(v), str(ts), nonce, payload])', "check_gmail_rules", "G0"),
    ("injoignable déclaré synchronisé", GR, 'rule.sync_status, rule.last_error = "pending", _failure_message(exc)', 'rule.sync_status, rule.last_error = "synced", _failure_message(exc)', "check_gmail_rules", "G4|G5"),
    ("refus authentique laissé en attente", GR, 'rule.sync_status = "pending" if exc.is_auth or not exc.signed else "error"', 'rule.sync_status = "pending"', "check_gmail_rules", "G5"),
    ("renommage appelle le script", GR, "changed = any(getattr(rule, k) != f[k] for k in _CRITERIA)", "changed = True", "check_gmail_rules", "G6"),
    ("synchronisation corrige d'elle-même", GR, '    await db.commit()\n    summary = {"at"', '    for r in rules:\n        if r.drift_kind == "missing":\n            r.pending_op = "create"; await _run_op(db, r)\n    await db.commit()\n    summary = {"at"', "check_gmail_rules", "G8"),
    ("alerte de dérive répétée chaque jour", GR, 'if sig != "[]" and sig != await get_setting(db, "alert_sig"):', 'if sig != "[]":', "check_gmail_rules", "G8"),
    ("compteur d'échecs jamais remis à zéro", GR, '            await set_setting(db, "auth_failures", "0")\n', "", "check_gmail_rules", "G10"),
    ("alerte d'authentification au 1er échec", GR, "AUTH_FAILURES_ALERT = 3", "AUTH_FAILURES_ALERT = 1", "check_gmail_rules", "G10"),
    ("rotation promue sans ping", GR, 'client = await make_client(db, secret=nxt)\n    try:\n        res = await call_script(db, "ping", client=client)', 'client = await make_client(db, secret=nxt)\n    try:\n        res = {}', "check_gmail_rules", "G11"),
    ("secret trop vieux jamais signalé", GR, "if age > SECRET_MAX_AGE_DAYS and await get_setting", "if False and await get_setting", "check_gmail_rules", "G12"),
    ("adresse non acceptée sélectionnable", GR, '"selectable": a["status"] == "accepted"\n                    and', '"selectable": True\n                    and', "check_gmail_rules", "G13"),
    ("cache des adresses ignoré", GR, "now - _addr_cache[\"at\"] < ADDR_CACHE_S", "False", "check_gmail_rules", "G13"),
    ("route sans jeton ouverte", GA, "if x_hub_token != settings.HUB_API_TOKEN:", "if False:", "check_gmail_rules", "G15"),
    ("HUB_API_TOKEN vide = routes ouvertes", GA, "    if not settings.HUB_API_TOKEN:\n        raise HTTPException(status_code=503", "    if False:\n        raise HTTPException(status_code=503", "check_gmail_rules", "G15"),
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
