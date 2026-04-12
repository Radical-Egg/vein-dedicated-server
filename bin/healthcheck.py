#!/usr/bin/env python3

import socket
import logging
import sys
from os import environ

QUERY_PORT = int(environ.get("VEIN_QUERY_PORT", 27015))
GAME_PORT = int(environ.get("VEIN_GAME_PORT", 7777))

logging.basicConfig(level=logging.INFO)

class HeartbeatError(RuntimeError):
    pass

def is_udp_port_bound(port: int) -> bool:
    port_hex = f"{port:04X}"
    tables = ["/proc/net/udp", "/proc/net/udp6"]

    for table in tables:
        try:
            with open(table, "r", encoding="utf-8") as handle:
                next(handle, None)
                for line in handle:
                    fields = line.split()
                    if len(fields) < 2:
                        continue
                    local_address = fields[1]
                    _, local_port = local_address.rsplit(":", 1)
                    if local_port.upper() == port_hex:
                        return True
        except FileNotFoundError:
            continue

    return False

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
        if not is_udp_port_bound(GAME_PORT):
            raise HeartbeatError(f"Game UDP port {GAME_PORT} is not bound")
    except HeartbeatError as e:
        logging.error(e)
        sys.exit(1)

    sys.exit(0)
