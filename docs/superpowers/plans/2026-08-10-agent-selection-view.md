# 지원자 데이터 보기 화면 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python -m agent_selection.view` 실행 시 가장 최근 수집 결과를 표로 보여주는 정적 HTML을 생성하고 브라우저로 자동 오픈한다.

**Architecture:** 신규 모듈 `agent_selection/view.py` 하나에 데이터 로딩(`find_latest_result`, `load_applicants`) → HTML 렌더링(`render_html`, `render_empty_html`) → 진입점(`main`)을 구현한다. 기존 `main.py`(수집) 로직은 건드리지 않는다.

**Tech Stack:** 표준 라이브러리만 사용 — `json`, `pathlib`, `string.Template`, `webbrowser`, `logging`. 신규 외부 의존성 없음.

## Global Constraints

- 불변성 유지 — 뮤테이션 금지 (프로젝트 CLAUDE.md)
- 환경변수는 `.env`로 관리, 하드코딩 금지 (프로젝트 CLAUDE.md) — 출력 경로는 기존 `Config.output_dir`(`XFILE_OUTPUT_DIR`)을 그대로 재사용한다
- 주석은 한국어로, WHY만 작성 (프로젝트 CLAUDE.md)
- 파일 200-400줄, 최대 800줄 / 함수 50줄 이하 (프로젝트 CLAUDE.md)
- 타입 힌트 필수, `const` 우선(파이썬에서는 `@dataclass(frozen=True)`/불변 자료구조 우선), 함수형 스타일 선호 (프로젝트 CLAUDE.md)
- Python 3.13 가상환경 사용 (`docs/superpowers/specs/2026-08-06-agent-selection-phase1-design.md` 참고 — 3.14는 playwright 빌드가 깨짐. 이 기능은 playwright를 쓰지 않지만 동일 venv에서 실행되므로 버전 고정을 유지한다)
- 읽기 전용 원칙 유지 — 이 화면에서 어떤 클릭도 승인/거절 등 엑스파일 사이트에 대한 쓰기 동작을 일으키지 않는다 (`docs/superpowers/specs/2026-08-10-agent-selection-view-design.md`)
- `output/` 결과 파일 포맷은 기존 `save_results`(`src/agent_selection/output.py`)가 만드는 `{YYYYMMDD_HHMMSS}.json` 그대로를 입력으로 삼는다 — 새 포맷을 만들지 않는다

---

## File Structure

- Create: `src/agent_selection/view.py` — 데이터 로딩 + HTML 렌더링 + 진입점, 단일 파일 (약 150줄 예상, 400줄 한도 내)
- Create: `tests/agent_selection/test_view.py` — 위 모듈의 단위 테스트
- Modify: `README.md` — "결과 보기" 사용법 섹션 추가

## 기존 인터페이스 (참고용, 변경 없음)

```python
# src/agent_selection/config.py
@dataclass(frozen=True)
class Config:
    login_url: str
    username: str
    password: str
    posting_urls: tuple[str, ...]
    headless: bool
    output_dir: str

def load_config(env_path: str | None = None) -> Config: ...
class ConfigError(Exception): ...

# src/agent_selection/applicant_parser.py
ROLE_TYPES: tuple[str, ...] = ("A", "B", "C")

# src/agent_selection/output.py
def save_results(
    applicants: list[Applicant], output_dir: Path, timestamp: str | None = None
) -> tuple[Path, Path]: ...
# json_path = output_dir / f"{ts}.json" where ts = "YYYYMMDD_HHMMSS"
# JSON 내용은 list[dict] — 각 dict는 Applicant의 asdict() (name, phone, role_type,
# participation_count, status, applied_at 등 14개 키 포함)
```

---

### Task 1: 최신 결과 파일 찾기 + 데이터 로드

**Files:**
- Create: `src/agent_selection/view.py`
- Test: `tests/agent_selection/test_view.py`

**Interfaces:**
- Consumes: `agent_selection.output.save_results` (테스트 픽스처 생성용), `pathlib.Path`
- Produces:
  - `class ViewError(Exception)` — 결과 파일을 읽지 못했을 때 발생
  - `find_latest_result(output_dir: Path) -> Path | None`
  - `load_applicants(json_path: Path) -> list[dict]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_view.py` 파일을 새로 만든다:

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `pytest tests/agent_selection/test_view.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_selection.view'`

- [ ] **Step 3: 최소 구현 작성**

