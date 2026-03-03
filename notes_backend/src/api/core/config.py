import os
from dataclasses import dataclass


def _read_db_url_from_db_connection_txt() -> str | None:
    """
    Read Postgres connection string using the notes_database convention.

    notes_database/db_connection.txt contains a command like:
      psql postgresql://user:pass@host:port/db

    This function extracts the URI portion.
    """
    # Path: backend container is note-organizer-*/notes_backend
    # notes_database lives in sibling workspace note-organizer-*/notes_database
    # In this mono-workspace, we can reference relative paths from this file's cwd at runtime,
    # but safest is to allow an env override first.
    candidates = [
        # Common when running from notes_backend container root:
        os.path.abspath(os.path.join(os.getcwd(), "..", "notes_database", "db_connection.txt")),
        # Common when running from src/:
        os.path.abspath(os.path.join(os.getcwd(), "..", "..", "..", "notes_database", "db_connection.txt")),
        # A fallback: use a workspace-known relative path if started at repo root:
        os.path.abspath(
            os.path.join(
                os.getcwd(),
                "note-organizer-235585-235650",
                "notes_database",
                "db_connection.txt",
            )
        ),
    ]

    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read().strip()
            if not raw:
                continue
            if raw.startswith("psql "):
                return raw[len("psql ") :].strip()
            return raw
        except OSError:
            continue

    return None


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_name: str
    app_version: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_exp_minutes: int
    cors_origins: list[str]
    database_url: str


# PUBLIC_INTERFACE
def get_settings() -> Settings:
    """
    Load settings from env vars.

    Required env vars:
    - JWT_SECRET_KEY: secret used to sign JWTs
    Optional env vars:
    - DATABASE_URL: Postgres URI. If not provided, we attempt to read notes_database/db_connection.txt
    - CORS_ORIGINS: comma-separated list of allowed origins (e.g. http://localhost:3000,https://...).
      If omitted, defaults to '*' behavior is NOT used (for credentialed requests); we default to localhost+frontend URL.
    """
    # NOTE: Orchestrator should set JWT_SECRET_KEY in notes_backend/.env
    jwt_secret_key = os.getenv("JWT_SECRET_KEY", "").strip()
    if not jwt_secret_key:
        raise RuntimeError("Missing required env var JWT_SECRET_KEY")

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        from_txt = _read_db_url_from_db_connection_txt()
        if not from_txt:
            raise RuntimeError(
                "Missing DATABASE_URL and could not locate notes_database/db_connection.txt to infer it."
            )
        database_url = from_txt

    cors_raw = os.getenv("CORS_ORIGINS", "").strip()
    if cors_raw:
        cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]
    else:
        # Sensible dev defaults. Next.js frontend is typically on :3000.
        cors_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    return Settings(
        app_name=os.getenv("APP_NAME", "Notes API"),
        app_version=os.getenv("APP_VERSION", "1.0.0"),
        jwt_secret_key=jwt_secret_key,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_exp_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        cors_origins=cors_origins,
        database_url=database_url,
    )
