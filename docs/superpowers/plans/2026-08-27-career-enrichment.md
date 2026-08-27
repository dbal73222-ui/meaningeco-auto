# 지원자 경력 데이터 보강 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `meaningeco-automation`의 "추천 보기" 화면에, expile-backend API에서 가져온 실제 경력 수(`career_count`)와 슈퍼바이저 후보 여부를 참고 정보로 추가한다.

**Architecture:** 기존 Playwright CSV 스크래핑 흐름은 그대로 두고, 공고별 CSV 파싱이 끝난 뒤 `xfile_api_client`로 expile-backend의 `/business/auth/login` + `/business/job-applications/:jobPostingId` API를 호출해 전화번호 기준으로 `career_count`를 채워 넣는 후처리 단계를 추가한다. API 호출이 실패해도 기존 CSV 결과는 그대로 살아있어야 하므로, 이 단계는 실패를 전부 흡수하고 `career_count=None`으로 계속 진행한다.

**Tech Stack:** Python 3.13, `requests`(신규 추가), `python-dotenv`, `playwright`, `pytest`

**Spec:** `docs/superpowers/specs/2026-08-24-career-enrichment-design.md`

## Global Constraints

- 100% 참고용 — 이 기능은 승인/거절 등 어떤 쓰기 액션도 하지 않는다 (스펙의 "원칙" 섹션)
- 기존 CSV/Playwright 흐름을 대체하지 않는다 — API 호출 실패가 기존 흐름을 절대 중단시키면 안 된다
- 경력 정보는 표시용일 뿐 정렬/그룹 기준에 포함하지 않는다 (참여횟수를 정렬에서 뺐던 것과 같은 이유)
- 슈퍼바이저 후보 판별 임계값(`XFILE_SUPERVISOR_CAREER_THRESHOLD`)은 이번 범위에서 숫자를 확정하지 않는다 — 미설정 시 해당 기능은 자동으로 꺼져 있어야 한다
- `Applicant`는 `frozen=True` dataclass다 — 필드를 채울 때 직접 대입이 아니라 `dataclasses.replace()`로 새 인스턴스를 만든다 (불변성 유지)

---

## 파일 구조

- `src/agent_selection/xfile_api_client.py` (신규) — API 로그인, 지원자+경력 조회, 공고 URL에서 jobPostingId 추출
- `src/agent_selection/applicant_parser.py` (수정) — `Applicant.career_count` 필드, 전화번호 매칭으로 채워 넣는 `enrich_applicants_with_career()`
- `src/agent_selection/config.py` (수정) — `XFILE_API_BASE_URL` / `XFILE_API_EMAIL` / `XFILE_API_PASSWORD` / `XFILE_SUPERVISOR_CAREER_THRESHOLD` 설정값
- `src/agent_selection/main.py` (수정) — CSV 스크래핑 후 공고별로 경력 보강 단계 호출
- `src/agent_selection/view.py` (수정) — "경력"/"슈퍼바이저 후보" 컬럼 표시
- `.env.example`, `requirements.txt`, `pyproject.toml` (수정) — 신규 설정값·의존성 문서화

---

### Task 1: `requests` 의존성 추가 + jobPostingId 추출 함수

**Files:**
- Modify: `requirements.txt`
- Modify: `pyproject.toml`
- Create: `src/agent_selection/xfile_api_client.py`
- Test: `tests/agent_selection/test_xfile_api_client.py`

**Interfaces:**
- Produces: `extract_job_posting_id(posting_url: str) -> str`, `XfileApiError(Exception)`, `XfileApiAuthError(XfileApiError)`

- [ ] **Step 1: `requests` 의존성 추가**

`requirements.txt`에 추가:
```
requests==2.32.3
```

`pyproject.toml`의 `dependencies` 배열에 추가:
```toml
dependencies = [
    "playwright==1.50.0",
    "python-dotenv==1.0.1",
    "requests==2.32.3",
]
```

가상환경에 설치:
```bash
cd /Users/apple/meaningeco-automation && .venv/bin/pip install requests==2.32.3
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/agent_selection/test_xfile_api_client.py` 새로 생성:

```python
from agent_selection.xfile_api_client import extract_job_posting_id


def test_extract_job_posting_id_from_detail_url():
    posting_id = extract_job_posting_id("https://console.ex-pile.com/job-posting/31a6d72d-e9bb")

    assert posting_id == "31a6d72d-e9bb"


def test_extract_job_posting_id_ignores_trailing_slash():
    posting_id = extract_job_posting_id("https://console.ex-pile.com/job-posting/abc123/")

    assert posting_id == "abc123"
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_xfile_api_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent_selection.xfile_api_client'` (파일이 아직 없음)

