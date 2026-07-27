"""fold 정의 계약과 채점 헬퍼 검증.

공식 원자료 없이 돌아야 하므로, 실제 라벨의 **가용성 구조만** 재현한 합성 프레임을 쓴다.
핵심 구조는 하나다 — Group 3은 2023년부터 라벨이 있다.
"""

import numpy as np
import pandas as pd
import pytest

from baram.folds import BACKWARD
from baram.folds import FOLDS
from baram.folds import FORWARD
from baram.folds import FoldSpec
from baram.folds import TRAIN_WINDOWS
from baram.folds import assert_fold_contract
from baram.folds import describe_folds
from baram.folds import group_error_terms
from baram.folds import label_mask
from baram.folds import paired_bootstrap_gap
from baram.folds import scoreable_targets
from baram.folds import total_from_terms
from baram.folds import train_window_bounds
from baram.folds import trainable_targets
from baram.folds import weather_slice
from baram.folds import window_predict_ranges
from baram.metrics import CAPACITY_KWH
from baram.metrics import TARGET_COLS
from baram.metrics import metric
from baram.metrics import metric_over


GROUP_3 = "kpx_group_3"


def makeLabels():
  """실제 라벨의 시간 범위와 Group 3 공백을 재현한 합성 프레임."""
  times = pd.date_range("2022-01-01 01:00", "2025-01-01 00:00", freq="h")
  rng = np.random.default_rng(20260727)
  frame = pd.DataFrame({"kst_dtm": times})
  for column in TARGET_COLS:
    frame[column] = rng.uniform(0, CAPACITY_KWH[column], size=len(times))
  frame.loc[frame["kst_dtm"].dt.year == 2022, GROUP_3] = np.nan
  return frame


def makePredictions(labels, index, offset):
  """실제값에서 일정량 벗어난 예측. offset이 클수록 점수가 낮다."""
  return pd.DataFrame(
    {column: labels.loc[index, column].to_numpy(dtype=float) + offset for column in TARGET_COLS},
    index=index,
  )


@pytest.fixture(name="labels")
def labelsFixture():
  return makeLabels()


def testFoldContractHoldsForEveryDefinedFold(labels):
  assert assert_fold_contract(labels) is True


def testForwardFoldsKeepTimeOrderAndBackwardFoldsInvertIt():
  for name, spec in FOLDS.items():
    trainStart, trainEnd = train_window_bounds(name)
    if spec.direction == FORWARD:
      assert pd.Timestamp(trainEnd) < pd.Timestamp(spec.valid_start), name
    else:
      assert spec.direction == BACKWARD, name
      assert pd.Timestamp(spec.valid_end) < pd.Timestamp(trainStart), name


def testGroup3IsUntrainableWhenTrainWindowIsOnly2022(labels):
  assert trainable_targets(labels, "F7") == TARGET_COLS[:2]
  assert GROUP_3 in trainable_targets(labels, "F0")


def testScoreableTargetsDropGroup3OnlyWhereLabelsAreMissing(labels):
  # F7은 학습 창이 2022뿐이라 Group 3을 학습할 수 없고, F8은 검증 구간이 2022라 채점할 수 없다.
  assert scoreable_targets(labels, "F7") == TARGET_COLS[:2]
  assert scoreable_targets(labels, "F8") == TARGET_COLS[:2]
  for name in ["F0", "F1", "F2", "F3", "F4", "F5", "F6"]:
    assert scoreable_targets(labels, name) == TARGET_COLS, name


def testCrossYearFoldsCoverThreeValidationYears():
  years = {spec.valid_year for spec in FOLDS.values()}
  assert years == {2022, 2023, 2024}


