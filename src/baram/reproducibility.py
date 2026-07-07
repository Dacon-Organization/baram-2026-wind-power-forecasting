"""Baseline inference reproducibility helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import random
from collections.abc import Mapping
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from baram.baseline import run_train_inference


SUBMISSION_LEDGER_COLUMNS = [
  "created_at_kst",
  "experiment_id",
  "git_commit",
  "seed",
  "config_sha256",
  "data_manifest_sha256",
  "submission_filename",
  "submission_sha256",
  "submission_rows",
  "submission_columns",
  "local_score",
  "public_score",
  "dacon_submission_id",
  "selected",
  "note",
]


@dataclass(frozen=True)
class BaselineRunConfig:
  experiment_id: str
  seed: int = 42
  model_params: Mapping[str, Any] | None = None
  notes: str = ""

  def effective_model_params(self) -> dict[str, Any]:
    params = dict(self.model_params or {})
    params["random_state"] = self.seed
    return params

  def as_record(self) -> dict[str, Any]:
    return {
      "experiment_id": self.experiment_id,
      "seed": self.seed,
      "model_params": self.effective_model_params(),
      "notes": self.notes,
    }

  def config_sha256(self) -> str:
    return sha256_text(stable_json_dumps(self.as_record()))


def seed_everything(seed):
  random.seed(seed)
  np.random.seed(seed)


def _normalize_for_json(value):
  if isinstance(value, np.generic):
    return _normalize_for_json(value.item())
  if isinstance(value, pd.Timestamp):
    return value.isoformat()
  if isinstance(value, datetime):
    return value.isoformat()
  if isinstance(value, date):
    return value.isoformat()
  if isinstance(value, Path):
    return value.as_posix()
  if isinstance(value, Mapping):
    return {
      _normalize_for_json(key): _normalize_for_json(item)
      for key, item in value.items()
    }
  if isinstance(value, (list, tuple)):
    return [_normalize_for_json(item) for item in value]
  if isinstance(value, set):
    normalized_items = [_normalize_for_json(item) for item in value]
    return sorted(normalized_items, key=lambda item: stable_json_dumps(item))
  return value


def stable_json_dumps(value):
  normalized = _normalize_for_json(value)
  return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value):
  return hashlib.sha256(value.encode("utf-8")).hexdigest()


def submission_to_csv_bytes(submission, encoding="utf-8-sig"):
  csv_text = submission.to_csv(
    index=False,
    date_format="%Y-%m-%d %H:%M:%S",
    lineterminator="\n",
  )
  return csv_text.encode(encoding)


def submission_csv_sha256(submission, encoding="utf-8-sig"):
  return hashlib.sha256(submission_to_csv_bytes(submission, encoding=encoding)).hexdigest()


def slugify_experiment_id(experiment_id):
  slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(experiment_id).strip()).strip("-")
  if not slug:
    raise ValueError("experiment_id must contain at least one filename-safe character")
  return slug


def normalize_created_at_kst(created_at_kst):
  try:
    timestamp = pd.Timestamp(created_at_kst)
  except (TypeError, ValueError) as exc:
    raise ValueError("created_at_kst must be a valid ISO timestamp, datetime, or pandas Timestamp") from exc
  if pd.isna(timestamp):
    raise ValueError("created_at_kst must be a valid ISO timestamp, datetime, or pandas Timestamp")
  if timestamp.tzinfo is None:
    timestamp = timestamp.tz_localize(ZoneInfo("Asia/Seoul"))
  else:
    timestamp = timestamp.tz_convert(ZoneInfo("Asia/Seoul"))
  return timestamp.to_pydatetime().isoformat(timespec="seconds")


def build_submission_filename(experiment_id, git_commit, created_at_kst):
  normalized_created_at = normalize_created_at_kst(created_at_kst)
  date_part = pd.Timestamp(normalized_created_at).strftime("%Y%m%d")
  experiment_slug = slugify_experiment_id(experiment_id)
  short_sha = git_commit[:7] if git_commit else "unknown"
  return f"submission_{date_part}_{experiment_slug}_{short_sha}.csv"


def _current_kst_isoformat():
  return datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")


def build_submission_ledger_entry(
  *,
  config,
  submission,
  git_commit,
  data_manifest_sha256,
  created_at_kst=None,
  local_score=None,
  public_score=None,
  dacon_submission_id=None,
  selected=False,
  note=None,
):
  created_at_source = _current_kst_isoformat() if created_at_kst is None else created_at_kst
  created_at = normalize_created_at_kst(created_at_source)
  entry = {
    "created_at_kst": created_at,
    "experiment_id": config.experiment_id,
    "git_commit": git_commit,
    "seed": config.seed,
    "config_sha256": config.config_sha256(),
    "data_manifest_sha256": data_manifest_sha256,
    "submission_filename": build_submission_filename(config.experiment_id, git_commit, created_at),
    "submission_sha256": submission_csv_sha256(submission),
    "submission_rows": int(len(submission)),
    "submission_columns": list(submission.columns),
    "local_score": local_score,
    "public_score": public_score,
    "dacon_submission_id": dacon_submission_id,
    "selected": selected,
    "note": config.notes if note is None else note,
  }
  return {column: entry[column] for column in SUBMISSION_LEDGER_COLUMNS}


def ledger_entry_to_frame(entry):
  return pd.DataFrame([{column: entry[column] for column in SUBMISSION_LEDGER_COLUMNS}], columns=SUBMISSION_LEDGER_COLUMNS)


def run_baseline_with_reproducibility(
  *,
  config,
  train_labels,
  ldaps_train,
  gfs_train,
  sample_submission,
  ldaps_test,
  gfs_test,
  git_commit,
  data_manifest_sha256,
  created_at_kst=None,
  local_score=None,
  public_score=None,
  dacon_submission_id=None,
  selected=False,
  note=None,
):
  seed_everything(config.seed)
  baseline_result = run_train_inference(
    train_labels,
    ldaps_train,
    gfs_train,
    sample_submission,
    ldaps_test,
    gfs_test,
    model_params=config.effective_model_params(),
  )
  ledger_entry = build_submission_ledger_entry(
    config=config,
    submission=baseline_result["submission"],
    git_commit=git_commit,
    data_manifest_sha256=data_manifest_sha256,
    created_at_kst=created_at_kst,
    local_score=local_score,
    public_score=public_score,
    dacon_submission_id=dacon_submission_id,
    selected=selected,
    note=note,
  )
  return {"baseline_result": baseline_result, "ledger_entry": ledger_entry}


def verify_baseline_inference_reproducibility(
  *,
  config,
  train_labels,
  ldaps_train,
  gfs_train,
  sample_submission,
  ldaps_test,
  gfs_test,
  git_commit,
  data_manifest_sha256,
  repeats=2,
  created_at_kst=None,
  local_score=None,
  public_score=None,
  dacon_submission_id=None,
  selected=False,
  note=None,
):
  if repeats < 1:
    raise ValueError("repeats must be at least 1")

  runs = []
  last_result = None
  for repeat_index in range(repeats):
    last_result = run_baseline_with_reproducibility(
      config=config,
      train_labels=train_labels,
      ldaps_train=ldaps_train,
      gfs_train=gfs_train,
      sample_submission=sample_submission,
      ldaps_test=ldaps_test,
      gfs_test=gfs_test,
      git_commit=git_commit,
      data_manifest_sha256=data_manifest_sha256,
      created_at_kst=created_at_kst,
      local_score=local_score,
      public_score=public_score,
      dacon_submission_id=dacon_submission_id,
      selected=selected,
      note=note,
    )
    runs.append(
      {
        "run_index": repeat_index + 1,
        "created_at_kst": last_result["ledger_entry"]["created_at_kst"],
        "submission_filename": last_result["ledger_entry"]["submission_filename"],
        "submission_sha256": last_result["ledger_entry"]["submission_sha256"],
        "config_sha256": last_result["ledger_entry"]["config_sha256"],
      }
    )

  expected_submission_sha256 = runs[0]["submission_sha256"]
  return {
    "is_reproducible": all(run["submission_sha256"] == expected_submission_sha256 for run in runs),
    "repeats": repeats,
    "runs": runs,
    "ledger_entry": last_result["ledger_entry"],
  }


__all__ = [
  "SUBMISSION_LEDGER_COLUMNS",
  "BaselineRunConfig",
  "build_submission_filename",
  "build_submission_ledger_entry",
  "ledger_entry_to_frame",
  "normalize_created_at_kst",
  "run_baseline_with_reproducibility",
  "seed_everything",
  "sha256_text",
  "slugify_experiment_id",
  "stable_json_dumps",
  "submission_to_csv_bytes",
  "submission_csv_sha256",
  "verify_baseline_inference_reproducibility",
]
