"""
Format checker for imported CSV files.

Validates against the canonical BoursoBank export format.
If the format differs, attempts column mapping and reports:
- Which columns were remapped
- The header line number (for audit / rollback reference)
"""
import re
import io
from dataclasses import dataclass, field

# ── Canonical format ──────────────────────────────────────────────────────────

# Columns required to process a row
REQUIRED_COLS = {"dateOp", "label", "amount"}

# All expected columns with descriptions
EXPECTED_COLS: dict[str, str] = {
    "dateOp":          "date de l'opération",
    "dateVal":         "date de valeur",
    "label":           "libellé",
    "category":        "catégorie banque",
    "categoryParent":  "catégorie parente",
    "supplierFound":   "marchand identifié",
    "amount":          "montant",
    "comment":         "commentaire",
    "accountNum":      "numéro de compte",
    "accountLabel":    "libellé du compte",
    "accountbalance":  "solde du compte",
}

# Synonym map: lowercase aliases → canonical column name
_SYNONYMS: dict[str, str] = {
    # dateOp
    "dateop": "dateOp", "date_op": "dateOp", "date operation": "dateOp",
    "date opération": "dateOp", "date": "dateOp", "dateoperation": "dateOp",
    "operation date": "dateOp",
    # dateVal
    "dateval": "dateVal", "date_val": "dateVal", "date valeur": "dateVal",
    "value date": "dateVal",
    # label
    "label": "label", "libelle": "label", "libellé": "label",
    "description": "label", "wording": "label", "transaction": "label",
    # category
    "category": "category", "catégorie": "category", "categorie": "category",
    "cat": "category",
    # categoryParent
    "categoryparent": "categoryParent", "category_parent": "categoryParent",
    "catégorie parente": "categoryParent",
    # supplierFound
    "supplierfound": "supplierFound", "supplier": "supplierFound",
    "marchand": "supplierFound", "merchant": "supplierFound",
    # amount
    "amount": "amount", "montant": "amount", "somme": "amount",
    "debit credit": "amount", "débit": "amount",
    # comment
    "comment": "comment", "commentaire": "comment", "note": "comment",
    "memo": "comment",
    # accountNum
    "accountnum": "accountNum", "account_num": "accountNum",
    "numéro de compte": "accountNum", "numero compte": "accountNum",
    "account number": "accountNum", "iban": "accountNum",
    # accountLabel
    "accountlabel": "accountLabel", "account_label": "accountLabel",
    "libellé compte": "accountLabel", "account name": "accountLabel",
    # accountbalance
    "accountbalance": "accountbalance", "account_balance": "accountbalance",
    "solde": "accountbalance", "balance": "accountbalance",
    "solde compte": "accountbalance",
}


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class FormatCheckResult:
    is_exact_match: bool
    separator: str
    header_line: int              # 1-indexed line number of the header row
    column_mapping: dict[str, str]  # canonical_col → found_col (identity if exact)
    missing_required: list[str]   # required columns not found/mapped
    missing_optional: list[str]   # optional columns not found/mapped
    extra_columns: list[str]      # columns in file with no canonical mapping
    warnings: list[str]
    can_proceed: bool             # True if all REQUIRED_COLS are mapped

    def summary(self) -> str:
        if self.is_exact_match:
            return "Format reconnu (correspondance exacte)."
        lines = [
            f"Format différent détecté — correspondance appliquée à partir de la ligne {self.header_line}.",
        ]
        remapped = {k: v for k, v in self.column_mapping.items() if k != v}
        if remapped:
            lines.append("Colonnes remappées :")
            for canon, found in remapped.items():
                lines.append(f"  « {found} » → « {canon} » ({EXPECTED_COLS.get(canon, '')})")
        if self.missing_optional:
            lines.append(f"Colonnes optionnelles absentes : {', '.join(self.missing_optional)}")
        if self.extra_columns:
            lines.append(f"Colonnes inconnues ignorées : {', '.join(self.extra_columns)}")
        if not self.can_proceed:
            lines.append(f"ERREUR — colonnes obligatoires introuvables : {', '.join(self.missing_required)}")
        return "\n".join(lines)


# ── Core check ────────────────────────────────────────────────────────────────

