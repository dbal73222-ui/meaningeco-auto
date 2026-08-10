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
