"""
Multi-bank format detection.

1. Extract headers from CSV bytes
2. Match against bank_formats DB (exact header set)
3. If no match: call Claude Haiku with headers only (minimal tokens)
4. Apply stored/detected mapping to produce canonical CSV
5. Save new format to DB
"""
import io
import json
import csv
import re
from app.services.database import get_pool
from app.services.format_checker import EXPECTED_COLS, _decode, _detect_separator, _split_row


def extract_csv_headers(content: bytes) -> list[str]:
    """Return the header row column names from CSV bytes."""
    text = _decode(content)
    lines = text.splitlines()
    if not lines:
        return []
    sep = _detect_separator(text)
    # Find first line with mostly string values (the header row)
    for line in lines[:10]:
        cols = _split_row(line, sep)
        non_numeric = sum(
            1 for c in cols
            if c.strip() and not re.match(r"^\d[\d.,/-]*$", c.strip().strip('"'))
        )
        if non_numeric >= max(2, len(cols) // 2):
            return [c.strip() for c in cols]
    return [c.strip() for c in _split_row(lines[0], sep)]


async def find_format_by_headers(headers: list[str]) -> dict | None:
    """Return saved bank_format dict if exact header set found, else None."""
    from app.services.database import _dsn
    pool = await get_pool(db_url=_dsn())
    rows = await pool.fetch("SELECT id, bank_name, headers, column_mapping, file_type FROM bank_formats")
    target = set(h for h in headers if h)
    for row in rows:
        stored = set(row["headers"])
        if stored == target:
            return dict(row)
    return None


async def detect_mapping_with_claude(headers: list[str]) -> dict:
    """Call Claude Haiku with headers only to produce a column mapping dict.

    Returns: {canonical_col: original_col, ...}
    Canonical cols: dateOp, label, amount, [amount_debit], [dateVal], [accountbalance], [accountNum]
    If debit and credit are separate columns: amount → credit col, amount_debit → debit col.
    """
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic()

    system = (
        "You are a bank CSV column mapper. Given column headers from a bank export, "
        "return a JSON object mapping standard field names to the matching header. "
        "Standard fields: "
        "dateOp (transaction date, required), "
        "label (description/wording, required), "
        "amount (signed number, positive=credit, negative=debit; required), "
        "dateVal (value date, optional), "
        "accountbalance (account balance, optional), "
        "accountNum (account number, optional). "
        "If debit and credit are separate columns, set amount to the credit column "
        "and add amount_debit for the debit column (both expressed as positive values in the CSV). "
        "Omit optional fields if not present. Return ONLY valid JSON, no explanation."
    )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": f"Headers: {json.dumps(headers)}"}],
    )

    text = response.content[0].text.strip()
    # Strip markdown code fences if present
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            try:
                return json.loads(p)
            except Exception:
                continue
    return json.loads(text)


async def save_bank_format(bank_name: str, headers: list[str], mapping: dict, file_type: str = "csv") -> int:
    """Insert a new bank format in bank_formats. Returns the new id."""
    from app.services.database import _dsn
    pool = await get_pool(db_url=_dsn())
    row = await pool.fetchrow(
        "INSERT INTO bank_formats (bank_name, headers, column_mapping, file_type) VALUES ($1, $2, $3, $4) RETURNING id",
        bank_name, headers, mapping, file_type,
    )
    return row["id"]


async def get_all_bank_formats() -> list[dict]:
    from app.services.database import _dsn
    pool = await get_pool(db_url=_dsn())
    rows = await pool.fetch("SELECT id, bank_name, file_type, created_at FROM bank_formats ORDER BY bank_name")
    return [dict(r) for r in rows]


def apply_bank_format_mapping(content: bytes, headers: list[str], mapping: dict) -> bytes:
    """
    Rewrite CSV bytes using a stored bank mapping to produce canonical CSV.

    mapping example:
      {"dateOp": "Date", "label": "Libellé", "amount": "Crédit", "amount_debit": "Débit"}

    Handles debit/credit split: if amount_debit is present, amount = credit - debit
    (both columns contain positive values in the source file).
    """
    text = _decode(content)
    lines = text.splitlines()
    sep = _detect_separator(text)

    # Locate header row by matching the stored headers set
    target_set = set(h for h in headers if h)
    header_line_idx = 0
    for i, line in enumerate(lines[:20]):
        cols = [c.strip() for c in _split_row(line, sep)]
        if set(c for c in cols if c) == target_set:
            header_line_idx = i
            break

    raw_header = [c.strip() for c in _split_row(lines[header_line_idx], sep)]

    amount_credit_col = mapping.get("amount")
    amount_debit_col = mapping.get("amount_debit")

    canonical_order = list(EXPECTED_COLS.keys())
    out_lines = [";".join(canonical_order)]

    for line in lines[header_line_idx + 1:]:
        if not line.strip():
            continue
        cells = _split_row(line, sep)
        row_dict = {raw_header[i]: (cells[i] if i < len(cells) else "") for i in range(len(raw_header))}

        out_row = []
        for canon_col in canonical_order:
            if canon_col == "amount" and amount_debit_col:
                # Combine separate debit/credit columns into a signed amount
                credit_raw = row_dict.get(amount_credit_col or "", "").strip().replace(" ", "").replace(" ", "").replace(",", ".")
                debit_raw = row_dict.get(amount_debit_col, "").strip().replace(" ", "").replace(" ", "").replace(",", ".")
                try:
                    credit = float(credit_raw) if credit_raw else 0.0
                    debit = float(debit_raw) if debit_raw else 0.0
                    signed = credit - debit
                    out_row.append(str(signed) if signed != 0 else "")
                except ValueError:
                    out_row.append("")
            else:
                orig_col = mapping.get(canon_col)
                out_row.append(row_dict.get(orig_col, "") if orig_col else "")

        out_lines.append(";".join(out_row))

    return "\n".join(out_lines).encode("utf-8")
