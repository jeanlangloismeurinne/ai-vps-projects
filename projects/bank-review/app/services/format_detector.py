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


def _columns_with_samples(content: bytes, n_samples: int = 5) -> list[dict]:
    """Return per-column descriptors {index, header, samples} from CSV bytes.

    Sample VALUES are what lets the model disambiguate duplicate or misleading headers
    (e.g. a transaction amount and an account balance both labelled "Solde").
    """
    text = _decode(content)
    lines = text.splitlines()
    if not lines:
        return []
    sep = _detect_separator(text)
    header = [c.strip() for c in _split_row(lines[0], sep)]
    samples: dict[int, list[str]] = {i: [] for i in range(len(header))}
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = _split_row(line, sep)
        for i in range(len(header)):
            val = cells[i].strip() if i < len(cells) else ""
            if val and len(samples[i]) < n_samples:
                samples[i].append(val)
        if all(len(samples[i]) >= n_samples for i in range(len(header))):
            break
    return [{"index": i, "header": header[i], "samples": samples[i]} for i in range(len(header))]


async def detect_mapping_with_claude(content: bytes) -> dict:
    """Call Claude Haiku with columns (index + header + sample values) to map them by INDEX.

    Returns: {canonical_col: column_index, ...}
    Canonical cols: dateOp, label, amount, [amount_debit], [dateVal], [accountbalance],
    [accountNum], [accountLabel], [category], [supplierFound].
    If debit and credit are separate columns: amount → credit column index, amount_debit → debit index.

    The mapping is INDEX-based (not header-name-based) so that columns with identical or
    misleading headers can still be resolved — the model decides from the sample values.
    """
    from anthropic import AsyncAnthropic
    client = AsyncAnthropic()

    cols = _columns_with_samples(content)

    system = (
        "You map columns of a bank-export CSV to canonical fields, BY COLUMN INDEX. "
        "Canonical fields: "
        "dateOp (transaction date, required), "
        "label (operation description/wording, required), "
        "amount (SIGNED transaction amount, positive=credit / negative=debit; required), "
        "dateVal (value date, optional), "
        "accountbalance (running account balance after the operation, optional), "
        "accountNum (account number, optional), "
        "accountLabel (account name, optional), "
        "category (bank category, optional), "
        "supplierFound (cleaned merchant/supplier name, optional). "
        "Headers may be DUPLICATE or MISLEADING (e.g. two columns both named 'Solde'): "
        "decide from the SAMPLE VALUES, not the header text. The transaction amount varies "
        "in sign and magnitude across rows; the running balance is larger and drifts slowly. "
        "If debit and credit are SEPARATE columns, set amount to the credit column index and "
        "add amount_debit for the debit column index (both positive values in the CSV). "
        "Return ONLY a JSON object {field: column_index}. Omit optional fields not present."
    )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": "Columns: " + json.dumps(cols, ensure_ascii=False)}],
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


def _cell_at(cells: list[str], idx) -> str:
    """Read a cell by column index, tolerating None / out-of-range."""
    if idx is None:
        return ""
    try:
        i = int(idx)
    except (TypeError, ValueError):
        return ""
    return cells[i] if 0 <= i < len(cells) else ""


def apply_bank_format_mapping(content: bytes, headers: list[str], mapping: dict) -> bytes:
    """
    Rewrite CSV bytes using a stored bank mapping to produce canonical CSV.

    mapping is INDEX-based, e.g.:
      {"dateOp": 0, "label": 2, "amount": 6, "accountbalance": 10}
      {"dateOp": 0, "label": 2, "amount": 5, "amount_debit": 6}   # separate debit/credit

    Reading cells by COLUMN INDEX (not by header name) is what lets columns with identical or
    misleading headers be resolved. Handles debit/credit split: if amount_debit is present,
    amount = credit - debit (both columns contain positive values in the source file).
    """
    text = _decode(content)
    lines = text.splitlines()
    sep = _detect_separator(text)

    # Locate the header row by matching the stored headers set, so any pre-header lines are skipped.
    target_set = set(h for h in headers if h)
    header_line_idx = 0
    for i, line in enumerate(lines[:20]):
        cols = [c.strip() for c in _split_row(line, sep)]
        if target_set and set(c for c in cols if c) == target_set:
            header_line_idx = i
            break

    amount_credit_idx = mapping.get("amount")
    amount_debit_idx = mapping.get("amount_debit")

    canonical_order = list(EXPECTED_COLS.keys())
    out_lines = [";".join(canonical_order)]

    for line in lines[header_line_idx + 1:]:
        if not line.strip():
            continue
        cells = _split_row(line, sep)

        out_row = []
        for canon_col in canonical_order:
            if canon_col == "amount" and amount_debit_idx is not None:
                # Combine separate debit/credit columns into a signed amount
                credit_raw = _cell_at(cells, amount_credit_idx).strip().replace(" ", "").replace(" ", "").replace(",", ".")
                debit_raw = _cell_at(cells, amount_debit_idx).strip().replace(" ", "").replace(" ", "").replace(",", ".")
                try:
                    credit = float(credit_raw) if credit_raw else 0.0
                    debit = float(debit_raw) if debit_raw else 0.0
                    signed = credit - debit
                    out_row.append(str(signed) if signed != 0 else "")
                except ValueError:
                    out_row.append("")
            else:
                out_row.append(_cell_at(cells, mapping.get(canon_col)))

        out_lines.append(";".join(out_row))

    return "\n".join(out_lines).encode("utf-8")
