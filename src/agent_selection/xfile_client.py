from __future__ import annotations

import csv
import io
import logging
from pathlib import Path

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

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
    # 실제 화면 마크업이 가정과 달라 요소를 못 찾으면 Playwright 기본 타임아웃 후
    # 원시 TimeoutError가 그대로 새어나가므로, 명확한 로그인 실패로 감싸서 재발생시킴
    try:
        page.goto(login_url)
        page.get_by_label("이메일").fill(username)
        page.get_by_label("비밀번호").fill(password)
        page.get_by_role("button", name="로그인").click()
        page.wait_for_load_state("networkidle")
    except PlaywrightTimeoutError as exc:
        raise XfileLoginError(
            "로그인 폼을 찾을 수 없습니다 — 화면 구조가 예상과 다를 수 있습니다."
        ) from exc

    error_message = page.get_by_text("아이디 또는 비밀번호가 일치하지 않습니다")
    if error_message.count() > 0:
        raise XfileLoginError("로그인 실패: 아이디 또는 비밀번호를 확인하세요.")


def scrape_posting_applicants(page: Page, posting_url: str) -> list[dict[str, str]]:
    # 지원자 목록 화면은 표가 아닌 카드 형태라 DOM 스크래핑이 불가능함(실사이트 확인 결과).
    # 대신 "엑셀 다운로드" 버튼이 커스텀옵션까지 포함된 CSV를 제공해 이를 내려받아 파싱함
    page.goto(posting_url)
    page.wait_for_load_state("networkidle")

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

    return rows
