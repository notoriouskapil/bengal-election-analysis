# Data quality notes

Source: ECI statistical reports, West Bengal Legislative Assembly 2021 and 2026,
downloaded 7 May 2026.

Everything below was found by profiling the raw workbooks. All of it is handled
in `src/clean.py`. The first two are the ones that matter — they produce wrong
answers rather than errors.

## Two labels for one party

2021 has both `CPI(M)` (139 rows) and `CPIM` (3 rows). Same party. Any
`GROUP BY party` splits it in two and understates CPI(M), and nothing warns you.

Fixed with `data/lookups/party_canonical.csv`, which also maps the ECI's `AITC`
code to `TMC`.

Not resolved: `AJSUP`/`AJUP`, `AIMF`/`AISF` and `UTSAP`/`SAP` look like they
might be the same parties under different labels. `RSSCMJP` polled 1.36% in 2021
then disappears; `AISF` polled 1.54% in 2026 having not existed before. These
could be renames. I haven't checked them against report 3 (List of Political
Parties Participated), so don't claim a party emerged or vanished on this data.

## Turnout is implausible and the roll shrank

93.6% in 2026 against 82.2% in 2021, with the electorate down from roughly 73.2M
to 68.1M. Rolls don't shrink 6% in five years on their own.

This isn't a bug in the pipeline — the ECI's own Highlight report states 93.71%.
The roll contraction tracks the turnout rise closely by region, which points to a
revision of the electoral register rather than a surge in participation.

I haven't confirmed what drove the revision. Treat the turnout figure as
explained-in-part, not settled.

## Constituency names don't join across years

2021 is mixed case (`Mekliganj`), 2026 is upper case with a reservation tag
(`MEKLIGANJ (SC)`). Exact match rate across years: 0 of 294.

The tag is parsed into `reservation` / `is_reserved`, the name normalised, and
`ac_no` used as the only join key.

## Names aren't unique within a year either

`Bishnupur` is two constituencies — `ac_no` 146 in South 24 Parganas and 255 in
Bankura. So `ac_name` isn't a key even within one election.

## A candidate name isn't a person

| Year | Name | Ages | |
|---|---|---|---|
| 2021 | HUMAYUN KABIR | 61, 59 | two people |
| 2026 | Arup Kumar Das | 52, 68 | two people |
| 2026 | Adhikari Suvendu | 57, 57 | one person, two seats |
| 2026 | Humayun Kabir | 63, 63 | one person, two seats |

Winning two seats is legal — the winner vacates one within 14 days. So 293 seats
in 2026 have 290 distinct winners. Seat counts and people counts are different
numbers.

All eight rows are in `data/clean/name_flags.csv`.

I didn't attempt cross-year candidate tracking. Even after normalising case and
word order only about 543 of 2,079 names match, and matching on name alone
fans out — joining 2026 winners to 2021 candidates by name returns 300 rows for
293 seats.

## One seat held no poll

Falta (`ac_no` 144) has no 2026 result, just a zero-vote NOTA row. The ECI
Highlight report independently counts 293 constituencies, so this is a genuine
countermanded poll.

Recorded in `seat_status.csv` as `no_poll`. Worth excluding deliberately — left
in, it reads as a seat where turnout fell 87 points, which drags any average.

## Margin was measured against the wrong denominator

The earlier version of this pipeline expressed `win_margin_pct` as a share of
registered electors. Published figures use share of votes polled, which is a
larger number and the comparable one.

Both are kept now, named `margin_pct_polled` and `margin_pct_electors`.

## Serial prefixes and one awkward comma

Candidate names come through as `1 Dadhiram Ray` — a ballot serial that needs
stripping. And one 2021 name contains a comma: `Arup Roy, S/o Late Prabhat Roy`.

That comma matters. Split naively, it shifts every column after it one to the
right, which moved his party into the category field and made TMC's 2021 seat
count read 214 instead of 215.

## NOTA was sitting in the candidate table

294 NOTA rows per year with null gender, age and category — which was the whole
of the dataset's apparent missing data. Now in `nota.csv`.

## Reconciling with the published totals

Both of these turned up when the assertions first ran, and both are properties of
the source rather than mistakes.

The ECI's elector total of 68,125,496 covers only the 293 seats that polled.
All 294 comes to 68,362,033 — the difference is exactly Falta's 236,537.

The ECI reports 63,842,843 votes polled; the Detailed Results workbook contains
63,753,070. The 89,773 gap is rejected votes, which that workbook doesn't
itemise. Valid votes (63,258,138) and NOTA (494,932) both match exactly.

So `turnout_pct` here runs about 0.13 points below the ECI's published poll
percentage. It's `(valid + NOTA) / electors`.

## Vote share convention

Party vote share here is a percentage of valid votes, excluding NOTA. NOTA is
reported separately as a share of votes polled. The ECI's own `% VOTES POLLED`
column uses valid + NOTA as its denominator, so these figures sit marginally
above it. Worth stating whenever you quote a number.

## About the district mapping

`data/lookups/constituencies.csv` maps all 294 seats to 23 districts and 8
regions. No ECI workbook in this repo carries district — West Bengal numbers its
constituencies contiguously by district, so the mapping is derived from that and
checked against the constituency names.

It reconciles: 23 districts, 294 seats, matching the state's actual district
count. But it isn't verified row by row against an official list. Regional
findings survive a one-seat boundary error. District-level claims should be
checked first.
