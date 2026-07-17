import numpy as np
import pandas as pd
import pytest

from baram.features.weather_grid import (
  SPATIAL_STATISTICS,
  aggregate_weather_grid,
  build_weather_feature_pair,
  build_weather_features,
  fit_train_median_imputer,
)


METADATA_COLUMNS = [
  "forecast_kst_dtm",
  "data_available_kst_dtm",
  "grid_id",
  "latitude",
  "longitude",
]


def makeWeatherFrame(source, *, periods=2, start="2024-01-01 01:00:00", gridCount=None):
  expectedGridCount = {"ldaps": 16, "gfs": 9}
  if gridCount is None:
    gridCount = expectedGridCount[source]

  rows = []
  forecastTimes = pd.date_range(start, periods=periods, freq="h")
  for timeIndex, forecastTime in enumerate(forecastTimes):
    availableTime = forecastTime - pd.Timedelta(hours=12)
    for gridIndex in range(gridCount):
      value = float(10 * timeIndex + gridIndex + 1)
      rows.append(
        {
          "forecast_kst_dtm": forecastTime,
          "data_available_kst_dtm": availableTime,
          "grid_id": f"{source}_{gridIndex:02d}",
          "latitude": 33.0 + gridIndex * 0.01,
          "longitude": 126.0 + gridIndex * 0.01,
          "wind_u": value,
          "wind_v": value * 2,
        }
      )
  return pd.DataFrame(rows)


def testMissingRequiredMetadataColumnFailsClosed():
  weatherFrame = makeWeatherFrame("ldaps").drop(columns=["longitude"])

  with pytest.raises(ValueError, match="필수 metadata 컬럼 누락.*longitude"):
    aggregate_weather_grid(weatherFrame, source="ldaps")


def testAvailabilityCutoffViolationFailsClosed():
  weatherFrame = makeWeatherFrame("ldaps")
  weatherFrame.loc[0, "data_available_kst_dtm"] = (
    weatherFrame.loc[0, "forecast_kst_dtm"] + pd.Timedelta(hours=1)
  )

  with pytest.raises(ValueError, match="cutoff 위반"):
    aggregate_weather_grid(weatherFrame, source="ldaps")


@pytest.mark.parametrize(
  ("source", "badGridCount", "expectedGridCount"),
  [("ldaps", 15, 16), ("gfs", 8, 9)],
)
def testSourceGridCountContractViolationFailsClosed(source, badGridCount, expectedGridCount):
  weatherFrame = makeWeatherFrame(source, gridCount=badGridCount)

  with pytest.raises(ValueError, match=rf"grid 수 계약 위반.*{expectedGridCount}"):
    aggregate_weather_grid(weatherFrame, source=source)


def testInconsistentLeadInsideForecastFailsClosed():
  weatherFrame = makeWeatherFrame("ldaps")
  weatherFrame.loc[1, "data_available_kst_dtm"] = (
    weatherFrame.loc[1, "data_available_kst_dtm"] - pd.Timedelta(hours=1)
  )

  with pytest.raises(ValueError, match="동일 forecast 내부 lead 불일치"):
    aggregate_weather_grid(weatherFrame, source="ldaps")


def testMissingNumericWeatherFeatureFailsClosed():
  weatherFrame = makeWeatherFrame("gfs")
  weatherFrame["wind_u"] = "not-numeric"
  weatherFrame["wind_v"] = "not-numeric"

  with pytest.raises(ValueError, match="숫자형 weather feature가 없습니다"):
    aggregate_weather_grid(weatherFrame, source="gfs")


@pytest.mark.parametrize("driftKind", ["name", "order"])
def testTrainTestWeatherSchemaNameOrOrderDriftFailsClosed(driftKind):
  trainLdaps = makeWeatherFrame("ldaps")
  testLdaps = makeWeatherFrame("ldaps", start="2025-01-01 01:00:00")
  trainGfs = makeWeatherFrame("gfs")
  testGfs = makeWeatherFrame("gfs", start="2025-01-01 01:00:00")

  if driftKind == "name":
    testLdaps = testLdaps.rename(columns={"wind_v": "wind_speed"})
  else:
    testLdaps = testLdaps[[*METADATA_COLUMNS, "wind_v", "wind_u"]]

  with pytest.raises(ValueError, match="train/test 컬럼 이름 또는 순서 drift"):
    build_weather_feature_pair(trainLdaps, trainGfs, testLdaps, testGfs)


