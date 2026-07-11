"""BARAM train CLI 진입점."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

if __package__ in {None, ""}:
  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from baram.baseline import build_training_features
from baram.baseline import train_random_forest_baseline
from baram.registry import (
  append_run_registry_entry,
  build_model_artifact,
  build_run_registry_entry,
  build_training_data_profile,
  default_metadata_path,
  fingerprint_files,
  save_model_artifact,
)
from baram.reproducibility import BaselineRunConfig


def build_parser():
  parser = argparse.ArgumentParser(description="BARAM baseline train entry point")
  parser.add_argument("--run", action="store_true", help="실제 학습을 실행합니다.")
  parser.add_argument("--train-labels", type=Path, help="train_labels.csv 경로")
  parser.add_argument("--ldaps-train", type=Path, help="학습 LDAPS CSV 경로")
  parser.add_argument("--gfs-train", type=Path, help="학습 GFS CSV 경로")
  parser.add_argument("--model-output", type=Path, help="명시적으로 저장할 model bundle 경로")
  parser.add_argument("--metadata-output", type=Path, help="model metadata JSON sidecar 경로")
  parser.add_argument("--registry-output", type=Path, help="model run을 누적할 CSV registry 경로")
  parser.add_argument("--data-manifest", type=Path, help="공식 데이터 MANIFEST.md 경로")
  parser.add_argument("--git-commit", help="코드 버전 commit SHA. 생략 시 현재 Git HEAD를 사용합니다.")
  parser.add_argument("--experiment-id", default="baseline_rf", help="run registry 실험 식별자")
  parser.add_argument("--created-at-kst", help="재현용 KST 실행 시각. 기본값은 현재 시각입니다.")
  parser.add_argument("--seed", type=int, default=42, help="RandomForest random_state")
  parser.add_argument("--n-estimators", type=int, default=120, help="RandomForest tree 개수")
  parser.add_argument("--n-jobs", type=int, default=-1, help="RandomForest n_jobs")
  parser.add_argument("--split-name", help="local validation split 이름")
  parser.add_argument("--train-start-kst", help="local validation 학습 시작 시각")
  parser.add_argument("--train-end-kst", help="local validation 학습 종료 시각")
  parser.add_argument("--validation-start-kst", help="local validation 시작 시각")
  parser.add_argument("--validation-end-kst", help="local validation 종료 시각")
  parser.add_argument("--total-score", type=float, help="local total score")
  parser.add_argument("--one-minus-nmae", type=float, help="local 1-NMAE")
  parser.add_argument("--ficr", type=float, help="local FICR")
  return parser


def _require_paths(parser, args):
  required = [
    "train_labels",
    "ldaps_train",
    "gfs_train",
    "model_output",
    "registry_output",
    "data_manifest",
  ]
  missing = [name for name in required if getattr(args, name) is None]
  if missing:
    parser.error(f"--run requires: {', '.join('--' + name.replace('_', '-') for name in missing)}")


def _resolve_git_commit(explicit_commit):
  if explicit_commit is not None and explicit_commit.strip():
    return explicit_commit.strip()
  project_root = Path(__file__).resolve().parents[2]
  completed = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=project_root,
    text=True,
    capture_output=True,
    check=False,
  )
  if completed.returncode != 0 or not completed.stdout.strip():
    raise ValueError("현재 Git commit을 확인할 수 없습니다. --git-commit을 지정하세요")
  return completed.stdout.strip()


def _validate_output_paths(args):
  metadata_output = args.metadata_output or default_metadata_path(args.model_output)
  destinations = {
    "model_output": Path(args.model_output).resolve(),
    "metadata_output": Path(metadata_output).resolve(),
    "registry_output": Path(args.registry_output).resolve(),
  }
  if len(set(destinations.values())) != len(destinations):
    raise ValueError(f"train artifact 경로는 서로 달라야 합니다: {destinations}")
  return metadata_output


def _build_validation_record(args):
  score_values = [args.total_score, args.one_minus_nmae, args.ficr]
  if any(value is not None for value in score_values) and not all(value is not None for value in score_values):
    raise ValueError("local score는 --total-score, --one-minus-nmae, --ficr를 모두 지정해야 합니다")
  fields = {
    "split_name": args.split_name,
    "train_start_kst": args.train_start_kst,
    "train_end_kst": args.train_end_kst,
    "validation_start_kst": args.validation_start_kst,
    "validation_end_kst": args.validation_end_kst,
    "total_score": args.total_score,
    "one_minus_nmae": args.one_minus_nmae,
    "ficr": args.ficr,
  }
  record = {key: value for key, value in fields.items() if value is not None}
  return record or None


def run_train(args):
  metadata_output = _validate_output_paths(args)
  train_labels = pd.read_csv(args.train_labels, encoding="utf-8-sig")
  ldaps_train = pd.read_csv(args.ldaps_train, encoding="utf-8-sig")
  gfs_train = pd.read_csv(args.gfs_train, encoding="utf-8-sig")
  train_features = build_training_features(train_labels, ldaps_train, gfs_train)
  config = BaselineRunConfig(
    experiment_id=args.experiment_id,
    seed=args.seed,
    model_params={
      "n_estimators": args.n_estimators,
      "n_jobs": args.n_jobs,
    },
  )
  bundle = train_random_forest_baseline(
    train_features.X,
    train_features.frame,
    model_params=config.effective_model_params(),
  )
  data_profile = build_training_data_profile(
    train_labels=train_labels,
    ldaps_train=ldaps_train,
    gfs_train=gfs_train,
    train_features=train_features,
  )
  input_files = fingerprint_files(
    {
      "train_labels": args.train_labels,
      "ldaps_train": args.ldaps_train,
      "gfs_train": args.gfs_train,
    }
  )
  data_manifest_sha256 = hashlib.sha256(Path(args.data_manifest).read_bytes()).hexdigest()
  artifact = build_model_artifact(
    bundle=bundle,
    config=config,
    data_profile=data_profile,
    git_commit=_resolve_git_commit(args.git_commit),
    data_manifest_sha256=data_manifest_sha256,
    input_files=input_files,
    created_at_kst=args.created_at_kst,
    validation=_build_validation_record(args),
  )
  saved = save_model_artifact(
    artifact,
    args.model_output,
    metadata_path=metadata_output,
  )
  entry = build_run_registry_entry(
    artifact=artifact,
    model_path=saved.model_path,
    metadata_path=saved.metadata_path,
  )
  try:
    append_run_registry_entry(args.registry_output, entry)
  except Exception:
    saved.model_path.unlink(missing_ok=True)
    saved.metadata_path.unlink(missing_ok=True)
    raise

  print(f"saved_model={saved.model_path}")
  print(f"saved_metadata={saved.metadata_path}")
  print(f"run_registry={args.registry_output}")
  print(f"run_id={artifact.metadata['run_id']}")
  return artifact


def main(argv=None):
  parser = build_parser()
  args = parser.parse_args(argv)
  if not args.run:
    print("BARAM train dry-run: no model file or outputs will be created.")
    return 0
  _require_paths(parser, args)
  run_train(args)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
