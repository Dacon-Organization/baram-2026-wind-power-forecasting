"""metric-aware calibration — 예측을 정산 구간 경계에 대해 다듬는 보정 (설계서 04 7.1절 M6).

**왜 별도 모듈인가.** FICR은 연속 지표가 아니라 오차율 6%·8%의 계단 함수다
(`metrics.py`). 노트북 11이 피처 개선분의 79.6%가 FICR에서 나왔다고 쟀고, 노트북 12가
평가 행의 18.5%가 경계 ±1%p 안에 몰려 있음을 행 단위로 보였다. 평균 오차를 줄이는
것보다 **오차율 분포를 계단 경계에 대해 옮기는 것**이 남은 지렛대라는 것이 M6의 전제다.

**세 가지 계약을 코드로 못 박는다.**

1. 보정은 전부 **설비용량 정규화 공간**(`p̂ = pred / capacity ∈ [0, 1]`)에서 정의한다.
   그래야 설비용량이 다른 세 그룹이 파라미터 하나를 공유할 수 있고, Group 3 라벨이
   0행인 학습 창(W_2022)에서도 보정이 정의된다.
2. fit은 **학습 창 내부 OOF에서만** 한다(`inner_oof_blocks()`). 검증 구간 값으로 fit하면
   설계서 06 2.2절의 절대 금지다. 검증 구간 fit(`oracle_fit`)은 **상한 진단으로만** 쓴다.
3. 목적함수는 **total_score**다. FICR 단독이 아니다 — FICR만 올리고 1-NMAE를 버리는
   보정을 채택하는 것은 설계서 04 7.2절 위반이다.

하이퍼파라미터에 해당하는 그리드는 고정값이며 fold 성적을 보고 넓히지 않는다
(노트북 15 Decision Box ㉔와 같은 이유).
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Callable

import numpy as np
import pandas as pd

from baram.folds import FOLDS
from baram.folds import label_mask
from baram.folds import scoreable_targets
from baram.metrics import CAPACITY_KWH
from baram.metrics import TARGET_COLS


# 공식 산식의 계단 구조. `metrics.metric()`의 `np.select`와 같은 값이며,
# 두 구현이 같은 점수를 낸다는 것은 `tests/test_calibration.py`가 지킨다.
FICR_TIER_EDGES = (0.06, 0.08)
FICR_TIER_PRICES = (4.0, 3.0)
EVALUATION_RATIO = 0.10

# 고정 그리드. 정규화 공간이므로 0.001은 설비용량의 0.1%p, 즉 21.6 kWh 남짓이다.
BIAS_GRID = np.round(np.arange(-0.060, 0.060 + 1e-9, 0.001), 6)
SLOPE_GRID = np.round(np.arange(0.80, 1.20 + 1e-9, 0.01), 6)
BINNED_BINS = 5
BINNED_PASSES = 2

# OOF 분할. 창을 4블록으로 나눠 뒤쪽 3블록을 예측하므로 OOF가 창의 75%를 덮는다.
# 더 쪼개면 OOF 행은 늘지만 inner 학습 크기가 내려가 최종 모델과의 괴리가 커진다.
DEFAULT_OOF_BLOCKS = 4


@dataclass(frozen=True)
class Calibration:
  """fit 결과. `params`는 표에 그대로 싣고 호출하면 정규화 예측에 적용된다.

  `__call__`이 `[0, 1]` clip을 담당하므로 fit 단계의 목적함수 평가와 실제 적용이
  **같은 함수**를 지난다. clip을 적용 시점에만 걸면 fit이 쓰지 않는 변환을
  최적화하게 된다.
  """

  name: str
  params: dict = field(default_factory=dict)
  transform: Callable[[np.ndarray], np.ndarray] = None

  def __call__(self, normalized):
    values = np.asarray(normalized, dtype=float)
    # 빈 배열을 그대로 통과시킨다. 채점 그룹이 fold마다 다르므로 평가 대상 행이 0개인
    # 그룹이 정상적으로 생기며(W_2022의 Group 3), sklearn의 isotonic은 빈 입력을
    # 예외로 거절한다. 여기서 막지 않으면 그 예외가 노트북 중간에서 터진다.
    if values.size == 0:
      return values
    if self.transform is None:
      return np.clip(values, 0.0, 1.0)
    return np.clip(self.transform(values), 0.0, 1.0)

  def describe(self):
    """파라미터를 한 줄 문자열로. 노트북 파라미터 표에 쓴다."""
    if not self.params:
      return "항등"
    parts = []
    for key, value in self.params.items():
      if isinstance(value, (list, tuple, np.ndarray)):
        parts.append(f"{key}=[" + ", ".join(f"{v:+.4f}" for v in value) + "]")
      elif isinstance(value, float):
        parts.append(f"{key}={value:+.4f}")
      else:
        parts.append(f"{key}={value}")
    return " ".join(parts)


# --------------------------------------------------------------------------------------
# 채점 — 정규화 공간
# --------------------------------------------------------------------------------------


def normalized_terms(labels, predictions, index, columns):
  """평가 대상 행만 남긴 그룹별 `(예측 이용률, 실제 이용률)` 쌍.

  `folds.group_error_terms()`는 이미 오차율을 계산해 돌려주지만, 보정은 오차율이 아니라
  **예측값 자체**를 움직여야 하므로 예측과 실측을 따로 들고 있는 짝이 필요하다.
  평가 대상은 실제값이 설비용량의 10% 이상인 행이다(`metrics.py`).
  """
  unknown = [column for column in columns if column not in TARGET_COLS]
  if unknown:
    raise ValueError(f"알 수 없는 target 컬럼: {unknown}")

  terms = {}
  for column in columns:
    capacity = CAPACITY_KWH[column]
    actual = labels.loc[index, column].to_numpy(dtype=float)
    forecast = predictions.loc[index, column].to_numpy(dtype=float)
    keep = actual >= capacity * EVALUATION_RATIO
    terms[column] = (forecast[keep] / capacity, actual[keep] / capacity)
  return terms


def fold_normalized_terms(labels, predictions, fold_name, columns=None):
  """`normalized_terms()`를 fold의 검증 구간에 적용한다. `folds.score_fold()`와 같은 범위."""
  spec = FOLDS[fold_name]
  index = labels.loc[label_mask(labels, spec.valid_start, spec.valid_end)].index
  columns = list(columns) if columns is not None else scoreable_targets(labels, fold_name)
  return normalized_terms(labels, predictions, index, columns)


def _score_shifted(shifted_by_group, terms):
  """보정된 예측에서 total_score. 마지막 축이 행이므로 그리드 축이 앞에 붙어도 된다.

  `shifted`가 `(rows,)`면 스칼라, `(grid, rows)`면 `(grid,)`를 돌려준다 —
  그리드 탐색이 파이썬 루프 없이 한 번에 채점된다.
  """
  nmae_parts, ficr_parts = [], []
  for column, shifted in shifted_by_group.items():
    actual = terms[column][1]
    if actual.size == 0:
      continue
    error_rate = np.abs(shifted - actual)
    nmae_parts.append(error_rate.mean(axis=-1))
    unit_price = np.where(
      error_rate <= FICR_TIER_EDGES[0],
      FICR_TIER_PRICES[0],
      np.where(error_rate <= FICR_TIER_EDGES[1], FICR_TIER_PRICES[1], 0.0),
    )
    earned = (unit_price * actual).sum(axis=-1)
    ficr_parts.append(earned / (FICR_TIER_PRICES[0] * actual.sum()))
  if not nmae_parts:
    raise ValueError("채점 가능한 그룹이 없습니다")
  one_minus_nmae = 1.0 - np.mean(nmae_parts, axis=0)
  return 0.5 * one_minus_nmae + 0.5 * np.mean(ficr_parts, axis=0)


def score_normalized(terms, calibration=None):
  """정규화 공간에서 total_score. 보정을 주면 적용한 뒤 채점한다.

  `metrics.metric_over()`·`folds.total_from_terms()`와 같은 산식이다 (FICR은 비율이라
  설비용량으로 나눠도 값이 변하지 않는다). 세 구현의 일치는 테스트가 지킨다.
  """
  shifted = {
    column: (predicted if calibration is None else calibration(predicted))
    for column, (predicted, _) in terms.items()
  }
  return float(_score_shifted(shifted, terms))


def nmae_normalized(terms, calibration=None):
  """그룹별 평균 오차율의 평균 = NMAE. `bias_mae`의 목적함수다."""
  parts = []
  for column, (predicted, actual) in terms.items():
    if actual.size == 0:
      continue
    shifted = predicted if calibration is None else calibration(predicted)
    parts.append(float(np.abs(shifted - actual).mean()))
  if not parts:
    raise ValueError("채점 가능한 그룹이 없습니다")
  return float(np.mean(parts))


def decompose_normalized(terms, calibration=None):
  """`(total, one_minus_nmae, ficr)` — `metrics.metric_over()`와 같은 3종 분해."""
  nmae_parts, ficr_parts = [], []
  for column, (predicted, actual) in terms.items():
    if actual.size == 0:
      continue
    shifted = predicted if calibration is None else calibration(predicted)
    error_rate = np.abs(shifted - actual)
    nmae_parts.append(float(error_rate.mean()))
    unit_price = np.where(
      error_rate <= FICR_TIER_EDGES[0],
      FICR_TIER_PRICES[0],
      np.where(error_rate <= FICR_TIER_EDGES[1], FICR_TIER_PRICES[1], 0.0),
    )
    ficr_parts.append(float((unit_price * actual).sum() / (FICR_TIER_PRICES[0] * actual.sum())))
  if not nmae_parts:
    raise ValueError("채점 가능한 그룹이 없습니다")
  one_minus_nmae = 1.0 - float(np.mean(nmae_parts))
  ficr = float(np.mean(ficr_parts))
  return 0.5 * one_minus_nmae + 0.5 * ficr, one_minus_nmae, ficr


# --------------------------------------------------------------------------------------
# 보정 후보 — 6종 사전 등록
# --------------------------------------------------------------------------------------


def _pool(terms):
  """그룹을 세로로 이어붙인 `(예측, 실측)`. 그룹 공유 파라미터를 fit할 때 쓴다."""
  predicted = np.concatenate([pair[0] for pair in terms.values()]) if terms else np.empty(0)
  actual = np.concatenate([pair[1] for pair in terms.values()]) if terms else np.empty(0)
  return predicted, actual


def _require_rows(terms):
  predicted, _ = _pool(terms)
  if predicted.size == 0:
    raise ValueError("보정을 fit할 평가 대상 행이 없습니다")
  return predicted.size


def _argbest(scores, grid, *, maximize=True, tolerance=1e-12):
  """최적 격자점. 동률이면 **크기가 작은 쪽**을 고른다 — 근거가 같으면 덜 움직인다.

  `np.argmax`는 첫 인덱스를 돌려주므로 그리드가 음수부터 시작하면 동률에서 가장 큰
  음수 보정이 뽑힌다. 그리드 순서가 결정에 개입하지 않도록 명시적으로 고른다.
  """
  scores = np.asarray(scores, dtype=float)
  best = scores.max() if maximize else scores.min()
  tied = np.flatnonzero(np.abs(scores - best) <= tolerance)
  return int(tied[np.argmin(np.abs(np.asarray(grid, dtype=float)[tied]))])


def _bias_candidates(terms, grid):
  """`(grid, rows)` 형태로 bias 그리드 전체를 한 번에 만든다."""
  return {
    column: np.clip(predicted[None, :] + np.asarray(grid, dtype=float)[:, None], 0.0, 1.0)
    for column, (predicted, _) in terms.items()
  }


def fit_none(terms):
  """통제군 — 아무것도 하지 않는다."""
  _require_rows(terms)
  return Calibration("none")


def fit_bias_mae(terms):
  """단일 가산 보정, **NMAE 최소**. metric-aware의 대조군이다.

  `fit_bias_metric()`과 함수 형태·그리드가 같고 목적함수만 다르다. 두 결과가 갈리는지가
  "metric-aware"라는 말이 내용을 갖는지를 결정한다.
  """
  _require_rows(terms)
  candidates = _bias_candidates(terms, BIAS_GRID)
  errors = []
  for column, shifted in candidates.items():
    actual = terms[column][1]
    if actual.size == 0:
      continue
    errors.append(np.abs(shifted - actual).mean(axis=-1))
  nmae = np.mean(errors, axis=0)
  bias = float(BIAS_GRID[_argbest(nmae, BIAS_GRID, maximize=False)])
  return Calibration("bias_mae", {"b": bias}, lambda values: values + bias)


def fit_bias_metric(terms):
  """단일 가산 보정, **total_score 최대**. 가장 단순한 metric-aware 후보다."""
  _require_rows(terms)
  scores = _score_shifted(_bias_candidates(terms, BIAS_GRID), terms)
  bias = float(BIAS_GRID[_argbest(scores, BIAS_GRID)])
  return Calibration("bias_metric", {"b": bias}, lambda values: values + bias)


def fit_affine_metric(terms):
  """`a·p̂ + b`, total_score 최대. 수준과 기울기를 함께 본다.

  트리 모델은 평균으로 수축하는 경향이 있어 높은 예측을 낮게, 낮은 예측을 높게 낸다.
  기울기 자유도가 그 수축을 되돌릴 수 있는지 보는 후보다.
  """
  _require_rows(terms)
  bestScore, bestParams = -np.inf, (1.0, 0.0)
  for slope in SLOPE_GRID:
    candidates = {
      column: np.clip(slope * predicted[None, :] + BIAS_GRID[:, None], 0.0, 1.0)
      for column, (predicted, _) in terms.items()
    }
    scores = _score_shifted(candidates, terms)
    index = _argbest(scores, BIAS_GRID)
    # 동률이면 기울기 1에 가까운 쪽을 유지한다 — 앞선 slope가 이미 1에 더 가깝다.
    if scores[index] > bestScore + 1e-12:
      bestScore, bestParams = float(scores[index]), (float(slope), float(BIAS_GRID[index]))
  slope, bias = bestParams
  return Calibration(
    "affine_metric", {"a": slope, "b": bias}, lambda values: slope * values + bias
  )


def _bin_edges(predicted, bins):
  """예측 분위 경계. 내부 경계만 돌려주므로 `searchsorted`가 0..bins-1을 낸다."""
  quantiles = np.linspace(0.0, 1.0, bins + 1)[1:-1]
  edges = np.unique(np.quantile(predicted, quantiles))
  return edges


def fit_binned_metric(terms, bins=BINNED_BINS, passes=BINNED_PASSES):
  """예측 분위 구간별 가산 보정, total_score 최대. 조건부 편향을 교정한다.

  단일 bias가 잡지 못하는 것은 **예측 수준에 따라 편향의 방향이 다른** 경우다.
  구간별로 따로 밀면 그것을 잡을 수 있고, 계단 경계 근처 행이 특정 예측 수준에
  몰려 있다면 그 구간만 집중적으로 옮길 수 있다.

  좌표 상승법이다 — 구간 하나씩 그리드를 훑고 나머지는 고정한다. 전역 최적을
  보장하지 않지만, 보장하려면 그리드가 `len(BIAS_GRID) ** bins`가 되어 후보 수를
  누르자는 취지에 어긋난다.
  """
  _require_rows(terms)
  pooledPredicted, _ = _pool(terms)
  edges = _bin_edges(pooledPredicted, bins)
  binOf = {
    column: np.searchsorted(edges, predicted, side="right")
    for column, (predicted, _) in terms.items()
  }
  binCount = len(edges) + 1
  offsets = np.zeros(binCount)

  for _ in range(passes):
    for target in range(binCount):
      candidates = {}
      for column, (predicted, _) in terms.items():
        shifted = predicted + offsets[binOf[column]]
        block = np.repeat(shifted[None, :], BIAS_GRID.size, axis=0)
        mask = binOf[column] == target
        if mask.any():
          block[:, mask] = predicted[mask][None, :] + BIAS_GRID[:, None]
        candidates[column] = np.clip(block, 0.0, 1.0)
      scores = _score_shifted(candidates, terms)
      offsets[target] = float(BIAS_GRID[_argbest(scores, BIAS_GRID)])

  frozenEdges, frozenOffsets = edges.copy(), offsets.copy()

  def transform(values):
    return values + frozenOffsets[np.searchsorted(frozenEdges, values, side="right")]

  return Calibration(
    "binned_metric",
    {"edges": frozenEdges.tolist(), "offsets": frozenOffsets.tolist()},
    transform,
  )


def fit_isotonic(terms):
  """isotonic `p̂ → ŷ`. 단조 제약만 두고 형태는 데이터가 정한다.

  metric-aware가 **아니다** — 제곱오차를 줄이며 계단 경계를 모른다. 유연한 함수 형태가
  목적함수보다 중요한지 가르는 대조군으로 둔다.
  """
  _require_rows(terms)
  from sklearn.isotonic import IsotonicRegression

  predicted, actual = _pool(terms)
  model = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
  model.fit(predicted, actual)
  knots = int(np.size(model.X_thresholds_))
  return Calibration(
    "isotonic",
    {"knots": knots},
    lambda values: np.asarray(model.predict(values), dtype=float),
  )


CALIBRATORS = {
  "none": fit_none,
  "bias_mae": fit_bias_mae,
  "bias_metric": fit_bias_metric,
  "affine_metric": fit_affine_metric,
  "binned_metric": fit_binned_metric,
  "isotonic": fit_isotonic,
}


def fit_calibration(name, terms):
  """이름으로 fit한다. 등록되지 않은 이름은 예외로 멈춘다."""
  if name not in CALIBRATORS:
    raise ValueError(f"등록되지 않은 보정 후보: {name!r} (등록: {list(CALIBRATORS)})")
  return CALIBRATORS[name](terms)


def apply_calibration(predictions, calibration, columns=None):
  """원단위 예측 프레임에 보정을 적용한다 (÷용량 → 보정 → ×용량).

  NaN은 그대로 남긴다 — `folds.run_window()`가 학습 라벨 없는 target을 NaN으로
  남기므로, 보정이 그 자리를 0으로 채우면 없는 예측을 만들어내는 셈이 된다.
  """
  columns = list(columns) if columns is not None else [
    column for column in TARGET_COLS if column in predictions.columns
  ]
  calibrated = predictions.copy()
  for column in columns:
    capacity = CAPACITY_KWH[column]
    values = predictions[column].to_numpy(dtype=float) / capacity
    finite = np.isfinite(values)
    adjusted = values.copy()
    if finite.any():
      adjusted[finite] = calibration(values[finite])
    calibrated[column] = np.clip(adjusted * capacity, 0.0, capacity)
  return calibrated


# --------------------------------------------------------------------------------------
# 진단 — 상한과 밴드 이동
# --------------------------------------------------------------------------------------


def oracle_row_bound(terms, delta):
  """행마다 이상적인 `±delta` 밀기를 허용했을 때의 total_score — **달성 불가능한 천장**.

  두 지표 모두 오차율에 대해 단조이므로(NMAE는 증가, 단가는 비증가) 행별 최적은
  **오차를 delta만큼 0으로 당기는 것**이며 그 사이에 상충이 없다. 따라서 이 값은
  행별 보정 크기가 `delta` 이하인 **어떤** 보정도 넘을 수 없는 상한이다.

  후보의 Δ가 0에 가까울 때 "보정이 무력한 것"과 "우리 후보가 약한 것"을 구분하는
  장치다. 상한 자체가 문턱보다 작으면 이 방향에 남은 것이 없다는 뜻이다.
  """
  if delta < 0:
    raise ValueError("delta는 0 이상이어야 합니다")
  nmae_parts, ficr_parts = [], []
  for predicted, actual in terms.values():
    if actual.size == 0:
      continue
    error_rate = np.maximum(np.abs(predicted - actual) - float(delta), 0.0)
    nmae_parts.append(float(error_rate.mean()))
    unit_price = np.where(
      error_rate <= FICR_TIER_EDGES[0],
      FICR_TIER_PRICES[0],
      np.where(error_rate <= FICR_TIER_EDGES[1], FICR_TIER_PRICES[1], 0.0),
    )
    ficr_parts.append(float((unit_price * actual).sum() / (FICR_TIER_PRICES[0] * actual.sum())))
  if not nmae_parts:
    raise ValueError("채점 가능한 그룹이 없습니다")
  return 0.5 * (1.0 - float(np.mean(nmae_parts))) + 0.5 * float(np.mean(ficr_parts))


def price_band(error_rate):
  """오차율을 단가 밴드로. 0 = 4원, 1 = 3원, 2 = 0원."""
  error_rate = np.asarray(error_rate, dtype=float)
  return np.where(
    error_rate <= FICR_TIER_EDGES[0], 0, np.where(error_rate <= FICR_TIER_EDGES[1], 1, 2)
  )


def band_transition(terms, calibration):
  """보정 전후의 단가 밴드 이동을 센다.

  노트북 12가 S1→S2 제출에 했던 분석을 보정 전후에 적용하는 것이다. 개선분이
  정말 계단 구조에서 나왔는지 확인하는 직접 증거이며, 순증이 이동 수에 비해
  작다면 보정이 신호와 잡음을 함께 밀었다는 뜻이다.
  """
  rows = []
  for column, (predicted, actual) in terms.items():
    if actual.size == 0:
      continue
    before = price_band(np.abs(predicted - actual))
    after = price_band(np.abs(calibration(predicted) - actual))
    moved = before != after
    rows.append(
      {
        "그룹": column,
        "평가 행": int(actual.size),
        "밴드 이동": int(moved.sum()),
        "좋아짐": int((after < before).sum()),
        "나빠짐": int((after > before).sum()),
        "순증": int((after < before).sum() - (after > before).sum()),
        "이동 비율": float(moved.mean()),
      }
    )
  if not rows:
    raise ValueError("채점 가능한 그룹이 없습니다")
  frame = pd.DataFrame(rows).set_index("그룹")
  total = frame[["평가 행", "밴드 이동", "좋아짐", "나빠짐", "순증"]].sum()
  total["이동 비율"] = total["밴드 이동"] / total["평가 행"]
  frame.loc["합계"] = total
  return frame


def boundary_density(terms, window=0.01):
  """계단 경계 `±window` 안에 있는 평가 행 비율과 밴드별 비율.

  노트북 12가 S2에서 18.5%로 쟀던 값을 fold마다 다시 재는 함수다. 이 밀도가 낮으면
  경계를 옮기는 전략의 여지가 애초에 작다.
  """
  rows = []
  for column, (predicted, actual) in terms.items():
    if actual.size == 0:
      continue
    error_rate = np.abs(predicted - actual)
    near = np.zeros(error_rate.shape, dtype=bool)
    for edge in FICR_TIER_EDGES:
      near |= np.abs(error_rate - edge) <= window
    band = price_band(error_rate)
    rows.append(
      {
        "그룹": column,
        "평가 행": int(error_rate.size),
        "4원 비율": float((band == 0).mean()),
        "3원 비율": float((band == 1).mean()),
        "0원 비율": float((band == 2).mean()),
        f"경계 ±{window:.0%} 비율": float(near.mean()),
        "평균 오차율": float(error_rate.mean()),
      }
    )
  if not rows:
    raise ValueError("채점 가능한 그룹이 없습니다")
  return pd.DataFrame(rows).set_index("그룹")


# --------------------------------------------------------------------------------------
# 학습 창 내부 OOF 분할
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class OofBlock:
  """학습 창 내부 expanding-window 분할 한 조각.

  `train_*`은 창의 시작부터 이 블록 직전까지, `predict_*`가 OOF 구간이다.
  블록 번호는 1부터이며 블록 0은 첫 학습분이라 OOF가 없다.
  """

  block: int
  train_start: pd.Timestamp
  train_end: pd.Timestamp
  predict_start: pd.Timestamp
  predict_end: pd.Timestamp

  @property
  def bounds(self):
    """`run_window_pooled(train_bounds=...)`에 그대로 넘길 짝."""
    return (self.train_start, self.train_end)


def inner_oof_blocks(start, end, blocks=DEFAULT_OOF_BLOCKS, freq="h"):
  """학습 창을 시간 순 `blocks`등분해 expanding-window OOF 분할을 만든다.

  fold 정의와 같은 이유로 **계약**이다. 학습 구간이 예측 블록과 겹치거나 시간 순서가
  뒤집히면 조용히 통과하지 않고 `ValueError`로 멈춘다 — 이 분할이 새면 보정은
  검증 구간을 미리 본 것과 같아지고, 그 실수는 점수만 조용히 좋아진다.
  """
  begin, finish = pd.Timestamp(start), pd.Timestamp(end)
  if not begin < finish:
    raise ValueError(f"학습 창의 시작이 끝보다 늦다: {begin} ~ {finish}")
  if blocks < 2:
    raise ValueError(f"blocks는 2 이상이어야 한다 (받은 값 {blocks})")

  step = pd.Timedelta(1, unit=freq)
  edges = pd.date_range(begin, finish, periods=blocks + 1).floor(freq)
  if len(set(edges)) != len(edges):
    raise ValueError(f"학습 창이 {blocks}등분하기에 너무 짧다: {begin} ~ {finish}")

  splits = []
  for block in range(1, blocks):
    predictStart = edges[block]
    predictEnd = finish if block == blocks - 1 else edges[block + 1] - step
    trainEnd = predictStart - step
    if not begin <= trainEnd < predictStart:
      raise ValueError(f"블록 {block}의 학습 구간이 비었거나 예측 구간과 겹친다")
    if not predictStart <= predictEnd:
      raise ValueError(f"블록 {block}의 예측 구간이 비었다")
    splits.append(OofBlock(block, begin, trainEnd, predictStart, predictEnd))
  return splits


def describe_oof_blocks(labels, window_name, bounds, blocks=DEFAULT_OOF_BLOCKS):
  """OOF 분할을 표로. 학습 행 수와 OOF 행 수, 겹침 0을 눈으로 확인하는 용도다."""
  rows = []
  for split in inner_oof_blocks(bounds[0], bounds[1], blocks=blocks):
    trainRows = label_mask(labels, split.train_start, split.train_end)
    predictRows = label_mask(labels, split.predict_start, split.predict_end)
    rows.append(
      {
        "창": window_name,
        "블록": split.block,
        "inner train": f"{split.train_start:%Y-%m-%d} ~ {split.train_end:%Y-%m-%d}",
        "OOF": f"{split.predict_start:%Y-%m-%d} ~ {split.predict_end:%Y-%m-%d}",
        "train 행": int(trainRows.sum()),
        "OOF 행": int(predictRows.sum()),
        "겹침 행": int((trainRows & predictRows).sum()),
      }
    )
  return pd.DataFrame(rows)


__all__ = [
  "BIAS_GRID",
  "BINNED_BINS",
  "BINNED_PASSES",
  "CALIBRATORS",
  "DEFAULT_OOF_BLOCKS",
  "EVALUATION_RATIO",
  "FICR_TIER_EDGES",
  "FICR_TIER_PRICES",
  "SLOPE_GRID",
  "Calibration",
  "OofBlock",
  "apply_calibration",
  "band_transition",
  "boundary_density",
  "decompose_normalized",
  "describe_oof_blocks",
  "fit_affine_metric",
  "fit_bias_mae",
  "fit_bias_metric",
  "fit_binned_metric",
  "fit_calibration",
  "fit_isotonic",
  "fit_none",
  "fold_normalized_terms",
  "inner_oof_blocks",
  "nmae_normalized",
  "normalized_terms",
  "oracle_row_bound",
  "price_band",
  "score_normalized",
]
