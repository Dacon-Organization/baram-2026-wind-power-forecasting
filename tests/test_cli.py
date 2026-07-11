import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from baram.inference import main as inferenceMain
from baram.inference import _validate_output_paths as validateInferenceOutputPaths
from baram.inference import write_submission_after_validation
from baram.metrics import CAPACITY_KWH
from baram.train import main as trainMain
from baram.train import _validate_output_paths as validateTrainOutputPaths
from baram.validation import EXPECTED_SUBMISSION_ROWS


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def makeSampleSubmission(rowCount=EXPECTED_SUBMISSION_ROWS):
  forecastTimes = pd.date_range("2025-01-01 01:00:00", periods=rowCount, freq="h")
  return pd.DataFrame(
    {
      "forecast_id": [f"forecast_{index:04d}" for index in range(1, rowCount + 1)],
      "forecast_kst_dtm": forecastTimes.strftime("%Y-%m-%d %H:%M:%S"),
      "kpx_group_1": 0.0,
      "kpx_group_2": 0.0,
      "kpx_group_3": 0.0,
    }
  )


def makeValidSubmission():
  submission = makeSampleSubmission().copy()
  submission["kpx_group_1"] = 100.0
  submission["kpx_group_2"] = 200.0
  submission["kpx_group_3"] = 300.0
  return submission


def makeWeatherFrame(times, values):
  rows = []
  for timeIndex, forecastTime in enumerate(pd.to_datetime(times)):
    for gridId in [1, 2]:
      value = float(values[timeIndex] + gridId)
      rows.append(
        {
          "forecast_kst_dtm": forecastTime,
          "data_available_kst_dtm": forecastTime - pd.Timedelta(hours=12),
          "grid_id": gridId,
          "latitude": 37.0 + gridId * 0.01,
          "longitude": 128.0 + gridId * 0.01,
          "heightAboveGround_10_10u": value,
          "heightAboveGround_10_10v": value * 2,
        }
      )
  return pd.DataFrame(rows)


def createRegisteredModelFiles(tmp_path):
  times = pd.date_range("2024-01-01 01:00:00", periods=5, freq="h")
  labels = pd.DataFrame(
    {
      "kst_dtm": times,
      "kpx_group_1": [1000.0, 2000.0, 3000.0, 4000.0, 5000.0],
      "kpx_group_2": [2000.0, 3000.0, 4000.0, 5000.0, 6000.0],
      "kpx_group_3": [None, None, 3000.0, 4000.0, 5000.0],
    }
  )
  labelsPath = tmp_path / "train_labels.csv"
  ldapsPath = tmp_path / "ldaps_train.csv"
  gfsPath = tmp_path / "gfs_train.csv"
  manifestPath = tmp_path / "MANIFEST.md"
  modelPath = tmp_path / "baseline.pkl"
  registryPath = tmp_path / "run_registry.csv"
  labels.to_csv(labelsPath, index=False, encoding="utf-8-sig")
  makeWeatherFrame(times, [1, 2, 3, 4, 5]).to_csv(ldapsPath, index=False, encoding="utf-8-sig")
  makeWeatherFrame(times, [10, 20, 30, 40, 50]).to_csv(gfsPath, index=False, encoding="utf-8-sig")
  manifestPath.write_text("synthetic manifest", encoding="utf-8")

  status = trainMain(
    [
      "--run",
      "--train-labels", str(labelsPath),
      "--ldaps-train", str(ldapsPath),
      "--gfs-train", str(gfsPath),
      "--model-output", str(modelPath),
      "--registry-output", str(registryPath),
      "--data-manifest", str(manifestPath),
      "--git-commit", "abcdef123456",
      "--experiment-id", "cli_registry_smoke",
      "--n-estimators", "4",
      "--n-jobs", "1",
    ]
  )
  return {
    "status": status,
    "model": modelPath,
    "metadata": modelPath.with_name(f"{modelPath.name}.metadata.json"),
    "registry": registryPath,
  }


def testTrainAndInferenceDefaultEntrypointsDoNotCreateArtifacts(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)

  assert trainMain([]) == 0
  assert inferenceMain([]) == 0

  assert list(tmp_path.iterdir()) == []


def testScriptEntrypointsRunDryWithoutPythonpath(tmp_path):
  for scriptPath in [
    PROJECT_ROOT / "src" / "baram" / "train.py",
    PROJECT_ROOT / "src" / "baram" / "inference.py",
  ]:
    result = subprocess.run(
      [sys.executable, str(scriptPath)],
      cwd=tmp_path,
      capture_output=True,
      text=True,
      check=False,
    )
    assert result.returncode == 0, result.stderr

  assert list(tmp_path.iterdir()) == []


