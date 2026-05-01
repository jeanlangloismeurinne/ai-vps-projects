"""
PostgreSQL access layer via asyncpg.
Connection string from env: DATABASE_URL
Default for local dev: postgresql://bank:bank_secure_pwd@localhost:5432/db_bank
In Docker (Coolify): postgresql://bank:bank_secure_pwd@shared-postgres:5432/db_bank
"""
import asyncpg
import os
from typing import Optional

_pool: Optional[asyncpg.Pool] = None


def _dsn() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://bank:bank_secure_pwd@localhost:5432/db_bank",
    )


async def _init_conn(conn):
    import json as _json
    await conn.set_type_codec("jsonb", encoder=_json.dumps, decoder=_json.loads, schema="pg_catalog")
    await conn.set_type_codec("json", encoder=_json.dumps, decoder=_json.loads, schema="pg_catalog")


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(_dsn(), min_size=1, max_size=5, init=_init_conn)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# ── Deduplication ─────────────────────────────────────────────────────────────

async def get_existing_dedup_keys() -> set[str]:
    pool = await get_pool()
    rows = await pool.fetch("SELECT dedup_key FROM transactions")
    return {r["dedup_key"] for r in rows}


# ── Accounts ──────────────────────────────────────────────────────────────────

async def upsert_account(account_num: str, account_label: str):
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO accounts (account_num, account_label)
        VALUES ($1, $2)
        ON CONFLICT (account_num) DO UPDATE SET account_label = EXCLUDED.account_label
        """,
        account_num, account_label,
    )


# ── Transactions ──────────────────────────────────────────────────────────────

async def insert_transactions(rows: list[dict]) -> int:
    """Bulk insert, skipping duplicates. Returns number of rows actually inserted."""
    if not rows:
        return 0
    pool = await get_pool()

    inserted = 0
    async with pool.acquire() as conn:
        for row in rows:
            try:
                await conn.execute(
                    """
                    INSERT INTO transactions (
                        date_op, date_val, real_date,
                        label, label_clean, amount, currency,
                        account_num, account_balance,
                        bank_category, bank_category_parent, supplier, comment,
                        category, confidence, classification_method,
                        precision_note, source, dedup_key
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,
                        $14,$15,$16,$17,$18,$19
                    )
                    ON CONFLICT (dedup_key) DO NOTHING
                    """,
                    row["date_op"], row.get("date_val"), row.get("real_date"),
                    row["label"], row.get("label_clean"), row["amount"], row.get("currency", "EUR"),
                    row.get("account_num"), row.get("account_balance"),
                    row.get("bank_category"), row.get("bank_category_parent"),
                    row.get("supplier"), row.get("comment"),
                    row.get("category"), row.get("confidence"),
                    row.get("classification_method"),
                    row.get("precision_note"), row.get("source", "export"),
                    row["dedup_key"],
                )
                inserted += 1
            except asyncpg.ForeignKeyViolationError:
                # Category not in table yet — insert as non catégorisé
                row["category"] = "Non catégorisé"
                await conn.execute(
                    """
                    INSERT INTO transactions (
                        date_op, date_val, real_date,
                        label, label_clean, amount, currency,
                        account_num, account_balance,
                        bank_category, bank_category_parent, supplier, comment,
                        category, confidence, classification_method,
                        precision_note, source, dedup_key
                    ) VALUES (
                        $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,
                        $14,$15,$16,$17,$18,$19
                    )
                    ON CONFLICT (dedup_key) DO NOTHING
                    """,
                    row["date_op"], row.get("date_val"), row.get("real_date"),
                    row["label"], row.get("label_clean"), row["amount"], row.get("currency", "EUR"),
                    row.get("account_num"), row.get("account_balance"),
                    row.get("bank_category"), row.get("bank_category_parent"),
                    row.get("supplier"), row.get("comment"),
                    "Non catégorisé", row.get("confidence"),
                    row.get("classification_method"),
                    row.get("precision_note"), row.get("source", "export"),
                    row["dedup_key"],
                )
                inserted += 1
    return inserted


# ── Classification rules ──────────────────────────────────────────────────────

async def get_classification_rules() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, keyword, category, created_at FROM classification_rules ORDER BY created_at DESC"
    )
    return [dict(r) for r in rows]


async def create_classification_rule(keyword: str, category: str) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        "INSERT INTO classification_rules (keyword, category) VALUES ($1, $2) RETURNING id",
        keyword.strip(), category.strip(),
    )
    return row["id"]


async def delete_classification_rule(rule_id: int):
    pool = await get_pool()
    await pool.execute("DELETE FROM classification_rules WHERE id = $1", rule_id)


async def apply_rule_to_year(keyword: str, category: str, year_id: int) -> int:
    """Apply a keyword rule to all matching transactions in a given year. Returns count updated."""
    pool = await get_pool()
    result = await pool.execute(
        """
        UPDATE transactions t
        SET category = $1
        FROM budget_years y
        WHERE t.date_op BETWEEN y.start_date AND y.end_date
          AND y.id = $2
          AND strpos(UPPER(COALESCE(t.label_clean, t.label, '')), UPPER($3)) > 0
        """,
        category, year_id, keyword,
    )
    return int(result.split()[-1]) if result else 0


async def check_rule_conflict(keyword: str, category: str) -> dict | None:
    """Return the first rule whose keyword matches and points to a different category."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, keyword, category FROM classification_rules WHERE lower(keyword) = lower($1) AND lower(category) != lower($2) LIMIT 1",
        keyword.strip(), category.strip(),
    )
    return dict(row) if row else None


