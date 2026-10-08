"""Shared database configuration; never log credentials."""
import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg
from sqlalchemy import URL, create_engine, text

ROOT = Path(__file__).resolve().parents[1]


def connection_settings():
    load_dotenv(ROOT / ".env", override=False)
    password = os.environ.get("PG_PASSWORD")
    if not password or password == "replace-with-a-local-password":
        raise ValueError("Set PG_PASSWORD in .env or the environment.")
    return dict(
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        user=os.getenv("PG_USER", "medicare"),
        password=password,
        dbname=os.getenv("PG_DB", "medicare"),
    )


def get_conn():
    return psycopg.connect(**connection_settings(), connect_timeout=10)


def get_engine():
    settings = connection_settings()
    settings["database"] = settings.pop("dbname")
    settings["username"] = settings.pop("user")
    return create_engine(URL.create("postgresql+psycopg", **settings),
                         pool_pre_ping=True, connect_args={"connect_timeout": 10})


if __name__ == "__main__":
    with get_conn() as conn:
        print(conn.execute("select version()").fetchone()[0])
        schemas = conn.execute(
            "select schema_name from information_schema.schemata "
            "where schema_name in ('bronze', 'analysis') order by schema_name"
        ).fetchall()
        if schemas != [("analysis",), ("bronze",)]:
            raise RuntimeError("Required startup schemas are missing.")
        print("PASS: connection and startup schemas")
    engine = get_engine()
    try:
        with engine.connect() as conn:
            expected = connection_settings()["dbname"]
            if conn.execute(text("select current_database()")).scalar_one() != expected:
                raise RuntimeError("SQLAlchemy connected to an unexpected database.")
        print("PASS: SQLAlchemy connection")
    finally:
        engine.dispose()
