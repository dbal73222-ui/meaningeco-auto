from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class XfileApiError(Exception):
    """expile-backend API 호출 실패 (네트워크, 인증, 권한, 응답 형식 등)"""


class XfileApiAuthError(XfileApiError):
    """expile-backend API 로그인 실패"""


def extract_job_posting_id(posting_url: str) -> str:
    path = urlparse(posting_url).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def login(
    base_url: str,
    email: str,
    password: str,
    http_client=requests,
) -> str:
    try:
        response = http_client.post(
            f"{base_url}/business/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
    except requests.exceptions.RequestException as exc:
        raise XfileApiAuthError(f"로그인 요청 중 네트워크 오류: {exc}") from exc

    if response.status_code != 200:
        raise XfileApiAuthError(f"로그인 실패 (status={response.status_code})")

    payload = response.json()
    access_token = payload.get("accessToken")
    if not access_token:
        raise XfileApiAuthError("로그인 응답에 accessToken이 없습니다.")

    return access_token
