import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from baram.reproducibility import (
  SUBMISSION_LEDGER_COLUMNS,
  BaselineRunConfig,
  build_submission_ledger_entry,
  build_submission_filename,
  ledger_entry_to_frame,
  run_baseline_with_reproducibility,
  submission_to_csv_bytes,
  submission_csv_sha256,
  verify_baseline_inference_reproducibility,
)


def makeWeatherFrame(times, values):
  rows = []
  for timeIndex, forecastTime in enumerate(pd.to_datetime(times)):
    availableTime = forecastTime - pd.Timedelta(hours=12)
    for gridId in [1, 2]:
      value = float(values[timeIndex] + gridId)
      rows.append(
        {
          "forecast_kst_dtm": forecastTime,
          "data_available_kst_dtm": availableTime,
          "grid_id": gridId,
          "latitude": 37.0 + gridId * 0.01,
          "longitude": 128.0 + gridId * 0.01,
          "heightAboveGround_10_10u": value,
          "heightAboveGround_10_10v": value * 2,
        }
      )
  return pd.DataFrame(rows)


def makeLabelFrame():
  times = pd.date_range("2024-01-01 01:00:00", periods=5, freq="h")
  return pd.DataFrame(
    {
      "kst_dtm": times,
      "kpx_group_1": [1000.0, 3000.0, 5000.0, 7000.0, 9000.0],
      "kpx_group_2": [2000.0, 4000.0, 6000.0, 8000.0, 10000.0],
      "kpx_group_3": [np.nan, np.nan, 2100.0, 5000.0, 8000.0],
    }
  )


def makeSampleSubmission(times):
  return pd.DataFrame(
    {
      "forecast_id": [f"F{i:03d}" for i in range(len(times))],
      "forecast_kst_dtm": pd.to_datetime(times),
      "kpx_group_1": 0.0,
      "kpx_group_2": 0.0,
      "kpx_group_3": 0.0,
    }
  )


