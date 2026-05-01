"""
Import pipeline:
  1. Parse export CSV
  2. Deduplicate against PostgreSQL (via dedup_key)
  3. Classify (rules → Claude fallback)
  4. Return classified rows ready for review / DB insert
"""
import re
import pandas as pd
from datetime import date
from typing import Optional

from app.services.classifier import (
    TransactionClassifier, extract_real_date, clean_label_for_claude,
)
from app.services.database import get_existing_dedup_keys, get_classified_history, get_classifier_rules_all
from app.services.deduplicator import normalize_amount

USER_CATEGORIES = [
    "Nourriture", "Restaurant", "Vacances", "Transport", "Navigo", "Voiture",
    "Appartement", "Loyer", "Électricité", "Box", "Assurances",
    "Charges appartement", "Charges appartement exceptionnel",
    "Santé", "Pharmacie", "Crèche", "Loisirs", "Culture", "Cadeaux", "Dons",
    "Impôts", "Jean", "Amélie", "Paul", "Bébé",
    "Entrée mensuelle", "Entrée exceptionnelle", "Entrée",
    "Espèces", "Travaux", "Déménagement", "Notaire", "Taxe foncière",
    "Non catégorisé",
]

_PIPE_RE = re.compile(r"^[^|]+\|\s*")


def _canonical_label(raw: str) -> str:
    """Keep only the canonical (uppercase) part of a piped label."""
    raw = str(raw).strip()
    if "|" in raw:
        return raw.split("|", 1)[1].strip()
    return raw


def _build_dedup_key(date_op: str, label: str, amount: float) -> str:
    label_norm = label.upper().strip()
    label_norm = re.sub(r"\s+CB\*\w+", "", label_norm)
    label_norm = re.sub(r"\s+", " ", label_norm)
    return f"{str(date_op)[:10]}|{label_norm}|{amount}"


def _parse_date(val) -> Optional[date]:
    try:
        d = pd.to_datetime(str(val))
        return None if pd.isna(d) else d.date()
    except Exception:
        return None


def load_export_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", dtype=str)


async def run_import_pipeline(
    export_path: str,
    vacation_periods: list[tuple[date, date]] | None = None,
) -> list[dict]:
    """
    Returns classified rows (not yet persisted) ready for user review.
    """
    df_export = load_export_csv(export_path)

    # Fetch existing dedup keys from DB
    existing_keys = await get_existing_dedup_keys()

    # Build classifier with history + user rules from DB
    classifier = TransactionClassifier(vacation_periods=vacation_periods or [])
    history = await get_classified_history(500)
    classifier.set_history_from_db(history)
    rules = await get_classifier_rules_all()
    classifier.set_rules(rules)

    results: list[dict] = []
    pending_indices: list[int] = []

    for _, row in df_export.iterrows():
        raw_label = str(row.get("label", ""))
        label = _canonical_label(raw_label)
        label_clean = clean_label_for_claude(raw_label)
        date_op = str(row.get("dateOp", ""))
        bank_cat = str(row.get("category", ""))
        bank_cat_parent = str(row.get("categoryParent", "")) if pd.notna(row.get("categoryParent")) else None
        supplier = str(row.get("supplierFound", "")) if pd.notna(row.get("supplierFound")) else None
        account_num = str(row.get("accountNum", "")) if pd.notna(row.get("accountNum")) else None
        account_label = str(row.get("accountLabel", "")) if pd.notna(row.get("accountLabel")) else None
        comment = str(row.get("comment", "")) if pd.notna(row.get("comment")) else None

        try:
            amount = normalize_amount(row.get("amount", "0"))
        except Exception:
            amount = 0.0

        try:
            balance = float(str(row.get("accountbalance", "")).replace(",", "."))
        except Exception:
            balance = None

        dedup_key = _build_dedup_key(date_op, label, amount)
        if dedup_key in existing_keys:
            continue  # already in DB

        real_date = extract_real_date(raw_label)
        result = classifier.classify_one(raw_label, date_op, bank_cat)

        entry = {
            "date_op":               _parse_date(date_op),
            "date_val":              _parse_date(row.get("dateVal")),
            "real_date":             real_date,
            "label":                 label,
            "label_clean":           label_clean,
            "amount":                amount,
            "currency":              "EUR",
            "account_num":           account_num,
            "account_label":         account_label,
            "account_balance":       balance,
            "bank_category":         bank_cat,
            "bank_category_parent":  bank_cat_parent,
            "supplier":              supplier,
            "comment":               comment,
            "category":              result.category,
            "confidence":            result.confidence,
            "classification_method": result.method,
            "source":                "export",
            "dedup_key":             dedup_key,
            # UI-only fields (not stored)
            "_display_label":        raw_label,
        }
        results.append(entry)
        if result.method == "pending":
            pending_indices.append(len(results) - 1)

    # Claude batch for pending rows
    if pending_indices:
        pending_rows = [
            {
                "label":    results[j]["label"],
                "bank_cat": results[j]["bank_category"],
            }
            for j in pending_indices
        ]
        claude_results = await classifier.classify_batch_with_claude(pending_rows, USER_CATEGORIES)
        for j, cr in zip(pending_indices, claude_results):
            results[j]["category"] = cr.category
            results[j]["confidence"] = cr.confidence
            results[j]["classification_method"] = cr.method

    results.sort(key=lambda r: str(r["date_op"] or ""), reverse=True)
    return results
