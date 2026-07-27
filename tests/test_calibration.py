"""metric-aware calibration 모듈 검증.

공식 원자료 없이 돌아야 하므로 합성 예측·라벨을 쓴다. 이 파일이 지키는 것 세 가지:

1. 정규화 공간 채점이 `metrics.metric_over()`·`folds.total_from_terms()`와 **같은 값**
2. `bias_mae`와 `bias_metric`이 계단 경계를 심은 데이터에서 **다른 값**을 고른다
   — "metric-aware"가 이름뿐이 아님을 코드 수준에서 고정한다
3. OOF 분할이 시간 순서를 지키고 학습·예측 구간이 겹치지 않는다
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.tree import DecisionTreeRegressor

from baram.calibration import BIAS_GRID
from baram.calibration import CALIBRATORS
from baram.calibration import Calibration
from baram.calibration import apply_calibration
from baram.calibration import band_transition
from baram.calibration import boundary_density
from baram.calibration import decompose_normalized
from baram.calibration import describe_oof_blocks
from baram.calibration import fit_bias_mae
from baram.calibration import fit_bias_metric
from baram.calibration import fit_calibration
from baram.calibration import fold_normalized_terms
from baram.calibration import inner_oof_blocks
from baram.calibration import nmae_normalized
from baram.calibration import normalized_terms
from baram.calibration import oracle_row_bound
from baram.calibration import price_band
from baram.calibration import score_normalized
from baram.feature_config import get_feature_set
from baram.folds import group_error_terms
from baram.folds import total_from_terms
from baram.gbm import run_window_pooled
from baram.metrics import CAPACITY_KWH
from baram.metrics import TARGET_COLS
from baram.metrics import metric_over

from test_feature_pipeline import makeTurbineLocations
from test_feature_pipeline import makeWeatherFrame


HOURS = 400
START = "2024-01-01 01:00"


def makeFrames(seed=3, bias=0.0):
  """평가 대상 행이 충분한 합성 라벨·예측 짝.

  실제값을 설비용량의 30~95%로 두어 전부 평가 대상(10% 이상)이 되게 하고, 예측은
  실제값에 잡음과 `bias`를 더해 만든다. 오차율이 6%·8% 경계 양쪽에 퍼지도록
  잡음 폭을 설비용량의 ±12%로 잡았다.
  """
  generator = np.random.default_rng(seed)
  times = pd.date_range(START, periods=HOURS, freq="h")
  labels = pd.DataFrame({"kst_dtm": times})
  predictions = pd.DataFrame(index=labels.index)
  for column in TARGET_COLS:
    capacity = CAPACITY_KWH[column]
    actual = generator.uniform(0.30, 0.95, size=HOURS)
    noise = generator.uniform(-0.12, 0.12, size=HOURS)
    labels[column] = actual * capacity
    predictions[column] = np.clip(actual + noise + bias, 0.0, 1.0) * capacity
  return labels, predictions


def makeTerms(seed=3, bias=0.0):
  labels, predictions = makeFrames(seed=seed, bias=bias)
  return normalized_terms(labels, predictions, labels.index, TARGET_COLS)


# --------------------------------------------------------------------------------------
# 1. 채점이 공식 산식과 일치한다
# --------------------------------------------------------------------------------------


def testScoreNormalizedMatchesOfficialMetric():
  labels, predictions = makeFrames()
  terms = normalized_terms(labels, predictions, labels.index, TARGET_COLS)

  expected = metric_over(labels[TARGET_COLS], predictions, TARGET_COLS)
  assert score_normalized(terms) == pytest.approx(expected[0], abs=1e-12)


def testDecomposeNormalizedMatchesOfficialThreeWaySplit():
  labels, predictions = makeFrames(seed=11)
  terms = normalized_terms(labels, predictions, labels.index, TARGET_COLS)

  total, oneMinusNmae, ficr = decompose_normalized(terms)
  expected = metric_over(labels[TARGET_COLS], predictions, TARGET_COLS)
  assert (total, oneMinusNmae, ficr) == pytest.approx(expected, abs=1e-12)
  # 재조립도 성립해야 한다 — 전사 오류를 여기서 잡는다 (노트북 12와 같은 검사).
  assert total == pytest.approx(0.5 * oneMinusNmae + 0.5 * ficr, abs=1e-12)


def testScoreNormalizedMatchesFoldTermsPath():
  """`folds.total_from_terms()`는 (오차율, 실제값)을, 이 모듈은 (예측, 실측)을 받는다."""
  labels, predictions = makeFrames(seed=5)
  index = labels.index
  errorTerms = {}
  for column in TARGET_COLS:
    capacity = CAPACITY_KWH[column]
    actual = labels[column].to_numpy(dtype=float)
    forecast = predictions[column].to_numpy(dtype=float)
    keep = actual >= capacity * 0.10
    errorTerms[column] = (np.abs(forecast[keep] - actual[keep]) / capacity, actual[keep])

  terms = normalized_terms(labels, predictions, index, TARGET_COLS)
  assert score_normalized(terms) == pytest.approx(total_from_terms(errorTerms), abs=1e-12)


def testNmaeNormalizedIsOneMinusTheOfficialOneMinusNmae():
  terms = makeTerms(seed=17)
  _, oneMinusNmae, _ = decompose_normalized(terms)
  assert nmae_normalized(terms) == pytest.approx(1.0 - oneMinusNmae, abs=1e-12)


def testPriceBandMatchesOfficialTierEdges():
  # 경계값은 `<=`로 포함된다 — `metrics.py`의 `np.select`와 같은 방향이어야 한다.
  assert list(price_band([0.0, 0.06, 0.060001, 0.08, 0.0800001, 0.5])) == [0, 0, 1, 1, 2, 2]


def testNormalizedTermsKeepsOnlyEvaluationRows():
  labels, predictions = makeFrames(seed=23)
  # 절반을 설비용량 5%로 내려 평가 대상에서 빠지게 만든다.
  half = len(labels) // 2
  for column in TARGET_COLS:
    labels.loc[: half - 1, column] = CAPACITY_KWH[column] * 0.05

  terms = normalized_terms(labels, predictions, labels.index, TARGET_COLS)
  for predicted, actual in terms.values():
    assert predicted.size == len(labels) - half
    assert (actual >= 0.10).all()


def testNormalizedTermsRejectsUnknownColumns():
  labels, predictions = makeFrames()
  with pytest.raises(ValueError, match="알 수 없는 target"):
    normalized_terms(labels, predictions, labels.index, ["kpx_group_9"])


# --------------------------------------------------------------------------------------
# 2. 보정 후보
# --------------------------------------------------------------------------------------


def testRegistryHoldsExactlyThePreRegisteredSix():
  # 후보 수를 누르는 것이 M6 설계의 핵심이다. 조용히 늘면 이 검사가 막는다.
  assert list(CALIBRATORS) == [
    "none",
    "bias_mae",
    "bias_metric",
    "affine_metric",
    "binned_metric",
    "isotonic",
  ]


def testIdentityCalibrationLeavesTheScoreUnchanged():
  terms = makeTerms()
  base = score_normalized(terms)
  assert score_normalized(terms, fit_calibration("none", terms)) == pytest.approx(base, abs=1e-12)


def testFitCalibrationRejectsUnknownName():
  terms = makeTerms()
  with pytest.raises(ValueError, match="등록되지 않은 보정 후보"):
    fit_calibration("bias_magic", terms)


def testFitOnEmptyTermsRaises():
  empty = {column: (np.empty(0), np.empty(0)) for column in TARGET_COLS}
  with pytest.raises(ValueError, match="평가 대상 행이 없습니다"):
    fit_calibration("bias_metric", empty)


@pytest.mark.parametrize("name", list(CALIBRATORS))
def testEveryCandidateNeverLowersTheScoreItWasFitOn(name):
  """fit한 바로 그 데이터에서는 통제군 이상이어야 한다.

  표본 밖 성능을 말하는 검사가 아니다. `b = 0`·`a = 1`이 전부 그리드 안에 있으므로
  fit 데이터에서 통제군보다 나쁘면 탐색이나 목적함수가 깨진 것이다.
  """
  terms = makeTerms(seed=31, bias=0.03)
  base = score_normalized(terms)
  calibration = fit_calibration(name, terms)
  assert score_normalized(terms, calibration) >= base - 1e-12


@pytest.mark.parametrize("bias", [0.04, -0.04])
def testBiasMetricReversesAPlantedBias(bias):
  terms = makeTerms(seed=41, bias=bias)
  fitted = fit_bias_metric(terms)
  # 심은 편향과 반대 부호로, 비슷한 크기만큼 되돌려야 한다.
  assert np.sign(fitted.params["b"]) == -np.sign(bias)
  assert fitted.params["b"] == pytest.approx(-bias, abs=0.015)


def testBiasMaeAndBiasMetricDisagreeOnStepStructuredData():
  """같은 함수 형태·같은 그리드에서 목적함수만 바꿨을 때 결과가 갈려야 한다.

  갈리지 않으면 "metric-aware"는 이름뿐이다. 두 덩어리를 일부러 비대칭으로 둔다.

  - 200행은 오차 6.2%로 **경계 바로 위**에 있다. 0.2%p만 당기면 4원으로 올라간다
  - 400행은 오차 3.0%로 이미 안전하다. 다수이므로 평균은 이쪽으로 끌린다

  MAE만 보면 다수 덩어리의 잔차(+0.030)로 가는 것이 최적이고, 그러면 소수 덩어리는
  오차 9.2%가 되어 **0원으로 떨어진다.** 계단을 보는 쪽은 두 덩어리를 모두 6% 안에
  두는 −0.002를 고른다. 평균은 조금 나빠지고 정산 비율은 1.0이 된다.
  """
  actual = np.full(600, 0.60)
  predicted = np.concatenate([actual[:200] + 0.062, actual[200:] - 0.030])
  terms = {"kpx_group_1": (predicted, actual)}

  maeFit = fit_bias_mae(terms)
  metricFit = fit_bias_metric(terms)

  assert maeFit.params["b"] == pytest.approx(0.030)
  assert metricFit.params["b"] == pytest.approx(-0.002)
  # 계단을 보는 쪽이 경계 위 덩어리를 6% 안으로 끌어내려 총점이 더 높다.
  assert score_normalized(terms, metricFit) > score_normalized(terms, maeFit)
  _, _, metricFicr = decompose_normalized(terms, metricFit)
  _, _, maeFicr = decompose_normalized(terms, maeFit)
  assert metricFicr == pytest.approx(1.0)
  assert maeFicr < metricFicr
  # 그 대가로 평균 오차는 나빠진다. 목적함수가 다르다는 것이 이 부등호다.
  assert nmae_normalized(terms, maeFit) < nmae_normalized(terms, metricFit)


def testBiasFitsStayInsideTheFixedGrid():
  terms = makeTerms(seed=53, bias=0.5)
  fitted = fit_bias_metric(terms)
  # 그리드는 고정값이다. 편향이 그리드보다 크더라도 넘어서 탐색하지 않는다.
  assert fitted.params["b"] in set(BIAS_GRID.tolist())


def testAffineRecoversAPlantedSlopeShrinkage():
  """평균으로 수축한 예측을 심으면 기울기가 1보다 커야 한다."""
  generator = np.random.default_rng(61)
  actual = generator.uniform(0.20, 0.95, size=800)
  center = actual.mean()
  # 실제값을 중심으로 0.7배 수축 — 트리 모델의 전형적인 편향 방향이다.
  predicted = center + 0.7 * (actual - center)
  terms = {"kpx_group_1": (predicted, actual)}

  fitted = fit_calibration("affine_metric", terms)
  assert fitted.params["a"] > 1.0
  assert score_normalized(terms, fitted) > score_normalized(terms)


def testBinnedCalibrationCorrectsDirectionDependentBias():
  """예측 수준에 따라 편향의 방향이 다르면 단일 bias는 못 잡고 구간별은 잡는다."""
  generator = np.random.default_rng(71)
  actual = generator.uniform(0.20, 0.95, size=900)
  predicted = actual.copy()
  low = actual < 0.4
  high = actual > 0.75
  predicted[low] += 0.07
  predicted[high] -= 0.07
  terms = {"kpx_group_1": (np.clip(predicted, 0.0, 1.0), actual)}

  binned = fit_calibration("binned_metric", terms)
  single = fit_bias_metric(terms)
  assert score_normalized(terms, binned) > score_normalized(terms, single)
  assert len(binned.params["offsets"]) == len(binned.params["edges"]) + 1


def testIsotonicIsMonotoneOnTheUnitInterval():
  terms = makeTerms(seed=83, bias=0.02)
  fitted = fit_calibration("isotonic", terms)
  grid = np.linspace(0.0, 1.0, 101)
  mapped = fitted(grid)
  assert np.all(np.diff(mapped) >= -1e-12)
  assert mapped.min() >= 0.0 and mapped.max() <= 1.0


def testCalibrationCallClipsToTheUnitInterval():
  calibration = Calibration("test", {"b": 5.0}, lambda values: values + 5.0)
  assert calibration([0.1, 0.9]).tolist() == [1.0, 1.0]
  calibration = Calibration("test", {"b": -5.0}, lambda values: values - 5.0)
  assert calibration([0.1, 0.9]).tolist() == [0.0, 0.0]


@pytest.mark.parametrize("name", list(CALIBRATORS))
def testEveryCandidateAcceptsAnEmptyGroup(name):
  """평가 대상 행이 0개인 그룹은 정상이다 — W_2022에는 Group 3 라벨이 없다.

  fold마다 채점 그룹이 다르므로 빈 그룹이 섞인 terms가 그대로 채점에 들어온다.
  sklearn의 isotonic은 빈 입력을 예외로 거절하므로 `Calibration.__call__`이 막아야 한다.
  """
  terms = makeTerms(seed=167)
  terms["kpx_group_3"] = (np.empty(0), np.empty(0))
  calibration = fit_calibration(name, terms)

  assert calibration(np.empty(0)).size == 0
  # 빈 그룹이 섞여 있어도 채점·분해·밴드 이동이 모두 끝까지 돌아야 한다.
  assert np.isfinite(score_normalized(terms, calibration))
  assert np.isfinite(decompose_normalized(terms, calibration)[0])
  assert "kpx_group_3" not in band_transition(terms, calibration).index


def testDescribeRendersParametersForTheNotebookTable():
  assert Calibration("none").describe() == "항등"
  assert Calibration("bias", {"b": 0.0125}).describe() == "b=+0.0125"
  rendered = Calibration("binned", {"offsets": [0.01, -0.02]}).describe()
  assert rendered == "offsets=[+0.0100, -0.0200]"


# --------------------------------------------------------------------------------------
# 3. 진단 — 오라클 상한, 밴드 이동, 경계 밀도
# --------------------------------------------------------------------------------------


def testOracleBoundWithZeroDeltaEqualsTheBaseScore():
  terms = makeTerms(seed=97)
  assert oracle_row_bound(terms, 0.0) == pytest.approx(score_normalized(terms), abs=1e-12)


def testOracleBoundIsMonotoneInDelta():
  terms = makeTerms(seed=101)
  bounds = [oracle_row_bound(terms, delta) for delta in [0.0, 0.005, 0.01, 0.02]]
  assert bounds == sorted(bounds)


@pytest.mark.parametrize("name", list(CALIBRATORS))
def testOracleBoundDominatesEveryCandidateWithinItsShiftBudget(name):
  """행별 보정 크기가 delta 이하인 어떤 보정도 상한을 넘을 수 없다."""
  terms = makeTerms(seed=103, bias=0.02)
  calibration = fit_calibration(name, terms)
  shifts = [
    np.abs(calibration(predicted) - predicted).max()
    for predicted, _ in terms.values()
    if predicted.size
  ]
  budget = float(max(shifts)) if shifts else 0.0
  assert score_normalized(terms, calibration) <= oracle_row_bound(terms, budget) + 1e-12


def testOracleBoundRejectsNegativeDelta():
  with pytest.raises(ValueError, match="delta는 0 이상"):
    oracle_row_bound(makeTerms(), -0.01)


def testBandTransitionCountsHandCheckedMoves():
  actual = np.array([0.5, 0.5, 0.5, 0.5])
  # 오차율 3% / 7% / 7% / 9% → 밴드 0 / 1 / 1 / 2
  predicted = np.array([0.53, 0.57, 0.57, 0.59])
  terms = {"kpx_group_1": (predicted, actual)}
  # 일괄 −0.01: 오차 2% / 6% / 6% / 8% → 밴드 0 / 0 / 0 / 1. 셋이 좋아지고 하나는 그대로.
  calibration = Calibration("shift", {"b": -0.01}, lambda values: values - 0.01)

  frame = band_transition(terms, calibration)
  assert int(frame.loc["kpx_group_1", "밴드 이동"]) == 3
  assert int(frame.loc["kpx_group_1", "좋아짐"]) == 3
  assert int(frame.loc["kpx_group_1", "나빠짐"]) == 0
  assert int(frame.loc["kpx_group_1", "순증"]) == 3
  assert int(frame.loc["합계", "평가 행"]) == 4


def testBandTransitionNetsOutOffsettingMoves():
  actual = np.array([0.5, 0.5])
  # 오차율 5%(밴드 0)와 7%(밴드 1). +0.02를 더하면 7%(밴드 1)와 9%(밴드 2)가 된다.
  predicted = np.array([0.55, 0.57])
  terms = {"kpx_group_1": (predicted, actual)}
  calibration = Calibration("shift", {"b": 0.02}, lambda values: values + 0.02)

  frame = band_transition(terms, calibration)
  assert int(frame.loc["합계", "나빠짐"]) == 2
  assert int(frame.loc["합계", "순증"]) == -2


def testBoundaryDensityBandsSumToOne():
  frame = boundary_density(makeTerms(seed=107))
  ratios = frame[["4원 비율", "3원 비율", "0원 비율"]].sum(axis=1)
  assert ratios.to_numpy() == pytest.approx(np.ones(len(frame)), abs=1e-12)


def testBoundaryDensityCountsRowsNearEitherEdge():
  actual = np.full(4, 0.5)
  # 오차율 1% / 5.5% / 8.5% / 20% → 경계 ±1%p 안에 있는 것은 가운데 둘이다.
  predicted = np.array([0.51, 0.555, 0.585, 0.70])
  frame = boundary_density({"kpx_group_1": (predicted, actual)}, window=0.01)
  assert frame.loc["kpx_group_1", "경계 ±1% 비율"] == pytest.approx(0.5)


# --------------------------------------------------------------------------------------
# 4. OOF 분할 계약
# --------------------------------------------------------------------------------------


def testInnerOofBlocksSplitsIntoExpandingWindows():
  splits = inner_oof_blocks("2022-01-01 01:00", "2023-12-31 23:00", blocks=4)

  assert [split.block for split in splits] == [1, 2, 3]
  for split in splits:
    assert split.train_start == pd.Timestamp("2022-01-01 01:00")
    assert split.train_end < split.predict_start
    assert split.predict_start <= split.predict_end
  # expanding이므로 학습 끝이 블록마다 뒤로 밀린다.
  assert splits[0].train_end < splits[1].train_end < splits[2].train_end
  # 예측 블록끼리 겹치지 않고 이어진다.
  assert splits[0].predict_end < splits[1].predict_start
  assert splits[1].predict_end < splits[2].predict_start
  # 마지막 블록이 창의 끝까지 덮는다.
  assert splits[-1].predict_end == pd.Timestamp("2023-12-31 23:00")


def testInnerOofBlocksBoundsFeedRunWindowPooledDirectly():
  split = inner_oof_blocks("2023-01-01 01:00", "2023-12-31 23:00")[0]
  assert split.bounds == (split.train_start, split.train_end)


def testInnerOofBlocksCoversTheTailOfTheWindow():
  splits = inner_oof_blocks("2023-01-01 00:00", "2023-12-31 23:00", blocks=4)
  window = pd.Timestamp("2023-12-31 23:00") - pd.Timestamp("2023-01-01 00:00")
  covered = splits[-1].predict_end - splits[0].predict_start
  assert covered / window == pytest.approx(0.75, abs=0.01)


def testInnerOofBlocksRejectsBadArguments():
  with pytest.raises(ValueError, match="시작이 끝보다 늦다"):
    inner_oof_blocks("2024-01-01 00:00", "2023-01-01 00:00")
  with pytest.raises(ValueError, match="blocks는 2 이상"):
    inner_oof_blocks("2023-01-01 00:00", "2023-12-31 23:00", blocks=1)
  with pytest.raises(ValueError, match="너무 짧다"):
    inner_oof_blocks("2023-01-01 00:00", "2023-01-01 02:00", blocks=8)


def testDescribeOofBlocksReportsNoOverlap():
  labels, _ = makeFrames()
  frame = describe_oof_blocks(labels, "W_TEST", (START, str(labels["kst_dtm"].max())))
  assert len(frame) == 3
  assert (frame["겹침 행"] == 0).all()
  assert (frame["train 행"] > 0).all()
  assert (frame["OOF 행"] > 0).all()


# --------------------------------------------------------------------------------------
# 5. 예측 프레임에 적용
# --------------------------------------------------------------------------------------


def testApplyCalibrationStaysInsideCapacityAndKeepsShape():
  labels, predictions = makeFrames(seed=113)
  calibration = Calibration("shift", {"b": 0.5}, lambda values: values + 0.5)
  calibrated = apply_calibration(predictions, calibration)

  assert list(calibrated.columns) == list(predictions.columns)
  assert calibrated.index.equals(predictions.index)
  for column in TARGET_COLS:
    assert calibrated[column].min() >= 0.0
    assert calibrated[column].max() <= CAPACITY_KWH[column]


def testApplyCalibrationDoesNotMutateTheInput():
  labels, predictions = makeFrames(seed=127)
  before = predictions.copy()
  apply_calibration(predictions, Calibration("shift", {"b": 0.1}, lambda v: v + 0.1))
  assert predictions.equals(before)


def testApplyCalibrationPreservesMissingPredictions():
  """학습 라벨이 없어 NaN으로 남은 target을 0으로 채우면 없는 예측을 만들어내는 셈이다."""
  labels, predictions = makeFrames(seed=131)
  predictions["kpx_group_3"] = np.nan
  calibrated = apply_calibration(
    predictions, Calibration("shift", {"b": 0.1}, lambda values: values + 0.1)
  )
  assert calibrated["kpx_group_3"].isna().all()
  assert calibrated["kpx_group_1"].notna().all()


def testApplyCalibrationMatchesScoringOnTheSameRows():
  """프레임 경로와 terms 경로가 같은 점수를 내야 한다 — 둘이 갈리면 노트북이 거짓말한다."""
  labels, predictions = makeFrames(seed=137, bias=0.03)
  terms = normalized_terms(labels, predictions, labels.index, TARGET_COLS)
  calibration = fit_bias_metric(terms)

  viaTerms = score_normalized(terms, calibration)
  calibrated = apply_calibration(predictions, calibration)
  viaFrame = metric_over(labels[TARGET_COLS], calibrated, TARGET_COLS)[0]
  assert viaTerms == pytest.approx(viaFrame, abs=1e-12)


# --------------------------------------------------------------------------------------
# 6. fold 경로와 pooled 학습 경로 연결
# --------------------------------------------------------------------------------------


def testFoldNormalizedTermsMatchesFoldErrorTerms():
  """`fold_normalized_terms()`가 `folds.group_error_terms()`와 같은 행을 고른다."""
  generator = np.random.default_rng(149)
  times = pd.date_range("2024-01-01 00:00", "2024-12-31 23:00", freq="h")
  labels = pd.DataFrame({"kst_dtm": times})
  predictions = pd.DataFrame(index=labels.index)
  for column in TARGET_COLS:
    capacity = CAPACITY_KWH[column]
    actual = generator.uniform(0.05, 0.95, size=len(times))
    labels[column] = actual * capacity
    predictions[column] = np.clip(actual + generator.uniform(-0.1, 0.1, len(times)), 0, 1) * capacity

  terms = fold_normalized_terms(labels, predictions, "F0", columns=TARGET_COLS)
  errorTerms = group_error_terms(labels, predictions, "F0", columns=TARGET_COLS)
  for column in TARGET_COLS:
    predicted, actual = terms[column]
    errorRate, errorActual = errorTerms[column]
    assert predicted.size == errorRate.size
    assert np.abs(predicted - actual) == pytest.approx(errorRate, abs=1e-12)
    assert actual * CAPACITY_KWH[column] == pytest.approx(errorActual, abs=1e-6)


def testRunWindowPooledTrainBoundsMatchesRegisteredWindow(monkeypatch):
  """`train_bounds`가 등록된 창과 같은 구간을 받으면 결과가 같아야 한다."""
  import baram.gbm as gbmModule

  trainStart, trainHours = "2023-01-01 01:00", 72
  trainEnd = str(pd.Timestamp(trainStart) + pd.Timedelta(hours=trainHours - 1))
  predictStart, predictHours = "2023-02-01 01:00", 24
  predictEnd = str(pd.Timestamp(predictStart) + pd.Timedelta(hours=predictHours - 1))
  monkeypatch.setitem(gbmModule.TRAIN_WINDOWS, "W_TEST", (trainStart, trainEnd))

  times = pd.DatetimeIndex(
    list(pd.date_range(trainStart, periods=trainHours, freq="h"))
    + list(pd.date_range(predictStart, periods=predictHours, freq="h"))
  )
  generator = np.random.default_rng(151)
  labels = pd.DataFrame({"kst_dtm": times})
  for column in TARGET_COLS:
    labels[column] = generator.uniform(0.2, 0.9, size=len(times)) * CAPACITY_KWH[column]

  config = get_feature_set("spatial_idw2_all_group")
  shared = {
    "labels": labels,
    "ldaps": makeWeatherFrame("ldaps", start=trainStart, periods=trainHours + 24 * 32, seed=11),
    "gfs": makeWeatherFrame("gfs", start=trainStart, periods=trainHours + 24 * 32, seed=12),
    "turbine_locations": makeTurbineLocations(),
    "make_estimator": lambda: DecisionTreeRegressor(max_depth=4, random_state=42),
  }

  byName = run_window_pooled(config, "W_TEST", predictStart, predictEnd, **shared)
  byBounds = run_window_pooled(
    config, "무명 구간", predictStart, predictEnd, train_bounds=(trainStart, trainEnd), **shared
  )

  assert byBounds.predictions.equals(byName.predictions)
  assert byBounds.train_rows == byName.train_rows
  assert byBounds.trained_targets == byName.trained_targets


def testRunWindowPooledAcceptsTimestampBoundsFromOofBlocks(monkeypatch):
  """`inner_oof_blocks()`가 돌려주는 Timestamp 짝이 그대로 학습 구간이 된다."""
  trainStart, hours = "2023-01-01 01:00", 96
  windowEnd = str(pd.Timestamp(trainStart) + pd.Timedelta(hours=hours - 1))
  split = inner_oof_blocks(trainStart, windowEnd, blocks=4)[-1]

  times = pd.date_range(trainStart, periods=hours, freq="h")
  generator = np.random.default_rng(157)
  labels = pd.DataFrame({"kst_dtm": times})
  for column in TARGET_COLS:
    labels[column] = generator.uniform(0.2, 0.9, size=len(times)) * CAPACITY_KWH[column]

  run = run_window_pooled(
    get_feature_set("official_mean"),
    "OOF 블록",
    split.predict_start,
    split.predict_end,
    labels=labels,
    ldaps=makeWeatherFrame("ldaps", start=trainStart, periods=hours, seed=21),
    gfs=makeWeatherFrame("gfs", start=trainStart, periods=hours, seed=22),
    make_estimator=lambda: DecisionTreeRegressor(max_depth=3, random_state=42),
    train_bounds=split.bounds,
  )

  predictRows = labels[
    (labels["kst_dtm"] >= split.predict_start) & (labels["kst_dtm"] <= split.predict_end)
  ]
  assert len(run.predictions) == len(predictRows)
  assert run.predictions.notna().all().all()
