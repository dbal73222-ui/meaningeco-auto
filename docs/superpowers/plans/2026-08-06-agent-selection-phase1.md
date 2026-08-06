# 요원 선발 자동화 Phase 1 (엑스파일 로그인 + 지원자 수집) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 엑스파일 관리자 페이지에 로그인해 지정된 공고들의 지원자 데이터를 수집하고, 콘솔 출력 + JSON/CSV 파일로 저장하는 독립 실행 스크립트를 만든다.

**Architecture:** `config` → `xfile_client`(Playwright 로그인/스크래핑) → `applicant_parser`(원시 행 → 구조화 데이터) → `output`(저장/출력) → `main`(오케스트레이션). 각 모듈은 단일 책임을 가지며, 실사이트 의존이 없는 `config`/`applicant_parser`/`output`은 TDD로 구현하고, 실사이트 의존인 `xfile_client`/`main`은 수동 통합 테스트로 검증한다.

**Tech Stack:** Python, Playwright(sync API), python-dotenv, pytest

## Global Constraints

- 불변성 유지 — 뮤테이션 금지, 데이터 클래스는 `frozen=True`로 선언
- 환경변수는 `.env`로 관리, 하드코딩 금지
- 주석은 한국어로 (WHY만, 자명한 내용은 주석 없이)
- 파일 200~400줄, 최대 800줄
- 함수 50줄 이하, 넘으면 분리
- 타입 힌트 필수, 함수형 스타일 선호
- 로그인은 매 실행마다 새로 수행 (세션 저장/재사용 금지) — [스펙](../specs/2026-08-06-agent-selection-phase1-design.md) 결정 사항
- 공고 URL은 `.env`(`XFILE_POSTING_URLS`)에 직접 나열, 자동 발견 로직 없음 — 스펙 결정 사항

---

### Task 1: 프로젝트 스캐폴딩 + `config.py` (환경설정 로드)

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `pyproject.toml`
- Create: `src/agent_selection/__init__.py`
- Create: `src/agent_selection/config.py`
- Create: `tests/agent_selection/__init__.py`
- Create: `tests/agent_selection/test_config.py`

**Interfaces:**
- Produces: `Config` 데이터클래스 (`login_url: str`, `username: str`, `password: str`, `posting_urls: tuple[str, ...]`, `headless: bool`), `load_config(env_path: str | None = None) -> Config`, `ConfigError` 예외 — 이후 모든 태스크가 사용

- [ ] **Step 1: 스캐폴딩 파일 작성**

`requirements.txt`:
```
playwright==1.50.0
python-dotenv==1.0.1
pytest==8.3.3
```

> **환경 노트 (Task 1 리뷰 중 확정):** 이 머신은 macOS 12.7.6이라 Playwright 최신 버전(1.6x)은 `playwright install chromium`이 "does not support chromium on mac12"로 거부한다. `playwright==1.47.0`이 의존하는 `greenlet==3.0.3`은 Python 3.13/3.14 모두에서 사전빌드 휠이 없어 컴파일 실패한다. 실측 검증 결과 `playwright==1.50.0`(greenlet 3.5.4 사전빌드 휠 사용)이 Python 3.13에서 빌드되고 macOS 12에서 Chromium 다운로드·실행까지 정상 동작하는 유일한 조합이었다. 반드시 `playwright==1.50.0`을 사용할 것.

`.env.example`:
```
XFILE_LOGIN_URL=https://admin.xfile.example.com/login
XFILE_USERNAME=
XFILE_PASSWORD=
XFILE_POSTING_URLS=https://admin.xfile.example.com/postings/123,https://admin.xfile.example.com/postings/456
XFILE_HEADLESS=true
```

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

`src/agent_selection/__init__.py`: 빈 파일

`tests/agent_selection/__init__.py`: 빈 파일

- [ ] **Step 2: 의존성 설치**

Run: `cd /Users/apple/meaningeco-automation && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && playwright install chromium`