def testAllGridNaNForecastRemainsVisibleBeforeImputation():
  weatherFrame = makeWeatherFrame("ldaps")
  firstForecast = weatherFrame.loc[0, "forecast_kst_dtm"]
  weatherFrame.loc[weatherFrame["forecast_kst_dtm"] == firstForecast, "wind_u"] = np.nan

  aggregated = aggregate_weather_grid(
    weatherFrame,
    source="ldaps",
    statistics=SPATIAL_STATISTICS,
    include_lead=True,
  )
  firstRow = aggregated.loc[aggregated["forecast_kst_dtm"] == firstForecast].iloc[0]

  for statistic in SPATIAL_STATISTICS:
    assert pd.isna(firstRow[f"ldaps_wind_u_{statistic}"])


def testSourcePrefixCollisionFailsClosed():
  with pytest.raises(ValueError, match="source prefix 충돌"):
    build_weather_features(
      makeWeatherFrame("ldaps"),
      makeWeatherFrame("gfs"),
      source_prefixes=("weather", "weather"),
    )


def testDuplicateRawFeatureNameFailsClosed():
  weatherFrame = makeWeatherFrame("ldaps")
  duplicateFrame = pd.concat([weatherFrame, weatherFrame[["wind_u"]]], axis=1)

  with pytest.raises(ValueError, match="중복 feature 이름"):
    aggregate_weather_grid(duplicateFrame, source="ldaps")


def testPopulationStandardDeviationAndFeatureOrderAreFixed():
  weatherFrame = makeWeatherFrame("gfs", periods=1)
  aggregated = aggregate_weather_grid(
    weatherFrame,
    source="gfs",
    statistics=("max", "std", "mean", "min"),
    include_lead=True,
  )

  expectedColumns = ["forecast_kst_dtm"]
  for rawColumn in ["wind_u", "wind_v"]:
    expectedColumns.extend(
      f"gfs_{rawColumn}_{statistic}"
      for statistic in SPATIAL_STATISTICS
    )
  expectedColumns.append("gfs_lead_hour")

  assert list(aggregated.columns) == expectedColumns
  assert aggregated.loc[0, "gfs_wind_u_std"] == pytest.approx(
    np.std(np.arange(1.0, 10.0), ddof=0)
  )


def testFeaturePairKeepsExactTrainTestFeatureSchema():
  pair = build_weather_feature_pair(
    makeWeatherFrame("ldaps"),
    makeWeatherFrame("gfs"),
    makeWeatherFrame("ldaps", start="2025-01-01 01:00:00"),
    makeWeatherFrame("gfs", start="2025-01-01 01:00:00"),
    statistics=SPATIAL_STATISTICS,
    include_lead=True,
  )

  assert tuple(pair.train.columns[1:]) == pair.feature_columns
  assert tuple(pair.test.columns[1:]) == pair.feature_columns
  assert list(pair.train.columns) == list(pair.test.columns)


def testMedianImputerFitsTrainingOnlyAndRejectsColumnOrderDrift():
  trainFeatures = pd.DataFrame(
    {
      "feature_a": [1.0, 3.0, np.nan],
      "feature_b": [10.0, np.nan, 30.0],
    }
  )
  testFeatures = pd.DataFrame(
    {
      "feature_a": [1000.0, np.nan],
      "feature_b": [np.nan, 3000.0],
    }
  )

  fittedImputer = fit_train_median_imputer(trainFeatures)
  transformed = fittedImputer.transform(testFeatures)

  assert list(fittedImputer.statistics_) == pytest.approx([2.0, 20.0])
  assert transformed.loc[0, "feature_b"] == pytest.approx(20.0)
  assert transformed.loc[1, "feature_a"] == pytest.approx(2.0)

  with pytest.raises(ValueError, match="feature 컬럼 이름 또는 순서 drift"):
    fittedImputer.transform(testFeatures[["feature_b", "feature_a"]])
