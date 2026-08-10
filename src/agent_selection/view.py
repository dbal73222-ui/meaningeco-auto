from __future__ import annotations

import json
import logging
from pathlib import Path
from string import Template

from agent_selection.applicant_parser import ROLE_TYPES

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
