-- Bengal Assembly Elections 2021 vs 2026 - schema
-- Built by src/load_db.py from data/clean/. Drop and rebuild; never append.

DROP VIEW  IF EXISTS v_winners;
DROP VIEW  IF EXISTS v_results;
DROP TABLE IF EXISTS name_flags;
DROP TABLE IF EXISTS seat_status;
DROP TABLE IF EXISTS electorate;
DROP TABLE IF EXISTS nota;
DROP TABLE IF EXISTS winners;
DROP TABLE IF EXISTS results;
DROP TABLE IF EXISTS constituencies;

-- One row per constituency. ac_no is the ONLY safe key: constituency names
-- do not join across years, and "Bishnupur" is two different seats.
CREATE TABLE constituencies (
    ac_no        INTEGER PRIMARY KEY,
    ac_name      TEXT NOT NULL,
    reservation  TEXT NOT NULL,          -- GEN | SC | ST
    is_reserved  INTEGER NOT NULL,
    ac_name_2021 TEXT,
    ac_name_2026 TEXT,
    district     TEXT NOT NULL,
    region       TEXT NOT NULL
);

-- One row per candidate per election. NOTA is NOT here - see the nota table.
CREATE TABLE results (
    year          INTEGER NOT NULL,
    ac_no         INTEGER NOT NULL REFERENCES constituencies(ac_no),
    candidate     TEXT    NOT NULL,
    gender        TEXT,
    age           REAL,
    category      TEXT,
    party         TEXT    NOT NULL,
    general_votes INTEGER NOT NULL,
    postal_votes  INTEGER NOT NULL,
    total_votes   INTEGER NOT NULL,
    vote_pct      REAL,
    position      INTEGER NOT NULL       -- 1 = winner, 2 = runner-up, ...
);

-- One row per seat per election, winner and runner-up side by side.
-- Two margin definitions are carried deliberately; name the one you use.
CREATE TABLE winners (
    year                INTEGER NOT NULL,
    ac_no               INTEGER NOT NULL REFERENCES constituencies(ac_no),
    winner              TEXT    NOT NULL,
    winner_party        TEXT    NOT NULL,
    gender              TEXT,
    age                 REAL,
    category            TEXT,
    winner_votes        INTEGER NOT NULL,
    runner_up           TEXT,
    runner_up_party     TEXT,
    runner_up_votes     INTEGER,
    win_margin          INTEGER,
    margin_pct_polled   REAL,            -- margin as % of votes polled  <- use this
    margin_pct_electors REAL,            -- margin as % of registered electors
    votes_polled        INTEGER,
    total_electors      INTEGER,
    turnout_pct         REAL
);

CREATE TABLE nota (
    year       INTEGER NOT NULL,
    ac_no      INTEGER NOT NULL REFERENCES constituencies(ac_no),
    nota_votes INTEGER NOT NULL,
    nota_pct   REAL
);

-- turnout_pct = (valid + NOTA) / electors. Runs ~0.13pp under the ECI's
-- published poll %, which also counts 89,773 rejected votes statewide.
CREATE TABLE electorate (
    year           INTEGER NOT NULL,
    ac_no          INTEGER NOT NULL REFERENCES constituencies(ac_no),
    total_electors INTEGER NOT NULL,
    votes_polled   INTEGER NOT NULL,
    turnout_pct    REAL
);

-- Falta (ac_no 144) held no poll in 2026. Join this table and filter
-- result_status = 'polled' rather than letting the seat vanish silently.
CREATE TABLE seat_status (
    year          INTEGER NOT NULL,
    ac_no         INTEGER NOT NULL REFERENCES constituencies(ac_no),
    result_status TEXT    NOT NULL       -- polled | no_poll
);

-- Winners sharing a name. Same age + party = one person who won two seats;
-- different ages = different people. Seat counts and people counts differ.
CREATE TABLE name_flags (
    year  INTEGER NOT NULL,
    ac_no INTEGER NOT NULL,
    name  TEXT    NOT NULL,
    age   REAL,
    party TEXT,
    flag  TEXT    NOT NULL
);

CREATE INDEX idx_results_year_ac ON results (year, ac_no);
CREATE INDEX idx_results_party   ON results (party);
CREATE INDEX idx_winners_year_ac ON winners (year, ac_no);
CREATE INDEX idx_winners_party   ON winners (winner_party);
CREATE INDEX idx_elec_year_ac    ON electorate (year, ac_no);

-- Convenience views: geography pre-joined, no-poll seats already excluded.
CREATE VIEW v_results AS
SELECT r.*, c.ac_name, c.district, c.region, c.reservation, c.is_reserved
FROM results r
JOIN constituencies c ON c.ac_no = r.ac_no;

CREATE VIEW v_winners AS
SELECT w.*, c.ac_name, c.district, c.region, c.reservation, c.is_reserved
FROM winners w
JOIN constituencies c ON c.ac_no = w.ac_no;
