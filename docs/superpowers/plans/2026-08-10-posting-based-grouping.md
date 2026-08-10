# 공고별 지원자 관리 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 역할타입(A/B/C) 검증/집계 방식을 없애고, 지원자를 "어느 공고에서 왔는지" 기준으로 관리하도록 전환한다.

**Architecture:** `applicant_parser.py`에서 역할타입/참여횟수 검증을 제거하고 `posting_title` 필드를 추가한다. `xfile_client.py`는 공고 제목을 함께 추출해 반환하고, `output.py`/`view.py`는 집계·필터 기준을 역할타입에서 공고명으로 바꾼다. `main.py`는 바뀐 시그니처에 맞춰 호출부만 수정한다.

**Tech Stack:** 기존과 동일 (표준 라이브러리 + Playwright). 신규 의존성 없음.

## Global Constraints

- 불변성 유지 — 뮤테이션 금지 (프로젝트 CLAUDE.md), `@dataclass(frozen=True)` 유지
- 환경변수는 `.env`로 관리, 하드코딩 금지 (프로젝트 CLAUDE.md)
- 주석은 한국어로, WHY만 작성 (프로젝트 CLAUDE.md)
- 파일 200-400줄, 최대 800줄 / 함수 50줄 이하, 타입 힌트 필수 (프로젝트 CLAUDE.md)
- 읽기 전용 원칙 유지 — 어떤 태스크도 엑스파일 사이트에 쓰기 동작을 추가하지 않는다
- `xfile_client.py`는 Playwright 실브라우저 의존 모듈이라 기존 컨벤션대로 단위 테스트 없이 실사이트 수동 검증으로 확인한다 (`docs/superpowers/plans/2026-08-06-agent-selection-phase1.md`의 Task 4와 동일한 전례)

---

## File Structure

- Modify: `src/agent_selection/applicant_parser.py` — `ROLE_TYPES`/`VALID_ROLE_TYPES`/`ApplicantParseError` 제거, `Applicant`에 `posting_title` 추가, `role_type`/`participation_count`를 검증 없는 `str`로 변경
- Modify: `tests/agent_selection/test_applicant_parser.py` — 검증 제거에 맞춰 전면 재작성
- Modify: `src/agent_selection/xfile_client.py` — `scrape_posting_applicants`가 `(공고 제목, 지원자 행)` 튜플을 반환하도록 변경
- Modify: `src/agent_selection/output.py` — `print_summary`를 공고명 기준 집계로 변경
- Modify: `tests/agent_selection/test_output.py` — 공고명 기준 집계 테스트로 변경
- Modify: `src/agent_selection/main.py` — 바뀐 반환 타입/시그니처에 맞춰 호출부 수정
- Modify: `src/agent_selection/view.py` — 공고명 컬럼 추가, 필터 버튼을 공고 기준으로 동적 생성, HTML 이스케이프 적용
- Modify: `tests/agent_selection/test_view.py` — 공고 필터/컬럼에 맞춰 전면 재작성

## 기존 인터페이스 (참고용, 변경 없음)

```python
# src/agent_selection/config.py — 변경 없음
@dataclass(frozen=True)
class Config:
    login_url: str
    username: str
    password: str
    posting_urls: tuple[str, ...]
    headless: bool
    output_dir: str

# src/agent_selection/xfile_client.py — 변경 없음
EXPECTED_COLUMNS: list[tuple[str, str]]  # (한글 라벨, 영문 키) 13쌍
class XfilePageError(Exception): ...
class XfileLoginError(Exception): ...
```

---

### Task 1: applicant_parser.py — 검증 제거, posting_title 추가

**Files:**
- Modify: `src/agent_selection/applicant_parser.py`
- Modify: `tests/agent_selection/test_applicant_parser.py`

