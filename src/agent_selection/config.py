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
