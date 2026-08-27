import json
from pathlib import Path

import pytest

import agent_selection.view as view_module
from agent_selection.applicant_parser import Applicant
from agent_selection.config import Config, ConfigError
from agent_selection.output import save_results
from agent_selection.view import (
    ViewError,
    find_latest_result,
    format_collected_at,
    group_pending_by_schedule,
    load_applicants,
    render_empty_html,
    render_html,
)

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
    participation_count="3",
    custom_option_3="기타",
    posting_url="https://a.example.com",
    posting_title="미화 공고",
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
    assert applicants[0]["posting_title"] == "미화 공고"


def test_load_applicants_raises_view_error_on_broken_json(tmp_path: Path):
    broken_path = tmp_path / "20260806_100000.json"
    broken_path.write_text("{이건 json이 아님", encoding="utf-8")

    with pytest.raises(ViewError):
        load_applicants(broken_path)


SAMPLE_ROWS = [
    {
        "no": "1",
        "name": "홍길동",
        "phone": "010-1234-5678",
        "posting_url": "https://a.example.com/1",
        "posting_title": "미화 공고",
        "role_type": "A",
        "participation_count": "3",
        "status": "대기",
        "applied_at": "2026-08-01 10:00",
    },
    {
        "no": "2",
        "name": "김철수",
        "phone": "010-9999-0000",
        "posting_url": "https://a.example.com/2",
        "posting_title": "다회용기 공고",
        "role_type": "",
        "participation_count": "",
        "status": "합격",
        "applied_at": "2026-08-02 11:00",
    },
]


def _raw_applicant(status: str, selected_schedule: str, applied_at: str, name: str = "홍길동") -> dict:
    return {
        "name": name,
        "phone": "010-0000-0000",
        "posting_title": "미화 공고",
        "role_type": "A",
        "participation_count": "3",
        "status": status,
        "applied_at": applied_at,
        "selected_schedule": selected_schedule,
    }


def test_group_pending_by_schedule_filters_non_pending():
    applicants = [
        _raw_applicant("대기", "1일차", "2026-08-01 10:00"),
        _raw_applicant("합격", "1일차", "2026-08-01 11:00"),
    ]

    result = group_pending_by_schedule(applicants)

    assert len(result) == 1
    assert len(result[0]["applicants"]) == 1


def test_group_pending_by_schedule_groups_by_selected_schedule():
    applicants = [
        _raw_applicant("대기", "1일차", "2026-08-01 10:00", name="홍길동"),
        _raw_applicant("대기", "2일차", "2026-08-01 11:00", name="김철수"),
    ]

    result = group_pending_by_schedule(applicants)

    schedules = [group["schedule"] for group in result]
    assert schedules == ["1일차", "2일차"]


def test_group_pending_by_schedule_empty_schedule_becomes_unspecified():
    applicants = [_raw_applicant("대기", "", "2026-08-01 10:00")]

    result = group_pending_by_schedule(applicants)

    assert result[0]["schedule"] == "미지정"


def test_group_pending_by_schedule_sorts_within_group_by_applied_at():
    applicants = [
        _raw_applicant("대기", "1일차", "2026-08-02 09:00", name="나중지원"),
        _raw_applicant("대기", "1일차", "2026-08-01 09:00", name="먼저지원"),
    ]

    result = group_pending_by_schedule(applicants)

    names = [row["name"] for row in result[0]["applicants"]]
    assert names == ["먼저지원", "나중지원"]


def test_group_pending_by_schedule_puts_unspecified_group_last():
    applicants = [
        _raw_applicant("대기", "", "2026-08-01 10:00"),
        _raw_applicant("대기", "1일차", "2026-08-01 11:00"),
    ]

    result = group_pending_by_schedule(applicants)

    schedules = [group["schedule"] for group in result]
    assert schedules == ["1일차", "미지정"]


def test_group_pending_by_schedule_projects_view_columns_only():
    applicants = [_raw_applicant("대기", "1일차", "2026-08-01 10:00")]

    result = group_pending_by_schedule(applicants)

    row = result[0]["applicants"][0]
    assert set(row.keys()) == {
        "name", "phone", "posting_title",
        "participation_count", "status", "applied_at",
    }


def test_group_pending_by_schedule_ignores_participation_count_in_order():
    # 참여횟수가 높아도(9) 지원일시가 늦으면 뒤로 가야 함 — 참여횟수는 정렬 기준이 아님
    high_count_but_later = {
        **_raw_applicant("대기", "1일차", "2026-08-02 09:00", name="많이참여"),
        "participation_count": "9",
    }
    low_count_but_earlier = {
        **_raw_applicant("대기", "1일차", "2026-08-01 09:00", name="적게참여"),
        "participation_count": "0",
    }

    result = group_pending_by_schedule([high_count_but_later, low_count_but_earlier])

    names = [row["name"] for row in result[0]["applicants"]]
    assert names == ["적게참여", "많이참여"]


def test_render_html_includes_applicant_values():
    html = render_html(SAMPLE_ROWS, "2026-08-10 14:30:00")

    assert "홍길동" in html
    assert "010-1234-5678" in html
    assert "총 2명" in html
    assert "2026-08-10 14:30:00" in html


