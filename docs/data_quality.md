# Data quality

Every defect below was found by profiling the raw ECI workbooks and the
intermediate CSVs, and every one is corrected in `src/clean.py`. The two marked
**critical** produce wrong answers rather than errors, which is what makes them
dangerous.

Source: Election Commission of India statistical reports, downloaded 2026-05-07.
West Bengal Legislative Assembly, 2021 and 2026.

---

## Critical

### 1. Two labels for one party

In 2021 the party column carries both `CPI(M)` (139 rows) and `CPIM` (3 rows).
These are the same party. Left uncorrected, any `GROUP BY party` splits CPI(M)
into two buckets and understates it — silently, with no error raised.

Corrected by `data/lookups/party_canonical.csv`. The same lookup maps the ECI's
`AITC` code to `TMC`.

**Still unverified:** `AJSUP`/`AJUP`, `AIMF`/`AISF` and `UTSAP`/`SAP` are
fuzzy-similar label pairs across the two years. `RSSCMJP` polled 1.36% in 2021
and disappears; `AISF` polled 1.54% in 2026 and appears from nowhere. These may
be renames or may be different parties. Verify against report 3 (*List of
Political Parties Participated*) before claiming a party emerged or vanished.

### 2. Turnout is anomalously high and the electorate shrank

Turnout in 2026 is 93.6% against 82.2% in 2021, while the electorate fell from
roughly 73.2M to 68.1M — about 6%. Electorates do not shrink naturally over five
years.

This is **not** a pipeline artefact: the ECI's own Highlight report states a
state polling percentage of 93.71%. A smaller denominator raises the percentage
without a single extra vote being cast, so a roll revision is the obvious
candidate explanation.

**Status: unresolved.** Do not publish a turnout chart without establishing
whether a Special Intensive Revision of electoral rolls preceded the poll.

---

## Moderate

### 3. Constituency names do not join across years

2021 names are mixed case (`Mekliganj`); 2026 names are upper case and carry a
reservation tag (`MEKLIGANJ (SC)`). Exact match rate across the two years:
**0 of 294**.

Corrected by parsing the tag into `reservation` / `is_reserved`, normalising the
name, and using `ac_no` as the only join key.

### 4. Constituency name is not unique even within one year

`Bishnupur` is two different constituencies — `ac_no` 146 (South 24 Parganas)
and 255 (Bankura). `ac_name` is not a key. Join on `ac_no`.

### 5. Candidate name is not a person

| Year | Name | Ages | Verdict |
|---|---|---|---|
| 2021 | HUMAYUN KABIR | 61, 59 | two different people |
| 2026 | Arup Kumar Das | 52, 68 | two different people |
| 2026 | Adhikari Suvendu | 57, 57 | one person, two seats |
| 2026 | Humayun Kabir | 63, 63 | one person, two seats |

Winning two seats is legal in India; the winner vacates one within 14 days. So
293 seats in 2026 have only **290 distinct winners**. Seat counts and people
counts are different numbers.

Recorded in `data/clean/name_flags.csv`. Cross-year candidate tracking is *not*
attempted: even after normalising case and token order, only about 543 of 2,079
names match between the two years, which is too unreliable to build an
incumbency figure on.

### 6. One constituency held no poll

Falta (`ac_no` 144) has no 2026 result — only a zero-vote NOTA row. The ECI
Highlight report independently counts 293 constituencies, confirming this is a
genuine countermanded poll rather than a scrape failure.

Recorded in `data/clean/seat_status.csv` as `result_status = 'no_poll'` so it is
excluded deliberately rather than vanishing from aggregates unnoticed.

### 7. Margin percentage was defined against the wrong denominator

The original pipeline computed `win_margin_pct` as a share of *registered
electors*. Published psephology expresses margin as a share of *votes polled*,
which is a materially larger number.

Both are now carried and named explicitly: `margin_pct_polled` (use this) and
`margin_pct_electors`.

---

## Minor

### 8. Embedded commas and serial prefixes in candidate names

Candidate names arrive as `1 Dadhiram Ray` — a ballot serial prefix. One 2021
name contains a comma: `Arup Roy, S/o Late Prabhat Roy`.

That comma matters. Under naive CSV splitting it shifts every subsequent column
right, which moved his party from `TMC` into the category column — and made TMC's
2021 seat count read as **214 instead of the correct 215**. A single
unescaped character changed a headline number.

### 9. NOTA sat inside the candidate table

294 NOTA rows per year carried null gender, age and category — the entirety of
the dataset's apparent "missing data". Moved to `data/clean/nota.csv`.

---

## Two reconciliation notes

Both surfaced when the pipeline's assertions were first run against the ECI
Highlight report, and both are properties of the source, not bugs.

**Electors.** The ECI's published total of 68,125,496 covers only the 293
constituencies that polled. Summing all 294 gives 68,362,033 — the difference is
exactly Falta's 236,537 electors.

**Votes polled.** The ECI reports 63,842,843 votes polled, but the Detailed
Results workbook contains 63,753,070. The gap of 89,773 is *rejected* votes,
which that workbook does not itemise. Valid votes (63,258,138) and NOTA
(494,932) each match the published figure exactly.

Consequently `turnout_pct` in this dataset runs about 0.13 points below the
ECI's published poll percentage. It is computed as
`(valid + NOTA) / electors`.

---

## Vote share convention

Party vote share is expressed as a percentage of **valid votes**, excluding
NOTA. NOTA is reported separately as a share of votes polled. The ECI's own
`% VOTES POLLED` column uses valid votes + NOTA as its denominator, so figures
here run marginally above it. State which convention you are using whenever you
quote a number.

---

## Provenance warning: the district mapping

`data/lookups/constituencies.csv` maps all 294 constituencies to 23 districts
and 8 regions. **No ECI workbook in this repository contains district
information** — the mapping is derived from the fact that West Bengal numbers
its constituencies contiguously by district, and was checked against
constituency names.

It reconciles correctly: 23 districts totalling 294 seats, matching West
Bengal's actual district count. But it has not been verified row by row against
an official source. Spot-check it against the ECI constituency list before
publishing any district-level claim. Region-level findings are robust to a
one-seat boundary error; district-level findings are not.
