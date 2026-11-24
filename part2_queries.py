"""CSCI 341 Assignment 3 - Part 2: SQL operations through Python and SQLAlchemy.

Runs every numbered task (1-8) against PostgreSQL and prints, for each task,
the SQL statement, its bound parameters and its result.

* Tasks 1 and 2 rebuild the schema and seed data (so this script always starts
  from the original seed dataset).
* Every update/delete (tasks 3 and 4) runs inside a transaction: the script
  shows the rows before, executes the statement, shows the rows after and
  then ROLLS BACK, so every later task again runs against the original seed.

Usage:
    DATABASE_URL=postgresql://user:pass@host:5432/confdb python part2_queries.py
Output is printed and also written to part2_output.txt.
"""
import sys
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

from db import SCHEMA_FILE, SEED_FILE, VIEW_FILE, get_engine, run_sql_file

OUTPUT_FILE = Path(__file__).resolve().parent / "part2_output.txt"

# ----------------------------------------------------------- query parameters
PARAMS = {
    "3.1": {"email": "arman.armanov@example.com", "phone": "+77773414141"},
    "3.2": {"city": "Astana", "astana_days": 7, "other_days": 3},
    "4.1": {"email": "amina.aminova@example.com", "status": "withdrawn"},
    "4.2": {"city": "Astana"},
    "5.1": {"status": "accepted"},
    "5.2": {"phrase": "machine learning"},
    "5.3": {"paper_id": 2},
    "5.4": {"conference_id": 1, "area": "Databases", "min_years": 3},
    "7":   {},
}

TABLES = ["app_user", "author", "author_research_area", "reviewer", "reviewer_expertise",
          "conference", "conference_host", "conference_reviewer", "track",
          "conference_session", "paper", "paper_keyword", "paper_author",
          "paper_version", "review"]


# ------------------------------------------------------------------ printing
class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)

    def flush(self):
        for st in self.streams:
            st.flush()


def fmt(v):
    if v is None:
        return "NULL"
    if isinstance(v, Decimal):
        return f"{v:.2f}"
    if isinstance(v, (datetime, date, time)):
        return v.isoformat(sep=" ") if isinstance(v, datetime) else v.isoformat()
    return str(v)


def print_table(result):
    cols = list(result.keys())
    rows = [[fmt(v) for v in r] for r in result.fetchall()]
    widths = [max(len(c), *(len(r[i]) for r in rows)) if rows else len(c)
              for i, c in enumerate(cols)]
    line = "+".join("-" * (w + 2) for w in widths)
    print("+" + line + "+")
    print("| " + " | ".join(c.ljust(w) for c, w in zip(cols, widths)) + " |")
    print("+" + line + "+")
    for r in rows:
        print("| " + " | ".join(v.ljust(w) for v, w in zip(r, widths)) + " |")
    print("+" + line + "+")
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})\n")


