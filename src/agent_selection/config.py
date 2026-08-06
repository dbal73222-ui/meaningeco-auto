from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(Exception):
    """설정값 누락 또는 형식 오류"""


@dataclass(frozen=True)
class Config:
    login_url: str
    username: str
    password: str
    posting_urls: tuple[str, ...]
    headless: bool


def load_config(env_path: str | None = None) -> Config:
    load_dotenv(dotenv_path=env_path)

    login_url = os.getenv("XFILE_LOGIN_URL", "").strip()
    username = os.getenv("XFILE_USERNAME", "").strip()
    password = os.getenv("XFILE_PASSWORD", "").strip()
    posting_urls_raw = os.getenv("XFILE_POSTING_URLS", "").strip()
    headless_raw = os.getenv("XFILE_HEADLESS", "true").strip().lower()

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

    return Config(
        login_url=login_url,
        username=username,
        password=password,
        posting_urls=posting_urls,
        headless=headless_raw != "false",
    )