# ── Import sessions ───────────────────────────────────────────────────────────

async def create_import_session(
    filename: str | None,
    row_count: int,
    date_min,
    date_max,
    year_id: int | None,
) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO import_sessions (filename, row_count, date_min, date_max, year_id)
        VALUES ($1, $2, $3, $4, $5) RETURNING id
        """,
        filename, row_count, date_min, date_max, year_id,
    )
    return row["id"]


async def get_import_sessions(limit: int = 20) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT id, created_at, filename, row_count, date_min, date_max, year_id
        FROM import_sessions
        ORDER BY created_at DESC
        LIMIT $1
        """,
        limit,
    )
    result = []
    for r in rows:
        d = dict(r)
        d["created_at"] = d["created_at"].isoformat() if d["created_at"] else None
        d["date_min"] = str(d["date_min"]) if d["date_min"] else None
        d["date_max"] = str(d["date_max"]) if d["date_max"] else None
        result.append(d)
    return result


async def link_transactions_to_session(dedup_keys: list[str], session_id: int):
    if not dedup_keys:
        return
    pool = await get_pool()
    await pool.execute(
        "UPDATE transactions SET import_session_id = $1 WHERE dedup_key = ANY($2) AND import_session_id IS NULL",
        session_id, dedup_keys,
    )


async def get_session_with_transactions(session_id: int) -> tuple[dict | None, list[dict]]:
    pool = await get_pool()
    session = await pool.fetchrow(
        "SELECT id, created_at, filename, row_count, date_min, date_max, year_id FROM import_sessions WHERE id = $1",
        session_id,
    )
    if not session:
        return None, []
    session_dict = dict(session)
    session_dict["created_at"] = session_dict["created_at"].isoformat() if session_dict["created_at"] else None
    session_dict["date_min"] = str(session_dict["date_min"]) if session_dict["date_min"] else None
    session_dict["date_max"] = str(session_dict["date_max"]) if session_dict["date_max"] else None

    rows = await pool.fetch(
        """
        SELECT id, date_op, real_date, label, label_clean, amount,
               bank_category, category, confidence, classification_method, precision_note
        FROM transactions
        WHERE import_session_id = $1
        ORDER BY date_op DESC, id DESC
        """,
        session_id,
    )
    txs = []
    for r in rows:
        d = dict(r)
        d["date_op"] = str(d["date_op"])
        d["real_date"] = str(d["real_date"]) if d["real_date"] else None
        d["amount"] = float(d["amount"])
        txs.append(d)
    return session_dict, txs


# ── Classifier rules (new system) ────────────────────────────────────────────

