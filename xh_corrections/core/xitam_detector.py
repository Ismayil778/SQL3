"""
Detects closed (xitam) policies via XalqLife.INS_POLICY where POLICY_STATE='E'.
Returns policies whose completion date falls within the reporting period.
"""
import pyodbc


def _yyyymmdd_to_sql(d: str) -> str:
    """Convert 'YYYYMMDD' to SQL-friendly 'YYYY-MM-DD'."""
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}"


def load_xitam_policies(
    conn_life: pyodbc.Connection,
    period_start: str,   # 'YYYYMMDD'
    report_date: str,    # 'YYYYMMDD'
) -> list[dict]:
    """
    Returns closed XMLI policies whose POLICY_COMPLETE_DATE is within
    [period_start, report_date].

    Each dict has: policy_number, policy_complete_date, policy_id.
    AMOUNT is intentionally absent — accountant fills it manually from XalqLife.
    """
    start_sql = _yyyymmdd_to_sql(period_start)
    end_sql   = _yyyymmdd_to_sql(report_date)

    sql = f"""
        SELECT
            LTRIM(RTRIM(p.POLICY_NUMBER)) AS policy_number,
            p.POLICY_COMPLETE_DATE        AS policy_complete_date,
            LTRIM(RTRIM(p.POLICY_ID))     AS policy_id
        FROM INS_POLICY p
        WHERE p.POLICY_NUMBER LIKE 'XMLI%'
          AND p.POLICY_STATE = 'E'
          AND p.POLICY_COMPLETE_DATE IS NOT NULL
          AND CAST(p.POLICY_COMPLETE_DATE AS DATE)
              BETWEEN '{start_sql}' AND '{end_sql}'
        ORDER BY p.POLICY_COMPLETE_DATE
    """

    cursor = conn_life.cursor()
    cursor.execute(sql)
    cols = [c[0] for c in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    cursor.close()

    # Normalise datetime to date where pyodbc returns datetime objects
    for row in rows:
        d = row.get("policy_complete_date")
        if d is not None and hasattr(d, "date"):
            row["policy_complete_date"] = d.date()

    return rows
