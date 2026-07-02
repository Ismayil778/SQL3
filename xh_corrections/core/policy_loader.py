"""
Loads XMLI policy data from two sources:
  - XalqLife: active policy list with insurance_start_date, payment plans
  - Base_1c77: already-recognised income from _1SENTRY (AZ→7W/7X entries)
"""
import pyodbc
from collections import defaultdict
from typing import Optional, Callable


def load_xmli_policies_from_life(conn_life: pyodbc.Connection) -> list[dict]:
    """
    Returns active XMLI policies (POLICY_STATE='D') from XalqLife.INS_POLICY.

    Each dict has: policy_id, policy_number, insurance_start_date.
    """
    sql = """
        SELECT
            LTRIM(RTRIM(p.POLICY_ID))     AS policy_id,
            LTRIM(RTRIM(p.POLICY_NUMBER)) AS policy_number,
            p.INSURANCE_START_DATE        AS insurance_start_date
        FROM INS_POLICY p
        WHERE p.POLICY_NUMBER LIKE 'XMLI%'
          AND p.POLICY_STATE = 'D'
        ORDER BY p.POLICY_NUMBER
    """
    cursor = conn_life.cursor()
    cursor.execute(sql)
    cols = [c[0] for c in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()
    return rows


def load_payment_plans(conn_life: pyodbc.Connection) -> dict[str, float]:
    """
    Returns dict of policy_id -> monthly_installment from XalqLife payment plan.

    Annual detection: if gap between first two payments > 60 days,
    divide PAYMENT_AMOUNT by 12.
    """
    sql = """
        SELECT pp.POLICY_ID,
               pp.PAYMENT_DATE,
               pp.PAYMENT_AMOUNT
        FROM INS_POLICY_PAYMENT_PLAN pp
        JOIN INS_POLICY p ON p.POLICY_ID = pp.POLICY_ID
        WHERE p.POLICY_NUMBER LIKE 'XMLI%'
        ORDER BY pp.POLICY_ID, pp.PAYMENT_DATE ASC
    """
    cursor = conn_life.cursor()
    cursor.execute(sql)
    cols = [c[0] for c in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()

    by_policy: dict[str, list] = defaultdict(list)
    for row in rows:
        pid = str(row.get("POLICY_ID") or "").strip()
        if pid:
            by_policy[pid].append(row)

    result: dict[str, float] = {}
    for policy_id, payments in by_policy.items():
        if not payments:
            continue
        first_amount = float(payments[0].get("PAYMENT_AMOUNT") or 0)
        if first_amount <= 0:
            continue

        if len(payments) >= 2:
            d0 = payments[0].get("PAYMENT_DATE")
            d1 = payments[1].get("PAYMENT_DATE")
            if d0 is not None and d1 is not None:
                # pyodbc may return datetime; .date() normalises
                if hasattr(d0, "date"):
                    d0 = d0.date()
                if hasattr(d1, "date"):
                    d1 = d1.date()
                days_diff = (d1 - d0).days
                if days_diff > 60:
                    # Annual payment — divide by 12
                    result[policy_id] = round(first_amount / 12, 2)
                    continue

        result[policy_id] = round(first_amount, 2)

    return result


def load_recognised_income_from_1c(
    conn_1c: pyodbc.Connection,
    report_date: str,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> dict[str, float]:
    """
    Returns dict of policy_number -> total_recognised from Base_1c77.

    Sums _1SENTRY entries where:
      dt=AZ (account 84.1.1) and kt IN (7W, 7X) (accounts 38.1.x)
    Both 7W and 7X are summed as one logical income account
    (38.1.1 and 38.1.2 are a technical import artifact, not a real split).

    report_date: 'YYYYMMDD'
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
        )
        SELECT pc.policy_number,
               SUM(e.SUM_) AS total_recognised
        FROM _1SENTRY e (NOLOCK)
        JOIN policy_codes pc
            ON LTRIM(RTRIM(e.DTSC0)) = pc.sc_code
            OR LTRIM(RTRIM(e.KTSC0)) = pc.sc_code
        WHERE LTRIM(RTRIM(e.ACCDTID)) = 'AZ'
          AND LTRIM(RTRIM(e.ACCKTID)) IN ('7W', '7X')
          AND LEFT(e.DATE_TIME_DOCID, 8) <= '{report_date}'
        GROUP BY pc.policy_number
    """

    cursor = conn_1c.cursor()
    cursor.execute(sql)
    cols = [c[0] for c in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()

    if progress_callback:
        progress_callback(1, 1)

    return {
        str(row["policy_number"]).strip(): float(row["total_recognised"] or 0)
        for row in rows
        if row.get("policy_number")
    }