def testF5MirrorsF4WithOnlyTheYearChanged(labels):
  described = describe_folds(labels)
  f4, f5 = FOLDS["F4"], FOLDS["F5"]
  # 계절이 같다 — 두 fold 모두 7월 1일부터 12월 31일까지를 검증한다.
  assert pd.Timestamp(f4.valid_start).strftime("%m-%d") == pd.Timestamp(f5.valid_start).strftime("%m-%d")
  assert pd.Timestamp(f4.valid_end).strftime("%m-%d") == pd.Timestamp(f5.valid_end).strftime("%m-%d")
  # 연도만 1년 차이다.
  assert f4.valid_year - f5.valid_year == 1
  # 검증 행 수가 같고, 학습 창 길이 차이는 2024 윤일 하루뿐이다.
  assert int(described.loc["F4", "valid 행"]) == int(described.loc["F5", "valid 행"])
  f4Start, f4End = train_window_bounds("F4")
  f5Start, f5End = train_window_bounds("F5")
  f4Span = pd.Timestamp(f4End) - pd.Timestamp(f4Start)
  f5Span = pd.Timestamp(f5End) - pd.Timestamp(f5Start)
  assert abs(f4Span - f5Span) <= pd.Timedelta(days=1)


def testDescribeFoldsReportsNoOverlap(labels):
  described = describe_folds(labels)
  assert set(described.index) == set(FOLDS)
  assert (described["겹침 행"] == 0).all()
  assert (described["valid 행"] > 0).all()


def testAssertFoldContractRejectsOverlappingFold(labels, monkeypatch):
  broken = dict(FOLDS)
  broken["FX"] = FoldSpec("W_2022_2023", "2023-06-01 00:00", "2023-12-31 23:00", FORWARD, 2023, "겹침")
  monkeypatch.setattr("baram.folds.FOLDS", broken)
  with pytest.raises(ValueError, match="겹침"):
    assert_fold_contract(labels, fold_names=["FX"])


def testAssertFoldContractRejectsWrongDirectionLabel(labels, monkeypatch):
  broken = dict(FOLDS)
  # train이 2024인데 valid가 2023이면 역방향이다. 순방향이라고 적으면 걸려야 한다.
  broken["FX"] = FoldSpec("W_2024", "2023-01-01 01:00", "2023-12-31 23:00", FORWARD, 2023, "방향 오기")
  monkeypatch.setattr("baram.folds.FOLDS", broken)
  with pytest.raises(ValueError, match="순방향"):
    assert_fold_contract(labels, fold_names=["FX"])


def testAssertFoldContractRejectsFoldWithNoScoreableGroup(labels, monkeypatch):
  broken = dict(FOLDS)
  # 학습도 검증도 2022뿐이면 Group 3이 빠지는 것을 넘어 겹침으로 먼저 걸린다.
  # 여기서는 채점 그룹이 0인 경우만 보려고 라벨을 전부 지운 프레임을 쓴다.
  broken["FX"] = FoldSpec("W_2022", "2023-01-01 01:00", "2023-12-31 23:00", FORWARD, 2023, "빈 검증")
  monkeypatch.setattr("baram.folds.FOLDS", broken)
  emptyValid = labels.copy()
  emptyValid.loc[emptyValid["kst_dtm"].dt.year == 2023, TARGET_COLS] = 0.0
  with pytest.raises(ValueError, match="채점 가능한 그룹"):
    assert_fold_contract(emptyValid, fold_names=["FX"])


def testWindowPredictRangesCoverEveryFoldValidSpan():
  ranges = window_predict_ranges()
  assert set(ranges) <= set(TRAIN_WINDOWS)
  for spec in FOLDS.values():
    start, end = ranges[spec.train_window]
    assert pd.Timestamp(start) <= pd.Timestamp(spec.valid_start)
    assert pd.Timestamp(end) >= pd.Timestamp(spec.valid_end)


def testLabelMaskAndWeatherSliceAreInclusiveOnBothEnds(labels):
  mask = label_mask(labels, "2023-01-01 01:00", "2023-01-01 03:00")
  assert int(mask.sum()) == 3

  weather = pd.DataFrame(
    {"forecast_kst_dtm": pd.date_range("2023-01-01 01:00", periods=5, freq="h"), "value": range(5)}
  )
  assert len(weather_slice(weather, "2023-01-01 01:00", "2023-01-01 03:00")) == 3


