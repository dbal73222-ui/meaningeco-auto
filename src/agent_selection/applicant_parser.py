from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# output.py도 동일 값을 참조하므로 여기서 단일 정의하고 파생시킴 (역할타입 중복 정의 방지)
ROLE_TYPES: tuple[str, ...] = ("A", "B", "C")
VALID_ROLE_TYPES = frozenset(ROLE_TYPES)


class ApplicantParseError(Exception):
    """지원자 행 파싱 실패"""


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
    participation_count: int
    custom_option_3: str
    posting_url: str


def parse_applicant_row(row: dict[str, str], posting_url: str) -> Applicant:
    role_type = row.get("custom_option_1", "").strip().upper()
    if role_type not in VALID_ROLE_TYPES:
        raise ApplicantParseError(
            f"알 수 없는 역할타입: {row.get('custom_option_1')!r} (no={row.get('no')})"
        )

    participation_raw = row.get("custom_option_2", "").strip()
    try:
        participation_count = int(participation_raw)
    except ValueError as exc:
        raise ApplicantParseError(
            f"참여이력이 숫자가 아닙니다: {participation_raw!r} (no={row.get('no')})"
        ) from exc

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
        role_type=role_type,
        participation_count=participation_count,
        custom_option_3=row.get("custom_option_3", ""),
        posting_url=posting_url,
    )


def parse_applicant_rows(
    rows: list[dict[str, str]], posting_url: str
) -> list[Applicant]:
    applicants: list[Applicant] = []
    for row in rows:
        try:
            applicants.append(parse_applicant_row(row, posting_url))
        except ApplicantParseError as exc:
            logger.warning("지원자 행 스킵: %s", exc)
    return applicants
