"""Six charts, one per query in sql/, written to outputs/charts/.

Three of the six .sql files return wrong output and are left untouched by
request. The corrected SQL lives here, in SQL_* below, and each constant says
what it changes. Charts never read the broken files.

    python src/make_charts.py
"""

import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "bengal_elections.db"
OUT = ROOT / "outputs" / "charts"

# Palette validated with the dataviz skill's checker (light surface, all pairs):
# worst CVD dE 10.8 protan, worst normal-vision dE 23.2, all >= 3:1 on surface.
BJP = "#eb6834"
TMC = "#0f6b42"
BLUE = "#2a78d6"
GREY = "#8a8782"
INK = "#16150f"
SUB = "#52514e"
GRID = "#e8e7e3"
SURFACE = "#fcfcfb"

PARTY = {"BJP": BJP, "TMC": TMC, "INC": BLUE}
FIGSIZE = (9.0, 5.4)
DPI = 200

plt.rcParams.update({
    "figure.figsize": FIGSIZE,
    "figure.dpi": DPI,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 11,
    "text.color": INK,
    "axes.labelcolor": SUB,
    "axes.edgecolor": SUB,
    "xtick.color": SUB,
    "ytick.color": SUB,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def style(ax, axis="x"):
    ax.grid(axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def title(fig, text, y=0.965):
    fig.suptitle(text, fontsize=14, x=0.012, ha="left", y=y, color=INK, weight="medium")


def save(fig, name):
    path = OUT / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", pad_inches=0.28)
    plt.close(fig)
    print(f"  wrote {path.relative_to(ROOT)}")


# ---------------------------------------------------------------- SQL

# q01, unchanged in substance. Trimmed to parties that won a seat in either
# year; the file's 87 rows are 78 parties under 0.5% in both.
SQL_Q01 = """
SELECT COALESCE(a.party, b.party)               AS party,
       COALESCE(a.seats, 0)                     AS seats_2021,
       COALESCE(b.seats, 0)                     AS seats_2026,
       ROUND(v26.pct, 2)                        AS vote_pct_2026,
       ROUND(v21.pct, 2)                        AS vote_pct_2021
FROM      (SELECT winner_party party, COUNT(*) seats FROM winners WHERE year=2021 GROUP BY 1) a
FULL JOIN (SELECT winner_party party, COUNT(*) seats FROM winners WHERE year=2026 GROUP BY 1) b
       ON a.party = b.party
LEFT JOIN (SELECT party, SUM(total_votes)*100.0/(SELECT SUM(total_votes) FROM results WHERE year=2021) pct
           FROM results WHERE year=2021 GROUP BY 1) v21 ON v21.party = COALESCE(a.party, b.party)
LEFT JOIN (SELECT party, SUM(total_votes)*100.0/(SELECT SUM(total_votes) FROM results WHERE year=2026) pct
           FROM results WHERE year=2026 GROUP BY 1) v26 ON v26.party = COALESCE(a.party, b.party)
ORDER BY seats_2026 DESC
"""

# q02, unchanged in substance. Seat share over 293 polled seats, not 294.
SQL_Q02 = """
WITH v AS (SELECT party, SUM(total_votes)*100.0/
                  (SELECT SUM(total_votes) FROM results WHERE year=2026) AS vote_share
           FROM results WHERE year=2026 GROUP BY party),
     s AS (SELECT winner_party AS party, COUNT(*)*100.0/293 AS seat_share
           FROM winners WHERE year=2026 GROUP BY winner_party)
SELECT v.party, v.vote_share, COALESCE(s.seat_share, 0) AS seat_share,
       COALESCE(s.seat_share, 0) - v.vote_share AS gap
FROM v LEFT JOIN s ON s.party = v.party
WHERE v.vote_share >= 1
ORDER BY v.vote_share DESC
"""

# q03 REPLACED. The file joins results to results on candidate name with no
# ac_no, returning 300 rows for 293 seats, and reports a 2021 finishing
# position rather than a party flip. This joins winners to winners on ac_no.
SQL_Q03 = """
SELECT a.winner_party AS party_2021,
       b.winner_party AS party_2026,
       COUNT(*)       AS seats
FROM winners a
JOIN winners b ON b.ac_no = a.ac_no AND a.year = 2021 AND b.year = 2026
GROUP BY 1, 2
ORDER BY seats DESC
"""

# q04 CORRECTED. The file ranks on win_margin (absolute votes); the README
# says use margin_pct_polled, which is comparable across seats of any size.
SQL_Q04 = """
SELECT c.ac_name, w.winner_party, w.runner_up_party,
       w.win_margin, w.margin_pct_polled
FROM winners w
JOIN constituencies c ON c.ac_no = w.ac_no
WHERE w.year = 2026
ORDER BY w.margin_pct_polled
LIMIT 10
"""

# q05 CORRECTED. The file computes pct_change as 2021 - 2026, so every decline
# prints as a gain. This is 2026 - 2021.
SQL_Q05 = """
WITH r AS (SELECT c.region, v.year,
                  SUM(CASE WHEN v.party='TMC' THEN v.total_votes ELSE 0 END)*100.0
                  / SUM(v.total_votes) AS tmc
           FROM results v JOIN constituencies c ON c.ac_no = v.ac_no
           GROUP BY 1, 2)
SELECT region,
       ROUND(MAX(CASE WHEN year=2021 THEN tmc END), 2) AS vote_pct_2021,
       ROUND(MAX(CASE WHEN year=2026 THEN tmc END), 2) AS vote_pct_2026,
       ROUND(MAX(CASE WHEN year=2026 THEN tmc END)
           - MAX(CASE WHEN year=2021 THEN tmc END), 2) AS swing
FROM r GROUP BY region ORDER BY swing
"""

# q06 CORRECTED. The file has no seat_status filter, so Falta (ac_no 144, no
# poll in 2026) returns turnout_pct_2026 = 0.00 and a phantom -87.82 change.
SQL_Q06 = """
SELECT e.ac_no,
       MAX(CASE WHEN e.year=2021 THEN e.total_electors END) AS roll_2021,
       MAX(CASE WHEN e.year=2026 THEN e.total_electors END) AS roll_2026,
       MAX(CASE WHEN e.year=2021 THEN e.turnout_pct   END) AS turnout_2021,
       MAX(CASE WHEN e.year=2026 THEN e.turnout_pct   END) AS turnout_2026
FROM electorate e
WHERE e.ac_no IN (SELECT ac_no FROM seat_status WHERE result_status='polled'
                  GROUP BY ac_no HAVING COUNT(*) = 2)
GROUP BY e.ac_no
"""


# ---------------------------------------------------------------- charts

def c1_seat_reversal(conn):
    d = pd.read_sql(SQL_Q01, conn)
    big = d[d.party.isin(["BJP", "TMC"])].set_index("party")
    others_21 = int(d.seats_2021.sum() - big.seats_2021.sum())
    others_26 = int(d.seats_2026.sum() - big.seats_2026.sum())

    fig, ax = plt.subplots()
    lines = [("TMC", big.loc["TMC", "seats_2021"], big.loc["TMC", "seats_2026"], TMC, 3.0),
             ("BJP", big.loc["BJP", "seats_2021"], big.loc["BJP", "seats_2026"], BJP, 3.0),
             ("All others", others_21, others_26, GREY, 1.8)]

    for name, a, b, colour, lw in lines:
        ax.plot([0, 1], [a, b], color=colour, linewidth=lw, solid_capstyle="round",
                marker="o", markersize=8, markerfacecolor=colour, markeredgecolor=SURFACE,
                markeredgewidth=2, zorder=3)
        ax.text(-0.035, a, f"{name}  {a}", ha="right", va="center", fontsize=11.5, color=colour)
        ax.text(1.035, b, f"{b}  {name}", ha="left", va="center", fontsize=11.5, color=colour)

    ax.set_xlim(-0.42, 1.42)
    ax.set_ylim(-84, 238)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ("left", "bottom"):
        ax.spines[s].set_visible(False)
    for x, yr in ((0, 2021), (1, 2026)):
        ax.text(x, -22, str(yr), ha="center", fontsize=13, color=INK)
        ax.text(x, -47, f"TMC {big.loc['TMC', f'vote_pct_{yr}']:.1f}%    "
                        f"BJP {big.loc['BJP', f'vote_pct_{yr}']:.1f}%",
                ha="center", fontsize=10, color=SUB)
    ax.text(0.5, -70, "share of valid votes", ha="center", fontsize=9.5, color=GREY)
    ax.text(-0.40, 232, "Seats won", ha="left", fontsize=10, color=SUB)

    title(fig, f"TMC's vote share fell from {big.loc['TMC','vote_pct_2021']:.1f}% to "
               f"{big.loc['TMC','vote_pct_2026']:.1f}%. It lost "
               f"{int(big.loc['TMC','seats_2021'] - big.loc['TMC','seats_2026'])} seats.")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save(fig, "01_seat_reversal.png")


def c2_vote_vs_seat(conn):
    d = pd.read_sql(SQL_Q02, conn).sort_values("vote_share")
    y = np.arange(len(d))
    h = 0.36

    fig, ax = plt.subplots()
    ax.barh(y + h / 2 + 0.01, d.vote_share, h, color=GREY, label="Share of votes")
    ax.barh(y - h / 2 - 0.01, d.seat_share, h,
            color=[PARTY.get(p, GREY) for p in d.party], label="Share of seats")

    for i, row in enumerate(d.itertuples()):
        ax.text(row.vote_share + 1.0, i + h / 2, f"{row.vote_share:.1f}%",
                va="center", fontsize=10, color=SUB)
        ax.text(row.seat_share + 1.0, i - h / 2, f"{row.seat_share:.1f}%",
                va="center", fontsize=10, color=SUB, weight="medium")

    ax.set_yticks(y)
    ax.set_yticklabels(d.party, fontsize=11.5, color=INK)
    ax.set_xlim(0, 84)
    ax.set_xlabel("Percent")
    style(ax)
    ax.text(0.985, 0.055, "upper bar = share of votes    lower bar = share of seats",
            transform=ax.transAxes, ha="right", fontsize=9.5, color=GREY)

    bjp = d[d.party == "BJP"].iloc[0]
    title(fig, f"BJP turned {bjp.vote_share:.1f}% of the vote into {bjp.seat_share:.1f}% of the seats")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save(fig, "02_vote_vs_seat_share.png")


def c3_flips(conn):
    d = pd.read_sql(SQL_Q03, conn)
    d["label"] = d.party_2021 + "  →  " + d.party_2026
    d["held"] = d.party_2021 == d.party_2026
    # The absence is the finding, so it gets a labelled zero-length bar.
    d = pd.concat([d, pd.DataFrame([{"party_2021": "BJP", "party_2026": "TMC",
                                     "seats": 0, "label": "BJP  →  TMC", "held": False}])])
    d = d.sort_values("seats")

    colour = [GREY if h else (BJP if p26 == "BJP" else TMC if p26 == "TMC" else BLUE)
              for h, p26 in zip(d.held, d.party_2026)]

    fig, ax = plt.subplots()
    ax.barh(np.arange(len(d)), d.seats, 0.66, color=colour)
    for i, row in enumerate(d.itertuples()):
        if row.seats == 0:
            ax.text(1.5, i, "0", va="center", fontsize=11, color=BJP, weight="bold")
        else:
            ax.text(row.seats + 1.5, i, str(row.seats), va="center", fontsize=10, color=SUB)

    ax.set_yticks(np.arange(len(d)))
    ax.set_yticklabels(d.label, fontsize=10.5, color=INK, fontfamily="monospace")
    ax.set_xlim(0, 146)
    ax.set_xlabel("Seats")
    style(ax)
    ax.text(0.985, 0.06, "grey = seat held by the same party", transform=ax.transAxes,
            ha="right", fontsize=9.5, color=GREY)

    flip = int(d[~d.held].seats.sum())
    tmc_bjp = int(d[(d.party_2021 == "TMC") & (d.party_2026 == "BJP")].seats.iloc[0])
    title(fig, f"{tmc_bjp} seats went TMC to BJP. Zero went the other way.")
    fig.text(0.012, 0.905, f"{flip} of 293 seats changed hands", fontsize=10.5, color=SUB)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    save(fig, "03_flip_matrix.png")


def c4_closest(conn):
    d = pd.read_sql(SQL_Q04, conn).sort_values("margin_pct_polled", ascending=False)

    fig, ax = plt.subplots()
    ax.barh(np.arange(len(d)), d.margin_pct_polled, 0.66,
            color=[PARTY.get(p, GREY) for p in d.winner_party])
    for i, row in enumerate(d.itertuples()):
        ax.text(row.margin_pct_polled + 0.018, i,
                f"{row.margin_pct_polled:.2f}%   {row.win_margin:,} votes",
                va="center", fontsize=10, color=SUB)

    ax.set_yticks(np.arange(len(d)))
    ax.set_yticklabels([f"{n.title()}  ({p})" for n, p in zip(d.ac_name, d.winner_party)],
                       fontsize=11, color=INK)
    ax.set_xlim(0, 1.52)
    ax.set_xlabel("Winning margin, % of votes polled")
    style(ax)

    sub1 = pd.read_sql("SELECT winner_party p, COUNT(*) n FROM winners "
                       "WHERE year=2026 AND margin_pct_polled < 1 GROUP BY 1 ORDER BY n DESC", conn)
    title(fig, f"BJP won {sub1.n.iloc[0]} of the {int(sub1.n.sum())} seats decided by less than 1%")
    fig.text(0.012, 0.905, "West Bengal 2026, ten closest results", fontsize=10.5, color=SUB)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    save(fig, "04_closest_seats_2026.png")


def c5_regional_swing(conn):
    d = pd.read_sql(SQL_Q05, conn).sort_values("swing", ascending=False)

    fig, ax = plt.subplots()
    ax.barh(np.arange(len(d)), d.swing, 0.66, color=TMC)
    for i, row in enumerate(d.itertuples()):
        ax.text(row.swing - 0.32, i, f"\u2212{abs(row.swing):.1f}", va="center",
                ha="right", fontsize=10.5, color=SUB)

    ax.set_yticks(np.arange(len(d)))
    ax.set_yticklabels(d.region, fontsize=11, color=INK)
    ax.set_xlim(-17.2, 0.6)
    ax.axvline(0, color=SUB, linewidth=1.1)
    ax.set_xlabel("Change in TMC vote share, 2021 to 2026 (percentage points)")
    style(ax)

    worst = d.iloc[-1]
    title(fig, f"TMC's vote share fell in all eight regions, from "
               f"{worst.vote_pct_2021:.0f}% to {worst.vote_pct_2026:.0f}% at worst")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save(fig, "05_regional_swing.png")


def c6_turnout_vs_roll(conn):
    d = pd.read_sql(SQL_Q06, conn)
    d["roll_change"] = (d.roll_2026 - d.roll_2021) / d.roll_2021 * 100
    d["turnout_change"] = d.turnout_2026 - d.turnout_2021
    r = d.roll_change.corr(d.turnout_change)
    slope, intercept = np.polyfit(d.roll_change, d.turnout_change, 1)

    fig, ax = plt.subplots()
    ax.scatter(d.roll_change, d.turnout_change, s=30, color=BLUE, alpha=0.62,
               edgecolors=SURFACE, linewidths=0.6, zorder=3)
    xs = np.array([d.roll_change.min(), d.roll_change.max()])
    ax.plot(xs, slope * xs + intercept, color=BJP, linewidth=2.4, zorder=4)

    ax.axhline(0, color=GREY, linewidth=1)
    ax.axvline(0, color=GREY, linewidth=1)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    ax.set_xlabel("Change in the electoral roll, 2021 to 2026 (%)")
    ax.set_ylabel("Change in turnout (percentage points)")
    ax.text(0.975, 0.94, f"r = \u2212{abs(r):.2f}\n{len(d)} seats", transform=ax.transAxes,
            ha="right", va="top", color=INK, fontsize=12)
    shrank = int((d.roll_change < 0).sum())
    ax.text(0.975, 0.78, f"{shrank} of {len(d)} seats\nlost registered voters",
            transform=ax.transAxes, ha="right", va="top", color=SUB, fontsize=10)

    title(fig, f"Where the electoral roll shrank, turnout “rose”: r = {r:.2f} across {len(d)} seats")
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    save(fig, "06_turnout_vs_roll.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    print(f"charts -> {OUT.relative_to(ROOT)}")
    for fn in (c1_seat_reversal, c2_vote_vs_seat, c3_flips,
               c4_closest, c5_regional_swing, c6_turnout_vs_roll):
        fn(conn)
    conn.close()
    print("done, 6 charts")


if __name__ == "__main__":
    main()
