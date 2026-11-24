"""Shared database helpers (SQLAlchemy engine + SQL script runner)."""
import os
from pathlib import Path

from sqlalchemy import create_engine, inspect

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "sql" / "schema.sql"
VIEW_FILE = BASE_DIR / "sql" / "view.sql"
SEED_FILE = BASE_DIR / "sql" / "seed.sql"

DEFAULT_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/confdb"


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", DEFAULT_URL)
    # Some hosts (Render, Heroku) hand out postgres:// URLs; SQLAlchemy needs postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def get_engine(echo: bool = False):
    return create_engine(database_url(), echo=echo, pool_pre_ping=True, future=True)


def run_sql_file(conn, path: Path) -> None:
    """Execute a multi-statement SQL script on an open SQLAlchemy connection.

    exec_driver_sql passes the script straight to psycopg2 (no bind-parameter
    parsing), so literals such as '09:00' are not mistaken for :params.
    """
    conn.exec_driver_sql(Path(path).read_text(encoding="utf-8"))


def create_schema(conn, with_view: bool = True) -> None:
    run_sql_file(conn, SCHEMA_FILE)
    if with_view:
        run_sql_file(conn, VIEW_FILE)


def load_seed(conn) -> None:
    run_sql_file(conn, SEED_FILE)


def reset_database(engine) -> None:
    """Drop + recreate all tables/views and load the seed data in one transaction."""
    with engine.begin() as conn:
        create_schema(conn)
        load_seed(conn)


def schema_exists(engine) -> bool:
    return inspect(engine).has_table("app_user")
