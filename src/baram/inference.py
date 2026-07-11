"""BARAM inference CLI 진입점."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from baram.baseline import build_inference_features
from baram.baseline import build_submission
from baram.baseline import predict_random_forest_baseline
from baram.registry import default_metadata_path
from baram.registry import load_registered_model_artifact
from baram.registry import update_run_registry_submission
from baram.validation import build_validated_submission_artifact


def write_submission_after_validation(submission, sample_submission, output_path, encoding="utf-8-sig"):
  """validator 통과 후 canonical bytes만 저장한다."""
  artifact = build_validated_submission_artifact(
    submission,
    sample_submission,
    encoding=encoding,
  )
  destination = Path(output_path)
  destination.parent.mkdir(parents=True, exist_ok=True)
  destination.write_bytes(artifact.csv_bytes)
  return artifact


def build_parser():
  parser = argparse.ArgumentParser(description="BARAM baseline inference entry point")
  parser.add_argument("--run", action="store_true", help="실제 inference를 실행합니다.")
  parser.add_argument("--model-input", type=Path, help="train CLI가 저장한 model bundle 경로")
  parser.add_argument("--model-metadata", type=Path, help="train CLI가 저장한 model metadata sidecar 경로")
  parser.add_argument("--run-registry", type=Path, help="model run과 submission hash를 연결할 CSV registry")
  parser.add_argument("--sample-submission", type=Path, help="공식 sample_submission.csv 경로")
  parser.add_argument("--ldaps-test", type=Path, help="평가 LDAPS CSV 경로")
  parser.add_argument("--gfs-test", type=Path, help="평가 GFS CSV 경로")
  parser.add_argument("--submission-output", type=Path, help="검증 통과 후 저장할 제출 CSV 경로")
  parser.add_argument(
    "--encoding",
    choices=["utf-8", "utf-8-sig"],
    default="utf-8-sig",
    help="제출 CSV 저장 인코딩",
  )
  return parser


def _require_paths(parser, args):
  required = ["model_input", "run_registry", "sample_submission", "ldaps_test", "gfs_test"]
  missing = [name for name in required if getattr(args, name) is None]
  if missing:
    parser.error(f"--run requires: {', '.join('--' + name.replace('_', '-') for name in missing)}")


def _validate_output_paths(args):
  if args.submission_output is None:
    return
  metadata_path = args.model_metadata or default_metadata_path(args.model_input)
  protected_paths = {
    "model_input": Path(args.model_input).resolve(),
    "model_metadata": Path(metadata_path).resolve(),
    "run_registry": Path(args.run_registry).resolve(),
    "sample_submission": Path(args.sample_submission).resolve(),
    "ldaps_test": Path(args.ldaps_test).resolve(),
    "gfs_test": Path(args.gfs_test).resolve(),
  }
  submission_output = Path(args.submission_output).resolve()
  collisions = [name for name, path in protected_paths.items() if path == submission_output]
  if collisions:
    raise ValueError(f"submission output이 입력/registry 경로와 충돌합니다: {collisions}")


def run_inference(args):
  _validate_output_paths(args)
  bundle, metadata = load_registered_model_artifact(
    args.model_input,
    args.model_metadata,
    args.run_registry,
  )
  sample_submission = pd.read_csv(args.sample_submission, encoding="utf-8-sig")
  ldaps_test = pd.read_csv(args.ldaps_test, encoding="utf-8-sig")
  gfs_test = pd.read_csv(args.gfs_test, encoding="utf-8-sig")

  inference_features = build_inference_features(sample_submission, ldaps_test, gfs_test)
  expected_feature_columns = list(metadata["model"]["feature_columns"])
  if list(inference_features.X.columns) != expected_feature_columns:
    raise ValueError("inference feature 순서가 model metadata와 일치하지 않습니다")
  predictions = predict_random_forest_baseline(bundle, inference_features.X)
  submission = build_submission(sample_submission, predictions)
  artifact = build_validated_submission_artifact(
    submission,
    sample_submission,
    encoding=args.encoding,
  )
  if args.submission_output is not None:
    destination = Path(args.submission_output)
    if destination.exists():
      raise FileExistsError(f"기존 submission을 덮어쓸 수 없습니다: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(artifact.csv_bytes)
    try:
      update_run_registry_submission(
        args.run_registry,
        run_id=metadata["run_id"],
        submission_filename=destination.as_posix(),
        submission_sha256=artifact.sha256,
        submission_rows=artifact.report.row_count,
        submission_encoding=artifact.encoding,
      )
    except Exception:
      destination.unlink(missing_ok=True)
      raise
    print(f"saved_submission={destination}")
  else:
    print("submission_output=not_requested")
  print(f"submission_sha256={artifact.sha256}")
  return artifact


def main(argv=None):
  parser = build_parser()
  args = parser.parse_args(argv)
  if not args.run:
    print("BARAM inference dry-run: no submission CSV or outputs will be created.")
    return 0
  _require_paths(parser, args)
  run_inference(args)
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