- [ ] **Step 3: 실패하는 테스트 작성**

`tests/agent_selection/test_config.py`:
```python
import pytest

from agent_selection.config import ConfigError, load_config


def _write_env(tmp_path, content: str):
    env_file = tmp_path / ".env"
    env_file.write_text(content, encoding="utf-8")
    return env_file


def test_load_config_success(tmp_path, monkeypatch):
    for key in (
        "XFILE_LOGIN_URL",
        "XFILE_USERNAME",
        "XFILE_PASSWORD",
        "XFILE_POSTING_URLS",
        "XFILE_HEADLESS",
    ):
        monkeypatch.delenv(key, raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_USERNAME=tester\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com,https://b.example.com\n"
        "XFILE_HEADLESS=false\n",
    )

    config = load_config(env_path=str(env_file))

    assert config.login_url == "https://admin.example.com/login"
    assert config.username == "tester"
    assert config.password == "secret"
    assert config.posting_urls == ("https://a.example.com", "https://b.example.com")
    assert config.headless is False


def test_load_config_missing_username_raises(tmp_path, monkeypatch):
    for key in (
        "XFILE_LOGIN_URL",
        "XFILE_USERNAME",
        "XFILE_PASSWORD",
        "XFILE_POSTING_URLS",
    ):
        monkeypatch.delenv(key, raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com\n",
    )

    with pytest.raises(ConfigError, match="XFILE_USERNAME"):
        load_config(env_path=str(env_file))
```

- [ ] **Step 4: 테스트 실행해서 실패 확인**

Run: `pytest tests/agent_selection/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_selection.config'`

- [ ] **Step 5: `config.py` 구현**

`src/agent_selection/config.py`:
```python
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(Exception):
    """설정값 누락 또는 형식 오류"""


@dataclass(frozen=True)
class Config:
    login_url: str
    username: str
    password: str
    posting_urls: tuple[str, ...]
    headless: bool


def load_config(env_path: str | None = None) -> Config:
    load_dotenv(dotenv_path=env_path)

    login_url = os.getenv("XFILE_LOGIN_URL", "").strip()
    username = os.getenv("XFILE_USERNAME", "").strip()
    password = os.getenv("XFILE_PASSWORD", "").strip()
    posting_urls_raw = os.getenv("XFILE_POSTING_URLS", "").strip()
    headless_raw = os.getenv("XFILE_HEADLESS", "true").strip().lower()

    if not login_url:
        raise ConfigError("XFILE_LOGIN_URL이 설정되지 않았습니다.")
    if not username:
        raise ConfigError("XFILE_USERNAME이 설정되지 않았습니다.")
    if not password:
        raise ConfigError("XFILE_PASSWORD가 설정되지 않았습니다.")
    if not posting_urls_raw:
        raise ConfigError("XFILE_POSTING_URLS가 설정되지 않았습니다.")

    posting_urls = tuple(
        url.strip() for url in posting_urls_raw.split(",") if url.strip()
    )

    return Config(
        login_url=login_url,
        username=username,
        password=password,
        posting_urls=posting_urls,
        headless=headless_raw != "false",
    )
```

- [ ] **Step 6: 테스트 실행해서 통과 확인**

Run: `pytest tests/agent_selection/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: 커밋**

```bash
git add requirements.txt .env.example pyproject.toml src/agent_selection/__init__.py src/agent_selection/config.py tests/agent_selection/__init__.py tests/agent_selection/test_config.py
git commit -m "feat: 프로젝트 스캐폴딩 및 환경설정 로더 추가"
```

---

### Task 2: `applicant_parser.py` (지원자 행 파싱)

**Files:**
- Create: `src/agent_selection/applicant_parser.py`
- Create: `tests/agent_selection/test_applicant_parser.py`

**Interfaces:**
- Consumes: 없음 (독립 모듈)
- Produces: `Applicant` 데이터클래스 (`no, name, phone, birth_date, gender, applied_at, status, status_changed_at, selected_schedule, approved_schedule, role_type, participation_count, custom_option_3, posting_url`), `parse_applicant_row(row: dict[str, str], posting_url: str) -> Applicant`, `parse_applicant_rows(rows: list[dict[str, str]], posting_url: str) -> list[Applicant]`, `ApplicantParseError` — Task 3(`output.py`), Task 5(`main.py`)가 사용

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_applicant_parser.py`:
```python
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
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `pytest tests/agent_selection/test_applicant_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_selection.applicant_parser'`

