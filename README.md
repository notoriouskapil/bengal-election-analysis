# West Bengal Assembly Elections: 2021 vs 2026

Comparing two West Bengal state elections using the Election Commission's
published statistical reports. 294 constituencies, 5,052 candidates.

Python (pandas) · SQLite · Power BI

## What I found

**A 15-point vote swing produced a 135-seat reversal.** TMC's vote share went
from 48.6% to 41.1%, BJP's from 38.4% to 46.2%. Seats went from TMC 215 / BJP 77
to BJP 207 / TMC 80. Under first-past-the-post a swing concentrated near the
margin flips a lot of seats at once — BJP took 46% of the vote and 71% of
the seats.

**Not one seat flipped against the tide.** 129 seats went TMC to BJP. Zero went
BJP to TMC.

**Most of the turnout "rise" is arithmetic.** Turnout reads 93.6% against 82.2%
in 2021, but the electoral roll shrank about 6% — 241 of 293 seats lost voters
from the register. The regions where the roll shrank most are the regions where
turnout rose most: Kolkata & Howrah lost 16.7% of its electorate and gained 19.5
points of turnout, while Jangalmahal lost 0.7% and gained 7.6. A smaller
denominator raises the percentage without anyone extra voting.

| Party | 2021 vote | 2026 vote | 2021 seats | 2026 seats |
|---|---|---|---|---|
| TMC | 48.55% | 41.12% | 215 | 80 |
| BJP | 38.39% | 46.20% | 77 | 207 |
| CPI(M) | 4.78% | 4.49% | 0 | 1 |
| INC | 3.06% | 2.99% | 0 | 2 |
| NOTA | 1.10% | 0.78% | — | — |

Vote share is a percentage of valid votes, NOTA excluded.

## Running it

```bash
pip install -r requirements.txt
python src/clean.py     # raw workbooks -> data/clean/
python src/load_db.py   # data/clean/  -> bengal_elections.db
```

`clean.py` checks its own output against the totals the ECI publishes and exits
non-zero if they don't match:

```
ok   electors, 293 polled seats           68,125,496
ok   valid votes                          63,258,138
ok   NOTA votes                              494,932
ok   contestants                               2,920
```

## Layout

```
data/raw/        the 15 ECI workbooks as downloaded
data/clean/      generated tables
data/lookups/    party name mapping, constituency -> district -> region
src/             clean.py, load_db.py
sql/             schema plus the six analysis queries
docs/            data quality notes
```

Tables: `constituencies` (294), `results` (5,052 candidates, NOTA excluded),
`winners` (587, runner-up alongside), `nota`, `electorate`, `seat_status`,
`name_flags`. The views `v_results` and `v_winners` have district and region
joined in already.

## Before you query

Join on `ac_no`, never on name — constituency names match 0 of 294 across the
two years, and Bishnupur is two different seats.

Filter `seat_status`. Falta held no poll in 2026, so it's 293 seats that year,
not 294.

Use `margin_pct_polled` rather than `margin_pct_electors`. Both are there; the
first is the convention published figures use.

## Data quality

Nine problems in the source data, all corrected in `clean.py` and written up in
[docs/data_quality.md](docs/data_quality.md). Two worth knowing about here:

The 2021 party column contains both `CPI(M)` (139 rows) and `CPIM` (3 rows).
Nothing errors — it just splits the party in two in any aggregation.

One candidate is named `Arup Roy, S/o Late Prabhat Roy`. That comma shifted his
row's columns under naive parsing, which put his party in the wrong field and
made TMC's 2021 seat count read 214 instead of 215.

## Limitations

**No cross-year candidate tracking.** Only about 543 of 2,079 names match
between the two years even after normalising case and word order, so an
incumbency rate built on that would mislead.

**The district mapping is derived, not sourced.** No workbook here carries
district, so it's inferred from the ECI's contiguous numbering and checked
against constituency names. It reconciles to 23 districts and 294 seats but
hasn't been verified row by row. Regional findings survive a boundary error;
district-level ones might not.

**Turnout runs about 0.13 points below the ECI's published poll percentage**,
because the Detailed Results workbook doesn't itemise rejected votes.

**Nothing here is causal.** It shows what happened, not why.

## Source

ECI statistical reports for the West Bengal Legislative Assembly, 2021 and 2026.
The raw workbooks are committed under `data/raw/` so every figure above can be
traced back.
