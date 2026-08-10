import json
from pathlib import Path

import pytest

from agent_selection.applicant_parser import Applicant
from agent_selection.output import save_results
from agent_selection.view import ViewError, find_latest_result, load_applicants

SAMPLE_APPLICANT = Applicant(
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


def test_find_latest_result_picks_newest_timestamp(tmp_path: Path):
    save_results([SAMPLE_APPLICANT], tmp_path, timestamp="20260801_090000")
    save_results([SAMPLE_APPLICANT], tmp_path, timestamp="20260806_100000")
    save_results([SAMPLE_APPLICANT], tmp_path, timestamp="20260803_120000")

    latest = find_latest_result(tmp_path)

    assert latest == tmp_path / "20260806_100000.json"


def test_find_latest_result_returns_none_when_empty(tmp_path: Path):
    assert find_latest_result(tmp_path) is None


def test_load_applicants_parses_json(tmp_path: Path):
    json_path, _ = save_results([SAMPLE_APPLICANT], tmp_path, timestamp="20260806_100000")

    applicants = load_applicants(json_path)

    assert applicants[0]["name"] == "홍길동"
    assert applicants[0]["participation_count"] == 3


def test_load_applicants_raises_view_error_on_broken_json(tmp_path: Path):
    broken_path = tmp_path / "20260806_100000.json"
    broken_path.write_text("{이건 json이 아님", encoding="utf-8")

    with pytest.raises(ViewError):
        load_applicants(broken_path)
