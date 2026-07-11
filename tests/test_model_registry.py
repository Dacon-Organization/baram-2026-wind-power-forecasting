import copy
import hashlib

import numpy as np
import pandas as pd
import pytest

from baram.baseline import build_training_features
from baram.baseline import train_random_forest_baseline
from baram.registry import (
  RUN_REGISTRY_COLUMNS,
  append_run_registry_entry,
  build_model_artifact,
  build_run_registry_entry,
  build_training_data_profile,
  default_metadata_path,
  fingerprint_files,
  load_registered_model_artifact,
  load_model_artifact_bytes,
  save_model_artifact,
  update_run_registry_submission,
)
from baram.reproducibility import BaselineRunConfig


def makeWeatherFrame(times, values, *, missing_last=False):
  rows = []
  for timeIndex, forecastTime in enumerate(pd.to_datetime(times)):
    availableTime = forecastTime - pd.Timedelta(hours=12 + timeIndex)
    for gridId in [1, 2]:
      value = float(values[timeIndex] + gridId)
      if missing_last and timeIndex == len(times) - 1:
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
      "kpx_group_3": [np.nan, np.nan, 2100.0, 5000.0, 22000.0],
    }
  )


def makeModelContext(*, validation=None):
  labels = makeLabelFrame()
  ldaps = makeWeatherFrame(labels["kst_dtm"], [1, 2, 3, 4, 5], missing_last=True)
  gfs = makeWeatherFrame(labels["kst_dtm"], [10, 20, 30, 40, 50])
  features = build_training_features(labels, ldaps, gfs)
  bundle = train_random_forest_baseline(
    features.X,
    features.frame,
    model_params={"n_estimators": 4, "random_state": 7, "n_jobs": 1},
  )
  profile = build_training_data_profile(
    train_labels=labels,
    ldaps_train=ldaps,
    gfs_train=gfs,
    train_features=features,
  )
  config = BaselineRunConfig(
    experiment_id="rf_registry_smoke",
    seed=7,
    model_params={"n_estimators": 4, "n_jobs": 1},
    notes="registry contract test",
  )
  artifact = build_model_artifact(
    bundle=bundle,
    config=config,
    data_profile=profile,
    git_commit="abcdef123456",
    data_manifest_sha256="1" * 64,
    created_at_kst="2026-07-11T09:00:00+09:00",
    validation=validation,
  )
  return labels, features, bundle, profile, config, artifact


def testTrainingDataProfileCapturesDataUnderstandingAndPreprocessingContract():
  labels, features, _, profile, _, _ = makeModelContext()

  assert profile["labels"]["rows"] == len(labels)
  assert profile["labels"]["target_missing_rows"]["kpx_group_3"] == 2
  assert profile["labels"]["capacity_exceedance_rows"]["kpx_group_3"] == 1
  assert profile["weather"]["ldaps"]["grid_count_min"] == 2
  assert profile["weather"]["ldaps"]["grid_count_max"] == 2
  assert profile["weather"]["ldaps"]["lead_hour_min"] == 12.0
  assert profile["weather"]["ldaps"]["lead_hour_max"] == 16.0
  assert profile["feature_matrix"]["feature_columns"] == list(features.X.columns)
  assert profile["feature_matrix"]["missing_cells_before_imputation"] > 0
  assert len(profile["feature_matrix"]["feature_schema_sha256"]) == 64
  assert profile["preprocessing"]["weather_aggregation"]["statistics"] == ["mean"]
  assert profile["preprocessing"]["missing_values"]["strategy"] == "median"


def testModelArtifactHashesExactModelAndMetadataBytes():
  _, _, bundle, _, _, artifact = makeModelContext()

  assert artifact.model_sha256 == hashlib.sha256(artifact.model_bytes).hexdigest()
  assert artifact.metadata_sha256 == hashlib.sha256(artifact.metadata_bytes).hexdigest()
  assert artifact.metadata["model"]["model_sha256"] == artifact.model_sha256
  assert artifact.metadata["model"]["feature_columns"] == bundle.feature_columns
  assert artifact.metadata["model"]["target_train_rows"] == bundle.train_rows
  assert artifact.metadata["data_profile_sha256"]
  assert artifact.metadata["preprocessing_sha256"]


def testModelArtifactRoundTripRejectsTamperedBytesBeforeUnpickle():
  _, _, bundle, _, _, artifact = makeModelContext()

  loadedBundle, loadedMetadata = load_model_artifact_bytes(
    artifact.model_bytes,
    artifact.metadata_bytes,
  )
  assert loadedBundle.feature_columns == bundle.feature_columns
  assert loadedMetadata["run_id"] == artifact.metadata["run_id"]

  tamperedBytes = artifact.model_bytes[:-1] + bytes([artifact.model_bytes[-1] ^ 1])
  with pytest.raises(ValueError, match="model SHA256"):
    load_model_artifact_bytes(tamperedBytes, artifact.metadata_bytes)


def testBuildModelArtifactRejectsFeatureOrderDrift():
  _, _, bundle, profile, config, _ = makeModelContext()
  driftedProfile = copy.deepcopy(profile)
  driftedProfile["feature_matrix"]["feature_columns"] = list(
    reversed(driftedProfile["feature_matrix"]["feature_columns"])
  )

  with pytest.raises(ValueError, match="feature 순서"):
    build_model_artifact(
      bundle=bundle,
      config=config,
      data_profile=driftedProfile,
      git_commit="abcdef123456",
      data_manifest_sha256="1" * 64,
      created_at_kst="2026-07-11T09:00:00+09:00",
    )


