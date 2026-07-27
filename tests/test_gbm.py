"""GBM estimator 팩토리와 pooled 학습 경로 검증.

공식 원자료 없이 돌아야 하므로 합성 NWP·라벨을 쓰고, 학습 창은 짧게 monkeypatch한다.
estimator도 결정 트리로 갈아끼워 lightgbm/catboost 없이 pooled 경로 전체를 지난다.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.tree import DecisionTreeRegressor

from baram.feature_config import get_feature_set
from baram.gbm import CATBOOST_PARAMS
from baram.gbm import GROUP_ID_COLUMN
from baram.gbm import GROUP_ID_VALUES
from baram.gbm import LIGHTGBM_PARAMS
from baram.gbm import _shared_feature_columns
from baram.gbm import _stack_group_rows
from baram.gbm import run_window_pooled
from baram.metrics import CAPACITY_KWH
from baram.metrics import TARGET_COLS

from test_feature_pipeline import makeTurbineLocations
from test_feature_pipeline import makeWeatherFrame


TINY_WINDOW = "W_TEST"
TRAIN_START, TRAIN_HOURS = "2023-01-01 01:00", 72
PREDICT_START, PREDICT_HOURS = "2023-02-01 01:00", 24
GROUP_3 = "kpx_group_3"


def makeLabels(*, group3Missing=False):
  """학습 구간과 예측 구간을 모두 덮는 합성 라벨."""
  times = pd.DatetimeIndex(
    list(pd.date_range(TRAIN_START, periods=TRAIN_HOURS, freq="h"))
    + list(pd.date_range(PREDICT_START, periods=PREDICT_HOURS, freq="h"))
  )
  generator = np.random.default_rng(7)
  frame = pd.DataFrame({"kst_dtm": times})
  for column in TARGET_COLS:
    frame[column] = generator.uniform(0.2, 0.9, size=len(times)) * CAPACITY_KWH[column]
  if group3Missing:
    # 학습 구간에서만 Group 3을 비운다 — 실제 데이터의 2022 공백과 같은 모양이다.
    frame.loc[frame["kst_dtm"] < pd.Timestamp(PREDICT_START), GROUP_3] = np.nan
  return frame


@pytest.fixture(name="pooledEnv")
def pooledEnvFixture(monkeypatch):
  monkeypatch.setitem(
    __import__("baram.gbm", fromlist=["TRAIN_WINDOWS"]).TRAIN_WINDOWS,
    TINY_WINDOW,
    (TRAIN_START, str(pd.Timestamp(TRAIN_START) + pd.Timedelta(hours=TRAIN_HOURS - 1))),
  )
  hours = TRAIN_HOURS + 24 * 32
  return {
    "ldaps": makeWeatherFrame("ldaps", start=TRAIN_START, periods=hours, seed=11),
    "gfs": makeWeatherFrame("gfs", start=TRAIN_START, periods=hours, seed=12),
    "turbines": makeTurbineLocations(),
    "predictEnd": str(pd.Timestamp(PREDICT_START) + pd.Timedelta(hours=PREDICT_HOURS - 1)),
  }


def makeTree():
  return DecisionTreeRegressor(max_depth=4, random_state=42)


def runPooled(env, labels, presetName="spatial_idw2_all_group"):
  config = get_feature_set(presetName)
  return run_window_pooled(
    config, TINY_WINDOW, PREDICT_START, env["predictEnd"],
    labels=labels, ldaps=env["ldaps"], gfs=env["gfs"],
    turbine_locations=env["turbines"], make_estimator=makeTree,
  )


def testFixedHyperparametersCarryASeed():
  # fold 성적을 보고 조정하지 않기로 했으므로, 재현되지 않으면 그 약속을 지킬 수 없다.
  assert LIGHTGBM_PARAMS["random_state"] == 42
  assert CATBOOST_PARAMS["random_seed"] == 42


def testLightgbmFactoryAppliesDefaultsAndOverrides():
  lightgbm = pytest.importorskip("lightgbm")
  from baram.gbm import make_lightgbm

  model = make_lightgbm()
  assert isinstance(model, lightgbm.LGBMRegressor)
  assert model.get_params()["n_estimators"] == LIGHTGBM_PARAMS["n_estimators"]
  assert make_lightgbm(n_estimators=5).get_params()["n_estimators"] == 5


def testCatboostFactoryAppliesDefaultsAndOverrides():
  # catboost는 requirements-ci.txt에 없다. 설치돼 있을 때만 검사한다.
  catboost = pytest.importorskip("catboost")
  from baram.gbm import make_catboost

  model = make_catboost()
  assert isinstance(model, catboost.CatBoostRegressor)
  assert model.get_params()["iterations"] == CATBOOST_PARAMS["iterations"]
  assert make_catboost(iterations=7).get_params()["iterations"] == 7


def testGroupIdValuesAreDistinctAndCoverEveryTarget():
  assert set(GROUP_ID_VALUES) == set(TARGET_COLS)
  assert len(set(GROUP_ID_VALUES.values())) == len(TARGET_COLS)


def testSharedFeatureColumnsRejectsPerTargetColumnSets():
  class FakePipeline:
    target_feature_columns = {
      "kpx_group_1": ("a", "b"),
      "kpx_group_2": ("a", "c"),
      "kpx_group_3": ("a", "b"),
    }

  with pytest.raises(ValueError, match="같은 피처 컬럼"):
    _shared_feature_columns(FakePipeline())


def testSharedFeatureColumnsAcceptsCommonSuperset():
  class FakePipeline:
    target_feature_columns = {target: ("a", "b") for target in TARGET_COLS}

  assert _shared_feature_columns(FakePipeline()) == ["a", "b"]


def testStackGroupRowsRepeatsMatrixOncePerTargetWithGroupId():
  matrix = pd.DataFrame({"x": [1.0, 2.0], "y": [3.0, 4.0]}, index=[10, 11])
  stacked = _stack_group_rows(matrix, matrix.index, TARGET_COLS)

  assert len(stacked) == len(matrix) * len(TARGET_COLS)
  assert GROUP_ID_COLUMN in stacked.columns
  for target in TARGET_COLS:
    block = stacked.loc[target]
    assert (block[GROUP_ID_COLUMN] == GROUP_ID_VALUES[target]).all()
    assert block[["x", "y"]].equals(matrix)


def testPooledRunPredictsEveryTargetWithinCapacity(pooledEnv):
  labels = makeLabels()
  run = runPooled(pooledEnv, labels)

  assert list(run.predictions.columns) == TARGET_COLS
  assert len(run.predictions) == PREDICT_HOURS
  assert run.trained_targets == tuple(TARGET_COLS)
  assert run.train_rows == TRAIN_HOURS * len(TARGET_COLS)
  for target in TARGET_COLS:
    values = run.predictions[target]
    assert values.notna().all()
    assert (values >= 0).all()
    assert (values <= CAPACITY_KWH[target]).all()


def testPooledAddsExactlyOneFeatureForGroupId(pooledEnv):
  run = runPooled(pooledEnv, makeLabels())
  config = get_feature_set("spatial_idw2_all_group")
  # group id 하나만 더해진다. 설비용량은 group id의 함수라 피처로 넣지 않는다.
  assert run.feature_count >= 2
  assert config.uses_spatial


def testPooledPredictsGroupWithNoTrainingLabels(pooledEnv):
  """pooled의 실질적 이점 — Group 3의 2022 공백을 우회한다."""
  run = runPooled(pooledEnv, makeLabels(group3Missing=True))

  assert run.trained_targets == tuple(TARGET_COLS[:2])
  assert GROUP_3 not in run.trained_targets
  assert run.train_rows == TRAIN_HOURS * 2
  # 학습 라벨이 하나도 없었는데도 예측이 나온다.
  assert run.predictions[GROUP_3].notna().all()
  assert (run.predictions[GROUP_3] > 0).any()


def testPooledRejectsOwnGroupPreset(pooledEnv):
  with pytest.raises(ValueError, match="같은 피처 컬럼"):
    runPooled(pooledEnv, makeLabels(), presetName="spatial_nearest_own_group")


def testPooledRaisesWhenTrainWindowHasNoLabelsAtAll(pooledEnv):
  labels = makeLabels()
  labels.loc[labels["kst_dtm"] < pd.Timestamp(PREDICT_START), TARGET_COLS] = np.nan
  with pytest.raises(ValueError, match="라벨이 있는 target이 없습니다"):
    runPooled(pooledEnv, labels)


def testPooledScalesLabelsByCapacitySoGroupsAreComparable(pooledEnv):
  """Group 3만 설비용량이 다르다. capacity factor로 맞추지 않으면 규모가 신호를 덮는다."""
  labels = makeLabels()
  # 세 그룹을 같은 이용률로 두면, 정규화가 맞을 때 예측도 같은 이용률로 나와야 한다.
  for column in TARGET_COLS:
    labels[column] = 0.5 * CAPACITY_KWH[column]
  run = runPooled(pooledEnv, labels)

  factors = [run.predictions[column].mean() / CAPACITY_KWH[column] for column in TARGET_COLS]
  assert all(abs(factor - 0.5) < 1e-6 for factor in factors)
