"""BARAM train CLI 진입점."""

from __future__ import annotations

import argparse
from pathlib import Path
import pickle
import sys

if __package__ in {None, ""}:
  sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from baram.baseline import build_training_features
from baram.baseline import train_random_forest_baseline


def build_parser():
  parser = argparse.ArgumentParser(description="BARAM baseline train entry point")
  parser.add_argument("--run", action="store_true", help="실제 학습을 실행합니다.")
  parser.add_argument("--train-labels", type=Path, help="train_labels.csv 경로")
  parser.add_argument("--ldaps-train", type=Path, help="학습 LDAPS CSV 경로")
  parser.add_argument("--gfs-train", type=Path, help="학습 GFS CSV 경로")
  parser.add_argument("--model-output", type=Path, help="명시적으로 저장할 model bundle 경로")
  parser.add_argument("--seed", type=int, default=42, help="RandomForest random_state")
  parser.add_argument("--n-estimators", type=int, default=120, help="RandomForest tree 개수")
  parser.add_argument("--n-jobs", type=int, default=-1, help="RandomForest n_jobs")
  return parser


def _require_paths(parser, args):
  required = ["train_labels", "ldaps_train", "gfs_train", "model_output"]
  missing = [name for name in required if getattr(args, name) is None]
  if missing:
    parser.error(f"--run requires: {', '.join('--' + name.replace('_', '-') for name in missing)}")


def run_train(args):
  train_labels = pd.read_csv(args.train_labels)
  ldaps_train = pd.read_csv(args.ldaps_train)
  gfs_train = pd.read_csv(args.gfs_train)
  train_features = build_training_features(train_labels, ldaps_train, gfs_train)
  bundle = train_random_forest_baseline(
    train_features.X,
    train_features.frame,
    model_params={
      "random_state": args.seed,
      "n_estimators": args.n_estimators,
      "n_jobs": args.n_jobs,
    },
  )

  destination = Path(args.model_output)
  destination.parent.mkdir(parents=True, exist_ok=True)
  with destination.open("wb") as model_file:
    pickle.dump(bundle, model_file)
  print(f"saved_model={destination}")
  return bundle


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
