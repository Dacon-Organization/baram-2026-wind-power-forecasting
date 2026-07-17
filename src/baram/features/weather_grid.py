"""LDAPS/GFS 격자 통계 feature와 train-fit 결측 처리를 관리한다."""

from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer


WEATHER_METADATA_COLUMNS = (
  "forecast_kst_dtm",
  "data_available_kst_dtm",
  "grid_id",
  "latitude",
  "longitude",
)
EXPECTED_GRID_COUNTS = {
  "ldaps": 16,
  "gfs": 9,
}
EXPECTED_LEAD_RANGE_HOURS = (12.0, 35.0)
SPATIAL_STATISTICS = ("mean", "std", "min", "max")
STD_DDOF = 0


@dataclass(frozen=True)
class WeatherFeaturePair:
  """동일 schema로 잠긴 train/test weather feature 묶음."""

  train: pd.DataFrame
  test: pd.DataFrame
  feature_columns: tuple[str, ...]


@dataclass(frozen=True)
class TrainMedianImputer:
  """학습 frame에만 fit하고 exact schema로 transform하는 median imputer."""

  feature_columns: tuple[str, ...]
  imputer: SimpleImputer

  @property
  def statistics_(self):
    """학습 데이터에서 계산한 median을 sklearn과 같은 이름으로 노출한다."""
    return self.imputer.statistics_

  def transform(self, feature_frame):
    """fit 당시 컬럼 이름과 순서가 같은 frame만 변환한다."""
    _validate_feature_matrix(feature_frame, "transform feature_frame")
    if tuple(feature_frame.columns) != self.feature_columns:
      raise ValueError(
        "feature 컬럼 이름 또는 순서 drift: "
        f"expected={list(self.feature_columns)}, actual={list(feature_frame.columns)}"
      )

    transformed = self.imputer.transform(feature_frame)
    result = pd.DataFrame(
      transformed,
      columns=self.feature_columns,
      index=feature_frame.index,
    )
    if result.isna().any().any():
      raise ValueError("train-fit median 변환 후에도 결측 feature가 남았습니다")
    return result


def _validate_source(source):
  if source not in EXPECTED_GRID_COUNTS:
    raise ValueError(
      f"지원하지 않는 weather source: {source!r}; "
      f"허용값={list(EXPECTED_GRID_COUNTS)}"
    )


