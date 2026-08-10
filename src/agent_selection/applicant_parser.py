from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Applicant:
    no: str
    name: str
    phone: str
    birth_date: str
    gender: str
    applied_at: str
    status: str
    status_changed_at: str
    selected_schedule: str
    approved_schedule: str
    role_type: str
    participation_count: str
    custom_option_3: str
    posting_url: str
    posting_title: str


def parse_applicant_row(
    row: dict[str, str], posting_url: str, posting_title: str
) -> Applicant:
    return Applicant(
        no=row.get("no", ""),
        name=row.get("name", ""),
        phone=row.get("phone", ""),
        birth_date=row.get("birth_date", ""),
        gender=row.get("gender", ""),
        applied_at=row.get("applied_at", ""),
        status=row.get("status", ""),
        status_changed_at=row.get("status_changed_at", ""),
        selected_schedule=row.get("selected_schedule", ""),
        approved_schedule=row.get("approved_schedule", ""),
        role_type=row.get("custom_option_1", "").strip(),
        participation_count=row.get("custom_option_2", "").strip(),
        custom_option_3=row.get("custom_option_3", ""),
        posting_url=posting_url,
        posting_title=posting_title,
    )


def parse_applicant_rows(
    rows: list[dict[str, str]], posting_url: str, posting_title: str
) -> list[Applicant]:
    return [parse_applicant_row(row, posting_url, posting_title) for row in rows]