_DEFAULT_STAGE0 = [
    {"stage": 0, "sort_order": 10, "keywords": ["URSSAF"],              "match_mode": "OR", "category": "Nounou",          "source": "system"},
    {"stage": 0, "sort_order": 20, "keywords": ["JUSTINIANO"],          "match_mode": "OR", "category": "Nounou",          "source": "system"},
]
_DEFAULT_STAGE3 = [
    {"stage": 3, "sort_order": 10,  "keywords": ["NAVIGO"],                                                                        "match_mode": "OR", "category": "Navigo",           "source": "system"},
    {"stage": 3, "sort_order": 20,  "keywords": ["RATP"],                                                                           "match_mode": "OR", "category": "Navigo",           "source": "system"},
    {"stage": 3, "sort_order": 30,  "keywords": ["SNCF"],                                                                           "match_mode": "OR", "category": "Transport",        "source": "system"},
    {"stage": 3, "sort_order": 40,  "keywords": ["BLABLACAR", "FLIXBUS"],                                                           "match_mode": "OR", "category": "Transport",        "source": "system"},
    {"stage": 3, "sort_order": 50,  "keywords": ["EDF", "ENGIE"],                                                                   "match_mode": "OR", "category": "Electricité",     "source": "system"},
    {"stage": 3, "sort_order": 60,  "keywords": ["FREE", "ORANGE", "SFR", "BOUYGUES"],                                              "match_mode": "OR", "category": "Box",             "source": "system"},
    {"stage": 3, "sort_order": 70,  "keywords": ["LOYER"],                                                                          "match_mode": "OR", "category": "Loyer",           "source": "system"},
    {"stage": 3, "sort_order": 80,  "keywords": ["SALAIRE", "PAIE"],                                                                "match_mode": "OR", "category": "Entrée mensuelle","source": "system"},
    {"stage": 3, "sort_order": 90,  "keywords": ["CAF"],                                                                            "match_mode": "OR", "category": "Entrée",          "source": "system"},
    {"stage": 3, "sort_order": 100, "keywords": ["IMPOT", "DGFIP", "FISC"],                                                        "match_mode": "OR", "category": "Impôts",          "source": "system"},
    {"stage": 3, "sort_order": 110, "keywords": ["SAS LORIN"],                                                                      "match_mode": "OR", "category": "Restaurant",      "source": "system"},
    {"stage": 3, "sort_order": 120, "keywords": ["VIREMENT AUTOMATIQUE JLM"],                                                       "match_mode": "OR", "category": "Entrée mensuelle","source": "system"},
    {"stage": 3, "sort_order": 130, "keywords": ["AMELI", "CPAM"],                                                                  "match_mode": "OR", "category": "Santé",           "source": "system"},
    {"stage": 3, "sort_order": 140, "keywords": ["AXA", "MAIF", "MACIF", "ALLIANZ", "GMF"],                                        "match_mode": "OR", "category": "Assurances",      "source": "system"},
    {"stage": 3, "sort_order": 150, "keywords": ["CRECHE", "NOUNOU", "BABY"],                                                       "match_mode": "OR", "category": "Crèche",          "source": "system"},
    {"stage": 3, "sort_order": 160, "keywords": ["PHARMACI"],                                                                       "match_mode": "OR", "category": "Pharmacie",       "source": "system"},
    {"stage": 3, "sort_order": 170, "keywords": ["MEDECIN", "DOCTEUR", "DR ", "CLINIQUE", "HOPITAL", "LABO", "CERBA"],              "match_mode": "OR", "category": "Santé",           "source": "system"},
    {"stage": 3, "sort_order": 180, "keywords": ["VINTED"],                                                                         "match_mode": "OR", "category": "Paul",            "source": "system"},
    {"stage": 3, "sort_order": 190, "keywords": ["AMAZON", "FNAC", "DECATHLON", "ZARA", "H&M"],                                    "match_mode": "OR", "category": "Loisirs",         "source": "system"},
    {"stage": 3, "sort_order": 200, "keywords": ["LECLERC", "CARREFOUR", "LIDL", "ALDI", "INTERMARCHE", "MONOPRIX", "FRANPRIX", "PRIMEUR", "MON.MARCHE"], "match_mode": "OR", "category": "Nourriture", "source": "system"},
    {"stage": 3, "sort_order": 210, "keywords": ["METAL"],                                                                          "match_mode": "OR", "category": "Entrée",          "source": "system"},
]


