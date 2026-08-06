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

logger = logging.getLogger(__name__)


def run() -> int:
    # 모듈 import만으로 root logger가 재설정되지 않도록 실행 시점으로 이동
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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

            parsed = parse_applicant_rows(raw_rows, posting_url)
            all_applicants.extend(parsed)
            # 페이지네이션으로 일부만 수집됐을 가능성을 운영자가 화면과 대조할 수 있도록 기록
            logger.info("공고 %s: %d명 수집", posting_url, len(raw_rows))

        browser.close()

    print_summary(all_applicants)
    if skipped_postings:
        print(f"스킵된 공고: {len(skipped_postings)}건")
        for url in skipped_postings:
            print(f"  - {url}")

    json_path, csv_path = save_results(all_applicants, Path(config.output_dir))
    print(f"저장 완료: {json_path}, {csv_path}")

    return 0


if __name__ == "__main__":
    sys.exit(run())
