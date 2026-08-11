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


# $ 치환만 처리하므로 CSS/JS의 중괄호를 이스케이프할 필요가 없음 (f-string 대비 안전)
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
    rows = [
        {col: applicant.get(col, "") for col in VIEW_COLUMNS}
        | {"posting_url": applicant.get("posting_url", "")}
        for applicant in applicants
    ]

    # 공고명이 같아도 다른 공고일 수 있어(예: 매달 반복되는 동일 제목 공고) URL을 필터 키로 쓰고
    # 공고명은 사람이 읽을 라벨로만 사용. 공고명은 엑스파일 관리자가 입력하는 자유 텍스트라
    # HTML 특수문자가 섞일 수 있어 이스케이프 필요
    posting_titles_by_url: dict[str, str] = {}
    for applicant in applicants:
        url = applicant.get("posting_url", "")
        title = applicant.get("posting_title", "")
        if url:
            posting_titles_by_url.setdefault(url, title)

    posting_buttons = '<button data-posting="ALL" class="active">전체</button>' + "".join(
        f'<button data-posting="{html.escape(url)}">{html.escape(title)}</button>'
        for url, title in sorted(posting_titles_by_url.items(), key=lambda item: item[1])
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
        recommend_json=_safe_json(group_pending_by_schedule(applicants)),
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
