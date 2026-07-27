"""공식 `info.xlsx`에서 터빈 위치·용량 메타데이터를 읽는 모듈.

노트북 08 셀 안에만 있던 인라인 변환을 승격했다. 공간 pooling은 이 로더가
돌려주는 스키마를 그대로 받으므로, 좌표 규약이 바뀌면 여기 한 곳만 고친다.
"""

from __future__ import annotations

import math
from pathlib import Path
import re

import pandas as pd

from baram.features.turbine_spatial import TURBINE_LOCATION_COLUMNS


TURBINE_COUNT = 17
GROUP_TURBINE_COUNTS = {"group_1": 6, "group_2": 6, "group_3": 5}
GROUP_CAPACITY_MW = {"group_1": 21.6, "group_2": 21.6, "group_3": 21.0}

INFO_HEADER_MARKERS = ("제작사", "호기", "좌표(Google)", "KPX그룹", "설비용량(MW)")
MAX_HEADER_SCAN_ROWS = 20
CAPACITY_TOLERANCE_MW = 1e-6

_DMS_PATTERN = re.compile(
  r"^\s*(?P<latDegree>\d+)\s*°\s*(?P<latMinute>\d+)\s*'\s*(?P<latSecond>\d+(?:\.\d+)?)\s*\"\s*(?P<latHemisphere>[NS])"
  r"\s+(?P<lonDegree>\d+)\s*°\s*(?P<lonMinute>\d+)\s*'\s*(?P<lonSecond>\d+(?:\.\d+)?)\s*\"\s*(?P<lonHemisphere>[EW])\s*$"
)


def _to_decimal_degrees(degree, minute, second, hemisphere):
  if not 0 <= minute < 60 or not 0 <= second < 60:
    raise ValueError(
      f"좌표의 분/초는 0 이상 60 미만이어야 합니다: {degree}°{minute}'{second}\""
    )
  magnitude = degree + minute / 60.0 + second / 3600.0
  return -magnitude if hemisphere in ("S", "W") else magnitude


def parse_dms_coordinate(text):
  """`37°16'55.61"N 128°57'02.10"E` 형식을 (위도, 경도) 십진수로 변환한다."""
  if not isinstance(text, str):
    raise ValueError(f"좌표는 문자열이어야 합니다: {text!r}")

  matched = _DMS_PATTERN.match(text)
  if matched is None:
    raise ValueError(f"공식 DMS 좌표 형식이 아닙니다: {text!r}")

  latitude = _to_decimal_degrees(
    int(matched["latDegree"]),
    int(matched["latMinute"]),
    float(matched["latSecond"]),
    matched["latHemisphere"],
  )
  longitude = _to_decimal_degrees(
    int(matched["lonDegree"]),
    int(matched["lonMinute"]),
    float(matched["lonSecond"]),
    matched["lonHemisphere"],
  )
  return latitude, longitude


def _find_header_row(path):
  """제목·빈 줄이 몇 줄이든 헤더 마커가 모두 있는 행을 찾는다."""
  preview = pd.read_excel(path, header=None, nrows=MAX_HEADER_SCAN_ROWS)
  for position in range(len(preview)):
    values = {
      str(value).strip()
      for value in preview.iloc[position].tolist()
      if not pd.isna(value)
    }
    if all(marker in values for marker in INFO_HEADER_MARKERS):
      return position
  raise ValueError(
    f"info 워크북에서 헤더 행을 찾지 못했습니다. 필요한 마커={list(INFO_HEADER_MARKERS)}"
  )


def _normalize_group_id(value):
  text = str(value).strip()
  if text.startswith("group_"):
    return text
  return f"group_{int(float(text))}"


