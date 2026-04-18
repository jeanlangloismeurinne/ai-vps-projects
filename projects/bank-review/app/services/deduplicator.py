import pandas as pd
import re


def normalize_amount(val) -> float:
    """Handle both comma and dot decimal separators."""
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    return round(float(str(val).replace("\u00a0", "").replace(" ", "").replace(",", ".")), 2)


def normalize_label(val: str) -> str:
    val = str(val).strip()
    # Export labels are duplicated: "Carte 28/09/25 Foo | CARTE 28/09/25 FOO CB*..."
    # Keep only the canonical uppercase part after the pipe if present
    if "|" in val:
        val = val.split("|", 1)[1].strip()
    val = val.upper()
    # Remove card suffix like CB*9402 and extra spaces
    val = re.sub(r"\s+CB\*\w+", "", val)
    val = re.sub(r"\s+", " ", val)
    return val


def build_historical_key(row) -> str:
    date = str(row.get("DATE OPERATION", ""))[:10]
    label = normalize_label(row.get("LIBELLE", ""))
    amount = normalize_amount(row.get("MONTANT", 0))
    return f"{date}|{label}|{amount}"


def build_export_key(row) -> str:
    date = str(row.get("dateOp", ""))[:10]
    label = normalize_label(row.get("label", ""))
    amount = normalize_amount(row.get("amount", 0))
    return f"{date}|{label}|{amount}"


def find_new_transactions(df_history: pd.DataFrame, df_export: pd.DataFrame) -> pd.DataFrame:
    """Return rows in df_export that are not already in df_history."""
    existing_keys = set(df_history.apply(build_historical_key, axis=1))
    mask = df_export.apply(lambda r: build_export_key(r) not in existing_keys, axis=1)
    return df_export[mask].reset_index(drop=True)
