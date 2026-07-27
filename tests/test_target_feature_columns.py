import numpy as np
import pandas as pd
import pytest
from sklearn.impute import SimpleImputer

from baram.baseline import (
  predict_random_forest_baseline,
  train_random_forest_baseline,
)
from baram.metrics import CAPACITY_KWH, TARGET_COLS


SUPERSET_COLUMNS = [
  "shared_a",
  "shared_b",
  "pool_group_1_idw",
  "pool_group_2_idw",
  "pool_group_3_idw",
]
OWN_GROUP_COLUMNS = {
  "kpx_group_1": ["shared_a", "shared_b", "pool_group_1_idw"],
  "kpx_group_2": ["shared_a", "shared_b", "pool_group_2_idw"],
  "kpx_group_3": ["shared_a", "shared_b", "pool_group_3_idw"],
}
FAST_RF_PARAMS = {"n_estimators": 8, "max_depth": 4, "n_jobs": 1}


def makeMatrix(rows=64, seed=0, withNaN=True):
  generator = np.random.default_rng(seed)
  frame = pd.DataFrame(
    generator.normal(size=(rows, len(SUPERSET_COLUMNS))),
    columns=SUPERSET_COLUMNS,
  )
  if withNaN:
    frame.loc[frame.index[:5], "shared_b"] = np.nan
    frame.loc[frame.index[7:9], "pool_group_2_idw"] = np.nan
  return frame


def makeLabels(matrix, seed=1):
  generator = np.random.default_rng(seed)
  frame = pd.DataFrame(index=matrix.index)
  for position, target in enumerate(TARGET_COLS):
    frame[target] = (
      1000.0
      + 500.0 * matrix[f"pool_group_{position + 1}_idw"].fillna(0.0)
      + generator.normal(scale=50.0, size=len(matrix))
    )
  frame.loc[frame.index[:3], "kpx_group_3"] = np.nan
  return frame


class TestBackwardCompatibility:
  def test_target_feature_columns를_안_주면_전체를_공유한다(self):
    matrix = makeMatrix()
    labels = makeLabels(matrix)
    bundle = train_random_forest_baseline(matrix, labels, model_params=FAST_RF_PARAMS)
    assert bundle.feature_columns == SUPERSET_COLUMNS
    for target in TARGET_COLS:
      assert bundle.target_feature_columns[target] == SUPERSET_COLUMNS

  def test_명시적_superset은_생략과_같은_예측을_낸다(self):
    matrix = makeMatrix()
    labels = makeLabels(matrix)
    implicit = train_random_forest_baseline(matrix, labels, model_params=FAST_RF_PARAMS)
    explicit = train_random_forest_baseline(
      matrix,
      labels,
      model_params=FAST_RF_PARAMS,
      target_feature_columns={target: list(SUPERSET_COLUMNS) for target in TARGET_COLS},
    )
    pd.testing.assert_frame_equal(
      predict_random_forest_baseline(implicit, matrix),
      predict_random_forest_baseline(explicit, matrix),
    )


class TestOwnGroupSlicing:
  def test_target마다_다른_컬럼으로_학습한다(self):
    matrix = makeMatrix()
    labels = makeLabels(matrix)
    bundle = train_random_forest_baseline(
      matrix,
      labels,
      model_params=FAST_RF_PARAMS,
      target_feature_columns=OWN_GROUP_COLUMNS,
    )
    for target, columns in OWN_GROUP_COLUMNS.items():
      assert bundle.target_feature_columns[target] == columns
      assert bundle.models[target].n_features_in_ == len(columns)

  def test_superset_median_imputation은_부분집합_fit과_같다(self):
    """imputer를 superset에 fit해도 부분집합 컬럼의 대치값이 같아야 한다."""
    matrix = makeMatrix()
    supersetImputer = SimpleImputer(strategy="median").fit(matrix)
    supersetImputed = pd.DataFrame(
      supersetImputer.transform(matrix),
      columns=SUPERSET_COLUMNS,
      index=matrix.index,
    )
    for columns in OWN_GROUP_COLUMNS.values():
      subsetImputer = SimpleImputer(strategy="median").fit(matrix[columns])
      subsetImputed = pd.DataFrame(
        subsetImputer.transform(matrix[columns]),
        columns=columns,
        index=matrix.index,
      )
      pd.testing.assert_frame_equal(supersetImputed[columns], subsetImputed)

  def test_추론도_target별_컬럼으로_슬라이스한다(self):
    matrix = makeMatrix()
    labels = makeLabels(matrix)
    bundle = train_random_forest_baseline(
      matrix,
      labels,
      model_params=FAST_RF_PARAMS,
      target_feature_columns=OWN_GROUP_COLUMNS,
    )
    predictions = predict_random_forest_baseline(bundle, makeMatrix(rows=16, seed=9))
    assert list(predictions.columns) == list(TARGET_COLS)
    assert len(predictions) == 16
    for target in TARGET_COLS:
      assert predictions[target].between(0, CAPACITY_KWH[target]).all()

  def test_추론_입력이_superset이면_컬럼_순서가_달라도_된다(self):
    matrix = makeMatrix()
    labels = makeLabels(matrix)
    bundle = train_random_forest_baseline(
      matrix,
      labels,
      model_params=FAST_RF_PARAMS,
      target_feature_columns=OWN_GROUP_COLUMNS,
    )
    shuffled = makeMatrix(rows=16, seed=9)[list(reversed(SUPERSET_COLUMNS))]
    ordered = makeMatrix(rows=16, seed=9)
    pd.testing.assert_frame_equal(
      predict_random_forest_baseline(bundle, shuffled),
      predict_random_forest_baseline(bundle, ordered),
    )


class TestValidation:
  def test_target이_빠지면_거부한다(self):
    matrix = makeMatrix()
    labels = makeLabels(matrix)
    partial = dict(OWN_GROUP_COLUMNS)
    partial.pop("kpx_group_3")
    with pytest.raises(ValueError, match="target"):
      train_random_forest_baseline(
        matrix,
        labels,
        model_params=FAST_RF_PARAMS,
        target_feature_columns=partial,
      )

  def test_superset에_없는_컬럼을_거부한다(self):
    matrix = makeMatrix()
    labels = makeLabels(matrix)
    invalid = {target: ["shared_a", "ghost"] for target in TARGET_COLS}
    with pytest.raises(ValueError, match="feature matrix에 없는"):
      train_random_forest_baseline(
        matrix,
        labels,
        model_params=FAST_RF_PARAMS,
        target_feature_columns=invalid,
      )

  def test_빈_컬럼_목록을_거부한다(self):
    matrix = makeMatrix()
    labels = makeLabels(matrix)
    empty = {target: [] for target in TARGET_COLS}
    with pytest.raises(ValueError, match="하나 이상"):
      train_random_forest_baseline(
        matrix,
        labels,
        model_params=FAST_RF_PARAMS,
        target_feature_columns=empty,
      )

  def test_추론에_필요한_컬럼이_없으면_거부한다(self):
    matrix = makeMatrix()
    labels = makeLabels(matrix)
    bundle = train_random_forest_baseline(
      matrix,
      labels,
      model_params=FAST_RF_PARAMS,
      target_feature_columns=OWN_GROUP_COLUMNS,
    )
    with pytest.raises(ValueError, match="추론 feature 누락"):
      predict_random_forest_baseline(bundle, matrix.drop(columns=["pool_group_2_idw"]))
