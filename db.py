import os
from pathlib import Path

from sqlalchemy import create_engine, inspect

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "sql" / "schema.sql"
VIEW_FILE = BASE_DIR / "sql" / "view.sql"
SEED_FILE = BASE_DIR / "sql" / "seed.sql"

DEFAULT_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/confdb"


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", DEFAULT_URL).strip().strip("'\"")
    # Tolerate a pasted "psql 'postgresql://...'" command from the Neon console
    if url.startswith("psql "):
        url = url[5:].strip().strip("'\"")
    if not url.startswith(("postgres://", "postgresql://", "postgresql+")):
        scheme = url.split("://", 1)[0] if "://" in url else url[:20]
        raise RuntimeError(
            f"DATABASE_URL must be a PostgreSQL connection string "
            f"(postgresql://user:password@host/dbname?sslmode=require), but it starts with "
            f"'{scheme}'. In Neon use Dashboard -> Connect -> 'Connection string', "
            f"not the project web/REST URL.")
    # Some hosts (Render, Heroku) hand out postgres:// URLs; SQLAlchemy needs postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def get_engine(echo: bool = False):
    return create_engine(database_url(), echo=echo, pool_pre_ping=True, future=True)


def run_sql_file(conn, path: Path) -> None:
    conn.exec_driver_sql(Path(path).read_text(encoding="utf-8"))


def create_schema(conn, with_view: bool = True) -> None:
    run_sql_file(conn, SCHEMA_FILE)
    if with_view:
        run_sql_file(conn, VIEW_FILE)


def load_seed(conn) -> None:
    run_sql_file(conn, SEED_FILE)


def reset_database(engine) -> None:
    with engine.begin() as conn:
        create_schema(conn)
        load_seed(conn)


def schema_exists(engine) -> bool:
    return inspect(engine).has_table("app_user")