**Interfaces:**
- Consumes: 없음 (순수 함수 모듈)
- Produces:
  - `Applicant` 데이터클래스 — `role_type: str`, `participation_count: str` (기존 `int`에서 변경), `posting_title: str` (신규)
  - `parse_applicant_row(row: dict[str, str], posting_url: str, posting_title: str) -> Applicant`
  - `parse_applicant_rows(rows: list[dict[str, str]], posting_url: str, posting_title: str) -> list[Applicant]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_applicant_parser.py` 전체를 아래 내용으로 교체:

```python
from agent_selection.applicant_parser import (
    Applicant,
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `pytest tests/agent_selection/test_applicant_parser.py -v`
Expected: FAIL — `TypeError: parse_applicant_row() missing 1 required positional argument: 'posting_title'` (또는 import 단계에서 실패)

- [ ] **Step 3: 구현 수정**

`src/agent_selection/applicant_parser.py` 전체를 아래 내용으로 교체:

```python
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
```

- [ ] **Step 4: 테스트가 통과하는지 확인**

Run: `pytest tests/agent_selection/test_applicant_parser.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/agent_selection/applicant_parser.py tests/agent_selection/test_applicant_parser.py
git commit -m "feat: 역할타입 검증 제거, 지원자에 공고명 필드 추가"
```

---

### Task 2: xfile_client.py — 공고 제목 추출

**Files:**
- Modify: `src/agent_selection/xfile_client.py`

**Interfaces:**
- Consumes: Task 1의 변경 없음 (이 모듈은 raw dict만 반환, `Applicant`를 모름)
- Produces: `scrape_posting_applicants(page: Page, posting_url: str) -> tuple[str, list[dict[str, str]]]` (기존엔 `list[dict[str, str]]`만 반환했음 — 반환 타입이 튜플로 바뀜)

이 모듈은 Playwright 실브라우저에 의존해 단위 테스트가 없다(Global Constraints 참고). 아래 수정을 적용하고 Task 4까지 마친 뒤 Manual Verification에서 실사이트로 확인한다.

- [ ] **Step 1: `scrape_posting_applicants` 수정**

`src/agent_selection/xfile_client.py`의 `scrape_posting_applicants` 함수를 아래 내용으로 교체:

```python
def scrape_posting_applicants(page: Page, posting_url: str) -> tuple[str, list[dict[str, str]]]:
    # 지원자 목록 화면은 표가 아닌 카드 형태라 DOM 스크래핑이 불가능함(실사이트 확인 결과).
    # 대신 "엑셀 다운로드" 버튼이 커스텀옵션까지 포함된 CSV를 제공해 이를 내려받아 파싱함
    page.goto(posting_url)
    page.wait_for_load_state("networkidle")

    # 공고 제목은 실사이트에서 이 클래스 조합의 div에만 들어있는 것을 확인함
    # (Tailwind 유틸리티 클래스 기반이라 사이트 스타일이 바뀌면 셀렉터가 깨질 수 있음)
    try:
        title = page.locator(".text-lg.font-semibold").first.inner_text().strip()
    except PlaywrightTimeoutError as exc:
        raise XfilePageError(f"공고 제목을 찾을 수 없습니다: {posting_url}") from exc

    try:
        with page.expect_download(timeout=30000) as download_info:
            page.get_by_text("엑셀 다운로드").click()
    except PlaywrightTimeoutError as exc:
        raise XfilePageError(f"지원자 목록 다운로드에 실패했습니다: {posting_url}") from exc

    download_path = download_info.value.path()
    # 브라우저가 저장한 파일이 BOM 포함 UTF-8 CSV라 utf-8-sig로 읽어 BOM을 제거
    csv_text = Path(download_path).read_text(encoding="utf-8-sig")

    reader = csv.DictReader(io.StringIO(csv_text))
    header_fields = reader.fieldnames or []
    missing = [label for label, _ in EXPECTED_COLUMNS if label not in header_fields]
    if missing:
        raise XfilePageError(
            f"예상 컬럼을 찾을 수 없습니다 {missing} (실제 헤더: {header_fields})"
        )

    rows: list[dict[str, str]] = []
    for raw_row in reader:
        if any(raw_row.get(label) is None for label, _ in EXPECTED_COLUMNS):
            logger.warning("행의 컬럼 수가 예상과 달라 스킵: %s", posting_url)
            continue
        rows.append({key: (raw_row[label] or "").strip() for label, key in EXPECTED_COLUMNS})

    return title, rows
