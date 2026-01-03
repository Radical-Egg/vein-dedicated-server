#!/usr/bin/env python3

import socket
import logging
import sys
from os import environ

QUERY_PORT = environ.get("VEIN_QUERY_PORT", 27015)
GAME_PORT = environ.get("VEIN_GAME_PORT", 7777)

logging.basicConfig(level=logging.INFO)

class HeartbeatError(RuntimeError):
    pass

def heartbeat(host, port, test_packet, recvfrom=False, timeout=2):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    try:
        sock.sendto(test_packet, (host, port))
        if recvfrom:
            sock.recvfrom(4096)
    except socket.timeout as e:
        raise HeartbeatError(
            f"Timeout exceeded when attempting to heartbeat with port {port}: {e}"
        ) from e
    except OSError as e:
        raise HeartbeatError(
            f"Socket error heartbeating with port {port}: {e}"
        ) from e
    finally:
        sock.close()

if __name__ == "__main__":
    test_packet = b'\xff\xff\xff\xffTSource Engine Query\x00'

    try:
        heartbeat("127.0.0.1", QUERY_PORT, test_packet, recvfrom=True)
        heartbeat("127.0.0.1", GAME_PORT, b'heartbeat')
    except HeartbeatError as e:
        logging.error(e)
        sys.exit(1)

    sys.exit(0)
