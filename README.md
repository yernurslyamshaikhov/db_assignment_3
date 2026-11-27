# CSCI 341 Assignment 3 — Research Conference and Paper Review Management System

PostgreSQL database + Python/SQLAlchemy query program (Part 2) + Flask web application (Part 3).

## 1. Software versions

| Component | Version |
|---|---|
| Python | 3.12 / 3.13 (tested on 3.13) |
| PostgreSQL | 16 (any 14+ works) |
| SQLAlchemy | 2.1.9 |
| psycopg2-binary | 2.9.13 |
| Flask | 3.1.3 |
| gunicorn (deployment) | 27.0.1 |

## 2. Project layout

```
sql/schema.sql        tables, keys, constraints, indexes (re-runnable: drops first)
sql/view.sql          Task 8 view accepted_paper_schedule
sql/seed.sql          sample data
dump/confdb_dump.sql  plain pg_dump export of schema + seed data + view
db.py                 SQLAlchemy engine + SQL-script runner (shared)
init_db.py            recreate schema + view + seed (restores the initial dataset)
part2_queries.py      Part 2 tasks 1–8, prints SQL, parameters, results
part2_output.txt      captured output of part2_queries.py
app.py, templates/    Part 3 Flask web application
requirements.txt      Python dependencies
render.yaml           deployment blueprint for Render
```

## 3. Setup and database restoration

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# create an empty database once
createdb -U postgres confdb        # or in psql: CREATE DATABASE confdb;

