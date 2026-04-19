"""
One-time migration: import 2025_comptes_raw_data.xlsx → PostgreSQL.
Run from project root: python scripts/migrate_historical.py
"""
import asyncio
import sys
import os
import re
from datetime import date

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database import get_pool, upsert_account, insert_transactions, close_pool
from app.services.classifier import clean_label_for_claude, extract_real_date
from app.services.deduplicator import normalize_amount

EXCEL_PATH = "uploads/2025_comptes_raw_data.xlsx"
ACCOUNT_NUM = "00040341880"
ACCOUNT_LABEL = "AMELIE et JEAN"


def build_dedup_key(date_op: str, label: str) -> str:
    label_norm = label.upper().strip()
    label_norm = re.sub(r"\s+CB\*\w+", "", label_norm)
    label_norm = re.sub(r"\s+", " ", label_norm)
    return f"{str(date_op)[:10]}|{label_norm}"


def parse_date(val) -> date | None:
    try:
        d = pd.to_datetime(str(val))
        if pd.isna(d):
            return None
        return d.date()
    except Exception:
        return None


async def migrate():
    print(f"Loading {EXCEL_PATH}…")
    df = pd.read_excel(EXCEL_PATH, sheet_name="Export", dtype=str)
    df = df.dropna(subset=["DATE OPERATION", "LIBELLE", "MONTANT"]).reset_index(drop=True)
    print(f"  {len(df)} rows to migrate")

    await upsert_account(ACCOUNT_NUM, ACCOUNT_LABEL)

    rows = []
    skipped = 0
    for _, r in df.iterrows():
        label = str(r["LIBELLE"]).strip()
        date_op = parse_date(r["DATE OPERATION"])
        if date_op is None:
            skipped += 1
            continue

        try:
            amount = normalize_amount(r["MONTANT"])
        except Exception:
            skipped += 1
            continue

        # Build dedup key matching the same logic used for export CSVs
        dedup_key = build_dedup_key(str(date_op), label)

        # Amount is needed in the key for historical since labels aren't piped
        dedup_key = f"{dedup_key}|{amount}"

        rows.append({
            "date_op":               date_op,
            "date_val":              parse_date(r.get("DATE VALEUR")),
            "real_date":             extract_real_date(label),
            "label":                 label,
            "label_clean":           clean_label_for_claude(label),
            "amount":                amount,
            "currency":              str(r.get("DEVISE", "EUR")).strip() or "EUR",
            "account_num":           ACCOUNT_NUM,
            "account_balance":       None,
            "bank_category":         str(r["Tag #1"]) if pd.notna(r.get("Tag #1")) else None,
            "bank_category_parent":  None,
            "supplier":              None,
            "comment":               None,
            "category":              str(r["Catégorie"]).strip() if pd.notna(r.get("Catégorie")) else None,
            "confidence":            100,   # human-validated
            "classification_method": "manual",
            "precision_note":        str(r["Précision"]).strip() if pd.notna(r.get("Précision")) else None,
            "source":                "historical",
            "dedup_key":             dedup_key,
        })

    print(f"  {skipped} rows skipped (unparseable date/amount)")
    print(f"  Inserting {len(rows)} rows…")

    inserted = await insert_transactions(rows)
    print(f"  ✓ {inserted} rows inserted ({len(rows) - inserted} duplicates ignored)")

    pool = await get_pool()
    total = await pool.fetchval("SELECT count(*) FROM transactions")
    print(f"  Total in DB: {total}")

    await close_pool()


if __name__ == "__main__":
    asyncio.run(migrate())
