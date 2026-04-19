import re
import json
import pandas as pd
from datetime import date
from dataclasses import dataclass
from typing import Optional
from collections import defaultdict

import anthropic
import os

MODEL = "claude-haiku-4-5-20251001"

# ── Category mapping: bank category → user category ──────────────────────────

BANK_TO_USER: dict[str, tuple[str, int]] = {
    "alimentation":                               ("Nourriture",   80),
    "restaurants, bars, discothèques":            ("Restaurant",   85),
    "pharmacie et laboratoire":                   ("Pharmacie",    90),
    "transports quotidiens (métro, bus":          ("Navigo",       85),
    "transports longue distance (avions, trains": ("Transport",    80),
    "médecins et frais médicaux":                 ("Santé",        85),
    "complémentaires santé":                      ("Assurances",   80),
    "remboursements frais de santé":              ("Santé",        75),
    "energie (électricité, gaz, fuel":            ("Electricité",  90),
    "téléphonie (fixe et mobile)":                ("Box",          80),
    "crèche, nounou, babysitter":                 ("Crèche",       95),
    "dons et cadeaux":                            ("Cadeaux",      80),
    "livres, cd/dvd, bijoux, jouets":             ("Culture",      75),
    "parking":                                    ("Voiture",      85),
    "péages":                                     ("Voiture",      90),
    "carburant":                                  ("Voiture",      90),
    "auto / moto":                                ("Voiture",      80),
    "assurances (auto/moto)":                     ("Assurances",   90),
    "virements reçus de comptes à comptes":       ("Entrée",       70),
    "virements reçus":                            ("Entrée mensuelle", 70),
    "mobilier, électroménager, décoration":       ("Appartement",  70),
    "abonnements & téléphonie":                   ("Box",          75),
    "journaux, magazines":                        ("Culture",      80),
    "retraits cash":                              ("Espèces",      95),
    "chèques":                                    ("Espèces",      80),
}

# ── Keyword rules on label ────────────────────────────────────────────────────

LABEL_RULES: list[tuple[str, str, int]] = [
    (r"\bNAVIGO\b",                                                                    "Navigo",          95),
    (r"\bRATP\b",                                                                       "Navigo",          95),
    (r"\bSNCF\b",                                                                       "Transport",       95),
    (r"\bBLABLACar\b|\bFLIXBUS\b",                                                     "Transport",       90),
    (r"\bEDF\b|\bENGIE\b",                                                              "Electricité",     95),
    (r"\bFREE\b|\bORANGE\b|\bSFR\b|\bBOUYGUES\b",                                     "Box",             90),
    (r"\bLOYER\b",                                                                      "Loyer",           95),
    (r"\bSALAIRE\b|\bPAIE\b",                                                          "Entrée mensuelle",90),
    (r"\bCAF\b",                                                                        "Entrée",          90),
    (r"\bIMPOT\b|\bDGFIP\b|\bFISC\b|\bURSSAF\b",                                      "Impôts",          95),
    (r"\bAMELI\b|\bCPAM\b",                                                            "Santé",           90),
    (r"\bAXA\b|\bMAIF\b|\bMACIF\b|\bALLIANZ\b|\bGMF\b",                              "Assurances",      90),
    (r"\bCRECHE\b|\bNOUNOU\b|\bBABY\b",                                                "Crèche",          90),
    (r"\bPHARMACI\w*",                                                                  "Pharmacie",       90),
    (r"\bMEDECIN\b|\bDOCTEUR\b|\bDR \b|\bCLINIQUE\b|\bHOPITAL\b|\bLABO\b|\bCERBA\b","Santé",           85),
    (r"\bVINTED\b",                                                                     "Paul",            70),
    (r"\bAMAZON\b|\bFNAC\b|\bDECATHLON\b|\bZARA\b|\bH&M\b",                          "Loisirs",         65),
    (r"\bLECLERC\b|\bCAREFOUR\b|\bLIDL\b|\bALDI\b|\bINTERMARCHE\b|\bMONOPRIX\b|\bFRANCHIPRIX\b|\bPRIMEUR\b", "Nourriture", 85),
]

# Bank categories whose value is too generic to be useful for Claude
_UNINFORMATIVE_BANK_CATS = {
    "non catégorisé", "virements émis", "virements reçus",
    "remboursements", "remboursement de frais / offres boursobank",
}

# Prefixes to strip from labels before sending to Claude
_LABEL_STRIP_RE = re.compile(
    r"^(CARTE\s+\d{2}/\d{2}/\d{2,4}\s+|PRLV\s+SEPA\s+|VIR\s+INST\s+|VIR\s+RECU\s+|VIR\s+|TDF\s+EMIS\s+VIA\s+CB\s+\d{2}/\d{2}/\d{2}\s+)",
    re.IGNORECASE,
)
_CB_SUFFIX_RE = re.compile(r"\s+CB\*\w+$", re.IGNORECASE)
_PIPE_RE = re.compile(r"^[^|]+\|\s*")  # "Foo | BAR" → keep BAR


def clean_label_for_claude(label: str) -> str:
    """Strip banking boilerplate, keep only the meaningful merchant name."""
    val = str(label).strip()
    # Use canonical part after pipe if present
    if "|" in val:
        val = val.split("|", 1)[1].strip()
    val = _CB_SUFFIX_RE.sub("", val)
    val = _LABEL_STRIP_RE.sub("", val)
    return val.strip()[:40]


# ── Date extraction from label ────────────────────────────────────────────────

_DATE_IN_LABEL_RE = re.compile(r"\bCARTE\s+(\d{2})/(\d{2})/(\d{2,4})\b", re.IGNORECASE)


