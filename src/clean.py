"""Builds the clean tables from the raw ECI workbooks. Run before load_db.py."""

from pathlib import Path
import re
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
LOOKUPS = ROOT / "data" / "lookups"
CLEAN.mkdir(parents=True, exist_ok=True)

# From the ECI's "4 - Highlight" report. Two traps here:
# the elector total covers only the 293 seats that polled (excludes Falta),
# and "votes polled" includes 89,773 rejected votes that the Detailed Results
# workbook doesn't itemise - so we check valid votes and NOTA separately.
ECI_2026 = {
    "electors": 68_125_496,
    "valid_votes": 63_258_138,
    "nota": 494_932,
    "contestants": 2_920,
    "votes_polled_reported": 63_842_843,
}

# The two years use different column names for the same things.
SOURCES = {
    2021: ("10-Detailed Results.xlsx", "SEX", "% VOTES POLLED"),
    2026: ("10-Detailed_Results_1778165388.xlsx", "GENDER", "OVER VALID VOTES + NOTA"),
}

canon = pd.read_csv(LOOKUPS / "party_canonical.csv")
CANON = dict(zip(canon.raw_party, canon.canonical_party))


def parse_year(year):
    filename, gender_col, pct_col = SOURCES[year]
    raw = pd.read_excel(RAW / str(year) / filename, header=None)

    # First three rows are report titles; the header is row 3.
    df = raw.iloc[3:].reset_index(drop=True)
    df.columns = df.iloc[0]
    df = df[1:].reset_index(drop=True)

    df = df[["STATE/UT NAME", "AC NO.", "AC NAME", "CANDIDATE NAME",
             gender_col, "AGE", "CATEGORY", "PARTY",
             "GENERAL", "POSTAL", "TOTAL", pct_col, "TOTAL ELECTORS"]].copy()
    df.columns = ["state", "ac_no", "ac_name_raw", "candidate", "gender", "age",
                  "category", "party", "general_votes", "postal_votes",
                  "total_votes", "vote_pct", "total_electors"]

    # Drop the summary rows at the bottom of each section.
    df = df[df.state.notna() & df.ac_no.notna() & df.candidate.notna()].copy()

    for c in ["ac_no", "age", "general_votes", "postal_votes",
              "total_votes", "vote_pct", "total_electors"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ac_no"] = df.ac_no.astype(int)

    # Names arrive as "1 Dadhiram Ray" - strip the ballot serial.
    df["candidate"] = df.candidate.astype(str).str.replace(r"^\d+\s+", "", regex=True).str.strip()

    # CPIM and CPI(M) both appear in 2021. Unmapped, that splits the party
    # in two in any GROUP BY and nothing errors.
    df["party"] = (df.party.fillna("UNKNOWN").astype(str).str.strip().str.upper()
                   .map(lambda p: CANON.get(p, p)))

    df["year"] = year
    print(f"  {year}: {len(df)} rows, {df.ac_no.nunique()} seats, {df.party.nunique()} party labels")
    return df


print("Reading raw workbooks")
raw21 = parse_year(2021)
raw26 = parse_year(2026)
allrows = pd.concat([raw21, raw26], ignore_index=True)


def split_reservation(name):
    """MEKLIGANJ (SC) -> ('MEKLIGANJ', 'SC'). 2021 names have no tag."""
    name = str(name).strip()
    m = re.search(r"\((SC|ST)\)\s*$", name)
    return re.sub(r"\s*\((SC|ST)\)\s*$", "", name).strip().upper(), m.group(1) if m else "GEN"


print("\nConstituencies")
names21 = raw21.groupby("ac_no").ac_name_raw.first()
names26 = raw26.groupby("ac_no").ac_name_raw.first()

cons = pd.DataFrame({"ac_no": range(1, 295)})
parsed = cons.ac_no.map(lambda n: split_reservation(names26.get(n, names21.get(n))))
cons["ac_name"] = parsed.str[0]
cons["reservation"] = parsed.str[1]
cons["is_reserved"] = (cons.reservation != "GEN").astype(int)
cons["ac_name_2021"] = cons.ac_no.map(names21)
cons["ac_name_2026"] = cons.ac_no.map(names26)
cons = cons.merge(pd.read_csv(LOOKUPS / "constituencies.csv"), on="ac_no", validate="1:1")

# Bishnupur is two different seats, so ac_name isn't a key even within a year.
dupes = list(cons[cons.duplicated("ac_name", keep=False)].ac_name.unique())
print(f"  names shared by two seats: {dupes}")
print(f"  reservation: {dict(cons.reservation.value_counts())}")

# NOTA sat in the candidate table with null gender/age/category - all of the
# dataset's apparent missing data was this.
nota = (allrows[allrows.party == "NOTA"][["year", "ac_no", "total_votes", "vote_pct"]]
        .rename(columns={"total_votes": "nota_votes", "vote_pct": "nota_pct"})
        .sort_values(["year", "ac_no"]).reset_index(drop=True))
print(f"\nNOTA split out: {len(nota)} rows")

elec = (allrows.groupby(["year", "ac_no"])
        .agg(total_electors=("total_electors", "first"),
             votes_polled=("total_votes", "sum"))
        .reset_index())
elec["turnout_pct"] = (elec.votes_polled / elec.total_electors * 100).round(2)

seat_total = allrows.groupby(["year", "ac_no"]).total_votes.transform("sum")
allrows["vote_pct_calc"] = (allrows.total_votes / seat_total * 100).round(2)

results = allrows[allrows.party != "NOTA"].copy()
results["position"] = (results.groupby(["year", "ac_no"]).total_votes
                       .rank(method="first", ascending=False).astype(int))
results = results[["year", "ac_no", "candidate", "gender", "age", "category", "party",
                   "general_votes", "postal_votes", "total_votes", "vote_pct", "position"]]
results = results.sort_values(["year", "ac_no", "position"]).reset_index(drop=True)

print("Winners and margins")
runners = (results[results.position == 2][["year", "ac_no", "candidate", "party", "total_votes"]]
           .rename(columns={"candidate": "runner_up", "party": "runner_up_party",
                            "total_votes": "runner_up_votes"}))
win = (results[results.position == 1]
       .merge(runners, on=["year", "ac_no"], how="left")
       .merge(elec, on=["year", "ac_no"], how="left"))

win["win_margin"] = win.total_votes - win.runner_up_votes
# Published figures use votes polled as the denominator; the earlier version of
# this pipeline used electors. Keeping both, named, so nobody has to guess.
win["margin_pct_polled"] = (win.win_margin / win.votes_polled * 100).round(2)
win["margin_pct_electors"] = (win.win_margin / win.total_electors * 100).round(2)

win = win.rename(columns={"candidate": "winner", "party": "winner_party",
                          "total_votes": "winner_votes"})
win = win[["year", "ac_no", "winner", "winner_party", "gender", "age", "category",
           "winner_votes", "runner_up", "runner_up_party", "runner_up_votes",
           "win_margin", "margin_pct_polled", "margin_pct_electors",
           "votes_polled", "total_electors", "turnout_pct"]]
win = win.sort_values(["year", "ac_no"]).reset_index(drop=True)

# Falta held no poll in 2026. Recording it explicitly beats letting the seat
# quietly disappear from every aggregate.
status = []
for year in (2021, 2026):
    polled = set(results[results.year == year].ac_no)
    for n in range(1, 295):
        status.append({"year": year, "ac_no": n,
                       "result_status": "polled" if n in polled else "no_poll"})
status = pd.DataFrame(status)
print(f"  no poll: {status[status.result_status == 'no_poll'][['year', 'ac_no']].to_dict('records')}")

# Winners sharing a name: same age and party means one person took two seats
# (legal, they vacate one). Different ages means two different people.
flags = []
dup = win.groupby(["year", "winner"]).filter(lambda g: len(g) > 1)
for (year, name), g in dup.groupby(["year", "winner"]):
    same_person = g.age.nunique() == 1 and g.winner_party.nunique() == 1
    for _, row in g.iterrows():
        flags.append({"year": year, "ac_no": row.ac_no, "name": name, "age": row.age,
                      "party": row.winner_party,
                      "flag": "same_person_two_seats" if same_person
                              else "different_people_same_name"})
flags = pd.DataFrame(flags)
for _, f in flags.iterrows():
    print(f"  {f.year} ac {f.ac_no}: {f['name']} ({f.age:.0f}, {f.party}) - {f.flag}")


print("\nChecking against the ECI Highlight report")
errors = []

def check(label, got, want):
    ok = got == want
    print(f"  {'ok  ' if ok else 'FAIL'} {label:<34} {got:>12,}")
    if not ok:
        errors.append(f"{label}: got {got:,}, expected {want:,}")

polled26 = set(status[(status.year == 2026) & (status.result_status == "polled")].ac_no)
e26 = elec[(elec.year == 2026) & elec.ac_no.isin(polled26)]
r26 = results[results.year == 2026]
n26 = nota[nota.year == 2026]

check("electors, 293 polled seats", int(e26.total_electors.sum()), ECI_2026["electors"])
check("valid votes", int(r26.total_votes.sum()), ECI_2026["valid_votes"])
check("NOTA votes", int(n26.nota_votes.sum()), ECI_2026["nota"])
check("contestants", len(r26), ECI_2026["contestants"])
check("seats polled 2026", len(polled26), 293)
check("seats polled 2021", int((status[status.year == 2021].result_status == "polled").sum()), 294)
check("seats mapped to a region", int(cons.region.notna().sum()), 294)

if not (allrows.general_votes + allrows.postal_votes == allrows.total_votes).all():
    errors.append("general + postal != total on some rows")

drift = (allrows.vote_pct_calc - allrows.vote_pct).abs().max()
if drift >= 0.05:
    errors.append(f"vote_pct drifts from recomputed share by {drift}")

rejected = ECI_2026["votes_polled_reported"] - int(r26.total_votes.sum() + n26.nota_votes.sum())
print(f"  note {rejected:,} rejected votes aren't in the Detailed Results, so turnout")
print(f"       here runs {rejected / ECI_2026['electors'] * 100:.2f}pp under the ECI's poll %")

if errors:
    print("\nFAILED:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)

print("\nWriting data/clean/")
for name, df in [("constituencies", cons), ("results", results), ("winners", win),
                 ("nota", nota), ("electorate", elec), ("seat_status", status),
                 ("name_flags", flags)]:
    df.to_csv(CLEAN / f"{name}.csv", index=False)
    print(f"  {name}.csv  {len(df)} rows")
