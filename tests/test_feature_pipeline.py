import numpy as np
import pandas as pd
import pytest

from baram.feature_config import (
  FeatureSetConfig,
  SpatialPoolingConfig,
  get_feature_set,
)
from baram.feature_pipeline import (
  FeaturePipeline,
  build_feature_pipeline,
  target_group_id,
)
from baram.metrics import TARGET_COLS


GRID_COUNTS = {"ldaps": 16, "gfs": 9}
VECTOR_COLUMNS = {
  "ldaps": ["heightAboveGround_10_10u", "heightAboveGround_10_10v"],
  "gfs": [
    "heightAboveGround_10_10u",
    "heightAboveGround_10_10v",
    "heightAboveGround_80_u",
    "heightAboveGround_80_v",
    "heightAboveGround_100_100u",
    "heightAboveGround_100_100v",
  ],
}
EXTRA_COLUMNS = {"ldaps": ["surface_t2m"], "gfs": ["surface_t2m", "surface_sp"]}


def makeWeatherFrame(source, *, start, periods, seed=0):
  """grid 수·lead 계약을 만족하는 합성 NWP frame."""
  generator = np.random.default_rng(seed)
  gridCount = GRID_COUNTS[source]
  rows = []
  for timeIndex, forecastTime in enumerate(pd.date_range(start, periods=periods, freq="h")):
    availableTime = forecastTime - pd.Timedelta(hours=13)
    for gridIndex in range(gridCount):
      row = {
        "forecast_kst_dtm": forecastTime,
        "data_available_kst_dtm": availableTime,
        "grid_id": f"{source}_{gridIndex:02d}",
        "latitude": 37.25 + gridIndex * 0.01,
        "longitude": 128.94 + gridIndex * 0.01,
      }
      for column in VECTOR_COLUMNS[source] + EXTRA_COLUMNS[source]:
        row[column] = float(generator.normal(loc=5.0 + timeIndex * 0.1, scale=1.0))
      rows.append(row)
  return pd.DataFrame(rows)


def makeTurbineLocations():
  rows = []
  layout = {"group_1": (6, 3.6), "group_2": (6, 3.6), "group_3": (5, 4.2)}
  index = 0
  for groupId, (turbineCount, capacity) in layout.items():
    for _ in range(turbineCount):
      rows.append(
        {
          "turbine_id": f"T-{index:02d}",
          "group_id": groupId,
          "latitude": 37.26 + index * 0.004,
          "longitude": 128.95 + index * 0.003,
          "capacity_mw": capacity,
        }
      )
      index += 1
  return pd.DataFrame(rows)


@pytest.fixture
def weatherFrames():
  return {
    "train_ldaps": makeWeatherFrame("ldaps", start="2024-01-01 01:00", periods=8, seed=1),
    "train_gfs": makeWeatherFrame("gfs", start="2024-01-01 01:00", periods=8, seed=2),
    "test_ldaps": makeWeatherFrame("ldaps", start="2025-01-01 01:00", periods=5, seed=3),
    "test_gfs": makeWeatherFrame("gfs", start="2025-01-01 01:00", periods=5, seed=4),
  }


@pytest.fixture
def timeAxes(weatherFrames):
  return {
    "train_time_index": weatherFrames["train_ldaps"]["forecast_kst_dtm"].drop_duplicates(),
    "test_time_index": weatherFrames["test_ldaps"]["forecast_kst_dtm"].drop_duplicates(),
  }


def buildPipeline(config, weatherFrames, timeAxes, *, turbineLocations=None):
  return build_feature_pipeline(
    config,
    train_time_index=timeAxes["train_time_index"],
    test_time_index=timeAxes["test_time_index"],
    train_ldaps=weatherFrames["train_ldaps"],
    train_gfs=weatherFrames["train_gfs"],
    test_ldaps=weatherFrames["test_ldaps"],
    test_gfs=weatherFrames["test_gfs"],
    turbine_locations=turbineLocations,
  )