- [ ] **Step 4: 최소 구현 작성**

`src/agent_selection/xfile_api_client.py` 새로 생성:

```python
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
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_xfile_api_client.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: 커밋**

```bash
cd /Users/apple/meaningeco-automation
git add requirements.txt pyproject.toml src/agent_selection/xfile_api_client.py tests/agent_selection/test_xfile_api_client.py
git commit -m "feat: xfile_api_client 골격 및 jobPostingId 추출 함수 추가"
```

---

### Task 2: API 로그인 (`login`)

**Files:**
- Modify: `src/agent_selection/xfile_api_client.py`
- Test: `tests/agent_selection/test_xfile_api_client.py`

**Interfaces:**
- Consumes: `XfileApiAuthError` (Task 1)
- Produces: `login(base_url: str, email: str, password: str, http_client=requests) -> str`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_xfile_api_client.py`에 추가:

```python
from agent_selection.xfile_api_client import XfileApiAuthError, login


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeHttpClient:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.last_call: dict | None = None

    def post(self, url, json=None, headers=None, timeout=None):
        self.last_call = {"url": url, "json": json, "headers": headers, "timeout": timeout}
        return self._response


def test_login_returns_access_token_on_success():
    fake_http = _FakeHttpClient(_FakeResponse(200, {"accessToken": "abc123", "refreshToken": "xyz"}))

    token = login("https://api.example.com", "biz@example.com", "secret", http_client=fake_http)

    assert token == "abc123"
    assert fake_http.last_call["url"] == "https://api.example.com/business/auth/login"
    assert fake_http.last_call["json"] == {"email": "biz@example.com", "password": "secret"}


def test_login_raises_on_non_200_status():
    fake_http = _FakeHttpClient(_FakeResponse(401, {"message": "unauthorized"}))

    with pytest.raises(XfileApiAuthError):
        login("https://api.example.com", "biz@example.com", "wrong", http_client=fake_http)


def test_login_raises_on_network_error():
    class _RaisingHttpClient:
        def post(self, url, json=None, headers=None, timeout=None):
            raise requests.exceptions.ConnectionError("connection refused")

    with pytest.raises(XfileApiAuthError):
        login("https://api.example.com", "biz@example.com", "secret", http_client=_RaisingHttpClient())
```

파일 맨 위 import에 `pytest`, `requests` 추가:
```python
import pytest
import requests

from agent_selection.xfile_api_client import XfileApiAuthError, extract_job_posting_id, login
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_xfile_api_client.py -v`
Expected: FAIL — `ImportError: cannot import name 'login'`

- [ ] **Step 3: 최소 구현 작성**

`src/agent_selection/xfile_api_client.py`에 추가 (파일 상단 import에 `import requests` 추가):

```python
import requests
```

파일 끝에 추가:

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_xfile_api_client.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 커밋**

```bash
cd /Users/apple/meaningeco-automation
git add src/agent_selection/xfile_api_client.py tests/agent_selection/test_xfile_api_client.py
git commit -m "feat: xfile_api_client에 API 로그인 함수 추가"
```

---

### Task 3: 지원자 + 경력 조회 (`fetch_applicants_with_career`)

**Files:**
- Modify: `src/agent_selection/xfile_api_client.py`
- Test: `tests/agent_selection/test_xfile_api_client.py`

**Interfaces:**
- Consumes: `XfileApiError` (Task 1)
- Produces: `fetch_applicants_with_career(base_url: str, token: str, job_posting_id: str, http_client=requests) -> dict[str, int]` — 반환 딕셔너리의 키는 숫자만 남긴 전화번호(하이픈 제거)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_xfile_api_client.py`에 추가 (import에 `XfileApiError`, `fetch_applicants_with_career` 추가):

```python
def _job_applications_response(items: list[dict], total: int | None = None) -> dict:
    return {
        "data": items,
        "page": 1,
        "limit": 200,
        "total": total if total is not None else len(items),
        "totalPage": 1,
    }


def _applicant_item(phone_no: str, career_count: int) -> dict:
    return {
        "id": "app-1",
        "status": "PENDING",
        "agentUser": {
            "id": "agent-1",
            "phoneNo": phone_no,
            "careers": [{"jobPostingId": f"posting-{i}"} for i in range(career_count)],
        },
    }