- [ ] **Step 3: `applicant_parser.py` 구현**

`src/agent_selection/applicant_parser.py`:
```python
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

VALID_ROLE_TYPES = {"A", "B", "C"}


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
```

- [ ] **Step 4: 테스트 실행해서 통과 확인**

Run: `pytest tests/agent_selection/test_applicant_parser.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/agent_selection/applicant_parser.py tests/agent_selection/test_applicant_parser.py
git commit -m "feat: 지원자 행 파싱 로직 추가"
```

---

### Task 3: `output.py` (결과 저장 + 콘솔 출력)

**Files:**
- Create: `src/agent_selection/output.py`
- Create: `tests/agent_selection/test_output.py`

**Interfaces:**
- Consumes: `Applicant` (Task 2)
- Produces: `save_results(applicants: list[Applicant], output_dir: Path, timestamp: str | None = None) -> tuple[Path, Path]`, `print_summary(applicants: list[Applicant]) -> None` — Task 5(`main.py`)가 사용

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_output.py`:
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
```

- [ ] **Step 2: 테스트 실행해서 실패 확인**

Run: `pytest tests/agent_selection/test_output.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_selection.output'`

- [ ] **Step 3: `output.py` 구현**

`src/agent_selection/output.py`:
```python
from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from agent_selection.applicant_parser import Applicant

ROLE_TYPES = ("A", "B", "C")


def save_results(
    applicants: list[Applicant],
    output_dir: Path,
    timestamp: str | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = output_dir / f"{ts}.json"
    csv_path = output_dir / f"{ts}.csv"

    rows = [asdict(applicant) for applicant in applicants]
    fieldnames = list(rows[0].keys()) if rows else list(Applicant.__dataclass_fields__.keys())

    json_path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with csv_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return json_path, csv_path


def print_summary(applicants: list[Applicant]) -> None:
    print(f"총 수집 지원자: {len(applicants)}명")
    for role_type in ROLE_TYPES:
        count = sum(1 for applicant in applicants if applicant.role_type == role_type)
        print(f"  {role_type}타입: {count}명")
    for applicant in applicants:
        print(
            f"  [{applicant.no}] {applicant.name} / {applicant.role_type}타입 "
            f"/ 참여 {applicant.participation_count}회 / {applicant.status}"
        )
```

- [ ] **Step 4: 테스트 실행해서 통과 확인**

Run: `pytest tests/agent_selection/test_output.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/agent_selection/output.py tests/agent_selection/test_output.py
git commit -m "feat: 지원자 결과 저장/출력 기능 추가"
```

---

### Task 4: `xfile_client.py` (Playwright 로그인 + 지원자 테이블 스크래핑)

**Files:**
- Create: `src/agent_selection/xfile_client.py`

**Interfaces:**
- Consumes: `playwright.sync_api.Page` (Playwright가 제공)
- Produces: `login(page: Page, login_url: str, username: str, password: str) -> None`, `scrape_posting_applicants(page: Page, posting_url: str) -> list[dict[str, str]]`, `XfileLoginError`, `XfilePageError` — Task 5(`main.py`)가 사용