def test_render_html_includes_posting_filter_buttons():
    html = render_html(SAMPLE_ROWS, "2026-08-10 14:30:00")

    assert 'data-posting="https://a.example.com/1"' in html
    assert 'data-posting="https://a.example.com/2"' in html
    assert 'data-posting="ALL"' in html
    assert ">미화 공고<" in html
    assert ">다회용기 공고<" in html


def test_render_html_keeps_same_titled_postings_separate():
    # 매달 반복되는 것처럼 제목은 같지만 URL(=실제 공고)이 다른 두 지원자
    rows = [
        {**SAMPLE_ROWS[0], "posting_url": "https://a.example.com/1", "posting_title": "미화 공고"},
        {**SAMPLE_ROWS[1], "posting_url": "https://a.example.com/2", "posting_title": "미화 공고"},
    ]

    html = render_html(rows, "2026-08-10 14:30:00")

    assert 'data-posting="https://a.example.com/1"' in html
    assert 'data-posting="https://a.example.com/2"' in html
    assert html.count(">미화 공고<") == 2


def test_render_html_escapes_posting_title_html():
    rows = [{**SAMPLE_ROWS[0], "posting_title": '<script>alert(1)</script>"'}]

    html = render_html(rows, "2026-08-10 14:30:00")

    assert "<script>alert(1)</script>" not in html


def test_render_html_handles_empty_applicant_list():
    html = render_html([], "2026-08-10 14:30:00")

    assert "총 0명" in html


def test_render_html_includes_recommend_toggle_button():
    html = render_html(SAMPLE_ROWS, "2026-08-10 14:30:00")

    assert 'id="toggle-recommend"' in html
    assert "추천 보기" in html


def test_render_html_includes_recommend_notice_text():
    html = render_html(SAMPLE_ROWS, "2026-08-10 14:30:00")

    assert "실제 승인/거절은 엑스파일에서 직접 진행하세요" in html


def test_render_html_embeds_pending_schedule_groups():
    html = render_html(SAMPLE_ROWS, "2026-08-10 14:30:00")

    assert '"schedule": "미지정"' in html
    assert '"name": "홍길동"' in html


def test_render_html_embeds_empty_recommend_groups_when_no_pending():
    rows = [{**SAMPLE_ROWS[0], "status": "합격"}]

    html = render_html(rows, "2026-08-10 14:30:00")

    assert "const RECOMMEND_GROUPS = [];" in html


def test_render_html_escapes_script_close_tag_in_applicant_data():
    rows = [{**SAMPLE_ROWS[0], "name": "</script><script>alert(1)</script>"}]

    html = render_html(rows, "2026-08-10 14:30:00")

    assert "</script><script>alert(1)</script>" not in html


def test_render_empty_html_shows_guidance_message():
    html = render_empty_html()

    assert "아직 수집된 데이터가 없습니다" in html
    assert "agent_selection.main" in html


def test_format_collected_at_formats_timestamp_stem(tmp_path: Path):
    json_path = tmp_path / "20260810_143000.json"

    assert format_collected_at(json_path) == "2026-08-10 14:30:00"


def _make_config(output_dir: Path) -> Config:
    return Config(
        login_url="https://example.com",
        username="user",
        password="pw",
        posting_urls=("https://example.com/posting/1",),
        headless=True,
        output_dir=str(output_dir),
        api_base_url=None,
        api_email="user",
        api_password="pw",
        supervisor_career_threshold=None,
    )


def test_main_opens_browser_with_latest_result(tmp_path, monkeypatch):
    save_results([SAMPLE_APPLICANT], tmp_path, timestamp="20260806_100000")
    monkeypatch.setattr(view_module, "load_config", lambda: _make_config(tmp_path))
    opened_urls = []
    monkeypatch.setattr(view_module.webbrowser, "open", lambda url: opened_urls.append(url))

    exit_code = view_module.main()

    assert exit_code == 0
    view_path = tmp_path / "view.html"
    assert view_path.exists()
    assert "홍길동" in view_path.read_text(encoding="utf-8")
    assert opened_urls and opened_urls[0].startswith("file://")


def test_main_shows_empty_guidance_when_no_results(tmp_path, monkeypatch):
    monkeypatch.setattr(view_module, "load_config", lambda: _make_config(tmp_path))
    opened_urls = []
    monkeypatch.setattr(view_module.webbrowser, "open", lambda url: opened_urls.append(url))

    exit_code = view_module.main()

    assert exit_code == 0
    view_path = tmp_path / "view.html"
    assert "아직 수집된 데이터가 없습니다" in view_path.read_text(encoding="utf-8")
    assert opened_urls


def test_main_returns_1_on_config_error(monkeypatch):
    def _raise_config_error():
        raise ConfigError("설정 없음")

    monkeypatch.setattr(view_module, "load_config", _raise_config_error)
    opened_urls = []
    monkeypatch.setattr(view_module.webbrowser, "open", lambda url: opened_urls.append(url))

    exit_code = view_module.main()

    assert exit_code == 1
    assert opened_urls == []


def test_main_returns_1_on_broken_result_file(tmp_path, monkeypatch):
    (tmp_path / "20260806_100000.json").write_text("{이건 json이 아님", encoding="utf-8")
    monkeypatch.setattr(view_module, "load_config", lambda: _make_config(tmp_path))
    opened_urls = []
    monkeypatch.setattr(view_module.webbrowser, "open", lambda url: opened_urls.append(url))

    exit_code = view_module.main()

    assert exit_code == 1
    assert opened_urls == []
