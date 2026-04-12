import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from healthcheck import is_udp_port_bound


def test_is_udp_port_bound_detects_unbound_port():
    assert is_udp_port_bound(65534) is False
