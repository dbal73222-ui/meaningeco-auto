import csv
import json
from pathlib import Path

from agent_selection.applicant_parser import Applicant
from agent_selection.output import print_summary, save_results

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


def test_save_results_creates_json_and_csv(tmp_path: Path):
    json_path, csv_path = save_results(
        [SAMPLE_APPLICANT], tmp_path, timestamp="20260806_100000"
    )

    assert json_path == tmp_path / "20260806_100000.json"
    assert csv_path == tmp_path / "20260806_100000.csv"

    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved[0]["name"] == "홍길동"
    assert saved[0]["participation_count"] == 3

    with csv_path.open(encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        row = next(reader)
        assert row["name"] == "홍길동"
        assert row["role_type"] == "A"


def test_save_results_handles_empty_list(tmp_path: Path):
    json_path, csv_path = save_results([], tmp_path, timestamp="20260806_100000")

    assert json.loads(json_path.read_text(encoding="utf-8")) == []
    assert csv_path.read_text(encoding="utf-8-sig") != ""


def test_print_summary_outputs_counts(capsys):
    print_summary([SAMPLE_APPLICANT])
    captured = capsys.readouterr()

    assert "총 수집 지원자: 1명" in captured.out
    assert "A타입: 1명" in captured.out
