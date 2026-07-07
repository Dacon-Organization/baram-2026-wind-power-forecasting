"""공식 RandomForest baseline의 train/inference 분리 모듈."""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer

from baram.metrics import CAPACITY_KWH, TARGET_COLS


OFFICIAL_RF_PARAMS = {
  "n_estimators": 120,
  "max_depth": 14,
  "min_samples_leaf": 8,
  "max_features": "sqrt",
  "random_state": 42,
  "n_jobs": -1,
}


@dataclass
class BaselineFeatureSet:
  """baseline 학습/추론에 필요한 병합 frame과 feature matrix."""

  frame: pd.DataFrame
  X: pd.DataFrame
  weather: pd.DataFrame


@dataclass
class RandomForestBaselineBundle:
  """target별 RandomForest와 공통 imputer를 묶은 inference bundle."""

  imputer: SimpleImputer
  models: dict
  feature_columns: list
  train_rows: dict


def _require_columns(frame, required_columns, frame_name):
  missing_columns = [column for column in required_columns if column not in frame.columns]
  if missing_columns:
    raise ValueError(f"{frame_name} 필수 컬럼 누락: {missing_columns}")


def _validate_weather_cutoff(frame, frame_name):
  _require_columns(
    frame,
    ["forecast_kst_dtm", "data_available_kst_dtm", "grid_id", "latitude", "longitude"],
    frame_name,
  )
  forecast_time = pd.to_datetime(frame["forecast_kst_dtm"])
  available_time = pd.to_datetime(frame["data_available_kst_dtm"])
  if (available_time > forecast_time).any():
    bad_count = int((available_time > forecast_time).sum())
    raise ValueError(f"{frame_name} cutoff 위반: 사용 가능 시각이 예보 대상 시각보다 늦은 행 {bad_count}개")


def aggregate_weather(frame, prefix):
  """격자별 NWP 예보를 forecast 시각 단위 평균 feature로 집계한다."""
  _validate_weather_cutoff(frame, prefix)
  working = frame.copy()
  working["forecast_kst_dtm"] = pd.to_datetime(working["forecast_kst_dtm"])
  working["data_available_kst_dtm"] = pd.to_datetime(working["data_available_kst_dtm"])
  working["_lead_hour"] = (
    working["forecast_kst_dtm"] - working["data_available_kst_dtm"]
  ).dt.total_seconds() / 3600

  meta_columns = {
    "forecast_kst_dtm",
    "data_available_kst_dtm",
    "grid_id",
    "latitude",
    "longitude",
    "_lead_hour",
  }
  value_columns = [
    column
    for column in working.columns
    if column not in meta_columns and pd.api.types.is_numeric_dtype(working[column])
  ]
  if not value_columns:
    raise ValueError(f"{prefix} 집계 가능한 숫자 예보 컬럼이 없습니다")

  aggregated = working.groupby("forecast_kst_dtm")[value_columns].mean()
  aggregated.columns = [f"{prefix}_{column}_mean" for column in aggregated.columns]

  lead_feature = working.groupby("forecast_kst_dtm")["_lead_hour"].first().rename(f"{prefix}_lead_hour")
  return aggregated.join(lead_feature).reset_index()


def build_weather_features(ldaps_frame, gfs_frame):
  """LDAPS/GFS 집계 feature를 forecast 시각 기준으로 병합한다."""
  ldaps_weather = aggregate_weather(ldaps_frame, "ldaps")
  gfs_weather = aggregate_weather(gfs_frame, "gfs")
  return ldaps_weather.merge(gfs_weather, on="forecast_kst_dtm", how="outer").sort_values("forecast_kst_dtm")


def calendar_features(dt_series):
  """target 시각에서 leakage 없는 calendar feature를 만든다."""
  dt = pd.to_datetime(dt_series)
  features = pd.DataFrame(index=dt.index)
  features["month"] = dt.dt.month
  features["day"] = dt.dt.day
  features["hour"] = dt.dt.hour
  features["dayofweek"] = dt.dt.dayofweek
  features["is_weekend"] = dt.dt.dayofweek.isin([5, 6]).astype(int)
  features["hour_sin"] = np.sin(2 * np.pi * features["hour"] / 24)
  features["hour_cos"] = np.cos(2 * np.pi * features["hour"] / 24)
  features["month_sin"] = np.sin(2 * np.pi * features["month"] / 12)
  features["month_cos"] = np.cos(2 * np.pi * features["month"] / 12)
  return features


def _feature_matrix(merged_frame, drop_columns):
  feature_frame = merged_frame.drop(columns=drop_columns)
  return pd.concat(
    [calendar_features(merged_frame["forecast_kst_dtm"]), feature_frame],
    axis=1,
  )


def build_training_features(label_frame, ldaps_frame, gfs_frame):
  """label과 NWP를 병합해 학습용 feature set을 만든다."""
  _require_columns(label_frame, ["kst_dtm", *TARGET_COLS], "label_frame")
  weather = build_weather_features(ldaps_frame, gfs_frame)
  base = label_frame.copy().rename(columns={"kst_dtm": "forecast_kst_dtm"})
  base["forecast_kst_dtm"] = pd.to_datetime(base["forecast_kst_dtm"])
  merged = base.merge(weather, on="forecast_kst_dtm", how="left", sort=False)
  X = _feature_matrix(merged, ["forecast_kst_dtm", *TARGET_COLS])
  return BaselineFeatureSet(frame=merged, X=X, weather=weather)


