# 선발 추천 보기 기능 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 결과 보기 화면(`view.py`)에 "대기" 상태 지원자를 선택일정별로 그룹화해서 보여주는 참고용 "추천 보기" 토글을 추가한다.

**Architecture:** 새 순수 함수 `group_pending_by_schedule`이 필터링(대기 상태만)+그룹핑(선택일정별)+정렬(그룹 내 지원일시 오름차순)을 담당하고, `render_html`이 그 결과를 JSON으로 임베드한다. 클라이언트 사이드 JS가 토글 버튼으로 기존 테이블 뷰와 새 그룹 뷰를 전환한다. 서버/네트워크 요청 없음 — 기존 아키텍처 그대로.

**Tech Stack:** Python 3.13, 순수 함수 + `string.Template` 기반 정적 HTML/JS, pytest.

## Global Constraints

- 이 기능은 100% 참고용이다. 실제 승인/거절 등 엑스파일 사이트에 대한 어떤 액션도 수행하지 않는다.
- 참여횟수(`participation_count`)는 그룹핑/정렬 로직에서 절대 사용하지 않는다 (표시 컬럼으로만 유지).
- 그룹핑 키는 `selected_schedule`이며, 빈 값은 "미지정" 그룹으로 묶는다.
- 그룹 내 정렬은 `applied_at` 오름차순(선착순)이다.
- 배포 범위는 완전 로컬이다 — 서버, 외부 접근 URL 없음.
- 기존 `_safe_json` 이스케이프 방식을 재사용해 stored-XSS를 방지한다.

---

### Task 1: `group_pending_by_schedule` 순수 함수

**Files:**
- Modify: `src/agent_selection/view.py` (VIEW_COLUMN_LABELS 정의 바로 다음, `_PAGE_TEMPLATE` 정의 앞에 함수 추가)
- Test: `tests/agent_selection/test_view.py`

**Interfaces:**
- Consumes: 모듈에 이미 있는 `VIEW_COLUMNS: tuple[str, ...]` (name, phone, posting_title, role_type, participation_count, status, applied_at)
- Produces: `group_pending_by_schedule(applicants: list[dict]) -> list[dict]` — Task 2에서 `render_html`이 이 함수를 호출해 `recommend_json`을 만드는 데 사용한다. 반환값은 `[{"schedule": str, "applicants": list[dict]}, ...]` 형태이며, 각 `applicants` 항목의 dict는 `VIEW_COLUMNS` 키만 가진다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_view.py`의 `SAMPLE_ROWS` 정의 아래(대략 93번째 줄 근처, 기존 `test_render_html_includes_applicant_values` 앞)에 아래 헬퍼와 테스트를 추가한다:

```python
from agent_selection.view import group_pending_by_schedule


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
        "name", "phone", "posting_title", "role_type",
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/pytest tests/agent_selection/test_view.py -k group_pending_by_schedule -v`
Expected: FAIL — `ImportError: cannot import name 'group_pending_by_schedule'`

- [ ] **Step 3: 최소 구현 작성**

`src/agent_selection/view.py`에서 `VIEW_COLUMN_LABELS` 딕셔너리 정의가 끝나는 줄(현재 51번째 줄, `}` 다음) 바로 아래, `_PAGE_TEMPLATE = Template(...)` 정의 앞에 추가:

```python
def group_pending_by_schedule(applicants: list[dict]) -> list[dict]:
    # 참여횟수는 외부 경력을 반영 못하므로 그룹/정렬 기준에서 제외 (표시 컬럼으로만 유지)
    groups: dict[str, list[dict]] = {}
    for applicant in applicants:
        if applicant.get("status") != "대기":
            continue
        schedule = applicant.get("selected_schedule") or "미지정"
        row = {col: applicant.get(col, "") for col in VIEW_COLUMNS}
        groups.setdefault(schedule, []).append(row)

    for rows in groups.values():
        rows.sort(key=lambda row: row.get("applied_at", ""))

    return [
        {"schedule": schedule, "applicants": groups[schedule]}
        for schedule in sorted(groups, key=lambda s: (s == "미지정", s))
    ]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `.venv/bin/pytest tests/agent_selection/test_view.py -k group_pending_by_schedule -v`
Expected: PASS (7개 테스트 전부)

- [ ] **Step 5: 커밋**

