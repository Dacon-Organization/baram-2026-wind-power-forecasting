import json
from pathlib import Path

import pandas as pd
import pytest

from baram.feature_config import DEFAULT_FEATURE_SET, get_feature_set
from baram.inference import main as inferenceMain
from baram.registry import feature_set_from_metadata
from baram.train import main as trainMain
from baram.train import resolve_training_feature_set
from baram.validation import EXPECTED_SUBMISSION_ROWS


GRID_COUNTS = {"ldaps": 16, "gfs": 9}
VECTOR_COLUMNS = {
  "ldaps": ["heightAboveGround_10_10u", "heightAboveGround_10_10v"],
  "gfs": [
    "heightAboveGround_10_10u",
    "heightAboveGround_10_10v",
    "heightAboveGround_80_u",
    "heightAboveGround_80_v",
    "heightAboveGround_100_100u",
    "heightAboveGround_100_100v",
  ],
}
TRAIN_HOURS = 6


def makeWeatherFrame(times, source, offset=0.0):
  rows = []
  for timeIndex, forecastTime in enumerate(pd.to_datetime(times)):
    for gridId in range(1, GRID_COUNTS[source] + 1):
      row = {
        "forecast_kst_dtm": forecastTime,
        "data_available_kst_dtm": forecastTime - pd.Timedelta(hours=13),
        "grid_id": gridId,
        "latitude": 37.26 + gridId * 0.004,
        "longitude": 128.95 + gridId * 0.003,
      }
      for position, column in enumerate(VECTOR_COLUMNS[source]):
        row[column] = float(offset + timeIndex + gridId * 0.5 + position)
      rows.append(row)
  return pd.DataFrame(rows)


def writeTrainInputs(tmp_path):
  times = pd.date_range("2024-01-01 01:00:00", periods=TRAIN_HOURS, freq="h")
  labels = pd.DataFrame(
    {
      "kst_dtm": times,
      "kpx_group_1": [1000.0 + index * 100 for index in range(TRAIN_HOURS)],
      "kpx_group_2": [2000.0 + index * 100 for index in range(TRAIN_HOURS)],
      "kpx_group_3": [None, None, *[3000.0 + index * 100 for index in range(TRAIN_HOURS - 2)]],
    }
  )
  paths = {
    "labels": tmp_path / "train_labels.csv",
    "ldaps": tmp_path / "ldaps_train.csv",
    "gfs": tmp_path / "gfs_train.csv",
    "manifest": tmp_path / "MANIFEST.md",
    "model": tmp_path / "baseline.pkl",
    "registry": tmp_path / "run_registry.csv",
  }
  labels.to_csv(paths["labels"], index=False, encoding="utf-8-sig")
  makeWeatherFrame(times, "ldaps").to_csv(paths["ldaps"], index=False, encoding="utf-8-sig")
  makeWeatherFrame(times, "gfs", offset=10.0).to_csv(paths["gfs"], index=False, encoding="utf-8-sig")
  paths["manifest"].write_text("synthetic manifest", encoding="utf-8")
  return paths


def runTrain(paths, extraArgs=()):
  return trainMain(
    [
      "--run",
      "--train-labels", str(paths["labels"]),
      "--ldaps-train", str(paths["ldaps"]),
      "--gfs-train", str(paths["gfs"]),
      "--model-output", str(paths["model"]),
      "--registry-output", str(paths["registry"]),
      "--data-manifest", str(paths["manifest"]),
      "--git-commit", "abcdef123456",
      "--experiment-id", "cli_feature_set",
      "--n-estimators", "4",
      "--n-jobs", "1",
      *extraArgs,
    ]
  )


def readMetadata(paths):
  metadataPath = paths["model"].with_name(f"{paths['model'].name}.metadata.json")
  return metadataPath, json.loads(metadataPath.read_bytes().decode("utf-8"))


class TestTrainFeatureSetArgument:
  def test_기본값은_official_mean으로_기록된다(self, tmp_path):
    paths = writeTrainInputs(tmp_path)
    assert runTrain(paths) == 0
    _, metadata = readMetadata(paths)
    assert metadata["schema_version"] == "1.1"
    assert metadata["feature_set"]["name"] == DEFAULT_FEATURE_SET
    assert metadata["feature_set"]["source"] == "preset"
    assert metadata["feature_set"]["scope"] is None

  def test_프리셋을_주면_피처_수가_늘고_metadata에_남는다(self, tmp_path):
    officialRoot = tmp_path / "official"
    officialRoot.mkdir()
    officialPaths = writeTrainInputs(officialRoot)
    runTrain(officialPaths)
    _, officialMetadata = readMetadata(officialPaths)

    expandedRoot = tmp_path / "expanded"
    expandedRoot.mkdir()
    expandedPaths = writeTrainInputs(expandedRoot)
    assert runTrain(expandedPaths, ["--feature-set", "expanded_vector"]) == 0
    _, expandedMetadata = readMetadata(expandedPaths)

    assert expandedMetadata["feature_set"]["name"] == "expanded_vector"
    assert expandedMetadata["feature_set"]["feature_count"] > officialMetadata["feature_set"]["feature_count"]
    assert (
      expandedMetadata["preprocessing_sha256"] != officialMetadata["preprocessing_sha256"]
    ), "전처리가 달라졌는데 계약 hash가 같으면 재현성 레이어가 거짓 신호를 낸다"

  def test_metadata의_config로_피처셋을_복원할_수_있다(self, tmp_path):
    paths = writeTrainInputs(tmp_path)
    runTrain(paths, ["--feature-set", "expanded_vector"])
    _, metadata = readMetadata(paths)
    restored = feature_set_from_metadata(metadata)
    assert restored == get_feature_set("expanded_vector")

  def test_YAML_오버라이드도_metadata에_출처를_남긴다(self, tmp_path):
    paths = writeTrainInputs(tmp_path)
    configPath = tmp_path / "no_lead.yaml"
    configPath.write_text(
      "extends: expanded_vector\noverrides:\n  include_lead: false\n",
      encoding="utf-8",
    )
    assert runTrain(paths, ["--feature-set-config", str(configPath)]) == 0
    _, metadata = readMetadata(paths)
    assert metadata["feature_set"]["source"] == "yaml:no_lead.yaml"
    assert metadata["feature_set"]["name"] == "expanded_vector+no_lead"
    assert feature_set_from_metadata(metadata).include_lead is False