**중요 — 실사이트 셀렉터 가정:** 소스코드 접근 없이 어드민 화면만 볼 수 있어, 아래 구현은 "아이디"/"비밀번호" 라벨이 붙은 입력창과 "로그인" 텍스트 버튼, `<table><thead><tbody>` 구조를 가정한다. 실제 화면과 다르면 Step 2(수동 통합 테스트)에서 즉시 드러나므로, 그때 실제 마크업에 맞춰 셀렉터만 조정한다. 이 모듈은 실사이트 의존이라 자동화된 단위 테스트를 작성하지 않는다 (스펙의 에러 처리/테스트 전략 결정 사항).

- [ ] **Step 1: `xfile_client.py` 구현**

`src/agent_selection/xfile_client.py`:
```python
from __future__ import annotations

from playwright.sync_api import Page

EXPECTED_COLUMNS: list[tuple[str, str]] = [
    ("no.", "no"),
    ("실명", "name"),
    ("전화번호", "phone"),
    ("생년월일", "birth_date"),
    ("성별", "gender"),
    ("지원일시", "applied_at"),
    ("지원상태", "status"),
    ("상태변경일시", "status_changed_at"),
    ("선택일정", "selected_schedule"),
    ("합격일정", "approved_schedule"),
    ("커스텀옵션1", "custom_option_1"),
    ("커스텀옵션2", "custom_option_2"),
    ("커스텀옵션3", "custom_option_3"),
]


class XfileLoginError(Exception):
    """엑스파일 로그인 실패"""


class XfilePageError(Exception):
    """엑스파일 공고 페이지 접근/파싱 실패"""


def login(page: Page, login_url: str, username: str, password: str) -> None:
    page.goto(login_url)
    page.get_by_label("아이디").fill(username)
    page.get_by_label("비밀번호").fill(password)
    page.get_by_role("button", name="로그인").click()

    error_message = page.get_by_text("아이디 또는 비밀번호가 일치하지 않습니다")
    if error_message.count() > 0:
        raise XfileLoginError("로그인 실패: 아이디 또는 비밀번호를 확인하세요.")


def scrape_posting_applicants(page: Page, posting_url: str) -> list[dict[str, str]]:
    page.goto(posting_url)

    table = page.locator("table")
    if table.count() == 0:
        raise XfilePageError(f"지원자 테이블을 찾을 수 없습니다: {posting_url}")

    header_cells = table.locator("thead th").all_inner_texts()
    header_index = {text.strip(): idx for idx, text in enumerate(header_cells)}

    missing = [label for label, _ in EXPECTED_COLUMNS if label not in header_index]
    if missing:
        raise XfilePageError(
            f"예상 컬럼을 찾을 수 없습니다 {missing} (실제 헤더: {header_cells})"
        )

    rows: list[dict[str, str]] = []
    row_locators = table.locator("tbody tr")
    for i in range(row_locators.count()):
        cells = row_locators.nth(i).locator("td").all_inner_texts()
        row = {key: cells[header_index[label]].strip() for label, key in EXPECTED_COLUMNS}
        rows.append(row)

    return rows
```

- [ ] **Step 2: 커밋**

```bash
git add src/agent_selection/xfile_client.py
git commit -m "feat: 엑스파일 로그인 및 지원자 테이블 스크래핑 추가"
```

---

### Task 5: `main.py` (오케스트레이션) + 실사이트 수동 통합 테스트

**Files:**
- Create: `src/agent_selection/main.py`

**Interfaces:**
- Consumes: `load_config`/`Config`/`ConfigError` (Task 1), `login`/`scrape_posting_applicants`/`XfileLoginError`/`XfilePageError` (Task 4), `parse_applicant_rows` (Task 2), `save_results`/`print_summary` (Task 3)
- Produces: `run() -> int` (0=성공, 1=설정/로그인 실패) — CLI 진입점

- [ ] **Step 1: `main.py` 구현**

