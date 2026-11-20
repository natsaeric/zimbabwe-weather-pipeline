/* ============================================================
   Zimbabwe Weather Pipeline - database setup
   Run once in SSMS against server EricNatsa.
   ============================================================ */
USE master;
GO
SET NOCOUNT ON;
GO

IF DB_ID('WeatherDB') IS NULL
    CREATE DATABASE WeatherDB;
GO

USE WeatherDB;
GO
SET NOCOUNT ON;
GO

/* ------------------------------------------------------------
   Final table: one row per city per hour (kept permanently).
   The primary key lets the pipeline re-run safely (upsert).
   ------------------------------------------------------------ */
IF OBJECT_ID('dbo.WeatherHourly', 'U') IS NULL
BEGIN
    CREATE TABLE dbo.WeatherHourly
    (
        City         NVARCHAR(50)  NOT NULL,
        ObsTime      DATETIME2(0)  NOT NULL,   -- local Zimbabwe time
        TempC        DECIMAL(5,2)  NULL,
        HumidityPct  DECIMAL(5,2)  NULL,
        PrecipMm     DECIMAL(6,2)  NULL,
        WindKmh      DECIMAL(6,2)  NULL,
        WeatherCode  INT           NULL,       -- WMO weather code
        LoadedAt     DATETIME2(0)  NOT NULL CONSTRAINT DF_WeatherHourly_LoadedAt DEFAULT SYSUTCDATETIME(),
        CONSTRAINT PK_WeatherHourly PRIMARY KEY (City, ObsTime)
    );
END
GO

/* ------------------------------------------------------------
   Stage table: wiped and refilled on every run.
   ------------------------------------------------------------ */
IF OBJECT_ID('dbo.WeatherHourly_Stage', 'U') IS NOT NULL
    DROP TABLE dbo.WeatherHourly_Stage;
GO

CREATE TABLE dbo.WeatherHourly_Stage
(
    City         NVARCHAR(50)  NOT NULL,
    ObsTime      DATETIME2(0)  NOT NULL,
    TempC        DECIMAL(5,2)  NULL,
    HumidityPct  DECIMAL(5,2)  NULL,
    PrecipMm     DECIMAL(6,2)  NULL,
    WindKmh      DECIMAL(6,2)  NULL,
    WeatherCode  INT           NULL
);
GO

/* ------------------------------------------------------------
   Reporting view for Power BI: one row per city per day.
   ------------------------------------------------------------ */
IF OBJECT_ID('dbo.vw_DailyWeather', 'V') IS NOT NULL
    DROP VIEW dbo.vw_DailyWeather;
GO

CREATE VIEW dbo.vw_DailyWeather
AS
WITH DailyAgg AS
(
    -- Collapse hourly readings into one summary row per city per day
    SELECT
        City,
        ObsDate      = CAST(ObsTime AS DATE),
        AvgTempC     = AVG(TempC),
        MinTempC     = MIN(TempC),
        MaxTempC     = MAX(TempC),
        AvgHumidity  = AVG(HumidityPct),
        TotalRainMm  = SUM(PrecipMm),
        MaxWindKmh   = MAX(WindKmh),
        Readings     = COUNT(*)
    FROM dbo.WeatherHourly
    GROUP BY City, CAST(ObsTime AS DATE)
)
SELECT
    City,
    ObsDate,
    AvgTempC     = CAST(AvgTempC    AS DECIMAL(5,2)),
    MinTempC,
    MaxTempC,
    AvgHumidity  = CAST(AvgHumidity AS DECIMAL(5,2)),
    TotalRainMm,
    MaxWindKmh,
    Readings
FROM DailyAgg;
GO

PRINT 'WeatherDB setup complete.';
GO