def tinyRunInputs():
  labels = makeLabelFrame()
  sample = makeSampleSubmission(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"))
  return {
    "train_labels": labels,
    "ldaps_train": makeWeatherFrame(labels["kst_dtm"], [1, 2, 3, 4, 5]),
    "gfs_train": makeWeatherFrame(labels["kst_dtm"], [10, 20, 30, 40, 50]),
    "sample_submission": sample,
    "ldaps_test": makeWeatherFrame(sample["forecast_kst_dtm"], [6, 7]),
    "gfs_test": makeWeatherFrame(sample["forecast_kst_dtm"], [60, 70]),
  }


def testBaselineRunConfigInjectsSeedAndStableConfigHash():
  config = BaselineRunConfig(
    experiment_id="rf_smoke",
    seed=777,
    model_params={"n_estimators": 4, "n_jobs": 1},
  )

  assert config.effective_model_params()["random_state"] == 777
  assert config.effective_model_params()["n_jobs"] == 1
  assert config.config_sha256() == BaselineRunConfig(
    experiment_id="rf_smoke",
    seed=777,
    model_params={"n_jobs": 1, "n_estimators": 4},
  ).config_sha256()
  assert config.config_sha256() != BaselineRunConfig(
    experiment_id="rf_smoke",
    seed=778,
    model_params={"n_estimators": 4, "n_jobs": 1},
  ).config_sha256()


def testBaselineRunConfigNormalizesNonJsonModelParamsForStableHash():
  config = BaselineRunConfig(
    experiment_id="rf_smoke",
    seed=777,
    model_params={
      "depth": np.int64(4),
      "ratio": np.float64(0.25),
      "when": pd.Timestamp("2026-07-07 09:00:00", tz="Asia/Seoul"),
      "path": Path("configs/baseline.yaml"),
      "choices": {"b", "a"},
    },
  )
  nativeConfig = BaselineRunConfig(
    experiment_id="rf_smoke",
    seed=777,
    model_params={
      "depth": 4,
      "ratio": 0.25,
      "when": "2026-07-07T09:00:00+09:00",
      "path": "configs/baseline.yaml",
      "choices": ["a", "b"],
    },
  )

  assert config.config_sha256() == nativeConfig.config_sha256()


def testBuildSubmissionFilenameSlugifiesExperimentIdAndNormalizesTimestamp():
  assert build_submission_filename(
    "exp/a b",
    "abcdef123",
    "2026-07-07T09:00:00+09:00",
  ) == "submission_20260707_exp-a-b_abcdef1.csv"


def testBuildSubmissionFilenameRejectsInvalidTimestampAndEmptyExperimentId():
  with pytest.raises(ValueError, match="created_at_kst"):
    build_submission_filename("rf_smoke", "abcdef123", "not-a-timestamp")

  with pytest.raises(ValueError, match="experiment_id"):
    build_submission_filename(" / ", "abcdef123", "2026-07-07T09:00:00+09:00")


def testBuildSubmissionLedgerEntryRejectsBlankCreatedAt():
  submission = makeSampleSubmission(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"))

  with pytest.raises(ValueError, match="created_at_kst"):
    build_submission_ledger_entry(
      config=BaselineRunConfig(experiment_id="rf_smoke"),
      submission=submission,
      git_commit="abcdef123",
      data_manifest_sha256="manifest-sha",
      created_at_kst="",
    )


def testSubmissionCsvSha256UsesCanonicalCsvBytes():
  submission = makeSampleSubmission(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"))

  assert submission_csv_sha256(submission) == hashlib.sha256(submission_to_csv_bytes(submission)).hexdigest()


def testRunBaselineWithReproducibilityReturnsLedgerEntryWithoutWritingFiles(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)
  result = run_baseline_with_reproducibility(
    config=BaselineRunConfig(
      experiment_id="rf_smoke",
      seed=7,
      model_params={"n_estimators": 4, "n_jobs": 1},
    ),
    **tinyRunInputs(),
    git_commit="abc1234",
    data_manifest_sha256="manifest-sha",
    created_at_kst="2026-07-07T09:00:00+09:00",
  )

  ledger = result["ledger_entry"]
  assert ledger["experiment_id"] == "rf_smoke"
  assert ledger["seed"] == 7
  assert ledger["git_commit"] == "abc1234"
  assert ledger["data_manifest_sha256"] == "manifest-sha"
  assert ledger["submission_rows"] == 2
  assert ledger["submission_sha256"] == submission_csv_sha256(result["baseline_result"]["submission"])
  assert list(ledger) == SUBMISSION_LEDGER_COLUMNS
  assert set(ledger) == set(SUBMISSION_LEDGER_COLUMNS)
  assert list(tmp_path.iterdir()) == []


def testVerifyBaselineInferenceReproducibilityRunsTwiceWithSameSubmissionHash():
  report = verify_baseline_inference_reproducibility(
    config=BaselineRunConfig(
      experiment_id="rf_smoke",
      seed=7,
      model_params={"n_estimators": 4, "n_jobs": 1},
    ),
    **tinyRunInputs(),
    git_commit="abc1234",
    data_manifest_sha256="manifest-sha",
    repeats=2,
    created_at_kst="2026-07-07T09:00:00+09:00",
  )

  assert report["is_reproducible"] is True
  assert report["repeats"] == 2
  assert len({run["submission_sha256"] for run in report["runs"]}) == 1
  assert report["ledger_entry"]["submission_sha256"] == report["runs"][0]["submission_sha256"]
  assert report["runs"][0]["submission_filename"] == report["ledger_entry"]["submission_filename"]
  assert report["runs"][0]["created_at_kst"] == report["ledger_entry"]["created_at_kst"]
  assert report["runs"][0]["config_sha256"] == report["ledger_entry"]["config_sha256"]


def testLedgerEntryToFramePreservesColumnOrder():
  entry = {column: None for column in SUBMISSION_LEDGER_COLUMNS}

  frame = ledger_entry_to_frame(entry)

  assert list(frame.columns) == SUBMISSION_LEDGER_COLUMNS
  assert len(frame) == 1
