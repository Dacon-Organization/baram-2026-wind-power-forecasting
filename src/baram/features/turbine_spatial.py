"""공식 터빈 위치와 NWP 격자 사이의 공간 pooling 계약."""

from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Real
import re

import numpy as np
import pandas as pd

from baram.features.weather_grid import (
  _validate_prefix,
  _validate_source,
  _validated_working_frame,
)


TURBINE_LOCATION_COLUMNS = (
  "turbine_id",
  "group_id",
  "latitude",
  "longitude",
  "capacity_mw",
)
SPATIAL_POOLING_METHODS = ("nearest", "idw")
DEFAULT_IDW_POWER = 2.0
EARTH_MEAN_RADIUS_KM = 6371.0088


def _validate_pooling_methods(pooling_methods):
  if isinstance(pooling_methods, str):
    requested = (pooling_methods,)
  else:
    try:
      requested = tuple(pooling_methods)
    except TypeError as error:
      raise ValueError("pooling_methods는 하나 이상의 method여야 합니다") from error

  if not requested:
    raise ValueError("pooling_methods는 하나 이상이어야 합니다")
  if len(set(requested)) != len(requested):
    raise ValueError(f"중복 pooling method: {list(requested)}")

  unsupported = [
    method
    for method in requested
    if method not in SPATIAL_POOLING_METHODS
  ]
  if unsupported:
    raise ValueError(f"지원하지 않는 pooling method: {unsupported}")

  return tuple(
    method
    for method in SPATIAL_POOLING_METHODS
    if method in requested
  )


def _validate_idw_power(idw_power):
  if (
    isinstance(idw_power, (bool, np.bool_))
    or not isinstance(idw_power, Real)
    or not np.isfinite(idw_power)
    or idw_power <= 0
  ):
    raise ValueError("idw_power는 0보다 큰 유한한 실수여야 합니다")
  return float(idw_power)


def _is_real_number(value):
  return (
    isinstance(value, Real)
    and not isinstance(value, (bool, np.bool_))
  )


def _validate_turbine_locations(turbine_locations):
  frame_name = "turbine_locations"
  if not isinstance(turbine_locations, pd.DataFrame):
    raise TypeError(f"{frame_name}는 pandas DataFrame이어야 합니다")
  if turbine_locations.empty:
    raise ValueError(f"{frame_name}가 비어 있습니다")

  duplicate_columns = list(
    turbine_locations.columns[turbine_locations.columns.duplicated()]
  )
  if duplicate_columns:
    raise ValueError(f"{frame_name} 중복 컬럼: {duplicate_columns}")

  missing_columns = [
    column
    for column in TURBINE_LOCATION_COLUMNS
    if column not in turbine_locations.columns
  ]
  if missing_columns:
    raise ValueError(
      f"{frame_name} 필수 metadata 컬럼 누락: {missing_columns}"
    )

  working = turbine_locations[list(TURBINE_LOCATION_COLUMNS)].copy()
  turbine_ids = working["turbine_id"]
  if turbine_ids.isna().any() or not turbine_ids.map(
    lambda value: isinstance(value, str) and bool(value.strip())
  ).all():
    raise ValueError("turbine_id는 비어 있지 않은 문자열이어야 합니다")
  if turbine_ids.duplicated().any():
    duplicates = sorted(turbine_ids[turbine_ids.duplicated(keep=False)].unique())
    raise ValueError(f"turbine_id 중복: {duplicates}")

  group_ids = working["group_id"]
  valid_group_ids = group_ids.map(
    lambda value: (
      isinstance(value, str)
      and re.fullmatch(r"group_[1-9][0-9]*", value) is not None
    )
  )
  if not valid_group_ids.all():
    invalid = sorted(group_ids[~valid_group_ids].astype(str).unique())
    raise ValueError(f"group_id 형식 위반: {invalid}")

  if working[["latitude", "longitude"]].isna().any().any():
    raise ValueError("터빈 좌표 결측")
  for column, lower, upper in (
    ("latitude", -90.0, 90.0),
    ("longitude", -180.0, 180.0),
  ):
    values = working[column]
    if not values.map(_is_real_number).all():
      raise ValueError(f"유효 범위를 벗어난 좌표: {column}")
    numeric_values = values.to_numpy(dtype=float)
    if (
      not np.isfinite(numeric_values).all()
      or (numeric_values < lower).any()
      or (numeric_values > upper).any()
    ):
      raise ValueError(f"유효 범위를 벗어난 좌표: {column}")
    working[column] = numeric_values

  capacities = working["capacity_mw"]
  if not capacities.map(_is_real_number).all():
    raise ValueError("capacity_mw는 0보다 큰 유한한 실수여야 합니다")
  numeric_capacities = capacities.to_numpy(dtype=float)
  if (
    not np.isfinite(numeric_capacities).all()
    or (numeric_capacities <= 0).any()
  ):
    raise ValueError("capacity_mw는 0보다 큰 유한한 실수여야 합니다")
  working["capacity_mw"] = numeric_capacities
  return working


