"""Forecast from the National Weather Service API (free, no key) for the home location in .env."""
import json
import urllib.request

from common import HOME_LATITUDE, HOME_LONGITUDE

# api.weather.gov asks every caller to identify itself.
HEADERS = {"User-Agent": "Low-vision Mac assistant (local, personal use)",
           "Accept": "application/geo+json"}


def get_json(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def forecast(periods=4, latitude=None, longitude=None):
    latitude = float(latitude if latitude is not None else HOME_LATITUDE or "nan")
    longitude = float(longitude if longitude is not None else HOME_LONGITUDE or "nan")
    if latitude != latitude or longitude != longitude:  # NaN: not set.
        raise ValueError("Set BRAIN_HOME_LATITUDE and BRAIN_HOME_LONGITUDE in .env.")
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
