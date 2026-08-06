import logging

import pytest

from agent_selection.applicant_parser import (
    Applicant,
    ApplicantParseError,
    parse_applicant_row,
    parse_applicant_rows,
)

VALID_ROW = {
    "no": "1",
    "name": "홍길동",
    "phone": "010-1234-5678",
    "birth_date": "1990-01-01",
    "gender": "남",
    "applied_at": "2026-08-01 10:00",
    "status": "대기",
    "status_changed_at": "2026-08-01 10:00",
    "selected_schedule": "1일차",
    "approved_schedule": "",
    "custom_option_1": "A",
    "custom_option_2": "3",
    "custom_option_3": "기타",
}


def test_parse_applicant_row_success():
    applicant = parse_applicant_row(VALID_ROW, posting_url="https://a.example.com")

    assert applicant == Applicant(
        no="1",
        name="홍길동",
        phone="010-1234-5678",
        birth_date="1990-01-01",
        gender="남",
        applied_at="2026-08-01 10:00",
        status="대기",
        status_changed_at="2026-08-01 10:00",
        selected_schedule="1일차",
        approved_schedule="",
        role_type="A",
        participation_count=3,
        custom_option_3="기타",
        posting_url="https://a.example.com",
    )


def test_parse_applicant_row_invalid_role_type_raises():
    row = {**VALID_ROW, "custom_option_1": "Z"}

    with pytest.raises(ApplicantParseError, match="역할타입"):
        parse_applicant_row(row, posting_url="https://a.example.com")


def test_parse_applicant_row_invalid_participation_count_raises():
    row = {**VALID_ROW, "custom_option_2": "세번"}

    with pytest.raises(ApplicantParseError, match="참여이력"):
        parse_applicant_row(row, posting_url="https://a.example.com")


def test_parse_applicant_rows_skips_invalid_and_logs_warning(caplog):
    rows = [VALID_ROW, {**VALID_ROW, "no": "2", "custom_option_1": "Z"}]

    with caplog.at_level(logging.WARNING):
        applicants = parse_applicant_rows(rows, posting_url="https://a.example.com")

    assert len(applicants) == 1
    assert applicants[0].no == "1"
    assert "역할타입" in caplog.text
