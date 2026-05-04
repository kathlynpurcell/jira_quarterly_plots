# clause opus 4.7

import argparse
import csv
import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# Workday length in hours (e.g. 9-3 M-F = 6h/day, 9-4 M-F = 7h/day, 9-5 M-F = 8h/day).
# Change this single value to recompute the quarter and expected hours.
HOURS_PER_DAY = 8


def format_hours_as_work_time(hours, hours_per_day=None, days_per_week=5):
    """Pretty-print hours as 'Xw Yd Z.ZZh'."""
    if hours_per_day is None:
        hours_per_day = HOURS_PER_DAY
    if hours < 0:
        raise ValueError("hours must be non-negative")
    week_hours = hours_per_day * days_per_week
    weeks = int(hours // week_hours)
    remaining = hours - weeks * week_hours
    days = int(remaining // hours_per_day)
    remaining -= days * hours_per_day
    parts = []
    if weeks:
        parts.append(f"{weeks}w")
    if days:
        parts.append(f"{days}d")
    if remaining or not parts:
        parts.append(f"{remaining:.2f}h")
    return " ".join(parts)


def workday_hours_between(start, end, hours_per_day=None):
    """Count Mon-Fri workday hours between two dates, inclusive."""
    if hours_per_day is None:
        hours_per_day = HOURS_PER_DAY
    if start > end:
        return 0
    days = 0
    d = start
    while d <= end:
        if d.weekday() < 5:
            days += 1
        d += timedelta(days=1)
    return days * hours_per_day


def add_calendar_months(d, months):
    """Add N calendar months to a date, clamping the day if the target month is shorter."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    # Clamp day to the last day of the target month
    if month == 12:
        next_month_first = datetime(year + 1, 1, 1).date()
    else:
        next_month_first = datetime(year, month + 1, 1).date()
    last_day_of_month = (next_month_first - timedelta(days=1)).day
    day = min(d.day, last_day_of_month)
    return datetime(year, month, day).date()


def parse_jira_csv(fn):
    """Sum Σ Time Spent (seconds) per label.
    Returns (labels_in_seconds, earliest_updated_date)."""
    labels = {}
    earliest = None
    with open(fn) as f:
        reader = csv.reader(f)
        headers = next(reader)
        labels_idx = headers.index("Labels")
        updated_idx = headers.index("Updated")
        time_idx = next(i for i, h in enumerate(headers) if "Time Spent" in h)
        for row in reader:
            if not row:
                continue
            secs_str = row[time_idx].strip()
            if not secs_str:
                continue  # skip rows with no time logged
            secs = int(secs_str)
            label = row[labels_idx].strip() or "(no label)"
            labels[label] = labels.get(label, 0) + secs
            updated = datetime.strptime(row[updated_idx], "%d/%b/%y %I:%M %p").date()
            if earliest is None or updated < earliest:
                earliest = updated
    return labels, earliest


def plot_pies(labels_secs, report_date, today_date, out_path):
    # Left pie: hours spent per label
    sorted_labels = sorted(labels_secs.items(), key=lambda kv: kv[1], reverse=True)
    label_names = [name for name, _ in sorted_labels]
    label_hours = [secs / 3600.0 for _, secs in sorted_labels]
    total_hours = sum(label_hours)

    # Right pie: planned allocations (percent)
    allocations = {
        "admin": 10,
        "Operations": 20,
        "Vacation": 17,
        "radar": 6,
        "20m + RH8": 30,
        "python3": 20,
        "20m Contractor": 8,
    }
    alloc_names = list(allocations.keys())
    alloc_values = list(allocations.values())

    # Shared color mapping — match labels case-insensitively, ignoring spaces/_/+
    def norm(s):
        return s.lower().replace(" ", "").replace("_", "").replace("+", "")

    cmap = plt.get_cmap("tab20")
    key_to_color = {}
    for name in label_names + alloc_names:
        key = norm(name)
        if key not in key_to_color:
            key_to_color[key] = cmap(len(key_to_color) % 20)

    label_colors = [key_to_color[norm(n)] for n in label_names]
    alloc_colors = [key_to_color[norm(n)] for n in alloc_names]

    # Quarter runs from report_date for 3 calendar months.
    quarter_end = add_calendar_months(report_date, 3)
    quarter_total_hours = workday_hours_between(report_date, quarter_end)
    elapsed_end = min(today_date, quarter_end)
    elapsed_quarter_hours = workday_hours_between(report_date, elapsed_end)

    # Expected hours per allocation = (alloc% / 100) * elapsed quarter hours
    alloc_total_pct = sum(alloc_values) or 1  # guard div-by-zero; allocations may not sum to 100
    expected_hours = {
        name: (val / alloc_total_pct) * elapsed_quarter_hours
        for name, val in allocations.items()
    }

    # Outer labels: name + hours (left = actual logged, right = expected so far)
    label_pie_labels = [f"{n}\n({h:.2f}h)" for n, h in zip(label_names, label_hours)]
    alloc_pie_labels = [f"{n}\n({expected_hours[n]:.1f}h exp)" for n in alloc_names]

    def fmt_pct(pct):
        return f"{pct:.1f}%"

    fig, axes = plt.subplots(1, 2, figsize=(14, 8))
    axes[0].pie(
        label_hours,
        labels=label_pie_labels,
        colors=label_colors,
        autopct=fmt_pct,
        startangle=90,
        radius=0.9,
    )
    axes[0].set_title(
        f"JIRA Time by Label since {report_date.isoformat()} "
        f"(today: {today_date.isoformat()}, total: {total_hours:.2f}h)",
        pad=24,
    )
    axes[0].axis("equal")

    axes[1].pie(
        alloc_values,
        labels=alloc_pie_labels,
        colors=alloc_colors,
        autopct=fmt_pct,
        startangle=90,
        radius=0.9,
    )
    axes[1].set_title("Allocations (expected hrs so far)", pad=24)
    axes[1].axis("equal")

    elapsed = workday_hours_between(report_date, today_date)
    fig.text(
        0.5, 0.02,
        f"Total logged: {total_hours:.2f}h ({format_hours_as_work_time(total_hours)})    "
        f"Quarter: {report_date.isoformat()} → {quarter_end.isoformat()} "
        f"({elapsed_quarter_hours}h elapsed of {quarter_total_hours}h @ {HOURS_PER_DAY}h/day)",
        ha="center",
    )
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    print(f"Saved plot to {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("jira_csv")
    parser.add_argument("-o", "--out", default=None,
                        help="output PNG path (default: <csv_basename>.png)")
    args = parser.parse_args()

    out_path = args.out or (os.path.splitext(args.jira_csv)[0] + ".png")
    today = datetime.now().date()
    labels_secs, report_date = parse_jira_csv(args.jira_csv)

    total_hours = sum(labels_secs.values()) / 3600.0
    print(f"{'(label)':20s} {'(hrs)':>6s} {'(%)':>6s}  (work time)")
    for label, secs in sorted(labels_secs.items(), key=lambda kv: kv[1], reverse=True):
        hrs = secs / 3600.0
        pct = 100.0 * hrs / total_hours if total_hours else 0.0
        print(f"{label:20s} {hrs:6.2f} {pct:6.2f}  {format_hours_as_work_time(hrs)}")
    print(f"Total logged: {total_hours:.2f}h ({format_hours_as_work_time(total_hours)})")
    print(f"Report date / quarter start (earliest Updated in CSV): {report_date.isoformat()}")
    quarter_end = add_calendar_months(report_date, 3)
    quarter_total = workday_hours_between(report_date, quarter_end)
    elapsed_end = min(today, quarter_end)
    elapsed_q_hours = workday_hours_between(report_date, elapsed_end)
    print(f"Quarter end (start + 3 months): {quarter_end.isoformat()}")
    print(f"Quarter hours @ {HOURS_PER_DAY}h/day: {quarter_total}h total, {elapsed_q_hours}h elapsed")
    print(f"Today: {today.isoformat()}")

    plot_pies(labels_secs, report_date, today, out_path)


if __name__ == "__main__":
    main()