def _validate_grid_coordinates(working, frame_name):
  for column, lower, upper in (
    ("latitude", -90.0, 90.0),
    ("longitude", -180.0, 180.0),
  ):
    values = working[column]
    if not values.map(_is_real_number).all():
      raise ValueError(f"{frame_name} grid 좌표가 숫자형이 아닙니다: {column}")
    numeric_values = values.to_numpy(dtype=float)
    if (
      not np.isfinite(numeric_values).all()
      or (numeric_values < lower).any()
      or (numeric_values > upper).any()
    ):
      raise ValueError(
        f"{frame_name} grid 유효 범위를 벗어난 좌표: {column}"
      )
    working[column] = numeric_values


def _grid_id_sort_key(grid_id):
  if _is_real_number(grid_id):
    return (0, float(grid_id), type(grid_id).__name__)
  return (1, type(grid_id).__name__, repr(grid_id))


def _ordered_geometry(rows, grid_ids):
  indexed = rows.set_index("grid_id")
  try:
    ordered = indexed.loc[list(grid_ids), ["latitude", "longitude"]]
  except KeyError as error:
    raise ValueError("forecast 사이 grid_id drift") from error
  return ordered.to_numpy(dtype=float)


def _fit_grid_geometry(working):
  first_forecast = working["forecast_kst_dtm"].min()
  reference_rows = working.loc[
    working["forecast_kst_dtm"] == first_forecast,
    ["grid_id", "latitude", "longitude"],
  ]
  grid_ids = tuple(
    sorted(reference_rows["grid_id"].tolist(), key=_grid_id_sort_key)
  )
  if working["grid_id"].nunique() != len(grid_ids):
    raise ValueError("forecast 사이 grid_id drift")

  coordinate_counts = working.groupby("grid_id", sort=False)[
    ["latitude", "longitude"]
  ].nunique(dropna=False)
  if coordinate_counts.ne(1).any().any():
    raise ValueError("forecast 사이 grid 좌표 drift")

  reference_geometry = _ordered_geometry(reference_rows, grid_ids)
  return grid_ids, reference_geometry


def _validate_transform_geometry(working, grid_ids, fitted_geometry):
  if set(working["grid_id"].unique()) != set(grid_ids):
    raise ValueError("fit/transform grid_id drift")

  coordinate_counts = working.groupby("grid_id", sort=False)[
    ["latitude", "longitude"]
  ].nunique(dropna=False)
  if coordinate_counts.ne(1).any().any():
    raise ValueError("fit/transform grid 좌표 drift")

  transform_geometry = (
    working[["grid_id", "latitude", "longitude"]]
    .drop_duplicates("grid_id")
  )
  geometry = _ordered_geometry(transform_geometry, grid_ids)
  if not np.array_equal(geometry, fitted_geometry):
    raise ValueError("fit/transform grid 좌표 drift")