```

- [ ] **Step 2: 커밋**

```bash
git add src/agent_selection/xfile_client.py
git commit -m "feat: 지원자 수집 시 공고 제목도 함께 추출"
```

---

### Task 3: output.py — 공고명 기준 집계

**Files:**
- Modify: `src/agent_selection/output.py`
- Modify: `tests/agent_selection/test_output.py`

**Interfaces:**
- Consumes: Task 1의 `Applicant` (이제 `posting_title: str` 필드를 가짐)
- Produces: `print_summary(applicants: list[Applicant]) -> None` (시그니처는 동일, 출력 내용만 변경)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_output.py` 전체를 아래 내용으로 교체:

```python
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
    participation_count="3",
    custom_option_3="기타",
    posting_url="https://a.example.com",
    posting_title="미화 공고",
)


def test_save_results_creates_json_and_csv(tmp_path: Path):
    json_path, csv_path = save_results(
        [SAMPLE_APPLICANT], tmp_path, timestamp="20260806_100000"
    )

    assert json_path == tmp_path / "20260806_100000.json"
    assert csv_path == tmp_path / "20260806_100000.csv"

    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved[0]["name"] == "홍길동"
    assert saved[0]["posting_title"] == "미화 공고"

    with csv_path.open(encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        row = next(reader)
        assert row["name"] == "홍길동"
        assert row["role_type"] == "A"


def test_save_results_handles_empty_list(tmp_path: Path):
    json_path, csv_path = save_results([], tmp_path, timestamp="20260806_100000")

    assert json.loads(json_path.read_text(encoding="utf-8")) == []
    assert csv_path.read_text(encoding="utf-8-sig") != ""


def test_print_summary_groups_by_posting_title(capsys):
    other_applicant = Applicant(
        no="2",
        name="김철수",
        phone="010-9999-0000",
        birth_date="1992-05-05",
        gender="남",
        applied_at="2026-08-02 11:00",
        status="합격",
        status_changed_at="2026-08-02 12:00",
        selected_schedule="",
        approved_schedule="",
        role_type="",
        participation_count="",
        custom_option_3="",
        posting_url="https://b.example.com",
        posting_title="다회용기 공고",
    )

    print_summary([SAMPLE_APPLICANT, other_applicant])
    captured = capsys.readouterr()

    assert "총 수집 지원자: 2명" in captured.out
    assert "미화 공고: 1명" in captured.out
    assert "다회용기 공고: 1명" in captured.out
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `pytest tests/agent_selection/test_output.py -v`
Expected: FAIL — `test_save_results_creates_json_and_csv`는 `posting_title` 키를 아직 못 찾아 실패, `test_print_summary_groups_by_posting_title`은 예전 출력 형식이라 문자열이 안 맞아 실패

- [ ] **Step 3: `print_summary` 수정**

`src/agent_selection/output.py`에서 import와 `print_summary`를 아래로 교체:

```python
from agent_selection.applicant_parser import Applicant
```

```python
def print_summary(applicants: list[Applicant]) -> None:
    print(f"총 수집 지원자: {len(applicants)}명")
    posting_titles = sorted({applicant.posting_title for applicant in applicants})
    for posting_title in posting_titles:
        count = sum(1 for applicant in applicants if applicant.posting_title == posting_title)
        print(f"  {posting_title}: {count}명")
    for applicant in applicants:
        print(f"  [{applicant.no}] {applicant.name} / {applicant.posting_title} / {applicant.status}")
