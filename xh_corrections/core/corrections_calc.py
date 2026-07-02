"""
Business logic: calculate corrective entries (Types 3-4) for each XMLI policy.

Algorithm (section 11 of spec):
  1. Parse policy parameters (inception date, full premium, monthly installment)
  2. Count already-recognised months
  3. Compute months_to_correct = months_elapsed - months_recognised
  4. Generate correction rows if months_to_correct > 0
"""
from datetime import date
from typing import Optional


# Account IDs after LTRIM/RTRIM
ACC_78  = "B7"   # долгосрочный актив
ACC_79  = "BA"   # краткосрочный актив
ACC_83  = "9U"   # долгосрочное обязательство
ACC_84  = "AZ"   # краткосрочное обязательство
ACC_77  = "5F"   # текущая дебиторка
ACC_38W = "7W"   # доход (юрлица, артефакт)
ACC_38X = "7X"   # доход (физлица, основной)
ACC_A3  = "A3"   # хитам / возврат

INCOME_ACCOUNTS = {ACC_38W, ACC_38X}


def _parse_date(date_str: str) -> Optional[date]:
    """Parse YYYYMMDD string to date object."""
    try:
        return date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    except (ValueError, TypeError, IndexError):
        return None


def _months_between(d1: date, d2: date) -> int:
    """
    Number of calendar months from d1 to d2 inclusive.
    e.g. same month → 1, next month → 2.
    """
    return (d2.year - d1.year) * 12 + (d2.month - d1.month) + 1


def _extract_client_from_sp210(sp210: str, policy_number: str) -> str:
    """
    Try to extract client name from SP210 field.
    Format: "... duzelishleri Ehmedli Senan Guloglan oglu.  Policy XMLI ..."
    Falls back to empty string.
    """
    if not sp210:
        return ""
    lower = sp210.lower()
    if "duzelishleri" in lower:
        idx_start = lower.index("duzelishleri") + len("duzelishleri")
        # find "Policy" or "Polis" keyword after client name
        idx_end = lower.find(" policy ", idx_start)
        if idx_end == -1:
            idx_end = lower.find(" polis ", idx_start)
        if idx_end != -1:
            return sp210[idx_start:idx_end].strip(" .")
    return ""


def calculate_corrections(
    policies: list[dict],
    entries_by_policy: dict[str, list[dict]],
    report_date_str: str,
) -> tuple[list[dict], list[str]]:
    """
    Main entry point.

    Args:
        policies: list of {'policy_sc_code', 'policy_number'}
        entries_by_policy: sc_code -> list of entry dicts
        report_date_str: 'YYYYMMDD'

    Returns:
        (corrections, hitam_policies) where:
          corrections — list of row dicts ready for export
          hitam_policies — list of policy numbers that are closed (hitam)
    """
    report_date = _parse_date(report_date_str)
    if not report_date:
        raise ValueError(f"Invalid report_date: {report_date_str}")

    corrections: list[dict] = []
    hitam_policies: list[str] = []

    for policy in policies:
        sc_code = policy["policy_sc_code"]
        policy_number = policy["policy_number"]
        entries = entries_by_policy.get(sc_code, [])

        if not entries:
            continue

        result = _process_policy(
            sc_code=sc_code,
            policy_number=policy_number,
            entries=entries,
            report_date=report_date,
        )

        if result is None:
            continue

        status, rows = result
        if status == "hitam":
            hitam_policies.append(policy_number)
            corrections.append({
                "DT": "",
                "KT": "",
                "AMOUNT": 0.0,
                "Policy_Number": policy_number,
                "Client": "Xitam",
                "Months": 0,
            })
        elif status == "ok" and rows:
            corrections.extend(rows)

    return corrections, hitam_policies


def _process_policy(
    sc_code: str,
    policy_number: str,
    entries: list[dict],
    report_date: date,
) -> Optional[tuple[str, list[dict]]]:
    """
    Process one policy. Returns:
      ('hitam', [])  — policy is closed
      ('ok', rows)   — correction rows (may be empty if already up-to-date)
      None           — skip (cannot determine parameters)
    """

    # --- Step 1: Detect HITAM (closed policy) ---
    has_hitam = _detect_hitam(entries)
    if has_hitam:
        return ("hitam", [])

    # --- Step 2: Get inception date and full premium ---
    inception_info = _get_inception(entries)
    if inception_info is None:
        return None
    inception_date, full_premium = inception_info

    if inception_date > report_date:
        # Policy starts after report date — nothing to do
        return ("ok", [])

    # --- Step 3: Get monthly installment ---
    monthly_installment = _get_monthly_installment(entries, full_premium)
    if monthly_installment is None or monthly_installment <= 0:
        return None

    # --- Step 4: Count already-recognised months ---
    total_recognised = _get_total_recognised(entries, monthly_installment)
    months_recognised = round(total_recognised / monthly_installment) if monthly_installment else 0

    # --- Step 5: Months elapsed ---
    months_elapsed = _months_between(inception_date, report_date)
    months_to_correct = months_elapsed - months_recognised

    if months_to_correct <= 0:
        return ("ok", [])

    # --- Step 6: Extract client name ---
    client = _get_client_name(entries, policy_number)

    # --- Step 7: Generate correction rows ---
    amount = round(monthly_installment * months_to_correct, 2)

    rows = [
        {
            "DT": "84.1.1.",
            "KT": "38.1.2.",
            "AMOUNT": amount,
            "Policy_Number": policy_number,
            "Client": client,
            "Months": months_to_correct,
        },
        {
            "DT": "77.1.1.1.",
            "KT": "79.1.1.1.",
            "AMOUNT": amount,
            "Policy_Number": policy_number,
            "Client": client,
            "Months": months_to_correct,
        },
    ]
    return ("ok", rows)