class TestGuards:
  def test_공간_프리셋인데_info_xlsx가_없으면_실패한다(self, tmp_path):
    paths = writeTrainInputs(tmp_path)
    with pytest.raises(ValueError, match="--info-xlsx"):
      runTrain(paths, ["--feature-set", "spatial_idw2_all_group"])
    assert not paths["model"].exists()

  def test_프리셋과_YAML을_동시에_주면_실패한다(self, tmp_path):
    paths = writeTrainInputs(tmp_path)
    configPath = tmp_path / "override.yaml"
    configPath.write_text("extends: expanded_vector\n", encoding="utf-8")
    with pytest.raises(ValueError, match="동시에"):
      runTrain(
        paths,
        ["--feature-set", "expanded_vector", "--feature-set-config", str(configPath)],
      )

  def test_알_수_없는_프리셋은_argparse가_거른다(self, tmp_path):
    paths = writeTrainInputs(tmp_path)
    with pytest.raises(SystemExit):
      runTrain(paths, ["--feature-set", "no_such_preset"])

  def test_schema_1_0_sidecar는_official_mean으로_본다(self):
    assert feature_set_from_metadata({"schema_version": "1.0"}) == get_feature_set(
      DEFAULT_FEATURE_SET
    )
    assert feature_set_from_metadata(None) == get_feature_set(DEFAULT_FEATURE_SET)

  def test_resolve는_공간_프리셋에_터빈_좌표를_요구한다(self, tmp_path):
    class Args:
      feature_set = "spatial_nearest_own_group"
      feature_set_config = None
      info_xlsx = None

    with pytest.raises(ValueError, match="--info-xlsx"):
      resolve_training_feature_set(Args())


class TestInferenceRestoresFeatureSet:
  def test_피처셋을_metadata에서_복원해_제출물을_만든다(self, tmp_path):
    paths = writeTrainInputs(tmp_path)
    runTrain(paths, ["--feature-set", "expanded_vector"])
    metadataPath, _ = readMetadata(paths)

    # validator가 공식 8,760행을 요구하므로 test 시간축은 축소하지 않는다.
    testTimes = pd.date_range("2025-01-01 01:00:00", periods=EXPECTED_SUBMISSION_ROWS, freq="h")
    sample = pd.DataFrame(
      {
        "forecast_id": [
          f"forecast_{index:04d}" for index in range(1, EXPECTED_SUBMISSION_ROWS + 1)
        ],
        "forecast_kst_dtm": testTimes.strftime("%Y-%m-%d %H:%M:%S"),
        "kpx_group_1": 0.0,
        "kpx_group_2": 0.0,
        "kpx_group_3": 0.0,
      }
    )
    samplePath = tmp_path / "sample_submission.csv"
    ldapsTestPath = tmp_path / "ldaps_test.csv"
    gfsTestPath = tmp_path / "gfs_test.csv"
    sample.to_csv(samplePath, index=False, encoding="utf-8-sig")
    makeWeatherFrame(testTimes, "ldaps").to_csv(ldapsTestPath, index=False, encoding="utf-8-sig")
    makeWeatherFrame(testTimes, "gfs", offset=10.0).to_csv(
      gfsTestPath, index=False, encoding="utf-8-sig"
    )

    status = inferenceMain(
      [
        "--run",
        "--model-input", str(paths["model"]),
        "--model-metadata", str(metadataPath),
        "--run-registry", str(paths["registry"]),
        "--sample-submission", str(samplePath),
        "--ldaps-test", str(ldapsTestPath),
        "--gfs-test", str(gfsTestPath),
      ]
    )
    assert status == 0

  def test_test_피처셋이_train과_다르면_실패한다(self, tmp_path):
    paths = writeTrainInputs(tmp_path)
    runTrain(paths, ["--feature-set", "expanded_vector"])
    metadataPath, metadata = readMetadata(paths)
    # metadata의 피처셋만 official_mean으로 바꿔치기하면 컬럼 수가 어긋난다.
    metadata["feature_set"]["config"]["statistics"] = ["mean"]
    metadata["feature_set"]["config"]["wind_vector"] = False
    Path(metadataPath).write_bytes(
      json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")
    )
    assert feature_set_from_metadata(metadata).statistics == ("mean",)
