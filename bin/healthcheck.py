#!/usr/bin/env python3

import socket
from os import environ

QUERY_PORT = environ.get("VEIN_QUERY_PORT", 27015)

def udp_healthcheck(host, port, test_packet, timeout=2):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    
    try:
        sock.sendto(test_packet, (host, port))
        data, _ = sock.recvfrom(4096)
        return True, data
    except socket.timeout:
        return False, None
    except Exception as e:
        return False, str(e)
    finally:
        sock.close()

if __name__ == "__main__":
    test_packet = b'\xff\xff\xff\xffTSource Engine Query\x00'
    alive, _ = udp_healthcheck("127.0.0.1", QUERY_PORT, test_packet)

    if not alive:
        exit(1)
