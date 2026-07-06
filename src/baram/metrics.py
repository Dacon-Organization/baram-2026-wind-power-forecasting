"""DACON BARAM 2026 공식 평가 산식 재현 모듈."""

import numpy as np


TARGET_COLS = ["kpx_group_1", "kpx_group_2", "kpx_group_3"]

CAPACITY_KWH = {
  "kpx_group_1": 21600,
  "kpx_group_2": 21600,
  "kpx_group_3": 21000,
}


def metric(answer_df, pred_df):
  """공식 노트북의 total_score, 1-NMAE, FICR 계산을 재현한다."""
  group_nmae = []
  group_ficr = []

  with np.errstate(divide="ignore", invalid="ignore"):
    for col in TARGET_COLS:
      actual = answer_df[col].to_numpy(dtype=float)
      forecast = pred_df[col].to_numpy(dtype=float)
      capacity = CAPACITY_KWH[col]

      valid = actual >= capacity * 0.10

      actual = actual[valid]
      forecast = forecast[valid]

      if actual.size == 0:
        group_nmae.append(np.nan)
        group_ficr.append(np.nan)
        continue

      error_rate = np.abs(forecast - actual) / capacity
      group_nmae.append(np.mean(error_rate))

      unit_price = np.select(
        [error_rate <= 0.06, error_rate <= 0.08],
        [4.0, 3.0],
        default=0.0,
      )

      earned_settlement = np.sum(actual * unit_price)
      max_settlement = np.sum(actual * 4.0)

      group_ficr.append(earned_settlement / max_settlement)

    one_minus_nmae = 1 - np.mean(group_nmae)
    ficr = np.mean(group_ficr)

    total_score = 0.5 * one_minus_nmae + 0.5 * ficr

  return total_score, one_minus_nmae, ficr


__all__ = ["CAPACITY_KWH", "TARGET_COLS", "metric"]
