import pytest

from agent_selection.config import ConfigError, load_config


def _write_env(tmp_path, content: str):
    env_file = tmp_path / ".env"
    env_file.write_text(content, encoding="utf-8")
    return env_file


def test_load_config_success(tmp_path, monkeypatch):
    for key in (
        "XFILE_LOGIN_URL",
        "XFILE_USERNAME",
        "XFILE_PASSWORD",
        "XFILE_POSTING_URLS",
        "XFILE_HEADLESS",
    ):
        monkeypatch.delenv(key, raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_USERNAME=tester\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com,https://b.example.com\n"
        "XFILE_HEADLESS=false\n",
    )

    config = load_config(env_path=str(env_file))

    assert config.login_url == "https://admin.example.com/login"
    assert config.username == "tester"
    assert config.password == "secret"
    assert config.posting_urls == ("https://a.example.com", "https://b.example.com")
    assert config.headless is False


def test_load_config_missing_username_raises(tmp_path, monkeypatch):
    for key in (
        "XFILE_LOGIN_URL",
        "XFILE_USERNAME",
        "XFILE_PASSWORD",
        "XFILE_POSTING_URLS",
    ):
        monkeypatch.delenv(key, raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com\n",
    )

    with pytest.raises(ConfigError, match="XFILE_USERNAME"):
        load_config(env_path=str(env_file))