def testTrainRunWritesModelSidecarAndRegistryWithExactHashes(tmp_path):
  paths = createRegisteredModelFiles(tmp_path)
  modelPath = paths["model"]
  metadataPath = paths["metadata"]
  metadataBytes = metadataPath.read_bytes()
  metadata = json.loads(metadataBytes.decode("utf-8"))
  registry = pd.read_csv(paths["registry"], encoding="utf-8-sig")
  row = registry.iloc[0]

  assert paths["status"] == 0
  assert metadata["model"]["model_sha256"] == hashlib.sha256(modelPath.read_bytes()).hexdigest()
  assert row["metadata_sha256"] == hashlib.sha256(metadataBytes).hexdigest()
  assert row["model_sha256"] == metadata["model"]["model_sha256"]
  assert row["run_id"] == metadata["run_id"]
  assert row["status"] == "trained"


def testInferenceRunLoadsRegisteredSidecarAndUpdatesValidatedSubmissionHash(tmp_path):
  paths = createRegisteredModelFiles(tmp_path)
  sample = makeSampleSubmission()
  forecastTimes = pd.to_datetime(sample["forecast_kst_dtm"])
  samplePath = tmp_path / "sample_submission.csv"
  ldapsTestPath = tmp_path / "ldaps_test.csv"
  gfsTestPath = tmp_path / "gfs_test.csv"
  submissionPath = tmp_path / "submission.csv"
  sample.to_csv(samplePath, index=False, encoding="utf-8-sig")
  values = range(EXPECTED_SUBMISSION_ROWS)
  makeWeatherFrame(forecastTimes, values).to_csv(ldapsTestPath, index=False, encoding="utf-8-sig")
  makeWeatherFrame(forecastTimes, values).to_csv(gfsTestPath, index=False, encoding="utf-8-sig")

  status = inferenceMain(
    [
      "--run",
      "--model-input", str(paths["model"]),
      "--model-metadata", str(paths["metadata"]),
      "--run-registry", str(paths["registry"]),
      "--sample-submission", str(samplePath),
      "--ldaps-test", str(ldapsTestPath),
      "--gfs-test", str(gfsTestPath),
      "--submission-output", str(submissionPath),
      "--encoding", "utf-8-sig",
    ]
  )

  registry = pd.read_csv(paths["registry"], encoding="utf-8-sig")
  row = registry.iloc[0]
  savedBytes = submissionPath.read_bytes()
  assert status == 0
  assert row["status"] == "submission_validated"
  assert row["submission_filename"] == submissionPath.as_posix()
  assert row["submission_sha256"] == hashlib.sha256(savedBytes).hexdigest()
  assert row["submission_rows"] == EXPECTED_SUBMISSION_ROWS
  assert row["submission_encoding"] == "utf-8-sig"


def testCliRejectsArtifactPathCollisions(tmp_path):
  modelPath = tmp_path / "baseline.pkl"
  with pytest.raises(ValueError, match="서로 달라야"):
    validateTrainOutputPaths(
      SimpleNamespace(
        model_output=modelPath,
        metadata_output=None,
        registry_output=modelPath,
      )
    )

  registryPath = tmp_path / "run_registry.csv"
  with pytest.raises(ValueError, match="충돌"):
    validateInferenceOutputPaths(
      SimpleNamespace(
        model_input=modelPath,
        model_metadata=None,
        run_registry=registryPath,
        sample_submission=tmp_path / "sample.csv",
        ldaps_test=tmp_path / "ldaps.csv",
        gfs_test=tmp_path / "gfs.csv",
        submission_output=registryPath,
      )
    )


def testInferenceWriterDoesNotSaveWhenValidatorFails(tmp_path):
  sampleSubmission = makeSampleSubmission()
  brokenSubmission = makeValidSubmission()
  brokenSubmission.loc[0, "kpx_group_3"] = CAPACITY_KWH["kpx_group_3"] + 1
  outputPath = tmp_path / "submission.csv"

  with pytest.raises(ValueError, match="capacity"):
    write_submission_after_validation(brokenSubmission, sampleSubmission, outputPath)

  assert not outputPath.exists()


def testInferenceWriterUsesValidatedCanonicalBytesForLedgerHash(tmp_path):
  sampleSubmission = makeSampleSubmission()
  submission = makeValidSubmission()
  outputPath = tmp_path / "submission.csv"

  artifact = write_submission_after_validation(
    submission,
    sampleSubmission,
    outputPath,
    encoding="utf-8-sig",
  )

  savedBytes = outputPath.read_bytes()
  assert savedBytes == artifact.csv_bytes
  assert artifact.sha256 == hashlib.sha256(savedBytes).hexdigest()
  assert artifact.ledger_sha256 == artifact.sha256
