"""BARAM 제출 CSV 검증과 canonical bytes 생성."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pandas as pd

from baram.metrics import CAPACITY_KWH
from baram.metrics import TARGET_COLS
from baram.reproducibility import submission_to_csv_bytes


EXPECTED_SUBMISSION_ROWS = 8760
SUBMISSION_COLUMNS = ["forecast_id", "forecast_kst_dtm", *TARGET_COLS]
SUPPORTED_ENCODINGS = {"utf-8", "utf-8-sig"}


@dataclass(frozen=True)
class SubmissionValidationReport:
  ok: bool
  errors: list[str]
  row_count: int
  columns: list[str]


@dataclass(frozen=True)
class SubmissionCsvArtifact:
  csv_bytes: bytes
  sha256: str
  ledger_sha256: str
  encoding: str
  report: SubmissionValidationReport


def _string_series(frame, column):
  return frame[column].astype(str).reset_index(drop=True)


def _first_mismatch(left, right):
  mismatch_mask = left.ne(right)
  if not mismatch_mask.any():
    return None
  return int(mismatch_mask[mismatch_mask].index[0])


def _target_numeric_series(submission, target, errors):
  values = pd.to_numeric(submission[target], errors="coerce")
  if values.isna().any():
    errors.append(f"{target} NaN values: {int(values.isna().sum())}")
  return values


def validate_submission(submission, sample_submission):
  """공식 sample_submission 기준으로 제출 후보의 구조와 값을 검증한다."""
  errors = []
  columns = list(submission.columns)
  row_count = int(len(submission))

  if columns != SUBMISSION_COLUMNS:
    errors.append(f"column order mismatch: expected {SUBMISSION_COLUMNS}, got {columns}")

  if row_count != EXPECTED_SUBMISSION_ROWS:
    errors.append(f"row count mismatch: expected {EXPECTED_SUBMISSION_ROWS}, got {row_count}")

  sample_columns = list(sample_submission.columns)
  if sample_columns != SUBMISSION_COLUMNS:
    errors.append(f"sample column order mismatch: expected {SUBMISSION_COLUMNS}, got {sample_columns}")

  if len(sample_submission) != EXPECTED_SUBMISSION_ROWS:
    errors.append(
      f"sample row count mismatch: expected {EXPECTED_SUBMISSION_ROWS}, got {len(sample_submission)}"
    )

  has_identity_columns = all(
    column in submission.columns and column in sample_submission.columns
    for column in ["forecast_id", "forecast_kst_dtm"]
  )
  if has_identity_columns and row_count == len(sample_submission):
    forecast_id_mismatch = _first_mismatch(
      _string_series(submission, "forecast_id"),
      _string_series(sample_submission, "forecast_id"),
    )
    if forecast_id_mismatch is not None:
      errors.append(f"forecast_id mismatch at row {forecast_id_mismatch}")

    forecast_time_mismatch = _first_mismatch(
      _string_series(submission, "forecast_kst_dtm"),
      _string_series(sample_submission, "forecast_kst_dtm"),
    )
    if forecast_time_mismatch is not None:
      errors.append(f"forecast_kst_dtm mismatch at row {forecast_time_mismatch}")

  for target in TARGET_COLS:
    if target not in submission.columns:
      continue
    values = _target_numeric_series(submission, target, errors)
    if values.isna().any():
      continue

    negative_count = int((values < 0).sum())
    if negative_count:
      errors.append(f"{target} negative values: {negative_count}")

    capacity_count = int((values > CAPACITY_KWH[target]).sum())
    if capacity_count:
      errors.append(f"{target} capacity exceeded values: {capacity_count}")

  return SubmissionValidationReport(
    ok=len(errors) == 0,
    errors=errors,
    row_count=row_count,
    columns=columns,
  )


def assert_valid_submission(submission, sample_submission):
  report = validate_submission(submission, sample_submission)
  if not report.ok:
    raise ValueError("; ".join(report.errors))
  return report


def build_validated_submission_artifact(submission, sample_submission, encoding="utf-8-sig"):
  if encoding not in SUPPORTED_ENCODINGS:
    raise ValueError(f"encoding must be one of {sorted(SUPPORTED_ENCODINGS)}")
  report = assert_valid_submission(submission, sample_submission)
  csv_bytes = submission_to_csv_bytes(submission, encoding=encoding)
  csv_sha256 = hashlib.sha256(csv_bytes).hexdigest()
  return SubmissionCsvArtifact(
    csv_bytes=csv_bytes,
    sha256=csv_sha256,
    ledger_sha256=csv_sha256,
    encoding=encoding,
    report=report,
  )


__all__ = [
  "EXPECTED_SUBMISSION_ROWS",
  "SUBMISSION_COLUMNS",
  "SubmissionCsvArtifact",
  "SubmissionValidationReport",
  "assert_valid_submission",
  "build_validated_submission_artifact",
  "validate_submission",
]
