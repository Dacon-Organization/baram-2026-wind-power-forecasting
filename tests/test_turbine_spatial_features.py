import numpy as np
import pandas as pd
import pytest

from baram.features.turbine_spatial import (
  SPATIAL_POOLING_METHODS,
  fit_turbine_spatial_pooler,
)


GFS_GRID = pd.DataFrame(
  {
    "grid_id": list(range(1, 10)),
    "latitude": [37.50, 37.50, 37.50, 37.25, 37.25, 37.25, 37.00, 37.00, 37.00],
    "longitude": [128.75, 129.00, 129.25, 128.75, 129.00, 129.25, 128.75, 129.00, 129.25],
  }
)


def makeWeatherFrame(*, periods=2, start="2024-01-01 01:00:00"):
  rows = []
  for timeIndex, forecastTime in enumerate(pd.date_range(start, periods=periods, freq="h")):
    for gridIndex, grid in GFS_GRID.iterrows():
      value = float(100 * timeIndex + gridIndex + 1)
      rows.append(
        {
          "forecast_kst_dtm": forecastTime,
          "data_available_kst_dtm": forecastTime - pd.Timedelta(hours=12),
          "grid_id": grid["grid_id"],
          "latitude": grid["latitude"],
          "longitude": grid["longitude"],
          "wind": value,
          "temperature": value * 10.0,
        }
      )
  return pd.DataFrame(rows)


def makeTurbineLocations():
  return pd.DataFrame(
    {
      "turbine_id": ["g1_a", "g1_b", "g2_a", "g3_a"],
      "group_id": ["group_1", "group_1", "group_2", "group_3"],
      "latitude": [37.50, 37.50, 37.25, 37.00],
      "longitude": [128.75, 129.00, 129.00, 129.25],
      "capacity_mw": [1.0, 3.0, 2.0, 4.0],
    }
  )


def fitPooler(**kwargs):
  options = {
    "source": "gfs",
    "pooling_methods": SPATIAL_POOLING_METHODS,
  }
  options.update(kwargs)
  return fit_turbine_spatial_pooler(
    makeWeatherFrame(),
    makeTurbineLocations(),
    **options,
  )


def testMissingTurbineMetadataFailsClosed():
  turbines = makeTurbineLocations().drop(columns=["capacity_mw"])

  with pytest.raises(ValueError, match="필수 metadata 컬럼 누락.*capacity_mw"):
    fit_turbine_spatial_pooler(
      makeWeatherFrame(), turbines, source="gfs"
    )


def testDuplicateTurbineIdFailsClosed():
  turbines = makeTurbineLocations()
  turbines.loc[1, "turbine_id"] = turbines.loc[0, "turbine_id"]

  with pytest.raises(ValueError, match="turbine_id 중복"):
    fit_turbine_spatial_pooler(
      makeWeatherFrame(), turbines, source="gfs"
    )


@pytest.mark.parametrize(
  ("column", "badValue", "message"),
  [
    ("latitude", np.nan, "터빈 좌표 결측"),
    ("latitude", 91.0, "유효 범위를 벗어난 좌표"),
    ("longitude", np.inf, "유효 범위를 벗어난 좌표"),
    ("capacity_mw", 0.0, "capacity_mw"),
    ("capacity_mw", True, "capacity_mw"),
    ("group_id", "Group 1", "group_id 형식 위반"),
  ],
)
def testInvalidTurbineMetadataFailsClosed(column, badValue, message):
  turbines = makeTurbineLocations()
  if isinstance(badValue, bool):
    turbines[column] = turbines[column].astype(object)
  turbines.loc[0, column] = badValue

  with pytest.raises(ValueError, match=message):
    fit_turbine_spatial_pooler(
      makeWeatherFrame(), turbines, source="gfs"
    )


@pytest.mark.parametrize(
  ("kwargs", "message"),
  [
    ({"pooling_methods": ()}, "pooling_methods는 하나 이상"),
    ({"pooling_methods": ("nearest", "nearest")}, "중복 pooling method"),
    ({"pooling_methods": ("kriging",)}, "지원하지 않는 pooling method"),
    ({"idw_power": 0.0}, "idw_power"),
    ({"idw_power": np.inf}, "idw_power"),
    ({"idw_power": True}, "idw_power"),
    ({"prefix": "GFS bad"}, "source prefix 형식 위반"),
  ],
)
def testInvalidPoolingConfigurationFailsClosed(kwargs, message):
  with pytest.raises(ValueError, match=message):
    fitPooler(**kwargs)


def testUnsupportedSourceFailsClosed():
  with pytest.raises(ValueError, match="지원하지 않는 weather source"):
    fit_turbine_spatial_pooler(
      makeWeatherFrame(), makeTurbineLocations(), source="wrf"
    )


def testGridGeometryDriftAcrossTrainForecastsFailsClosed():
  weather = makeWeatherFrame()
  secondForecast = weather["forecast_kst_dtm"].max()
  driftRow = weather.index[
    (weather["forecast_kst_dtm"] == secondForecast)
    & (weather["grid_id"] == 1)
  ][0]
  weather.loc[driftRow, "latitude"] += 0.01

  with pytest.raises(ValueError, match="forecast 사이 grid 좌표 drift"):
    fit_turbine_spatial_pooler(
      weather, makeTurbineLocations(), source="gfs"
    )


