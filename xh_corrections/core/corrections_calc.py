"""
Business logic: corrective entries (Types 1-4) and xitam list.

Algorithm (v3 — balance-file based):
  1. Excel balance file provides account snapshots as of period_start (31.03.2026)
  2. Monthly installment = last BA→B7 reclassification / 12  (Base_1c77)
     Fallback: XalqLife payment_plan / 12 if annual, else payment_plan (monthly)
  3. Five processing cases per policy (see below)

Five cases:
  1. Not in balance file   → new policy (skip — Base_1c77 fallback TBD)
  2. All balances zero     → already processed, skip
  3. Active (D)            → generate Q2 corrections (3 months)
  4. Closed before period  → corrections from last reclass date to close date
  5. Closed in period      → corrections from period start to close date

Four correction types generated per case:
  Types 1+2 (amount_34):
      DT=84.1.1. / KT=38.1.2.       (income recognition)
      DT=77.1.1.1. / KT=79.1.1.1.   (receivable correction)
  Types 3+4 (need_reclass, only if > 0):
      DT=79.1.1.1. / KT=78.1.1.1.   (reclassify short-term receivable)
      DT=83.1.1. / KT=84.1.1.        (reclassify short-term liability)
"""
from datetime import date


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def calculate_corrections(
    policies: list[dict],
    balances: dict[str, dict[str, float]],
    last_reclass: dict[str, dict],
    payment_plans: dict[str, dict],
    period_start: date,
    period_end: date,
) -> tuple[list[dict], list[dict]]:
    """
    Returns (corrections_rows, xitam_rows).

    Args:
        policies:      XalqLife policy list (from load_xmli_policies_from_life)
        balances:      Excel balance file {policy_number: {account: amount}}
        last_reclass:  Base_1c77 last BA→B7 {policy_number: {amount, date}}
        payment_plans: XalqLife payment summary {policy_number: {is_annual, payment_amount}}
        period_start:  First day of reporting period (e.g. date(2026, 4, 1))
        period_end:    Last day of reporting period  (e.g. date(2026, 6, 30))
    """
    corrections: list[dict] = []
    xitam: list[dict] = []

    # Number of months in the period (inclusive)
    period_months = (
        (period_end.year - period_start.year) * 12
        + (period_end.month - period_start.month)
        + 1
    )

    for policy in policies:
        policy_number = str(policy.get("policy_number") or "").strip()
        state         = str(policy.get("policy_state") or "").strip()
        complete_date = policy.get("policy_complete_date")

        if not policy_number:
            continue

        monthly = _get_monthly(policy_number, last_reclass, payment_plans)
        if monthly <= 0:
            continue

        b  = balances.get(policy_number, {})
        B7 = b.get("78.1.1.1", 0.0)
        BA = b.get("79.1.1.1", 0.0)
        U9 = b.get("83.1.1",   0.0)
        AZ = b.get("84.1.1",   0.0)

        # ── Case 1: new policy (not in balance file) ──────────────────────
        if policy_number not in balances:
            # Not yet implemented — would require separate 1C query
            continue

        # ── Case 2: all zeros = already processed ────────────────────────
        if B7 == 0 and BA == 0 and U9 == 0 and AZ == 0:
            continue

        # ── Case 3: active ────────────────────────────────────────────────
        if state == "D":
            months      = period_months
            amount_34   = round(monthly * months, 2)
            need_reclass = round(monthly * 12 - (BA - amount_34), 2)
            _add_rows(corrections, policy_number, amount_34, need_reclass)

        # ── Case 4: closed BEFORE period start ───────────────────────────
        elif state == "E" and complete_date is not None and complete_date < period_start:
            reclass_info = last_reclass.get(policy_number)
            if reclass_info and reclass_info.get("date"):
                reclass_date = _parse_yyyymmdd(reclass_info["date"])
                if reclass_date:
                    months = _months_between(reclass_date, complete_date)
                    if months > 0:
                        amount_34    = round(monthly * months, 2)
                        need_reclass = round(-(BA - amount_34), 2)
                        _add_rows(corrections, policy_number, amount_34, need_reclass)
            _add_xitam(xitam, policy_number, complete_date)

        # ── Case 5: closed IN period ──────────────────────────────────────
        elif (
            state == "E"
            and complete_date is not None
            and period_start <= complete_date <= period_end
        ):
            months = _months_between(period_start, complete_date)
            if months > 0:
                amount_34    = round(monthly * months, 2)
                need_reclass = round(-(BA - amount_34), 2)
                _add_rows(corrections, policy_number, amount_34, need_reclass)
            _add_xitam(xitam, policy_number, complete_date)

    return corrections, xitam


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_monthly(
    policy_number: str,
    last_reclass: dict[str, dict],
    payment_plans: dict[str, dict],
) -> float:
    """
    Monthly installment = last_reclass_amount / 12  (primary source).
    Fallback: XalqLife payment_plan (for new policies without reclassification).
    """
    reclass = last_reclass.get(policy_number)
    if reclass and reclass.get("amount", 0) > 0:
        return round(reclass["amount"] / 12, 4)

    plan = payment_plans.get(policy_number)
    if plan and plan.get("payment_amount", 0) > 0:
        if plan.get("is_annual"):
            return round(plan["payment_amount"] / 12, 4)
        return round(plan["payment_amount"], 4)

    return 0.0


def _months_between(d1: date, d2: date) -> int:
    """Inclusive month count: same month → 1, consecutive months → 2, etc."""
    return (d2.year - d1.year) * 12 + (d2.month - d1.month) + 1


def _parse_yyyymmdd(s: str) -> date | None:
    """Parse 'YYYYMMDD' string to date, return None on error."""
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except (ValueError, TypeError, IndexError):
        return None


def _add_rows(
    out: list[dict],
    policy_number: str,
    amount_34: float,
    need_reclass: float,
) -> None:
    """Append Type 1+2 rows, and optionally Type 3+4 rows."""
    if amount_34 > 0:
        out.append({
            "DT": "84.1.1.", "KT": "38.1.2.",
            "AMOUNT": amount_34, "Policy_Number": policy_number,
            "Type": "1",
        })
        out.append({
            "DT": "77.1.1.1.", "KT": "79.1.1.1.",
            "AMOUNT": amount_34, "Policy_Number": policy_number,
            "Type": "2",
        })
    if need_reclass > 0:
        out.append({
            "DT": "79.1.1.1.", "KT": "78.1.1.1.",
            "AMOUNT": need_reclass, "Policy_Number": policy_number,
            "Type": "3",
        })
        out.append({
            "DT": "83.1.1.", "KT": "84.1.1.",
            "AMOUNT": need_reclass, "Policy_Number": policy_number,
            "Type": "4",
        })


def _add_xitam(out: list[dict], policy_number: str, complete_date: date) -> None:
    out.append({
        "Policy_Number":  policy_number,
        "Xitam tarixi":  complete_date.strftime("%d.%m.%Y"),
        "DT":             "22.1.1.",
        "KT":             "77.1.1.X.",
        "AMOUNT":         None,      # filled manually from XalqLife
    })
