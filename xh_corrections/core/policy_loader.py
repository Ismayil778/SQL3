"""
Loads XMLI policy list and their full entry history from _1SENTRY.
Batch-loads in chunks of 500 to avoid slow OR-joins on 1.28M rows.
"""
import pyodbc
from typing import Callable, Optional


PRODUCT_PREFIX = "XMLI"
BATCH_SIZE = 500

# Account IDs (from _1SACCS.ID, after LTRIM/RTRIM)
ACC = {
    "78": "B7",
    "79": "BA",
    "83": "9U",
    "84": "AZ",
    "77": "5F",
    "38w": "7W",
    "38x": "7X",
    # Hitam storno account
    "A3": "A3",
}


def load_all_policies(conn: pyodbc.Connection) -> list[dict]:
    """
    Returns list of {'policy_sc_code': str, 'policy_number': str}
    for all active XMLI policies from SC14632.
    """
    sql = """
        SELECT LTRIM(RTRIM(ID)) AS policy_sc_code,
               LTRIM(RTRIM(DESCR)) AS policy_number
        FROM SC14632 (NOLOCK)
        WHERE DESCR LIKE 'XMLI%'
          AND LEN(LTRIM(RTRIM(DESCR))) > 0
        ORDER BY DESCR
    """
    cursor = conn.cursor()
    cursor.execute(sql)
    columns = [col[0] for col in cursor.description]
    result = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()

    # Filter out batch/service subconto codes
    batch_codes = {"FN", "0", "I"}
    result = [p for p in result if p["policy_sc_code"] not in batch_codes]
    return result


def load_entries_for_policies(
    conn: pyodbc.Connection,
    policies: list[dict],
    report_date: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> dict[str, list[dict]]:
    """
    Load all _1SENTRY rows for the given policies up to report_date (YYYYMMDD).
    Returns dict: policy_sc_code -> list of entry rows.

    Uses #temp tables in batches of BATCH_SIZE to avoid slow OR-joins.
    """
    entries_by_policy: dict[str, list[dict]] = {p["policy_sc_code"]: [] for p in policies}
    sc_codes = [p["policy_sc_code"] for p in policies]

    total_batches = (len(sc_codes) + BATCH_SIZE - 1) // BATCH_SIZE
    processed = 0

    for batch_idx in range(0, len(sc_codes), BATCH_SIZE):
        batch = sc_codes[batch_idx: batch_idx + BATCH_SIZE]

        cursor = conn.cursor()

        # Create temp table
        cursor.execute("CREATE TABLE #policy_codes (sc_code VARCHAR(20))")

        # Insert batch values
        placeholders = ",".join(["(?)" for _ in batch])
        cursor.execute(f"INSERT INTO #policy_codes (sc_code) VALUES {placeholders}", batch)

        # Query entries
        query = f"""
            SELECT
                LTRIM(RTRIM(e.ACCDTID)) AS dt_id,
                LTRIM(RTRIM(e.ACCKTID)) AS kt_id,
                CASE
                    WHEN LTRIM(RTRIM(e.DTSC0)) IN (SELECT sc_code FROM #policy_codes)
                         THEN LTRIM(RTRIM(e.DTSC0))
                    ELSE LTRIM(RTRIM(e.KTSC0))
                END AS policy_sc_code,
                e.SUM_,
                LEFT(e.DATE_TIME_DOCID, 8) AS date_,
                ISNULL(e.SP210, '') AS SP210
            FROM _1SENTRY e (NOLOCK)
            JOIN #policy_codes p
                ON LTRIM(RTRIM(e.DTSC0)) = p.sc_code
                OR LTRIM(RTRIM(e.KTSC0)) = p.sc_code
            WHERE LEFT(e.DATE_TIME_DOCID, 8) <= '{report_date}'
            ORDER BY LEFT(e.DATE_TIME_DOCID, 8) ASC
        """
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()

        for row in rows:
            row_dict = dict(zip(columns, row))
            sc = row_dict.get("policy_sc_code", "")
            if sc in entries_by_policy:
                entries_by_policy[sc].append(row_dict)

        cursor.execute("DROP TABLE #policy_codes")
        conn.commit()
        cursor.close()

        processed += 1
        if progress_callback:
            progress_callback(processed, total_batches)

    return entries_by_policy
