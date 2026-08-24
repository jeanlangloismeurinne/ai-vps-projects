"""
Bornes de sécurité du doc système de l'agent (roadmap §5.4, tickets #1787559677495 / #1787559677496
/ #1787559677497).

Ces contrôles s'appliquent à **tout** chemin d'écriture du doc système — proposition générée par
le modèle comme édition manuelle humaine. Une édition par un humain n'est pas une raison de
désactiver les contrôles : c'est le scénario où un contenu injecté depuis la queue de consignes
serait recopié sans relecture.

Le doc système est une consigne en **langage naturel**. Tout ce qui ressemble à du code, à une
commande, à un appel d'outil ou à une tentative de neutraliser la validation est refusé
automatiquement, sans passer par la revue humaine.
"""
import logging
import re
from dataclasses import dataclass, field

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GuardrailVerdict:
    ok: bool
    reasons: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return " · ".join(self.reasons) if self.reasons else "conforme"


# ── Motifs cherchant à neutraliser les garde-fous (§5.4) ──────────────────────
# Rédigés sans accents obligatoires : le texte est normalisé avant test.
_JAILBREAK_PATTERNS = [
    (r"ignore[rz]?\s+(les\s+|toutes\s+les\s+|vos\s+)?(instructions|consignes|regles)", "neutralisation des consignes"),
    (r"oublie[rz]?\s+(les\s+|toutes\s+les\s+|tes\s+)?(instructions|consignes|regles)", "neutralisation des consignes"),
    (r"ignore\s+(all\s+|previous\s+|prior\s+)+(instructions|rules|prompts)", "neutralisation des consignes (en)"),
    (r"disregard\s+(all\s+|previous\s+|the\s+)?(instructions|rules)", "neutralisation des consignes (en)"),
    (r"desactive[rz]?\s+(la\s+|les\s+)?(validation|verification|garde|controle|securite)", "desactivation de la validation"),
    (r"disable\s+(the\s+)?(validation|check|guardrail|safety)", "desactivation de la validation (en)"),
    (r"n['e]\s*exige\s+plus\s+(d[e']\s*)?approbation", "suppression de l'approbation"),
    (r"sans\s+approbation\s+humaine", "suppression de l'approbation"),
    (r"no\s+(longer\s+)?require[sd]?\s+approval", "suppression de l'approbation (en)"),
    (r"auto[-\s]?approuve", "auto-approbation"),
    (r"tu\s+es\s+maintenant\s+", "tentative de redefinition de role"),
    (r"you\s+are\s+now\s+", "tentative de redefinition de role (en)"),
    (r"developer\s+mode|mode\s+developpeur", "mode developpeur"),
    (r"execute[rz]?\s+(cette\s+|la\s+)?commande", "demande d'execution"),
    (r"\bsudo\b|\brm\s+-rf\b|\bcurl\b|\bwget\b|\bchmod\b", "commande shell"),
]

# ── Code / appels d'outil (§5.1 : la sortie doit etre du langage naturel) ─────
_CODE_PATTERNS = [
    (r"```", "bloc de code"),
    (r"<\s*script\b", "balise script"),
    (r"\b(?:def|class|import|from)\s+\w+.*:", "code Python"),
    (r"\b(?:function|const|let|var)\s+\w+\s*[=(]", "code JavaScript"),
    # `$(...)` uniquement. Les backticks simples ne sont PAS un signal : le doc système lui-même
    # cite `/feature` en Markdown inline, et les flaguer rejetait toute proposition qui préserve
    # le texte d'origine — un garde-fou qui bloque le cas nominal ne protège de rien.
    # Les blocs de code, eux, restent couverts par la règle ``` ci-dessus.
    (r"\$\(", "substitution shell"),
    (r"\b(?:SELECT|INSERT|UPDATE|DELETE|DROP)\b\s+.*\b(?:FROM|INTO|TABLE|SET)\b", "requete SQL"),
    (r"<\s*tool_call|<\s*function_call|\btool_use\b", "appel d'outil"),
]

