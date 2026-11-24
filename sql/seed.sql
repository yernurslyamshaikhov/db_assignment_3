-- =====================================================================
-- CSCI 341 Assignment 3 - Seed data (all people and organisations fictional)
-- Run after schema.sql. Explicit IDs are used so query parameters are stable;
-- identity sequences are advanced at the end.
-- =====================================================================

-- ---------------------------------------------------------------- users (12)
INSERT INTO app_user (user_id, given_name, surname, email, affiliation, country, phone_number) VALUES
 (1,  'Arman',   'Armanov',   'arman.armanov@example.com',   'Nazarbayev University',             'Kazakhstan', '+77011112233'),
 (2,  'Amina',   'Aminova',   'amina.aminova@example.com',   'Astana IT University',              'Kazakhstan', '+77022223344'),
 (3,  'Dana',    'Sultanova', 'dana.sultanova@example.com',  'Al-Farabi Kazakh National University','Kazakhstan', '+77033334455'),
 (4,  'Timur',   'Bekov',     'timur.bekov@example.com',     'Kazakh-British Technical University','Kazakhstan', '+77044445566'),
 (5,  'Aigerim', 'Nurlanova', 'aigerim.nurlanova@example.com','Nazarbayev University',            'Kazakhstan', '+77055556677'),
 (6,  'Yerlan',  'Kassymov',  'yerlan.kassymov@example.com', 'Satbayev University',               'Kazakhstan', '+77066667788'),
 (7,  'Madina',  'Ospanova',  'madina.ospanova@example.com', 'Eurasian National University',      'Kazakhstan', '+77077778899'),
 (8,  'Nurlan',  'Zhakupov',  'nurlan.zhakupov@example.com', 'Karaganda Technical University',    'Kazakhstan', '+77088889900'),
 (9,  'Saule',   'Akhmetova', 'saule.akhmetova@example.com', 'Suleyman Demirel University',       'Kazakhstan', '+77099990011'),
 (10, 'Ruslan',  'Ibraev',    'ruslan.ibraev@example.com',   'Tashkent University of IT',         'Uzbekistan', '+998901234567'),
 (11, 'Elena',   'Petrova',   'elena.petrova@example.com',   'Novosibirsk State University',      'Russia',     '+79131234567'),
 (12, 'Daniyar', 'Serikov',   'daniyar.serikov@example.com', 'Astana IT University',              'Kazakhstan', '+77012345678');

-- Authors: 1,2,4,5,7,9,11,12   (author-only: 2,5,9,12)
INSERT INTO author (author_id, orcid) VALUES
 (1,  '0000-0001-1111-0001'),
 (2,  '0000-0001-1111-0002'),
 (4,  NULL),
 (5,  '0000-0001-1111-0005'),
 (7,  '0000-0001-1111-0007'),
 (9,  NULL),
 (11, '0000-0001-1111-0011'),
 (12, NULL);

INSERT INTO author_research_area (author_id, area_label) VALUES
 (1, 'Databases'), (1, 'Distributed Systems'),
 (2, 'Machine Learning'), (2, 'Natural Language Processing'),
 (4, 'Databases'),
 (5, 'Databases'), (5, 'Stream Processing'),
 (7, 'Natural Language Processing'), (7, 'Query Optimization'),
 (9, 'Data Mining'), (9, 'Machine Learning'),
 (11, 'Machine Learning'), (11, 'Data Management'),
 (12, 'Graph Databases'), (12, 'Machine Learning');

-- Reviewers: 1,3,4,6,7,8,10,11  (reviewer-only: 3,6,8,10; both roles: 1,4,7,11)
INSERT INTO reviewer (reviewer_id, years_experience) VALUES
 (1, 5), (3, 8), (4, 2), (6, 6), (7, 4), (8, 3), (10, 7), (11, 10);

INSERT INTO reviewer_expertise (reviewer_id, area_label) VALUES
 (1, 'Databases'), (1, 'Distributed Systems'),
 (3, 'Databases'), (3, 'Query Optimization'),
 (4, 'Databases'),
 (6, 'Machine Learning'), (6, 'Data Mining'),
 (7, 'Natural Language Processing'),
 (8, 'Databases'), (8, 'Software Testing'),
 (10, 'Machine Learning'), (10, 'Software Testing'),
 (11, 'Databases'), (11, 'Machine Learning');

