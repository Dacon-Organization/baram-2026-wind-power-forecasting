import json
from pathlib import Path
import warnings

import numpy as np
import pandas as pd

from baram.metrics import CAPACITY_KWH, TARGET_COLS, metric


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_METRIC_NOTEBOOK = PROJECT_ROOT / "references" / "official" / "notebooks" / "evaluation_metric.ipynb"


def load_official_metric():
  notebook = json.loads(OFFICIAL_METRIC_NOTEBOOK.read_text(encoding="utf-8"))
  namespace = {}
  for cell in notebook["cells"]:
    if cell["cell_type"] == "code":
      exec("".join(cell["source"]), namespace)
  return namespace["metric"]


def callIgnoringOfficialRuntimeWarnings(official_metric, answer_df, pred_df):
  with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    return official_metric(answer_df, pred_df)


def makeOfficialExample():
  return (
    pd.DataFrame(
      {
        "kpx_group_1": [2160.0, 3000.0, 1000.0, np.nan],
        "kpx_group_2": [2160.0, 4000.0, 8000.0, 1200.0],
        "kpx_group_3": [2100.0, 2500.0, 22000.0, np.nan],
      }
    ),
    pd.DataFrame(
      {
        "kpx_group_1": [2160.0, 4296.0, 1000.0, 500.0],
        "kpx_group_2": [3456.0, 5728.0, -100.0, 1200.0],
        "kpx_group_3": [3360.0, 4180.0, 23000.0, 500.0],
      }
    ),
  )


def testMetricMatchesOfficialNotebookCode():
  answer_df, pred_df = makeOfficialExample()
  official_metric = load_official_metric()

  actual = metric(answer_df, pred_df)
  expected = callIgnoringOfficialRuntimeWarnings(official_metric, answer_df, pred_df)

  assert np.allclose(actual, expected, equal_nan=True)


def testMetricKeepsOfficialNaNBehaviorForPredictionNaN():
  answer_df, pred_df = makeOfficialExample()
  pred_df.loc[0, "kpx_group_1"] = np.nan
  official_metric = load_official_metric()

  actual = metric(answer_df, pred_df)
  expected = callIgnoringOfficialRuntimeWarnings(official_metric, answer_df, pred_df)

  assert np.isnan(actual[0])
  assert np.isnan(actual[1])
  assert np.allclose(actual, expected, equal_nan=True)


def testMetricReturnsNaNWhenGroupHasNoValidRows():
  answer_df = pd.DataFrame({col: [0.0, np.nan, CAPACITY_KWH[col] * 0.05] for col in TARGET_COLS})
  pred_df = pd.DataFrame({col: [0.0, 1.0, CAPACITY_KWH[col] * 0.05] for col in TARGET_COLS})
  official_metric = load_official_metric()

  actual = metric(answer_df, pred_df)
  expected = callIgnoringOfficialRuntimeWarnings(official_metric, answer_df, pred_df)

  assert np.all(np.isnan(actual))
  assert np.allclose(actual, expected, equal_nan=True)


def testMetricRequiresAllTargetColumns():
  answer_df, pred_df = makeOfficialExample()
  missing_pred_df = pred_df.drop(columns=["kpx_group_3"])

  with np.testing.assert_raises(KeyError):
    metric(answer_df, missing_pred_df)