`src/agent_selection/view.py` 새로 생성:

```python
from __future__ import annotations

import json
import logging
from pathlib import Path

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
```

- [ ] **Step 4: 테스트가 통과하는지 확인**

Run: `pytest tests/agent_selection/test_view.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/agent_selection/view.py tests/agent_selection/test_view.py
git commit -m "feat: 최신 수집 결과 파일 탐색 및 로드 기능 추가"
```

---

### Task 2: HTML 렌더링

**Files:**
- Modify: `src/agent_selection/view.py`
- Test: `tests/agent_selection/test_view.py`

**Interfaces:**
- Consumes: `agent_selection.applicant_parser.ROLE_TYPES`, Task 1의 `load_applicants` 반환 형식(`list[dict]`, 각 dict가 `name`/`phone`/`role_type`/`participation_count`/`status`/`applied_at` 키를 가짐)
- Produces:
  - `VIEW_COLUMNS: tuple[str, ...]`, `VIEW_COLUMN_LABELS: dict[str, str]`
  - `render_html(applicants: list[dict], collected_at: str) -> str`
  - `render_empty_html() -> str`
  - `format_collected_at(json_path: Path) -> str` (Task 3의 `main()`이 사용)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_view.py`에 이어서 추가:

```python
from agent_selection.view import (
    format_collected_at,
    render_empty_html,
    render_html,
)


