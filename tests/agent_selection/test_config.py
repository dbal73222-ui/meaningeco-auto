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
        "XFILE_OUTPUT_DIR",
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
        "XFILE_OUTPUT_DIR",
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


def test_load_config_output_dir_explicit_is_respected(tmp_path, monkeypatch):
    for key in (
        "XFILE_LOGIN_URL",
        "XFILE_USERNAME",
        "XFILE_PASSWORD",
        "XFILE_POSTING_URLS",
        "XFILE_HEADLESS",
        "XFILE_OUTPUT_DIR",
    ):
        monkeypatch.delenv(key, raising=False)

    env_file = _write_env(
        tmp_path,
        "XFILE_LOGIN_URL=https://admin.example.com/login\n"
        "XFILE_USERNAME=tester\n"
        "XFILE_PASSWORD=secret\n"
        "XFILE_POSTING_URLS=https://a.example.com\n"
        "XFILE_OUTPUT_DIR=custom_output\n",
    )

    config = load_config(env_path=str(env_file))

    assert config.output_dir == "custom_output"


def test_load_config_output_dir_defaults_to_output(tmp_path, monkeypatch):
    for key in (
        "XFILE_LOGIN_URL",
        "XFILE_USERNAME",
        "XFILE_PASSWORD",
        "XFILE_POSTING_URLS",
        "XFILE_HEADLESS",
        "XFILE_OUTPUT_DIR",
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

    assert config.output_dir == "output"


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
