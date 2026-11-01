"""Create local-only configuration with random secrets, without overwriting files."""

import secrets
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / ".env"
    if target.exists():
        raise SystemExit(
            ".env already exists; edit it manually (nothing was overwritten)."
        )
    content = (root / ".env.example").read_text(encoding="utf-8")
    password = secrets.token_hex(24)
    content = content.replace("POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={password}\n")
    content = content.replace("REPLACE_WITH_POSTGRES_PASSWORD", password)
    content = content.replace("JWT_SECRET=\n", f"JWT_SECRET={secrets.token_hex(32)}\n")
    content = content.replace(
        "GRAFANA_ADMIN_PASSWORD=\n", f"GRAFANA_ADMIN_PASSWORD={secrets.token_hex(24)}\n"
    )
    with target.open("x", encoding="utf-8") as stream:
        stream.write(content)
    target.chmod(0o600)
    print("Created .env with random local secrets. Do not commit this file.")


if __name__ == "__main__":
    main()
