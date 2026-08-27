import pytest
import requests

from agent_selection.xfile_api_client import XfileApiAuthError, extract_job_posting_id, login


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


def test_extract_job_posting_id_from_detail_url():
    posting_id = extract_job_posting_id("https://console.ex-pile.com/job-posting/31a6d72d-e9bb")

    assert posting_id == "31a6d72d-e9bb"


def test_extract_job_posting_id_ignores_trailing_slash():
    posting_id = extract_job_posting_id("https://console.ex-pile.com/job-posting/abc123/")

    assert posting_id == "abc123"
