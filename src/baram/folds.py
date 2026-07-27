"""BARAM 시간 fold 정의와 fold runner.

노트북 13이 로컬 코드로 들고 있던 `TRAIN_WINDOWS`·`FOLDS`·`runWindow`를 승격한 모듈이다.
노트북 14가 검증 연도를 2022·2023까지 넓히면서 fold가 5개에서 9개로 늘었고, GBM
작업이 같은 fold를 재사용할 예정이라 정의를 한 곳에 모은다.

fold 정의는 **계약**이다. `assert_fold_contract()`가 시간 순서와 비겹침을 검사하며,
정의를 잘못 고치면 조용히 통과하지 않고 `ValueError`로 드러난다.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from baram.baseline import OFFICIAL_RF_PARAMS
from baram.metrics import CAPACITY_KWH
from baram.metrics import TARGET_COLS
from baram.metrics import metric_over


# 학습 창. 같은 창을 쓰는 fold는 학습을 공유한다 — 행 간 연산이 0건이므로
# 한 번 예측한 뒤 검증 구간별로 잘라 써도 개별 실행과 결과가 같다.
TRAIN_WINDOWS = {
  "W_2022_2023": ("2022-01-01 01:00", "2023-12-31 23:00"),
  "W_2023": ("2023-01-01 01:00", "2023-12-31 23:00"),
  "W_2023_2024H1": ("2023-01-01 01:00", "2024-06-30 23:00"),
  "W_2022_2023H1": ("2022-01-01 01:00", "2023-06-30 23:00"),
  "W_2024": ("2024-01-01 00:00", "2024-12-31 23:00"),
  "W_2022": ("2022-01-01 01:00", "2022-12-31 23:00"),
}

FORWARD = "순"
BACKWARD = "역"


@dataclass(frozen=True)
class FoldSpec:
  """fold 하나의 정의.

  direction이 `FORWARD`면 train이 valid보다 과거이고 실제 운영 순서와 같다.
  `BACKWARD`면 순서가 뒤집힌 fold이며 **순위 탐침으로만** 쓴다. 수준 추정에
  쓰면 안 된다 (노트북 14 Decision Box ㉒).
  """

  train_window: str
  valid_start: str
  valid_end: str
  direction: str
  valid_year: int
  purpose: str


FOLDS = {
  # --- 노트북 13이 정의한 2024 검증 fold. 정의를 바꾸지 않는다 ---
  "F0": FoldSpec("W_2022_2023", "2024-01-01 00:00", "2024-12-31 23:00", FORWARD, 2024, "기존 기준선 (노트북 08·11·12)"),
  "F1": FoldSpec("W_2022_2023", "2024-01-01 00:00", "2024-05-31 23:00", FORWARD, 2024, "겨울·봄 저온/강풍"),
  "F2": FoldSpec("W_2022_2023", "2024-06-01 00:00", "2024-10-31 23:00", FORWARD, 2024, "여름·가을 장마/저풍속"),
  "F3": FoldSpec("W_2023", "2024-01-01 00:00", "2024-12-31 23:00", FORWARD, 2024, "2022 제거 영향"),
  "F4": FoldSpec("W_2023_2024H1", "2024-07-01 00:00", "2024-12-31 23:00", FORWARD, 2024, "최신 분포 rolling"),
  # --- 노트북 14가 추가한 cross-year fold ---
  "F5": FoldSpec("W_2022_2023H1", "2023-07-01 00:00", "2023-12-31 23:00", FORWARD, 2023, "F4의 연도 미러 — 계절·창 길이 고정"),
  "F6": FoldSpec("W_2024", "2023-01-01 01:00", "2023-12-31 23:00", BACKWARD, 2023, "2023 전체 · 3그룹 (역방향 탐침)"),
  "F7": FoldSpec("W_2022", "2023-01-01 01:00", "2023-12-31 23:00", FORWARD, 2023, "2023 전체 · G1·G2 (G3 학습 라벨 없음)"),
  "F8": FoldSpec("W_2023", "2022-01-01 01:00", "2022-12-31 23:00", BACKWARD, 2022, "2022 전체 · G1·G2 (역방향 탐침)"),
}

# 노트북 13이 확정한 순위 문턱. 간격이 이보다 작으면 크기를 확정하지 않는다.
RANK_THRESHOLD = 0.0036


def label_mask(labels, start, end):
  """라벨 프레임에서 [start, end] 구간 행을 고르는 boolean mask."""
  times = labels["kst_dtm"]
  return (times >= pd.Timestamp(start)) & (times <= pd.Timestamp(end))


def weather_slice(frame, start, end):
  """NWP 프레임을 예보 대상 시각 기준으로 자른다."""
  times = frame["forecast_kst_dtm"]
  return frame[(times >= pd.Timestamp(start)) & (times <= pd.Timestamp(end))]


def train_window_bounds(fold_name):
  return TRAIN_WINDOWS[FOLDS[fold_name].train_window]


def trainable_targets(labels, fold_name):
  """그 fold의 학습 창에서 라벨이 1행이라도 있는 target."""
  start, end = train_window_bounds(fold_name)
  subset = labels.loc[label_mask(labels, start, end)]
  return [target for target in TARGET_COLS if int(subset[target].notna().sum()) > 0]


def scoreable_targets(labels, fold_name):
  """그 fold에서 채점 가능한 target — 학습 라벨과 평가 대상 행이 모두 있어야 한다.

  평가 대상은 실제값이 설비용량의 10% 이상인 행이다(`metrics.py`). Group 3은
  2022 라벨이 0행이라 학습 창이나 검증 구간이 2022뿐이면 자동으로 빠진다.
  """
  spec = FOLDS[fold_name]
  valid = labels.loc[label_mask(labels, spec.valid_start, spec.valid_end)]
  trainable = set(trainable_targets(labels, fold_name))
  return [
    target
    for target in TARGET_COLS
    if target in trainable and int((valid[target] >= CAPACITY_KWH[target] * 0.10).sum()) > 0
  ]


def describe_folds(labels, fold_names=None):
  """fold별 행 수·라벨 수·시간 순서를 표로 만든다."""
  rows = []
  for fold_name in fold_names or list(FOLDS):
    spec = FOLDS[fold_name]
    train_start, train_end = train_window_bounds(fold_name)
    train_rows = labels.loc[label_mask(labels, train_start, train_end)]
    valid_rows = labels.loc[label_mask(labels, spec.valid_start, spec.valid_end)]
    scoreable = scoreable_targets(labels, fold_name)
    rows.append(
      {
        "fold": fold_name,
        "방향": spec.direction,
        "검증 연도": spec.valid_year,
        "train 창": spec.train_window,
        "train": f"{train_start[:10]} ~ {train_end[:10]}",
        "valid": f"{spec.valid_start[:10]} ~ {spec.valid_end[:10]}",
        "train 행": len(train_rows),
        "G3 train 라벨": int(train_rows["kpx_group_3"].notna().sum()),
        "valid 행": len(valid_rows),
        "채점 그룹": len(scoreable),
        "겹침 행": int(
          (
            label_mask(labels, train_start, train_end)
            & label_mask(labels, spec.valid_start, spec.valid_end)
          ).sum()
        ),
        "목적": spec.purpose,
      }
    )
  return pd.DataFrame(rows).set_index("fold")


def assert_fold_contract(labels, fold_names=None):
  """fold 정의가 계약을 지키는지 검사한다. 위반하면 예외로 멈춘다.

  - train과 valid가 한 행도 겹치지 않는다
  - 순방향 fold는 train 끝 < valid 시작
  - 역방향 fold는 valid 끝 < train 시작
  - 채점 가능한 그룹이 최소 1개 있다
  """
  errors = []
  for fold_name in fold_names or list(FOLDS):
    spec = FOLDS[fold_name]
    train_start, train_end = train_window_bounds(fold_name)
    overlap = int(
      (
        label_mask(labels, train_start, train_end)
        & label_mask(labels, spec.valid_start, spec.valid_end)
      ).sum()
    )
    if overlap:
      errors.append(f"{fold_name}: train/valid 겹침 {overlap}행")

    if spec.direction == FORWARD:
      if not pd.Timestamp(train_end) < pd.Timestamp(spec.valid_start):
        errors.append(f"{fold_name}: 순방향인데 train 끝이 valid 시작보다 늦다")
    elif spec.direction == BACKWARD:
      if not pd.Timestamp(spec.valid_end) < pd.Timestamp(train_start):
        errors.append(f"{fold_name}: 역방향인데 valid 끝이 train 시작보다 늦다")
    else:
      errors.append(f"{fold_name}: 알 수 없는 방향 {spec.direction!r}")

    if not scoreable_targets(labels, fold_name):
      errors.append(f"{fold_name}: 채점 가능한 그룹이 없다")

  if errors:
    raise ValueError("fold 계약 위반: " + "; ".join(errors))
  return True


def window_predict_ranges(fold_names=None):
  """학습 창별로 예측해야 할 구간 = 그 창을 쓰는 fold들의 valid 합집합."""
  ranges = {}
  for fold_name in fold_names or list(FOLDS):
    spec = FOLDS[fold_name]
    current = ranges.get(spec.train_window)
    if current is None:
      ranges[spec.train_window] = (spec.valid_start, spec.valid_end)
    else:
      ranges[spec.train_window] = (
        min(current[0], spec.valid_start),
        max(current[1], spec.valid_end),
      )
  return ranges


def default_estimator():
  """공식 노트북 파라미터의 RandomForest. GBM은 이 자리에 다른 estimator를 넣는다."""
  from sklearn.ensemble import RandomForestRegressor

  return RandomForestRegressor(**dict(OFFICIAL_RF_PARAMS))


@dataclass(frozen=True)
class WindowRun:
  predictions: pd.DataFrame
  feature_count: int
  skipped_targets: tuple


def run_window(
  config,
  window_name,
  predict_start,
  predict_end,
  *,
  labels,
  ldaps,
  gfs,
  turbine_locations=None,
  make_estimator=None,
):
  """한 학습 창으로 학습해 예측 구간 전체를 예측한다.

  전처리는 전부 train 구간에만 fit한다(설계서 06 3절). 학습 라벨이 0행인 target은
  학습하지 않고 예측을 NaN으로 남긴다 — Group 3의 2022 공백이 여기에 해당한다.
  """
  from sklearn.impute import SimpleImputer

  from baram.feature_pipeline import build_feature_pipeline

  make_estimator = make_estimator or default_estimator
  train_start, train_end = TRAIN_WINDOWS[window_name]
  train_mask = label_mask(labels, train_start, train_end)
  predict_mask = label_mask(labels, predict_start, predict_end)

  pipeline = build_feature_pipeline(
    config,
    train_time_index=labels.loc[train_mask, "kst_dtm"],
    test_time_index=labels.loc[predict_mask, "kst_dtm"],
    train_ldaps=weather_slice(ldaps, train_start, train_end),
    train_gfs=weather_slice(gfs, train_start, train_end),
    test_ldaps=weather_slice(ldaps, predict_start, predict_end),
    test_gfs=weather_slice(gfs, predict_start, predict_end),
    turbine_locations=turbine_locations if config.uses_spatial else None,
  )

  imputer = SimpleImputer(strategy="median")
  train_imputed = pd.DataFrame(
    imputer.fit_transform(pipeline.train_matrix),
    columns=pipeline.feature_columns,
    index=pipeline.train_matrix.index,
  )
  predict_imputed = pd.DataFrame(
    imputer.transform(pipeline.test_matrix),
    columns=pipeline.feature_columns,
    index=pipeline.test_matrix.index,
  )

  predictions = pd.DataFrame(index=labels.loc[predict_mask].index)
  train_subset = labels.loc[train_mask]
  skipped = []
  for target in TARGET_COLS:
    target_columns = list(pipeline.target_feature_columns[target])
    target_labels = train_subset[target]
    non_null = target_labels.notna().to_numpy()
    if not non_null.any():
      predictions[target] = np.nan
      skipped.append(target)
      continue
    model = make_estimator()
    model.fit(train_imputed.loc[non_null, target_columns], target_labels.to_numpy()[non_null])
    predictions[target] = np.clip(
      model.predict(predict_imputed[target_columns]), 0, CAPACITY_KWH[target]
    )
  return WindowRun(
    predictions=predictions,
    feature_count=len(pipeline.feature_columns),
    skipped_targets=tuple(skipped),
  )


def score_fold(labels, predictions, fold_name, columns=None):
  """fold의 검증 구간만 잘라 공식 산식으로 채점한다.

  `columns`를 주지 않으면 그 fold에서 채점 가능한 그룹을 자동으로 고른다.
  """
  spec = FOLDS[fold_name]
  index = labels.loc[label_mask(labels, spec.valid_start, spec.valid_end)].index
  columns = list(columns) if columns is not None else scoreable_targets(labels, fold_name)
  return metric_over(labels.loc[index, TARGET_COLS], predictions.loc[index], columns)


def group_error_terms(labels, predictions, fold_name, columns=None):
  """bootstrap 재표집의 단위 — 그룹별 (평가행 오차율, 실제값) 쌍.

  평가 대상 행을 이미 걸러낸 뒤이므로, 같은 인덱스로 두 모델을 재표집하면
  paired bootstrap이 된다.
  """
  spec = FOLDS[fold_name]
  index = labels.loc[label_mask(labels, spec.valid_start, spec.valid_end)].index
  columns = list(columns) if columns is not None else scoreable_targets(labels, fold_name)
  terms = {}
  for column in columns:
    actual = labels.loc[index, column].to_numpy(dtype=float)
    forecast = predictions.loc[index, column].to_numpy(dtype=float)
    keep = actual >= CAPACITY_KWH[column] * 0.10
    terms[column] = (np.abs(forecast[keep] - actual[keep]) / CAPACITY_KWH[column], actual[keep])
  return terms


def total_from_terms(terms):
  """`group_error_terms()` 결과에서 total_score를 계산한다. 공식 산식과 동일하다."""
  group_nmae, group_ficr = [], []
  for error_rate, actual in terms.values():
    if error_rate.size == 0:
      continue
    group_nmae.append(float(np.mean(error_rate)))
    unit_price = np.select([error_rate <= 0.06, error_rate <= 0.08], [4.0, 3.0], default=0.0)
    group_ficr.append(float(np.sum(actual * unit_price) / np.sum(actual * 4.0)))
  if not group_nmae:
    raise ValueError("채점 가능한 그룹이 없습니다")
  return 0.5 * (1 - float(np.mean(group_nmae))) + 0.5 * float(np.mean(group_ficr))


def paired_bootstrap_gap(terms_a, terms_b, draws=4000, seed=20260727):
  """두 모델의 total_score 차이를 평가행 재표집으로 흔든다.

  같은 재표집 인덱스를 두 모델에 적용하는 paired 방식이라, 표본이 만드는 공통
  변동은 상쇄되고 두 모델의 차이만 남는다(노트북 12와 같은 구조).
  """
  columns = list(terms_a)
  if columns != list(terms_b):
    raise ValueError("두 모델의 채점 그룹이 다릅니다")
  rng = np.random.default_rng(seed)
  gaps = np.empty(draws)
  for draw in range(draws):
    picks = {column: rng.integers(0, terms_a[column][0].size, terms_a[column][0].size) for column in columns}
    resampled_a = {column: (terms_a[column][0][picks[column]], terms_a[column][1][picks[column]]) for column in columns}
    resampled_b = {column: (terms_b[column][0][picks[column]], terms_b[column][1][picks[column]]) for column in columns}
    gaps[draw] = total_from_terms(resampled_a) - total_from_terms(resampled_b)
  return gaps


__all__ = [
  "BACKWARD",
  "FOLDS",
  "FORWARD",
  "FoldSpec",
  "RANK_THRESHOLD",
  "TRAIN_WINDOWS",
  "WindowRun",
  "assert_fold_contract",
  "default_estimator",
  "describe_folds",
  "group_error_terms",
  "label_mask",
  "paired_bootstrap_gap",
  "run_window",
  "score_fold",
  "scoreable_targets",
  "total_from_terms",
  "train_window_bounds",
  "trainable_targets",
  "weather_slice",
  "window_predict_ranges",
]
