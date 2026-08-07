"""Deterministic JSON-LD JobPosting salary-disclosure audit."""
from decimal import Decimal, InvalidOperation
from typing import Any

MAX_JOB_POSTINGS = 25


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else [value]


def _number(value: Any) -> float | None:
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _currency(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip().upper()
    return value if len(value) == 3 and value.isalpha() else None


def audit_job(job: dict[str, Any]) -> dict[str, Any]:
    salary = job.get("baseSalary")
    salary = salary if isinstance(salary, dict) else {}
    value = salary.get("value")
    value = value if isinstance(value, dict) else {}
    minimum, maximum, exact = (_number(value.get(name)) for name in ("minValue", "maxValue", "value"))
    currency = _currency(salary.get("currency"))
    unit = value.get("unitText") if isinstance(value.get("unitText"), str) else None
    issues: list[str] = []
    if not salary:
        issues.append("missing_base_salary")
    if not currency:
        issues.append("missing_or_invalid_currency")
    if minimum is None and maximum is None and exact is None:
        issues.append("missing_numeric_salary")
    if minimum is not None and maximum is not None and minimum > maximum:
        issues.append("salary_range_reversed")
    if unit is None:
        issues.append("missing_salary_unit")
    return {
        "event_type": "salary-disclosure-audited", "billable_units": 1,
        "job_id": str(job.get("identifier") or job.get("url") or job.get("title") or "unknown"),
        "title": job.get("title") if isinstance(job.get("title"), str) else None,
        "currency": currency, "minimum": minimum, "maximum": maximum, "exact": exact,
        "unit_text": unit, "disclosure_status": "disclosed" if not issues else "incomplete", "issues": issues,
    }


def build_salary_audit(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != {"job_postings"}:
        raise ValueError("body must be an object with only job_postings")
    postings = payload["job_postings"]
    if not isinstance(postings, list) or not postings or len(postings) > MAX_JOB_POSTINGS:
        raise ValueError(f"job_postings must be an array of 1..{MAX_JOB_POSTINGS} objects")
    for job in postings:
        if not isinstance(job, dict) or "JobPosting" not in _as_list(job.get("@type")):
            raise ValueError("each job_postings entry must be an object declaring @type JobPosting")
    records = [audit_job(job) for job in postings]
    return {"product": "salary-disclosure-audit", "unit": {"job_postings": len(records), "billable_request_units": 1}, "audits": records}