def testMetricOverMatchesOfficialMetricOnAllThreeGroups(labels):
  index = labels.loc[label_mask(labels, "2023-01-01 01:00", "2023-12-31 23:00")].index
  predictions = makePredictions(labels, index, offset=900.0)
  actual = labels.loc[index, TARGET_COLS]
  assert np.allclose(metric_over(actual, predictions, TARGET_COLS), metric(actual, predictions))


def testMetricOverIgnoresGroupsOutsideTheColumnList(labels):
  index = labels.loc[label_mask(labels, "2023-01-01 01:00", "2023-12-31 23:00")].index
  predictions = makePredictions(labels, index, offset=900.0)
  actual = labels.loc[index, TARGET_COLS]

  twoGroup = metric_over(actual, predictions, TARGET_COLS[:2])
  # Group 3 예측을 완전히 망가뜨려도 두 그룹 점수는 변하지 않아야 한다.
  broken = predictions.copy()
  broken[GROUP_3] = 0.0
  assert np.allclose(metric_over(actual, broken, TARGET_COLS[:2]), twoGroup)
  assert not np.allclose(metric_over(actual, broken, TARGET_COLS), metric_over(actual, predictions, TARGET_COLS))


def testMetricOverRejectsUnknownColumn(labels):
  index = labels.loc[label_mask(labels, "2023-01-01 01:00", "2023-01-31 23:00")].index
  predictions = makePredictions(labels, index, offset=100.0)
  with pytest.raises(ValueError, match="알 수 없는 target"):
    metric_over(labels.loc[index, TARGET_COLS], predictions, ["kpx_group_9"])


def testTotalFromTermsReproducesMetricOverTotal(labels):
  index = labels.loc[label_mask(labels, "2023-07-01 00:00", "2023-12-31 23:00")].index
  predictions = makePredictions(labels, index, offset=1500.0)
  terms = group_error_terms(labels, predictions, "F5")
  expected, _, _ = metric_over(labels.loc[index, TARGET_COLS], predictions, TARGET_COLS)
  assert total_from_terms(terms) == pytest.approx(expected)


def testGroupErrorTermsKeepOnlyEvaluationRows(labels):
  index = labels.loc[label_mask(labels, "2023-07-01 00:00", "2023-12-31 23:00")].index
  predictions = makePredictions(labels, index, offset=0.0)
  terms = group_error_terms(labels, predictions, "F5")
  for column, (errorRate, actual) in terms.items():
    assert errorRate.size == actual.size
    assert (actual >= CAPACITY_KWH[column] * 0.10).all()


def testPairedBootstrapGapIsDeterministicAndCentredOnObservedGap(labels):
  index = labels.loc[label_mask(labels, "2023-07-01 00:00", "2023-12-31 23:00")].index
  better = makePredictions(labels, index, offset=300.0)
  worse = makePredictions(labels, index, offset=1800.0)
  termsBetter = group_error_terms(labels, better, "F5")
  termsWorse = group_error_terms(labels, worse, "F5")

  gaps = paired_bootstrap_gap(termsBetter, termsWorse, draws=50)
  assert gaps.shape == (50,)
  assert np.array_equal(gaps, paired_bootstrap_gap(termsBetter, termsWorse, draws=50))
  # 더 나은 모델이 확실히 앞서면 재표집에서도 부호가 뒤집히지 않는다.
  assert (gaps > 0).all()


def testPairedBootstrapGapRejectsMismatchedColumns(labels):
  index = labels.loc[label_mask(labels, "2023-07-01 00:00", "2023-12-31 23:00")].index
  predictions = makePredictions(labels, index, offset=300.0)
  three = group_error_terms(labels, predictions, "F5")
  two = group_error_terms(labels, predictions, "F5", columns=TARGET_COLS[:2])
  with pytest.raises(ValueError, match="채점 그룹이 다릅니다"):
    paired_bootstrap_gap(three, two, draws=5)