class _FakeGetHttpClient:
    def __init__(self, response: _FakeResponse):
        self._response = response
        self.last_call: dict | None = None

    def get(self, url, headers=None, params=None, timeout=None):
        self.last_call = {"url": url, "headers": headers, "params": params, "timeout": timeout}
        return self._response


def test_fetch_applicants_with_career_maps_phone_to_career_count():
    items = [_applicant_item("010-1234-5678", 3), _applicant_item("010-0000-0000", 0)]
    fake_http = _FakeGetHttpClient(_FakeResponse(200, _job_applications_response(items)))

    result = fetch_applicants_with_career(
        "https://api.example.com", "token-abc", "posting-1", http_client=fake_http
    )

    assert result == {"01012345678": 3, "01000000000": 0}
    assert fake_http.last_call["url"] == "https://api.example.com/business/job-applications/posting-1"
    assert fake_http.last_call["headers"] == {"Authorization": "Bearer token-abc"}
    assert fake_http.last_call["params"] == {
        "sortBy": "career",
        "sortOrder": "desc",
        "page": 1,
        "limit": 200,
    }


def test_fetch_applicants_with_career_logs_warning_when_total_exceeds_limit(caplog):
    items = [_applicant_item("010-1234-5678", 1)]
    fake_http = _FakeGetHttpClient(_FakeResponse(200, _job_applications_response(items, total=500)))

    with caplog.at_level(logging.WARNING):
        fetch_applicants_with_career(
            "https://api.example.com", "token-abc", "posting-1", http_client=fake_http
        )

    assert any("500" in message for message in caplog.messages)


def test_fetch_applicants_with_career_raises_on_non_200_status():
    fake_http = _FakeGetHttpClient(_FakeResponse(403, {"message": "forbidden"}))

    with pytest.raises(XfileApiError):
        fetch_applicants_with_career(
            "https://api.example.com", "token-abc", "posting-1", http_client=fake_http
        )


def test_fetch_applicants_with_career_raises_on_network_error():
    class _RaisingHttpClient:
        def get(self, url, headers=None, params=None, timeout=None):
            raise requests.exceptions.ConnectionError("connection refused")

    with pytest.raises(XfileApiError):
        fetch_applicants_with_career(
            "https://api.example.com", "token-abc", "posting-1", http_client=_RaisingHttpClient()
        )
```

파일 상단에 `import logging` 추가.

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_xfile_api_client.py -v`
Expected: FAIL — `ImportError: cannot import name 'fetch_applicants_with_career'`

- [ ] **Step 3: 최소 구현 작성**

`src/agent_selection/xfile_api_client.py` 파일 끝에 추가:

```python
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
    except requests.exceptions.RequestException as exc:
        raise XfileApiError(f"지원자 조회 중 네트워크 오류 (jobPostingId={job_posting_id}): {exc}") from exc

    if response.status_code != 200:
        raise XfileApiError(
            f"지원자 조회 실패 (jobPostingId={job_posting_id}, status={response.status_code})"
        )

    payload = response.json()
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
        agent_user = item.get("agentUser", {})
        phone_no = agent_user.get("phoneNo")
        careers = agent_user.get("careers", [])
        if not phone_no:
            continue
        career_counts_by_phone[_normalize_phone(phone_no)] = len(careers)

    return career_counts_by_phone
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_xfile_api_client.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: 커밋**

```bash
cd /Users/apple/meaningeco-automation
git add src/agent_selection/xfile_api_client.py tests/agent_selection/test_xfile_api_client.py
git commit -m "feat: xfile_api_client에 지원자+경력 조회 함수 추가"
```

---

### Task 4: 설정값 추가

**Files:**
- Modify: `src/agent_selection/config.py`
- Modify: `.env.example`
- Test: `tests/agent_selection/test_config.py`

**Interfaces:**
- Produces: `Config.api_base_url: str | None`, `Config.api_email: str`, `Config.api_password: str`, `Config.supervisor_career_threshold: int | None`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_config.py`에 추가 (기존 테스트들의 `monkeypatch.delenv` 목록에 `XFILE_API_BASE_URL`, `XFILE_API_EMAIL`, `XFILE_API_PASSWORD`, `XFILE_SUPERVISOR_CAREER_THRESHOLD`도 함께 추가):

