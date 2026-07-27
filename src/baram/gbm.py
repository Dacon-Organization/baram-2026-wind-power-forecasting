"""GBM 후보 estimator와 pooled 학습 경로.

설계서 04 7.1절의 M2(그룹별 GBM)와 M3(pooled GBM + group id)를 구현한다.
M2는 `folds.run_window(..., make_estimator=...)`에 estimator만 갈아끼우면 되므로
여기서는 **estimator 팩토리**와 **pooled 학습 경로**만 제공한다.

하이퍼파라미터는 고정값이다. fold 성적을 보고 조정하면 그 fold가 검증셋이 아니라
학습셋이 되며, 설계서 06 5.1절이 경고한 holdout 과적합이 시작된다
(노트북 15 Decision Box ㉔).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from baram.folds import TRAIN_WINDOWS
from baram.folds import label_mask
from baram.folds import weather_slice
from baram.metrics import CAPACITY_KWH
from baram.metrics import TARGET_COLS


# 고정 하이퍼파라미터. 550개 피처에 1.3만 행이라 정규화를 우선한다.
LIGHTGBM_PARAMS = {
  "n_estimators": 800,
  "learning_rate": 0.03,
  "num_leaves": 31,
  "min_child_samples": 30,
  "colsample_bytree": 0.5,
  "subsample": 0.8,
  "subsample_freq": 1,
  "reg_lambda": 1.0,
  "random_state": 42,
  "n_jobs": -1,
  "verbose": -1,
}

CATBOOST_PARAMS = {
  "iterations": 1500,
  "learning_rate": 0.03,
  "depth": 6,
  "l2_leaf_reg": 3.0,
  "rsm": 0.5,
  "random_seed": 42,
  "verbose": 0,
  "allow_writing_files": False,
}

# pooled 학습에서 그룹을 구분하는 피처 이름.
GROUP_ID_COLUMN = "pooled_group_id"
GROUP_ID_VALUES = {target: index + 1 for index, target in enumerate(TARGET_COLS)}


def make_lightgbm(**overrides):
  """LightGBM estimator 팩토리. 라이브러리는 호출 시점에만 필요하다."""
  from lightgbm import LGBMRegressor

  return LGBMRegressor(**{**LIGHTGBM_PARAMS, **overrides})


def make_catboost(**overrides):
  """CatBoost estimator 팩토리. 라이브러리는 호출 시점에만 필요하다."""
  from catboost import CatBoostRegressor

  return CatBoostRegressor(**{**CATBOOST_PARAMS, **overrides})


@dataclass(frozen=True)
class PooledRun:
  predictions: pd.DataFrame
  feature_count: int
  trained_targets: tuple
  train_rows: int


def _shared_feature_columns(pipeline):
  """세 target이 같은 피처 컬럼을 쓰는지 확인하고 그 컬럼을 돌려준다.

  own_group 프리셋은 target마다 컬럼이 다르므로 그대로는 행을 쌓을 수 없다.
  pooled는 all_group 스코프(또는 공간 피처가 없는 프리셋)에서만 정의된다.
  """
  columns = {target: tuple(pipeline.target_feature_columns[target]) for target in TARGET_COLS}
  distinct = set(columns.values())
  if len(distinct) != 1:
    raise ValueError(
      "pooled 학습은 세 target이 같은 피처 컬럼을 쓸 때만 가능합니다. "
      "own_group 프리셋은 target별로 컬럼이 다르므로 all_group 프리셋을 쓰세요"
    )
  return list(distinct.pop())


def _stack_group_rows(matrix, frame_index, targets):
  """target별로 같은 행렬을 복제하고 group id를 붙여 세로로 쌓는다."""
  blocks = []
  for target in targets:
    block = matrix.copy()
    block[GROUP_ID_COLUMN] = GROUP_ID_VALUES[target]
    block.index = pd.MultiIndex.from_product([[target], frame_index], names=["target", "row"])
    blocks.append(block)
  return pd.concat(blocks)


def run_window_pooled(
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
  """세 그룹을 한 모델로 학습한다 (설계서 04 M3).

  라벨은 **설비용량으로 나눠** capacity factor로 맞춘다. Group 3만 21.0 MW라
  원단위로 쌓으면 모델이 그룹 간 규모 차이를 먼저 학습해 버린다.

  pooled의 실질적 이점은 **학습 라벨이 없는 그룹도 예측할 수 있다**는 것이다.
  Group 3은 2022 라벨이 0행이지만, 2022로 학습한 pooled 모델은 group id만 바꿔
  Group 3을 예측한다. `trained_targets`가 실제로 라벨을 기여한 target을 기록한다.
  """
  from sklearn.impute import SimpleImputer

  from baram.feature_pipeline import build_feature_pipeline

  make_estimator = make_estimator or make_lightgbm
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
  feature_columns = _shared_feature_columns(pipeline)

  imputer = SimpleImputer(strategy="median")
  train_imputed = pd.DataFrame(
    imputer.fit_transform(pipeline.train_matrix),
    columns=pipeline.feature_columns,
    index=pipeline.train_matrix.index,
  )[feature_columns]
  predict_imputed = pd.DataFrame(
    imputer.transform(pipeline.test_matrix),
    columns=pipeline.feature_columns,
    index=pipeline.test_matrix.index,
  )[feature_columns]

  train_subset = labels.loc[train_mask]
  trained = [target for target in TARGET_COLS if int(train_subset[target].notna().sum()) > 0]
  if not trained:
    raise ValueError(f"{window_name} 학습 창에 라벨이 있는 target이 없습니다")

  stacked = _stack_group_rows(train_imputed, train_subset.index, trained)
  # 라벨을 설비용량으로 나눠 그룹 간 규모 차이를 제거한다.
  stacked_labels = pd.concat(
    [train_subset[target] / CAPACITY_KWH[target] for target in trained],
    keys=trained,
    names=["target", "row"],
  )
  keep = stacked_labels.notna().to_numpy()

  model = make_estimator()
  model.fit(stacked.loc[keep], stacked_labels.to_numpy()[keep])

  predictions = pd.DataFrame(index=labels.loc[predict_mask].index)
  for target in TARGET_COLS:
    block = predict_imputed.copy()
    block[GROUP_ID_COLUMN] = GROUP_ID_VALUES[target]
    capacity = CAPACITY_KWH[target]
    predictions[target] = np.clip(model.predict(block) * capacity, 0, capacity)

  return PooledRun(
    predictions=predictions,
    feature_count=len(feature_columns) + 1,
    trained_targets=tuple(trained),
    train_rows=int(keep.sum()),
  )


__all__ = [
  "CATBOOST_PARAMS",
  "GROUP_ID_COLUMN",
  "GROUP_ID_VALUES",
  "LIGHTGBM_PARAMS",
  "PooledRun",
  "make_catboost",
  "make_lightgbm",
  "run_window_pooled",
]