@pytest.mark.parametrize("driftKind", ["name", "order"])
def testTransformRawSchemaNameOrOrderDriftFailsClosed(driftKind):
  pooler = fitPooler()
  weather = makeWeatherFrame(start="2025-01-01 01:00:00")
  if driftKind == "name":
    weather = weather.rename(columns={"temperature": "humidity"})
  else:
    weather = weather[
      [
        "forecast_kst_dtm",
        "data_available_kst_dtm",
        "grid_id",
        "latitude",
        "longitude",
        "temperature",
        "wind",
      ]
    ]

  with pytest.raises(ValueError, match="fit/transform 컬럼 이름 또는 순서 drift"):
    pooler.transform(weather)


def testTransformGridIdDriftFailsClosed():
  pooler = fitPooler()
  weather = makeWeatherFrame(start="2025-01-01 01:00:00")
  weather.loc[weather["grid_id"] == 1, "grid_id"] = 99

  with pytest.raises(ValueError, match="fit/transform grid_id drift"):
    pooler.transform(weather)


def testTransformGridCoordinateDriftFailsClosed():
  pooler = fitPooler()
  weather = makeWeatherFrame(start="2025-01-01 01:00:00")
  weather.loc[weather["grid_id"] == 1, "latitude"] += 0.001

  with pytest.raises(ValueError, match="fit/transform grid 좌표 drift"):
    pooler.transform(weather)


def testExactGridMatchControlsNearestAndIdwWithCapacityWeights():
  result = fitPooler().transform(makeWeatherFrame(periods=1))

  assert result.loc[0, "gfs_wind_group_1_nearest"] == pytest.approx(1.75)
  assert result.loc[0, "gfs_wind_group_1_idw"] == pytest.approx(1.75)
  assert result.loc[0, "gfs_wind_group_2_nearest"] == pytest.approx(5.0)
  assert result.loc[0, "gfs_wind_group_3_idw"] == pytest.approx(9.0)


def testNearestTieIsSplitIndependentOfInputOrder():
  turbines = pd.DataFrame(
    {
      "turbine_id": ["tie"],
      "group_id": ["group_1"],
      "latitude": [37.50],
      "longitude": [128.875],
      "capacity_mw": [1.0],
    }
  )
  weather = makeWeatherFrame(periods=1)
  pooler = fit_turbine_spatial_pooler(
    weather, turbines, source="gfs", pooling_methods=("nearest",)
  )

  normal = pooler.transform(weather)
  shuffled = pooler.transform(weather.sample(frac=1.0, random_state=7))

  assert normal.loc[0, "gfs_wind_group_1_nearest"] == pytest.approx(1.5)
  pd.testing.assert_frame_equal(normal, shuffled)


def testPartialMissingRenormalizesAndAllMissingStaysMissing():
  pooler = fitPooler(pooling_methods=("nearest",))
  weather = makeWeatherFrame(periods=2)
  firstForecast = weather["forecast_kst_dtm"].min()
  weather.loc[
    (weather["forecast_kst_dtm"] == firstForecast)
    & (weather["grid_id"] == 1),
    "wind",
  ] = np.nan
  weather.loc[weather["forecast_kst_dtm"] != firstForecast, "wind"] = np.nan

  result = pooler.transform(weather)

  assert result.loc[0, "gfs_wind_group_1_nearest"] == pytest.approx(2.0)
  assert result.loc[1, [
    "gfs_wind_group_1_nearest",
    "gfs_wind_group_2_nearest",
    "gfs_wind_group_3_nearest",
  ]].isna().all()


def testOutputAxisFeatureNamesAndOrderAreDeterministic():
  weather = makeWeatherFrame()
  pooler = fitPooler(pooling_methods=("idw", "nearest"))

  result = pooler.transform(weather.sample(frac=1.0, random_state=42))
  expectedColumns = ["forecast_kst_dtm"]
  for rawFeature in ["wind", "temperature"]:
    for groupId in ["group_1", "group_2", "group_3"]:
      for method in SPATIAL_POOLING_METHODS:
        expectedColumns.append(f"gfs_{rawFeature}_{groupId}_{method}")

  assert list(result.columns) == expectedColumns
  assert result["forecast_kst_dtm"].is_monotonic_increasing
  assert isinstance(result.index, pd.RangeIndex)
  assert pooler.feature_columns == tuple(expectedColumns[1:])


def testFitAndTransformLeaveInputsUnchanged():
  trainWeather = makeWeatherFrame()
  turbines = makeTurbineLocations()
  transformWeather = makeWeatherFrame(start="2025-01-01 01:00:00")
  originalTrain = trainWeather.copy(deep=True)
  originalTurbines = turbines.copy(deep=True)
  originalTransform = transformWeather.copy(deep=True)

  pooler = fit_turbine_spatial_pooler(
    trainWeather, turbines, source="gfs"
  )
  pooler.transform(transformWeather)

  pd.testing.assert_frame_equal(trainWeather, originalTrain)
  pd.testing.assert_frame_equal(turbines, originalTurbines)
  pd.testing.assert_frame_equal(transformWeather, originalTransform)