def extract_real_date(label: str) -> Optional[date]:
    m = _DATE_IN_LABEL_RE.search(str(label))
    if not m:
        return None
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ClassificationResult:
    category: str
    confidence: int       # 0–100
    method: str           # "vacation" | "label_rule" | "bank_mapping" | "claude"
    real_date: Optional[str] = None


# ── History index builder ─────────────────────────────────────────────────────

def build_history_index(df_history: pd.DataFrame, examples_per_cat: int = 6) -> str:
    """
    Build a compact per-category example list from historical data.
    Replaces a raw 150-row CSV (~2000 tokens) with ~400 tokens of dense context.
    """
    df = df_history[["LIBELLE", "Catégorie"]].dropna()
    by_cat: dict[str, list[str]] = defaultdict(list)
    seen: set[str] = set()

    for _, row in df.iterrows():
        cat = str(row["Catégorie"]).strip()
        merchant = clean_label_for_claude(str(row["LIBELLE"]))
        if merchant and len(merchant) > 2 and merchant not in seen:
            seen.add(merchant)
            by_cat[cat].append(merchant)

    lines = []
    for cat, merchants in sorted(by_cat.items()):
        sample = merchants[-examples_per_cat:]   # most recent examples
        lines.append(f"{cat}: {', '.join(sample)}")
    return "\n".join(lines)


# ── Main classifier ───────────────────────────────────────────────────────────

class TransactionClassifier:

    def __init__(self, vacation_periods: list[tuple[date, date]] | None = None):
        self.vacation_periods: list[tuple[date, date]] = vacation_periods or []
        self._claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self._history_index: str = ""

    def set_history_sample(self, df_history: pd.DataFrame, n: int = 150):
        self._history_index = build_history_index(df_history)

    def set_history_from_db(self, rows: list[dict]):
        """Build history index from DB rows (label_clean + category)."""
        from collections import defaultdict
        by_cat: dict[str, list[str]] = defaultdict(list)
        seen: set[str] = set()
        for r in rows:
            cat = str(r.get("category") or "").strip()
            merchant = str(r.get("label_clean") or clean_label_for_claude(r.get("label", "")))
            if cat and merchant and merchant not in seen:
                seen.add(merchant)
                by_cat[cat].append(merchant)
        lines = []
        for cat, merchants in sorted(by_cat.items()):
            lines.append(f"{cat}: {', '.join(merchants[-6:])}")
        self._history_index = "\n".join(lines)

    def _is_vacation(self, label: str, date_op: str) -> tuple[bool, Optional[str]]:
        real = extract_real_date(label)
        check_date = real or _parse_date(date_op)
        if check_date is None:
            return False, None
        for start, end in self.vacation_periods:
            if start <= check_date <= end:
                return True, str(real) if real else None
        return False, None

    def classify_one(self, label: str, date_op: str, bank_category: str) -> ClassificationResult:
        label_up = str(label).upper()

        # 1. Vacation period
        in_vacation, real_date = self._is_vacation(label, date_op)
        if in_vacation:
            return ClassificationResult("Vacances", 95, "vacation", real_date)

        # 2. Label keyword rules
        for pattern, cat, conf in LABEL_RULES:
            if re.search(pattern, label_up):
                return ClassificationResult(cat, conf, "label_rule", None)

        # 3. Bank category mapping
        bank_low = str(bank_category).lower()
        for key, (cat, conf) in BANK_TO_USER.items():
            if key in bank_low:
                return ClassificationResult(cat, conf, "bank_mapping", None)

        return ClassificationResult("?", 0, "pending", None)

    async def classify_batch_with_claude(
        self, rows: list[dict], user_categories: list[str]
    ) -> list[ClassificationResult]:
        """
        One Claude call for all pending rows.
        Static context (categories + history) is marked for prompt caching.
        Per-line format: "N. MERCHANT_NAME[ | bank_hint]"
        """
        cats_str = ", ".join(user_categories)

        static_block = (
            f"Catégories disponibles : {cats_str}\n\n"
            f"Exemples historiques (catégorie: marchands typiques) :\n{self._history_index}"
        )

        lines = []
        for i, r in enumerate(rows):
            merchant = clean_label_for_claude(r["label"])
            bank_cat = r["bank_cat"].strip()
            hint = "" if bank_cat.lower() in _UNINFORMATIVE_BANK_CATS else f" | {bank_cat}"
            lines.append(f"{i+1}. {merchant}{hint}")

        transactions_block = (
            "Classifie chaque transaction. Réponds UNIQUEMENT avec un JSON array :\n"
            "[{\"c\":\"catégorie\",\"p\":0-100}, ...]\n\n"
            + "\n".join(lines)
        )

        msg = self._claude.messages.create(
            model=MODEL,
            max_tokens=512,
            system="Tu classifies des dépenses bancaires. Réponds uniquement en JSON.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": static_block,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": transactions_block,
                        },
                    ],
                }
            ],
        )

        raw = msg.content[0].text.strip()
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return [ClassificationResult("Non catégorisé", 30, "claude") for _ in rows]

        results_raw = json.loads(match.group())
        out = []
        for r in results_raw:
            cat = r.get("c") or r.get("category", "Non catégorisé")
            conf = min(100, max(0, int(r.get("p") or r.get("confidence", 50))))
            out.append(ClassificationResult(cat, conf, "claude"))
        return out


def _parse_date(val) -> Optional[date]:
    try:
        return pd.to_datetime(str(val)).date()
    except Exception:
        return None
