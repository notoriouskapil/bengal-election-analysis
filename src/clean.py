"""
Bengal Assembly Elections 2021 vs 2026 - cleaning pipeline.

Reads the raw Election Commission of India workbooks and writes analysis-ready
tables to data/clean/. Rerunnable: it drops and rebuilds every output.

The pipeline corrects nine defects found in the raw data. Each is marked
[DEFECT n] below and documented in docs/data_quality.md.

    python src/clean.py
"""

from pathlib import Path
import re
import sys
import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
RAW     = ROOT / "data" / "raw"
CLEAN   = ROOT / "data" / "clean"
LOOKUPS = ROOT / "data" / "lookups"
CLEAN.mkdir(parents=True, exist_ok=True)

# Totals published in the ECI's own "4 - Highlight" report for 2026.
# The pipeline hard-fails if our numbers drift from these.
#
# Two of these need care, and getting them wrong is how a pipeline ships a
# plausible-looking wrong number:
#   * The elector total covers only the 293 constituencies that polled. It
#     excludes Falta (236,537 electors), which was countermanded.
#   * "Total votes polled" (4a) includes 89,773 REJECTED votes which the
#     Detailed Results do not itemise. Valid votes (4b) and NOTA (5a) are
#     what that workbook actually contains, and both match to the vote.
ECI_2026 = {
    "electors_polled_seats": 68_125_496,   # report 4, item 3(i), 293 seats
    "valid_votes":           63_258_138,   # report 4, item 4b
    "nota_votes":               494_932,   # report 4, item 5a
    "contestants":                2_920,   # report 4, item 2
    "votes_polled_reported": 63_842_843,   # report 4, item 4a - incl. rejected
}

SOURCES = {
    2021: {
        "path": RAW / "2021" / "10-Detailed Results.xlsx",
        "gender_col": "SEX",
        "pct_col": "% VOTES POLLED",
    },
    2026: {
        "path": RAW / "2026" / "10-Detailed_Results_1778165388.xlsx",
        "gender_col": "GENDER",
        "pct_col": "OVER VALID VOTES + NOTA",
    },
}

CANON = {}
for _, r in pd.read_csv(LOOKUPS / "party_canonical.csv").iterrows():
    CANON[r["raw_party"]] = r["canonical_party"]


def log(msg):
    print(msg, flush=True)