```python
def test_load_config_api_base_url_defaults_to_none_when_unset(tmp_path, monkeypatch):
    for key in (
        "XFILE_LOGIN_URL",
        "XFILE_USERNAME",
        "XFILE_PASSWORD",
        "XFILE_POSTING_URLS",
        "XFILE_API_BASE_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_USERNAME=tester\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com\n",
    )

    config = load_config(env_path=str(env_file))

    assert config.api_base_url is None


def test_load_config_api_credentials_default_to_playwright_credentials(tmp_path, monkeypatch):
    for key in ("XFILE_LOGIN_URL", "XFILE_USERNAME", "XFILE_PASSWORD", "XFILE_POSTING_URLS",
                "XFILE_API_EMAIL", "XFILE_API_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_USERNAME=tester@example.com\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com\n",
    )

    config = load_config(env_path=str(env_file))

    assert config.api_email == "tester@example.com"
    assert config.api_password == "secret"


def test_load_config_api_credentials_explicit_override(tmp_path, monkeypatch):
    for key in ("XFILE_LOGIN_URL", "XFILE_USERNAME", "XFILE_PASSWORD", "XFILE_POSTING_URLS",
                "XFILE_API_EMAIL", "XFILE_API_PASSWORD"):
        monkeypatch.delenv(key, raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_USERNAME=tester@example.com\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com\n"
        "XFILE_API_EMAIL=api-only@example.com\n"
        "XFILE_API_PASSWORD=api-only-secret\n",
    )

    config = load_config(env_path=str(env_file))

    assert config.api_email == "api-only@example.com"
    assert config.api_password == "api-only-secret"


def test_load_config_supervisor_threshold_parses_int(tmp_path, monkeypatch):
    monkeypatch.delenv("XFILE_SUPERVISOR_CAREER_THRESHOLD", raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_USERNAME=tester\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com\n"
        "XFILE_SUPERVISOR_CAREER_THRESHOLD=5\n",
    )

    config = load_config(env_path=str(env_file))

    assert config.supervisor_career_threshold == 5


def test_load_config_supervisor_threshold_defaults_to_none_when_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("XFILE_SUPERVISOR_CAREER_THRESHOLD", raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_USERNAME=tester\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com\n",
    )

    config = load_config(env_path=str(env_file))

    assert config.supervisor_career_threshold is None


def test_load_config_supervisor_threshold_invalid_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("XFILE_SUPERVISOR_CAREER_THRESHOLD", raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_USERNAME=tester\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com\n"
        "XFILE_SUPERVISOR_CAREER_THRESHOLD=not-a-number\n",
    )

    with pytest.raises(ConfigError, match="XFILE_SUPERVISOR_CAREER_THRESHOLD"):
        load_config(env_path=str(env_file))
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_config.py -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'api_base_url'`

- [ ] **Step 3: 최소 구현 작성**

`src/agent_selection/config.py`를 다음과 같이 수정:

```python
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


class ConfigError(Exception):
    """설정값 누락 또는 형식 오류"""


@dataclass(frozen=True)
class Config:
    login_url: str
    username: str
    # 실수로 print/log 되어도 비밀번호가 노출되지 않도록 repr에서 제외
    password: str = field(repr=False)
    posting_urls: tuple[str, ...]
    headless: bool
    output_dir: str
    api_base_url: str | None
    api_email: str
    api_password: str = field(repr=False)
    supervisor_career_threshold: int | None


def load_config(env_path: str | None = None) -> Config:
    load_dotenv(dotenv_path=env_path)

    login_url = os.getenv("XFILE_LOGIN_URL", "").strip()
    username = os.getenv("XFILE_USERNAME", "").strip()
    password = os.getenv("XFILE_PASSWORD", "").strip()
    posting_urls_raw = os.getenv("XFILE_POSTING_URLS", "").strip()
    headless_raw = os.getenv("XFILE_HEADLESS", "true").strip().lower()
    # 출력 경로는 필수값이 아니므로 미설정시 기본값 "output"으로 대체
    output_dir = os.getenv("XFILE_OUTPUT_DIR", "output").strip() or "output"

    if not login_url:
        raise ConfigError("XFILE_LOGIN_URL이 설정되지 않았습니다.")
    if not username:
        raise ConfigError("XFILE_USERNAME이 설정되지 않았습니다.")
    if not password:
        raise ConfigError("XFILE_PASSWORD가 설정되지 않았습니다.")
    if not posting_urls_raw:
        raise ConfigError("XFILE_POSTING_URLS가 설정되지 않았습니다.")

    posting_urls = tuple(
        url.strip() for url in posting_urls_raw.split(",") if url.strip()
    )

    # 경력 보강 기능은 완전히 선택적이므로 미설정 시 None — main.py가 이 값으로 기능을 끈다
    api_base_url = os.getenv("XFILE_API_BASE_URL", "").strip() or None
    # 기업회원 로그인이 기존 Playwright 관리자 로그인과 같은 계정 체계일 가능성이 높아
    # 기본값은 기존 XFILE_USERNAME/PASSWORD를 재사용하고, 다르면 명시적으로 덮어쓸 수 있게 함
    api_email = os.getenv("XFILE_API_EMAIL", "").strip() or username
    api_password = os.getenv("XFILE_API_PASSWORD", "").strip() or password

    threshold_raw = os.getenv("XFILE_SUPERVISOR_CAREER_THRESHOLD", "").strip()
    supervisor_career_threshold: int | None = None
    if threshold_raw:
        try:
            supervisor_career_threshold = int(threshold_raw)
        except ValueError as exc:
            raise ConfigError(
                "XFILE_SUPERVISOR_CAREER_THRESHOLD은 정수여야 합니다."
            ) from exc

    return Config(
        login_url=login_url,
        username=username,
        password=password,
        posting_urls=posting_urls,
        headless=headless_raw != "false",
        output_dir=output_dir,
        api_base_url=api_base_url,
        api_email=api_email,
        api_password=api_password,
        supervisor_career_threshold=supervisor_career_threshold,
    )
```