def build_inference_features(sample_submission, ldaps_frame, gfs_frame):
  """sample_submission 시간축을 고정한 추론용 feature set을 만든다."""
  _require_columns(sample_submission, ["forecast_id", "forecast_kst_dtm"], "sample_submission")
  weather = build_weather_features(ldaps_frame, gfs_frame)
  base = sample_submission[["forecast_id", "forecast_kst_dtm"]].copy()
  base["forecast_kst_dtm"] = pd.to_datetime(base["forecast_kst_dtm"])
  merged = base.merge(weather, on="forecast_kst_dtm", how="left", sort=False)
  X = _feature_matrix(merged, ["forecast_id", "forecast_kst_dtm"])
  return BaselineFeatureSet(frame=merged, X=X, weather=weather)


def train_random_forest_baseline(X_train, train_frame, model_params=None):
  """target별 non-null mask로 RandomForest baseline을 학습한다."""
  _require_columns(train_frame, TARGET_COLS, "train_frame")
  if len(X_train) != len(train_frame) or not X_train.index.equals(train_frame.index):
    raise ValueError("X_train과 train_frame의 index/행 수가 일치해야 합니다")

  params = dict(OFFICIAL_RF_PARAMS)
  if model_params is not None:
    params.update(model_params)
  feature_columns = list(X_train.columns)

  imputer = SimpleImputer(strategy="median")
  X_train_imputed = pd.DataFrame(
    imputer.fit_transform(X_train),
    columns=feature_columns,
    index=X_train.index,
  )

  models = {}
  train_rows = {}
  for target in TARGET_COLS:
    train_mask = train_frame[target].notna()
    if not train_mask.any():
      raise ValueError(f"{target} 학습 가능한 non-null label이 없습니다")
    model = RandomForestRegressor(**params)
    model.fit(X_train_imputed.loc[train_mask], train_frame.loc[train_mask, target])
    models[target] = model
    train_rows[target] = int(train_mask.sum())

  return RandomForestBaselineBundle(
    imputer=imputer,
    models=models,
    feature_columns=feature_columns,
    train_rows=train_rows,
  )


def predict_random_forest_baseline(bundle, X_predict):
  """학습 bundle과 동일 feature 순서로 예측하고 capacity 범위로 clip한다."""
  missing_columns = [column for column in bundle.feature_columns if column not in X_predict.columns]
  if missing_columns:
    raise ValueError(f"추론 feature 누락: {missing_columns}")

  X_ordered = X_predict[bundle.feature_columns]
  X_imputed = pd.DataFrame(
    bundle.imputer.transform(X_ordered),
    columns=bundle.feature_columns,
    index=X_predict.index,
  )

  predictions = pd.DataFrame(index=X_predict.index)
  for target in TARGET_COLS:
    if target not in bundle.models:
      raise ValueError(f"{target} 모델이 bundle에 없습니다")
    raw_prediction = bundle.models[target].predict(X_imputed)
    predictions[target] = np.clip(raw_prediction, 0, CAPACITY_KWH[target])

  return predictions


def build_submission(sample_submission, predictions):
  """공식 제출 template의 id/time 컬럼을 보존하고 target만 교체한다."""
  _require_columns(sample_submission, ["forecast_id", "forecast_kst_dtm", *TARGET_COLS], "sample_submission")
  _require_columns(predictions, TARGET_COLS, "predictions")
  if len(sample_submission) != len(predictions):
    raise ValueError("sample_submission과 predictions 행 수가 다릅니다")

  submission = sample_submission[["forecast_id", "forecast_kst_dtm"]].copy()
  for target in TARGET_COLS:
    submission[target] = predictions[target].to_numpy()
  return submission


def run_train_inference(train_labels, ldaps_train, gfs_train, sample_submission, ldaps_test, gfs_test, model_params=None):
  """공식 baseline의 학습과 추론을 파일 저장 없이 한 번에 실행한다."""
  train_features = build_training_features(train_labels, ldaps_train, gfs_train)
  inference_features = build_inference_features(sample_submission, ldaps_test, gfs_test)
  bundle = train_random_forest_baseline(train_features.X, train_features.frame, model_params=model_params)
  predictions = predict_random_forest_baseline(bundle, inference_features.X)
  submission = build_submission(sample_submission, predictions)
  return {
    "train_features": train_features,
    "inference_features": inference_features,
    "bundle": bundle,
    "predictions": predictions,
    "submission": submission,
  }


__all__ = [
  "BaselineFeatureSet",
  "OFFICIAL_RF_PARAMS",
  "RandomForestBaselineBundle",
  "aggregate_weather",
  "build_inference_features",
  "build_submission",
  "build_training_features",
  "build_weather_features",
  "calendar_features",
  "predict_random_forest_baseline",
  "run_train_inference",
  "train_random_forest_baseline",
]
