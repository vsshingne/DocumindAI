"""Bounded startup probe without relying on utilities inside Qdrant's image."""

import time

import httpx

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    headers = {}
    if settings.qdrant_api_key:
        headers["api-key"] = settings.qdrant_api_key.get_secret_value()
    with httpx.Client(timeout=3) as client:
        for attempt in range(30):
            try:
                client.get(
                    settings.qdrant_url.rstrip("/") + "/readyz", headers=headers
                ).raise_for_status()
                return
            except httpx.HTTPError:
                if attempt == 29:
                    raise SystemExit("Qdrant failed readiness after 30 attempts") from None
                time.sleep(2)


if __name__ == "__main__":
    main()
