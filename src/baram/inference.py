"""BARAM inference CLI 진입점."""

from __future__ import annotations

import argparse
from pathlib import Path
import pickle
import sys

if __package__ in {None, ""}:
  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from baram.baseline import build_inference_features
from baram.baseline import build_submission
from baram.baseline import predict_random_forest_baseline
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
  required = ["model_input", "sample_submission", "ldaps_test", "gfs_test"]
  missing = [name for name in required if getattr(args, name) is None]
  if missing:
    parser.error(f"--run requires: {', '.join('--' + name.replace('_', '-') for name in missing)}")


def run_inference(args):
  sample_submission = pd.read_csv(args.sample_submission)
  ldaps_test = pd.read_csv(args.ldaps_test)
  gfs_test = pd.read_csv(args.gfs_test)
  with args.model_input.open("rb") as model_file:
    bundle = pickle.load(model_file)

  inference_features = build_inference_features(sample_submission, ldaps_test, gfs_test)
  predictions = predict_random_forest_baseline(bundle, inference_features.X)
  submission = build_submission(sample_submission, predictions)
  artifact = build_validated_submission_artifact(
    submission,
    sample_submission,
    encoding=args.encoding,
  )
  if args.submission_output is not None:
    destination = Path(args.submission_output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(artifact.csv_bytes)
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
