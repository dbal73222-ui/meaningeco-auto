from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from agent_selection.applicant_parser import Applicant


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
    # 공고명이 같아도 다른 공고일 수 있어(예: 매달 반복되는 동일 제목 공고) URL을 진짜 그룹 키로 사용
    posting_titles_by_url: dict[str, str] = {}
    for applicant in applicants:
        posting_titles_by_url.setdefault(applicant.posting_url, applicant.posting_title)

    for posting_url in sorted(posting_titles_by_url, key=lambda url: posting_titles_by_url[url]):
        title = posting_titles_by_url[posting_url]
        count = sum(1 for applicant in applicants if applicant.posting_url == posting_url)
        print(f"  {title}: {count}명")
    for applicant in applicants:
        print(f"  [{applicant.no}] {applicant.name} / {applicant.posting_title} / {applicant.status}")