```bash
git add src/agent_selection/view.py tests/agent_selection/test_view.py
git commit -m "feat: 대기 지원자를 선택일정별로 그룹화하는 함수 추가"
```

---

### Task 2: HTML/JS에 "추천 보기" 토글 통합

**Files:**
- Modify: `src/agent_selection/view.py` (`_PAGE_TEMPLATE` 전체 교체, `render_html` 함수의 `return _PAGE_TEMPLATE.substitute(...)` 호출부 수정)
- Test: `tests/agent_selection/test_view.py`

**Interfaces:**
- Consumes: Task 1의 `group_pending_by_schedule(applicants: list[dict]) -> list[dict]`; 기존 `_safe_json(value: object) -> str`
- Produces: `render_html`이 만드는 HTML에 `id="toggle-recommend"` 버튼과 `RECOMMEND_GROUPS` JS 상수가 포함됨 (이후 태스크나 수동 확인에서 이 마커를 사용할 수 있음)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_view.py`의 `test_render_html_handles_empty_applicant_list` 테스트 다음에 추가:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `.venv/bin/pytest tests/agent_selection/test_view.py -k "recommend" -v`
Expected: FAIL — `toggle-recommend` 등의 문자열이 HTML에 없어서 assert 실패

- [ ] **Step 3: `_PAGE_TEMPLATE` 전체 교체**

`src/agent_selection/view.py`의 `_PAGE_TEMPLATE = Template("""...""")` 전체를 아래로 교체한다:

```python
_PAGE_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>지원자 목록</title>
<style>
  body { font-family: -apple-system, sans-serif; margin: 2rem; }
  .summary { margin-bottom: 1rem; color: #555; }
  .mode-toggle { margin-bottom: 1rem; }
  .mode-toggle button { padding: 0.4rem 0.8rem; border: 1px solid #ccc; background: #fff; border-radius: 4px; cursor: pointer; }
  .notice { background: #fff8e1; border: 1px solid #ffe082; padding: 0.6rem 0.8rem; border-radius: 4px; margin-bottom: 1rem; }
  .controls { margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; }
  .controls button { padding: 0.4rem 0.8rem; border: 1px solid #ccc; background: #fff; border-radius: 4px; cursor: pointer; }
  .controls button.active { background: #333; color: #fff; }
  input[type=search] { padding: 0.4rem; border: 1px solid #ccc; border-radius: 4px; flex: 1; max-width: 240px; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; }
  th, td { border: 1px solid #ddd; padding: 0.5rem; text-align: left; }
  th { background: #f5f5f5; }
  #view-recommend h2 { margin-top: 1.5rem; }
</style>
</head>
<body>
<h1>지원자 목록</h1>
<div class="summary">총 $total명 · 수집 시각 $collected_at</div>
<div class="mode-toggle">
  <button id="toggle-recommend" type="button">추천 보기</button>
</div>
<div id="view-all">
  <div class="controls">
    $posting_buttons
    <input type="search" id="search" placeholder="이름 또는 전화번호 검색">
  </div>
  <table id="table">
    <thead><tr>$table_headers</tr></thead>
    <tbody></tbody>
  </table>
</div>
<div id="view-recommend" style="display:none;">
  <p class="notice">이 목록은 참고용이며, 실제 승인/거절은 엑스파일에서 직접 진행하세요.</p>
  <div id="recommend-groups"></div>
</div>
<script>
const DATA = $data_json;
const COLUMNS = $columns_json;
const RECOMMEND_GROUPS = $recommend_json;
const tbody = document.querySelector("#table tbody");
let activePosting = "ALL";
let query = "";

function render() {
  tbody.innerHTML = "";
  DATA.filter(row => (activePosting === "ALL" || row.posting_url === activePosting))
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

function renderRecommend() {
  const container = document.querySelector("#recommend-groups");
  container.innerHTML = "";
  if (RECOMMEND_GROUPS.length === 0) {
    const p = document.createElement("p");
    p.textContent = "현재 대기 중인 지원자가 없습니다";
    container.appendChild(p);
    return;
  }
  RECOMMEND_GROUPS.forEach(group => {
    const h2 = document.createElement("h2");
    h2.textContent = group.schedule + " (" + group.applicants.length + "명)";
    container.appendChild(h2);

    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    COLUMNS.forEach(col => {
      const th = document.createElement("th");
      th.textContent = col.label;
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const body = document.createElement("tbody");
    group.applicants.forEach(row => {
      const tr = document.createElement("tr");
      COLUMNS.forEach(col => {
        const td = document.createElement("td");
        td.textContent = row[col.key];
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    table.appendChild(body);
    container.appendChild(table);
  });
}

const viewAll = document.querySelector("#view-all");
const viewRecommend = document.querySelector("#view-recommend");
const toggleBtn = document.querySelector("#toggle-recommend");
let recommendMode = false;

toggleBtn.addEventListener("click", () => {
  recommendMode = !recommendMode;
  viewAll.style.display = recommendMode ? "none" : "";
  viewRecommend.style.display = recommendMode ? "" : "none";
  toggleBtn.textContent = recommendMode ? "전체 목록" : "추천 보기";
  if (recommendMode) renderRecommend();
});

render();
</script>
</body>
</html>
""")
```

- [ ] **Step 4: `render_html`의 `substitute` 호출부 수정**

`render_html` 함수 마지막의 `return _PAGE_TEMPLATE.substitute(...)` 블록을 아래로 교체:

```python
    return _PAGE_TEMPLATE.substitute(
        total=len(applicants),
        collected_at=collected_at,
        posting_buttons=posting_buttons,
        table_headers=table_headers,
        data_json=_safe_json(rows),
        columns_json=_safe_json(columns),
        recommend_json=_safe_json(group_pending_by_schedule(applicants)),
    )
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `.venv/bin/pytest tests/agent_selection/test_view.py -v`
Expected: PASS (기존 테스트 포함 전부 — 새 마크업이 기존 `data-posting`, `<table id="table">` 등 기존 어서션과 충돌하지 않아야 함)

- [ ] **Step 6: 전체 스위트 확인**

Run: `.venv/bin/pytest -v`
Expected: PASS — 전체 테스트 스위트(기존 28개 + Task 1의 7개 + Task 2의 4개 = 39개)가 모두 통과

- [ ] **Step 7: 커밋**

```bash
git add src/agent_selection/view.py tests/agent_selection/test_view.py
git commit -m "feat: 결과 보기 화면에 추천 보기(대기 지원자 일정별 그룹) 토글 추가"
```

---

### Task 3: README 문서화 및 수동 확인

**Files:**
- Modify: `README.md` (기존 "결과 보기" 섹션 다음에 하위 항목 추가)

**Interfaces:**
- Consumes: 없음 (문서 작업)
- Produces: 없음 (다음 태스크 없음 — 이 계획의 마지막 태스크)

- [ ] **Step 1: README에 "추천 보기" 설명 추가**

`README.md`의 "## 결과 보기" 섹션 끝(`먼저 python -m agent_selection.main을 실행하세요.` 다음 줄) 뒤에 추가:

```markdown
### 추천 보기 (참고용)

결과 보기 화면 상단의 "추천 보기" 버튼을 누르면, 아직 결정되지 않은("대기" 상태) 지원자만 골라 선택일정별로 묶어서 보여줍니다.

- 그룹 내 정렬은 지원일시 선착순입니다.
- 참여횟수는 표에 참고용으로만 표시되고, 그룹/정렬 기준에는 쓰이지 않습니다 (미닝에코 외 다른 곳에서의 경력은 데이터에 없기 때문입니다).
- **완전히 참고용 화면입니다.** 여기서 클릭해도 실제 승인/거절 등 엑스파일 사이트에 어떤 영향도 주지 않습니다 — 최종 결정은 엑스파일에서 직접 진행하세요.
- "전체 목록" 버튼을 누르면 원래의 공고별 필터/검색 화면으로 돌아갑니다.
```

- [ ] **Step 2: 전체 테스트 스위트 재확인**

Run: `.venv/bin/pytest -v`
Expected: PASS — 전부 통과 (README만 수정했으므로 실패할 이유 없음, 회귀 확인 차원)

- [ ] **Step 3: 수동 확인 (선택 — 사용자가 원할 때)**

Run: `.venv/bin/python -m agent_selection.view`
Expected: 브라우저가 열리고 상단에 "추천 보기" 버튼이 보임. 클릭하면 대기 상태 지원자가 일정별로 묶여 나오고 참고용 안내 문구가 표시됨. "전체 목록"을 누르면 원래 화면으로 돌아감.

- [ ] **Step 4: 커밋**

```bash
git add README.md
git commit -m "docs: 추천 보기 기능 사용법 추가"
```
