# Executive Summary — CSCI 341 Assignment 3

**Project:** Research Conference and Paper Review Management System

| Member               | Student ID | Contributions                                                        |
| -------------------- | ---------- | -------------------------------------------------------------------- |
| Yernur Slyamshaikhov | 202278977  | <e.g. schema, seed data, Part 2 queries, web app, deployment, video> |
| Yernur Kaltayev      | 202232849  | <e.g. schema, seed data, Part 2 queries, web app, deployment, video> |
| Olzhas Nurseit       | 202270951  | <e.g. schema, seed data, Part 2 queries, web app, deployment, video> |

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
