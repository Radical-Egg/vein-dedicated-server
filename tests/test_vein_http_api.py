#!/usr/bin/env python3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import vein_http_api


class FakeResponse:
    def __init__(self):
        self.raise_for_status_called = False

    def raise_for_status(self):
        self.raise_for_status_called = True


def test_call_endpoint_requests_save_endpoint(monkeypatch):
    calls = []
    response = FakeResponse()

    def fake_post(url, data, headers, timeout):
        calls.append((url, data, headers, timeout))
        return response

    monkeypatch.setattr(vein_http_api.requests, "post", fake_post)

    result = vein_http_api.call_endpoint("save", "vein", 8080, 3.5)

    assert result is response
    assert response.raise_for_status_called
    assert calls == [
        ("http://vein:8080/Save", b"", {"Content-Length": "0"}, 3.5)
    ]


def test_call_endpoint_requests_save_and_exit_endpoint(monkeypatch):
    calls = []

    def fake_post(url, data, headers, timeout):
        calls.append((url, data, headers, timeout))
        return FakeResponse()

    monkeypatch.setattr(vein_http_api.requests, "post", fake_post)

    vein_http_api.call_endpoint("save-and-exit", "127.0.0.1", 9090, 10)

    assert calls == [
        ("http://127.0.0.1:9090/SaveAndExit", b"", {"Content-Length": "0"}, 10)
    ]


def test_call_endpoint_requests_status_endpoint_with_get(monkeypatch):
    calls = []

    def fake_get(url, timeout):
        calls.append((url, timeout))
        return FakeResponse()

    monkeypatch.setattr(vein_http_api.requests, "get", fake_get)

    vein_http_api.call_endpoint("status", "vein", 8080, 10)

    assert calls == [("http://vein:8080/status", 10)]


def test_call_endpoint_wraps_request_errors(monkeypatch):
    def fake_post(_url, data, headers, timeout):
        raise vein_http_api.requests.RequestException("connection refused")

    monkeypatch.setattr(vein_http_api.requests, "post", fake_post)

    with pytest.raises(vein_http_api.VeinHttpApiError, match="connection refused"):
        vein_http_api.call_endpoint("save", "vein", 8080, 10)


def test_parse_args_uses_environment_defaults(monkeypatch):
    monkeypatch.setenv("VEIN_SERVER_HTTP_API_HOST", "vein")
    monkeypatch.setenv("VEIN_SERVER_HTTPPORT", "9090")
    monkeypatch.setenv("VEIN_SERVER_HTTP_API_TIMEOUT_SECONDS", "2.5")

    args = vein_http_api.parse_args(["save"])

    assert args.host == "vein"
    assert args.port == 9090
    assert args.timeout == 2.5


def test_main_returns_failure_for_api_errors(monkeypatch, capsys):
    def fake_call_endpoint(_action, _host, _port, _timeout):
        raise vein_http_api.VeinHttpApiError("boom")

    monkeypatch.setattr(vein_http_api, "call_endpoint", fake_call_endpoint)

    assert vein_http_api.main(["save"]) == 1
    assert "boom" in capsys.readouterr().err


def test_main_returns_success_for_completed_request(monkeypatch, capsys):
    calls = []

    def fake_call_endpoint(action, host, port, timeout):
        calls.append((action, host, port, timeout))

    monkeypatch.setattr(vein_http_api, "call_endpoint", fake_call_endpoint)

    assert vein_http_api.main(["save-and-exit", "--host", "vein"]) == 0
    assert calls == [("save-and-exit", "vein", 8080, 10.0)]
    assert "Requested /SaveAndExit successfully." in capsys.readouterr().out
