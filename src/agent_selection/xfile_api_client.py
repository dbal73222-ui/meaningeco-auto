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
        if response.status_code != 200:
            raise XfileApiAuthError(f"로그인 실패 (status={response.status_code})")
        # response.json() 파싱 실패(JSONDecodeError)도 RequestException의 하위 클래스라
        # 이 try 블록 안에 있어야 아래 except로 잡힌다 — 밖에 두면 보호되지 않는다.
        payload = response.json()
    except requests.exceptions.RequestException as exc:
        raise XfileApiAuthError(f"로그인 요청 중 오류: {exc}") from exc

    access_token = payload.get("accessToken")
    if not access_token:
        raise XfileApiAuthError("로그인 응답에 accessToken이 없습니다.")

    return access_token


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def fetch_applicants_with_career(
    base_url: str,
    token: str,
    job_posting_id: str,
    http_client=requests,
) -> dict[str, int]:
    limit = 200
    try:
        response = http_client.get(
            f"{base_url}/business/job-applications/{job_posting_id}",
            headers={"Authorization": f"Bearer {token}"},
            params={"sortBy": "career", "sortOrder": "desc", "page": 1, "limit": limit},
            timeout=10,
        )
        if response.status_code != 200:
            raise XfileApiError(
                f"지원자 조회 실패 (jobPostingId={job_posting_id}, status={response.status_code})"
            )
        # response.json() 파싱 실패도 RequestException 하위 클래스라 try 안에 둬야 보호된다.
        payload = response.json()
    except requests.exceptions.RequestException as exc:
        raise XfileApiError(f"지원자 조회 중 오류 (jobPostingId={job_posting_id}): {exc}") from exc

    total = payload.get("total", 0)
    if total > limit:
        logger.warning(
            "공고 %s의 지원자 수(%d)가 페이지 크기(%d)를 초과 — 가진 페이지만 사용합니다.",
            job_posting_id,
            total,
            limit,
        )

    career_counts_by_phone: dict[str, int] = {}
    for item in payload.get("data", []):
        # .get(key, {})은 키가 아예 없을 때만 기본값을 쓴다. agentUser가 명시적으로
        # null(탈퇴·삭제된 요원)이면 None이 그대로 반환되므로 "or {}"로 한 번 더 막는다.
        agent_user = item.get("agentUser") or {}
        phone_no = agent_user.get("phoneNo")
        careers = agent_user.get("careers", [])
        if not phone_no:
            continue
        career_counts_by_phone[_normalize_phone(phone_no)] = len(careers)

    return career_counts_by_phone