async def migrate_classifier_tables() -> None:
    """Idempotent startup migration: seed classifier_rules if empty."""
    pool = await get_pool()
    count = await pool.fetchval("SELECT COUNT(*) FROM classifier_rules")
    if count and count > 0:
        return

    async with pool.acquire() as conn:
        # Migrate existing user rules from classification_rules
        old_rules = await conn.fetch(
            "SELECT keyword, category, created_at FROM classification_rules ORDER BY created_at"
        )
        for i, r in enumerate(old_rules):
            await conn.execute(
                "INSERT INTO classifier_rules (stage, sort_order, keywords, match_mode, category, source) VALUES ($1,$2,$3,$4,$5,$6)",
                2, (i + 1) * 10, [r["keyword"]], "OR", r["category"], "user",
            )
        # Insert stage 0 defaults
        for r in _DEFAULT_STAGE0:
            await conn.execute(
                "INSERT INTO classifier_rules (stage, sort_order, keywords, match_mode, category, source) VALUES ($1,$2,$3,$4,$5,$6)",
                r["stage"], r["sort_order"], r["keywords"], r["match_mode"], r["category"], r["source"],
            )
        # Insert stage 3 defaults
        for r in _DEFAULT_STAGE3:
            await conn.execute(
                "INSERT INTO classifier_rules (stage, sort_order, keywords, match_mode, category, source) VALUES ($1,$2,$3,$4,$5,$6)",
                r["stage"], r["sort_order"], r["keywords"], r["match_mode"], r["category"], r["source"],
            )


async def get_classifier_rules_all() -> list[dict]:
    """Return all active classifier rules sorted by stage + sort_order (for classification)."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, stage, sort_order, keywords, match_mode, category, year_id, source, is_active FROM classifier_rules WHERE is_active = TRUE ORDER BY stage, sort_order, id"
    )
    return [
        {**dict(r), "keywords": list(r["keywords"])}
        for r in rows
    ]


async def get_classifier_rules_for_settings() -> list[dict]:
    """Return ALL classifier rules (incl. inactive) for the settings page."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, stage, sort_order, keywords, match_mode, category, year_id, source, is_active, created_at, updated_at FROM classifier_rules ORDER BY stage, sort_order, id"
    )
    result = []
    for r in rows:
        d = dict(r)
        d["keywords"] = list(d["keywords"])
        d["created_at"] = d["created_at"].isoformat() if d["created_at"] else None
        d["updated_at"] = d["updated_at"].isoformat() if d["updated_at"] else None
        result.append(d)
    return result


async def create_classifier_rule_new(
    stage: int,
    keywords: list[str],
    match_mode: str,
    category: str,
    source: str = "user",
    year_id: int | None = None,
) -> int:
    pool = await get_pool()
    max_row = await pool.fetchrow(
        "SELECT COALESCE(MAX(sort_order), 0) AS m FROM classifier_rules WHERE stage = $1", stage
    )
    sort_order = (max_row["m"] or 0) + 10
    row = await pool.fetchrow(
        "INSERT INTO classifier_rules (stage, sort_order, keywords, match_mode, category, year_id, source) VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id",
        stage, sort_order, keywords, match_mode, category.strip(), year_id, source,
    )
    return row["id"]


