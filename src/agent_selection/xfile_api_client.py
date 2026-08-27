from __future__ import annotations

import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class XfileApiError(Exception):
    """expile-backend API 호출 실패 (네트워크, 인증, 권한, 응답 형식 등)"""


class XfileApiAuthError(XfileApiError):
    """expile-backend API 로그인 실패"""


def extract_job_posting_id(posting_url: str) -> str:
    path = urlparse(posting_url).path.rstrip("/")
    return path.rsplit("/", 1)[-1]