`.env.example`에 추가:

```
# --- 경력 데이터 보강 (선택 기능, 미설정 시 자동으로 꺼짐) ---
# expile-backend API 기본 URL. 비워두면 경력 보강 기능 전체가 비활성화됨
XFILE_API_BASE_URL=
# 비워두면 XFILE_USERNAME/XFILE_PASSWORD를 그대로 사용함
XFILE_API_EMAIL=
XFILE_API_PASSWORD=
# 이 경력 수 이상이면 "슈퍼바이저 후보"로 표시. 비워두면 표시 기능 자체가 꺼짐 (대표님 확인 전까지 비워둘 것)
XFILE_SUPERVISOR_CAREER_THRESHOLD=
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_config.py -v`
Expected: PASS (전체 통과 — 기존 테스트 포함)

- [ ] **Step 5: 커밋**

```bash
cd /Users/apple/meaningeco-automation
git add src/agent_selection/config.py .env.example tests/agent_selection/test_config.py
git commit -m "feat: 경력 데이터 보강용 설정값 추가"
```

---

### Task 5: `Applicant`에 경력 필드 추가 + 매칭 함수

**Files:**
- Modify: `src/agent_selection/applicant_parser.py`
- Test: `tests/agent_selection/test_applicant_parser.py`

**Interfaces:**
- Produces: `Applicant.career_count: int | None`, `enrich_applicants_with_career(applicants: list[Applicant], career_counts_by_phone: dict[str, int]) -> list[Applicant]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_applicant_parser.py`에 추가 (import에 `enrich_applicants_with_career` 추가):

```python
def test_enrich_applicants_with_career_fills_matching_phone():
    applicant = parse_applicant_row(
        VALID_ROW, posting_url="https://a.example.com", posting_title="미화 공고"
    )

    enriched = enrich_applicants_with_career([applicant], {"01012345678": 4})

    assert enriched[0].career_count == 4


def test_enrich_applicants_with_career_normalizes_phone_format_differences():
    row = {**VALID_ROW, "phone": "01012345678"}  # 하이픈 없는 형식
    applicant = parse_applicant_row(row, posting_url="https://a.example.com", posting_title="미화 공고")

    # career_counts_by_phone 쪽은 하이픈 있는 형식으로 와도 매칭되어야 함
    enriched = enrich_applicants_with_career([applicant], {"010-1234-5678": 2})

    assert enriched[0].career_count == 2


def test_enrich_applicants_with_career_leaves_none_for_unmatched_phone():
    applicant = parse_applicant_row(
        VALID_ROW, posting_url="https://a.example.com", posting_title="미화 공고"
    )

    enriched = enrich_applicants_with_career([applicant], {"01099998888": 4})

    assert enriched[0].career_count is None


def test_enrich_applicants_with_career_does_not_mutate_original_list():
    applicant = parse_applicant_row(
        VALID_ROW, posting_url="https://a.example.com", posting_title="미화 공고"
    )
    original = [applicant]

    enrich_applicants_with_career(original, {"01012345678": 4})

    assert original[0].career_count is None
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_applicant_parser.py -v`
Expected: FAIL — `ImportError: cannot import name 'enrich_applicants_with_career'`

- [ ] **Step 3: 최소 구현 작성**

`src/agent_selection/applicant_parser.py`를 다음과 같이 수정:

