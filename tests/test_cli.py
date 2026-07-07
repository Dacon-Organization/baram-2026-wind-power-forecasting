import hashlib
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from baram.inference import main as inferenceMain
from baram.inference import write_submission_after_validation
from baram.metrics import CAPACITY_KWH
from baram.train import main as trainMain
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
