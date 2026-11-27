# Executive Summary — CSCI 341 Assignment 3

**Project:** Research Conference and Paper Review Management System

| Member | Student ID | Contributions |
| --- | --- | --- |
| Yernur Slyamshaikhov | 202278977 | Part 1: relational schema from the Assignment 1 design (`sql/schema.sql`) with all PK/FK/UNIQUE/CHECK constraints, cascades and reviewer-pool composite FKs; sample data (`sql/seed.sql`) covering every required case; `pg_dump` export; schema/keys and business-rule sections of the README. |
| Yernur Kaltayev | 202232849 | Part 2: SQLAlchemy layer (`db.py`, `init_db.py`) and `part2_queries.py` for Tasks 1–8 with bound parameters, before/after output and rollback; aggregate queries, acceptance rate and the `accepted_paper_schedule` view (`sql/view.sql`); query parameter documentation and `part2_output.txt`. |
| Olzhas Nurseit | 202278977 | Part 3: Flask application (`app.py`, `templates/`) with CRUD for users, papers, reviews and sessions; self-review and session-assignment checks with transactions and error messages; deployment on Render with Neon PostgreSQL and keep-alive health check. |

All members: testing, video presentation and this summary.

**Completed work**

- Part 1: PostgreSQL schema with 15 relations, all required PK/FK/NOT NULL/UNIQUE/CHECK
  constraints, ON DELETE CASCADE from papers to versions, composite FKs keeping track
  coordinators and session chairs in the conference reviewer pool, and seed data covering every
  required case (12 users, 3 conferences, 12 papers, 15 versions, 16 reviews).
- Part 2: `part2_queries.py` runs Tasks 1–8 through SQLAlchemy with bound parameters, printing
  each SQL statement and result; updates/deletes show before/after and are rolled back.
- Part 3: Flask application with full CRUD for users (author/reviewer profiles), papers
  (authors, keywords, versions), reviews and sessions; enforces database constraints and both
  application checks (self-review, session assignment) with clear error messages; deployed on
  Render with persistent Neon PostgreSQL storage.

**Incomplete or non-working requirements:** None known. <edit if needed>

**Links:** see links.txt (video and application URL).