def _haversine_distance_matrix(turbines, grid_geometry):
  turbine_latitude = np.radians(
    turbines["latitude"].to_numpy(dtype=float)
  )[:, None]
  turbine_longitude = np.radians(
    turbines["longitude"].to_numpy(dtype=float)
  )[:, None]
  grid_latitude = np.radians(grid_geometry[:, 0])[None, :]
  grid_longitude = np.radians(grid_geometry[:, 1])[None, :]

  latitude_delta = grid_latitude - turbine_latitude
  longitude_delta = grid_longitude - turbine_longitude
  haversine = (
    np.sin(latitude_delta / 2.0) ** 2
    + np.cos(turbine_latitude)
    * np.cos(grid_latitude)
    * np.sin(longitude_delta / 2.0) ** 2
  )
  angular_distance = 2.0 * np.arcsin(
    np.sqrt(np.clip(haversine, 0.0, 1.0))
  )
  return EARTH_MEAN_RADIUS_KM * angular_distance


def _nearest_weights(distances):
  minimum_distances = distances.min(axis=1, keepdims=True)
  nearest = np.isclose(
    distances,
    minimum_distances,
    rtol=1e-12,
    atol=1e-12,
  )
  return nearest / nearest.sum(axis=1, keepdims=True)


def _idw_weights(distances, idw_power):
  weights = np.zeros_like(distances, dtype=float)
  exact_matches = distances == 0.0
  has_exact_match = exact_matches.any(axis=1)

  if has_exact_match.any():
    matched = exact_matches[has_exact_match]
    weights[has_exact_match] = matched / matched.sum(axis=1, keepdims=True)

  without_exact_match = ~has_exact_match
  if without_exact_match.any():
    nonzero_distances = distances[without_exact_match]
    scaled_inverse_distance = np.power(
      nonzero_distances.min(axis=1, keepdims=True) / nonzero_distances,
      idw_power,
    )
    weights[without_exact_match] = (
      scaled_inverse_distance
      / scaled_inverse_distance.sum(axis=1, keepdims=True)
    )
  return weights


def _group_sort_key(group_id):
  return int(group_id.removeprefix("group_"))


def _fit_group_weights(
  turbines,
  grid_geometry,
  group_ids,
  pooling_methods,
  idw_power,
):
  distances = _haversine_distance_matrix(turbines, grid_geometry)
  turbine_weights = {}
  if "nearest" in pooling_methods:
    turbine_weights["nearest"] = _nearest_weights(distances)
  if "idw" in pooling_methods:
    turbine_weights["idw"] = _idw_weights(distances, idw_power)

  rows = []
  turbine_groups = turbines["group_id"].to_numpy()
  capacities = turbines["capacity_mw"].to_numpy(dtype=float)
  for group_id in group_ids:
    group_mask = turbine_groups == group_id
    group_capacity = capacities[group_mask]
    capacity_weights = group_capacity / group_capacity.sum()
    for method in pooling_methods:
      group_weights = capacity_weights @ turbine_weights[method][group_mask]
      group_weights = group_weights / group_weights.sum()
      rows.append(tuple(float(value) for value in group_weights))
  return tuple(rows)


def _weighted_pool(values, weights):
  available = ~np.isnan(values)
  weighted_values = np.where(available, values, 0.0) * weights
  numerator = weighted_values.sum(axis=1)
  denominator = (available * weights).sum(axis=1)
  pooled = np.full(len(values), np.nan, dtype=float)
  np.divide(numerator, denominator, out=pooled, where=denominator > 0.0)
  return pooled


