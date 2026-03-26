#!/usr/bin/env python3
"""
Bangalore Weather Scraper
=========================
Scrapes current weather data for Bangalore (temperature & rainfall probability)
from wttr.in, prints it to console, writes it to bangalore_weather.md,
and commits + pushes the update to the GitHub repository.

Usage:
    python3 scrape_bangalore_weather.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CITY = "Bangalore"
WTTR_URL = f"https://wttr.in/{CITY}?format=j1"
MD_FILE = "bangalore_weather.md"
IST = timezone(timedelta(hours=5, minutes=30))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_weather() -> dict:
    """Fetch weather JSON from wttr.in for Bangalore."""
    print(f"[INFO] Fetching weather data from {WTTR_URL} ...")
    resp = requests.get(WTTR_URL, timeout=30, headers={"User-Agent": "curl/7.68.0"})
    resp.raise_for_status()
    return resp.json()


def parse_weather(data: dict) -> dict:
    """Extract the fields we care about from the raw JSON."""
    current = data["current_condition"][0]
    today_forecast = data["weather"][0]

    # Hourly breakdown for rain probability
    hourly_rain = []
    for h in today_forecast.get("hourly", []):
        hour_val = int(h["time"]) // 100  # "600" -> 6, "1200" -> 12
        hourly_rain.append({
            "hour": f"{hour_val:02d}:00",
            "temp_c": h["tempC"],
            "rain_chance": h["chanceofrain"],
            "description": h["weatherDesc"][0]["value"].strip(),
        })

    return {
        "city": CITY,
        "observation_time": current.get("localObsDateTime", "N/A"),
        "temp_c": current["temp_C"],
        "feels_like_c": current["FeelsLikeC"],
        "humidity": current["humidity"],
        "weather_desc": current["weatherDesc"][0]["value"].strip(),
        "wind_kmph": current["windspeedKmph"],
        "precip_mm": current["precipMM"],
        "uv_index": current["uvIndex"],
        "min_temp_c": today_forecast["mintempC"],
        "max_temp_c": today_forecast["maxtempC"],
        "hourly": hourly_rain,
    }


def print_weather(w: dict) -> None:
    """Pretty-print weather data to console."""
    print("\n" + "=" * 55)
    print(f"  🌤  Weather Report for {w['city']}")
    print("=" * 55)
    print(f"  Observed at      : {w['observation_time']}")
    print(f"  Condition        : {w['weather_desc']}")
    print(f"  Temperature      : {w['temp_c']}°C  (feels like {w['feels_like_c']}°C)")
    print(f"  Min / Max today  : {w['min_temp_c']}°C / {w['max_temp_c']}°C")
    print(f"  Humidity         : {w['humidity']}%")
    print(f"  Wind             : {w['wind_kmph']} km/h")
    print(f"  Precipitation    : {w['precip_mm']} mm")
    print(f"  UV Index         : {w['uv_index']}")
    print("-" * 55)
    print("  Hourly Forecast (Temperature & Rain Probability):")
    print(f"  {'Hour':<8} {'Temp':>6} {'Rain%':>7}  {'Condition'}")
    print(f"  {'----':<8} {'----':>6} {'-----':>7}  {'---------'}")
    for h in w["hourly"]:
        print(f"  {h['hour']:<8} {h['temp_c']:>5}°C {h['rain_chance']:>6}%  {h['description']}")
    print("=" * 55 + "\n")


def write_markdown(w: dict, filepath: str) -> None:
    """Write weather data to a markdown file."""
    now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

    lines = [
        f"# 🌤 Bangalore Weather Report",
        "",
        f"> **Last updated:** {now_ist}",
        "",
        "---",
        "",
        "## Current Conditions",
        "",
        f"| Parameter | Value |",
        f"|-----------|-------|",
        f"| **Condition** | {w['weather_desc']} |",
        f"| **Temperature** | {w['temp_c']}°C (feels like {w['feels_like_c']}°C) |",
        f"| **Min / Max** | {w['min_temp_c']}°C / {w['max_temp_c']}°C |",
        f"| **Humidity** | {w['humidity']}% |",
        f"| **Wind Speed** | {w['wind_kmph']} km/h |",
        f"| **Precipitation** | {w['precip_mm']} mm |",
        f"| **UV Index** | {w['uv_index']} |",
        "",
        "---",
        "",
        "## Hourly Forecast",
        "",
        "| Hour | Temperature | Rain Probability | Condition |",
        "|------|-------------|------------------|-----------|",
    ]

    for h in w["hourly"]:
        lines.append(
            f"| {h['hour']} | {h['temp_c']}°C | {h['rain_chance']}% | {h['description']} |"
        )

    lines += [
        "",
        "---",
        "",
        f"*Data sourced from [wttr.in](https://wttr.in/{CITY})*",
        "",
    ]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[INFO] Weather data written to {filepath}")


def git_commit_and_push(filepath: str) -> None:
    """Stage, commit, and push the markdown file to the repository."""
    repo_dir = os.path.dirname(os.path.abspath(filepath)) or "."
    now_ist = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    commit_msg = f"Update Bangalore weather report – {now_ist}"

    def run(cmd):
        print(f"[GIT] {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[GIT:STDERR] {result.stderr.strip()}")
        if result.stdout.strip():
            print(f"[GIT:STDOUT] {result.stdout.strip()}")
        return result.returncode

    run(["git", "add", os.path.basename(filepath)])
    # Check if there are changes to commit
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo_dir, capture_output=True
    )
    if result.returncode == 0:
        print("[INFO] No changes to commit (file unchanged).")
        return

    run(["git", "commit", "-m", commit_msg])
    ret = run(["git", "push"])
    if ret == 0:
        print("[INFO] Successfully pushed to remote repository.")
    else:
        print("[ERROR] Push failed. You may need to configure credentials or push manually.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    try:
        raw_data = fetch_weather()
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch weather data: {e}", file=sys.stderr)
        sys.exit(1)

    weather = parse_weather(raw_data)

    # 1. Print to console
    print_weather(weather)

    # 2. Write markdown file (in same directory as this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(script_dir, MD_FILE)
    write_markdown(weather, md_path)

    # 3. Commit & push
    git_commit_and_push(md_path)


if __name__ == "__main__":
    main()