```python
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Applicant:
    no: str
    name: str
    phone: str
    birth_date: str
    gender: str
    applied_at: str
    status: str
    status_changed_at: str
    selected_schedule: str
    approved_schedule: str
    role_type: str
    participation_count: str
    custom_option_3: str
    posting_url: str
    posting_title: str
    # expile-backend API 조회 결과로 채워짐. 매칭 실패/API 미사용 시 None ("정보 없음"으로 표시)
    career_count: int | None = None


def parse_applicant_row(
    row: dict[str, str], posting_url: str, posting_title: str
) -> Applicant:
    return Applicant(
        no=row.get("no", ""),
        name=row.get("name", ""),
        phone=row.get("phone", ""),
        birth_date=row.get("birth_date", ""),
        gender=row.get("gender", ""),
        applied_at=row.get("applied_at", ""),
        status=row.get("status", ""),
        status_changed_at=row.get("status_changed_at", ""),
        selected_schedule=row.get("selected_schedule", ""),
        approved_schedule=row.get("approved_schedule", ""),
        role_type=row.get("custom_option_1", "").strip(),
        participation_count=row.get("custom_option_2", "").strip(),
        custom_option_3=row.get("custom_option_3", ""),
        posting_url=posting_url,
        posting_title=posting_title,
    )


def parse_applicant_rows(
    rows: list[dict[str, str]], posting_url: str, posting_title: str
) -> list[Applicant]:
    return [parse_applicant_row(row, posting_url, posting_title) for row in rows]


def _normalize_phone(phone: str) -> str:
    return "".join(ch for ch in phone if ch.isdigit())


def enrich_applicants_with_career(
    applicants: list[Applicant], career_counts_by_phone: dict[str, int]
) -> list[Applicant]:
    normalized_counts = {
        _normalize_phone(phone): count for phone, count in career_counts_by_phone.items()
    }
    return [
        replace(
            applicant,
            career_count=normalized_counts.get(_normalize_phone(applicant.phone)),
        )
        for applicant in applicants
    ]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_applicant_parser.py tests/agent_selection/test_column_keys.py -v`
Expected: PASS (전체 통과 — `test_column_keys.py`가 여전히 통과하는지도 함께 확인해 회귀 방지)

- [ ] **Step 5: 커밋**

```bash
cd /Users/apple/meaningeco-automation
git add src/agent_selection/applicant_parser.py tests/agent_selection/test_applicant_parser.py
git commit -m "feat: Applicant에 career_count 필드 및 전화번호 매칭 함수 추가"
```

---

### Task 6: `main.py`에 경력 보강 단계 연결

**Files:**
- Modify: `src/agent_selection/main.py`
- Test: 수동 검증 (아래 참고) — `main.py`는 Playwright 브라우저를 직접 구동하는 진입점이라 기존에도 유닛 테스트가 없음 (기존 패턴 유지)

**Interfaces:**
- Consumes: `extract_job_posting_id`, `login`, `fetch_applicants_with_career`, `XfileApiError` (Task 1-3), `enrich_applicants_with_career` (Task 5), `Config.api_base_url` 등 (Task 4)

- [ ] **Step 1: `main.py` 수정**

`src/agent_selection/main.py`의 import 섹션에 추가:

```python
from agent_selection.applicant_parser import Applicant, enrich_applicants_with_career, parse_applicant_rows
from agent_selection.config import Config, ConfigError, load_config
from agent_selection.xfile_api_client import (
    XfileApiError,
    extract_job_posting_id,
    fetch_applicants_with_career,
    login as api_login,
)
```

(기존 `from agent_selection.applicant_parser import parse_applicant_rows` 줄과 `from agent_selection.config import ConfigError, load_config` 줄은 위 두 줄로 각각 대체)

`run()` 함수의 for 루프를 다음과 같이 수정 (기존 `parsed = parse_applicant_rows(...)` 다음, `all_applicants.extend(parsed)` 이전에 삽입):

```python
        for posting_url in config.posting_urls:
            try:
                posting_title, raw_rows = scrape_posting_applicants(page, posting_url)
            except XfilePageError as exc:
                logger.warning("공고 스킵: %s", exc)
                skipped_postings.append(posting_url)
                continue

            parsed = parse_applicant_rows(raw_rows, posting_url, posting_title)

            if config.api_base_url:
                parsed = _enrich_with_career_data(parsed, config, posting_url, posting_title)

            all_applicants.extend(parsed)
            # 페이지네이션으로 일부만 수집됐을 가능성을 운영자가 화면과 대조할 수 있도록 기록
            logger.info("공고 %s (%s): %d명 수집", posting_title, posting_url, len(raw_rows))
```

