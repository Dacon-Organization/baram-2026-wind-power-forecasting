import hashlib

import pandas as pd
import pytest

from baram.metrics import CAPACITY_KWH, TARGET_COLS
from baram.reproducibility import submission_to_csv_bytes
from baram.validation import (
  EXPECTED_SUBMISSION_ROWS,
  SUBMISSION_COLUMNS,
  assert_valid_submission,
  build_validated_submission_artifact,
  validate_submission,
)


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


def withWrongColumnOrder(submission):
  return submission[["forecast_kst_dtm", "forecast_id", *TARGET_COLS]].copy()


def withWrongRowCount(submission):
  return submission.iloc[:-1].copy()


def withWrongForecastId(submission):
  broken = submission.copy()
  broken.loc[10, "forecast_id"] = "forecast_broken"
  return broken


def withWrongForecastTime(submission):
  broken = submission.copy()
  broken.loc[10, "forecast_kst_dtm"] = "2025-01-03 03:00:00"
  return broken


def withTargetNan(submission):
  broken = submission.copy()
  broken.loc[20, "kpx_group_1"] = pd.NA
  return broken


def withNegativeTarget(submission):
  broken = submission.copy()
  broken.loc[30, "kpx_group_2"] = -0.01
  return broken


def withCapacityExceeded(submission):
  broken = submission.copy()
  broken.loc[40, "kpx_group_3"] = CAPACITY_KWH["kpx_group_3"] + 0.01
  return broken


@pytest.mark.parametrize(
  ("breakSubmission", "expectedMessage"),
  [
    (withWrongColumnOrder, "column order"),
    (withWrongRowCount, "row count"),
    (withWrongForecastId, "forecast_id"),
    (withWrongForecastTime, "forecast_kst_dtm"),
    (withTargetNan, "NaN"),
    (withNegativeTarget, "negative"),
    (withCapacityExceeded, "capacity"),
  ],
)
def testInvalidSubmissionsAreRejectedBeforeCsvBytes(breakSubmission, expectedMessage):
  sampleSubmission = makeSampleSubmission()
  brokenSubmission = breakSubmission(makeValidSubmission())

  report = validate_submission(brokenSubmission, sampleSubmission)

  assert report.ok is False
  assert any(expectedMessage in error for error in report.errors)
  with pytest.raises(ValueError, match=expectedMessage):
    assert_valid_submission(brokenSubmission, sampleSubmission)


def testValidSubmissionReturnsCanonicalUtf8SigBytesAndHash():
  sampleSubmission = makeSampleSubmission()
  submission = makeValidSubmission()

  artifact = build_validated_submission_artifact(
    submission,
    sampleSubmission,
    encoding="utf-8-sig",
  )

  assert artifact.report.ok is True
  assert artifact.encoding == "utf-8-sig"
  assert artifact.csv_bytes == submission_to_csv_bytes(submission, encoding="utf-8-sig")
  assert artifact.csv_bytes.startswith(b"\xef\xbb\xbf")
  assert artifact.sha256 == hashlib.sha256(artifact.csv_bytes).hexdigest()
  assert artifact.ledger_sha256 == artifact.sha256


def testValidSubmissionCanUsePlainUtf8BytesWithoutBom():
  sampleSubmission = makeSampleSubmission()
  submission = makeValidSubmission()

  artifact = build_validated_submission_artifact(
    submission,
    sampleSubmission,
    encoding="utf-8",
  )

  assert artifact.csv_bytes == submission_to_csv_bytes(submission, encoding="utf-8")
  assert not artifact.csv_bytes.startswith(b"\xef\xbb\xbf")
  assert artifact.sha256 == hashlib.sha256(artifact.csv_bytes).hexdigest()


def testSubmissionColumnContractMatchesOfficialTemplate():
  assert EXPECTED_SUBMISSION_ROWS == 8760
  assert SUBMISSION_COLUMNS == ["forecast_id", "forecast_kst_dtm", *TARGET_COLS]
