"""모델 metadata sidecar와 run registry를 관리한다."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import pickle
import platform
import tempfile
from typing import Any, Mapping

import numpy as np
import pandas as pd
import sklearn

from baram.feature_config import (
  DEFAULT_FEATURE_SET,
  FeatureSetConfig,
  feature_set_sha256,
  get_feature_set,
)
from baram.features.wind_vector import DEFAULT_WIND_VECTOR_SPECS
from baram.metrics import CAPACITY_KWH, TARGET_COLS
from baram.reproducibility import (
  normalize_created_at_kst,
  sha256_text,
  slugify_experiment_id,
  stable_json_dumps,
)


MODEL_METADATA_SCHEMA_VERSION = "1.1"
LEGACY_METADATA_SCHEMA_VERSIONS = ("1.0",)
MODEL_METADATA_ENCODING = "utf-8"
REGISTRY_ENCODING = "utf-8-sig"

PREPROCESSING_CONTRACT = {
  "weather_cutoff": {
    "rule": "data_available_kst_dtm <= forecast_kst_dtm",
    "on_violation": "fail",
  },
  "weather_aggregation": {
    "group_key": "forecast_kst_dtm",
    "statistics": ["mean"],
    "source_prefixes": ["ldaps", "gfs"],
    "excluded_columns": [
      "data_available_kst_dtm",
      "grid_id",
      "latitude",
      "longitude",
    ],
  },
  "lead_feature": {
    "formula": "forecast_kst_dtm - data_available_kst_dtm",
    "unit": "hour",
    "aggregation": "first",
  },
  "calendar_features": [
    "month",
    "day",
    "hour",
    "dayofweek",
    "is_weekend",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
  ],
  "missing_values": {
    "transformer": "sklearn.impute.SimpleImputer",
    "strategy": "median",
    "fit_scope": "training feature matrix",
  },
  "target_training": {
    "mask": "target-specific non-null labels",
    "models": "one model per target",
  },
  "prediction_bounds": {
    "lower": 0,
    "upper": CAPACITY_KWH,
  },
}

_WEATHER_EXCLUDED_COLUMNS = [
  "data_available_kst_dtm",
  "grid_id",
  "latitude",
  "longitude",
]
_CALENDAR_FEATURES = [
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


def build_preprocessing_contract(feature_set=None):
  """피처셋 config에서 전처리 계약을 파생한다.

  하드코딩 상수를 두면 전처리가 바뀌어도 `preprocessing_sha256`가 같아져서
  재현성 레이어가 거짓 신호를 낸다. `official_mean`에 대해서는 legacy
  `PREPROCESSING_CONTRACT`와 완전히 같은 dict를 돌려주며, 이 등가성은
  golden 테스트로 잠근다.
  """
  config = get_feature_set(DEFAULT_FEATURE_SET) if feature_set is None else feature_set
  if not isinstance(config, FeatureSetConfig):
    raise TypeError("feature_set은 FeatureSetConfig여야 합니다")

  contract = {
    "weather_cutoff": {
      "rule": "data_available_kst_dtm <= forecast_kst_dtm",
      "on_violation": "fail",
    },
    "weather_aggregation": {
      "group_key": "forecast_kst_dtm",
      "statistics": list(config.statistics),
      "source_prefixes": ["ldaps", "gfs"],
      "excluded_columns": list(_WEATHER_EXCLUDED_COLUMNS),
    },
  }

  if config.include_lead:
    contract["lead_feature"] = {
      "formula": "forecast_kst_dtm - data_available_kst_dtm",
      "unit": "hour",
      "aggregation": "first",
    }

  if config.wind_vector:
    contract["wind_vector"] = {
      "derived_from": "raw grid rows before aggregation",
      "components": ["speed", "wind_from_sin", "wind_from_cos"],
      "specs": {
        source: [spec.name for spec in specs]
        for source, specs in sorted(DEFAULT_WIND_VECTOR_SPECS.items())
      },
    }

  if config.spatial is not None:
    contract["spatial_pooling"] = {
      "methods": list(config.spatial.methods),
      "idw_power": config.spatial.idw_power,
      "scope": config.spatial.scope,
      "weights": "haversine distance, turbine capacity weighted within group",
      "fit_scope": "training weather grid geometry",
    }

  if config.calendar:
    contract["calendar_features"] = list(_CALENDAR_FEATURES)

  contract["missing_values"] = {
    "transformer": "sklearn.impute.SimpleImputer",
    "strategy": "median",
    "fit_scope": "training feature matrix",
  }
  contract["target_training"] = {
    "mask": "target-specific non-null labels",
    "models": "one model per target",
  }
  contract["prediction_bounds"] = {
    "lower": 0,
    "upper": CAPACITY_KWH,
  }
  return contract


def build_feature_set_record(resolved=None, pipeline=None):
  """metadata sidecar에 남길 피처셋 블록을 만든다."""
  if resolved is None:
    return {
      "name": DEFAULT_FEATURE_SET,
      "source": "legacy",
      "resolved_sha256": feature_set_sha256(get_feature_set(DEFAULT_FEATURE_SET)),
      "scope": None,
      "feature_count": None,
      "target_feature_counts": {},
    }

  config = resolved.config
  return {
    "name": config.name,
    "source": resolved.source,
    "resolved_sha256": resolved.sha256,
    "scope": None if config.spatial is None else config.spatial.scope,
    "feature_count": None if pipeline is None else len(pipeline.feature_columns),
    "target_feature_counts": (
      {}
      if pipeline is None
      else {
        target: len(columns)
        for target, columns in sorted(pipeline.target_feature_columns.items())
      }
    ),
  }


RUN_REGISTRY_COLUMNS = [
  "created_at_kst",
  "run_id",
  "experiment_id",
  "status",
  "git_commit",
  "seed",
  "config_sha256",
  "data_manifest_sha256",
  "data_profile_sha256",
  "preprocessing_sha256",
  "feature_schema_sha256",
  "split_name",
  "train_start_kst",
  "train_end_kst",
  "validation_start_kst",
  "validation_end_kst",
  "total_score",
  "one_minus_nmae",
  "ficr",
  "label_rows",
  "feature_rows",
  "feature_count",
  "target_train_rows",
  "model_type",
  "model_filename",
  "model_sha256",
  "model_bytes",
  "metadata_filename",
  "metadata_sha256",
  "submission_filename",
  "submission_sha256",
  "submission_rows",
  "submission_encoding",
  "public_score",
  "dacon_submission_id",
  "selected",
  "note",
]

_VALIDATION_SCORE_FIELDS = ["total_score", "one_minus_nmae", "ficr"]


@dataclass(frozen=True)
class ModelArtifact:
  """메모리에서 검증을 마친 모델과 metadata canonical bytes."""

  model_bytes: bytes
  model_sha256: str
  metadata: dict[str, Any]
  metadata_bytes: bytes
  metadata_sha256: str


@dataclass(frozen=True)
class SavedModelArtifact:
  """명시적 저장으로 생성된 model/sidecar 경로와 hash."""

  model_path: Path
  metadata_path: Path
  model_sha256: str
  metadata_sha256: str


def _require_columns(frame, required_columns, frame_name):
  missing = [column for column in required_columns if column not in frame.columns]
  if missing:
    raise ValueError(f"{frame_name} 필수 컬럼 누락: {missing}")


def _require_sha256(value, field_name):
  text = str(value or "").strip().lower()
  if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
    raise ValueError(f"{field_name}는 64자리 SHA256이어야 합니다")
  return text


def _timestamp_text(value):
  timestamp = pd.Timestamp(value)
  if pd.isna(timestamp):
    raise ValueError("timestamp가 비어 있습니다")
  return timestamp.isoformat(sep=" ")


def _frame_period(frame, column):
  timestamp = pd.to_datetime(frame[column], errors="raise")
  return {
    "start_kst": _timestamp_text(timestamp.min()),
    "end_kst": _timestamp_text(timestamp.max()),
  }


def _weather_profile(frame, source_name):
  required = [
    "forecast_kst_dtm",
    "data_available_kst_dtm",
    "grid_id",
    "latitude",
    "longitude",
  ]
  _require_columns(frame, required, source_name)
  forecast_time = pd.to_datetime(frame["forecast_kst_dtm"], errors="raise")
  available_time = pd.to_datetime(frame["data_available_kst_dtm"], errors="raise")
  cutoff_violation = available_time > forecast_time
  if cutoff_violation.any():
    raise ValueError(
      f"{source_name} cutoff 위반: 사용 가능 시각이 예보 대상 시각보다 늦은 행 "
      f"{int(cutoff_violation.sum())}개"
    )

  lead_hour = (forecast_time - available_time).dt.total_seconds() / 3600
  grid_count = frame.assign(_forecast_time=forecast_time).groupby("_forecast_time")["grid_id"].nunique()
  row_count = frame.assign(_forecast_time=forecast_time).groupby("_forecast_time").size()
  metadata_columns = set(required)
  value_columns = [
    column
    for column in frame.columns
    if column not in metadata_columns and pd.api.types.is_numeric_dtype(frame[column])
  ]
  if not value_columns:
    raise ValueError(f"{source_name} 숫자형 weather feature가 없습니다")

  return {
    "rows": int(len(frame)),
    "columns": int(len(frame.columns)),
    "forecast_rows": int(forecast_time.nunique()),
    "forecast_start_kst": _timestamp_text(forecast_time.min()),
    "forecast_end_kst": _timestamp_text(forecast_time.max()),
    "available_start_kst": _timestamp_text(available_time.min()),
    "available_end_kst": _timestamp_text(available_time.max()),
    "grid_count_min": int(grid_count.min()),
    "grid_count_max": int(grid_count.max()),
    "rows_per_forecast_min": int(row_count.min()),
    "rows_per_forecast_max": int(row_count.max()),
    "lead_hour_min": float(lead_hour.min()),
    "lead_hour_max": float(lead_hour.max()),
    "lead_hour_unique": int(lead_hour.nunique()),
    "value_columns": value_columns,
    "missing_cells": int(frame[value_columns].isna().sum().sum()),
  }


def build_training_data_profile(
  *,
  train_labels,
  ldaps_train,
  gfs_train,
  train_features,
  feature_set=None,
):
  """실제 학습 입력과 baseline 전처리 결과를 JSON 가능한 profile로 만든다."""
  _require_columns(train_labels, ["kst_dtm", *TARGET_COLS], "train_labels")
  if not hasattr(train_features, "X") or not hasattr(train_features, "frame"):
    raise ValueError("train_features는 X와 frame을 가진 BaselineFeatureSet이어야 합니다")
  if len(train_features.X) != len(train_features.frame):
    raise ValueError("train feature matrix와 병합 frame의 행 수가 다릅니다")

  label_profile = {
    "rows": int(len(train_labels)),
    "columns": list(train_labels.columns),
    **_frame_period(train_labels, "kst_dtm"),
    "target_non_null_rows": {
      target: int(train_labels[target].notna().sum())
      for target in TARGET_COLS
    },
    "target_missing_rows": {
      target: int(train_labels[target].isna().sum())
      for target in TARGET_COLS
    },
    "target_negative_rows": {
      target: int((pd.to_numeric(train_labels[target], errors="coerce") < 0).sum())
      for target in TARGET_COLS
    },
    "capacity_exceedance_rows": {
      target: int((pd.to_numeric(train_labels[target], errors="coerce") > CAPACITY_KWH[target]).sum())
      for target in TARGET_COLS
    },
  }

  feature_columns = list(train_features.X.columns)
  feature_dtypes = {
    column: str(train_features.X[column].dtype)
    for column in feature_columns
  }
  feature_schema = {
    "columns": feature_columns,
    "dtypes": feature_dtypes,
  }
  missing_by_column = train_features.X.isna().sum()
  feature_profile = {
    "rows": int(len(train_features.X)),
    "columns": int(len(feature_columns)),
    "feature_columns": feature_columns,
    "feature_dtypes": feature_dtypes,
    "feature_schema_sha256": sha256_text(stable_json_dumps(feature_schema)),
    "missing_cells_before_imputation": int(missing_by_column.sum()),
    "rows_with_missing_before_imputation": int(train_features.X.isna().any(axis=1).sum()),
    "columns_with_missing_before_imputation": [
      column
      for column in feature_columns
      if int(missing_by_column[column]) > 0
    ],
  }

  return {
    "labels": label_profile,
    "weather": {
      "ldaps": _weather_profile(ldaps_train, "ldaps_train"),
      "gfs": _weather_profile(gfs_train, "gfs_train"),
    },
    "feature_matrix": feature_profile,
    "preprocessing": json.loads(
      stable_json_dumps(build_preprocessing_contract(feature_set))
    ),
  }


def _sha256_file(path, chunk_size=1024 * 1024):
  digest = hashlib.sha256()
  with Path(path).open("rb") as source:
    while chunk := source.read(chunk_size):
      digest.update(chunk)
  return digest.hexdigest()


def fingerprint_files(paths: Mapping[str, Path | str]):
  """실제 입력 파일 bytes의 크기와 SHA256을 source 이름별로 기록한다."""
  fingerprints = {}
  for source_name, raw_path in paths.items():
    path = Path(raw_path)
    if not path.is_file():
      raise FileNotFoundError(f"{source_name} 입력 파일을 찾을 수 없습니다: {path}")
    fingerprints[str(source_name)] = {
      "path": path.as_posix(),
      "bytes": int(path.stat().st_size),
      "sha256": _sha256_file(path),
    }
  return fingerprints


def _normalize_validation(validation):
  if validation is None:
    return {}
  normalized = json.loads(stable_json_dumps(dict(validation)))
  score_presence = [normalized.get(field) is not None for field in _VALIDATION_SCORE_FIELDS]
  if any(score_presence) and not all(score_presence):
    raise ValueError("validation 점수는 total_score, one_minus_nmae, ficr를 모두 제공해야 합니다")
  for field in _VALIDATION_SCORE_FIELDS:
    if normalized.get(field) is not None:
      score = float(normalized[field])
      if not np.isfinite(score):
        raise ValueError(f"validation {field}는 유한한 숫자여야 합니다")
      normalized[field] = score
  return normalized


def _current_kst_isoformat():
  return normalize_created_at_kst(pd.Timestamp.now(tz="Asia/Seoul"))


def _build_run_id(experiment_id, git_commit, config_sha256, created_at_kst):
  timestamp = pd.Timestamp(created_at_kst).strftime("%Y%m%dT%H%M%S")
  slug = slugify_experiment_id(experiment_id)
  commit = str(git_commit or "unknown")[:7]
  return f"{timestamp}-{slug}-{config_sha256[:8]}-{commit}"


def _metadata_bytes(metadata):
  return (stable_json_dumps(metadata) + "\n").encode(MODEL_METADATA_ENCODING)


def build_model_artifact(
  *,
  bundle,
  config,
  data_profile,
  git_commit,
  data_manifest_sha256,
  input_files=None,
  created_at_kst=None,
  validation=None,
  feature_set=None,
  feature_pipeline=None,
):
  """모델 bytes와 데이터/전처리 lineage sidecar를 메모리에서 만든다."""
  git_commit = str(git_commit or "").strip()
  if not git_commit:
    raise ValueError("git_commit은 비어 있을 수 없습니다")
  data_manifest_sha256 = _require_sha256(data_manifest_sha256, "data_manifest_sha256")

  feature_profile = data_profile.get("feature_matrix", {})
  profile_columns = list(feature_profile.get("feature_columns", []))
  bundle_columns = list(getattr(bundle, "feature_columns", []))
  if not bundle_columns:
    raise ValueError("bundle feature_columns가 비어 있습니다")
  if profile_columns != bundle_columns:
    raise ValueError("bundle과 data profile의 feature 순서가 일치하지 않습니다")

  feature_schema_sha256 = _require_sha256(
    feature_profile.get("feature_schema_sha256"),
    "feature_schema_sha256",
  )
  normalized_profile = json.loads(stable_json_dumps(data_profile))
  normalized_preprocessing = normalized_profile.get("preprocessing")
  if not normalized_preprocessing:
    raise ValueError("data profile에 preprocessing 계약이 없습니다")

  model_bytes = pickle.dumps(bundle, protocol=pickle.HIGHEST_PROTOCOL)
  model_sha256 = hashlib.sha256(model_bytes).hexdigest()
  created_at = _current_kst_isoformat() if created_at_kst is None else normalize_created_at_kst(created_at_kst)
  config_sha256 = config.config_sha256()
  validation_record = _normalize_validation(validation)
  run_id = _build_run_id(config.experiment_id, git_commit, config_sha256, created_at)

  metadata = {
    "schema_version": MODEL_METADATA_SCHEMA_VERSION,
    "run_id": run_id,
    "created_at_kst": created_at,
    "experiment_id": config.experiment_id,
    "git_commit": git_commit,
    "seed": int(config.seed),
    "config": config.as_record(),
    "config_sha256": config_sha256,
    "data_manifest_sha256": data_manifest_sha256,
    "input_files": json.loads(stable_json_dumps(input_files or {})),
    "data_profile": normalized_profile,
    "data_profile_sha256": sha256_text(stable_json_dumps(normalized_profile)),
    "preprocessing_sha256": sha256_text(stable_json_dumps(normalized_preprocessing)),
    "feature_set": json.loads(
      stable_json_dumps(build_feature_set_record(feature_set, feature_pipeline))
    ),
    "model": {
      "model_type": type(bundle).__name__,
      "model_module": type(bundle).__module__,
      "pickle_protocol": pickle.HIGHEST_PROTOCOL,
      "model_bytes": int(len(model_bytes)),
      "model_sha256": model_sha256,
      "feature_columns": bundle_columns,
      "feature_schema_sha256": feature_schema_sha256,
      "target_train_rows": {
        target: int(getattr(bundle, "train_rows", {}).get(target, 0))
        for target in TARGET_COLS
      },
      "target_model_types": {
        target: type(model).__name__
        for target, model in getattr(bundle, "models", {}).items()
      },
    },
    "validation": validation_record,
    "environment": {
      "python": platform.python_version(),
      "numpy": np.__version__,
      "pandas": pd.__version__,
      "scikit_learn": sklearn.__version__,
    },
    "note": config.notes,
  }
  metadata_bytes = _metadata_bytes(metadata)
  return ModelArtifact(
    model_bytes=model_bytes,
    model_sha256=model_sha256,
    metadata=metadata,
    metadata_bytes=metadata_bytes,
    metadata_sha256=hashlib.sha256(metadata_bytes).hexdigest(),
  )


def _validate_metadata_integrity(metadata):
  profile = metadata.get("data_profile")
  if not isinstance(profile, dict):
    raise ValueError("metadata data_profile이 없습니다")
  expected_profile_hash = _require_sha256(metadata.get("data_profile_sha256"), "data_profile_sha256")
  actual_profile_hash = sha256_text(stable_json_dumps(profile))
  if actual_profile_hash != expected_profile_hash:
    raise ValueError("metadata data profile SHA256이 일치하지 않습니다")

  preprocessing = profile.get("preprocessing")
  expected_preprocessing_hash = _require_sha256(
    metadata.get("preprocessing_sha256"),
    "preprocessing_sha256",
  )
  actual_preprocessing_hash = sha256_text(stable_json_dumps(preprocessing))
  if actual_preprocessing_hash != expected_preprocessing_hash:
    raise ValueError("metadata preprocessing SHA256이 일치하지 않습니다")


def load_model_artifact_bytes(model_bytes, metadata_bytes, *, expected_metadata_sha256=None):
  """hash와 feature 계약을 확인한 뒤 신뢰된 로컬 pickle을 역직렬화한다."""
  if expected_metadata_sha256 is not None:
    expected_metadata_sha256 = _require_sha256(expected_metadata_sha256, "expected_metadata_sha256")
    actual_metadata_sha256 = hashlib.sha256(metadata_bytes).hexdigest()
    if actual_metadata_sha256 != expected_metadata_sha256:
      raise ValueError("metadata SHA256이 run registry와 일치하지 않습니다")

  try:
    metadata = json.loads(metadata_bytes.decode(MODEL_METADATA_ENCODING))
  except (UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise ValueError("model metadata JSON을 읽을 수 없습니다") from exc
  _validate_metadata_integrity(metadata)

  expected_model_sha256 = _require_sha256(
    metadata.get("model", {}).get("model_sha256"),
    "model_sha256",
  )
  actual_model_sha256 = hashlib.sha256(model_bytes).hexdigest()
  if actual_model_sha256 != expected_model_sha256:
    raise ValueError("model SHA256이 metadata와 일치하지 않습니다")

  bundle = pickle.loads(model_bytes)
  metadata_columns = list(metadata.get("model", {}).get("feature_columns", []))
  bundle_columns = list(getattr(bundle, "feature_columns", []))
  profile_columns = list(
    metadata.get("data_profile", {}).get("feature_matrix", {}).get("feature_columns", [])
  )
  if not (bundle_columns == metadata_columns == profile_columns):
    raise ValueError("model artifact feature 순서가 metadata와 일치하지 않습니다")

  metadata_train_rows = metadata.get("model", {}).get("target_train_rows", {})
  bundle_train_rows = {
    target: int(getattr(bundle, "train_rows", {}).get(target, 0))
    for target in TARGET_COLS
  }
  if bundle_train_rows != metadata_train_rows:
    raise ValueError("model artifact target별 학습 행 수가 metadata와 일치하지 않습니다")
  return bundle, metadata


def default_metadata_path(model_path):
  model_path = Path(model_path)
  return model_path.with_name(f"{model_path.name}.metadata.json")


def _atomic_write_bytes(path, payload):
  path = Path(path)
  path.parent.mkdir(parents=True, exist_ok=True)
  temporary_path = None
  try:
    with tempfile.NamedTemporaryFile(
      mode="wb",
      dir=path.parent,
      prefix=f".{path.name}.",
      suffix=".tmp",
      delete=False,
    ) as temporary_file:
      temporary_file.write(payload)
      temporary_file.flush()
      os.fsync(temporary_file.fileno())
      temporary_path = Path(temporary_file.name)
    os.replace(temporary_path, path)
  finally:
    if temporary_path is not None and temporary_path.exists():
      temporary_path.unlink()


def save_model_artifact(artifact, model_path, metadata_path=None):
  """검증된 canonical bytes를 model과 sidecar에 원자적으로 저장한다."""
  model_path = Path(model_path)
  metadata_path = default_metadata_path(model_path) if metadata_path is None else Path(metadata_path)
  if model_path.resolve() == metadata_path.resolve():
    raise ValueError("model_path와 metadata_path는 달라야 합니다")
  existing_paths = [path for path in [model_path, metadata_path] if path.exists()]
  if existing_paths:
    raise FileExistsError(f"기존 model artifact를 덮어쓸 수 없습니다: {existing_paths}")
  if hashlib.sha256(artifact.model_bytes).hexdigest() != artifact.model_sha256:
    raise ValueError("저장 전 model bytes SHA256이 artifact와 일치하지 않습니다")
  if hashlib.sha256(artifact.metadata_bytes).hexdigest() != artifact.metadata_sha256:
    raise ValueError("저장 전 metadata bytes SHA256이 artifact와 일치하지 않습니다")

  _atomic_write_bytes(model_path, artifact.model_bytes)
  try:
    _atomic_write_bytes(metadata_path, artifact.metadata_bytes)
  except Exception:
    if model_path.exists():
      model_path.unlink()
    raise
  return SavedModelArtifact(
    model_path=model_path,
    metadata_path=metadata_path,
    model_sha256=artifact.model_sha256,
    metadata_sha256=artifact.metadata_sha256,
  )


def load_model_artifact(model_path, metadata_path=None, *, expected_metadata_sha256=None):
  model_path = Path(model_path)
  metadata_path = default_metadata_path(model_path) if metadata_path is None else Path(metadata_path)
  if not model_path.is_file():
    raise FileNotFoundError(f"model 파일을 찾을 수 없습니다: {model_path}")
  if not metadata_path.is_file():
    raise FileNotFoundError(f"model metadata sidecar를 찾을 수 없습니다: {metadata_path}")
  return load_model_artifact_bytes(
    model_path.read_bytes(),
    metadata_path.read_bytes(),
    expected_metadata_sha256=expected_metadata_sha256,
  )


def load_registered_model_artifact(model_path, metadata_path, registry_path):
  """registry hash를 신뢰점으로 model과 sidecar를 검증한 뒤 로드한다."""
  model_path = Path(model_path)
  metadata_path = default_metadata_path(model_path) if metadata_path is None else Path(metadata_path)
  registry_path = Path(registry_path)
  if not model_path.is_file():
    raise FileNotFoundError(f"model 파일을 찾을 수 없습니다: {model_path}")
  if not metadata_path.is_file():
    raise FileNotFoundError(f"model metadata sidecar를 찾을 수 없습니다: {metadata_path}")
  if not registry_path.is_file():
    raise FileNotFoundError(f"run registry를 찾을 수 없습니다: {registry_path}")

  model_bytes = model_path.read_bytes()
  metadata_bytes = metadata_path.read_bytes()
  try:
    untrusted_metadata = json.loads(metadata_bytes.decode(MODEL_METADATA_ENCODING))
  except (UnicodeDecodeError, json.JSONDecodeError) as exc:
    raise ValueError("model metadata JSON을 읽을 수 없습니다") from exc
  run_id = str(untrusted_metadata.get("run_id") or "")
  if not run_id:
    raise ValueError("model metadata에 run_id가 없습니다")

  registry = pd.read_csv(registry_path, encoding=REGISTRY_ENCODING)
  if list(registry.columns) != RUN_REGISTRY_COLUMNS:
    raise ValueError("기존 run registry 컬럼명 또는 순서가 고정 schema와 다릅니다")
  match = registry["run_id"].astype(str) == run_id
  if int(match.sum()) != 1:
    raise ValueError(f"run registry에서 고유한 run_id를 찾을 수 없습니다: {run_id}")
  row = registry.loc[match].iloc[0]

  expected_metadata_sha256 = _require_sha256(row["metadata_sha256"], "metadata_sha256")
  actual_metadata_sha256 = hashlib.sha256(metadata_bytes).hexdigest()
  if actual_metadata_sha256 != expected_metadata_sha256:
    raise ValueError("metadata SHA256이 run registry와 일치하지 않습니다")
  expected_model_sha256 = _require_sha256(row["model_sha256"], "model_sha256")
  actual_model_sha256 = hashlib.sha256(model_bytes).hexdigest()
  if actual_model_sha256 != expected_model_sha256:
    raise ValueError("model SHA256이 run registry와 일치하지 않습니다")

  return load_model_artifact_bytes(
    model_bytes,
    metadata_bytes,
    expected_metadata_sha256=expected_metadata_sha256,
  )


def build_run_registry_entry(
  *,
  artifact,
  model_path,
  metadata_path,
  submission_entry=None,
):
  """상세 sidecar를 가리키는 비교용 run registry 한 행을 만든다."""
  metadata = artifact.metadata
  validation = metadata.get("validation", {})
  submission = dict(submission_entry or {})
  has_submission = bool(submission.get("submission_sha256"))
  if has_submission:
    _require_sha256(submission["submission_sha256"], "submission_sha256")

  profile = metadata["data_profile"]
  feature_profile = profile["feature_matrix"]
  entry = {
    "created_at_kst": metadata["created_at_kst"],
    "run_id": metadata["run_id"],
    "experiment_id": metadata["experiment_id"],
    "status": "submission_validated" if has_submission else "trained",
    "git_commit": metadata["git_commit"],
    "seed": metadata["seed"],
    "config_sha256": metadata["config_sha256"],
    "data_manifest_sha256": metadata["data_manifest_sha256"],
    "data_profile_sha256": metadata["data_profile_sha256"],
    "preprocessing_sha256": metadata["preprocessing_sha256"],
    "feature_schema_sha256": metadata["model"]["feature_schema_sha256"],
    "split_name": validation.get("split_name"),
    "train_start_kst": validation.get("train_start_kst"),
    "train_end_kst": validation.get("train_end_kst"),
    "validation_start_kst": validation.get("validation_start_kst"),
    "validation_end_kst": validation.get("validation_end_kst"),
    "total_score": validation.get("total_score"),
    "one_minus_nmae": validation.get("one_minus_nmae"),
    "ficr": validation.get("ficr"),
    "label_rows": profile["labels"]["rows"],
    "feature_rows": feature_profile["rows"],
    "feature_count": feature_profile["columns"],
    "target_train_rows": stable_json_dumps(metadata["model"]["target_train_rows"]),
    "model_type": metadata["model"]["model_type"],
    "model_filename": Path(model_path).as_posix(),
    "model_sha256": artifact.model_sha256,
    "model_bytes": metadata["model"]["model_bytes"],
    "metadata_filename": Path(metadata_path).as_posix(),
    "metadata_sha256": artifact.metadata_sha256,
    "submission_filename": submission.get("submission_filename"),
    "submission_sha256": submission.get("submission_sha256"),
    "submission_rows": submission.get("submission_rows"),
    "submission_encoding": submission.get("submission_encoding"),
    "public_score": submission.get("public_score"),
    "dacon_submission_id": submission.get("dacon_submission_id"),
    "selected": bool(submission.get("selected", False)),
    "note": submission.get("note", metadata.get("note", "")),
  }
  return {column: entry[column] for column in RUN_REGISTRY_COLUMNS}


def _validate_registry_entry(entry):
  if list(entry) != RUN_REGISTRY_COLUMNS:
    raise ValueError("run registry entry 컬럼명 또는 순서가 고정 schema와 다릅니다")
  if not str(entry.get("run_id") or "").strip():
    raise ValueError("run registry entry의 run_id가 비어 있습니다")
  for field in [
    "config_sha256",
    "data_manifest_sha256",
    "data_profile_sha256",
    "preprocessing_sha256",
    "feature_schema_sha256",
    "model_sha256",
    "metadata_sha256",
  ]:
    _require_sha256(entry.get(field), field)


def _registry_to_csv_bytes(frame):
  return frame.to_csv(index=False, lineterminator="\n").encode(REGISTRY_ENCODING)


def _write_registry_frame(registry_path, frame):
  frame = frame[RUN_REGISTRY_COLUMNS]
  _atomic_write_bytes(registry_path, _registry_to_csv_bytes(frame))
  return frame


def append_run_registry_entry(registry_path, entry):
  """기존 행을 보존하고 고유 run_id 한 행을 registry에 추가한다."""
  _validate_registry_entry(entry)
  registry_path = Path(registry_path)
  if registry_path.exists():
    registry = pd.read_csv(registry_path, encoding=REGISTRY_ENCODING)
    if list(registry.columns) != RUN_REGISTRY_COLUMNS:
      raise ValueError("기존 run registry 컬럼명 또는 순서가 고정 schema와 다릅니다")
    if str(entry["run_id"]) in registry["run_id"].astype(str).tolist():
      raise ValueError(f"run_id 중복: {entry['run_id']}")
    registry = pd.concat([registry, pd.DataFrame([entry])], ignore_index=True)
  else:
    registry = pd.DataFrame([entry], columns=RUN_REGISTRY_COLUMNS)
  return _write_registry_frame(registry_path, registry)


def update_run_registry_submission(
  registry_path,
  *,
  run_id,
  submission_filename,
  submission_sha256,
  submission_rows,
  submission_encoding,
  public_score=None,
  dacon_submission_id=None,
  selected=None,
):
  """validator를 통과한 submission bytes hash를 기존 run에 연결한다."""
  registry_path = Path(registry_path)
  if not registry_path.is_file():
    raise FileNotFoundError(f"run registry를 찾을 수 없습니다: {registry_path}")
  submission_sha256 = _require_sha256(submission_sha256, "submission_sha256")
  if int(submission_rows) < 1:
    raise ValueError("submission_rows는 1 이상이어야 합니다")
  if submission_encoding not in {"utf-8", "utf-8-sig"}:
    raise ValueError("submission_encoding은 utf-8 또는 utf-8-sig여야 합니다")

  registry = pd.read_csv(registry_path, encoding=REGISTRY_ENCODING)
  if list(registry.columns) != RUN_REGISTRY_COLUMNS:
    raise ValueError("기존 run registry 컬럼명 또는 순서가 고정 schema와 다릅니다")
  match = registry["run_id"].astype(str) == str(run_id)
  if int(match.sum()) != 1:
    raise ValueError(f"run registry에서 고유한 run_id를 찾을 수 없습니다: {run_id}")

  for column in [
    "status",
    "submission_filename",
    "submission_sha256",
    "submission_encoding",
    "dacon_submission_id",
  ]:
    registry[column] = registry[column].astype("object")

  registry.loc[match, "status"] = "submission_validated"
  registry.loc[match, "submission_filename"] = str(submission_filename)
  registry.loc[match, "submission_sha256"] = submission_sha256
  registry.loc[match, "submission_rows"] = int(submission_rows)
  registry.loc[match, "submission_encoding"] = submission_encoding
  if public_score is not None:
    registry.loc[match, "public_score"] = float(public_score)
  if dacon_submission_id is not None:
    registry.loc[match, "dacon_submission_id"] = str(dacon_submission_id)
  if selected is not None:
    registry.loc[match, "selected"] = bool(selected)
  return _write_registry_frame(registry_path, registry)


__all__ = [
  "LEGACY_METADATA_SCHEMA_VERSIONS",
  "MODEL_METADATA_SCHEMA_VERSION",
  "ModelArtifact",
  "PREPROCESSING_CONTRACT",
  "build_feature_set_record",
  "build_preprocessing_contract",
  "RUN_REGISTRY_COLUMNS",
  "SavedModelArtifact",
  "append_run_registry_entry",
  "build_model_artifact",
  "build_run_registry_entry",
  "build_training_data_profile",
  "default_metadata_path",
  "fingerprint_files",
  "load_model_artifact",
  "load_model_artifact_bytes",
  "load_registered_model_artifact",
  "save_model_artifact",
  "update_run_registry_submission",
]