# point the programs at it (default is postgresql://postgres:postgres@localhost:5432/confdb)
set DATABASE_URL=postgresql://postgres:YOURPASSWORD@localhost:5432/confdb      # Windows cmd
$env:DATABASE_URL="postgresql://postgres:YOURPASSWORD@localhost:5432/confdb"  # PowerShell
export DATABASE_URL=postgresql://postgres:YOURPASSWORD@localhost:5432/confdb  # macOS/Linux
```

**Restore the initial dataset** (any time, any number of times):

* `python init_db.py` — drops and recreates all tables and the view, loads the seed, prints row counts; **or**
* `psql -U postgres -d confdb -f dump/confdb_dump.sql` into an empty database; **or**
* the "Reset database to seed data" button on the web app's home page.

## 4. Running Part 2 (queries)

```bash
python part2_queries.py
```

The program executes `sql/schema.sql` (Task 1) and `sql/seed.sql` (Task 2) through SQLAlchemy,
then runs Tasks 3–8. Every SQL statement is printed with its bound parameters and result.
Each update/delete runs inside a transaction: rows **before**, the statement and its row count,
rows **after**, then **ROLLBACK**, and a re-check showing the seed restored. Therefore every
mutation, query and the view run against the original seed. The full output is also written to
`part2_output.txt`. Note: running it re-creates the database (it is the "create" step), so any
changes made through the web app are replaced by the seed.

### Query parameter values

| Task | Parameters | Expected result on the seed |
|---|---|---|
| 3.1 | email = `arman.armanov@example.com`, phone = `+77773414141` | 1 row updated |
| 3.2 | city = `Astana` → +7 days, otherwise +3 days | 3 rows (1 Astana, 2 elsewhere: both branches) |
| 4.1 | email = `amina.aminova@example.com`, status = `withdrawn` | papers 10, 11 deleted (paper 12 is withdrawn but Amina is not corresponding → kept); cascades remove 3 authorships, 4 keywords, 2 versions, 2 reviews |
| 4.2 | city = `Astana` | session 3 deleted; empty Almaty session 5 and nonempty sessions kept |
| 5.1 | status = `accepted` | papers 1, 2, 3, 4, 7 |
| 5.2 | phrase = `machine learning` (ILIKE) | papers 3 ("Machine Learning"), 6, 10 |
| 5.3 | paper_id = `2` | versions 3, 1 (gap at 2) |
| 5.4 | conference_id = `1`, area = `Databases`, min_years = `3` | reviewers 1, 3, 8 (Timur has 2 years; Elena is not in pool 1) |
| 6.1–6.4, 7, 8 | none | 6.4 average = 2.00 → reviewers 3, 1, 6 |

## 5. Running the web application locally

```bash
python app.py            # http://127.0.0.1:5000
# or: gunicorn app:app
```

On first start with an empty database the app creates the schema and seed automatically
(`AUTO_INIT_DB=1`, default). Environment variables: `DATABASE_URL`, `SECRET_KEY`,
`ALLOW_RESET` (`1` shows the reset button, default), `AUTO_INIT_DB`.

No authentication is used (not required); no demo credentials are needed.

### Running with Docker (PostgreSQL + web app)

```bash
docker compose up --build          # http://localhost:8000
docker compose exec web python part2_queries.py   # run Part 2 inside the container
docker compose exec web python init_db.py         # re-create and re-seed the database
docker compose down -v             # stop and delete the database volume
```

The `db` service runs PostgreSQL 16 (database `confdb`, user/password `postgres`/`postgres`,
also exposed on `localhost:5432`); the `web` service seeds it automatically on first start.

### Deployment (free): Neon PostgreSQL + Render web service

1. **Database** — create a free project at neon.tech (region e.g. AWS Frankfurt, eu-central-1);
   copy its **pooled** connection string
   (`postgresql://user:pass@ep-...-pooler...neon.tech/neondb?sslmode=require`). Neon storage is persistent
   (unlike Render's free PostgreSQL, which expires after 30 days).
2. **Code** — push this folder to a GitHub repository.
3. **Web service** — on render.com: *New → Blueprint* → select the repo (uses `render.yaml`), region
   Frankfurt, and set `DATABASE_URL` to the Neon string. (Manual alternative: *New → Web Service*,
   build `pip install -r requirements.txt`, start `gunicorn app:app --bind 0.0.0.0:$PORT`,
   instance type *Free*, health check path `/healthz`, env vars `DATABASE_URL` and `SECRET_KEY`.)
4. Open the `https://<name>.onrender.com` URL; the first request creates and seeds the database.
5. **Keep it awake** — free Render services sleep after 15 min without traffic (the next request
   then takes ~1 minute). Create a free job at cron-job.org (or an UptimeRobot monitor) that sends
   `GET https://<name>.onrender.com/healthz` **every 10 minutes**. One always-on service uses
   ~744 of Render's 750 free hours per month. `/healthz` does not query the database, so Neon
   still scales to zero between real visits (it wakes in under a second) and stays within its
   free compute hours.
6. Put the URL in `links.txt`.

## 6. Schema, keys and references

PK = primary key, FK = foreign key. All columns are NOT NULL unless marked *optional*.

| Relation | Primary key | Foreign keys (ON DELETE action) | Other constraints |
|---|---|---|---|
| app_user(user_id, given_name, surname, email, affiliation, country, phone_number) | user_id (identity) | — | UNIQUE(email) |
| author(author_id, orcid *optional*) | author_id | author_id → app_user (CASCADE) | UNIQUE(orcid) |
| author_research_area(author_id, area_label) | (author_id, area_label) | author_id → author (CASCADE) | |
| reviewer(reviewer_id, years_experience) | reviewer_id | reviewer_id → app_user (CASCADE) | CHECK years_experience ≥ 0 |
| reviewer_expertise(reviewer_id, area_label) | (reviewer_id, area_label) | reviewer_id → reviewer (CASCADE) | |
| conference(conference_id, name, acronym, description, city, country, start_date, end_date, submission_deadline, review_deadline) | conference_id | — | CHECK end_date ≥ start_date |
| conference_host(conference_id, host_name) | (conference_id, host_name) | conference_id → conference (CASCADE) | |
| conference_reviewer(conference_id, reviewer_id) | (conference_id, reviewer_id) | conference_id → conference (CASCADE); reviewer_id → reviewer (CASCADE) | |
| track(track_id, conference_id, name, description, research_area, coordinator_id) | track_id | conference_id → conference (CASCADE); coordinator_id → reviewer (NO ACTION); (conference_id, coordinator_id) → conference_reviewer (NO ACTION) | |
| conference_session(session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) | session_id | conference_id → conference (CASCADE); chair_id → reviewer (NO ACTION); (conference_id, chair_id) → conference_reviewer (NO ACTION) | CHECK end_time > start_time |
| paper(paper_id, track_id, title, abstract, submission_date, status, session_id *optional*) | paper_id | track_id → track (NO ACTION); session_id → conference_session (SET NULL) | CHECK status ∈ {submitted, under review, accepted, rejected, withdrawn} |
| paper_keyword(paper_id, keyword) | (paper_id, keyword) | paper_id → paper (CASCADE) | |
| paper_author(paper_id, author_id, author_position, is_corresponding) | (paper_id, author_id) | paper_id → paper (CASCADE); author_id → author (NO ACTION) | UNIQUE(paper_id, author_position); CHECK author_position > 0; partial UNIQUE index: one row with is_corresponding per paper |
| paper_version(paper_id, version_no, file_location, uploaded_at, change_note *optional*) — weak entity | (paper_id, version_no) | paper_id → paper (**CASCADE**) | CHECK version_no > 0 |
| review(review_id, paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, confidential_comments *optional*, review_submission_date) | review_id | paper_id → paper (CASCADE); reviewer_id → reviewer (NO ACTION) | UNIQUE(paper_id, reviewer_id); CHECK overall_score BETWEEN 1 AND 5 (INTEGER); CHECK recommendation ∈ {accept, reject} |

View: `accepted_paper_schedule` (sql/view.sql) — a real view, not a table.

**Deletion behaviour (documented choices).** Deleting a paper cascades to its versions,
keywords, authorships and reviews. Deleting a session un-schedules its papers (SET NULL).
Deleting a conference removes its hosts, reviewer-pool memberships, tracks and sessions but
never users/reviewers; it is rejected while its tracks still contain papers. Deleting a user
removes their author/reviewer profiles, labels and pool memberships, but is **rejected** if they
author a paper, have written a review, coordinate a track or chair a session (keeps the
"at least one author" rule and review history intact). Foreign keys are never disabled.

Multivalued labels (research areas, expertise areas, host names, keywords) are stored in
separate relations; author lists are stored in paper_author. No comma-separated fields are stored
(the web forms accept comma-separated input and split it into rows).

## 7. Required checks

Database constraints: all PK/FK/NOT NULL/UNIQUE/CHECK constraints listed above.

Application checks (app.py, run inside the same transaction as the change; a violation rolls back
the whole change and the error is shown in a red message):

1. **No self-reviews** — `save_review` rejects a review whose reviewer is an author of the paper;
   `check_no_self_review` runs after every change to a paper's author list and rejects the change if
   a new author has already reviewed the paper.
2. **Valid session assignments** — `check_paper_session` requires a scheduled paper to be
   `accepted` and its track's conference to equal the session's conference. It runs when a paper
   is assigned (session page or paper form), when a paper's status/track/session changes, and
   for every assigned paper when a session's conference changes. Invalid changes are **rejected**.

## 8. Other business rules (Assignment 1)

All hold in the sample data. Enforcement:

| Rule | Enforced? | How |
|---|---|---|
| Every user is an author, a reviewer or both | Yes (app) | user form requires ≥1 role |
| Author has ≥1 research area; reviewer has ≥1 expertise area | Yes (app) | user form |
| Paper has ≥1 author | Yes (app) | paper form; author with papers cannot be deleted (FK) |
| Exactly one corresponding author per paper | Yes | at most one: DB partial unique index; at least one: app |
| Paper has ≥1 keyword | Yes (app) | paper form |
| Paper has ≥1 version | Yes (app) | v1 required on creation; last version cannot be deleted |
| Track coordinator and session chair belong to the conference's reviewer pool | Yes (DB) | composite FKs to conference_reviewer |
| Conference has ≥1 host, ≥1 track, ≥1 pool reviewer | No (seed data only) | supporting tables are seed-managed |
| Removing a conference keeps users/reviewers | Yes (DB) | cascade stops at conference_reviewer |
| Review dates/deadline consistency | No | not required |

## 9. Design assumptions

* The relational schema implements my Assignment 1 EER/UML design without material changes.
  The design follows the Assignment 1 specification and matches the Appendix A reference schema:
  AUTHOR and REVIEWER are overlapping, total subclasses of APP_USER with a shared primary key;
  PAPER_VERSION is a weak entity identified by (paper_id, version_no); multivalued labels
  (research areas, expertise areas, host institutions, keywords) are stored in separate relations;
  authorship and reviewer pools are M:N relations.
* Phone numbers are stored as text; ORCID is optional but unique when present.
* Author positions are renumbered 1..n in row order whenever the author list is edited.
* Status changes away from `accepted` for a scheduled paper are rejected (the user must
  unassign it first) rather than silently unscheduling it.
* The web app provides CRUD for users (with author/reviewer profiles and pool membership),
  papers (authors, keywords, versions), reviews and sessions (including assigning papers);
  conferences and tracks are read-only.

## 10. Sample data coverage

12 users (author-only 2, 5, 9, 12; reviewer-only 3, 6, 8, 10; both 1, 4, 7, 11), 3 conferences
(Astana, Almaty, Tashkent — the Tashkent one has no papers), 6 tracks (3 and 6 empty),
5 sessions (3 = empty Astana session, 5 = empty Almaty session), 12 papers with all five
statuses, multiple authors and versions, 15 versions, 16 completed reviews with review counts
0–4 (Nurlan Zhakupov has none), accepted papers with sessions (1, 2, 3, 7) and without (4),
Amina Aminova as corresponding author of withdrawn papers 10 and 11.

## 11. Suggested video demo (≈10 min)

1. `python init_db.py` / start of `part2_queries.py` (Tasks 1–2, row counts).
2. Scroll through Tasks 3–8 in the output (before/after/rollback, each query).
3. Web app: create → edit → delete a user, a paper (add/delete a version), a review, a session.
4. Rejections: review of paper 2 by Arman Armanov (self-review); add Arman as author of paper 1
   (he reviewed it); assign paper 7 (CASAI) to session 3 (AICDS); assign submitted paper 9.
5. Reset button to restore the seed.
