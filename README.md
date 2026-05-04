# readJiraCsv_q2_26.py

Generate side-by-side pie charts comparing actual time logged in JIRA
against planned quarterly allocations.

## Usage

    python3 readJiraCsv_q2_26.py q2_26.csv
    python3 readJiraCsv_q2_26.py q2_26.csv -o custom.png

The default output PNG matches the CSV name (`q2_26.csv` → `q2_26.png`).

## Input

A JIRA issue export (CSV) with at least these columns:

  - `Labels`        — used to bucket each ticket
  - `Updated`       — earliest value becomes the quarter start date
  - `Σ Time Spent`  — seconds logged per ticket; rows without a value
                      are skipped

Add this field in JIRA's export options if it isn't there by default.

## Output

A two-pie figure:

  - **Left pie**: hours logged per `Labels` value, summed from the CSV.
    Each slice is annotated with its percentage; the outer label shows
    the label name and total hours (`radar (31.08h)`).
  - **Right pie**: planned percent allocations, with each slice's
    "expected hours so far" given the elapsed fraction of the quarter.

Quarter is defined as: earliest `Updated` date in the CSV +
3 calendar months, with `HOURS_PER_DAY` hours per Mon–Fri workday.

## Configuration

Edit two things at the top of `plot_pies` / the module:

  - `HOURS_PER_DAY` (module-level constant) — workday length in hours.
    6h = 9-3, 7h = 9-4, 8h = 9-5.
  - `allocations` dict (in `plot_pies`) — your planned percent split.
    Names are matched to CSV labels case-insensitively, ignoring
    spaces / underscores / `+`, so `operations` ↔ `Operations` and
    `20m_RH8` ↔ `20m + RH8` share a color across both pies.

## Dependencies

`matplotlib` only. The script forces the `Agg` backend and saves to
PNG (no GUI window) for fast headless runs (~0.8s end-to-end).