def _require_group_capacity(frame, declared):
  """터빈 용량 합과 공식 그룹 설비용량이 일치하는지 검증한다."""
  totals = frame.groupby("group_id")["capacity_mw"].sum().to_dict()
  for group_id, expected in GROUP_CAPACITY_MW.items():
    actual = totals.get(group_id)
    if actual is None or abs(actual - expected) > CAPACITY_TOLERANCE_MW:
      raise ValueError(
        f"{group_id} 터빈 설비용량 합이 공식값과 다릅니다: 합계={actual}, 공식={expected}"
      )
    stated = declared.get(group_id)
    if stated is not None and abs(stated - expected) > CAPACITY_TOLERANCE_MW:
      raise ValueError(
        f"{group_id} 그룹설비용량 표기가 공식값과 다릅니다: 표기={stated}, 공식={expected}"
      )


def load_turbine_locations(info_path):
  """공식 info 워크북을 공간 pooler가 요구하는 스키마로 정규화한다."""
  path = Path(info_path)
  if not path.is_file():
    raise FileNotFoundError(f"공식 info 워크북이 없습니다: {path}")

  raw = pd.read_excel(path, header=_find_header_row(path))
  raw.columns = [str(column).strip() for column in raw.columns]
  missing = [column for column in INFO_HEADER_MARKERS if column not in raw.columns]
  if missing:
    raise ValueError(f"info 워크북 헤더 컬럼 누락: {missing}")

  working = raw[raw["좌표(Google)"].notna()].reset_index(drop=True)
  if len(working) != TURBINE_COUNT:
    raise ValueError(
      f"터빈 수가 공식값과 다릅니다: 읽음={len(working)}, 공식={TURBINE_COUNT}"
    )

  if pd.isna(working.loc[0, "KPX그룹"]):
    raise ValueError("첫 터빈 행에 KPX그룹이 없어 전방 채움 기준을 잡을 수 없습니다")

  # 공식 파일은 그룹의 첫 터빈에만 KPX그룹과 그룹설비용량을 적어 두므로 전방 채움한다.
  group_series = working["KPX그룹"].ffill().map(_normalize_group_id)
  declared_capacity = {
    _normalize_group_id(group_value): float(capacity_value)
    for group_value, capacity_value in zip(working["KPX그룹"], working["그룹설비용량(MW)"])
    if not pd.isna(group_value) and not pd.isna(capacity_value)
  }

  coordinates = working["좌표(Google)"].map(parse_dms_coordinate)
  frame = pd.DataFrame(
    {
      "turbine_id": [
        f"{str(maker).strip()}-{int(unit):02d}"
        for maker, unit in zip(working["제작사"], working["호기"])
      ],
      "group_id": group_series,
      "latitude": [pair[0] for pair in coordinates],
      "longitude": [pair[1] for pair in coordinates],
      "capacity_mw": working["설비용량(MW)"].astype(float),
    }
  )

  if not frame["turbine_id"].is_unique:
    duplicated = frame.loc[frame["turbine_id"].duplicated(), "turbine_id"].tolist()
    raise ValueError(f"터빈 id가 중복됩니다: {duplicated}")

  counts = frame["group_id"].value_counts().to_dict()
  if counts != GROUP_TURBINE_COUNTS:
    raise ValueError(
      f"그룹별 터빈 수가 공식값과 다릅니다: 읽음={counts}, 공식={GROUP_TURBINE_COUNTS}"
    )

  if not all(math.isfinite(value) for value in frame["latitude"]):
    raise ValueError("위도에 유한하지 않은 값이 있습니다")
  if not all(math.isfinite(value) for value in frame["longitude"]):
    raise ValueError("경도에 유한하지 않은 값이 있습니다")

  _require_group_capacity(frame, declared_capacity)
  return frame[list(TURBINE_LOCATION_COLUMNS)]


__all__ = [
  "GROUP_CAPACITY_MW",
  "GROUP_TURBINE_COUNTS",
  "INFO_HEADER_MARKERS",
  "TURBINE_COUNT",
  "load_turbine_locations",
  "parse_dms_coordinate",
]
