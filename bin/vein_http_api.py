#!/usr/bin/env python3
"""Small CLI for VEIN dedicated server HTTP API save endpoints."""

import argparse
import os
import sys

try:
    import requests
except ModuleNotFoundError:
    requests = None


ENDPOINTS = {
    "weather": "weather",
    "status": "status",
    "time": "time",
    "players": "players"
}

POST_ENDPOINTS = {
    "save",
    "save-and-exit",
}


class VeinHttpApiError(RuntimeError):
    pass

def call_endpoint(action, host, port, timeout):
    if requests is None:
        raise VeinHttpApiError(
            "Missing Python dependency: requests. Install it from requirements.txt."
        )

    endpoint = ENDPOINTS[action]
    url = f"http://{host}:{port}/{endpoint}"

    try:
        if action in POST_ENDPOINTS:
            response = requests.post(
                url,
                data=b"",
                headers={"Content-Length": "0"},
                timeout=timeout,
            )
        else:
            response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as e:
        raise VeinHttpApiError(f"Request to {url} failed: {e}") from e

    return response


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Call VEIN dedicated server HTTP API save endpoints."
    )
    parser.add_argument(
        "action",
        choices=sorted(ENDPOINTS),
        help="HTTP API action to request.",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("VEIN_SERVER_HTTP_API_HOST", "127.0.0.1"),
        help="HTTP API host. Defaults to VEIN_SERVER_HTTP_API_HOST or 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        default=os.environ.get("VEIN_SERVER_HTTPPORT", "8080"),
        type=int,
        help="HTTP API port. Defaults to VEIN_SERVER_HTTPPORT or 8080.",
    )
    parser.add_argument(
        "--timeout",
        default=os.environ.get("VEIN_SERVER_HTTP_API_TIMEOUT_SECONDS", "10"),
        type=float,
        help=(
            "Request timeout in seconds. Defaults to "
            "VEIN_SERVER_HTTP_API_TIMEOUT_SECONDS or 10."
        ),
    )

    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        call_endpoint(args.action, args.host, args.port, args.timeout)
    except VeinHttpApiError as e:
        print(e, file=sys.stderr)
        return 1

    print(f"Requested /{ENDPOINTS[args.action]} successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
