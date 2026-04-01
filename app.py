import json
import os
from collections import Counter
from flask import Flask, render_template, jsonify

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def get_available_months():
    """Return sorted list of (year, month) tuples that have data files."""
    months = []
    if not os.path.isdir(DATA_DIR):
        return months
    for year in sorted(os.listdir(DATA_DIR)):
        year_dir = os.path.join(DATA_DIR, year)
        if not os.path.isdir(year_dir):
            continue
        for filename in sorted(os.listdir(year_dir)):
            if filename.endswith("-tracks.json"):
                parts = filename.split("-")
                if len(parts) >= 2:
                    months.append((int(year), int(parts[1])))
    return months


def get_available_years():
    """Return sorted list of years that have at least one data file."""
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(
        int(y) for y in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, y)) and y.isdigit()
    )


def load_month_data(year, month):
    """Load and return scrobbles for a given year/month."""
    path = os.path.join(DATA_DIR, str(year), f"{year}-{month:02d}-tracks.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@app.route("/")
def index():
    available = get_available_months()
    if not available:
        return "No data found.", 404
    latest_year, latest_month = available[-1]
    return render_template(
        "index.html",
        available=available,
        available_years=get_available_years(),
        default_year=latest_year,
        default_month=latest_month,
    )


@app.route("/api/albums/<int:year>/<int:month>")
def api_albums(year, month):
    scrobbles = load_month_data(year, month)
    if scrobbles is None:
        return jsonify({"error": "No data for this month"}), 404

    # Count tracks per "Artist – Album"
    counts = Counter()
    for s in scrobbles:
        artist = s.get("artist", "Unknown Artist")
        album = s.get("album", "Unknown Album")
        key = f"{artist} — {album}"
        counts[key] += 1

    # Sort descending by play count
    albums = [{"label": label, "count": count} for label, count in counts.most_common()]
    return jsonify({"year": year, "month": month, "albums": albums})


@app.route("/api/albums/<int:year>")
def api_albums_year(year):
    months = get_available_months()
    year_months = [m for y, m in months if y == year]
    if not year_months:
        return jsonify({"error": "No data for this year"}), 404

    counts = Counter()
    for month in year_months:
        scrobbles = load_month_data(year, month)
        if scrobbles:
            for s in scrobbles:
                artist = s.get("artist", "Unknown Artist")
                album = s.get("album", "Unknown Album")
                counts[f"{artist} \u2014 {album}"] += 1

    albums = [{"label": label, "count": count} for label, count in counts.most_common()]
    return jsonify({"year": year, "albums": albums})


def aggregate_albums(from_year=None):
    """Aggregate album play counts across all months, optionally filtering by from_year."""
    counts = Counter()
    for year, month in get_available_months():
        if from_year is not None and year < from_year:
            continue
        scrobbles = load_month_data(year, month)
        if scrobbles:
            for s in scrobbles:
                artist = s.get("artist", "Unknown Artist")
                album = s.get("album", "Unknown Album")
                counts[f"{artist} \u2014 {album}"] += 1
    return [{"label": label, "count": count} for label, count in counts.most_common()]


def _rolling12_counts(year, month):
    """Return a Counter of album play counts for the 12 months ending at year/month."""
    counts = Counter()
    for i in range(12):
        m = month - i
        y = year
        while m < 1:
            m += 12
            y -= 1
        scrobbles = load_month_data(y, m)
        if scrobbles:
            for s in scrobbles:
                artist = s.get("artist", "Unknown Artist")
                album = s.get("album", "Unknown Album")
                counts[f"{artist} \u2014 {album}"] += 1
    return counts


@app.route("/api/albums/rolling12/<int:year>/<int:month>")
def api_albums_rolling12(year, month):
    """Aggregate the 12 months ending at (and including) the given year/month.
    Also computes previous window ranks for rank-change highlighting."""
    current = _rolling12_counts(year, month)

    # Previous window = rolling 12 ending one month before the current end
    prev_end_m = month - 1
    prev_end_y = year
    if prev_end_m < 1:
        prev_end_m = 12
        prev_end_y -= 1
    prev = _rolling12_counts(prev_end_y, prev_end_m)

    # Build rank lookup for previous window {label: rank (1-based)}
    prev_ranks = {label: rank for rank, (label, _) in enumerate(prev.most_common(), 1)}

    albums = []
    for rank, (label, count) in enumerate(current.most_common(), 1):
        prev_rank = prev_ranks.get(label)
        rank_change = (prev_rank - rank) if prev_rank is not None else None
        albums.append({"label": label, "count": count, "rank_change": rank_change})

    return jsonify({"year": year, "month": month, "albums": albums})


@app.route("/api/albums/all")
def api_albums_all():
    return jsonify({"albums": aggregate_albums()})


@app.route("/api/albums/since/<int:from_year>")
def api_albums_since(from_year):
    return jsonify({"from_year": from_year, "albums": aggregate_albums(from_year=from_year)})


if __name__ == "__main__":
    app.run(debug=True)
