"""
Loads XMLI policy data from two sources:
  - XalqLife: policy status (D=active, E=closed), payment plan (annual/monthly)
  - Base_1c77: last BA→B7 reclassification = annual installment (reflects amendments)

Key insight: INS_POLICY_PAYMENT_PLAN is NOT updated on amendments.
Monthly installment must come from last Base_1c77 reclassification / 12.
"""
import pyodbc
from collections import defaultdict
from typing import Optional, Callable


# ---------------------------------------------------------------------------
# XalqLife queries
# ---------------------------------------------------------------------------

def load_xmli_policies_from_life(conn_life: pyodbc.Connection) -> list[dict]:
    """
    Returns all XMLI policies from XalqLife.INS_POLICY.

    Each dict: policy_id, policy_number, policy_state,
               policy_complete_date, insurance_start_date
    """
    sql = """
        SELECT
            LTRIM(RTRIM(p.POLICY_ID))     AS policy_id,
            LTRIM(RTRIM(p.POLICY_NUMBER)) AS policy_number,
            LTRIM(RTRIM(p.POLICY_STATE))  AS policy_state,
            p.POLICY_COMPLETE_DATE        AS policy_complete_date,
            p.INSURANCE_START_DATE        AS insurance_start_date
        FROM INS_POLICY p
        WHERE p.POLICY_NUMBER LIKE 'XMLI%'
        ORDER BY p.POLICY_NUMBER
    """
    cursor = conn_life.cursor()
    cursor.execute(sql)
    cols = [c[0].lower() for c in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()

    # Normalise datetime → date
    for row in rows:
        for field in ("policy_complete_date", "insurance_start_date"):
            val = row.get(field)
            if val is not None and hasattr(val, "date"):
                row[field] = val.date()

    return rows


def load_payment_plans_summary(conn_life: pyodbc.Connection) -> dict[str, dict]:
    """
    Returns payment plan summary for annual/monthly detection only.
    DO NOT use amounts for installment calculation — use last_reclass instead.

    Returns: {policy_number: {'is_annual': bool, 'payment_amount': float}}
    """
    sql = """
        WITH ranked AS (
            SELECT
                LTRIM(RTRIM(p.POLICY_NUMBER)) AS policy_number,
                pp.PAYMENT_DATE,
                pp.PAYMENT_AMOUNT,
                ROW_NUMBER() OVER (
                    PARTITION BY pp.POLICY_ID
                    ORDER BY pp.PAYMENT_DATE ASC
                ) AS rn
            FROM INS_POLICY_PAYMENT_PLAN pp
            JOIN INS_POLICY p ON p.POLICY_ID = pp.POLICY_ID
            WHERE p.POLICY_NUMBER LIKE 'XMLI%'
        )
        SELECT policy_number, PAYMENT_DATE, PAYMENT_AMOUNT
        FROM ranked
        WHERE rn <= 2
        ORDER BY policy_number, PAYMENT_DATE
    """
    cursor = conn_life.cursor()
    cursor.execute(sql)
    cols = [c[0].lower() for c in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()

    by_policy: dict[str, list] = defaultdict(list)
    for row in rows:
        pn = str(row.get("policy_number") or "").strip()
        if pn:
            by_policy[pn].append(row)

    result: dict[str, dict] = {}
    for policy_number, payments in by_policy.items():
        if not payments:
            continue
        first_amount = float(payments[0].get("payment_amount") or 0)
        is_annual = False

        if len(payments) >= 2:
            d0 = payments[0].get("payment_date")
            d1 = payments[1].get("payment_date")
            if d0 is not None and d1 is not None:
                if hasattr(d0, "date"):
                    d0 = d0.date()
                if hasattr(d1, "date"):
                    d1 = d1.date()
                if (d1 - d0).days > 60:
                    is_annual = True

        result[policy_number] = {
            "is_annual": is_annual,
            "payment_amount": first_amount,
        }

    return result


# ---------------------------------------------------------------------------
# Base_1c77 queries
# ---------------------------------------------------------------------------

def load_last_reclassifications(
    conn_1c: pyodbc.Connection,
    balance_date: str,              # 'YYYYMMDD' — snapshot date (e.g. 20260331)
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> dict[str, dict]:
    """
    Returns last BA→B7 reclassification per XMLI policy from Base_1c77.

    Account codes:
        BA = 79.1.1.1  (Краткосрочный актив / DT side)
        B7 = 78.1.1.1  (Долгосрочный актив  / KT side)

    The policy sc_code is stored in DTSC1 (second subconto of account BA).
    Amount / 12 = monthly installment — reflects amendments automatically.

    Returns: {policy_number: {'amount': float, 'date': str 'YYYYMMDD'}}
    """
    if progress_callback:
        progress_callback(0, 1)

    sql = f"""
        WITH policy_codes AS (
            SELECT LTRIM(RTRIM(ID))    AS sc_code,
                   LTRIM(RTRIM(DESCR)) AS policy_number
            FROM SC14632 (NOLOCK)
            WHERE DESCR LIKE 'XMLI%'
              AND LEN(LTRIM(RTRIM(DESCR))) > 0
        ),
        reclass AS (
            SELECT
                pc.policy_number,
                e.SUM_                         AS reclass_amount,
                LEFT(e.DATE_TIME_DOCID, 8)     AS reclass_date,
                ROW_NUMBER() OVER (
                    PARTITION BY pc.policy_number
                    ORDER BY e.DATE_TIME_DOCID DESC
                ) AS rn
            FROM _1SENTRY e (NOLOCK)
            JOIN policy_codes pc
                ON LTRIM(RTRIM(e.DTSC1)) = pc.sc_code
                OR LTRIM(RTRIM(e.KTSC1)) = pc.sc_code
            WHERE LTRIM(RTRIM(e.ACCDTID)) = 'BA'
              AND LTRIM(RTRIM(e.ACCKTID)) = 'B7'
              AND LEFT(e.DATE_TIME_DOCID, 8) <= '{balance_date}'
        )
        SELECT policy_number, reclass_amount, reclass_date
        FROM reclass
        WHERE rn = 1
    """

    cursor = conn_1c.cursor()
    cursor.execute(sql)
    cols = [c[0].lower() for c in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()

    if progress_callback:
        progress_callback(1, 1)

    return {
        str(row["policy_number"]).strip(): {
            "amount": float(row.get("reclass_amount") or 0),
            "date":   str(row.get("reclass_date") or ""),
        }
        for row in rows
        if row.get("policy_number")
    }