async def update_classifier_rule_fields(rule_id: int, fields: dict) -> None:
    pool = await get_pool()
    allowed = {"stage", "sort_order", "keywords", "match_mode", "category", "is_active", "year_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    parts, values = [], []
    for i, (col, val) in enumerate(updates.items(), start=1):
        parts.append(f"{col} = ${i}")
        values.append(val)
    values.append(rule_id)
    await pool.execute(
        f"UPDATE classifier_rules SET {', '.join(parts)}, updated_at = NOW() WHERE id = ${len(values)}",
        *values,
    )


async def delete_classifier_rule_new(rule_id: int) -> None:
    pool = await get_pool()
    await pool.execute("DELETE FROM classifier_rules WHERE id = $1", rule_id)


async def reorder_classifier_rules(items: list[dict]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        for item in items:
            await conn.execute(
                "UPDATE classifier_rules SET stage = $1, sort_order = $2, updated_at = NOW() WHERE id = $3",
                item["stage"], item["sort_order"], item["id"],
            )


async def apply_classifier_rule_to_year(rule_id: int, year_id: int) -> int:
    pool = await get_pool()
    rule = await pool.fetchrow(
        "SELECT keywords, match_mode, category FROM classifier_rules WHERE id = $1", rule_id
    )
    if not rule:
        return 0
    keywords = list(rule["keywords"])
    if not keywords:
        return 0
    category = rule["category"]
    match_mode = rule["match_mode"] or "OR"
    kw_upper = [k.upper() for k in keywords]
    label_expr = "UPPER(COALESCE(t.label_clean, t.label, ''))"
    conditions = [f"strpos({label_expr}, ${i+3}) > 0" for i in range(len(kw_upper))]
    joiner = " AND " if match_mode == "AND" else " OR "
    where_clause = f"({joiner.join(conditions)})"
    params = [category, year_id] + kw_upper
    result = await pool.execute(
        f"UPDATE transactions t SET category = $1 FROM budget_years y WHERE t.date_op BETWEEN y.start_date AND y.end_date AND y.id = $2 AND {where_clause}",
        *params,
    )
    return int(result.split()[-1]) if result else 0


async def check_rule_conflict_new(keyword: str, category: str) -> dict | None:
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, keywords, category FROM classifier_rules
        WHERE EXISTS (SELECT 1 FROM jsonb_array_elements_text(keywords) k WHERE LOWER(k) = LOWER($1))
          AND LOWER(category) != LOWER($2) AND is_active = TRUE
        LIMIT 1
        """,
        keyword.strip(), category.strip(),
    )
    if not row:
        return None
    return {"id": row["id"], "keyword": keyword, "keywords": list(row["keywords"]), "category": row["category"]}


# ── Classifier snapshots ──────────────────────────────────────────────────────

async def get_classifier_snapshots(limit: int = 30) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT id, year_id, label, created_at, jsonb_array_length(snapshot_data->'rules') AS rule_count FROM classifier_snapshots ORDER BY created_at DESC LIMIT $1",
        limit,
    )
    result = []
    for r in rows:
        d = dict(r)
        d["created_at"] = d["created_at"].isoformat() if d["created_at"] else None
        result.append(d)
    return result


async def create_classifier_snapshot(label: str, year_id: int | None = None) -> int:
    pool = await get_pool()
    rules = await get_classifier_rules_for_settings()
    snapshot_rules = [
        {"stage": r["stage"], "sort_order": r["sort_order"], "keywords": r["keywords"],
         "match_mode": r["match_mode"], "category": r["category"], "year_id": r["year_id"],
         "source": r["source"], "is_active": r["is_active"]}
        for r in rules
    ]
    row = await pool.fetchrow(
        "INSERT INTO classifier_snapshots (year_id, snapshot_data, label) VALUES ($1, $2, $3) RETURNING id",
        year_id, {"rules": snapshot_rules}, label,
    )
    return row["id"]


async def restore_classifier_snapshot(snapshot_id: int) -> None:
    pool = await get_pool()
    snap = await pool.fetchrow("SELECT snapshot_data FROM classifier_snapshots WHERE id = $1", snapshot_id)
    if not snap:
        raise ValueError(f"Snapshot {snapshot_id} not found")
    data = snap["snapshot_data"]
    rules = data.get("rules", []) if isinstance(data, dict) else []
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM classifier_rules")
        for r in rules:
            await conn.execute(
                "INSERT INTO classifier_rules (stage, sort_order, keywords, match_mode, category, year_id, source, is_active) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)",
                r["stage"], r["sort_order"], r["keywords"], r["match_mode"],
                r["category"], r.get("year_id"), r.get("source", "user"), r.get("is_active", True),
            )


# ── History for classifier ────────────────────────────────────────────────────

async def get_classified_history(limit: int = 500) -> list[dict]:
    """Return recent classified transactions for building the history index."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT label_clean, label, category
        FROM transactions
        WHERE category IS NOT NULL
          AND source IN ('historical', 'export')
        ORDER BY date_op DESC
        LIMIT $1
        """,
        limit,
    )
    return [dict(r) for r in rows]