def _validate_prefix(prefix):
  if not isinstance(prefix, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", prefix):
    raise ValueError(f"source prefix 형식 위반: {prefix!r}")


def _validate_statistics(statistics, std_ddof):
  if isinstance(statistics, str):
    requested = (statistics,)
  else:
    requested = tuple(statistics)
  if not requested:
    raise ValueError("weather 공간 통계가 하나 이상 필요합니다")
  if len(set(requested)) != len(requested):
    raise ValueError(f"중복 공간 통계: {list(requested)}")

  unsupported = [statistic for statistic in requested if statistic not in SPATIAL_STATISTICS]
  if unsupported:
    raise ValueError(f"지원하지 않는 공간 통계: {unsupported}")
  if isinstance(std_ddof, bool) or not isinstance(std_ddof, int) or std_ddof < 0:
    raise ValueError("std_ddof는 0 이상의 정수여야 합니다")

  return tuple(
    statistic
    for statistic in SPATIAL_STATISTICS
    if statistic in requested
  )


def _validate_frame_columns(frame, frame_name):
  if not isinstance(frame, pd.DataFrame):
    raise TypeError(f"{frame_name}은 pandas DataFrame이어야 합니다")
  if frame.empty:
    raise ValueError(f"{frame_name}이 비어 있습니다")

  duplicate_columns = list(frame.columns[frame.columns.duplicated()])
  if duplicate_columns:
    raise ValueError(f"{frame_name} 중복 feature 이름: {duplicate_columns}")

  missing_columns = [
    column
    for column in WEATHER_METADATA_COLUMNS
    if column not in frame.columns
  ]
  if missing_columns:
    raise ValueError(f"{frame_name} 필수 metadata 컬럼 누락: {missing_columns}")


def _numeric_weather_columns(frame, frame_name):
  _validate_frame_columns(frame, frame_name)
  metadata_columns = set(WEATHER_METADATA_COLUMNS)
  value_columns = [
    column
    for column in frame.columns
    if column not in metadata_columns
    and pd.api.types.is_numeric_dtype(frame[column])
    and not pd.api.types.is_bool_dtype(frame[column])
  ]
  if not value_columns:
    raise ValueError(f"{frame_name} 숫자형 weather feature가 없습니다")
  return value_columns


def _validated_working_frame(frame, source):
  frame_name = f"{source}_weather"
  value_columns = _numeric_weather_columns(frame, frame_name)
  working = frame[[*WEATHER_METADATA_COLUMNS, *value_columns]].copy()

  try:
    working["forecast_kst_dtm"] = pd.to_datetime(
      working["forecast_kst_dtm"],
      errors="raise",
    )
    working["data_available_kst_dtm"] = pd.to_datetime(
      working["data_available_kst_dtm"],
      errors="raise",
    )
  except (TypeError, ValueError) as error:
    raise ValueError(f"{frame_name} timestamp 파싱 실패") from error

  null_metadata = {
    column: int(working[column].isna().sum())
    for column in WEATHER_METADATA_COLUMNS
    if working[column].isna().any()
  }
  if null_metadata:
    raise ValueError(f"{frame_name} metadata 결측: {null_metadata}")

  forecast_time = working["forecast_kst_dtm"]
  available_time = working["data_available_kst_dtm"]
  cutoff_violation = available_time > forecast_time
  if cutoff_violation.any():
    raise ValueError(
      f"{frame_name} cutoff 위반: 사용 가능 시각이 예보 대상 시각보다 늦은 행 "
      f"{int(cutoff_violation.sum())}개"
    )

  working["_lead_hour"] = (
    forecast_time - available_time
  ).dt.total_seconds().div(3600)
  lead_count = working.groupby("forecast_kst_dtm", sort=False)["_lead_hour"].nunique()
  inconsistent_lead = lead_count[lead_count != 1]
  if not inconsistent_lead.empty:
    raise ValueError(
      f"{frame_name} 동일 forecast 내부 lead 불일치: "
      f"forecast {len(inconsistent_lead)}개"
    )

  lead_minimum, lead_maximum = EXPECTED_LEAD_RANGE_HOURS
  lead_outside_contract = ~working["_lead_hour"].between(lead_minimum, lead_maximum)
  if lead_outside_contract.any():
    raise ValueError(
      f"{frame_name} lead 범위 계약 위반: "
      f"허용={lead_minimum:g}~{lead_maximum:g}시간, "
      f"위반 행={int(lead_outside_contract.sum())}개"
    )

  expected_grid_count = EXPECTED_GRID_COUNTS[source]
  grouped = working.groupby("forecast_kst_dtm", sort=False)
  rows_per_forecast = grouped.size()
  unique_grids = grouped["grid_id"].nunique()
  bad_grid_contract = (
    (rows_per_forecast != expected_grid_count)
    | (unique_grids != expected_grid_count)
  )
  if bad_grid_contract.any():
    raise ValueError(
      f"{frame_name} grid 수 계약 위반: forecast당 정확히 "
      f"{expected_grid_count}개가 필요하며 위반 forecast "
      f"{int(bad_grid_contract.sum())}개"
    )

  duplicate_grid_rows = working.duplicated(
    subset=["forecast_kst_dtm", "grid_id"],
    keep=False,
  )
  if duplicate_grid_rows.any():
    raise ValueError(
      f"{frame_name} grid 수 계약 위반: 동일 forecast/grid_id 중복 행 "
      f"{int(duplicate_grid_rows.sum())}개"
    )

  return working, value_columns


def aggregate_weather_grid(
  frame,
  *,
  source,
  statistics=("mean",),
  include_lead=False,
  prefix=None,
  std_ddof=STD_DDOF,
):
  """한 source의 raw grid를 forecast별 결정적 공간 통계로 집계한다.

  모든 grid가 NaN인 forecast-variable은 NaN을 그대로 유지한다. 결측 보정은
  이 함수 이후 학습 구간에만 fit한 imputer가 담당한다.
  """
  _validate_source(source)
  normalized_statistics = _validate_statistics(statistics, std_ddof)
  resolved_prefix = source if prefix is None else prefix
  _validate_prefix(resolved_prefix)
  working, value_columns = _validated_working_frame(frame, source)

  grouped = working.groupby("forecast_kst_dtm", sort=True)[value_columns]
  statistic_frames = {}
  if "mean" in normalized_statistics:
    statistic_frames["mean"] = grouped.mean()
  if "std" in normalized_statistics:
    statistic_frames["std"] = grouped.std(ddof=std_ddof)
  if "min" in normalized_statistics:
    statistic_frames["min"] = grouped.min()
  if "max" in normalized_statistics:
    statistic_frames["max"] = grouped.max()

  feature_series = {}
  for value_column in value_columns:
    for statistic in normalized_statistics:
      feature_name = f"{resolved_prefix}_{value_column}_{statistic}"
      if feature_name in feature_series:
        raise ValueError(f"집계 결과 중복 feature 이름: {feature_name}")
      feature_series[feature_name] = statistic_frames[statistic][value_column]

  aggregated = pd.DataFrame(feature_series)
  if include_lead:
    lead_name = f"{resolved_prefix}_lead_hour"
    if lead_name in aggregated.columns:
      raise ValueError(f"집계 결과 중복 feature 이름: {lead_name}")
    aggregated[lead_name] = working.groupby(
      "forecast_kst_dtm",
      sort=True,
    )["_lead_hour"].first()

  aggregated = aggregated.reset_index()
  aggregated.attrs["weather_grid_profile"] = {
    "source": source,
    "prefix": resolved_prefix,
    "expected_grid_count": EXPECTED_GRID_COUNTS[source],
    "statistics": list(normalized_statistics),
    "std_ddof": std_ddof,
    "include_lead": bool(include_lead),
    "forecast_rows": int(len(aggregated)),
    "numeric_weather_features": int(len(value_columns)),
    "missing_cells_before_imputation": int(
      aggregated.drop(columns=["forecast_kst_dtm"]).isna().sum().sum()
    ),
    "all_grid_nan_policy": "preserve_nan",
  }
  return aggregated


def _validate_source_prefixes(source_prefixes):
  prefixes = tuple(source_prefixes)
  if len(prefixes) != 2:
    raise ValueError("source_prefixes는 LDAPS/GFS 두 값을 가져야 합니다")
  for prefix in prefixes:
    _validate_prefix(prefix)
  if prefixes[0] == prefixes[1]:
    raise ValueError(f"source prefix 충돌: {prefixes[0]!r}")
  return prefixes


def _require_matching_forecast_axis(ldaps_features, gfs_features):
  ldaps_axis = pd.Index(ldaps_features["forecast_kst_dtm"])
  gfs_axis = pd.Index(gfs_features["forecast_kst_dtm"])
  if not ldaps_axis.equals(gfs_axis):
    ldaps_only = int((~ldaps_axis.isin(gfs_axis)).sum())
    gfs_only = int((~gfs_axis.isin(ldaps_axis)).sum())
    raise ValueError(
      "LDAPS/GFS forecast 시각 drift: "
      f"ldaps_only={ldaps_only}, gfs_only={gfs_only}"
    )


def build_weather_features(
  ldaps_frame,
  gfs_frame,
  *,
  statistics=("mean",),
  include_lead=False,
  source_prefixes=("ldaps", "gfs"),
  std_ddof=STD_DDOF,
):
  """LDAPS 다음 GFS 순서로 forecast별 feature를 결합한다."""
  ldaps_prefix, gfs_prefix = _validate_source_prefixes(source_prefixes)
  ldaps_features = aggregate_weather_grid(
    ldaps_frame,
    source="ldaps",
    statistics=statistics,
    include_lead=include_lead,
    prefix=ldaps_prefix,
    std_ddof=std_ddof,
  )
  gfs_features = aggregate_weather_grid(
    gfs_frame,
    source="gfs",
    statistics=statistics,
    include_lead=include_lead,
    prefix=gfs_prefix,
    std_ddof=std_ddof,
  )
  _require_matching_forecast_axis(ldaps_features, gfs_features)

  duplicate_features = sorted(
    set(ldaps_features.columns[1:]).intersection(gfs_features.columns[1:])
  )
  if duplicate_features:
    raise ValueError(f"source prefix 충돌 또는 중복 feature 이름: {duplicate_features}")

  merged = ldaps_features.merge(
    gfs_features,
    on="forecast_kst_dtm",
    how="inner",
    sort=True,
    validate="one_to_one",
  )
  if merged.columns.duplicated().any():
    duplicate_columns = list(merged.columns[merged.columns.duplicated()])
    raise ValueError(f"결합 결과 중복 feature 이름: {duplicate_columns}")

  merged.attrs["weather_grid_profile"] = {
    "source_order": ["ldaps", "gfs"],
    "statistics": list(_validate_statistics(statistics, std_ddof)),
    "std_ddof": std_ddof,
    "include_lead": bool(include_lead),
    "missing_cells_before_imputation": int(
      merged.drop(columns=["forecast_kst_dtm"]).isna().sum().sum()
    ),
    "all_grid_nan_policy": "preserve_nan",
  }
  return merged


def _require_raw_schema_match(train_frame, test_frame, source):
  _validate_frame_columns(train_frame, f"{source}_train")
  _validate_frame_columns(test_frame, f"{source}_test")
  if tuple(train_frame.columns) != tuple(test_frame.columns):
    raise ValueError(
      f"{source} train/test 컬럼 이름 또는 순서 drift: "
      f"train={list(train_frame.columns)}, test={list(test_frame.columns)}"
    )

  train_columns = tuple(_numeric_weather_columns(train_frame, f"{source}_train"))
  test_columns = tuple(_numeric_weather_columns(test_frame, f"{source}_test"))
  if train_columns != test_columns:
    raise ValueError(
      f"{source} train/test 컬럼 이름 또는 순서 drift: "
      f"train={list(train_columns)}, test={list(test_columns)}"
    )


def build_weather_feature_pair(
  train_ldaps,
  train_gfs,
  test_ldaps,
  test_gfs,
  *,
  statistics=("mean",),
  include_lead=False,
  source_prefixes=("ldaps", "gfs"),
  std_ddof=STD_DDOF,
):
  """raw schema와 집계 schema가 동일한 train/test feature pair를 만든다."""
  _require_raw_schema_match(train_ldaps, test_ldaps, "ldaps")
  _require_raw_schema_match(train_gfs, test_gfs, "gfs")

  train_features = build_weather_features(
    train_ldaps,
    train_gfs,
    statistics=statistics,
    include_lead=include_lead,
    source_prefixes=source_prefixes,
    std_ddof=std_ddof,
  )
  test_features = build_weather_features(
    test_ldaps,
    test_gfs,
    statistics=statistics,
    include_lead=include_lead,
    source_prefixes=source_prefixes,
    std_ddof=std_ddof,
  )

  train_columns = tuple(train_features.columns[1:])
  test_columns = tuple(test_features.columns[1:])
  if train_columns != test_columns:
    raise ValueError(
      "집계 train/test 컬럼 이름 또는 순서 drift: "
      f"train={list(train_columns)}, test={list(test_columns)}"
    )
  return WeatherFeaturePair(
    train=train_features,
    test=test_features,
    feature_columns=train_columns,
  )


def _validate_feature_matrix(feature_frame, frame_name):
  if not isinstance(feature_frame, pd.DataFrame):
    raise TypeError(f"{frame_name}은 pandas DataFrame이어야 합니다")
  if feature_frame.empty:
    raise ValueError(f"{frame_name}이 비어 있습니다")
  duplicate_columns = list(feature_frame.columns[feature_frame.columns.duplicated()])
  if duplicate_columns:
    raise ValueError(f"{frame_name} 중복 feature 이름: {duplicate_columns}")
  non_numeric = [
    column
    for column in feature_frame.columns
    if not pd.api.types.is_numeric_dtype(feature_frame[column])
    or pd.api.types.is_bool_dtype(feature_frame[column])
  ]
  if non_numeric:
    raise ValueError(f"{frame_name} 숫자형이 아닌 feature: {non_numeric}")


def fit_train_median_imputer(train_features):
  """오직 train feature로 median imputer를 fit한다."""
  _validate_feature_matrix(train_features, "train_features")
  all_nan_columns = [
    column
    for column in train_features.columns
    if train_features[column].isna().all()
  ]
  if all_nan_columns:
    raise ValueError(f"train 전체가 결측인 feature: {all_nan_columns}")

  imputer = SimpleImputer(strategy="median")
  imputer.fit(train_features)
  if not np.isfinite(imputer.statistics_).all():
    raise ValueError("train median 통계에 유한하지 않은 값이 있습니다")
  return TrainMedianImputer(
    feature_columns=tuple(train_features.columns),
    imputer=imputer,
  )


__all__ = [
  "EXPECTED_GRID_COUNTS",
  "EXPECTED_LEAD_RANGE_HOURS",
  "SPATIAL_STATISTICS",
  "STD_DDOF",
  "TrainMedianImputer",
  "WEATHER_METADATA_COLUMNS",
  "WeatherFeaturePair",
  "aggregate_weather_grid",
  "build_weather_feature_pair",
  "build_weather_features",
  "fit_train_median_imputer",
]
