"""피처셋을 1급 config로 표현하는 모듈.

노트북 랩에서 검증한 피처 조합을 production 파이프라인에서 선택할 수 있도록
named preset과 YAML 부분 오버라이드를 제공한다. 기본값은 공식 baseline과 동일한
`official_mean`이므로, 인자 없이 사용하면 승격 전과 같은 전처리가 유지된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import numbers
from pathlib import Path

import yaml

from baram.features.turbine_spatial import DEFAULT_IDW_POWER, SPATIAL_POOLING_METHODS
from baram.features.weather_grid import SPATIAL_STATISTICS


SPATIAL_SCOPES = ("all_group", "own_group")
DEFAULT_FEATURE_SET = "official_mean"

_FLOAT_FORMAT = ".10g"
_YAML_TOP_LEVEL_KEYS = ("extends", "overrides")


def _ordered_subset(values, allowed, label, korean_label):
  """허용값의 순서를 유지한 부분집합인지 검사하고 tuple로 정규화한다."""
  if isinstance(values, (str, bytes)):
    raise TypeError(f"{label}은 문자열이 아니라 순서열이어야 합니다")
  try:
    normalized = tuple(values)
  except TypeError as error:
    raise TypeError(f"{label}은 순서열이어야 합니다") from error
  if not normalized:
    raise ValueError(f"{label}은 하나 이상의 값을 가져야 합니다")

  unknown = [value for value in normalized if value not in allowed]
  if unknown:
    raise ValueError(
      f"지원하지 않는 {korean_label} 값: {unknown}; 허용값={list(allowed)}"
    )

  expected = tuple(value for value in allowed if value in set(normalized))
  if normalized != expected:
    raise ValueError(
      f"{label} 순서는 {list(allowed)} 순서를 유지한 부분집합이어야 합니다: {list(normalized)}"
    )
  return normalized


def _require_bool(value, label):
  if not isinstance(value, bool):
    raise TypeError(f"{label}은 bool이어야 합니다: {value!r}")
  return value


@dataclass(frozen=True)
class SpatialPoolingConfig:
  """터빈 공간 pooling 방식과 사용 범위."""

  methods: tuple[str, ...]
  idw_power: float = DEFAULT_IDW_POWER
  scope: str = "all_group"

  def __post_init__(self):
    object.__setattr__(
      self,
      "methods",
      _ordered_subset(
        self.methods,
        SPATIAL_POOLING_METHODS,
        "methods",
        "pooling method",
      ),
    )

    power = self.idw_power
    if (
      isinstance(power, bool)
      or not isinstance(power, numbers.Real)
      or power != power
      or power in (float("inf"), float("-inf"))
      or power <= 0
    ):
      raise ValueError(f"idw_power는 0보다 큰 유한한 실수여야 합니다: {power!r}")
    object.__setattr__(self, "idw_power", float(power))

    if self.scope not in SPATIAL_SCOPES:
      raise ValueError(
        f"지원하지 않는 pooling scope: {self.scope!r}; 허용값={list(SPATIAL_SCOPES)}"
      )


@dataclass(frozen=True)
class FeatureSetConfig:
  """train/inference가 공유하는 피처 조합 계약."""

  name: str
  statistics: tuple[str, ...] = ("mean",)
  include_lead: bool = False
  wind_vector: bool = False
  spatial: SpatialPoolingConfig | None = None
  calendar: bool = True

  def __post_init__(self):
    if not isinstance(self.name, str) or not self.name.strip():
      raise ValueError(f"name은 비어 있지 않은 문자열이어야 합니다: {self.name!r}")
    object.__setattr__(self, "name", self.name.strip())
    object.__setattr__(
      self,
      "statistics",
      _ordered_subset(self.statistics, SPATIAL_STATISTICS, "statistics", "통계"),
    )
    _require_bool(self.include_lead, "include_lead")
    _require_bool(self.wind_vector, "wind_vector")
    _require_bool(self.calendar, "calendar")
    if self.spatial is not None and not isinstance(self.spatial, SpatialPoolingConfig):
      raise TypeError(
        f"spatial은 SpatialPoolingConfig 또는 None이어야 합니다: {type(self.spatial).__name__}"
      )

  @property
  def uses_spatial(self):
    """공간 pooling을 쓰는지 여부. True면 터빈 좌표가 반드시 필요하다."""
    return self.spatial is not None


@dataclass(frozen=True)
class ResolvedFeatureSet:
  """해석이 끝난 config와 출처, 정규화 hash."""

  config: FeatureSetConfig
  source: str
  sha256: str = field(compare=False)


FEATURE_SETS = {
  "official_mean": FeatureSetConfig(name="official_mean"),
  "expanded_vector": FeatureSetConfig(
    name="expanded_vector",
    statistics=SPATIAL_STATISTICS,
    include_lead=True,
    wind_vector=True,
  ),
  "spatial_idw2_all_group": FeatureSetConfig(
    name="spatial_idw2_all_group",
    statistics=SPATIAL_STATISTICS,
    include_lead=True,
    wind_vector=True,
    spatial=SpatialPoolingConfig(methods=("idw",), idw_power=2.0, scope="all_group"),
  ),
  "spatial_nearest_own_group": FeatureSetConfig(
    name="spatial_nearest_own_group",
    statistics=SPATIAL_STATISTICS,
    include_lead=True,
    wind_vector=True,
    spatial=SpatialPoolingConfig(methods=("nearest",), scope="own_group"),
  ),
}


def get_feature_set(name):
  """등록된 프리셋을 이름으로 가져온다."""
  if name not in FEATURE_SETS:
    raise ValueError(
      f"알 수 없는 피처셋 이름: {name!r}; 허용값={sorted(FEATURE_SETS)}"
    )
  return FEATURE_SETS[name]


def feature_set_to_dict(config):
  """hash와 metadata 기록에 쓰는 정규화 dict를 만든다.

  float는 포맷 문자열로 고정해 플랫폼별 repr 차이가 hash를 흔들지 않게 한다.
  """
  if not isinstance(config, FeatureSetConfig):
    raise TypeError("config는 FeatureSetConfig여야 합니다")
  spatial = None
  if config.spatial is not None:
    spatial = {
      "methods": list(config.spatial.methods),
      "idw_power": format(config.spatial.idw_power, _FLOAT_FORMAT),
      "scope": config.spatial.scope,
    }
  return {
    "name": config.name,
    "statistics": list(config.statistics),
    "include_lead": config.include_lead,
    "wind_vector": config.wind_vector,
    "spatial": spatial,
    "calendar": config.calendar,
  }


def feature_set_canonical_json(config):
  """정렬·구분자를 고정한 정규화 JSON 문자열.

  `name`은 의도적으로 제외한다. hash가 식별하는 대상은 라벨이 아니라 전처리 의미이며,
  같은 전처리라면 preset 경로든 YAML 경로든 같은 hash가 나와야 하기 때문이다.
  """
  payload = feature_set_to_dict(config)
  payload.pop("name")
  return json.dumps(
    payload,
    sort_keys=True,
    ensure_ascii=False,
    separators=(",", ":"),
  )


def feature_set_sha256(config):
  """정규화 JSON의 SHA-256. preset 경로와 YAML 경로가 같은 값을 낸다."""
  return hashlib.sha256(feature_set_canonical_json(config).encode("utf-8")).hexdigest()


def _require_known_keys(mapping, allowed, label):
  unknown = sorted(set(mapping) - set(allowed))
  if unknown:
    raise ValueError(f"{label}에 알 수 없는 키: {unknown}; 허용값={sorted(allowed)}")


def _merge_spatial(base, override):
  """spatial만 부분 병합한다. None을 주면 공간 피처를 끈다."""
  if override is None:
    return None
  if not isinstance(override, dict):
    raise ValueError("spatial 오버라이드는 매핑이거나 null이어야 합니다")
  _require_known_keys(override, ("methods", "idw_power", "scope"), "spatial 오버라이드")

  if base is None:
    if "methods" not in override:
      raise ValueError(
        "상속한 프리셋에 spatial이 없으므로 methods를 함께 지정해야 합니다"
      )
    merged = {"methods": override["methods"]}
  else:
    merged = {
      "methods": base.methods,
      "idw_power": base.idw_power,
      "scope": base.scope,
    }
  merged.update(override)
  return SpatialPoolingConfig(**merged)


def load_feature_set_config(config_path):
  """`extends` 기반 YAML 오버라이드를 해석해 최종 config를 만든다."""
  path = Path(config_path)
  if not path.is_file():
    raise FileNotFoundError(f"피처셋 config 파일이 없습니다: {path}")

  document = yaml.safe_load(path.read_text(encoding="utf-8"))
  if not isinstance(document, dict):
    raise ValueError(f"피처셋 config는 최상위가 매핑이어야 합니다: {path}")
  _require_known_keys(document, _YAML_TOP_LEVEL_KEYS, "피처셋 config")

  base_name = document.get("extends")
  if not isinstance(base_name, str) or not base_name.strip():
    raise ValueError("피처셋 config에는 상속할 프리셋 이름을 extends로 지정해야 합니다")
  base = get_feature_set(base_name.strip())

  overrides = document.get("overrides") or {}
  if not isinstance(overrides, dict):
    raise ValueError("overrides는 매핑이어야 합니다")
  allowed = ("name", "statistics", "include_lead", "wind_vector", "spatial", "calendar")
  _require_known_keys(overrides, allowed, "overrides")

  values = {
    "name": overrides.get("name", f"{base.name}+{path.stem}"),
    "statistics": overrides.get("statistics", base.statistics),
    "include_lead": overrides.get("include_lead", base.include_lead),
    "wind_vector": overrides.get("wind_vector", base.wind_vector),
    "calendar": overrides.get("calendar", base.calendar),
    "spatial": (
      _merge_spatial(base.spatial, overrides["spatial"])
      if "spatial" in overrides
      else base.spatial
    ),
  }
  return FeatureSetConfig(**values)


def resolve_feature_set(*, name=None, config_path=None):
  """프리셋 이름 또는 YAML 경로 하나로 config를 확정한다."""
  if name is not None and config_path is not None:
    raise ValueError("--feature-set과 --feature-set-config는 동시에 지정할 수 없습니다")

  if config_path is not None:
    config = load_feature_set_config(config_path)
    source = f"yaml:{Path(config_path).name}"
  else:
    config = get_feature_set(DEFAULT_FEATURE_SET if name is None else name)
    source = "preset"

  return ResolvedFeatureSet(
    config=config,
    source=source,
    sha256=feature_set_sha256(config),
  )


__all__ = [
  "DEFAULT_FEATURE_SET",
  "FEATURE_SETS",
  "FeatureSetConfig",
  "ResolvedFeatureSet",
  "SPATIAL_SCOPES",
  "SpatialPoolingConfig",
  "feature_set_canonical_json",
  "feature_set_sha256",
  "feature_set_to_dict",
  "get_feature_set",
  "load_feature_set_config",
  "resolve_feature_set",
]
