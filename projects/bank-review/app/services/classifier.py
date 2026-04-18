import re
import json
import pandas as pd
from datetime import date, datetime
from dataclasses import dataclass, field
from typing import Optional

import anthropic
import os

# ── Category mapping: bank category → user category ──────────────────────────

BANK_TO_USER: dict[str, tuple[str, int]] = {
    # (user_category, confidence_pct)
    "alimentation":                                       ("Nourriture", 80),
    "restaurants, bars, discothèques":                    ("Restaurant", 85),
    "pharmacie et laboratoire":                           ("Pharmacie", 90),
    "transports quotidiens (métro, bus":                  ("Navigo",    85),
    "transports longue distance (avions, trains":         ("Transport", 80),
    "médecins et frais médicaux":                        ("Santé",     85),
    "complémentaires santé":                              ("Assurances",80),
    "remboursements frais de santé":                      ("Santé",     75),
    "energie (électricité, gaz, fuel":                    ("Electricité",90),
    "téléphonie (fixe et mobile)":                        ("Box",       80),
    "crèche, nounou, babysitter":                         ("Crèche",    95),
    "dons et cadeaux":                                    ("Cadeaux",   80),
    "livres, cd/dvd, bijoux, jouets":                     ("Culture",   75),
    "parking":                                            ("Voiture",   85),
    "péages":                                             ("Voiture",   90),
    "carburant":                                          ("Voiture",   90),
    "auto / moto":                                        ("Voiture",   80),
    "assurances (auto/moto)":                             ("Assurances",90),
    "virements reçus de comptes à comptes":               ("Entrée",    70),
    "virements reçus":                                    ("Entrée mensuelle", 70),
    "mobilier, électroménager, décoration":               ("Appartement",70),
    "abonnements & téléphonie":                           ("Box",       75),
    "journaux, magazines":                                ("Culture",   80),
    "retraits cash":                                      ("Espèces",   95),
    "chèques":                                            ("Espèces",   80),
}

# ── Keyword rules on label ────────────────────────────────────────────────────

LABEL_RULES: list[tuple[str, str, int]] = [
    # (regex_pattern, user_category, confidence)
    (r"\bNAVIGO\b",                     "Navigo",      95),
    (r"\bRATP\b",                        "Navigo",      95),
    (r"\bSNCF\b",                        "Transport",   95),
    (r"\bBLABLACar\b",                   "Transport",   90),
    (r"\bFLIXBUS\b",                     "Transport",   90),
    (r"\bEDF\b",                         "Electricité", 95),
    (r"\bENGIE\b",                       "Electricité", 95),
    (r"\bFREE\b|\bORANGE\b|\bSFR\b|\bBOUYGUES\b", "Box", 90),
    (r"\bLOYER\b",                       "Loyer",       95),
    (r"\bSALAIRE\b|\bPAIE\b",           "Entrée mensuelle", 90),
    (r"\bCAF\b",                         "Entrée",      90),
    (r"\bIMPOT\b|\bDGFIP\b|\bFISC",     "Impôts",      95),
    (r"\bAMELI\b|\bCPAM\b",             "Santé",       90),
    (r"\bAXA\b|\bMAIF\b|\bMACIF\b|\bALLIANZ\b|\bGMF\b", "Assurances", 90),
    (r"\bCRECHE\b|\bNOUNOU\b|\bBABY",   "Crèche",      90),
    (r"\bPHARMACI",                      "Pharmacie",   90),
    (r"\bMEDECIN\b|\bDOCTEUR\b|\bDR \b|\bCLINIQUE\b|\bHOPITAL\b|\bLABO", "Santé", 85),
    (r"\bVINTED\b",                      "Paul",        70),
    (r"\bAMAZON\b|\bFNAC\b|\bDECATHLON\b|\bZARA\b|\bH&M\b", "Loisirs", 65),
    (r"\bLECLERC\b|\bCAREFOUR\b|\bLIDL\b|\bALDI\b|\bINTERMARCHE\b|\bCORALIA\b|\bFRANCHIPRIX\b|\bMONOPRIX\b|\bPRIMEUR\b", "Nourriture", 85),
]


# ── Date extraction from label ────────────────────────────────────────────────

DATE_IN_LABEL_RE = re.compile(r"\bCARTE\s+(\d{2})/(\d{2})/(\d{2,4})\b", re.IGNORECASE)


def extract_real_date(label: str) -> Optional[date]:
    """Extract actual transaction date embedded in label (e.g. CARTE 29/08/25)."""
    m = DATE_IN_LABEL_RE.search(str(label))
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
    confidence: int          # 0-100
    method: str              # "vacation" | "label_rule" | "bank_mapping" | "claude" | "unclassified"
    real_date: Optional[str] = None   # extracted from label if found


# ── Main classifier ───────────────────────────────────────────────────────────

class TransactionClassifier:

    def __init__(self, vacation_periods: list[tuple[date, date]] | None = None):
        # list of (start_date, end_date) inclusive
        self.vacation_periods: list[tuple[date, date]] = vacation_periods or []
        self._claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self._history_sample: str = ""

    def set_history_sample(self, df_history: pd.DataFrame, n: int = 150):
        """Provide a sample of historical data for Claude context."""
        sample = df_history[["LIBELLE", "Catégorie"]].dropna().tail(n)
        self._history_sample = sample.to_csv(index=False)

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

        # 4. Claude fallback — handled separately (async batch)
        return ClassificationResult("?", 0, "pending", None)

    async def classify_batch_with_claude(
        self, rows: list[dict], user_categories: list[str]
    ) -> list[ClassificationResult]:
        """Classify pending rows via Claude (one API call for the batch)."""
        cats_str = ", ".join(user_categories)
        lines = "\n".join(
            f"{i+1}. label={r['label']} | bank_cat={r['bank_cat']} | amount={r['amount']}"
            for i, r in enumerate(rows)
        )
        prompt = f"""Tu dois classifier des transactions bancaires dans l'une des catégories suivantes :
{cats_str}

Historique de classification pour contexte :
{self._history_sample}

Transactions à classifier (réponds UNIQUEMENT avec un JSON array) :
{lines}

Format de réponse (JSON array, même ordre que les transactions) :
[{{"category": "...", "confidence": 0-100}}, ...]
"""
        msg = self._claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # Extract JSON array from response
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return [ClassificationResult("Non catégorisé", 30, "claude") for _ in rows]
        results_raw = json.loads(match.group())
        out = []
        for r in results_raw:
            cat = r.get("category", "Non catégorisé")
            conf = min(100, max(0, int(r.get("confidence", 50))))
            out.append(ClassificationResult(cat, conf, "claude"))
        return out


def _parse_date(val) -> Optional[date]:
    try:
        return pd.to_datetime(str(val)).date()
    except Exception:
        return None
