import pandas as pd
import io
from typing import Optional


def parse_upload(filename: str, content: bytes) -> tuple[pd.DataFrame, list[str]]:
    """Parse Excel or CSV file, return (dataframe, warnings)."""
    warnings = []
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext in ("xlsx", "xls"):
        df = pd.read_excel(io.BytesIO(content), dtype=str)
    elif ext == "csv":
        # Try common separators
        for sep in (",", ";", "\t"):
            try:
                df = pd.read_csv(io.BytesIO(content), sep=sep, dtype=str)
                if df.shape[1] > 1:
                    break
            except Exception:
                continue
        else:
            df = pd.read_csv(io.BytesIO(content), dtype=str)
    else:
        raise ValueError(f"Format non supporté : .{ext}")

    df = df.dropna(how="all").reset_index(drop=True)

    if df.empty:
        warnings.append("Le fichier ne contient aucune donnée.")

    return df, warnings


def df_to_preview(df: pd.DataFrame, max_rows: int = 100) -> dict:
    """Convert dataframe to a JSON-serializable preview dict."""
    truncated = len(df) > max_rows
    preview_df = df.head(max_rows)
    return {
        "columns": list(preview_df.columns),
        "rows": preview_df.fillna("").values.tolist(),
        "total_rows": len(df),
        "truncated": truncated,
    }
