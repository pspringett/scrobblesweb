from __future__ import annotations

import json
import os
from collections import Counter
from typing import Optional

from flask import Flask, render_template, jsonify
from flask.wrappers import Response

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
RELEASES_PATH = os.path.join(DATA_DIR, "releases.txt")

Scrobble = dict[str, str]
AlbumEntry = dict[str, object]


def _load_releases() -> dict[str, dict[str, int]]:
    """Load releases.txt, returning {artist: {album: year}}."""
    if not os.path.exists(RELEASES_PATH):
        return {}
    with open(RELEASES_PATH, encoding="utf-8") as f:
        return json.load(f)


# Loaded once at startup
RELEASES: dict[str, dict[str, int]] = _load_releases()


def get_available_months() -> list[tuple[int, int]]:
    """Return sorted list of (year, month) tuples that have data files."""
    months: list[tuple[int, int]] = []
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


def get_available_years() -> list[int]:
    """Return sorted list of years that have at least one data file."""
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(
        int(y) for y in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, y)) and y.isdigit()
    )


def load_month_data(year: int, month: int) -> Optional[list[Scrobble]]:
    """Load and return scrobbles for a given year/month."""
    path = os.path.join(DATA_DIR, str(year), f"{year}-{month:02d}-tracks.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _album_key(scrobble: Scrobble) -> str:
    artist = scrobble.get("artist", "Unknown Artist")
    album = scrobble.get("album", "Unknown Album")
    return f"{artist} \u2014 {album}"


def _split_label(label: str) -> tuple[str, str]:
    """Split 'Artist — Album' label into (artist, album)."""
    parts = label.split(" \u2014 ", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else (label, "")


@app.route("/")
def index() -> Response | tuple[str, int]:
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
def api_albums(year: int, month: int) -> tuple[Response, int] | Response:
    scrobbles = load_month_data(year, month)
    if scrobbles is None:
        return jsonify({"error": "No data for this month"}), 404

    counts: Counter[str] = Counter()
    for s in scrobbles:
        counts[_album_key(s)] += 1

    albums: list[AlbumEntry] = [
        {"label": label, "count": count} for label, count in counts.most_common()
    ]
    return jsonify({"year": year, "month": month, "albums": albums})


@app.route("/api/albums/<int:year>")
def api_albums_year(year: int) -> tuple[Response, int] | Response:
    months = get_available_months()
    year_months = [m for y, m in months if y == year]
    if not year_months:
        return jsonify({"error": "No data for this year"}), 404

    counts: Counter[str] = Counter()
    for month in year_months:
        scrobbles = load_month_data(year, month)
        if scrobbles:
            for s in scrobbles:
                counts[_album_key(s)] += 1

    albums: list[AlbumEntry] = [
        {"label": label, "count": count} for label, count in counts.most_common()
    ]
    return jsonify({"year": year, "albums": albums})


def aggregate_albums(from_year: Optional[int] = None) -> list[AlbumEntry]:
    """Aggregate album play counts across all months, optionally filtering by from_year."""
    counts: Counter[str] = Counter()
    for year, month in get_available_months():
        if from_year is not None and year < from_year:
            continue
        scrobbles = load_month_data(year, month)
        if scrobbles:
            for s in scrobbles:
                counts[_album_key(s)] += 1

    entries: list[AlbumEntry] = []
    for label, count in counts.most_common():
        artist, album = _split_label(label)
        entries.append({
            "label": label,
            "artist": artist,
            "album": album,
            "count": count,
            "has_releases": artist in RELEASES,
        })
    return entries


def _rolling12_counts(year: int, month: int) -> Counter[str]:
    """Return a Counter of album play counts for the 12 months ending at year/month."""
    counts: Counter[str] = Counter()
    for i in range(12):
        m = month - i
        y = year
        while m < 1:
            m += 12
            y -= 1
        scrobbles = load_month_data(y, m)
        if scrobbles:
            for s in scrobbles:
                counts[_album_key(s)] += 1
    return counts


@app.route("/api/albums/rolling12/<int:year>/<int:month>")
def api_albums_rolling12(year: int, month: int) -> Response:
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

    prev_ranks: dict[str, int] = {
        label: rank for rank, (label, _) in enumerate(prev.most_common(), 1)
    }

    albums: list[AlbumEntry] = []
    for rank, (label, count) in enumerate(current.most_common(), 1):
        prev_rank = prev_ranks.get(label)
        rank_change: Optional[int] = (prev_rank - rank) if prev_rank is not None else None
        albums.append({"label": label, "count": count, "rank_change": rank_change})

    return jsonify({"year": year, "month": month, "albums": albums})


@app.route("/api/albums/all")
def api_albums_all() -> Response:
    return jsonify({"albums": aggregate_albums()})


@app.route("/api/albums/since/<int:from_year>")
def api_albums_since(from_year: int) -> Response:
    return jsonify({"from_year": from_year, "albums": aggregate_albums(from_year=from_year)})


@app.route("/api/artist/<path:artist>")
def api_artist(artist: str) -> tuple[Response, int] | Response:
    """Return discography for an artist from releases.txt, sorted by year."""
    discography = RELEASES.get(artist)
    if discography is None:
        return jsonify({"error": "Artist not found"}), 404

    albums: list[dict[str, object]] = sorted(
        [{"album": album, "year": year} for album, year in discography.items()],
        key=lambda x: (x["year"] == -1, x["year"]),  # unknowns last
    )
    return jsonify({"artist": artist, "albums": albums})


if __name__ == "__main__":
    app.run(debug=True)