```

(`save_results`는 `asdict` 직렬화라 필드 추가/타입 변경에 자동 대응되므로 수정 불필요)

- [ ] **Step 4: 테스트가 통과하는지 확인**

Run: `pytest tests/agent_selection/test_output.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/agent_selection/output.py tests/agent_selection/test_output.py
git commit -m "feat: 지원자 요약을 공고명 기준으로 집계"
```

---

### Task 4: main.py — 호출부 수정

**Files:**
- Modify: `src/agent_selection/main.py`

**Interfaces:**
- Consumes: Task 1의 `parse_applicant_rows(rows, posting_url, posting_title)`, Task 2의 `scrape_posting_applicants(page, posting_url) -> tuple[str, list[dict]]`
- Produces: `run() -> int` (시그니처 동일)

이 파일은 오케스트레이션 진입점이라 기존에도 전용 단위 테스트가 없다(수동 통합 테스트로 검증). Task 5까지 마친 뒤 Manual Verification에서 함께 확인한다.

- [ ] **Step 1: 호출부 수정**

`src/agent_selection/main.py`의 for 루프 부분을 아래로 교체:

```python
        for posting_url in config.posting_urls:
            try:
                posting_title, raw_rows = scrape_posting_applicants(page, posting_url)
            except XfilePageError as exc:
                logger.warning("공고 스킵: %s", exc)
                skipped_postings.append(posting_url)
                continue

            parsed = parse_applicant_rows(raw_rows, posting_url, posting_title)
            all_applicants.extend(parsed)
            # 페이지네이션으로 일부만 수집됐을 가능성을 운영자가 화면과 대조할 수 있도록 기록
            logger.info("공고 %s (%s): %d명 수집", posting_title, posting_url, len(raw_rows))
```

- [ ] **Step 2: 커밋**

```bash
git add src/agent_selection/main.py
git commit -m "feat: 공고 제목을 수집 파이프라인에 연결"
```

---

### Task 5: view.py — 공고 기준 필터/컬럼

**Files:**
- Modify: `src/agent_selection/view.py`
- Modify: `tests/agent_selection/test_view.py`

**Interfaces:**
- Consumes: Task 3에서 저장된 JSON(`posting_title` 키 포함)을 `load_applicants`로 읽은 `list[dict]`
- Produces: `render_html(applicants: list[dict], collected_at: str) -> str` (시그니처 동일, 출력 HTML 내용 변경)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_view.py` 전체를 아래 내용으로 교체:

```python
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
        "posting_title": "다회용기 공고",
        "role_type": "",
        "participation_count": "",
        "status": "합격",
        "applied_at": "2026-08-02 11:00",
    },
]


def test_render_html_includes_applicant_values():
    html = render_html(SAMPLE_ROWS, "2026-08-10 14:30:00")

    assert "홍길동" in html
    assert "010-1234-5678" in html
    assert "총 2명" in html
    assert "2026-08-10 14:30:00" in html


def test_render_html_includes_posting_filter_buttons():
    html = render_html(SAMPLE_ROWS, "2026-08-10 14:30:00")

    assert 'data-posting="미화 공고"' in html
    assert 'data-posting="다회용기 공고"' in html
    assert 'data-posting="ALL"' in html


def test_render_html_escapes_posting_title_html():
    rows = [{**SAMPLE_ROWS[0], "posting_title": '<script>alert(1)</script>"'}]

    html = render_html(rows, "2026-08-10 14:30:00")

    assert "<script>alert(1)</script>" not in html


def test_render_html_handles_empty_applicant_list():
    html = render_html([], "2026-08-10 14:30:00")

    assert "총 0명" in html


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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `pytest tests/agent_selection/test_view.py -v`
Expected: FAIL — `test_render_html_includes_posting_filter_buttons`, `test_render_html_escapes_posting_title_html` 등이 `data-posting` 속성을 못 찾아 실패 (아직 `data-role` 기반이므로)

- [ ] **Step 3: `view.py` 수정**

`src/agent_selection/view.py` 전체를 아래 내용으로 교체:

```python
from __future__ import annotations

import html
import json
import logging
import sys
import webbrowser
from pathlib import Path
from string import Template

