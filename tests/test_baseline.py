import numpy as np
import pandas as pd
import pytest

from baram.baseline import (
  build_inference_features,
  build_submission,
  build_training_features,
  predict_random_forest_baseline,
  run_train_inference,
  train_random_forest_baseline,
)
from baram.metrics import CAPACITY_KWH, TARGET_COLS


def makeWeatherFrame(times, values, *, bad_cutoff=False, missing_last=False):
  rows = []
  for timeIndex, forecastTime in enumerate(pd.to_datetime(times)):
    availableTime = forecastTime - pd.Timedelta(hours=12)
    if bad_cutoff and timeIndex == 0:
      availableTime = forecastTime + pd.Timedelta(hours=1)
    for gridId in [1, 2]:
      value = float(values[timeIndex] + gridId)
      if missing_last and timeIndex == len(times) - 1 and gridId == 2:
        value = np.nan
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


def tinyModelParams():
  return {
    "n_estimators": 4,
    "random_state": 7,
    "n_jobs": 1,
  }


def testBuildFeatureSetsPreserveSubmissionKeysAndAddLeadFeatures():
  labels = makeLabelFrame()
  sample = makeSampleSubmission(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"))
  ldapsTrain = makeWeatherFrame(labels["kst_dtm"], [1, 2, 3, 4, 5])
  gfsTrain = makeWeatherFrame(labels["kst_dtm"], [10, 20, 30, 40, 50])
  ldapsTest = makeWeatherFrame(sample["forecast_kst_dtm"], [6, 7])
  gfsTest = makeWeatherFrame(sample["forecast_kst_dtm"], [60, 70])

  trainFeatures = build_training_features(labels, ldapsTrain, gfsTrain)
  inferenceFeatures = build_inference_features(sample, ldapsTest, gfsTest)

  assert "ldaps_lead_hour" in trainFeatures.X.columns
  assert "gfs_lead_hour" in trainFeatures.X.columns
  assert list(inferenceFeatures.frame["forecast_id"]) == list(sample["forecast_id"])
  assert list(inferenceFeatures.frame["forecast_kst_dtm"]) == list(sample["forecast_kst_dtm"])


def testTrainingUsesTargetSpecificNonNullMaskAndPredictionsAreClipped():
  labels = makeLabelFrame()
  sample = makeSampleSubmission(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"))
  trainFeatures = build_training_features(
    labels,
    makeWeatherFrame(labels["kst_dtm"], [1, 2, 3, 4, 5]),
    makeWeatherFrame(labels["kst_dtm"], [10, 20, 30, 40, 50]),
  )
  inferenceFeatures = build_inference_features(
    sample,
    makeWeatherFrame(sample["forecast_kst_dtm"], [6, 7]),
    makeWeatherFrame(sample["forecast_kst_dtm"], [60, 70]),
  )

  bundle = train_random_forest_baseline(
    trainFeatures.X,
    trainFeatures.frame,
    model_params=tinyModelParams(),
  )
  predictions = predict_random_forest_baseline(bundle, inferenceFeatures.X)

  assert bundle.train_rows["kpx_group_3"] == 3
  assert set(bundle.models) == set(TARGET_COLS)
  assert list(predictions.columns) == TARGET_COLS
  for target in TARGET_COLS:
    assert predictions[target].between(0, CAPACITY_KWH[target]).all()


def testInferenceWeatherMissingIsHandledByTrainingMedianImputer():
  labels = makeLabelFrame()
  sample = makeSampleSubmission(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"))
  trainFeatures = build_training_features(
    labels,
    makeWeatherFrame(labels["kst_dtm"], [1, 2, 3, 4, 5]),
    makeWeatherFrame(labels["kst_dtm"], [10, 20, 30, 40, 50]),
  )
  inferenceFeatures = build_inference_features(
    sample,
    makeWeatherFrame(sample["forecast_kst_dtm"], [6, 7], missing_last=True),
    makeWeatherFrame(sample["forecast_kst_dtm"], [60, 70], missing_last=True),
  )

  bundle = train_random_forest_baseline(
    trainFeatures.X,
    trainFeatures.frame,
    model_params=tinyModelParams(),
  )
  predictions = predict_random_forest_baseline(bundle, inferenceFeatures.X)

  assert not np.isnan(bundle.imputer.statistics_).any()
  assert not predictions.isna().any().any()


def testWeatherCutoffGuardRejectsUnavailableFutureForecast():
  labels = makeLabelFrame()
  badWeather = makeWeatherFrame(labels["kst_dtm"], [1, 2, 3, 4, 5], bad_cutoff=True)
  goodWeather = makeWeatherFrame(labels["kst_dtm"], [10, 20, 30, 40, 50])

  with pytest.raises(ValueError, match="cutoff"):
    build_training_features(labels, badWeather, goodWeather)


def testBuildSubmissionKeepsTemplateIdentityColumnsFixed():
  sample = makeSampleSubmission(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"))
  predictions = pd.DataFrame(
    {
      "kpx_group_1": [1.0, 2.0],
      "kpx_group_2": [3.0, 4.0],
      "kpx_group_3": [5.0, 6.0],
    }
  )

  submission = build_submission(sample, predictions)

  assert list(submission.columns) == ["forecast_id", "forecast_kst_dtm", *TARGET_COLS]
  assert list(submission["forecast_id"]) == list(sample["forecast_id"])
  assert list(submission["forecast_kst_dtm"]) == list(sample["forecast_kst_dtm"])
  pd.testing.assert_frame_equal(submission[TARGET_COLS], predictions[TARGET_COLS])


def testRunTrainInferenceDoesNotWriteArtifacts(tmp_path, monkeypatch):
  labels = makeLabelFrame()
  sample = makeSampleSubmission(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"))

  monkeypatch.chdir(tmp_path)
  result = run_train_inference(
    labels,
    makeWeatherFrame(labels["kst_dtm"], [1, 2, 3, 4, 5]),
    makeWeatherFrame(labels["kst_dtm"], [10, 20, 30, 40, 50]),
    sample,
    makeWeatherFrame(sample["forecast_kst_dtm"], [6, 7]),
    makeWeatherFrame(sample["forecast_kst_dtm"], [60, 70]),
    model_params=tinyModelParams(),
  )

  assert result["submission"].shape == (2, 5)
  assert list(tmp_path.iterdir()) == []


def testTrainingRejectsMisalignedFeatureAndLabelIndexes():
  labels = makeLabelFrame()
  trainFeatures = build_training_features(
    labels,
    makeWeatherFrame(labels["kst_dtm"], [1, 2, 3, 4, 5]),
    makeWeatherFrame(labels["kst_dtm"], [10, 20, 30, 40, 50]),
  )
  shiftedFrame = trainFeatures.frame.copy()
  shiftedFrame.index = shiftedFrame.index + 100

  with pytest.raises(ValueError, match="index"):
    train_random_forest_baseline(
      trainFeatures.X,
      shiftedFrame,
      model_params=tinyModelParams(),
    )
