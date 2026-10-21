"""Forecast from the National Weather Service API (free, no key). Defaults to Helena, MT."""
import json
import urllib.request

HELENA = (46.5891, -112.0391)
# api.weather.gov asks every caller to identify itself.
HEADERS = {"User-Agent": "Bruce accessibility assistant (local, personal use)",
           "Accept": "application/geo+json"}


def get_json(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def forecast(periods=4, latitude=HELENA[0], longitude=HELENA[1]):
    if not 1 <= periods <= 14:
        raise ValueError("periods must be 1–14 (each is a day or a night).")
    try:
        point = get_json(f"https://api.weather.gov/points/{latitude:.4f},{longitude:.4f}")
        where = point["properties"]["relativeLocation"]["properties"]
        data = get_json(point["properties"]["forecast"])
    except OSError as exc:
        raise RuntimeError(f"The weather service did not answer ({exc}).") from exc
    return {"place": f"{where['city']}, {where['state']}", "periods": [
        {"name": p["name"], "forecast": p["detailedForecast"]}
        for p in data["properties"]["periods"][:periods]]}