def check_format(content: bytes) -> FormatCheckResult:
    """
    Analyse raw CSV bytes, return a FormatCheckResult.
    Does not raise — caller decides what to do with can_proceed=False.
    """
    text = _decode(content)
    lines = text.splitlines()

    sep = _detect_separator(text)
    header_line, raw_cols = _find_header(lines, sep)
    col_mapping, missing_req, missing_opt, extra = _map_columns(raw_cols)

    is_exact = (
        raw_cols == list(EXPECTED_COLS.keys())
        and header_line == 1
    )

    warnings: list[str] = []
    if not is_exact and col_mapping:
        warnings.append(
            f"Le format du fichier a changé. "
            f"Correspondance automatique appliquée à partir de la ligne {header_line}."
        )

    return FormatCheckResult(
        is_exact_match=is_exact,
        separator=sep,
        header_line=header_line,
        column_mapping=col_mapping,
        missing_required=missing_req,
        missing_optional=missing_opt,
        extra_columns=extra,
        warnings=warnings,
        can_proceed=len(missing_req) == 0,
    )


def apply_mapping(content: bytes, result: FormatCheckResult) -> bytes:
    """
    Rewrite the CSV bytes so that column names match the canonical format.
    Skips pre-header lines, renames columns, drops unmapped extras.
    Returns new CSV bytes with ';' separator and canonical column order.
    """
    if result.is_exact_match:
        return content

    text = _decode(content)
    lines = text.splitlines()
    sep = result.separator

    # Reverse mapping: found_col → canonical_col
    reverse = {v: k for k, v in result.column_mapping.items()}

    # Parse data rows starting at header_line (1-indexed)
    raw_header = _split_row(lines[result.header_line - 1], sep)
    canonical_order = list(EXPECTED_COLS.keys())

    out_lines = [";".join(canonical_order)]
    for line in lines[result.header_line:]:  # data rows
        if not line.strip():
            continue
        cells = _split_row(line, sep)
        row_dict = dict(zip(raw_header, cells))
        out_row = []
        for canon_col in canonical_order:
            found_col = result.column_mapping.get(canon_col)
            out_row.append(row_dict.get(found_col, "") if found_col else "")
        out_lines.append(";".join(out_row))

    return "\n".join(out_lines).encode("utf-8")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _decode(content: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    return content.decode("latin-1", errors="replace")


def _detect_separator(text: str) -> str:
    first_line = text.splitlines()[0] if text else ""
    counts = {sep: first_line.count(sep) for sep in (";", ",", "\t")}
    return max(counts, key=counts.get)


def _find_header(lines: list[str], sep: str) -> tuple[int, list[str]]:
    """
    Find the header row: the first line that contains recognisable column names.
    Returns (1-indexed line number, list of column names).
    """
    for i, line in enumerate(lines[:20], start=1):
        cols = _split_row(line, sep)
        # A header row has mostly string values (no numbers in most cells)
        non_numeric = sum(1 for c in cols if c and not _looks_like_date_or_number(c))
        if non_numeric >= max(2, len(cols) // 2):
            return i, cols
    # Fallback: first line
    return 1, _split_row(lines[0], sep) if lines else []


def _split_row(line: str, sep: str) -> list[str]:
    """Split a CSV row, handling quoted fields."""
    import csv
    try:
        return next(csv.reader(io.StringIO(line), delimiter=sep))
    except StopIteration:
        return []


def _looks_like_date_or_number(val: str) -> bool:
    val = val.strip().strip('"')
    return bool(re.match(r"^\d[\d.,/-]*$", val))


def _map_columns(raw_cols: list[str]) -> tuple[dict, list[str], list[str], list[str]]:
    """
    Map raw column names to canonical names.
    Returns: (mapping, missing_required, missing_optional, extra)
    """
    mapping: dict[str, str] = {}   # canonical → found
    used: set[str] = set()

    for canon in EXPECTED_COLS:
        # 1. Exact match
        if canon in raw_cols:
            mapping[canon] = canon
            used.add(canon)
            continue
        # 2. Case-insensitive exact
        lower_map = {c.lower(): c for c in raw_cols}
        if canon.lower() in lower_map:
            mapping[canon] = lower_map[canon.lower()]
            used.add(lower_map[canon.lower()])
            continue
        # 3. Synonym lookup
        for raw in raw_cols:
            if raw in used:
                continue
            if _SYNONYMS.get(raw.lower().strip()) == canon:
                mapping[canon] = raw
                used.add(raw)
                break
        # 4. Substring fallback
        if canon not in mapping:
            for raw in raw_cols:
                if raw in used:
                    continue
                if canon.lower() in raw.lower() or raw.lower() in canon.lower():
                    mapping[canon] = raw
                    used.add(raw)
                    break

    missing_req = [c for c in REQUIRED_COLS if c not in mapping]
    missing_opt = [c for c in EXPECTED_COLS if c not in REQUIRED_COLS and c not in mapping]
    extra = [c for c in raw_cols if c not in used]

    return mapping, missing_req, missing_opt, extra
