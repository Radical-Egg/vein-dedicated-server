#!/usr/bin/env python3
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from healthcheck import HeartbeatError
from healthcheck import parse_a2s_challenge
from healthcheck import parse_a2s_info


def test_parse_a2s_info_response():
    payload = (
        struct.pack("<lBB", -1, 0x49, 17)
        + b"Test Server\x00"
        + b"Farm\x00"
        + b"vein\x00"
        + b"VEIN\x00"
        + struct.pack("<H", 27015)
    )

    info = parse_a2s_info(payload)

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


def test_parse_a2s_challenge_response():
    payload = struct.pack("<lBl", -1, 0x41, 123456)

    assert parse_a2s_challenge(payload) == 123456