class TestTargetGroupId:
  def test_target에서_그룹_id를_뽑는다(self):
    assert target_group_id("kpx_group_1") == "group_1"
    assert [target_group_id(target) for target in TARGET_COLS] == [
      "group_1",
      "group_2",
      "group_3",
    ]

  def test_알_수_없는_target을_거부한다(self):
    with pytest.raises(ValueError, match="target"):
      target_group_id("kpx_group_9")


class TestColumnOrderContract:
  def test_calendar가_맨_앞이고_ldaps가_gfs보다_먼저다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(get_feature_set("official_mean"), weatherFrames, timeAxes)
    columns = list(pipeline.feature_columns)
    assert columns[:9] == [
      "month",
      "day",
      "hour",
      "dayofweek",
      "is_weekend",
      "hour_sin",
      "hour_cos",
      "month_sin",
      "month_cos",
    ]
    firstGfs = next(index for index, name in enumerate(columns) if name.startswith("gfs_"))
    lastLdaps = max(index for index, name in enumerate(columns) if name.startswith("ldaps_"))
    assert lastLdaps < firstGfs

  def test_lead는_각_source의_마지막_집계_컬럼이다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(get_feature_set("official_mean"), weatherFrames, timeAxes)
    columns = list(pipeline.feature_columns)
    assert columns[columns.index("ldaps_lead_hour") + 1].startswith("gfs_")
    assert columns[-1] == "gfs_lead_hour"

  def test_calendar를_끄면_9개가_사라진다(self, weatherFrames, timeAxes):
    withCalendar = buildPipeline(get_feature_set("official_mean"), weatherFrames, timeAxes)
    config = FeatureSetConfig(name="no_calendar", include_lead=True, calendar=False)
    withoutCalendar = buildPipeline(config, weatherFrames, timeAxes)
    assert len(withCalendar.feature_columns) - len(withoutCalendar.feature_columns) == 9

  def test_공간_컬럼은_집계_컬럼_뒤에_온다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(
      get_feature_set("spatial_idw2_all_group"),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    columns = list(pipeline.feature_columns)
    spatialPositions = [
      index for index, name in enumerate(columns) if name.endswith("_idw")
    ]
    aggregatePositions = [
      index for index, name in enumerate(columns) if name.endswith(("_mean", "_std", "_min", "_max"))
    ]
    assert min(spatialPositions) > max(aggregatePositions)

  def test_공간_컬럼_이름은_prefix_raw_group_method_규약을_따른다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(
      get_feature_set("spatial_idw2_all_group"),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    spatial = [name for name in pipeline.feature_columns if name.endswith("_idw")]
    assert spatial[0].startswith("ldaps_")
    assert "_group_1_idw" in spatial[0]
    assert all(
      any(f"_group_{index}_idw" in name for index in (1, 2, 3)) for name in spatial
    )


class TestTrainTestSymmetry:
  @pytest.mark.parametrize(
    "presetName",
    ["official_mean", "expanded_vector", "spatial_idw2_all_group", "spatial_nearest_own_group"],
  )
  def test_train과_test의_컬럼_이름과_순서가_같다(self, presetName, weatherFrames, timeAxes):
    pipeline = buildPipeline(
      get_feature_set(presetName),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    assert list(pipeline.train_matrix.columns) == list(pipeline.test_matrix.columns)
    assert list(pipeline.train_matrix.columns) == list(pipeline.feature_columns)

  def test_행_수가_시간축과_같다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(get_feature_set("expanded_vector"), weatherFrames, timeAxes)
    assert len(pipeline.train_matrix) == len(timeAxes["train_time_index"])
    assert len(pipeline.test_matrix) == len(timeAxes["test_time_index"])

  def test_입력_frame을_바꾸지_않는다(self, weatherFrames, timeAxes):
    before = {name: frame.copy(deep=True) for name, frame in weatherFrames.items()}
    buildPipeline(
      get_feature_set("spatial_idw2_all_group"),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    for name, frame in weatherFrames.items():
      pd.testing.assert_frame_equal(frame, before[name])

  def test_같은_입력이면_결정론적이다(self, weatherFrames, timeAxes):
    left = buildPipeline(
      get_feature_set("spatial_idw2_all_group"),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    right = buildPipeline(
      get_feature_set("spatial_idw2_all_group"),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    pd.testing.assert_frame_equal(left.train_matrix, right.train_matrix)
    pd.testing.assert_frame_equal(left.test_matrix, right.test_matrix)


class TestFeatureCountProgression:
  def test_피처_수가_설계한_순서대로_늘어난다(self, weatherFrames, timeAxes):
    counts = {}
    for presetName in (
      "official_mean",
      "expanded_vector",
      "spatial_nearest_own_group",
      "spatial_idw2_all_group",
    ):
      pipeline = buildPipeline(
        get_feature_set(presetName),
        weatherFrames,
        timeAxes,
        turbineLocations=makeTurbineLocations(),
      )
      counts[presetName] = len(pipeline.feature_columns)
    assert counts["official_mean"] < counts["expanded_vector"]
    assert counts["expanded_vector"] < counts["spatial_idw2_all_group"]
    assert counts["spatial_nearest_own_group"] == counts["spatial_idw2_all_group"]

  def test_wind_vector는_source별_파생_컬럼을_더한다(self, weatherFrames, timeAxes):
    withoutVector = FeatureSetConfig(
      name="stats_only",
      statistics=("mean", "std", "min", "max"),
      include_lead=True,
    )
    withVector = get_feature_set("expanded_vector")
    plain = buildPipeline(withoutVector, weatherFrames, timeAxes)
    vector = buildPipeline(withVector, weatherFrames, timeAxes)
    # LDAPS 1쌍 + GFS 3쌍 = 4쌍 × (speed, sin, cos) 3개 × 통계 4종
    assert len(vector.feature_columns) - len(plain.feature_columns) == 4 * 3 * 4


class TestTargetFeatureColumns:
  def test_all_group은_세_target이_superset을_공유한다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(
      get_feature_set("spatial_idw2_all_group"),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    for target in TARGET_COLS:
      assert pipeline.target_feature_columns[target] == pipeline.feature_columns

  def test_공간_피처가_없으면_세_target이_superset을_공유한다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(get_feature_set("expanded_vector"), weatherFrames, timeAxes)
    for target in TARGET_COLS:
      assert pipeline.target_feature_columns[target] == pipeline.feature_columns

  def test_own_group은_자기_그룹_컬럼만_남긴다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(
      get_feature_set("spatial_nearest_own_group"),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    for target in TARGET_COLS:
      groupId = target_group_id(target)
      selected = pipeline.target_feature_columns[target]
      spatial = [name for name in selected if name.endswith("_nearest")]
      assert spatial, "공간 컬럼이 하나도 남지 않았습니다"
      assert all(f"_{groupId}_" in name for name in spatial)
      assert len(selected) < len(pipeline.feature_columns)

  def test_own_group의_target별_컬럼은_superset의_순서를_보존한다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(
      get_feature_set("spatial_nearest_own_group"),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    superset = list(pipeline.feature_columns)
    for target in TARGET_COLS:
      selected = list(pipeline.target_feature_columns[target])
      assert selected == [name for name in superset if name in set(selected)]

  def test_own_group_세_target의_합집합이_superset이다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(
      get_feature_set("spatial_nearest_own_group"),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    union = set()
    for target in TARGET_COLS:
      union |= set(pipeline.target_feature_columns[target])
    assert union == set(pipeline.feature_columns)


class TestSpatialGuards:
  def test_터빈_좌표_없이_공간_프리셋을_돌리면_실패한다(self, weatherFrames, timeAxes):
    with pytest.raises(ValueError, match="터빈 좌표"):
      buildPipeline(get_feature_set("spatial_idw2_all_group"), weatherFrames, timeAxes)

  def test_공간을_안_쓰면_pooler가_비어_있다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(get_feature_set("expanded_vector"), weatherFrames, timeAxes)
    assert pipeline.spatial_poolers == {}

  def test_공간을_쓰면_source별_pooler를_보관한다(self, weatherFrames, timeAxes):
    pipeline = buildPipeline(
      get_feature_set("spatial_idw2_all_group"),
      weatherFrames,
      timeAxes,
      turbineLocations=makeTurbineLocations(),
    )
    assert sorted(pipeline.spatial_poolers) == ["gfs", "ldaps"]

  def test_pooler는_train_geometry에만_fit한다(self, weatherFrames, timeAxes):
    drifted = weatherFrames["test_ldaps"].copy()
    drifted["latitude"] = drifted["latitude"] + 1.0
    weatherFrames["test_ldaps"] = drifted
    with pytest.raises(ValueError, match="drift"):
      buildPipeline(
        get_feature_set("spatial_idw2_all_group"),
        weatherFrames,
        timeAxes,
        turbineLocations=makeTurbineLocations(),
      )

  def test_method가_두_개면_컬럼도_두_배가_된다(self, weatherFrames, timeAxes):
    single = get_feature_set("spatial_idw2_all_group")
    both = FeatureSetConfig(
      name="both_methods",
      statistics=single.statistics,
      include_lead=single.include_lead,
      wind_vector=single.wind_vector,
      spatial=SpatialPoolingConfig(methods=("nearest", "idw"), idw_power=2.0),
    )
    onePipeline = buildPipeline(
      single, weatherFrames, timeAxes, turbineLocations=makeTurbineLocations()
    )
    bothPipeline = buildPipeline(
      both, weatherFrames, timeAxes, turbineLocations=makeTurbineLocations()
    )
    oneSpatial = [name for name in onePipeline.feature_columns if name.endswith("_idw")]
    bothSpatial = [
      name for name in bothPipeline.feature_columns if name.endswith(("_idw", "_nearest"))
    ]
    assert len(bothSpatial) == 2 * len(oneSpatial)

  def test_method_하나만_fit해도_컬럼_순서가_같다(self, weatherFrames, timeAxes):
    """랩은 두 method로 fit한 뒤 suffix로 걸렀다. 하나만 fit해도 같은 순서여야 한다."""
    single = get_feature_set("spatial_idw2_all_group")
    both = FeatureSetConfig(
      name="both_methods",
      statistics=single.statistics,
      include_lead=single.include_lead,
      wind_vector=single.wind_vector,
      spatial=SpatialPoolingConfig(methods=("nearest", "idw"), idw_power=2.0),
    )
    onePipeline = buildPipeline(
      single, weatherFrames, timeAxes, turbineLocations=makeTurbineLocations()
    )
    bothPipeline = buildPipeline(
      both, weatherFrames, timeAxes, turbineLocations=makeTurbineLocations()
    )
    oneSpatial = [name for name in onePipeline.feature_columns if name.endswith("_idw")]
    bothFiltered = [name for name in bothPipeline.feature_columns if name.endswith("_idw")]
    assert oneSpatial == bothFiltered
    pd.testing.assert_frame_equal(
      onePipeline.train_matrix[oneSpatial],
      bothPipeline.train_matrix[bothFiltered],
    )


class TestPipelineType:
  def test_결과는_FeaturePipeline이며_config를_보관한다(self, weatherFrames, timeAxes):
    config = get_feature_set("expanded_vector")
    pipeline = buildPipeline(config, weatherFrames, timeAxes)
    assert isinstance(pipeline, FeaturePipeline)
    assert pipeline.config is config

  def test_시간축이_weather에_없으면_결측으로_남긴다(self, weatherFrames, timeAxes):
    extended = pd.concat(
      [
        timeAxes["train_time_index"],
        pd.Series(pd.to_datetime(["2024-06-01 01:00"])),
      ],
      ignore_index=True,
    )
    timeAxes["train_time_index"] = extended
    pipeline = buildPipeline(get_feature_set("official_mean"), weatherFrames, timeAxes)
    assert len(pipeline.train_matrix) == len(extended)
    assert pipeline.train_matrix.iloc[-1].filter(like="ldaps_").isna().all()