# ── Secrets / exfiltration (§5.4) ─────────────────────────────────────────────
_SECRET_PATTERNS = [
    (r"\bxox[baprs]-[A-Za-z0-9-]{10,}", "token Slack"),
    (r"\bsk-[A-Za-z0-9]{20,}", "cle API"),
    (r"\bghp_[A-Za-z0-9]{20,}", "token GitHub"),
    (r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b", "cle AWS"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "cle privee"),
    (r"\b(?:api[_-]?key|password|passwd|secret|token|credential)s?\s*[:=]\s*\S{6,}", "credential en clair"),
    (r"postgresql://[^\s]*:[^\s]*@", "URL de base avec mot de passe"),
]

_URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)

# Le doc système peut légitimement citer les domaines du projet.
_URL_ALLOWLIST = {"jlmvpscode.duckdns.org", "slack.com", "api.slack.com"}


def _normalize(text: str) -> str:
    """Minuscules + accents retirés : les motifs restent lisibles sans multiplier les variantes."""
    import unicodedata

    lowered = (text or "").lower()
    stripped = unicodedata.normalize("NFKD", lowered)
    return "".join(c for c in stripped if not unicodedata.combining(c))


def _check_urls(text: str) -> list[str]:
    reasons = []
    for url in _URL_RE.findall(text or ""):
        host = re.sub(r"^https?://", "", url, flags=re.IGNORECASE).split("/")[0].split(":")[0].lower()
        if not any(host == allowed or host.endswith("." + allowed) for allowed in _URL_ALLOWLIST):
            reasons.append(f"URL sortante non autorisee ({host})")
    return reasons


def check_document(proposed: str, current: str | None = None) -> GuardrailVerdict:
    """Valide un doc système candidat. `current` sert à mesurer l'ajout ; None = doc initial.

    Renvoie un verdict ; ne lève jamais. L'appelant décide (refus automatique + audit + alerte).
    """
    reasons: list[str] = []
    proposed = proposed or ""
    normalized = _normalize(proposed)

    # 1. Bornes de taille
    if len(proposed.strip()) == 0:
        reasons.append("proposition vide")
    if len(proposed) > settings.AGENT_DOC_MAX_CHARS:
        reasons.append(f"doc trop long ({len(proposed)} > {settings.AGENT_DOC_MAX_CHARS} caracteres)")
    added = len(proposed) - len(current or "")
    if added > settings.AGENT_DOC_MAX_ADDED_CHARS:
        reasons.append(f"ajout trop volumineux (+{added} > {settings.AGENT_DOC_MAX_ADDED_CHARS} caracteres)")

    # 2. Code / appels d'outil — la sortie doit rester du langage naturel
    for pattern, label in _CODE_PATTERNS:
        if re.search(pattern, proposed, re.IGNORECASE | re.MULTILINE):
            reasons.append(f"contenu executable detecte ({label})")

    # 3. Secrets
    for pattern, label in _SECRET_PATTERNS:
        if re.search(pattern, proposed, re.IGNORECASE):
            reasons.append(f"secret detecte ({label})")

    # 4. URLs sortantes
    reasons.extend(_check_urls(proposed))

    # 5. Neutralisation des garde-fous
    for pattern, label in _JAILBREAK_PATTERNS:
        if re.search(pattern, normalized, re.IGNORECASE):
            reasons.append(f"motif interdit ({label})")

    # Dédoublonnage en conservant l'ordre — un motif peut matcher plusieurs fois.
    seen = set()
    deduped = [r for r in reasons if not (r in seen or seen.add(r))]

    verdict = GuardrailVerdict(ok=not deduped, reasons=deduped)
    if not verdict.ok:
        logger.warning(f"agent_guardrails: proposition refusee — {verdict.summary()}")
    return verdict