SAMPLE_ROWS = [
    {
        "no": "1",
        "name": "홍길동",
        "phone": "010-1234-5678",
        "role_type": "A",
        "participation_count": 3,
        "status": "대기",
        "applied_at": "2026-08-01 10:00",
    },
    {
        "no": "2",
        "name": "김철수",
        "phone": "010-9999-0000",
        "role_type": "B",
        "participation_count": 0,
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


def test_render_html_includes_role_type_filter_buttons():
    html = render_html(SAMPLE_ROWS, "2026-08-10 14:30:00")

    assert 'data-role="A"' in html
    assert 'data-role="B"' in html
    assert 'data-role="C"' in html


def test_render_html_handles_empty_applicant_list():
    html = render_html([], "2026-08-10 14:30:00")

    assert "총 0명" in html


def test_render_empty_html_shows_guidance_message():
    html = render_empty_html()

    assert "아직 수집된 데이터가 없습니다" in html
    assert "agent_selection.main" in html


def test_format_collected_at_formats_timestamp_stem(tmp_path: Path):
    json_path = tmp_path / "20260810_143000.json"

    assert format_collected_at(json_path) == "2026-08-10 14:30:00"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `pytest tests/agent_selection/test_view.py -v`
Expected: FAIL — `ImportError: cannot import name 'render_html' from 'agent_selection.view'`

- [ ] **Step 3: 최소 구현 작성**

`src/agent_selection/view.py`에 이어서 추가 (Task 1의 import 블록에 `from string import Template`를 더한다):

```python
from string import Template

from agent_selection.applicant_parser import ROLE_TYPES

VIEW_COLUMNS: tuple[str, ...] = (
    "name",
    "phone",
    "role_type",
    "participation_count",
    "status",
    "applied_at",
)

VIEW_COLUMN_LABELS: dict[str, str] = {
    "name": "이름",
    "phone": "전화번호",
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
  .controls { margin-bottom: 1rem; display: flex; gap: 0.5rem; align-items: center; }
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
  $role_buttons
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
let activeRole = "ALL";
let query = "";

function render() {
  tbody.innerHTML = "";
  DATA.filter(row => (activeRole === "ALL" || row.role_type === activeRole))
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

document.querySelectorAll(".controls button[data-role]").forEach(btn => {
  btn.addEventListener("click", () => {
    activeRole = btn.dataset.role;
    document.querySelectorAll(".controls button[data-role]").forEach(b => b.classList.remove("active"));
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


def render_html(applicants: list[dict], collected_at: str) -> str:
    rows = [{col: applicant.get(col, "") for col in VIEW_COLUMNS} for applicant in applicants]
    role_buttons = '<button data-role="ALL" class="active">전체</button>' + "".join(
        f'<button data-role="{role}">{role}</button>' for role in ROLE_TYPES
    )
    table_headers = "".join(f"<th>{VIEW_COLUMN_LABELS[col]}</th>" for col in VIEW_COLUMNS)
    columns = [{"key": col, "label": VIEW_COLUMN_LABELS[col]} for col in VIEW_COLUMNS]

    return _PAGE_TEMPLATE.substitute(
        total=len(applicants),
        collected_at=collected_at,
        role_buttons=role_buttons,
        table_headers=table_headers,
        data_json=json.dumps(rows, ensure_ascii=False),
        columns_json=json.dumps(columns, ensure_ascii=False),
    )


def render_empty_html() -> str:
    return _EMPTY_TEMPLATE


def format_collected_at(json_path: Path) -> str:
    # save_results가 만드는 고정 포맷 "YYYYMMDD_HHMMSS"을 사람이 읽기 좋게 변환
    ts = json_path.stem
    return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:13]}:{ts[13:15]}"
```

- [ ] **Step 4: 테스트가 통과하는지 확인**

Run: `pytest tests/agent_selection/test_view.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: 커밋**

```bash
git add src/agent_selection/view.py tests/agent_selection/test_view.py
git commit -m "feat: 지원자 목록 HTML 렌더링 추가 (필터/검색 포함)"
```

---

### Task 3: 진입점 연결 + README 업데이트

**Files:**
- Modify: `src/agent_selection/view.py`
- Test: `tests/agent_selection/test_view.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1의 `find_latest_result`/`load_applicants`/`ViewError`, Task 2의 `render_html`/`render_empty_html`/`format_collected_at`, 기존 `agent_selection.config.load_config`/`ConfigError`
- Produces: `main() -> int` (성공 0 / 실패 1, 기존 `main.py`의 `run()`과 동일한 반환 규약)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_view.py`에 이어서 추가:

```python
import agent_selection.view as view_module
from agent_selection.config import Config, ConfigError


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
Expected: FAIL — `AttributeError: module 'agent_selection.view' has no attribute 'main'`

- [ ] **Step 3: 최소 구현 작성**

`src/agent_selection/view.py` 맨 위 import 블록에 다음을 추가:

```python
import sys
import webbrowser

from agent_selection.config import ConfigError, load_config
```

파일 맨 아래에 추가:

```python
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
        html = render_empty_html()
    else:
        try:
            applicants = load_applicants(latest)
        except ViewError as exc:
            logger.error("%s", exc)
            return 1
        html = render_html(applicants, format_collected_at(latest))

    view_path = output_dir / "view.html"
    view_path.write_text(html, encoding="utf-8")
    webbrowser.open(f"file://{view_path.resolve()}")
    logger.info("결과 화면 생성 완료: %s", view_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트가 통과하는지 확인**

Run: `pytest tests/agent_selection/test_view.py -v`
Expected: PASS (13 passed)

전체 스위트도 함께 확인:

Run: `pytest -v`
Expected: PASS (기존 12개 + 신규 13개 = 25 passed)

- [ ] **Step 5: README에 사용법 추가**

`README.md`의 `## 결과물` 섹션 뒤에 아래 섹션을 추가:

```markdown
## 결과 보기

가장 최근 수집 결과를 표로 보기 좋게 보여주는 화면을 브라우저로 엽니다.

```bash
.venv/bin/python -m agent_selection.view
```

- 역할타입(A/B/C) 버튼과 이름/전화번호 검색으로 걸러볼 수 있습니다.
- 읽기 전용 화면입니다 — 여기서 클릭해도 엑스파일 사이트에는 어떤 영향도 없습니다.
- 아직 수집 결과가 없으면 안내 메시지가 뜹니다. 먼저 `python -m agent_selection.main`을 실행하세요.
```

- [ ] **Step 6: 커밋**

```bash
git add src/agent_selection/view.py tests/agent_selection/test_view.py README.md
git commit -m "feat: 지원자 데이터 보기 화면 진입점 추가 및 사용법 문서화"
```

---

## Manual Verification (구현 완료 후 사용자가 직접 확인)

1. `.venv/bin/python -m agent_selection.main`으로 실제 데이터를 한 번 수집한다 (이미 되어 있다면 생략)
2. `.venv/bin/python -m agent_selection.view` 실행
3. 브라우저가 자동으로 열리고 지원자 표가 보이는지 확인
4. A/B/C 필터 버튼을 눌러 표가 걸러지는지 확인
5. 검색창에 이름 일부를 입력해 실시간으로 걸러지는지 확인
6. `output/` 폴더를 비운 뒤 다시 실행해 "아직 수집된 데이터가 없습니다" 안내가 뜨는지 확인
