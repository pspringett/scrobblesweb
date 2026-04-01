# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**scrobblesweb** is a personal music listening history viewer built with Python/Flask. It reads local JSON scrobble data and presents it as a web interface.

## Environment Setup

```bash
# Activate virtual environment (required before running anything)
source .venv/Scripts/activate   # Windows/Git Bash
# or
.venv\Scripts\activate          # Windows cmd/PowerShell

# Install dependencies (if requirements.txt exists)
pip install -r requirements.txt
```

## Running the App

```bash
flask run           # Standard start (uses app.py by default)
flask run --debug   # Development mode with auto-reload
```

## Data

Scrobble data lives in `data/<year>/<year>-<month>-tracks.json` (e.g., `data/2025/2025-01-tracks.json`). Coverage: January 2015 through present.

Each record:
```json
{
  "datetime": "2025-01-01 11:51:03",
  "artist": "Artist Name",
  "album": "Album Name",
  "track": "Track Name"
}
```

Each file is a JSON array of these objects, ordered chronologically. The `data/` directory is not committed to git.

## Architecture

This is a Flask application. Expect:
- `app.py` — Flask app factory and routes
- `templates/` — Jinja2 HTML templates
- `static/` — CSS/JS assets
- `data/` — Local JSON data files (gitignored, not served directly)

Data is loaded from JSON files at request time or cached in memory at startup. No database.

## Python Version

Python 3.9 (`.venv` was created with 3.9).
