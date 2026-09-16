# West Bengal Assembly Elections: 2021 vs 2026

A comparative analysis of two West Bengal state elections, built from the
Election Commission of India's published statistical reports.

**Scope:** 294 constituencies, 5,052 candidates, two elections.
**Stack:** Python (pandas) · SQLite · Power BI

---

## Findings

> Analysis in progress. Replace this section with your own conclusions —
> written as sentences with numbers in them, before any chart appears.

The dataset's central puzzle, and the thing worth leading with once resolved:

**A 15-point vote swing produced a 135-seat reversal.** TMC's vote share fell
from 48.6% to 41.1% and BJP's rose from 38.4% to 46.2% — a swing of roughly 15
points between them. Seats moved from TMC 215 / BJP 77 to BJP 207 / TMC 80.
Under first-past-the-post, seats are won one at a time on a plurality, so a
swing concentrated near the margin flips a disproportionate number of them at
once.

**Turnout rose to 93.6% from 82.2%, while the electorate shrank about 6%**
(73.2M to 68.1M). A smaller denominator raises the percentage without a single
extra vote being cast. Whether a roll revision explains this is unresolved and
must be settled before any turnout figure is published. See
[`docs/data_quality.md`](docs/data_quality.md).

### Seats and vote share

| Party | 2021 vote | 2026 vote | 2021 seats | 2026 seats |
|---|---|---|---|---|
| TMC | 48.55% | 41.12% | 215 | 80 |
| BJP | 38.39% | 46.20% | 77 | 207 |
| CPI(M) | 4.78% | 4.49% | 0 | 1 |
| INC | 3.06% | 2.99% | 0 | 2 |
| NOTA | 1.10% | 0.78% | — | — |

Vote share is a percentage of valid votes, excluding NOTA.

---

## Running it

```bash
pip install -r requirements.txt
python src/clean.py      # raw ECI workbooks -> data/clean/
python src/load_db.py    # data/clean/ -> bengal_elections.db
```

`src/clean.py` validates its own output against the totals the ECI publishes in
its Highlight report and **exits non-zero if they drift**:

```
PASS  2026 electors (293 polled seats)   68,125,496
PASS  2026 valid votes                   63,258,138
PASS  2026 NOTA votes                       494,932
PASS  2026 contestants                        2,920
```

---

## Layout

```
data/raw/          15 ECI workbooks, as downloaded
data/clean/        analysis-ready tables (generated)
data/lookups/      party canonicalisation, constituency -> district -> region
data/reference/    the earlier pipeline and its output, kept for comparison
src/clean.py       raw -> clean, with assertions
src/load_db.py     clean -> SQLite
sql/schema.sql     schema, indexes and two convenience views
docs/              data quality report
```

### Tables

| Table | Grain | Rows |
|---|---|---|
| `constituencies` | one per seat | 294 |
| `results` | one per candidate per election, NOTA excluded | 5,052 |
| `winners` | one per seat per election, runner-up alongside | 587 |
| `nota` | one per seat per election | 588 |
| `electorate` | one per seat per election | 588 |
| `seat_status` | marks Falta 2026 as `no_poll` | 588 |
| `name_flags` | winners sharing a name | 8 |

Views `v_results` and `v_winners` join geography in for you.

---

## Three things to know before querying

**Join on `ac_no`, never on name.** Constituency names match 0 of 294 across the
two years, and `Bishnupur` is two different seats.

**Filter `seat_status`.** Falta held no poll in 2026. Excluding it deliberately
is correct; letting it disappear silently is not.

**Use `margin_pct_polled`, not `margin_pct_electors`.** Both are present. The
first is the convention published figures use.

---

## Data quality

Nine defects were found and corrected; two are documented as unresolved. Full
report: [`docs/data_quality.md`](docs/data_quality.md).

The one worth knowing about here: in 2021 the party column carried both
`CPI(M)` (139 rows) and `CPIM` (3 rows). It raises no error — it just quietly
splits the party in any aggregation. Separately, a single unescaped comma in the
candidate name `Arup Roy, S/o Late Prabhat Roy` shifted his row's columns under
naive parsing and made TMC's 2021 seat count read as 214 rather than the
correct 215.

---

## Limitations

- **Cross-year candidate tracking is not attempted.** Only about 543 of 2,079
  names match between the two years even after normalising case and token order,
  so any incumbency rate would be unreliable enough to mislead.
- **The district mapping is derived, not sourced.** No ECI workbook here carries
  district. See the provenance warning in the data quality report; region-level
  findings are robust to a boundary error, district-level ones are not.
- **No booth-level analysis.** The data does not exist at that grain in these
  reports.
- **No predictive model.** 294 rows per election. A model here would invite
  questions about sample size that add nothing the descriptive analysis has not
  already shown.
- **Turnout runs ~0.13pp below the ECI's published poll percentage**, because
  the Detailed Results workbook does not itemise rejected votes.

---

## Source

Election Commission of India statistical reports for the West Bengal
Legislative Assembly elections, 2021 and 2026. Raw workbooks are committed
under `data/raw/` as the provenance for every figure quoted above.
