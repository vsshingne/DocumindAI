"""Validate an already-started Compose deployment without third-party dependencies."""

import json
from urllib.request import urlopen


def main() -> None:
    for endpoint in ("live", "ready"):
        with urlopen(
            f"http://127.0.0.1:8000/api/v1/health/{endpoint}", timeout=15
        ) as response:
            payload = json.load(response)
            if response.status != 200 or payload["status"] != "ok":
                raise SystemExit(f"{endpoint} failed")
            if endpoint == "ready" and not all(payload["dependencies"].values()):
                raise SystemExit("A dependency is not ready")
        print(f"{endpoint}: passed")
    with urlopen("http://127.0.0.1:8000/metrics", timeout=5) as response:
        if "documind_http_requests_total" not in response.read().decode():
            raise SystemExit("Request metrics missing")
    print("metrics: passed")


if __name__ == "__main__":
    main()
