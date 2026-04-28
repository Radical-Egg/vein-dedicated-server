#!/usr/bin/env python3
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

import healthcheck

from healthcheck import A2S_INFO_REQUEST
from healthcheck import HeartbeatError
from healthcheck import parse_a2s_challenge
from healthcheck import parse_a2s_info
from healthcheck import query_a2s_info


def a2s_info_payload(header=-1, response_type=0x49):
    return (
        struct.pack("<lBB", header, response_type, 17)
        + b"Test Server\x00"
        + b"Farm\x00"
        + b"vein\x00"
        + b"VEIN\x00"
        + struct.pack("<H", 27015)
    )


def test_parse_a2s_info_response():
    info = parse_a2s_info(a2s_info_payload())

    assert info == {
        "protocol": 17,
        "name": "Test Server",
        "map": "Farm",
        "folder": "vein",
        "game": "VEIN",
        "app_id": 27015,
    }


def test_parse_a2s_info_rejects_truncated_response():
    payload = struct.pack("<lBB", -1, 0x49, 17) + b"Missing terminators"

    with pytest.raises(HeartbeatError, match="missing null terminator"):
        parse_a2s_info(payload)


def test_parse_a2s_info_rejects_wrong_header():
    with pytest.raises(HeartbeatError, match="Unexpected A2S_INFO packet header"):
        parse_a2s_info(a2s_info_payload(header=0))


def test_parse_a2s_info_rejects_wrong_response_type():
    with pytest.raises(HeartbeatError, match="Unexpected A2S_INFO response type"):
        parse_a2s_info(a2s_info_payload(response_type=0x41))


def test_parse_a2s_info_rejects_missing_app_id():
    payload = (
        struct.pack("<lBB", -1, 0x49, 17)
        + b"Test Server\x00"
        + b"Farm\x00"
        + b"vein\x00"
        + b"VEIN\x00"
    )

    with pytest.raises(HeartbeatError, match="missing app id"):
        parse_a2s_info(payload)


def test_parse_a2s_challenge_response():
    payload = struct.pack("<lBl", -1, 0x41, 123456)

    assert parse_a2s_challenge(payload) == 123456


def test_parse_a2s_challenge_rejects_short_response():
    with pytest.raises(HeartbeatError, match="packet too short"):
        parse_a2s_challenge(b"\xff\xff")


def test_parse_a2s_challenge_rejects_wrong_response_type():
    payload = struct.pack("<lBl", -1, 0x49, 123456)

    with pytest.raises(HeartbeatError, match="Unexpected A2S challenge response type"):
        parse_a2s_challenge(payload)


def test_query_a2s_info_retries_with_challenge(monkeypatch):
    class FakeSocket:
        def __init__(self):
            self.closed = False
            self.sent = []
            self.timeout = None
            self.responses = [
                (struct.pack("<lBl", -1, 0x41, 123456), ("127.0.0.1", 27015)),
                (a2s_info_payload(), ("127.0.0.1", 27015)),
            ]

        def settimeout(self, timeout):
            self.timeout = timeout

        def sendto(self, payload, address):
            self.sent.append((payload, address))

        def recvfrom(self, _size):
            return self.responses.pop(0)

        def close(self):
            self.closed = True

    fake_socket = FakeSocket()
    monkeypatch.setattr(healthcheck.socket, "socket", lambda *_args: fake_socket)

    info = query_a2s_info("127.0.0.1", 27015, timeout=0.5)

    assert info["name"] == "Test Server"
    assert fake_socket.timeout == 0.5
    assert fake_socket.sent == [
        (A2S_INFO_REQUEST, ("127.0.0.1", 27015)),
        (A2S_INFO_REQUEST + struct.pack("<l", 123456), ("127.0.0.1", 27015)),
    ]
    assert fake_socket.closed is True
