#!/usr/bin/env python3
# Send a heartbeat query to the game server and check that it responds with valid information.
# The A2S_INFO query can be used to get information about the steamcmd server.
# https://developer.valvesoftware.com/wiki/Server_queries

import logging
import socket
import struct
import sys
from os import environ

QUERY_HOST = environ.get("VEIN_HEARTBEAT_QUERY_HOST", "127.0.0.1")
QUERY_PORT = int(environ.get("VEIN_QUERY_PORT", 27015))

logging.basicConfig(level=logging.INFO)

A2S_INFO_REQUEST = b"\xff\xff\xff\xffTSource Engine Query\x00"
A2S_HEADER = -1
A2S_INFO_RESPONSE = 0x49
A2S_CHALLENGE_RESPONSE = 0x41


class HeartbeatError(RuntimeError):
    pass


def read_cstring(payload, offset):
    end = payload.find(b"\x00", offset)
    if end == -1:
        raise HeartbeatError("Malformed A2S_INFO response: missing null terminator")

    return payload[offset:end].decode("utf-8", errors="replace"), end + 1


def parse_a2s_info(payload):
    if len(payload) < 6:
        raise HeartbeatError("Malformed A2S_INFO response: packet too short")

    header, response_type = struct.unpack_from("<lB", payload, 0)
    if header != A2S_HEADER:
        raise HeartbeatError(
            f"Unexpected A2S_INFO packet header: {header!r}"
        )

    if response_type != A2S_INFO_RESPONSE:
        raise HeartbeatError(
            f"Unexpected A2S_INFO response type: 0x{response_type:02x}"
        )

    offset = 5
    protocol = payload[offset]
    offset += 1

    name, offset = read_cstring(payload, offset)
    map_name, offset = read_cstring(payload, offset)
    folder, offset = read_cstring(payload, offset)
    game, offset = read_cstring(payload, offset)

    if len(payload) < offset + 2:
        raise HeartbeatError("Malformed A2S_INFO response: missing app id")

    app_id = struct.unpack_from("<H", payload, offset)[0]

    return {
        "protocol": protocol,
        "name": name,
        "map": map_name,
        "folder": folder,
        "game": game,
        "app_id": app_id,
    }


def parse_a2s_challenge(payload):
    if len(payload) < 9:
        raise HeartbeatError("Malformed A2S challenge response: packet too short")

    header, response_type = struct.unpack_from("<lB", payload, 0)
    if header != A2S_HEADER:
        raise HeartbeatError(
            f"Unexpected A2S challenge packet header: {header!r}"
        )

    if response_type != A2S_CHALLENGE_RESPONSE:
        raise HeartbeatError(
            f"Unexpected A2S challenge response type: 0x{response_type:02x}"
        )

    return struct.unpack_from("<l", payload, 5)[0]


def query_a2s_info(host, port, timeout=2):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    try:
        sock.sendto(A2S_INFO_REQUEST, (host, port))
        payload, _ = sock.recvfrom(4096)

        if len(payload) >= 5 and payload[4] == A2S_CHALLENGE_RESPONSE:
            challenge = parse_a2s_challenge(payload)
            sock.sendto(A2S_INFO_REQUEST + struct.pack("<l", challenge), (host, port))
            payload, _ = sock.recvfrom(4096)
    except socket.timeout as e:
        raise HeartbeatError(
            f"Timeout exceeded when attempting A2S_INFO query on port {port}: {e}"
        ) from e
    except OSError as e:
        raise HeartbeatError(
            f"Socket error while querying A2S_INFO on port {port}: {e}"
        ) from e
    finally:
        sock.close()

    return parse_a2s_info(payload)


if __name__ == "__main__":
    try:
        info = query_a2s_info(QUERY_HOST, QUERY_PORT)
        logging.info(
            "A2S_INFO OK: name=%s game=%s app_id=%s protocol=%s",
            info["name"],
            info["game"],
            info["app_id"],
            info["protocol"],
        )
    except HeartbeatError as e:
        logging.error(e)
        sys.exit(1)

    sys.exit(0)
