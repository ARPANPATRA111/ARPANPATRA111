#!/usr/bin/env python3
"""Fetch WakaTime stats for the profile README.

WakaTime retired API-key authentication for non-plugin endpoints on 2026-11-01:

    API keys are write-only and should only be used in WakaTime plugins to send
    coding activity. For all other use cases, including apps, scripts, and
    integrations, use OAuth 2.0 access tokens.

https://wakatime.com/developers#authentication

So this script authenticates with an OAuth token created at
https://wakatime.com/oauth. The token is sent as `Authorization: Bearer <token>`
and, if that is rejected, as the documented `api_key` query parameter.

Output is wakatime_stats.json, consumed by scripts/generate_assets.py.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import pytz
import requests


# ============================================================
# CONFIGURATION
# ============================================================

API_BASE = os.environ.get("WAKATIME_API_BASE", "https://wakatime.com/api/v1").rstrip("/")
SUMMARIES_URL = f"{API_BASE}/users/current/summaries"
DURATIONS_URL = f"{API_BASE}/users/current/durations"

TOKEN_URL = "https://wakatime.com/oauth"
AUTH_DOCS_URL = "https://wakatime.com/developers#authentication"

LOCAL_TIMEZONE = "Asia/Kolkata"
OUTPUT_FILE = "wakatime_stats.json"

# WakaTime answers 202 while it recomputes stats for a range. Retry briefly
# instead of treating that as "no data" (a 202 on first use of a new token is
# normal and previously wiped README stats in other projects).
ACCEPTED_RETRIES = 3
ACCEPTED_BACKOFF_SECONDS = 2


class WakaTimeError(RuntimeError):
    """A WakaTime request failed in a way we cannot recover from."""


# The preview printed below contains emoji; don't crash on a non-UTF-8 console.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


# ============================================================
# HTTP
# ============================================================

def request_json(session, url, token, params):
    """GET a WakaTime endpoint with an OAuth access token.

    The docs allow two auth forms for OAuth tokens, and support for them varies
    by account, so try both: a Bearer header, then the `api_key` query argument
    (which the docs explicitly say to keep using with an OAuth token in place of
    an API key).
    """
    last_error = None

    for strategy in ("bearer", "api_key"):
        query = dict(params)
        headers = {"Accept": "application/json"}
        if strategy == "bearer":
            headers["Authorization"] = f"Bearer {token}"
        else:
            query["api_key"] = token

        for attempt in range(ACCEPTED_RETRIES + 1):
            try:
                resp = session.get(url, params=query, headers=headers, timeout=30)
            except requests.RequestException as exc:
                raise WakaTimeError(f"Could not reach {url}: {exc}") from exc

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 202:
                last_error = "202 Accepted (WakaTime is still computing stats)"
                time.sleep(ACCEPTED_BACKOFF_SECONDS * (attempt + 1))
                continue

            last_error = f"{resp.status_code} {resp.text.strip()[:300]}"
            break

    raise WakaTimeError(
        f"WakaTime rejected the request to {url}\n"
        f"Last response: {last_error}\n\n"
        "Since 2026-11-01, WakaTime API keys only work inside plugins; all other "
        "endpoints require an OAuth access token.\n"
        f"  1. Create a token at {TOKEN_URL}\n"
        "  2. Store it as the WAKATIME_OAUTH_TOKEN repo secret\n"
        "     (the legacy WAKATIME_API_KEY secret name still works)\n"
        f"Docs: {AUTH_DOCS_URL}"
    )


def fetch_summaries(session, token, start, end):
    """Return the daily summaries for [start, end] (YYYY-MM-DD strings)."""
    payload = request_json(
        session, SUMMARIES_URL, token, {"start": start, "end": end}
    )
    data = payload.get("data")
    if not isinstance(data, list):
        raise WakaTimeError(f"Unexpected summaries payload: {str(payload)[:300]}")
    return data


def fetch_first_activity(session, token, date_str, tz):
    """Earliest heartbeat time for a day, or None if it cannot be determined.

    Best-effort: a missing scope or an error here must not fail the whole run,
    since the rest of the stats are still valid.
    """
    try:
        payload = request_json(session, DURATIONS_URL, token, {"date": date_str})
        timestamps = [
            float(d["time"]) for d in payload.get("data", []) if d.get("time")
        ]
    except (WakaTimeError, TypeError, ValueError) as exc:
        print(f"⚠️  Wake-up time unavailable: {exc}")
        return None

    if not timestamps:
        return None
    return datetime.fromtimestamp(min(timestamps), timezone.utc).astimezone(tz)


# ============================================================
# AGGREGATION
# ============================================================

def calculate_total_seconds(data_list):
    return sum(day.get("grand_total", {}).get("total_seconds", 0) for day in data_list)


def format_time(seconds):
    if seconds == 0:
        return "0 hrs 0 mins"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours} hrs {minutes} mins"


def build_stats(data_last7, data_last14, wake_up_time):
    """Assemble the wakatime_stats.json payload from raw summaries."""
    this_week_seconds = calculate_total_seconds(data_last7)
    this_week_formatted = format_time(this_week_seconds)

    # The API returns days in chronological order, so the 14-day response is
    # [last week][this week]; days 1-7 are last week.
    last_week_data = data_last14[:7] if len(data_last14) >= 14 else []
    last_week_seconds = calculate_total_seconds(last_week_data)
    last_week_formatted = format_time(last_week_seconds)

    if last_week_seconds > 0:
        change_percent = ((this_week_seconds - last_week_seconds) / last_week_seconds) * 100
        change_indicator = "📈" if change_percent > 0 else "📉" if change_percent < 0 else "➡️"
        change_text = f"{change_indicator} {abs(change_percent):.1f}%"
    else:
        change_text = "🆕 New"

    daily_hours = []
    daily_labels = []
    for day in data_last7:
        date = day.get("range", {}).get("date", "")
        total_secs = day.get("grand_total", {}).get("total_seconds", 0)
        daily_hours.append(round(total_secs / 3600, 2))
        if date:
            daily_labels.append(datetime.strptime(date, "%Y-%m-%d").strftime("%a"))
        else:
            daily_labels.append("N/A")

    today_summary = data_last7[-1] if data_last7 else {}

    if data_last7:
        most_productive_day = max(
            data_last7, key=lambda x: x.get("grand_total", {}).get("total_seconds", 0)
        )
        most_productive_date = most_productive_day.get("range", {}).get("date", "")
        most_productive_hours = round(
            most_productive_day.get("grand_total", {}).get("total_seconds", 0) / 3600, 2
        )
        most_productive_day_name = (
            datetime.strptime(most_productive_date, "%Y-%m-%d").strftime("%A")
            if most_productive_date
            else "N/A"
        )
    else:
        most_productive_day_name = "N/A"
        most_productive_hours = 0

    languages = {}
    editors = {}
    for day in data_last7:
        for lang in day.get("languages", []):
            name = lang.get("name", "Unknown")
            languages[name] = languages.get(name, 0) + lang.get("total_seconds", 0)
        for editor in day.get("editors", []):
            name = editor.get("name", "Unknown")
            editors[name] = editors.get(name, 0) + editor.get("total_seconds", 0)

    top_language = max(languages.items(), key=lambda x: x[1])[0] if languages else "N/A"
    top_editor = max(editors.items(), key=lambda x: x[1])[0] if editors else "N/A"

    today_data = data_last7[-1] if len(data_last7) >= 1 else {}
    yesterday_data = data_last7[-2] if len(data_last7) >= 2 else {}
    today_formatted = format_time(today_data.get("grand_total", {}).get("total_seconds", 0))
    yesterday_formatted = format_time(
        yesterday_data.get("grand_total", {}).get("total_seconds", 0)
    )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "wake_up_time": wake_up_time.strftime("%H:%M:%S") if wake_up_time else "N/A",
        "summary_days": len(data_last7),
        "latest_day": today_summary.get("range", {}).get("date", ""),
        "total_coding_time": today_summary.get("grand_total", {}).get("text", "0 mins"),
        "today_total": today_formatted,
        "yesterday_total": yesterday_formatted,
        "this_week_total": this_week_formatted,
        "last_week_total": last_week_formatted,
        "week_change": change_text,
        "daily_hours": daily_hours,
        "daily_labels": daily_labels,
        "most_productive_day": most_productive_day_name,
        "most_productive_hours": most_productive_hours,
        "top_language": top_language,
        "top_editor": top_editor,
        "raw_data": data_last7,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    token = (
        os.environ.get("WAKATIME_OAUTH_TOKEN")
        or os.environ.get("WAKATIME_API_KEY")
        or ""
    ).strip()
    if not token:
        raise SystemExit(
            "No WakaTime credential found. Set the WAKATIME_OAUTH_TOKEN secret to "
            f"an OAuth token from {TOKEN_URL}."
        )

    session = requests.Session()
    tz = pytz.timezone(LOCAL_TIMEZONE)

    today_utc = datetime.now(timezone.utc).date()
    start_7 = (today_utc - timedelta(days=6)).strftime("%Y-%m-%d")
    end_7 = today_utc.strftime("%Y-%m-%d")
    start_14 = (today_utc - timedelta(days=13)).strftime("%Y-%m-%d")

    data_last7 = fetch_summaries(session, token, start_7, end_7)
    if not data_last7:
        raise SystemExit(
            "WakaTime returned no summary data for the last 7 days; leaving "
            "wakatime_stats.json untouched."
        )

    data_last14 = fetch_summaries(session, token, start_14, end_7)
    if len(data_last14) < 7:
        print("⚠️  Incomplete 14-day history; last-week comparison may be short.")

    latest_date = data_last7[-1].get("range", {}).get("date", "")
    wake_up_time = fetch_first_activity(session, token, latest_date, tz) if latest_date else None

    stats = build_stats(data_last7, data_last14, wake_up_time)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Today: {stats['today_total']}")
    print(f"Yesterday: {stats['yesterday_total']}")
    print(f"This Week: {stats['this_week_total']}")
    print(f"Last Week: {stats['last_week_total']}")
    print(f"Change: {stats['week_change']}")
    print(
        f"Most Productive: {stats['most_productive_day']} "
        f"({stats['most_productive_hours']} hrs)"
    )
    print(f"Wake-up: {stats['wake_up_time']}")


if __name__ == "__main__":
    try:
        main()
    except WakaTimeError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        sys.exit(1)