@dataclass(frozen=True)
class TurbineSpatialPooler:
  """train grid geometry에 fit한 터빈 그룹별 공간 pooler."""

  source: str
  prefix: str
  pooling_methods: tuple[str, ...]
  group_ids: tuple[str, ...]
  raw_feature_columns: tuple[str, ...]
  feature_columns: tuple[str, ...]
  idw_power: float
  _raw_schema: tuple[object, ...] = field(repr=False)
  _grid_ids: tuple[object, ...] = field(repr=False)
  _grid_geometry: tuple[tuple[float, float], ...] = field(repr=False)
  _group_weights: tuple[tuple[float, ...], ...] = field(repr=False)

  def transform(self, weather_frame: pd.DataFrame) -> pd.DataFrame:
    """fit 당시 schema와 geometry가 같은 weather frame만 변환한다."""
    if not isinstance(weather_frame, pd.DataFrame):
      raise TypeError("weather_frame은 pandas DataFrame이어야 합니다")
    if tuple(weather_frame.columns) != self._raw_schema:
      raise ValueError(
        "fit/transform 컬럼 이름 또는 순서 drift: "
        f"fit={list(self._raw_schema)}, transform={list(weather_frame.columns)}"
      )

    working, value_columns = _validated_working_frame(
      weather_frame,
      self.source,
    )
    if tuple(value_columns) != self.raw_feature_columns:
      raise ValueError(
        "fit/transform 컬럼 이름 또는 순서 drift: "
        "숫자형 weather feature 계약이 달라졌습니다"
      )
    _validate_grid_coordinates(working, f"{self.source}_weather")

    fitted_geometry = np.asarray(self._grid_geometry, dtype=float)
    _validate_transform_geometry(
      working,
      self._grid_ids,
      fitted_geometry,
    )

    forecast_axis = pd.Index(
      sorted(working["forecast_kst_dtm"].unique()),
      name="forecast_kst_dtm",
    )
    result_columns = {"forecast_kst_dtm": forecast_axis}
    weight_rows = [
      np.asarray(weights, dtype=float)
      for weights in self._group_weights
    ]
    for raw_feature in self.raw_feature_columns:
      pivoted = working.pivot(
        index="forecast_kst_dtm",
        columns="grid_id",
        values=raw_feature,
      ).reindex(index=forecast_axis, columns=list(self._grid_ids))
      values = pivoted.to_numpy(dtype=float, na_value=np.nan)
      weight_index = 0
      for group_id in self.group_ids:
        for method in self.pooling_methods:
          feature_name = f"{self.prefix}_{raw_feature}_{group_id}_{method}"
          result_columns[feature_name] = _weighted_pool(
            values,
            weight_rows[weight_index],
          )
          weight_index += 1

    return pd.DataFrame(result_columns).reset_index(drop=True)


def fit_turbine_spatial_pooler(
  train_weather,
  turbine_locations,
  *,
  source,
  pooling_methods=SPATIAL_POOLING_METHODS,
  idw_power=DEFAULT_IDW_POWER,
  prefix=None,
):
  """train weather geometry와 공식 터빈 위치로 결정적 가중치를 fit한다."""
  _validate_source(source)
  resolved_prefix = source if prefix is None else prefix
  _validate_prefix(resolved_prefix)
  normalized_methods = _validate_pooling_methods(pooling_methods)
  normalized_idw_power = _validate_idw_power(idw_power)
  turbines = _validate_turbine_locations(turbine_locations)

  working, value_columns = _validated_working_frame(train_weather, source)
  _validate_grid_coordinates(working, f"{source}_weather")
  grid_ids, grid_geometry = _fit_grid_geometry(working)

  group_ids = tuple(
    sorted(turbines["group_id"].unique(), key=_group_sort_key)
  )
  feature_columns = tuple(
    f"{resolved_prefix}_{raw_feature}_{group_id}_{method}"
    for raw_feature in value_columns
    for group_id in group_ids
    for method in normalized_methods
  )
  group_weights = _fit_group_weights(
    turbines,
    grid_geometry,
    group_ids,
    normalized_methods,
    normalized_idw_power,
  )

  return TurbineSpatialPooler(
    source=source,
    prefix=resolved_prefix,
    pooling_methods=normalized_methods,
    group_ids=group_ids,
    raw_feature_columns=tuple(value_columns),
    feature_columns=feature_columns,
    idw_power=normalized_idw_power,
    _raw_schema=tuple(train_weather.columns),
    _grid_ids=grid_ids,
    _grid_geometry=tuple(
      (float(latitude), float(longitude))
      for latitude, longitude in grid_geometry
    ),
    _group_weights=group_weights,
  )


__all__ = [
  "DEFAULT_IDW_POWER",
  "SPATIAL_POOLING_METHODS",
  "TURBINE_LOCATION_COLUMNS",
  "TurbineSpatialPooler",
  "fit_turbine_spatial_pooler",
]