from agent_selection.config import ConfigError, load_config

logger = logging.getLogger(__name__)


class ViewError(Exception):
    """결과 파일을 읽지 못했을 때 발생"""


def find_latest_result(output_dir: Path) -> Path | None:
    # 파일명이 YYYYMMDD_HHMMSS 형식이라 문자열 정렬 = 시간순 정렬
    json_files = sorted(output_dir.glob("*.json"))
    return json_files[-1] if json_files else None


def load_applicants(json_path: Path) -> list[dict]:
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ViewError(f"결과 파일을 읽을 수 없습니다: {json_path} ({exc})") from exc


VIEW_COLUMNS: tuple[str, ...] = (
    "name",
    "phone",
    "posting_title",
    "role_type",
    "participation_count",
    "status",
    "applied_at",
)

VIEW_COLUMN_LABELS: dict[str, str] = {
    "name": "이름",
    "phone": "전화번호",
    "posting_title": "공고명",
    "role_type": "역할타입",
    "participation_count": "참여횟수",
    "status": "지원상태",
    "applied_at": "지원일시",
}

# $ 치환만 처리하므로 CSS/JS의 중괄호를 이스케이프할 필요가 없음 (f-string 대비 안전)
_PAGE_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>지원자 목록</title>
<style>
  body { font-family: -apple-system, sans-serif; margin: 2rem; }
  .summary { margin-bottom: 1rem; color: #555; }
  .controls { margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
  .controls button { padding: 0.4rem 0.8rem; border: 1px solid #ccc; background: #fff; border-radius: 4px; cursor: pointer; }
  .controls button.active { background: #333; color: #fff; }
  input[type=search] { padding: 0.4rem; border: 1px solid #ccc; border-radius: 4px; flex: 1; max-width: 240px; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
  th { background: #f5f5f5; }
</style>
</head>
<body>
<h1>지원자 목록</h1>
<div class="summary">총 $total명 · 수집 시각 $collected_at</div>
<div class="controls">
  $posting_buttons
  <input type="search" id="search" placeholder="이름 또는 전화번호 검색">
</div>
<table id="table">
  <thead><tr>$table_headers</tr></thead>
  <tbody></tbody>
</table>
<script>
const DATA = $data_json;
const COLUMNS = $columns_json;
const tbody = document.querySelector("#table tbody");
let activePosting = "ALL";
let query = "";

function render() {
  tbody.innerHTML = "";
  DATA.filter(row => (activePosting === "ALL" || row.posting_title === activePosting))
      .filter(row => query === "" || row.name.includes(query) || row.phone.includes(query))
      .forEach(row => {
        const tr = document.createElement("tr");
        COLUMNS.forEach(col => {
          const td = document.createElement("td");
          td.textContent = row[col.key];
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
}

document.querySelectorAll(".controls button[data-posting]").forEach(btn => {
  btn.addEventListener("click", () => {
    activePosting = btn.dataset.posting;
    document.querySelectorAll(".controls button[data-posting]").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    render();
  });
});

document.querySelector("#search").addEventListener("input", (event) => {
  query = event.target.value.trim();
  render();
});

render();
</script>
</body>
</html>
""")

_EMPTY_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><title>지원자 목록</title></head>
<body style="font-family: -apple-system, sans-serif; margin: 2rem;">
<h1>아직 수집된 데이터가 없습니다</h1>
<p>먼저 <code>python -m agent_selection.main</code>을 실행해주세요.</p>
</body>
</html>
"""


def _safe_json(value: object) -> str:
    # 지원자 이름 등 외부 입력값에 "</script>"가 들어있으면 <script> 블록이 조기 종료되므로
    # "<"를 유니코드 이스케이프로 바꿔 HTML 파서가 스크립트 태그로 오인하지 않게 함
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def render_html(applicants: list[dict], collected_at: str) -> str:
    rows = [{col: applicant.get(col, "") for col in VIEW_COLUMNS} for applicant in applicants]

    # 공고명은 엑스파일 관리자가 입력하는 자유 텍스트라 HTML 특수문자가 섞일 수 있어 이스케이프 필요
    posting_titles = sorted(
        {
            applicant.get("posting_title", "")
            for applicant in applicants
            if applicant.get("posting_title")
        }
    )
    posting_buttons = '<button data-posting="ALL" class="active">전체</button>' + "".join(
        f'<button data-posting="{html.escape(title)}">{html.escape(title)}</button>'
        for title in posting_titles
    )
    table_headers = "".join(f"<th>{VIEW_COLUMN_LABELS[col]}</th>" for col in VIEW_COLUMNS)
    columns = [{"key": col, "label": VIEW_COLUMN_LABELS[col]} for col in VIEW_COLUMNS]

    return _PAGE_TEMPLATE.substitute(
        total=len(applicants),
        collected_at=collected_at,
        posting_buttons=posting_buttons,
        table_headers=table_headers,
        data_json=_safe_json(rows),
        columns_json=_safe_json(columns),
    )


def render_empty_html() -> str:
    return _EMPTY_TEMPLATE


def format_collected_at(json_path: Path) -> str:
    # save_results가 만드는 고정 포맷 "YYYYMMDD_HHMMSS"을 사람이 읽기 좋게 변환
    ts = json_path.stem
    return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}:{ts[13:15]}"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    try:
        config = load_config()
    except ConfigError as exc:
        logger.error("설정 오류: %s", exc)
        return 1

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    latest = find_latest_result(output_dir)

    if latest is None:
        html_content = render_empty_html()
    else:
        try:
            applicants = load_applicants(latest)
        except ViewError as exc:
            logger.error("%s", exc)
            return 1
        html_content = render_html(applicants, format_collected_at(latest))

    view_path = output_dir / "view.html"
    view_path.write_text(html_content, encoding="utf-8")
    # f-string으로 직접 조립하면 경로에 공백/한글이 있을 때 URL이 깨짐 (as_uri가 퍼센트 인코딩 처리)
    webbrowser.open(view_path.resolve().as_uri())
    logger.info("결과 화면 생성 완료: %s", view_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

(`main()` 내부의 로컬 변수명을 `html`에서 `html_content`로 바꾼 것에 주의 — 모듈 상단에 `import html`을 추가했으므로 지역변수가 모듈명을 가리면 안 됨)

- [ ] **Step 4: 테스트가 통과하는지 확인**

Run: `pytest tests/agent_selection/test_view.py -v`
Expected: PASS (15 passed)

전체 스위트도 확인:

Run: `pytest -v`
Expected: PASS, 실패 0건 (`test_config.py`, `test_column_keys.py`는 이번 변경과 무관하니 그대로 통과해야 함)

- [ ] **Step 5: 커밋**

```bash
git add src/agent_selection/view.py tests/agent_selection/test_view.py
git commit -m "feat: 결과 화면을 공고 기준 필터/컬럼으로 전환"
```

---

## Manual Verification (구현 완료 후 실사이트로 확인)

1. `.venv/bin/python -m agent_selection.main` 실행 — 로그에 공고 제목이 함께 찍히는지 확인 (`공고 <제목> (<URL>): N명 수집`)
2. 콘솔 요약이 "역할타입별"이 아니라 "공고명별"로 나오는지 확인
3. `.env`의 `XFILE_POSTING_URLS`에 서로 다른 공고 URL을 콤마로 2개 이상 넣고 다시 실행 — 여러 공고가 한 번에 수집되는지 확인
4. `.venv/bin/python -m agent_selection.view` 실행 — 표에 "공고명" 컬럼이 보이는지, 상단 필터 버튼이 실제 공고 개수만큼 생기는지, 버튼을 눌러 걸러지는지 확인
5. 커스텀옵션(역할타입/참여횟수)이 비어있는 공고와 값이 있는 공고를 섞어서 수집해보고, 빈 값이 화면에서 에러 없이 빈칸으로 나오는지 확인
