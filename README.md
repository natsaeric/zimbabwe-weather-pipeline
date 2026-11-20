# Zimbabwe Weather Pipeline

![Zimbabwe Weather Monitor dashboard](Zimbabwe%20Weather%20Dashboard.png)

An end-to-end data pipeline that collects hourly weather data for eight Zimbabwean cities, stores it in SQL Server, and reports it in a Power BI dashboard.

**Pipeline:** Open-Meteo API → Python → SQL Server (stage table + MERGE) → Power BI

## Cities
Harare, Bulawayo, Mutare, Gweru, Masvingo, Kwekwe, Victoria Falls, Kariba

## Data
Hourly readings for each city: temperature (°C), relative humidity (%), precipitation (mm), wind speed (km/h) and WMO weather code.

Weather data by [Open-Meteo.com](https://open-meteo.com) (CC BY 4.0). Values are model-based, not readings from a physical station in each city.

## How it works
1. `weather_pipeline.py` makes one API call for all eight cities, covering yesterday and today (48 hours each, 384 rows).
2. Rows are loaded into `dbo.WeatherHourly_Stage`.
3. A `MERGE` upserts them into `dbo.WeatherHourly` (primary key: city + hour), so re-running never creates duplicates and forecast hours are overwritten with better values on later runs.
4. `dbo.vw_DailyWeather` summarises each city per day for reporting.
5. A Windows Task Scheduler job runs the script daily at 08:50. Each run is logged to `pipeline.log`.

## Setup
1. Run `1_setup_weatherdb.sql` in SSMS to create `WeatherDB`, the tables and the view.
2. Install dependencies: `pip install requests pyodbc`
3. Edit `CONN_STR` in `weather_pipeline.py` if your SQL Server name differs from `EricNatsa`.
4. Run `python weather_pipeline.py`.
5. Schedule it (Anaconda Prompt):
   ```
   schtasks /Create /TN "WeatherPipeline" /SC DAILY /ST 08:50 /F /TR "\"%CONDA_PREFIX%\python.exe\" \"C:\path\to\weather_pipeline.py\""
   ```
6. Open `ZimbabweWeatherMonitor.pbix` in Power BI Desktop and click **Refresh**.

## Dashboard
City slicer, summary cards (average and maximum temperature, total rainfall, average humidity), hourly temperature by city, average temperature by city and total rainfall by city.

## Tech
Python (requests, pyodbc), SQL Server, Power BI, Windows Task Scheduler