def _detect_hitam(entries: list[dict]) -> bool:
    """
    Hitam: entry with dt_id='A3' AND kt_id contains '77' (ACC_77='5F')
    with POSITIVE SUM_ and SP210 contains 'CemiQaytarilanSH'.
    Negative SUM_ = storno (cancellation of hitam) → policy is still active.

    Check: after last positive hitam, if there are subsequent Type 3-4 entries,
    it means hitam was reversed and policy is active.
    """
    last_hitam_idx = None
    last_hitam_positive = False

    for i, e in enumerate(entries):
        dt = e.get("dt_id", "")
        kt = e.get("kt_id", "")
        sp210 = e.get("SP210", "") or ""
        sum_ = e.get("SUM_") or 0

        if dt == ACC_A3 and "CemiQaytarilanSH" in sp210:
            last_hitam_idx = i
            last_hitam_positive = float(sum_) > 0

    if last_hitam_idx is None:
        return False

    if not last_hitam_positive:
        # Last hitam entry is a storno — policy is active
        return False

    # Check if there are Type 3-4 entries AFTER the hitam
    for e in entries[last_hitam_idx + 1:]:
        dt = e.get("dt_id", "")
        kt = e.get("kt_id", "")
        sp210 = e.get("SP210", "") or ""
        if (dt == ACC_84 and kt in INCOME_ACCOUNTS) or \
           (dt == ACC_83 and kt in INCOME_ACCOUNTS and "hesablar" in sp210.lower()):
            return False  # Policy resumed after hitam

    return True


def _get_inception(entries: list[dict]) -> Optional[tuple[date, float]]:
    """
    Find the policy inception entry:
    dt_id IN (B7, 5F) AND kt_id = 9U  → returns (inception_date, full_premium)
    Takes the FIRST such entry chronologically.
    """
    for e in entries:
        dt = e.get("dt_id", "")
        kt = e.get("kt_id", "")
        if dt in (ACC_78, ACC_77) and kt == ACC_83:
            d = _parse_date(e.get("date_", ""))
            if d:
                return (d, float(e.get("SUM_") or 0))
    return None


def _get_monthly_installment(entries: list[dict], full_premium: float) -> Optional[float]:
    """
    Method 1: last reclassification entry dt=BA, kt=B7 (79→78) annual / 12
              OR dt=9U, kt=AZ (83→84) annual / 12

    Method 2 (new policy, no reclassification yet):
              first bank payment dt=BA, kt=5F → monthly amount directly

    Handles amendments: CemiAzalanSH / CemiElaveEdilenSH
    → use last reclassification (already reflects new tranche).
    """
    # Try to find reclassification entries
    reclass_entries = []
    for e in entries:
        dt = e.get("dt_id", "")
        kt = e.get("kt_id", "")
        if (dt == ACC_79 and kt == ACC_78) or (dt == ACC_83 and kt == ACC_84):
            reclass_entries.append(e)

    if reclass_entries:
        # Use the LAST reclassification (handles amendments automatically)
        last_reclass = reclass_entries[-1]
        annual = float(last_reclass.get("SUM_") or 0)
        if annual > 0:
            return round(annual / 12, 2)

    # Fallback: first bank payment (79→77 or BA→5F)
    for e in entries:
        dt = e.get("dt_id", "")
        kt = e.get("kt_id", "")
        if dt == ACC_79 and kt == ACC_77:
            amount = float(e.get("SUM_") or 0)
            if amount > 0:
                return round(amount, 2)

    # Last fallback: full_premium / 12 (should rarely happen)
    if full_premium > 0:
        return round(full_premium / 12, 2)

    return None


def _get_total_recognised(entries: list[dict], monthly_installment: float) -> float:
    """
    Sum all Type 3-4 income-recognition entries:
    - dt=AZ, kt IN (7W,7X), SP210 contains "Polislerin hesablar"
    - dt=9U, kt IN (7W,7X)  (first-month system entry)
    - dt=5F, kt=9U with simultaneous 9U→7X  (some formats)
    """
    total = 0.0
    for e in entries:
        dt = e.get("dt_id", "")
        kt = e.get("kt_id", "")
        sp210 = (e.get("SP210", "") or "").lower()
        sum_ = float(e.get("SUM_") or 0)

        # Standard correction entry
        if dt == ACC_84 and kt in INCOME_ACCOUNTS:
            if "polislerin hesablar" in sp210 or "duzelish" in sp210:
                total += sum_

        # First-month direct recognition 83→income
        if dt == ACC_83 and kt in INCOME_ACCOUNTS:
            total += sum_

    return total


def _get_client_name(entries: list[dict], policy_number: str) -> str:
    """
    Extract client name from SP210 of the first entry that has it.
    """
    for e in entries:
        sp210 = e.get("SP210", "") or ""
        client = _extract_client_from_sp210(sp210, policy_number)
        if client:
            return client
    return ""
