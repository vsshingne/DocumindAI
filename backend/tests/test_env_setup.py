"""The local setup must produce usable settings without committing a credential URL."""

import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

from app.core.config import Settings


def test_generated_environment_loads_without_password_url(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "init_env.py").write_bytes(
        (root / "scripts" / "init_env.py").read_bytes()
    )
    (tmp_path / ".env.example").write_bytes((root / ".env.example").read_bytes())

    result = subprocess.run(
        [sys.executable, str(tmp_path / "scripts" / "init_env.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    values = dotenv_values(tmp_path / ".env")
    assert "DATABASE_URL" not in values
    assert values["POSTGRES_PASSWORD"]
    assert values["GRAFANA_ADMIN_PASSWORD"]
    assert values["JWT_SECRET"]
    assert values["POSTGRES_PASSWORD"] not in result.stdout

    settings = Settings(_env_file=tmp_path / ".env", app_env="development")
    url = make_url(settings.database_url.get_secret_value())
    assert url.host == "localhost"
    assert url.password == values["POSTGRES_PASSWORD"]
    assert values["POSTGRES_PASSWORD"] not in repr(settings)

    # Compose overrides a URL from older generated .env files so it can use the
    # PostgreSQL service hostname instead of localhost inside the container.
    with (tmp_path / ".env").open("a", encoding="utf-8") as stream:
        stream.write(f"DATABASE_URL={settings.database_url.get_secret_value()}\n")
    container_settings = Settings(
        _env_file=tmp_path / ".env",
        app_env="development",
        database_url="",
        postgres_host="postgres",
    )
    assert make_url(container_settings.database_url.get_secret_value()).host == "postgres"

    repeated = subprocess.run(
        [sys.executable, str(tmp_path / "scripts" / "init_env.py")],
        capture_output=True,
        text=True,
    )
    assert repeated.returncode != 0
    assert dotenv_values(tmp_path / ".env")["POSTGRES_PASSWORD"] == values["POSTGRES_PASSWORD"]
