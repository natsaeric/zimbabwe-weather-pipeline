"""
Zimbabwe weather pipeline
Open-Meteo API -> dbo.WeatherHourly_Stage -> MERGE into dbo.WeatherHourly (SQL Server)
Fetches yesterday + today (hourly) for several Zimbabwean cities in one API call.
"""
import logging
import os
from datetime import datetime

import pyodbc
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    filename=os.path.join(HERE, "pipeline.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

CITIES = {
    "Harare":         (-17.8292, 31.0522),
    "Bulawayo":       (-20.1325, 28.6265),
    "Mutare":         (-18.9707, 32.6709),
    "Gweru":          (-19.4500, 29.8167),
    "Masvingo":       (-20.0744, 30.8328),
    "Kwekwe":         (-18.9281, 29.8149),
    "Victoria Falls": (-17.9243, 25.8572),
    "Kariba":         (-16.5167, 28.8000),
}

API_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,weather_code"

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=EricNatsa;DATABASE=WeatherDB;Trusted_Connection=yes;"
)

MERGE_SQL = """
MERGE dbo.WeatherHourly AS tgt
USING dbo.WeatherHourly_Stage AS src
    ON tgt.City = src.City AND tgt.ObsTime = src.ObsTime
WHEN MATCHED THEN UPDATE SET
    tgt.TempC       = src.TempC,
    tgt.HumidityPct = src.HumidityPct,
    tgt.PrecipMm    = src.PrecipMm,
    tgt.WindKmh     = src.WindKmh,
    tgt.WeatherCode = src.WeatherCode,
    tgt.LoadedAt    = SYSUTCDATETIME()
WHEN NOT MATCHED BY TARGET THEN
    INSERT (City, ObsTime, TempC, HumidityPct, PrecipMm, WindKmh, WeatherCode)
    VALUES (src.City, src.ObsTime, src.TempC, src.HumidityPct, src.PrecipMm, src.WindKmh, src.WeatherCode);
"""


def fetch_rows():
    names = list(CITIES)
    params = {
        "latitude": ",".join(str(CITIES[n][0]) for n in names),
        "longitude": ",".join(str(CITIES[n][1]) for n in names),
        "hourly": HOURLY_VARS,
        "timezone": "Africa/Harare",
        "past_days": 1,
        "forecast_days": 1,
    }
    resp = requests.get(API_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):  # single location returns a dict, multiple a list
        data = [data]

    rows = []
    for name, loc in zip(names, data):
        h = loc["hourly"]
        for i, t in enumerate(h["time"]):
            rows.append((
                name,
                datetime.fromisoformat(t),
                h["temperature_2m"][i],
                h["relative_humidity_2m"][i],
                h["precipitation"][i],
                h["wind_speed_10m"][i],
                h["weather_code"][i],
            ))
    return rows


def load(rows):
    with pyodbc.connect(CONN_STR) as conn:
        cur = conn.cursor()
        cur.fast_executemany = True
        cur.execute("TRUNCATE TABLE dbo.WeatherHourly_Stage;")
        cur.executemany(
            "INSERT INTO dbo.WeatherHourly_Stage "
            "(City, ObsTime, TempC, HumidityPct, PrecipMm, WindKmh, WeatherCode) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        cur.execute(MERGE_SQL)
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM dbo.WeatherHourly;").fetchone()[0]
    return total


def main():
    try:
        rows = fetch_rows()
        logging.info("Fetched %d rows", len(rows))
        total = load(rows)
        logging.info("Merge complete. WeatherHourly now has %d rows", total)
        print(f"OK: fetched {len(rows)} rows, table total {total}")
    except Exception:
        logging.exception("Pipeline failed")
        raise


if __name__ == "__main__":
    main()
