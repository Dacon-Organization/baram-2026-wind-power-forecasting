"""피처셋 config 하나로 train/test feature matrix를 대칭으로 조립하는 모듈.

조립 순서는 계약이다. 노트북 06~08의 랩이 만든 컬럼 이름과 순서를 그대로
재현해야 같은 RandomForest 점수가 나오므로, 아래 순서를 바꾸면 안 된다.

  ① raw grid 행에 wind vector 파생   (config.wind_vector)
  ② forecast 시각 단위 grid 통계 집계 (config.statistics / include_lead)
  ③ 터빈 그룹별 공간 pooling          (config.spatial)
  ④ calendar feature를 맨 앞에 결합   (config.calendar)

최종 컬럼 순서: calendar → ldaps 집계 → gfs 집계 → ldaps pooling → gfs pooling
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from baram.baseline import calendar_features
from baram.feature_config import FeatureSetConfig
from baram.features.turbine_spatial import fit_turbine_spatial_pooler
from baram.features.weather_grid import build_weather_feature_pair, build_weather_features
from baram.features.wind_vector import derive_wind_vector_features
from baram.metrics import TARGET_COLS


WEATHER_SOURCES = ("ldaps", "gfs")
_TARGET_GROUP_PREFIX = "kpx_"


@dataclass(frozen=True)
class TrainFeatureBuild:
  """train CLI가 test 파일 없이 만들 수 있는 학습용 조립 결과."""

  config: FeatureSetConfig
  matrix: pd.DataFrame
  feature_columns: tuple
  target_feature_columns: dict
  spatial_poolers: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FeaturePipeline:
  """config 한 벌로 만든 train/test feature matrix와 fit된 변환기."""

  config: FeatureSetConfig
  train_matrix: pd.DataFrame
  test_matrix: pd.DataFrame
  feature_columns: tuple[str, ...]
  target_feature_columns: dict
  spatial_poolers: dict = field(default_factory=dict)
  weather_profile: dict = field(default_factory=dict, repr=False)


def target_group_id(target):
  """`kpx_group_1` 같은 target 이름에서 공간 pooling 그룹 id를 뽑는다."""
  if target not in TARGET_COLS:
    raise ValueError(f"알 수 없는 target: {target!r}; 허용값={list(TARGET_COLS)}")
  return target.removeprefix(_TARGET_GROUP_PREFIX)


def _derive_vector_frames(config, frames):
  """① wind vector 파생. 끄면 원본을 그대로 쓴다."""
  if not config.wind_vector:
    return dict(frames)
  return {
    key: derive_wind_vector_features(frame, source=key.split("_")[0])
    for key, frame in frames.items()
  }


def _merge_on_forecast(left, right):
  return left.merge(
    right,
    on="forecast_kst_dtm",
    how="inner",
    sort=True,
    validate="one_to_one",
  )


def _build_spatial_features(config, vector_frames, turbine_locations):
  """③ 터빈 그룹별 공간 pooling. train geometry에만 fit한다."""
  poolers = {}
  train_parts = []
  test_parts = []
  for source in WEATHER_SOURCES:
    pooler = fit_turbine_spatial_pooler(
      vector_frames[f"{source}_train"],
      turbine_locations,
      source=source,
      pooling_methods=config.spatial.methods,
      idw_power=config.spatial.idw_power,
    )
    poolers[source] = pooler
    train_parts.append(pooler.transform(vector_frames[f"{source}_train"]))
    test_parts.append(pooler.transform(vector_frames[f"{source}_test"]))

  return (
    poolers,
    _merge_on_forecast(*train_parts),
    _merge_on_forecast(*test_parts),
  )


def _align_to_time_axis(time_index, features, frame_name):
  """label / sample_submission 시간축에 feature를 좌측 결합한다."""
  base = pd.DataFrame({"forecast_kst_dtm": pd.to_datetime(pd.Series(time_index).reset_index(drop=True))})
  merged = base.merge(
    features,
    on="forecast_kst_dtm",
    how="left",
    sort=False,
    validate="one_to_one",
  )
  if len(merged) != len(base):
    raise ValueError(f"{frame_name} 시간축과 feature 행 수가 다릅니다")
  return merged


def _assemble_matrix(config, time_index, weather_features, spatial_features, frame_name):
  """④ calendar를 맨 앞에 두고 집계 → 공간 순서로 결합한다."""
  merged = _align_to_time_axis(time_index, weather_features, frame_name)
  parts = []
  if config.calendar:
    parts.append(calendar_features(merged["forecast_kst_dtm"]))
  parts.append(merged.drop(columns=["forecast_kst_dtm"]))

  if spatial_features is not None:
    spatial_merged = _align_to_time_axis(time_index, spatial_features, f"{frame_name} spatial")
    parts.append(spatial_merged.drop(columns=["forecast_kst_dtm"]))

  matrix = pd.concat(parts, axis=1)
  duplicated = list(matrix.columns[matrix.columns.duplicated()])
  if duplicated:
    raise ValueError(f"{frame_name} 중복 feature 컬럼: {duplicated}")
  return matrix


def _target_columns(config, feature_columns, spatial_columns):
  """own_group scope에서만 target별로 컬럼을 슬라이스한다."""
  superset = tuple(feature_columns)
  if config.spatial is None or config.spatial.scope == "all_group":
    return {target: superset for target in TARGET_COLS}

  spatial_set = set(spatial_columns)
  selected = {}
  for target in TARGET_COLS:
    group_id = target_group_id(target)
    marker = f"_{group_id}_"
    columns = tuple(
      name
      for name in superset
      if name not in spatial_set or marker in name
    )
    if len(columns) == len(superset):
      raise ValueError(
        f"{target}의 own_group 슬라이스가 아무 컬럼도 걸러내지 못했습니다"
      )
    selected[target] = columns
  return selected


def _require_turbine_locations(config, turbine_locations):
  if config.uses_spatial and turbine_locations is None:
    raise ValueError(
      f"{config.name}은 공간 pooling을 사용하므로 터빈 좌표가 필요합니다. "
      "info.xlsx 경로를 지정하세요"
    )


def build_train_features(config, *, time_index, ldaps, gfs, turbine_locations=None):
  """train CLI 경로. test 파일 없이 학습용 matrix와 fit된 pooler를 만든다.

  train/test raw schema 대조는 여기서 하지 않는다. inference가 bundle의
  feature_columns와 대조하므로 drift는 그 시점에 실패로 드러난다.
  """
  if not isinstance(config, FeatureSetConfig):
    raise TypeError("config는 FeatureSetConfig여야 합니다")
  _require_turbine_locations(config, turbine_locations)

  vector_frames = _derive_vector_frames(config, {"ldaps_train": ldaps, "gfs_train": gfs})
  weather = build_weather_features(
    vector_frames["ldaps_train"],
    vector_frames["gfs_train"],
    statistics=config.statistics,
    include_lead=config.include_lead,
  )

  poolers = {}
  spatial_features = None
  spatial_columns = ()
  if config.uses_spatial:
    parts = []
    for source in WEATHER_SOURCES:
      pooler = fit_turbine_spatial_pooler(
        vector_frames[f"{source}_train"],
        turbine_locations,
        source=source,
        pooling_methods=config.spatial.methods,
        idw_power=config.spatial.idw_power,
      )
      poolers[source] = pooler
      parts.append(pooler.transform(vector_frames[f"{source}_train"]))
    spatial_features = _merge_on_forecast(*parts)
    spatial_columns = tuple(
      column for column in spatial_features.columns if column != "forecast_kst_dtm"
    )

  matrix = _assemble_matrix(config, time_index, weather, spatial_features, "train")
  feature_columns = tuple(matrix.columns)
  return TrainFeatureBuild(
    config=config,
    matrix=matrix,
    feature_columns=feature_columns,
    target_feature_columns=_target_columns(config, feature_columns, spatial_columns),
    spatial_poolers=poolers,
  )


def build_test_features(config, *, time_index, ldaps, gfs, spatial_poolers=None):
  """inference CLI 경로. train에서 fit한 pooler를 그대로 transform에만 쓴다."""
  if not isinstance(config, FeatureSetConfig):
    raise TypeError("config는 FeatureSetConfig여야 합니다")
  poolers = spatial_poolers or {}
  if config.uses_spatial and sorted(poolers) != sorted(WEATHER_SOURCES):
    raise ValueError(
      f"{config.name}은 공간 pooling을 사용하므로 train에서 fit한 pooler가 필요합니다: "
      f"받은 source={sorted(poolers)}"
    )

  vector_frames = _derive_vector_frames(config, {"ldaps_test": ldaps, "gfs_test": gfs})
  weather = build_weather_features(
    vector_frames["ldaps_test"],
    vector_frames["gfs_test"],
    statistics=config.statistics,
    include_lead=config.include_lead,
  )

  spatial_features = None
  if config.uses_spatial:
    spatial_features = _merge_on_forecast(
      *[poolers[source].transform(vector_frames[f"{source}_test"]) for source in WEATHER_SOURCES]
    )
  return _assemble_matrix(config, time_index, weather, spatial_features, "test")


def build_feature_pipeline(
  config,
  *,
  train_time_index,
  test_time_index,
  train_ldaps,
  train_gfs,
  test_ldaps,
  test_gfs,
  turbine_locations=None,
):
  """피처셋 config로 train/test feature matrix를 대칭으로 만든다."""
  if not isinstance(config, FeatureSetConfig):
    raise TypeError("config는 FeatureSetConfig여야 합니다")
  _require_turbine_locations(config, turbine_locations)

  frames = {
    "ldaps_train": train_ldaps,
    "gfs_train": train_gfs,
    "ldaps_test": test_ldaps,
    "gfs_test": test_gfs,
  }
  vector_frames = _derive_vector_frames(config, frames)

  weather_pair = build_weather_feature_pair(
    vector_frames["ldaps_train"],
    vector_frames["gfs_train"],
    vector_frames["ldaps_test"],
    vector_frames["gfs_test"],
    statistics=config.statistics,
    include_lead=config.include_lead,
  )

  spatial_poolers = {}
  spatial_train = None
  spatial_test = None
  spatial_columns = ()
  if config.uses_spatial:
    spatial_poolers, spatial_train, spatial_test = _build_spatial_features(
      config,
      vector_frames,
      turbine_locations,
    )
    spatial_columns = tuple(
      column for column in spatial_train.columns if column != "forecast_kst_dtm"
    )

  train_matrix = _assemble_matrix(
    config,
    train_time_index,
    weather_pair.train,
    spatial_train,
    "train",
  )
  test_matrix = _assemble_matrix(
    config,
    test_time_index,
    weather_pair.test,
    spatial_test,
    "test",
  )
  if list(train_matrix.columns) != list(test_matrix.columns):
    raise ValueError("train/test feature 컬럼 이름 또는 순서 drift")

  feature_columns = tuple(train_matrix.columns)
  return FeaturePipeline(
    config=config,
    train_matrix=train_matrix,
    test_matrix=test_matrix,
    feature_columns=feature_columns,
    target_feature_columns=_target_columns(config, feature_columns, spatial_columns),
    spatial_poolers=spatial_poolers,
    weather_profile={
      "aggregated_feature_count": len(weather_pair.feature_columns),
      "spatial_feature_count": len(spatial_columns),
      "total_feature_count": len(feature_columns),
    },
  )


__all__ = [
  "FeaturePipeline",
  "TrainFeatureBuild",
  "WEATHER_SOURCES",
  "build_feature_pipeline",
  "build_test_features",
  "build_train_features",
  "target_group_id",
]
