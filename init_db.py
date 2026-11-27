from sqlalchemy import text

from db import get_engine, reset_database

TABLES = ["app_user", "author", "author_research_area", "reviewer", "reviewer_expertise",
          "conference", "conference_host", "conference_reviewer", "track",
          "conference_session", "paper", "paper_keyword", "paper_author",
          "paper_version", "review"]

if __name__ == "__main__":
    engine = get_engine()
    reset_database(engine)
    with engine.connect() as conn:
        for t in TABLES:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one()
            print(f"{t:<22} {n:>4} rows")
    print("Database recreated and seeded.")
