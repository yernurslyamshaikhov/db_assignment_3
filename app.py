"""CSCI 341 Assignment 3 - Part 3: Flask web application.

CRUD for users (with author/reviewer profiles), papers (with authorship,
keywords and versions), reviews and sessions. All SQL goes through
SQLAlchemy Core with bound parameters; each request that changes data runs
in one transaction (engine.begin()), so a failed check rolls everything back.

Required application checks (see check_* functions):
  1. no self-reviews (on review save AND on paper-author changes)
  2. session assignments: paper must be accepted and its track's conference
     must equal the session's conference (on assignment, paper status/track
     change, and session conference change)
"""
import os
from datetime import datetime

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from db import get_engine, reset_database, schema_exists

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
engine = get_engine()

STATUSES = ["submitted", "under review", "accepted", "rejected", "withdrawn"]
MAX_AUTHORS = 6

# Friendly messages for named database constraints
CONSTRAINT_MESSAGES = {
    "uq_app_user_email": "A user with this email already exists.",
    "author_orcid_key": "This ORCID is already used by another author.",
    "ck_reviewer_experience": "Years of reviewing experience must be 0 or more.",
    "uq_paper_author_position": "Author positions must be unique within a paper.",
    "ck_author_position": "Author positions must be positive integers.",
    "uq_one_corresponding_author": "A paper can have only one corresponding author.",
    "ck_paper_status": "Invalid paper status.",
    "paper_version_pkey": "This version number already exists for the paper.",
    "ck_version_no": "Version numbers must be positive integers.",
    "uq_review_paper_reviewer": "This reviewer has already reviewed this paper (one review per reviewer and paper).",
    "ck_review_score": "Overall score must be an integer from 1 to 5.",
    "ck_review_recommendation": "Recommendation must be 'accept' or 'reject'.",
    "ck_session_times": "Session end time must be later than its start time.",
    "fk_session_chair_pool": "The session chair must belong to the conference's reviewer pool.",
    "fk_track_coordinator_pool": "This reviewer coordinates a track of that conference and must stay in its pool.",
    "paper_author_author_id_fkey": "This user authors papers, so the author role/user cannot be removed.",
    "review_reviewer_id_fkey": "This reviewer has submitted reviews, so the reviewer role/user cannot be removed.",
    "track_coordinator_id_fkey": "This reviewer coordinates a track, so the reviewer role/user cannot be removed.",
    "conference_session_chair_id_fkey": "This reviewer chairs a session, so the reviewer role/user cannot be removed.",
}


class AppError(Exception):
    """Business-rule violation detected by the application (causes rollback)."""


def db_error_message(e: DBAPIError) -> str:
    diag = getattr(e.orig, "diag", None)
    cname = getattr(diag, "constraint_name", None) if diag else None
    if cname in CONSTRAINT_MESSAGES:
        return f"{CONSTRAINT_MESSAGES[cname]} (database constraint {cname})"
    primary = getattr(diag, "message_primary", None) if diag else None
    return f"Database rejected the change: {primary or str(e.orig).splitlines()[0]}"


def run_tx(fn):
    """Run fn(conn) in one transaction. Returns (ok, result). Flashes errors."""
    try:
        with engine.begin() as conn:
            return True, fn(conn)
    except AppError as e:
        flash(str(e), "error")
    except (IntegrityError, DBAPIError) as e:
        flash(db_error_message(e), "error")
    return False, None


