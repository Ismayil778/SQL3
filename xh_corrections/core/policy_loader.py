"""
Loads XMLI policy list and their full entry history from _1SENTRY.

Strategy: one single pass over _1SENTRY filtered by the small set of known
account IDs (B7, BA, 9U, AZ, 5F, 7W, 7X, A3). Result is grouped in Python
by policy sc_code. This is dramatically faster than N/500 batch queries with
OR-joins.
"""
import pyodbc
from typing import Callable, Optional


# Known account IDs for İpoteka sığortası (after LTRIM/RTRIM)
XMLI_ACCOUNT_IDS = ('B7', 'BA', '9U', 'AZ', '5F', '7W', '7X', 'A3')
_ACC_IN = ",".join(f"'{a}'" for a in XMLI_ACCOUNT_IDS)

# Service subconto codes to ignore
BATCH_CODES = {"FN", "0", "I"}


def load_all_policies(conn: pyodbc.Connection) -> list[dict]:
    """
    Returns list of {'policy_sc_code': str, 'policy_number': str}
    for all XMLI policies from SC14632.
    """
    sql = """
        SELECT LTRIM(RTRIM(ID))    AS policy_sc_code,
               LTRIM(RTRIM(DESCR)) AS policy_number
        FROM SC14632 (NOLOCK)
        WHERE DESCR LIKE 'XMLI%'
          AND LEN(LTRIM(RTRIM(DESCR))) > 0
        ORDER BY DESCR
    """
    cursor = conn.cursor()
    cursor.execute(sql)
    cols   = [c[0] for c in cursor.description]
    result = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()

    return [p for p in result if p["policy_sc_code"] not in BATCH_CODES]


def load_entries_for_policies(
    conn: pyodbc.Connection,
    policies: list[dict],
    report_date: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> dict[str, list[dict]]:
    """
    Single-pass load: filter _1SENTRY by known account IDs, group in Python.

    Returns dict: policy_sc_code -> list of entry rows (sorted by date).
    """
    policy_sc_set: set[str] = {p["policy_sc_code"] for p in policies}
    entries_by_policy: dict[str, list[dict]] = {sc: [] for sc in policy_sc_set}

    # Signal "query started" (1 of 1 step)
    if progress_callback:
        progress_callback(0, 1)

    # One query — filter by account IDs, no OR-join, no temp tables.
    # LTRIM/RTRIM on DTSC0/KTSC0 in SELECT (spec requirement).
    # ACCDTID/ACCKTID are stored cleanly in 1C (no padding needed in WHERE).
    sql = f"""
        SELECT
            LTRIM(RTRIM(e.ACCDTID)) AS dt_id,
            LTRIM(RTRIM(e.ACCKTID)) AS kt_id,
            LTRIM(RTRIM(e.DTSC0))   AS dtsc0,
            LTRIM(RTRIM(e.KTSC0))   AS ktsc0,
            e.SUM_,
            LEFT(e.DATE_TIME_DOCID, 8)  AS date_,
            ISNULL(e.SP210, '')         AS SP210
        FROM _1SENTRY e (NOLOCK)
        WHERE (
            LTRIM(RTRIM(e.ACCDTID)) IN ({_ACC_IN})
            OR LTRIM(RTRIM(e.ACCKTID)) IN ({_ACC_IN})
        )
          AND LEFT(e.DATE_TIME_DOCID, 8) <= '{report_date}'
        ORDER BY LEFT(e.DATE_TIME_DOCID, 8) ASC
    """

    cursor = conn.cursor()
    cursor.execute(sql)
    cols = [c[0] for c in cursor.description]

    # Stream rows in chunks to avoid holding everything in memory at once
    chunk_size = 10_000
    while True:
        rows = cursor.fetchmany(chunk_size)
        if not rows:
            break
        for row in rows:
            r      = dict(zip(cols, row))
            dtsc0  = r.get("dtsc0", "")
            ktsc0  = r.get("ktsc0", "")

            # Determine which side carries the policy code
            if dtsc0 in policy_sc_set:
                r["policy_sc_code"] = dtsc0
                entries_by_policy[dtsc0].append(r)
            elif ktsc0 in policy_sc_set:
                r["policy_sc_code"] = ktsc0
                entries_by_policy[ktsc0].append(r)
            # rows where neither side is an XMLI policy are discarded

    cursor.close()

    if progress_callback:
        progress_callback(1, 1)

    return entries_by_policy