`src/agent_selection/main.py`:
```python
from __future__ import annotations

import logging
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from agent_selection.applicant_parser import parse_applicant_rows
from agent_selection.config import ConfigError, load_config
from agent_selection.output import print_summary, save_results
from agent_selection.xfile_client import (
    XfileLoginError,
    XfilePageError,
    login,
    scrape_posting_applicants,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        logger.error("설정 오류: %s", exc)
        return 1

    all_applicants = []
    skipped_postings: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=config.headless)
        page = browser.new_page()

        try:
            login(page, config.login_url, config.username, config.password)
        except XfileLoginError as exc:
            logger.error("로그인 실패: %s", exc)
            browser.close()
            return 1

        for posting_url in config.posting_urls:
            try:
                raw_rows = scrape_posting_applicants(page, posting_url)
            except XfilePageError as exc:
                logger.warning("공고 스킵: %s", exc)
                skipped_postings.append(posting_url)
                continue

            all_applicants.extend(parse_applicant_rows(raw_rows, posting_url))

        browser.close()

    print_summary(all_applicants)
    if skipped_postings:
        print(f"스킵된 공고: {len(skipped_postings)}건")
        for url in skipped_postings:
            print(f"  - {url}")

    json_path, csv_path = save_results(all_applicants, Path("output"))
    print(f"저장 완료: {json_path}, {csv_path}")

    return 0


if __name__ == "__main__":
    sys.exit(run())
```

- [ ] **Step 2: 자동화 단위 테스트 실행 (회귀 확인)**

Run: `pytest -v`
Expected: PASS (앞선 Task 1~3의 9개 테스트 모두 통과, `xfile_client`/`main`은 단위 테스트 없음)

- [ ] **Step 3: 커밋**

```bash
git add src/agent_selection/main.py
git commit -m "feat: 전체 흐름 오케스트레이션 진입점 추가"
```

- [ ] **Step 4: 실사이트 대상 수동 통합 테스트**

1. `.env.example`을 `.env`로 복사하고 실제 `XFILE_LOGIN_URL`, `XFILE_USERNAME`, `XFILE_PASSWORD`, 테스트할 공고 1~2개의 `XFILE_POSTING_URLS`를 입력한다. 처음에는 `XFILE_HEADLESS=false`로 설정해 브라우저 동작을 눈으로 확인한다.
2. Run: `cd /Users/apple/meaningeco-automation && source .venv/bin/activate && python -m agent_selection.main`
3. 콘솔에 지원자 목록과 역할타입별 집계가 출력되는지 확인한다.
4. `output/` 디렉터리에 JSON/CSV 파일이 생성되고, 값이 실제 엑스파일 화면과 일치하는지 확인한다.
5. 로그인 셀렉터(`get_by_label("아이디")` 등)나 테이블 헤더 매칭이 실패하면, 에러 로그에 실제 헤더 목록이 함께 출력되므로 그 값을 보고 `xfile_client.py`의 셀렉터/헤더 라벨을 실제 화면에 맞게 수정한다.

---

## Self-Review 결과

- **스펙 커버리지**: 로그인(Task 4) · 공고별 순회(Task 5) · 테이블 파싱(Task 2) · 역할타입/참여이력 매핑(Task 2) · 콘솔+JSON/CSV 저장(Task 3) · 로그인 실패시 즉시 종료(Task 4/5) · 공고 단위 스킵(Task 5) · 행 단위 스킵(Task 2) · 매 실행 재로그인(Task 5, 세션 저장 없음) · `.env` 공고 URL 목록(Task 1) · 계정정보 `.env`/`.gitignore` 관리(Task 1, 기존 `.gitignore`) — 스펙 전 항목 커버됨.
- **플레이스홀더 스캔**: TBD/TODO 없음, 모든 스텝에 실행 가능한 코드 포함.
- **타입 일관성**: `Applicant`(Task 2) 필드명이 `output.py`(Task 3)의 `asdict()` 사용과 `xfile_client.py`(Task 4)의 `EXPECTED_COLUMNS` 키(`no, name, phone, birth_date, gender, applied_at, status, status_changed_at, selected_schedule, approved_schedule, custom_option_1/2/3`)와 `applicant_parser.py`의 `row.get(...)` 키가 일치함을 확인.
