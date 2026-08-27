from agent_selection.applicant_parser import (
    Applicant,
    enrich_applicants_with_career,
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


def test_parse_applicant_row_maps_all_fields():
    applicant = parse_applicant_row(
        VALID_ROW, posting_url="https://a.example.com", posting_title="미화 공고"
    )

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
        participation_count="3",
        custom_option_3="기타",
        posting_url="https://a.example.com",
        posting_title="미화 공고",
    )


def test_parse_applicant_row_allows_empty_custom_options():
    row = {**VALID_ROW, "custom_option_1": "", "custom_option_2": ""}

    applicant = parse_applicant_row(
        row, posting_url="https://a.example.com", posting_title="미화 공고"
    )

    assert applicant.role_type == ""
    assert applicant.participation_count == ""


def test_parse_applicant_rows_maps_every_row():
    rows = [VALID_ROW, {**VALID_ROW, "no": "2", "name": "김철수"}]

    applicants = parse_applicant_rows(
        rows, posting_url="https://a.example.com", posting_title="미화 공고"
    )

    assert [a.no for a in applicants] == ["1", "2"]
    assert all(a.posting_title == "미화 공고" for a in applicants)


def test_enrich_applicants_with_career_fills_matching_phone():
    applicant = parse_applicant_row(
        VALID_ROW, posting_url="https://a.example.com", posting_title="미화 공고"
    )

    enriched = enrich_applicants_with_career([applicant], {"01012345678": 4})

    assert enriched[0].career_count == 4


def test_enrich_applicants_with_career_normalizes_phone_format_differences():
    row = {**VALID_ROW, "phone": "01012345678"}  # 하이픈 없는 형식
    applicant = parse_applicant_row(row, posting_url="https://a.example.com", posting_title="미화 공고")

    # career_counts_by_phone 쪽은 하이픈 있는 형식으로 와도 매칭되어야 함
    enriched = enrich_applicants_with_career([applicant], {"010-1234-5678": 2})

    assert enriched[0].career_count == 2


def test_enrich_applicants_with_career_leaves_none_for_unmatched_phone():
    applicant = parse_applicant_row(
        VALID_ROW, posting_url="https://a.example.com", posting_title="미화 공고"
    )

    enriched = enrich_applicants_with_career([applicant], {"01099998888": 4})

    assert enriched[0].career_count is None


def test_enrich_applicants_with_career_does_not_mutate_original_list():
    applicant = parse_applicant_row(
        VALID_ROW, posting_url="https://a.example.com", posting_title="미화 공고"
    )
    original = [applicant]

    enrich_applicants_with_career(original, {"01012345678": 4})

    assert original[0].career_count is None