-- ---------------------------------------------------------- conferences (3)
INSERT INTO conference (conference_id, name, acronym, description, city, country,
                        start_date, end_date, submission_deadline, review_deadline) VALUES
 (1, 'Astana International Conference on Data Systems', 'AICDS 2026',
     'Annual conference on database systems, data management and analytics.',
     'Astana', 'Kazakhstan', '2026-06-15', '2026-06-17', '2026-03-01', '2026-04-15'),
 (2, 'Central Asian Symposium on Artificial Intelligence', 'CASAI 2027',
     'Symposium on machine learning and language technologies for the region.',
     'Almaty', 'Kazakhstan', '2027-02-10', '2027-02-12', '2026-10-15', '2026-12-01'),
 (3, 'Silk Road Workshop on Software Engineering', 'SRWSE 2027',
     'Workshop on software testing and engineering practice. Call for papers open.',
     'Tashkent', 'Uzbekistan', '2027-04-20', '2027-04-21', '2027-01-15', '2027-03-01');

INSERT INTO conference_host (conference_id, host_name) VALUES
 (1, 'Nazarbayev University'), (1, 'L.N. Gumilyov Eurasian National University'),
 (2, 'Al-Farabi Kazakh National University'), (2, 'Kazakh-British Technical University'),
 (3, 'Tashkent University of Information Technologies');

INSERT INTO conference_reviewer (conference_id, reviewer_id) VALUES
 (1, 1), (1, 3), (1, 4), (1, 6), (1, 8),
 (2, 3), (2, 6), (2, 7), (2, 10), (2, 11),
 (3, 8), (3, 10);

-- --------------------------------------------------------------- tracks (6)
INSERT INTO track (track_id, conference_id, name, description, research_area, coordinator_id) VALUES
 (1, 1, 'Database Systems',          'Storage, indexing, transactions and query processing.', 'Databases',        3),
 (2, 1, 'Data Mining and Analytics', 'Mining, analytics and ML over data.',                   'Data Mining',      1),
 (3, 1, 'Industry Track',            'Industrial experience reports (no submissions yet).',   'Databases',        4),
 (4, 2, 'Machine Learning',          'Learning algorithms and applications.',                 'Machine Learning', 6),
 (5, 2, 'Natural Language Processing','Language technologies, especially Turkic languages.',  'Natural Language Processing', 7),
 (6, 3, 'Software Testing',          'Testing, verification and quality assurance.',          'Software Testing', 8);

