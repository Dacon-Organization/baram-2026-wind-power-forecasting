"""U/V 바람 성분에서 풍속과 순환형 풍향 feature를 파생한다."""

from __future__ import annotations

from dataclasses import dataclass
import numbers
import re

import numpy as np
import pandas as pd


DEFAULT_CALM_SPEED_THRESHOLD = 1e-6


@dataclass(frozen=True)
class WindVectorSpec:
  """동시에 관측된 U/V 성분 한 쌍의 파생 규격."""

  name: str
  u_column: str
  v_column: str


DEFAULT_WIND_VECTOR_SPECS = {
  "ldaps": (
    WindVectorSpec(
      "10m",
      "heightAboveGround_10_10u",
      "heightAboveGround_10_10v",
    ),
  ),
  "gfs": (
    WindVectorSpec(
      "10m",
      "heightAboveGround_10_10u",
      "heightAboveGround_10_10v",
    ),
    WindVectorSpec(
      "80m",
      "heightAboveGround_80_u",
      "heightAboveGround_80_v",
    ),
    WindVectorSpec(
      "100m",
      "heightAboveGround_100_100u",
      "heightAboveGround_100_100v",
    ),
  ),
}


def derive_wind_vector_features(
  frame,
  *,
  source,
  component_specs=None,
  calm_speed_threshold=DEFAULT_CALM_SPEED_THRESHOLD,
):
  """원시 grid 행마다 풍속과 meteorological wind-from sin/cos를 덧붙인다."""
  if source not in DEFAULT_WIND_VECTOR_SPECS:
    raise ValueError(
      f"지원하지 않는 weather source: {source!r}; "
      f"허용값={list(DEFAULT_WIND_VECTOR_SPECS)}"
    )
  if not isinstance(frame, pd.DataFrame):
    raise TypeError("frame은 pandas DataFrame이어야 합니다")
  if frame.empty:
    raise ValueError("frame은 비어 있을 수 없습니다")

  duplicateColumns = list(frame.columns[frame.columns.duplicated()])
  if duplicateColumns:
    raise ValueError(f"입력 중복 컬럼: {duplicateColumns}")
  if (
    isinstance(calm_speed_threshold, bool)
    or not isinstance(calm_speed_threshold, numbers.Real)
    or not np.isfinite(calm_speed_threshold)
    or calm_speed_threshold < 0
  ):
    raise ValueError(
      "calm_speed_threshold는 0 이상의 유한한 실수여야 합니다"
    )

  specs = (
    DEFAULT_WIND_VECTOR_SPECS[source]
    if component_specs is None
    else tuple(component_specs)
  )
  if not specs:
    raise ValueError("component_specs는 하나 이상의 U/V 쌍을 가져야 합니다")

  derivedNames = []
  requiredColumns = []
  for spec in specs:
    if not isinstance(spec, WindVectorSpec):
      raise TypeError("component_specs의 원소는 WindVectorSpec이어야 합니다")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_]*", spec.name):
      raise ValueError(f"wind vector 규격 이름 형식 위반: {spec.name!r}")
    if spec.u_column == spec.v_column:
      raise ValueError(f"U/V 컬럼은 서로 달라야 합니다: {spec.name!r}")
    requiredColumns.extend([spec.u_column, spec.v_column])
    derivedNames.extend(
      [
        f"windvec_{spec.name}_speed",
        f"windvec_{spec.name}_from_sin",
        f"windvec_{spec.name}_from_cos",
      ]
    )

  duplicateDerivedNames = sorted(
    name for name in set(derivedNames) if derivedNames.count(name) > 1
  )
  if duplicateDerivedNames:
    raise ValueError(f"중복 파생 feature 이름: {duplicateDerivedNames}")
  nameCollisions = [name for name in derivedNames if name in frame.columns]
  if nameCollisions:
    raise ValueError(f"파생 feature 이름 충돌: {nameCollisions}")

  missingColumns = [
    column for column in dict.fromkeys(requiredColumns) if column not in frame.columns
  ]
  if missingColumns:
    raise ValueError(f"필수 U/V 컬럼 누락: {missingColumns}")

  invalidDtypes = [
    column
    for column in dict.fromkeys(requiredColumns)
    if not pd.api.types.is_numeric_dtype(frame[column])
    or pd.api.types.is_bool_dtype(frame[column])
    or pd.api.types.is_complex_dtype(frame[column])
  ]
  if invalidDtypes:
    raise ValueError(f"실수형이 아닌 U/V 컬럼: {invalidDtypes}")
  infiniteColumns = [
    column
    for column in dict.fromkeys(requiredColumns)
    if np.isinf(frame[column].to_numpy(dtype=float)).any()
  ]
  if infiniteColumns:
    raise ValueError(f"무한값이 있는 U/V 컬럼: {infiniteColumns}")

  result = frame.copy(deep=True)
  for spec in specs:
    uValues = frame[spec.u_column].to_numpy(dtype=float)
    vValues = frame[spec.v_column].to_numpy(dtype=float)
    speed = np.hypot(uValues, vValues)
    directionIsDefined = (
      np.isfinite(uValues)
      & np.isfinite(vValues)
      & (speed > calm_speed_threshold)
    )
    fromSin = np.full(len(frame), np.nan, dtype=float)
    fromCos = np.full(len(frame), np.nan, dtype=float)
    np.divide(-uValues, speed, out=fromSin, where=directionIsDefined)
    np.divide(-vValues, speed, out=fromCos, where=directionIsDefined)

    result[f"windvec_{spec.name}_speed"] = speed
    result[f"windvec_{spec.name}_from_sin"] = fromSin
    result[f"windvec_{spec.name}_from_cos"] = fromCos

  return result


__all__ = [
  "DEFAULT_CALM_SPEED_THRESHOLD",
  "DEFAULT_WIND_VECTOR_SPECS",
  "WindVectorSpec",
  "derive_wind_vector_features",
]
