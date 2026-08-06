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
