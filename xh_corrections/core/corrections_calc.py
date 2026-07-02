"""
Business logic: calculate corrective entries (Types 3-4) for active XMLI policies.

Algorithm (v2 — two-database):
  1. Source policy list and insurance_start_date from XalqLife.INS_POLICY
  2. Source monthly_installment from XalqLife.INS_POLICY_PAYMENT_PLAN
     (already reflects amendments — no need to parse reclassification entries)
  3. Source already-recognised income from Base_1c77._1SENTRY (AZ→7W/7X)
  4. months_to_correct = months_elapsed - months_recognised
  5. Two correction rows per policy if months_to_correct > 0:
       Type 3: DT=84.1.1. / KT=38.1.2.
       Type 4: DT=77.1.1.1. / KT=79.1.1.1.
"""
from datetime import date


def _months_between(d1: date, d2: date) -> int:
    """
    Calendar months from d1 to d2 inclusive.
    Same month → 1, next month → 2.
    """
    return (d2.year - d1.year) * 12 + (d2.month - d1.month) + 1


def calculate_corrections(
    policies: list[dict],
    payment_plans: dict[str, float],
    recognised_income: dict[str, float],
    report_date_str: str,
) -> list[dict]:
    """
    Args:
        policies:          XalqLife active policies — list of dicts with
                           policy_id, policy_number, insurance_start_date
        payment_plans:     policy_id -> monthly_installment (from XalqLife)
        recognised_income: policy_number -> total_recognised (from Base_1c77)
        report_date_str:   'YYYYMMDD'

    Returns:
        list of correction row dicts with DT, KT, AMOUNT, Policy_Number, Months
    """
    rd = report_date_str
    try:
        report_date = date(int(rd[:4]), int(rd[4:6]), int(rd[6:8]))
    except (ValueError, TypeError):
        raise ValueError(f"Invalid report_date: {report_date_str!r}")

    corrections: list[dict] = []

    for policy in policies:
        policy_id     = str(policy.get("policy_id") or "").strip()
        policy_number = str(policy.get("policy_number") or "").strip()
        start_date    = policy.get("insurance_start_date")

        if not policy_id or not policy_number or start_date is None:
            continue

        # Normalise datetime → date
        if hasattr(start_date, "date"):
            start_date = start_date.date()

        if start_date > report_date:
            continue

        monthly = payment_plans.get(policy_id, 0.0)
        if monthly <= 0:
            continue

        total_recognised  = recognised_income.get(policy_number, 0.0)
        months_recognised = round(total_recognised / monthly) if monthly > 0 else 0

        months_elapsed    = _months_between(start_date, report_date)
        months_to_correct = months_elapsed - months_recognised

        if months_to_correct <= 0:
            continue

        amount = round(monthly * months_to_correct, 2)

        corrections.append({
            "DT":            "84.1.1.",
            "KT":            "38.1.2.",
            "AMOUNT":        amount,
            "Policy_Number": policy_number,
            "Months":        months_to_correct,
        })
        corrections.append({
            "DT":            "77.1.1.1.",
            "KT":            "79.1.1.1.",
            "AMOUNT":        amount,
            "Policy_Number": policy_number,
            "Months":        months_to_correct,
        })

    return corrections