`run()` 함수 위에 새 헬퍼 함수 추가:

```python
def _enrich_with_career_data(
    applicants: list[Applicant], config: Config, posting_url: str, posting_title: str
) -> list[Applicant]:
    # 경력 보강은 부가 정보이지 필수 경로가 아니므로, 실패해도 기존 CSV 결과는 그대로 유지한다
    try:
        job_posting_id = extract_job_posting_id(posting_url)
        token = api_login(config.api_base_url, config.api_email, config.api_password)
        career_counts_by_phone = fetch_applicants_with_career(
            config.api_base_url, token, job_posting_id
        )
        return enrich_applicants_with_career(applicants, career_counts_by_phone)
    except XfileApiError as exc:
        logger.warning("경력 데이터 보강 실패 (공고 %s): %s", posting_title, exc)
        return applicants
```

- [ ] **Step 2: 수동 검증**

`XFILE_API_BASE_URL`을 비워둔 상태로 실행해 기존 흐름이 그대로 동작하는지 확인:

```bash
cd /Users/apple/meaningeco-automation && .venv/bin/python -m agent_selection.main
```

Expected: 기존과 동일하게 동작 (career_count는 전부 None으로 채워짐, 에러 없음)

`XFILE_API_BASE_URL` 등을 설정한 뒤 다시 실행해, 실제 로그인 계정이 Playwright 계정과 같은지(스펙의 미확정 항목 #2), 응답이 예상 형식과 맞는지 로그로 확인 — 이 시점에 문제가 있으면 경고 로그만 남고 기존 흐름은 계속되므로 안전하게 검증 가능함

- [ ] **Step 3: 전체 테스트 스위트 통과 확인 (회귀 방지)**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest -v`
Expected: PASS (전체)

- [ ] **Step 4: 커밋**

```bash
cd /Users/apple/meaningeco-automation
git add src/agent_selection/main.py
git commit -m "feat: main.py에 경력 데이터 보강 단계 연결"
```

---

### Task 7: 화면에 경력·슈퍼바이저 후보 컬럼 표시

**Files:**
- Modify: `src/agent_selection/view.py`
- Test: `tests/agent_selection/test_view.py`

**Interfaces:**
- Consumes: 없음 (applicant dict에 `career_count` 키가 있으면 사용, 없으면 "정보 없음" 처리)
- Produces: `render_html(applicants, collected_at, supervisor_threshold=None)`, `group_pending_by_schedule(applicants, supervisor_threshold=None)`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/agent_selection/test_view.py`에 추가:

```python
def test_render_html_shows_no_info_for_missing_career_count():
    rows = [{**SAMPLE_ROWS[0], "career_count": None}]

    html = render_html(rows, "2026-08-10 14:30:00")

    assert "정보 없음" in html


def test_render_html_shows_career_count_value():
    rows = [{**SAMPLE_ROWS[0], "career_count": 7}]

    html = render_html(rows, "2026-08-10 14:30:00")

    assert ">7<" in html or "7" in html


def test_render_html_marks_supervisor_candidate_when_above_threshold():
    rows = [{**SAMPLE_ROWS[0], "career_count": 10}]

    html = render_html(rows, "2026-08-10 14:30:00", supervisor_threshold=5)

    assert "✓" in html


def test_render_html_does_not_mark_supervisor_candidate_below_threshold():
    rows = [{**SAMPLE_ROWS[0], "career_count": 2}]

    html = render_html(rows, "2026-08-10 14:30:00", supervisor_threshold=5)

    columns_data = html.split("const DATA = ")[1].split(";\nconst COLUMNS")[0]
    assert '"supervisor_candidate": ""' in columns_data


def test_render_html_includes_career_column_header():
    html = render_html(SAMPLE_ROWS, "2026-08-10 14:30:00")

    assert "경력" in html


def test_group_pending_by_schedule_includes_career_display_fields():
    applicant = {**_raw_applicant("대기", "1일차", "2026-08-01 10:00"), "career_count": 8}

    result = group_pending_by_schedule([applicant], supervisor_threshold=5)

    assert result[0]["applicants"][0]["career_count"] == "8"
    assert result[0]["applicants"][0]["supervisor_candidate"] == "✓"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_view.py -v`
Expected: FAIL — `TypeError: group_pending_by_schedule() got an unexpected keyword argument 'supervisor_threshold'` (및 "경력"/"✓" 관련 assert 실패)

- [ ] **Step 3: 최소 구현 작성**

`src/agent_selection/view.py`의 `VIEW_COLUMNS`/`VIEW_COLUMN_LABELS`를 다음과 같이 수정:

```python
VIEW_COLUMNS: tuple[str, ...] = (
    "name",
    "phone",
    "posting_title",
    "participation_count",
    "career_count",
    "supervisor_candidate",
    "status",
    "applied_at",
)

VIEW_COLUMN_LABELS: dict[str, str] = {
    "name": "이름",
    "phone": "전화번호",
    "posting_title": "공고명",
    "participation_count": "참여횟수",
    "career_count": "경력",
    "supervisor_candidate": "슈퍼바이저 후보",
    "status": "지원상태",
    "applied_at": "지원일시",
}


def _career_display_fields(applicant: dict, supervisor_threshold: int | None) -> dict[str, str]:
    career_count = applicant.get("career_count")
    if career_count is None:
        return {"career_count": "정보 없음", "supervisor_candidate": ""}
    is_candidate = supervisor_threshold is not None and career_count >= supervisor_threshold
    return {
        "career_count": str(career_count),
        "supervisor_candidate": "✓" if is_candidate else "",
    }
```

`group_pending_by_schedule`을 다음과 같이 수정:

```python
def group_pending_by_schedule(
    applicants: list[dict], supervisor_threshold: int | None = None
) -> list[dict]:
    # 참여횟수는 외부 경력을 반영 못하므로 그룹/정렬 기준에서 제외 (표시 컬럼으로만 유지)
    # 경력(career_count) 역시 표시용일 뿐 그룹/정렬 기준에는 포함하지 않음 — 같은 이유
    groups: dict[str, list[dict]] = {}
    for applicant in applicants:
        if applicant.get("status") != "대기":
            continue
        schedule = applicant.get("selected_schedule") or "미지정"
        row = {col: applicant.get(col, "") for col in VIEW_COLUMNS}
        row.update(_career_display_fields(applicant, supervisor_threshold))
        groups.setdefault(schedule, []).append(row)

    for rows in groups.values():
        rows.sort(key=lambda row: row.get("applied_at", ""))

    return [
        {"schedule": schedule, "applicants": groups[schedule]}
        for schedule in sorted(groups, key=lambda s: (s == "미지정", s))
    ]
```

`render_html`을 다음과 같이 수정:

```python
def render_html(
    applicants: list[dict], collected_at: str, supervisor_threshold: int | None = None
) -> str:
    rows = [
        {col: applicant.get(col, "") for col in VIEW_COLUMNS}
        | {"posting_url": applicant.get("posting_url", "")}
        | _career_display_fields(applicant, supervisor_threshold)
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
        recommend_json=_safe_json(group_pending_by_schedule(applicants, supervisor_threshold)),
    )
```

`main()` 함수에서 `render_html` 호출부를 수정:

```python
        html_content = render_html(
            applicants, format_collected_at(latest), config.supervisor_career_threshold
        )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest tests/agent_selection/test_view.py -v`
Expected: PASS (전체 통과 — 기존 테스트 포함)

- [ ] **Step 5: 전체 테스트 스위트 최종 확인**

Run: `cd /Users/apple/meaningeco-automation && .venv/bin/pytest -v`
Expected: PASS (전체)

- [ ] **Step 6: 커밋**

```bash
cd /Users/apple/meaningeco-automation
git add src/agent_selection/view.py tests/agent_selection/test_view.py
git commit -m "feat: 추천 보기 화면에 경력·슈퍼바이저 후보 컬럼 추가"
```

---

## 남은 미확정 항목 (구현 완료 후에도 유효)

1. **슈퍼바이저 임계값 숫자** — 대표님 확인 후 `.env`의 `XFILE_SUPERVISOR_CAREER_THRESHOLD`에 값 채워 넣기만 하면 됨 (코드 변경 불필요)
2. **API 로그인 계정이 Playwright 계정과 동일한지** — Task 6 Step 2에서 실제 `XFILE_API_BASE_URL` 설정 후 실행하며 확인. 다르면 `.env`에 `XFILE_API_EMAIL`/`XFILE_API_PASSWORD`를 별도로 채우면 됨 (코드 변경 불필요, config.py가 이미 지원)
3. **공고당 지원자 수가 200명을 넘는 경우** — 초과 시 경고 로그가 남으므로(Task 3) 실제 사용 중 관찰. 넘는 경우가 실제로 확인되면 페이지네이션 루프 추가는 별도 작업으로 진행