def testSaveModelArtifactWritesCanonicalBytesAndDefaultSidecar(tmp_path):
  _, _, _, _, _, artifact = makeModelContext()
  modelPath = tmp_path / "models" / "baseline.pkl"

  saved = save_model_artifact(artifact, modelPath)

  assert saved.model_path == modelPath
  assert saved.metadata_path == default_metadata_path(modelPath)
  assert saved.model_path.read_bytes() == artifact.model_bytes
  assert saved.metadata_path.read_bytes() == artifact.metadata_bytes


def testRunRegistryLinksValidationModelMetadataAndSubmissionLedger():
  validation = {
    "split_name": "2024_holdout",
    "train_start_kst": "2022-01-01 01:00:00",
    "train_end_kst": "2024-01-01 00:00:00",
    "validation_start_kst": "2024-01-01 01:00:00",
    "validation_end_kst": "2025-01-01 00:00:00",
    "total_score": 0.61,
    "one_minus_nmae": 0.82,
    "ficr": 0.40,
  }
  _, _, _, _, _, artifact = makeModelContext(validation=validation)
  submissionEntry = {
    "submission_filename": "submission_20260711_rf_registry_smoke_abcdef1.csv",
    "submission_sha256": "2" * 64,
    "submission_rows": 8760,
    "public_score": 0.59,
  }

  entry = build_run_registry_entry(
    artifact=artifact,
    model_path="outputs/models/baseline.pkl",
    metadata_path="outputs/models/baseline.pkl.metadata.json",
    submission_entry=submissionEntry,
  )

  assert list(entry) == RUN_REGISTRY_COLUMNS
  assert entry["status"] == "submission_validated"
  assert entry["split_name"] == "2024_holdout"
  assert entry["total_score"] == 0.61
  assert entry["model_sha256"] == artifact.model_sha256
  assert entry["metadata_sha256"] == artifact.metadata_sha256
  assert entry["submission_sha256"] == "2" * 64
  assert entry["submission_rows"] == 8760


def testAppendRunRegistryPreservesSchemaAndRejectsDuplicateRunId(tmp_path):
  _, _, _, _, _, artifact = makeModelContext()
  entry = build_run_registry_entry(
    artifact=artifact,
    model_path="baseline.pkl",
    metadata_path="baseline.pkl.metadata.json",
  )
  registryPath = tmp_path / "run_registry.csv"

  registry = append_run_registry_entry(registryPath, entry)

  assert list(registry.columns) == RUN_REGISTRY_COLUMNS
  assert registryPath.read_bytes().startswith(b"\xef\xbb\xbf")
  with pytest.raises(ValueError, match="run_id 중복"):
    append_run_registry_entry(registryPath, entry)


def testUpdateRunRegistryConnectsValidatedSubmissionHash(tmp_path):
  _, _, _, _, _, artifact = makeModelContext()
  entry = build_run_registry_entry(
    artifact=artifact,
    model_path="baseline.pkl",
    metadata_path="baseline.pkl.metadata.json",
  )
  registryPath = tmp_path / "run_registry.csv"
  append_run_registry_entry(registryPath, entry)

  updated = update_run_registry_submission(
    registryPath,
    run_id=artifact.metadata["run_id"],
    submission_filename="submission.csv",
    submission_sha256="3" * 64,
    submission_rows=8760,
    submission_encoding="utf-8-sig",
  )

  row = updated.iloc[0]
  assert row["status"] == "submission_validated"
  assert row["submission_filename"] == "submission.csv"
  assert row["submission_sha256"] == "3" * 64
  assert row["submission_rows"] == 8760
  assert row["submission_encoding"] == "utf-8-sig"


def testFingerprintFilesUsesExactInputBytes(tmp_path):
  labelPath = tmp_path / "train_labels.csv"
  labelBytes = b"kst_dtm,kpx_group_1\n2024-01-01 01:00:00,1\n"
  labelPath.write_bytes(labelBytes)

  fingerprints = fingerprint_files({"train_labels": labelPath})

  assert fingerprints["train_labels"]["bytes"] == len(labelBytes)
  assert fingerprints["train_labels"]["sha256"] == hashlib.sha256(labelBytes).hexdigest()


def testRegisteredModelLoadAnchorsModelAndMetadataHashes(tmp_path):
  _, _, _, _, _, artifact = makeModelContext()
  modelPath = tmp_path / "baseline.pkl"
  saved = save_model_artifact(artifact, modelPath)
  registryPath = tmp_path / "run_registry.csv"
  append_run_registry_entry(
    registryPath,
    build_run_registry_entry(
      artifact=artifact,
      model_path=saved.model_path,
      metadata_path=saved.metadata_path,
    ),
  )

  loadedBundle, loadedMetadata = load_registered_model_artifact(
    modelPath,
    saved.metadata_path,
    registryPath,
  )
  assert loadedBundle.feature_columns == artifact.metadata["model"]["feature_columns"]
  assert loadedMetadata["run_id"] == artifact.metadata["run_id"]

  saved.metadata_path.write_bytes(artifact.metadata_bytes + b" ")
  with pytest.raises(ValueError, match="metadata SHA256"):
    load_registered_model_artifact(modelPath, saved.metadata_path, registryPath)