-- ------------------------------------------------------------- sessions (5)
INSERT INTO conference_session (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
 (1, 1, 'Database Systems I',      '2026-06-15', '09:00', '10:30', 'Hall A',   3),
 (2, 1, 'Analytics and ML on Data','2026-06-16', '11:00', '12:30', 'Room 204', 1),
 (3, 1, 'Late-Breaking Results',   '2026-06-17', '14:00', '15:00', 'Room 105', 4),   -- empty, Astana
 (4, 2, 'Machine Learning Applications', '2027-02-11', '10:00', '11:30', 'Auditorium 1', 6),
 (5, 2, 'NLP and Speech',          '2027-02-12', '09:30', '11:00', 'Auditorium 2', 7); -- empty, Almaty

-- --------------------------------------------------------------- papers (12)
INSERT INTO paper (paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
 (1, 1, 'Adaptive Indexing for Hybrid Transactional Workloads',
     'We present an adaptive indexing technique that reorganises indexes incrementally under mixed OLTP and OLAP workloads.',
     '2026-02-10', 'accepted', 1),
 (2, 1, 'Cost-Based Optimization of Recursive SQL Queries',
     'This paper extends a cost-based optimizer with cardinality estimates for recursive common table expressions.',
     '2026-02-20', 'accepted', 1),
 (3, 2, 'Scalable Machine Learning Pipelines over Relational Data',
     'We show how Machine Learning pipelines can be pushed into the DBMS to avoid costly data export.',
     '2026-02-25', 'accepted', 2),
 (4, 2, 'Clustering Retail Transactions in Kazakhstan',
     'A study of clustering algorithms applied to anonymised retail transaction data from three cities.',
     '2026-02-27', 'accepted', NULL),
 (5, 1, 'A Survey of Graph Database Benchmarks',
     'We survey existing graph database benchmarks and categorise them by workload type.',
     '2026-02-28', 'rejected', NULL),
 (6, 2, 'Detecting Anomalies in Industrial Sensor Streams',
     'We compare statistical and machine learning detectors for anomalies in high-rate sensor streams.',
     '2026-02-15', 'rejected', NULL),
 (7, 4, 'Federated Learning for Medical Imaging in Central Asia',
     'A federated learning framework that lets regional hospitals train shared models without sharing images.',
     '2026-10-01', 'accepted', 4),
 (8, 4, 'Explainable Deep Models for Credit Scoring',
     'We evaluate post-hoc explanation methods for deep credit scoring models used by local banks.',
     '2026-10-05', 'under review', NULL),
 (9, 5, 'Low-Resource Machine Translation for Kazakh',
     'Back-translation and transfer learning for Kazakh-English translation with limited parallel data.',
     '2026-10-12', 'submitted', NULL),
 (10, 4, 'Benchmarking Gradient Boosting Libraries',
     'An empirical comparison of gradient boosting libraries on tabular machine learning tasks.',
     '2026-09-20', 'withdrawn', NULL),
 (11, 5, 'Sentiment Analysis of Kazakh Social Media',
     'A labelled corpus and baseline models for sentiment analysis of Kazakh-language posts.',
     '2026-09-25', 'withdrawn', NULL),
 (12, 5, 'Named Entity Recognition for Kazakh News',
     'We build a named entity recognition dataset from Kazakh news articles.',
     '2026-10-02', 'withdrawn', NULL);

INSERT INTO paper_keyword (paper_id, keyword) VALUES
 (1, 'indexing'), (1, 'HTAP'),
 (2, 'query optimization'), (2, 'recursive SQL'),
 (3, 'machine learning'), (3, 'in-database analytics'),
 (4, 'clustering'), (4, 'retail'),
 (5, 'graph databases'), (5, 'benchmarks'),
 (6, 'anomaly detection'), (6, 'streams'),
 (7, 'federated learning'), (7, 'medical imaging'),
 (8, 'explainability'), (8, 'credit scoring'),
 (9, 'machine translation'), (9, 'Kazakh'),
 (10, 'gradient boosting'), (10, 'benchmarks'),
 (11, 'sentiment analysis'), (11, 'Kazakh'),
 (12, 'named entity recognition'), (12, 'Kazakh');

-- Exactly one corresponding author per paper; positions 1..n
INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding) VALUES
 (1, 4, 1, TRUE),  (1, 5, 2, FALSE),
 (2, 7, 1, TRUE),  (2, 1, 2, FALSE), (2, 12, 3, FALSE),
 (3, 11, 1, TRUE), (3, 9, 2, FALSE),
 (4, 9, 1, TRUE),
 (5, 12, 1, TRUE), (5, 4, 2, FALSE),
 (6, 5, 1, TRUE),
 (7, 1, 1, TRUE),  (7, 7, 2, FALSE),
 (8, 4, 1, TRUE),  (8, 11, 2, FALSE),
 (9, 7, 1, TRUE),  (9, 5, 2, FALSE),
 (10, 2, 1, TRUE), (10, 12, 2, FALSE),     -- Amina corresponding, withdrawn
 (11, 2, 1, TRUE),                         -- Amina corresponding, withdrawn
 (12, 9, 1, TRUE), (12, 2, 2, FALSE);      -- withdrawn, Amina NOT corresponding (must survive 4.1)

-- Versions (gaps allowed: paper 2 has versions 1 and 3)
INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note) VALUES
 (1, 1, '/files/papers/1/v1.pdf', '2026-02-10 10:15:00', NULL),
 (1, 2, '/files/papers/1/v2.pdf', '2026-05-01 18:40:00', 'Camera-ready version'),
 (2, 1, '/files/papers/2/v1.pdf', '2026-02-20 09:00:00', NULL),
 (2, 3, '/files/papers/2/v3.pdf', '2026-05-03 21:05:00', 'Addressed reviewer comments; new experiments'),
 (3, 1, '/files/papers/3/v1.pdf', '2026-02-25 14:30:00', NULL),
 (4, 1, '/files/papers/4/v1.pdf', '2026-02-27 11:00:00', NULL),
 (5, 1, '/files/papers/5/v1.pdf', '2026-02-28 23:50:00', NULL),
 (6, 1, '/files/papers/6/v1.pdf', '2026-02-15 08:20:00', NULL),
 (7, 1, '/files/papers/7/v1.pdf', '2026-10-01 12:00:00', NULL),
 (7, 2, '/files/papers/7/v2.pdf', '2026-11-10 16:45:00', 'Fixed typos in Section 4'),
 (8, 1, '/files/papers/8/v1.pdf', '2026-10-05 13:10:00', NULL),
 (9, 1, '/files/papers/9/v1.pdf', '2026-10-12 17:25:00', NULL),
 (10, 1, '/files/papers/10/v1.pdf', '2026-09-20 10:00:00', NULL),
 (11, 1, '/files/papers/11/v1.pdf', '2026-09-25 10:30:00', NULL),
 (12, 1, '/files/papers/12/v1.pdf', '2026-10-02 15:00:00', NULL);