# --------------------------------------------------------------------------
# Parse one raw ECI "Detailed Results" workbook
# --------------------------------------------------------------------------
def parse_year(year):
    cfg = SOURCES[year]
    raw = pd.read_excel(cfg["path"], header=None)

    # The real header sits on row index 3; rows above are report title lines.
    df = raw.iloc[3:].reset_index(drop=True)
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)

    df = df[[
        "STATE/UT NAME", "AC NO.", "AC NAME", "CANDIDATE NAME",
        cfg["gender_col"], "AGE", "CATEGORY", "PARTY",
        "GENERAL", "POSTAL", "TOTAL", cfg["pct_col"], "TOTAL ELECTORS",
    ]].copy()
    df.columns = [
        "state", "ac_no", "ac_name_raw", "candidate",
        "gender", "age", "category", "party",
        "general_votes", "postal_votes", "total_votes", "vote_pct", "total_electors",
    ]

    # Summary/total rows carry no constituency or candidate.
    df = df[df.state.notna() & df.ac_no.notna() & df.candidate.notna()].copy()

    for c in ["ac_no", "age", "general_votes", "postal_votes",
              "total_votes", "vote_pct", "total_electors"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ac_no"] = df.ac_no.astype(int)

    # [DEFECT 8] Candidate names carry a serial prefix ("1 Dadhiram Ray") and,
    # in 2021, embedded commas ("Arup Roy, S/o Late Prabhat Roy").
    df["candidate"] = (df.candidate.astype(str)
                       .str.replace(r"^\d+\s+", "", regex=True).str.strip())

    # [DEFECT 1] CPIM and CPI(M) coexist in 2021 - 3 rows against 139.
    # Left unmapped this silently splits the party in any GROUP BY.
    df["party"] = (df.party.fillna("UNKNOWN").astype(str).str.strip().str.upper()
                   .map(lambda p: CANON.get(p, p)))

    df["year"] = year
    log(f"  {year}: {len(df):>5} rows  {df.ac_no.nunique():>3} constituencies  "
        f"{df.party.nunique():>2} party labels")
    return df


log("Parsing raw ECI workbooks")
raw21, raw26 = parse_year(2021), parse_year(2026)
allrows = pd.concat([raw21, raw26], ignore_index=True)


# --------------------------------------------------------------------------
# Constituencies  [DEFECT 3, 4, 5]
# --------------------------------------------------------------------------
log("\nBuilding constituency table")

# [DEFECT 3] 2026 names carry a "(SC)"/"(ST)" reservation tag, 2021 names do
# not, so ac_name matches 0 of 294 across years. Parse the tag into a column,
# strip it, and use ac_no as the only join key.
def split_reservation(name):
    m = re.search(r"\((SC|ST)\)\s*$", str(name).strip())
    return (re.sub(r"\s*\((SC|ST)\)\s*$", "", str(name)).strip().upper(),
            m.group(1) if m else "GEN")

names26 = raw26.groupby("ac_no").ac_name_raw.first()
names21 = raw21.groupby("ac_no").ac_name_raw.first()

cons = pd.DataFrame({"ac_no": range(1, 295)})
cons["ac_name"]      = cons.ac_no.map(lambda n: split_reservation(names26.get(n, names21.get(n)))[0])
cons["reservation"]  = cons.ac_no.map(lambda n: split_reservation(names26.get(n, names21.get(n)))[1])
cons["is_reserved"]  = (cons.reservation != "GEN").astype(int)
cons["ac_name_2021"] = cons.ac_no.map(names21)
cons["ac_name_2026"] = cons.ac_no.map(names26)

geo = pd.read_csv(LOOKUPS / "constituencies.csv")
cons = cons.merge(geo, on="ac_no", how="left", validate="1:1")

# [DEFECT 4] ac_name is not unique even within one year - "Bishnupur" is two
# different seats in 2021 (ac_no 146 and 255). Never join on name.
dupes = cons[cons.duplicated("ac_name", keep=False)].ac_name.unique()
log(f"  duplicate constituency names (join on ac_no, never name): {list(dupes)}")
log(f"  reservation: {dict(cons.reservation.value_counts())}")


# --------------------------------------------------------------------------
# NOTA  [DEFECT 2]
# --------------------------------------------------------------------------
log("\nSplitting NOTA out of the candidate table")
# [DEFECT 2] 294 NOTA rows per year sat inside the candidate table with null
# gender, age and category - the entirety of the dataset's "missing data".
nota = (allrows[allrows.party == "NOTA"]
        [["year", "ac_no", "total_votes", "vote_pct"]]
        .rename(columns={"total_votes": "nota_votes", "vote_pct": "nota_pct"})
        .sort_values(["year", "ac_no"]).reset_index(drop=True))
log(f"  nota rows: {len(nota)}  ({nota.groupby('year').size().to_dict()})")

results = allrows[allrows.party != "NOTA"].copy()


# --------------------------------------------------------------------------
# Electorate and turnout
# --------------------------------------------------------------------------
log("\nBuilding electorate table")
electors = allrows.groupby(["year", "ac_no"]).total_electors.first().reset_index()
polled   = allrows.groupby(["year", "ac_no"]).total_votes.sum().reset_index(name="votes_polled")
elec = electors.merge(polled, on=["year", "ac_no"])
elec["turnout_pct"] = (elec.votes_polled / elec.total_electors * 100).round(2)


# --------------------------------------------------------------------------
# Results: position within seat, recomputed vote share
# --------------------------------------------------------------------------
log("Ranking candidates within each seat")
seat_total = allrows.groupby(["year", "ac_no"]).total_votes.transform("sum")
allrows["vote_pct_calc"] = (allrows.total_votes / seat_total * 100).round(2)
results = allrows[allrows.party != "NOTA"].copy()
results["position"] = (results.groupby(["year", "ac_no"]).total_votes
                       .rank(method="first", ascending=False).astype(int))
results = results[[
    "year", "ac_no", "candidate", "gender", "age", "category", "party",
    "general_votes", "postal_votes", "total_votes", "vote_pct", "position",
]].sort_values(["year", "ac_no", "position"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Winners  [DEFECT 6, 7, 9]
# --------------------------------------------------------------------------
log("Deriving winners and margins")
w = results[results.position == 1].copy()
r = (results[results.position == 2]
     [["year", "ac_no", "candidate", "party", "total_votes"]]
     .rename(columns={"candidate": "runner_up", "party": "runner_up_party",
                      "total_votes": "runner_up_votes"}))
win = w.merge(r, on=["year", "ac_no"], how="left").merge(
    elec[["year", "ac_no", "votes_polled", "total_electors", "turnout_pct"]],
    on=["year", "ac_no"], how="left")

win["win_margin"] = win.total_votes - win.runner_up_votes

# [DEFECT 9] The original pipeline expressed margin as a share of ELECTORS.
# Published psephology uses share of VOTES POLLED. Both are kept, named
# explicitly, so no reader has to guess which definition is in play.
win["margin_pct_polled"]   = (win.win_margin / win.votes_polled * 100).round(2)
win["margin_pct_electors"] = (win.win_margin / win.total_electors * 100).round(2)

win = win.rename(columns={"candidate": "winner", "party": "winner_party",
                          "total_votes": "winner_votes"})
win = win[[
    "year", "ac_no", "winner", "winner_party", "gender", "age", "category",
    "winner_votes", "runner_up", "runner_up_party", "runner_up_votes",
    "win_margin", "margin_pct_polled", "margin_pct_electors",
    "votes_polled", "total_electors", "turnout_pct",
]].sort_values(["year", "ac_no"]).reset_index(drop=True)

# [DEFECT 5] Falta (ac_no 144) held no poll in 2026 - the ECI Highlight report
# itself counts 293 constituencies. Recorded explicitly so it is excluded on
# purpose rather than vanishing from aggregates unnoticed.
status = []
for year in (2021, 2026):
    have = set(results[results.year == year].ac_no)
    for n in range(1, 295):
        status.append({"year": year, "ac_no": n,
                       "result_status": "polled" if n in have else "no_poll"})
status = pd.DataFrame(status)
log(f"  no_poll seats: "
    f"{status[status.result_status=='no_poll'][['year','ac_no']].to_dict('records')}")

# [DEFECT 6] A person may win two seats; [DEFECT 7] and two different people
# may share a name. Neither is an error to remove - both are flagged so that
# seat counts and people counts are never silently conflated.
dup = (win.groupby(["year", "winner"]).filter(lambda g: len(g) > 1)
       .sort_values(["year", "winner"]))
flags = []
for (year, name), g in dup.groupby(["year", "winner"]):
    same = g.age.nunique() == 1 and g.winner_party.nunique() == 1
    for _, row in g.iterrows():
        flags.append({"year": year, "ac_no": row.ac_no, "name": name,
                      "age": row.age, "party": row.winner_party,
                      "flag": "same_person_two_seats" if same else "different_people_same_name"})
flags = pd.DataFrame(flags)
log(f"  duplicate winner names flagged: {len(flags)} rows")
for _, f in flags.iterrows():
    log(f"    {f.year} ac {f.ac_no:>3} {f['name']:<24} age {f.age:.0f} {f.party:<6} {f.flag}")


# --------------------------------------------------------------------------
# Assertions - the pipeline fails loudly rather than shipping wrong numbers
# --------------------------------------------------------------------------
log("\nValidating against the ECI Highlight report")
errors = []

def check(label, got, want):
    ok = got == want
    log(f"  {'PASS' if ok else 'FAIL'}  {label:<38} {got:>12,}  expected {want:>12,}")
    if not ok:
        errors.append(f"{label}: got {got}, expected {want}")

polled26 = set(status[(status.year == 2026) & (status.result_status == "polled")].ac_no)
e26 = elec[(elec.year == 2026) & (elec.ac_no.isin(polled26))]
r26 = results[results.year == 2026]
n26 = nota[nota.year == 2026]

check("2026 electors (293 polled seats)", int(e26.total_electors.sum()), ECI_2026["electors_polled_seats"])
check("2026 valid votes",      int(r26.total_votes.sum()),             ECI_2026["valid_votes"])
check("2026 NOTA votes",       int(n26.nota_votes.sum()),              ECI_2026["nota_votes"])
check("2026 contestants",      int(len(r26)),                          ECI_2026["contestants"])
check("2026 seats with result", int((status[(status.year==2026)].result_status=="polled").sum()), 293)
check("2021 seats with result", int((status[(status.year==2021)].result_status=="polled").sum()), 294)
check("constituencies mapped",  int(cons.region.notna().sum()),        294)

internal = (allrows.general_votes + allrows.postal_votes == allrows.total_votes).all()
log(f"  {'PASS' if internal else 'FAIL'}  general + postal == total            {internal}")
if not internal:
    errors.append("general + postal != total on some rows")

rejected = ECI_2026["votes_polled_reported"] - int(r26.total_votes.sum() + n26.nota_votes.sum())
log(f"  NOTE  rejected votes not in Detailed Results  {rejected:>12,}  "
    f"(turnout below runs {rejected / ECI_2026['electors_polled_seats'] * 100:.2f}pp under the ECI's poll %)")

drift = (allrows.vote_pct_calc - allrows.vote_pct).abs().max()
log(f"  {'PASS' if drift < 0.05 else 'FAIL'}  vote_pct matches recomputed share   max drift {drift:.3f}")
if drift >= 0.05:
    errors.append(f"vote_pct drift {drift}")

if errors:
    log("\nVALIDATION FAILED:")
    for e in errors:
        log(f"  - {e}")
    sys.exit(1)


# --------------------------------------------------------------------------
# Write
# --------------------------------------------------------------------------
log("\nWriting data/clean/")
outputs = {
    "constituencies.csv": cons,
    "results.csv":        results,
    "winners.csv":        win,
    "nota.csv":           nota,
    "electorate.csv":     elec,
    "seat_status.csv":    status,
    "name_flags.csv":     flags,
}
for name, df in outputs.items():
    df.to_csv(CLEAN / name, index=False)
    log(f"  {name:<22} {len(df):>5} rows  {len(df.columns):>2} cols")

log("\nClean. Next: python src/load_db.py")