def rows(sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()


def one(sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().first()


def split_labels(s):
    seen, out = set(), []
    for part in (s or "").replace("\n", ",").split(","):
        p = part.strip()
        if p and p.lower() not in seen:
            seen.add(p.lower())
            out.append(p)
    return out


def to_int(v, field, required=True):
    if v in (None, ""):
        if required:
            raise AppError(f"{field} is required.")
        return None
    try:
        return int(v)
    except ValueError:
        raise AppError(f"{field} must be an integer.")


def req(form, field, label):
    v = (form.get(field) or "").strip()
    if not v:
        raise AppError(f"{label} is required.")
    return v


# ======================================================= required app checks
def check_no_self_review(conn, paper_id):
    """Check 1: no review of this paper may be written by one of its authors."""
    bad = conn.execute(text("""
        SELECT u.given_name || ' ' || u.surname AS name
        FROM review r
        JOIN paper_author pa ON pa.paper_id = r.paper_id AND pa.author_id = r.reviewer_id
        JOIN app_user u ON u.user_id = r.reviewer_id
        WHERE r.paper_id = :pid"""), {"pid": paper_id}).scalars().all()
    if bad:
        raise AppError("Self-review rejected: " + ", ".join(bad) +
                       " is an author of this paper and has also reviewed it.")


def check_paper_session(conn, paper_id):
    """Check 2: a scheduled paper must be accepted and in the session's conference."""
    r = conn.execute(text("""
        SELECT p.title, p.status, p.session_id, t.conference_id AS track_conf,
               s.conference_id AS session_conf
        FROM paper p
        JOIN track t ON t.track_id = p.track_id
        LEFT JOIN conference_session s ON s.session_id = p.session_id
        WHERE p.paper_id = :pid"""), {"pid": paper_id}).mappings().first()
    if r is None or r["session_id"] is None:
        return
    if r["status"] != "accepted":
        raise AppError(f"Invalid session assignment: paper '{r['title']}' has status "
                       f"'{r['status']}'; only accepted papers can be assigned to a session.")
    if r["track_conf"] != r["session_conf"]:
        raise AppError(f"Invalid session assignment: paper '{r['title']}' belongs to a track of "
                       f"conference {r['track_conf']} but session {r['session_id']} belongs to "
                       f"conference {r['session_conf']}.")


# ===================================================================== home
@app.get("/healthz")
def healthz():
    """Keep-alive / health check for Render. Deliberately does NOT touch the
    database, so the pinger keeps the web service awake while Neon can still
    scale to zero between real visits."""
    return "ok", 200


@app.route("/")
def index():
    counts = one("""
        SELECT (SELECT COUNT(*) FROM app_user) AS users,
               (SELECT COUNT(*) FROM paper) AS papers,
               (SELECT COUNT(*) FROM review) AS reviews,
               (SELECT COUNT(*) FROM conference_session) AS sessions,
               (SELECT COUNT(*) FROM conference) AS conferences,
               (SELECT COUNT(*) FROM track) AS tracks""")
    schedule = rows("""SELECT * FROM accepted_paper_schedule
                       ORDER BY conference_id, session_date, start_time, session_id, paper_id""")
    return render_template("index.html", counts=counts, schedule=schedule,
                           allow_reset=os.environ.get("ALLOW_RESET", "1") == "1")


@app.route("/reference")
def reference():
    confs = rows("""
        SELECT c.*, (SELECT string_agg(host_name, '; ' ORDER BY host_name)
                     FROM conference_host h WHERE h.conference_id = c.conference_id) AS hosts,
               (SELECT string_agg(u.given_name || ' ' || u.surname, ', ' ORDER BY u.user_id)
                FROM conference_reviewer cr JOIN app_user u ON u.user_id = cr.reviewer_id
                WHERE cr.conference_id = c.conference_id) AS pool
        FROM conference c ORDER BY c.conference_id""")
    tracks = rows("""
        SELECT t.*, c.acronym, u.given_name || ' ' || u.surname AS coordinator
        FROM track t JOIN conference c USING (conference_id)
        JOIN app_user u ON u.user_id = t.coordinator_id ORDER BY t.track_id""")
    return render_template("reference.html", confs=confs, tracks=tracks)


@app.post("/admin/reset")
def admin_reset():
    if os.environ.get("ALLOW_RESET", "1") != "1":
        abort(403)
    reset_database(engine)
    flash("Database reset to the original seed data.", "ok")
    return redirect(url_for("index"))


# ==================================================================== users
def conferences():
    return rows("SELECT conference_id, acronym, city FROM conference ORDER BY conference_id")


@app.route("/users")
def users_list():
    users = rows("""
        SELECT u.*, (a.author_id IS NOT NULL) AS is_author, (r.reviewer_id IS NOT NULL) AS is_reviewer
        FROM app_user u
        LEFT JOIN author a ON a.author_id = u.user_id
        LEFT JOIN reviewer r ON r.reviewer_id = u.user_id
        ORDER BY u.user_id""")
    return render_template("users_list.html", users=users)


def user_form_data(uid):
    u = one("SELECT * FROM app_user WHERE user_id = :id", id=uid)
    if not u:
        abort(404)
    d = dict(u)
    a = one("SELECT orcid FROM author WHERE author_id = :id", id=uid)
    r = one("SELECT years_experience FROM reviewer WHERE reviewer_id = :id", id=uid)
    d["is_author"] = "on" if a else ""
    d["orcid"] = (a or {}).get("orcid") or ""
    d["research_areas"] = ", ".join(x["area_label"] for x in rows(
        "SELECT area_label FROM author_research_area WHERE author_id=:id ORDER BY area_label", id=uid))
    d["is_reviewer"] = "on" if r else ""
    d["years_experience"] = r["years_experience"] if r else ""
    d["expertise"] = ", ".join(x["area_label"] for x in rows(
        "SELECT area_label FROM reviewer_expertise WHERE reviewer_id=:id ORDER BY area_label", id=uid))
    d["pools"] = [str(x["conference_id"]) for x in rows(
        "SELECT conference_id FROM conference_reviewer WHERE reviewer_id=:id", id=uid)]
    return d


def save_user(conn, uid, f):
    data = {k: req(f, k, lbl) for k, lbl in [
        ("given_name", "Given name"), ("surname", "Surname"), ("email", "Email"),
        ("affiliation", "Affiliation"), ("country", "Country"), ("phone_number", "Phone number")]}
    is_author, is_reviewer = bool(f.get("is_author")), bool(f.get("is_reviewer"))
    if not (is_author or is_reviewer):
        raise AppError("Every user must be an author, a reviewer, or both.")
    if uid is None:
        uid = conn.execute(text("""
            INSERT INTO app_user (given_name, surname, email, affiliation, country, phone_number)
            VALUES (:given_name, :surname, :email, :affiliation, :country, :phone_number)
            RETURNING user_id"""), data).scalar_one()
    else:
        conn.execute(text("""
            UPDATE app_user SET given_name=:given_name, surname=:surname, email=:email,
                   affiliation=:affiliation, country=:country, phone_number=:phone_number
            WHERE user_id=:uid"""), {**data, "uid": uid})

    # ---- author profile
    if is_author:
        areas = split_labels(f.get("research_areas"))
        if not areas:
            raise AppError("Authors need at least one research area.")
        conn.execute(text("""
            INSERT INTO author (author_id, orcid) VALUES (:id, :orcid)
            ON CONFLICT (author_id) DO UPDATE SET orcid = EXCLUDED.orcid"""),
            {"id": uid, "orcid": (f.get("orcid") or "").strip() or None})
        conn.execute(text("DELETE FROM author_research_area WHERE author_id=:id"), {"id": uid})
        for a in areas:
            conn.execute(text("INSERT INTO author_research_area VALUES (:id, :a)"), {"id": uid, "a": a})
    else:
        conn.execute(text("DELETE FROM author WHERE author_id=:id"), {"id": uid})

    # ---- reviewer profile
    if is_reviewer:
        years = to_int(f.get("years_experience"), "Years of experience")
        exp = split_labels(f.get("expertise"))
        if not exp:
            raise AppError("Reviewers need at least one expertise area.")
        conn.execute(text("""
            INSERT INTO reviewer (reviewer_id, years_experience) VALUES (:id, :y)
            ON CONFLICT (reviewer_id) DO UPDATE SET years_experience = EXCLUDED.years_experience"""),
            {"id": uid, "y": years})
        conn.execute(text("DELETE FROM reviewer_expertise WHERE reviewer_id=:id"), {"id": uid})
        for a in exp:
            conn.execute(text("INSERT INTO reviewer_expertise VALUES (:id, :a)"), {"id": uid, "a": a})
        pools = [int(x) for x in f.getlist("pools")]
        conn.execute(text("""DELETE FROM conference_reviewer
                             WHERE reviewer_id=:id AND NOT (conference_id = ANY(CAST(:p AS integer[])))"""),
                     {"id": uid, "p": pools})
        for c in pools:
            conn.execute(text("""INSERT INTO conference_reviewer VALUES (:c, :id)
                                 ON CONFLICT DO NOTHING"""), {"c": c, "id": uid})
    else:
        conn.execute(text("DELETE FROM reviewer WHERE reviewer_id=:id"), {"id": uid})
    return uid


@app.route("/users/new", methods=["GET", "POST"])
def user_new():
    if request.method == "POST":
        ok, uid = run_tx(lambda c: save_user(c, None, request.form))
        if ok:
            flash(f"User {uid} created.", "ok")
            return redirect(url_for("user_detail", uid=uid))
        form: dict = {**request.form, "pools": request.form.getlist("pools")}
    else:
        form = {"pools": []}
    return render_template("user_form.html", form=form, confs=conferences(), uid=None)


@app.route("/users/<int:uid>/edit", methods=["GET", "POST"])
def user_edit(uid):
    if request.method == "POST":
        ok, _ = run_tx(lambda c: save_user(c, uid, request.form))
        if ok:
            flash("User updated.", "ok")
            return redirect(url_for("user_detail", uid=uid))
        form: dict = {**request.form, "pools": request.form.getlist("pools")}
    else:
        form = user_form_data(uid)
    return render_template("user_form.html", form=form, confs=conferences(), uid=uid)


@app.route("/users/<int:uid>")
def user_detail(uid):
    u = user_form_data(uid)
    papers = rows("""SELECT p.paper_id, p.title, p.status, pa.author_position, pa.is_corresponding
                     FROM paper_author pa JOIN paper p USING (paper_id)
                     WHERE pa.author_id=:id ORDER BY p.paper_id""", id=uid)
    reviews = rows("""SELECT r.review_id, r.paper_id, p.title, r.overall_score, r.recommendation
                      FROM review r JOIN paper p USING (paper_id)
                      WHERE r.reviewer_id=:id ORDER BY r.review_id""", id=uid)
    pools = rows("""SELECT c.acronym FROM conference_reviewer cr JOIN conference c USING (conference_id)
                    WHERE cr.reviewer_id=:id ORDER BY c.conference_id""", id=uid)
    return render_template("user_detail.html", u=u, papers=papers, reviews=reviews, pools=pools)


@app.post("/users/<int:uid>/delete")
def user_delete(uid):
    ok, n = run_tx(lambda c: c.execute(text("DELETE FROM app_user WHERE user_id=:id"), {"id": uid}).rowcount)
    if ok:
        flash(f"User {uid} deleted." if n else "User not found.", "ok")
        return redirect(url_for("users_list"))
    return redirect(url_for("user_detail", uid=uid))


# =================================================================== papers
def paper_choices():
    tracks = rows("""SELECT t.track_id, t.name, c.acronym FROM track t
                     JOIN conference c USING (conference_id) ORDER BY t.track_id""")
    sessions = rows("""SELECT s.session_id, s.title, c.acronym FROM conference_session s
                       JOIN conference c USING (conference_id) ORDER BY s.session_id""")
    authors = rows("""SELECT a.author_id, u.given_name || ' ' || u.surname AS name, u.email
                      FROM author a JOIN app_user u ON u.user_id = a.author_id ORDER BY a.author_id""")
    return dict(tracks=tracks, sessions=sessions, authors=authors, statuses=STATUSES,
                max_authors=MAX_AUTHORS)


@app.route("/papers")
def papers_list():
    papers = rows("""
        SELECT p.paper_id, p.title, p.status, p.session_id, t.name AS track, c.acronym,
               (SELECT string_agg(u.given_name || ' ' || u.surname, ', ' ORDER BY pa.author_position)
                FROM paper_author pa JOIN app_user u ON u.user_id = pa.author_id
                WHERE pa.paper_id = p.paper_id) AS authors,
               (SELECT MAX(version_no) FROM paper_version v WHERE v.paper_id = p.paper_id) AS current_version,
               (SELECT COUNT(*) FROM review r WHERE r.paper_id = p.paper_id) AS reviews
        FROM paper p JOIN track t USING (track_id) JOIN conference c USING (conference_id)
        ORDER BY p.paper_id""")
    return render_template("papers_list.html", papers=papers)


def paper_form_data(pid):
    p = one("SELECT * FROM paper WHERE paper_id=:id", id=pid)
    if not p:
        abort(404)
    d = {k: ("" if v is None else str(v)) for k, v in p.items()}
    d["keywords"] = ", ".join(r["keyword"] for r in rows(
        "SELECT keyword FROM paper_keyword WHERE paper_id=:id ORDER BY keyword", id=pid))
    for i, a in enumerate(rows("""SELECT author_id, is_corresponding FROM paper_author
                                  WHERE paper_id=:id ORDER BY author_position""", id=pid), start=1):
        d[f"author_{i}"] = str(a["author_id"])
        if a["is_corresponding"]:
            d["corresponding"] = str(i)
    return d


def save_paper(conn, pid, f):
    track_id = to_int(f.get("track_id"), "Track")
    title, abstract = req(f, "title", "Title"), req(f, "abstract", "Abstract")
    sub_date = req(f, "submission_date", "Submission date")
    status = f.get("status") or "submitted"
    session_id = to_int(f.get("session_id"), "Session", required=False)
    keywords = split_labels(f.get("keywords"))
    if not keywords:
        raise AppError("A paper needs at least one keyword.")

    # authors in row order -> positions 1..n
    authors, corr_author = [], None
    for i in range(1, MAX_AUTHORS + 1):
        aid = f.get(f"author_{i}")
        if aid:
            aid = int(aid)
            if aid in authors:
                raise AppError("The same author is listed twice.")
            authors.append(aid)
            if f.get("corresponding") == str(i):
                corr_author = aid
    if not authors:
        raise AppError("A paper needs at least one author.")
    if corr_author is None:
        raise AppError("Choose exactly one corresponding author (among the filled author rows).")

    params = dict(track_id=track_id, title=title, abstract=abstract, sub=sub_date,
                  status=status, session_id=session_id)
    if pid is None:
        pid = conn.execute(text("""
            INSERT INTO paper (track_id, title, abstract, submission_date, status, session_id)
            VALUES (:track_id, :title, :abstract, :sub, :status, :session_id)
            RETURNING paper_id"""), params).scalar_one()
        loc = req(f, "file_location", "Initial version file location")
        conn.execute(text("""
            INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
            VALUES (:pid, 1, :loc, COALESCE(CAST(:at AS timestamp), LOCALTIMESTAMP(0)), :note)"""),
            {"pid": pid, "loc": loc, "at": f.get("uploaded_at") or None,
             "note": (f.get("change_note") or "").strip() or None})
    else:
        conn.execute(text("""
            UPDATE paper SET track_id=:track_id, title=:title, abstract=:abstract,
                   submission_date=:sub, status=:status, session_id=:session_id
            WHERE paper_id=:pid"""), {**params, "pid": pid})

    conn.execute(text("DELETE FROM paper_keyword WHERE paper_id=:pid"), {"pid": pid})
    for k in keywords:
        conn.execute(text("INSERT INTO paper_keyword VALUES (:pid, :k)"), {"pid": pid, "k": k})

    conn.execute(text("DELETE FROM paper_author WHERE paper_id=:pid"), {"pid": pid})
    for pos, aid in enumerate(authors, start=1):
        conn.execute(text("""INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding)
                             VALUES (:pid, :aid, :pos, :corr)"""),
                     {"pid": pid, "aid": aid, "pos": pos, "corr": aid == corr_author})

    check_no_self_review(conn, pid)      # required check 1 (author change)
    check_paper_session(conn, pid)       # required check 2 (status / track / session change)
    return pid


@app.route("/papers/new", methods=["GET", "POST"])
def paper_new():
    if request.method == "POST":
        ok, pid = run_tx(lambda c: save_paper(c, None, request.form))
        if ok:
            flash(f"Paper {pid} created.", "ok")
            return redirect(url_for("paper_detail", pid=pid))
        form = request.form
    else:
        form = {"status": "submitted", "submission_date": datetime.now().date().isoformat(),
                "corresponding": "1"}
    return render_template("paper_form.html", form=form, pid=None, **paper_choices())


@app.route("/papers/<int:pid>/edit", methods=["GET", "POST"])
def paper_edit(pid):
    if request.method == "POST":
        ok, _ = run_tx(lambda c: save_paper(c, pid, request.form))
        if ok:
            flash("Paper updated.", "ok")
            return redirect(url_for("paper_detail", pid=pid))
        form = request.form
    else:
        form = paper_form_data(pid)
    return render_template("paper_form.html", form=form, pid=pid, **paper_choices())


@app.route("/papers/<int:pid>")
def paper_detail(pid):
    p = one("""SELECT p.*, t.name AS track, c.acronym, c.conference_id, s.title AS session_title
               FROM paper p JOIN track t USING (track_id) JOIN conference c ON c.conference_id = t.conference_id
               LEFT JOIN conference_session s ON s.session_id = p.session_id
               WHERE p.paper_id=:id""", id=pid)
    if not p:
        abort(404)
    authors = rows("""SELECT pa.*, u.given_name || ' ' || u.surname AS name, u.email
                      FROM paper_author pa JOIN app_user u ON u.user_id = pa.author_id
                      WHERE pa.paper_id=:id ORDER BY pa.author_position""", id=pid)
    keywords = rows("SELECT keyword FROM paper_keyword WHERE paper_id=:id ORDER BY keyword", id=pid)
    versions = rows("SELECT * FROM paper_version WHERE paper_id=:id ORDER BY version_no DESC", id=pid)
    reviews = rows("""SELECT r.*, u.given_name || ' ' || u.surname AS reviewer
                      FROM review r JOIN app_user u ON u.user_id = r.reviewer_id
                      WHERE r.paper_id=:id ORDER BY r.review_id""", id=pid)
    next_v = (versions[0]["version_no"] + 1) if versions else 1
    return render_template("paper_detail.html", p=p, authors=authors, keywords=keywords,
                           versions=versions, reviews=reviews, next_v=next_v,
                           now=datetime.now().strftime("%Y-%m-%dT%H:%M"))


@app.post("/papers/<int:pid>/delete")
def paper_delete(pid):
    ok, _ = run_tx(lambda c: c.execute(text("DELETE FROM paper WHERE paper_id=:id"), {"id": pid}).rowcount)
    if ok:
        flash(f"Paper {pid} and its authorship, keywords, versions and reviews were deleted.", "ok")
        return redirect(url_for("papers_list"))
    return redirect(url_for("paper_detail", pid=pid))


# ---- versions (managed inside the paper workflow)
@app.post("/papers/<int:pid>/versions")
def version_add(pid):
    f = request.form

    def do(conn):
        conn.execute(text("""
            INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
            VALUES (:pid, :v, :loc, COALESCE(CAST(:at AS timestamp), LOCALTIMESTAMP(0)), :note)"""),
            {"pid": pid, "v": to_int(f.get("version_no"), "Version number"),
             "loc": req(f, "file_location", "File location"), "at": f.get("uploaded_at") or None,
             "note": (f.get("change_note") or "").strip() or None})
    if run_tx(do)[0]:
        flash("Version added.", "ok")
    return redirect(url_for("paper_detail", pid=pid))


@app.post("/papers/<int:pid>/versions/<int:v>/edit")
def version_edit(pid, v):
    f = request.form

    def do(conn):
        n = conn.execute(text("""
            UPDATE paper_version SET file_location=:loc, uploaded_at=:at, change_note=:note
            WHERE paper_id=:pid AND version_no=:v"""),
            {"pid": pid, "v": v, "loc": req(f, "file_location", "File location"),
             "at": req(f, "uploaded_at", "Upload time"),
             "note": (f.get("change_note") or "").strip() or None}).rowcount
        if n == 0:
            raise AppError("Version not found.")
    if run_tx(do)[0]:
        flash(f"Version {v} updated.", "ok")
    return redirect(url_for("paper_detail", pid=pid))


@app.post("/papers/<int:pid>/versions/<int:v>/delete")
def version_delete(pid, v):
    def do(conn):
        cnt = conn.execute(text("SELECT COUNT(*) FROM paper_version WHERE paper_id=:pid"),
                           {"pid": pid}).scalar_one()
        if cnt <= 1:
            raise AppError("Every paper must keep at least one version; delete the paper instead.")
        conn.execute(text("DELETE FROM paper_version WHERE paper_id=:pid AND version_no=:v"),
                     {"pid": pid, "v": v})
    if run_tx(do)[0]:
        flash(f"Version {v} deleted.", "ok")
    return redirect(url_for("paper_detail", pid=pid))


# ================================================================== reviews
def review_choices():
    papers = rows("""SELECT p.paper_id, p.title, c.acronym FROM paper p JOIN track t USING (track_id)
                     JOIN conference c USING (conference_id) ORDER BY p.paper_id""")
    reviewers = rows("""SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS name
                        FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id ORDER BY r.reviewer_id""")
    return dict(papers=papers, reviewers=reviewers)


@app.route("/reviews")
def reviews_list():
    reviews = rows("""
        SELECT r.*, p.title, u.given_name || ' ' || u.surname AS reviewer
        FROM review r JOIN paper p USING (paper_id) JOIN app_user u ON u.user_id = r.reviewer_id
        ORDER BY r.review_id""")
    return render_template("reviews_list.html", reviews=reviews)


def save_review(conn, rid, f):
    params = {
        "paper_id": to_int(f.get("paper_id"), "Paper"),
        "reviewer_id": to_int(f.get("reviewer_id"), "Reviewer"),
        "score": to_int(f.get("overall_score"), "Overall score"),
        "rec": req(f, "recommendation", "Recommendation"),
        "comments": req(f, "comments_for_authors", "Comments for authors"),
        "conf": (f.get("confidential_comments") or "").strip() or None,
        "date": req(f, "review_submission_date", "Review submission date"),
    }
    # Required check 1: reviewer must not be an author of the paper
    is_author = conn.execute(text("""SELECT 1 FROM paper_author
                                     WHERE paper_id=:paper_id AND author_id=:reviewer_id"""),
                             params).first()
    if is_author:
        raise AppError("Self-review rejected: the selected reviewer is an author of this paper.")
    if rid is None:
        return conn.execute(text("""
            INSERT INTO review (paper_id, reviewer_id, overall_score, recommendation,
                                comments_for_authors, confidential_comments, review_submission_date)
            VALUES (:paper_id, :reviewer_id, :score, :rec, :comments, :conf, :date)
            RETURNING review_id"""), params).scalar_one()
    conn.execute(text("""
        UPDATE review SET paper_id=:paper_id, reviewer_id=:reviewer_id, overall_score=:score,
               recommendation=:rec, comments_for_authors=:comments,
               confidential_comments=:conf, review_submission_date=:date
        WHERE review_id=:rid"""), {**params, "rid": rid})
    return rid


@app.route("/reviews/new", methods=["GET", "POST"])
def review_new():
    if request.method == "POST":
        ok, rid = run_tx(lambda c: save_review(c, None, request.form))
        if ok:
            flash(f"Review {rid} saved.", "ok")
            return redirect(url_for("review_detail", rid=rid))
        form = request.form
    else:
        form = {"paper_id": request.args.get("paper_id", ""),
                "review_submission_date": datetime.now().date().isoformat()}
    return render_template("review_form.html", form=form, rid=None, **review_choices())


@app.route("/reviews/<int:rid>/edit", methods=["GET", "POST"])
def review_edit(rid):
    if request.method == "POST":
        ok, _ = run_tx(lambda c: save_review(c, rid, request.form))
        if ok:
            flash("Review updated.", "ok")
            return redirect(url_for("review_detail", rid=rid))
        form = request.form
    else:
        r = one("SELECT * FROM review WHERE review_id=:id", id=rid)
        if not r:
            abort(404)
        form = {k: ("" if v is None else str(v)) for k, v in r.items()}
    return render_template("review_form.html", form=form, rid=rid, **review_choices())


@app.route("/reviews/<int:rid>")
def review_detail(rid):
    r = one("""SELECT r.*, p.title, u.given_name || ' ' || u.surname AS reviewer
               FROM review r JOIN paper p USING (paper_id) JOIN app_user u ON u.user_id = r.reviewer_id
               WHERE r.review_id=:id""", id=rid)
    if not r:
        abort(404)
    return render_template("review_detail.html", r=r)


@app.post("/reviews/<int:rid>/delete")
def review_delete(rid):
    if run_tx(lambda c: c.execute(text("DELETE FROM review WHERE review_id=:id"), {"id": rid}))[0]:
        flash(f"Review {rid} deleted.", "ok")
    return redirect(url_for("reviews_list"))


# ================================================================= sessions
def session_choices():
    reviewers = rows("""SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS name,
                               (SELECT string_agg(c.acronym, ', ' ORDER BY c.conference_id)
                                FROM conference_reviewer cr JOIN conference c USING (conference_id)
                                WHERE cr.reviewer_id = r.reviewer_id) AS pools
                        FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id ORDER BY r.reviewer_id""")
    return dict(confs=conferences(), reviewers=reviewers)


@app.route("/sessions")
def sessions_list():
    sessions = rows("""
        SELECT s.*, c.acronym, c.city, u.given_name || ' ' || u.surname AS chair,
               (SELECT COUNT(*) FROM paper p WHERE p.session_id = s.session_id) AS papers
        FROM conference_session s JOIN conference c USING (conference_id)
        JOIN app_user u ON u.user_id = s.chair_id
        ORDER BY s.conference_id, s.session_date, s.start_time""")
    return render_template("sessions_list.html", sessions=sessions)


def save_session(conn, sid, f):
    params = {
        "conf": to_int(f.get("conference_id"), "Conference"),
        "title": req(f, "title", "Title"),
        "date": req(f, "session_date", "Date"),
        "start": req(f, "start_time", "Start time"),
        "end": req(f, "end_time", "End time"),
        "room": req(f, "room_label", "Room"),
        "chair": to_int(f.get("chair_id"), "Chair"),
    }
    if sid is None:
        return conn.execute(text("""
            INSERT INTO conference_session (conference_id, title, session_date, start_time,
                                            end_time, room_label, chair_id)
            VALUES (:conf, :title, :date, :start, :end, :room, :chair) RETURNING session_id"""),
            params).scalar_one()
    conn.execute(text("""
        UPDATE conference_session SET conference_id=:conf, title=:title, session_date=:date,
               start_time=:start, end_time=:end, room_label=:room, chair_id=:chair
        WHERE session_id=:sid"""), {**params, "sid": sid})
    # Required check 2: changing the session's conference must not invalidate assignments
    for pid in conn.execute(text("SELECT paper_id FROM paper WHERE session_id=:sid"),
                            {"sid": sid}).scalars():
        check_paper_session(conn, pid)
    return sid


@app.route("/sessions/new", methods=["GET", "POST"])
def session_new():
    if request.method == "POST":
        ok, sid = run_tx(lambda c: save_session(c, None, request.form))
        if ok:
            flash(f"Session {sid} created.", "ok")
            return redirect(url_for("session_detail", sid=sid))
        form = request.form
    else:
        form = {}
    return render_template("session_form.html", form=form, sid=None, **session_choices())


@app.route("/sessions/<int:sid>/edit", methods=["GET", "POST"])
def session_edit(sid):
    if request.method == "POST":
        ok, _ = run_tx(lambda c: save_session(c, sid, request.form))
        if ok:
            flash("Session updated.", "ok")
            return redirect(url_for("session_detail", sid=sid))
        form = request.form
    else:
        s = one("SELECT * FROM conference_session WHERE session_id=:id", id=sid)
        if not s:
            abort(404)
        form = {k: ("" if v is None else str(v)[:5] if k.endswith("_time") else str(v))
                for k, v in s.items()}
    return render_template("session_form.html", form=form, sid=sid, **session_choices())


@app.route("/sessions/<int:sid>")
def session_detail(sid):
    s = one("""SELECT s.*, c.acronym, u.given_name || ' ' || u.surname AS chair
               FROM conference_session s JOIN conference c USING (conference_id)
               JOIN app_user u ON u.user_id = s.chair_id WHERE s.session_id=:id""", id=sid)
    if not s:
        abort(404)
    papers = rows("""SELECT p.paper_id, p.title, p.status, t.name AS track
                     FROM paper p JOIN track t USING (track_id)
                     WHERE p.session_id=:id ORDER BY p.paper_id""", id=sid)
    # all papers are offered so that invalid assignments can be demonstrated (and rejected)
    candidates = rows("""SELECT p.paper_id, p.title, p.status, c.acronym, p.session_id
                         FROM paper p JOIN track t USING (track_id) JOIN conference c USING (conference_id)
                         WHERE p.session_id IS DISTINCT FROM :id ORDER BY p.paper_id""", id=sid)
    return render_template("session_detail.html", s=s, papers=papers, candidates=candidates)


@app.post("/sessions/<int:sid>/assign")
def session_assign(sid):
    def do(conn):
        pid = to_int(request.form.get("paper_id"), "Paper")
        conn.execute(text("UPDATE paper SET session_id=:sid WHERE paper_id=:pid"), {"sid": sid, "pid": pid})
        check_paper_session(conn, pid)
        return pid
    ok, pid = run_tx(do)
    if ok:
        flash(f"Paper {pid} assigned to session {sid}.", "ok")
    return redirect(url_for("session_detail", sid=sid))


@app.post("/sessions/<int:sid>/unassign/<int:pid>")
def session_unassign(sid, pid):
    if run_tx(lambda c: c.execute(text("""UPDATE paper SET session_id=NULL
                                          WHERE paper_id=:pid AND session_id=:sid"""),
                                  {"pid": pid, "sid": sid}))[0]:
        flash(f"Paper {pid} removed from session {sid}.", "ok")
    return redirect(url_for("session_detail", sid=sid))


@app.post("/sessions/<int:sid>/delete")
def session_delete(sid):
    if run_tx(lambda c: c.execute(text("DELETE FROM conference_session WHERE session_id=:id"), {"id": sid}))[0]:
        flash(f"Session {sid} deleted (its papers are now unscheduled).", "ok")
        return redirect(url_for("sessions_list"))
    return redirect(url_for("session_detail", sid=sid))


# ------------------------------------------------- first start on a fresh DB
if os.environ.get("AUTO_INIT_DB", "1") == "1":
    try:
        if not schema_exists(engine):
            reset_database(engine)
            print("Empty database detected: schema and seed data created.")
    except Exception as exc:  # do not crash the import if the DB is briefly unavailable
        print(f"Auto-init skipped: {exc}")


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