-- Completed reviews (16). Counts: Arman 3, Dana 4, Timur 1, Yerlan 3, Madina 1,
-- Nurlan 0, Ruslan 2, Elena 2  -> average 2.0 per reviewer. No reviewer reviews own paper.
INSERT INTO review (review_id, paper_id, reviewer_id, overall_score, recommendation,
                    comments_for_authors, confidential_comments, review_submission_date) VALUES
 (1,  1, 3, 5, 'accept', 'Clear contribution and strong experiments.', NULL, '2026-04-01'),
 (2,  1, 1, 4, 'accept', 'Good paper; please discuss related adaptive indexing work.', NULL, '2026-04-03'),
 (3,  2, 3, 4, 'accept', 'Solid optimizer extension.', 'Borderline novelty, but useful.', '2026-04-05'),
 (4,  2, 6, 5, 'accept', 'Excellent evaluation on real workloads.', NULL, '2026-04-06'),
 (5,  3, 1, 4, 'accept', 'Interesting system design.', NULL, '2026-04-02'),
 (6,  3, 3, 5, 'accept', 'Very relevant to the community.', NULL, '2026-04-08'),
 (7,  4, 6, 4, 'accept', 'Well-executed empirical study.', NULL, '2026-04-09'),
 (8,  5, 3, 2, 'reject', 'Survey lacks a clear taxonomy.', NULL, '2026-04-10'),
 (9,  5, 1, 1, 'reject', 'Coverage of benchmarks is incomplete.', 'Possible overlap with a prior survey.', '2026-04-11'),
 (10, 6, 6, 2, 'reject', 'Baselines are too weak.', NULL, '2026-04-12'),
 (11, 6, 4, 3, 'reject', 'Promising, but evaluation is limited to one dataset.', NULL, '2026-04-12'),
 (12, 7, 10, 5, 'accept', 'Important application with careful privacy analysis.', NULL, '2026-11-05'),
 (13, 7, 11, 4, 'accept', 'Good work; add communication cost analysis.', NULL, '2026-11-07'),
 (14, 8, 7, 3, 'accept', 'Reasonable study, needs more datasets.', NULL, '2026-11-15'),
 (15, 10, 10, 2, 'reject', 'Comparison misses recent libraries.', NULL, '2026-10-20'),
 (16, 11, 11, 3, 'reject', 'Corpus is too small for strong conclusions.', NULL, '2026-10-22');

-- Advance identity sequences past the explicit IDs
SELECT setval(pg_get_serial_sequence('app_user', 'user_id'),             (SELECT MAX(user_id) FROM app_user));
SELECT setval(pg_get_serial_sequence('conference', 'conference_id'),     (SELECT MAX(conference_id) FROM conference));
SELECT setval(pg_get_serial_sequence('track', 'track_id'),               (SELECT MAX(track_id) FROM track));
SELECT setval(pg_get_serial_sequence('conference_session', 'session_id'),(SELECT MAX(session_id) FROM conference_session));
SELECT setval(pg_get_serial_sequence('paper', 'paper_id'),               (SELECT MAX(paper_id) FROM paper));
SELECT setval(pg_get_serial_sequence('review', 'review_id'),             (SELECT MAX(review_id) FROM review));