def heading(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def show_sql(sql, params=None):
    print("SQL:")
    for ln in sql.strip("\n").splitlines():
        print("    " + ln)
    if params:
        print(f"Bound parameters: {params}")
    print()


def run_query(conn, label, sql, params=None):
    print(f"--- {label}")
    show_sql(sql, params)
    print_table(conn.execute(text(sql), params or {}))


def run_mutation(engine, label, stmt, params, check_sql, check_params=None):
    """Before -> mutate -> after -> ROLLBACK (restores the seed state)."""
    heading(label)
    with engine.connect() as conn:
        trans = conn.begin()
        print("BEFORE:")
        show_sql(check_sql, check_params)
        print_table(conn.execute(text(check_sql), check_params or {}))

        print("STATEMENT:")
        show_sql(stmt, params)
        res = conn.execute(text(stmt), params)
        print(f"Rows affected: {res.rowcount}\n")

        print("AFTER (inside the same transaction):")
        print_table(conn.execute(text(check_sql), check_params or {}))

        trans.rollback()
        print("Transaction ROLLED BACK -> seed data restored. Re-check:")
        print_table(conn.execute(text(check_sql), check_params or {}))


# ------------------------------------------------------------------- tasks
def task_1_create(engine):
    heading("TASK 1 - Create statements (tables + constraints from sql/schema.sql)")
    print(f"Executing {SCHEMA_FILE.name} through SQLAlchemy (conn.exec_driver_sql) ...\n")
    with engine.begin() as conn:
        run_sql_file(conn, SCHEMA_FILE)
    with engine.connect() as conn:
        run_query(conn, "1a. Tables created", """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name""")
        run_query(conn, "1b. Constraints created (PK, FK, UNIQUE, CHECK)", """
SELECT tc.table_name, tc.constraint_type, tc.constraint_name
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'public'
  AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK')
  AND tc.constraint_name NOT LIKE '%_not_null'
ORDER BY tc.table_name, tc.constraint_type, tc.constraint_name""")


def task_2_insert(engine):
    heading("TASK 2 - Insert statements (seed data from sql/seed.sql)")
    print(f"Executing {SEED_FILE.name} through SQLAlchemy ...\n")
    with engine.begin() as conn:
        run_sql_file(conn, SEED_FILE)
    union = "\nUNION ALL\n".join(
        f"SELECT '{t}' AS table_name, COUNT(*) AS row_count FROM {t}" for t in TABLES)
    with engine.connect() as conn:
        run_query(conn, "2. Row count of every table", union)
    print("To restore this initial dataset at any time run:  python init_db.py")


def task_3_updates(engine):
    run_mutation(
        engine, "TASK 3.1 - Update Arman Armanov's phone number (identified by email)",
        """
UPDATE app_user
SET phone_number = :phone
WHERE email = :email""",
        PARAMS["3.1"],
        """
SELECT user_id, given_name, surname, email, phone_number
FROM app_user
WHERE email = :email""",
        {"email": PARAMS["3.1"]["email"]})

    run_mutation(
        engine, "TASK 3.2 - Extend review deadlines: +7 days in Astana, +3 days elsewhere (single UPDATE)",
        """
UPDATE conference
SET review_deadline = review_deadline +
    CASE WHEN city = :city THEN :astana_days ELSE :other_days END
-- PostgreSQL: DATE + INTEGER adds that many days""",
        PARAMS["3.2"],
        """
SELECT conference_id, acronym, city, review_deadline
FROM conference
ORDER BY conference_id""")


def task_4_deletes(engine):
    p = PARAMS["4.1"]
    check_41 = """
SELECT 'paper' AS table_name, COUNT(*) AS rows_total,
       COUNT(*) FILTER (WHERE status = 'withdrawn') AS withdrawn_papers
FROM paper
UNION ALL SELECT 'paper_author',  COUNT(*), NULL FROM paper_author
UNION ALL SELECT 'paper_keyword', COUNT(*), NULL FROM paper_keyword
UNION ALL SELECT 'paper_version', COUNT(*), NULL FROM paper_version
UNION ALL SELECT 'review',        COUNT(*), NULL FROM review
UNION ALL SELECT 'app_user',      COUNT(*), NULL FROM app_user
UNION ALL SELECT 'track',         COUNT(*), NULL FROM track
UNION ALL SELECT 'conference',    COUNT(*), NULL FROM conference"""
    heading("TASK 4.1 (context) - withdrawn papers and their corresponding authors")
    with engine.connect() as conn:
        run_query(conn, "Withdrawn papers", """
SELECT p.paper_id, p.title, p.status, u.email AS corresponding_author_email
FROM paper p
JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
JOIN app_user u      ON u.user_id = pa.author_id
WHERE p.status = :status
ORDER BY p.paper_id""", {"status": p["status"]})
    run_mutation(
        engine,
        "TASK 4.1 - Delete withdrawn papers whose corresponding author is Amina Aminova\n"
        "(paper_author, paper_keyword, paper_version and review rows are removed by ON DELETE CASCADE)",
        """
DELETE FROM paper p
WHERE p.status = :status
  AND EXISTS (SELECT 1
              FROM paper_author pa
              JOIN app_user u ON u.user_id = pa.author_id
              WHERE pa.paper_id = p.paper_id
                AND pa.is_corresponding
                AND u.email = :email)""",
        p, check_41)

    run_mutation(
        engine, "TASK 4.2 - Delete empty sessions of conferences held in Astana",
        """
DELETE FROM conference_session s
WHERE s.conference_id IN (SELECT conference_id FROM conference WHERE city = :city)
  AND NOT EXISTS (SELECT 1 FROM paper p WHERE p.session_id = s.session_id)""",
        PARAMS["4.2"],
        """
SELECT s.session_id, s.title, c.acronym, c.city,
       (SELECT COUNT(*) FROM paper p WHERE p.session_id = s.session_id) AS assigned_papers
FROM conference_session s
JOIN conference c ON c.conference_id = s.conference_id
ORDER BY s.session_id""")


def task_5_simple(engine):
    heading("TASK 5 - Simple queries")
    with engine.connect() as conn:
        run_query(conn, "5.1 Accepted papers with corresponding author, track and conference", """
SELECT p.paper_id, p.title,
       u.given_name || ' ' || u.surname AS corresponding_author,
       u.email AS corresponding_email,
       t.name AS track_name,
       c.conference_id, c.acronym
FROM paper p
JOIN track t         ON t.track_id = p.track_id
JOIN conference c    ON c.conference_id = t.conference_id
JOIN paper_author pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
JOIN app_user u      ON u.user_id = pa.author_id
WHERE p.status = :status
ORDER BY p.paper_id""", PARAMS["5.1"])

        run_query(conn, "5.2 Papers whose abstract contains 'machine learning' (case-insensitive)", """
SELECT p.paper_id, p.title
FROM paper p
WHERE p.abstract ILIKE '%' || :phrase || '%'
ORDER BY p.paper_id""", PARAMS["5.2"])

        run_query(conn, "5.3 Versions of the selected paper, highest version first", """
SELECT v.version_no, v.file_location, v.uploaded_at
FROM paper_version v
WHERE v.paper_id = :paper_id
ORDER BY v.version_no DESC""", PARAMS["5.3"])

        run_query(conn, "5.4 Pool reviewers with 'Databases' expertise and >= 3 years experience", """
SELECT u.user_id AS reviewer_id,
       u.given_name || ' ' || u.surname AS full_name,
       u.email
FROM conference_reviewer cr
JOIN reviewer r ON r.reviewer_id = cr.reviewer_id
JOIN app_user u ON u.user_id = r.reviewer_id
WHERE cr.conference_id = :conference_id
  AND r.years_experience >= :min_years
  AND EXISTS (SELECT 1 FROM reviewer_expertise e
              WHERE e.reviewer_id = r.reviewer_id AND e.area_label = :area)
ORDER BY u.user_id""", PARAMS["5.4"])


def task_6_complex(engine):
    heading("TASK 6 - Complex (aggregate) queries")
    with engine.connect() as conn:
        run_query(conn, "6.1 Papers and distinct authors per track (empty tracks report 0)", """
SELECT t.track_id, t.name AS track_name, t.conference_id,
       COUNT(DISTINCT p.paper_id)   AS paper_count,
       COUNT(DISTINCT pa.author_id) AS distinct_author_count
FROM track t
LEFT JOIN paper p         ON p.track_id = t.track_id
LEFT JOIN paper_author pa ON pa.paper_id = p.paper_id
GROUP BY t.track_id, t.name, t.conference_id
ORDER BY t.track_id""")

        run_query(conn, "6.2 Completed reviews and average overall score per reviewer", """
SELECT r.reviewer_id,
       u.given_name || ' ' || u.surname     AS full_name,
       COUNT(rv.review_id)                  AS review_count,
       ROUND(AVG(rv.overall_score), 2)      AS avg_overall_score
FROM reviewer r
JOIN app_user u     ON u.user_id = r.reviewer_id
LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
GROUP BY r.reviewer_id, u.given_name, u.surname
ORDER BY r.reviewer_id""")

        run_query(conn, "6.3 Per conference: total papers, accepted papers, average review score\n"
                        "    (paper counts and review averages are aggregated separately so\n"
                        "     multiple reviews cannot inflate paper counts)", """
WITH paper_counts AS (
    SELECT t.conference_id,
           COUNT(*)                                     AS total_papers,
           COUNT(*) FILTER (WHERE p.status = 'accepted') AS accepted_papers
    FROM paper p
    JOIN track t ON t.track_id = p.track_id
    GROUP BY t.conference_id
),
review_scores AS (
    SELECT t.conference_id, AVG(rv.overall_score) AS avg_score
    FROM review rv
    JOIN paper p ON p.paper_id = rv.paper_id
    JOIN track t ON t.track_id = p.track_id
    GROUP BY t.conference_id
)
SELECT c.conference_id, c.acronym,
       COALESCE(pc.total_papers, 0)    AS total_papers,
       COALESCE(pc.accepted_papers, 0) AS accepted_papers,
       ROUND(rs.avg_score, 2)          AS avg_overall_score
FROM conference c
LEFT JOIN paper_counts pc  ON pc.conference_id = c.conference_id
LEFT JOIN review_scores rs ON rs.conference_id = c.conference_id
ORDER BY c.conference_id""")

        run_query(conn, "6.4 Reviewers with more reviews than the average per reviewer\n"
                        "    (average includes reviewers with zero reviews)", """
WITH reviewer_counts AS (
    SELECT r.reviewer_id,
           u.given_name || ' ' || u.surname AS full_name,
           COUNT(rv.review_id)              AS review_count
    FROM reviewer r
    JOIN app_user u     ON u.user_id = r.reviewer_id
    LEFT JOIN review rv ON rv.reviewer_id = r.reviewer_id
    GROUP BY r.reviewer_id, u.given_name, u.surname
),
overall AS (
    SELECT AVG(review_count) AS avg_reviews_per_reviewer FROM reviewer_counts
)
SELECT rc.reviewer_id, rc.full_name, rc.review_count,
       ROUND(o.avg_reviews_per_reviewer, 2) AS avg_reviews_per_reviewer
FROM reviewer_counts rc
CROSS JOIN overall o
WHERE rc.review_count > o.avg_reviews_per_reviewer
ORDER BY rc.review_count DESC, rc.reviewer_id""")


def task_7_derived(engine):
    heading("TASK 7 - Derived attribute: acceptance rate per conference")
    with engine.connect() as conn:
        run_query(conn, "7. Acceptance rate = 100 * accepted / (accepted + rejected)", """
SELECT c.conference_id, c.acronym,
       COUNT(p.paper_id) FILTER (WHERE p.status = 'accepted') AS accepted_count,
       COUNT(p.paper_id) FILTER (WHERE p.status = 'rejected') AS rejected_count,
       ROUND(100.0 * COUNT(p.paper_id) FILTER (WHERE p.status = 'accepted')
             / NULLIF(COUNT(p.paper_id) FILTER (WHERE p.status IN ('accepted', 'rejected')), 0),
             2) AS acceptance_rate_pct
FROM conference c
LEFT JOIN track t ON t.conference_id = c.conference_id
LEFT JOIN paper p ON p.track_id = t.track_id
GROUP BY c.conference_id, c.acronym
ORDER BY c.conference_id""")


def task_8_view(engine):
    heading("TASK 8 - View accepted_paper_schedule")
    view_sql = VIEW_FILE.read_text(encoding="utf-8")
    print("Creating the view:")
    show_sql(view_sql)
    with engine.begin() as conn:
        run_sql_file(conn, VIEW_FILE)
    with engine.connect() as conn:
        run_query(conn, "8a. Confirm it is a VIEW (not a stored table)", """
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_name = 'accepted_paper_schedule'""")
        run_query(conn, "8b. Query the view", """
SELECT *
FROM accepted_paper_schedule
ORDER BY conference_id, session_date, start_time, session_id, paper_id""")


def main():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        original = sys.stdout
        sys.stdout = Tee(original, f)
        try:
            engine = get_engine()
            print("CSCI 341 Assignment 3 - Part 2 output")
            print(f"Run at {datetime.now():%Y-%m-%d %H:%M:%S}")
            with engine.connect() as conn:
                print(conn.execute(text("SELECT version()")).scalar_one())
            task_1_create(engine)
            task_2_insert(engine)
            task_3_updates(engine)
            task_4_deletes(engine)
            task_5_simple(engine)
            task_6_complex(engine)
            task_7_derived(engine)
            task_8_view(engine)
            print("\nAll tasks completed. Database is in the original seed state.")
        finally:
            sys.stdout = original


if __name__ == "__main__":
    main()
