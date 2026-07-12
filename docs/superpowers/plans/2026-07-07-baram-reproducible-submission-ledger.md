# BARAM Reproducible Submission Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** baseline train/inference 결과에 config, seed, submission hash, ledger row, 재현성 검증 결과를 연결한다.

**Architecture:** 기존 `src/baram/baseline.py`는 feature/train/predict/submission 책임을 유지한다. 새 `src/baram/reproducibility.py`가 config 정규화, seed 고정, submission CSV SHA256, ledger row 생성, baseline inference 반복 실행 검증을 담당한다.

**Tech Stack:** Python, pandas, numpy, scikit-learn, pytest.

---

### Task 1: Config/Seed/Submission Ledger와 Inference 재현성 검증 연결

**Files:**
- Create: `src/baram/reproducibility.py`
- Create: `tests/test_reproducibility.py`
- Create: `notebooks/03_reproducible_submission_ledger.ipynb`
- Modify: `src/baram/__init__.py`
- Modify: `dev/dashboard/index.html`
- Create: `dev/dashboard/log/2026-07-07-baram-reproducible-submission-ledger.html`

- [ ] **Step 1: Write failing tests**

Add `tests/test_reproducibility.py` with synthetic data helpers equivalent to the baseline tests, then add tests for:

```python
def testBaselineRunConfigInjectsSeedAndStableConfigHash():
  config = BaselineRunConfig(
    experiment_id="rf_smoke",
    seed=777,
    model_params={"n_estimators": 4, "n_jobs": 1},
  )

  assert config.effective_model_params()["random_state"] == 777
  assert config.effective_model_params()["n_jobs"] == 1
  assert config.config_sha256() == BaselineRunConfig(
    experiment_id="rf_smoke",
    seed=777,
    model_params={"n_jobs": 1, "n_estimators": 4},
  ).config_sha256()
  assert config.config_sha256() != BaselineRunConfig(
    experiment_id="rf_smoke",
    seed=778,
    model_params={"n_estimators": 4, "n_jobs": 1},
  ).config_sha256()
```

```python
def testRunBaselineWithReproducibilityReturnsLedgerEntryWithoutWritingFiles(tmp_path, monkeypatch):
  monkeypatch.chdir(tmp_path)
  result = run_baseline_with_reproducibility(
    config=BaselineRunConfig(
      experiment_id="rf_smoke",
      seed=7,
      model_params={"n_estimators": 4, "n_jobs": 1},
    ),
    train_labels=makeLabelFrame(),
    ldaps_train=makeWeatherFrame(pd.date_range("2024-01-01 01:00:00", periods=5, freq="h"), [1, 2, 3, 4, 5]),
    gfs_train=makeWeatherFrame(pd.date_range("2024-01-01 01:00:00", periods=5, freq="h"), [10, 20, 30, 40, 50]),
    sample_submission=makeSampleSubmission(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h")),
    ldaps_test=makeWeatherFrame(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"), [6, 7]),
    gfs_test=makeWeatherFrame(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"), [60, 70]),
    git_commit="abc1234",
    data_manifest_sha256="manifest-sha",
    created_at_kst="2026-07-07T09:00:00+09:00",
  )

  ledger = result["ledger_entry"]
  assert ledger["experiment_id"] == "rf_smoke"
  assert ledger["seed"] == 7
  assert ledger["git_commit"] == "abc1234"
  assert ledger["data_manifest_sha256"] == "manifest-sha"
  assert ledger["submission_rows"] == 2
  assert ledger["submission_sha256"] == submission_csv_sha256(result["baseline_result"]["submission"])
  assert list(tmp_path.iterdir()) == []
```

```python
def testVerifyBaselineInferenceReproducibilityRunsTwiceWithSameSubmissionHash():
  report = verify_baseline_inference_reproducibility(
    config=BaselineRunConfig(
      experiment_id="rf_smoke",
      seed=7,
      model_params={"n_estimators": 4, "n_jobs": 1},
    ),
    train_labels=makeLabelFrame(),
    ldaps_train=makeWeatherFrame(pd.date_range("2024-01-01 01:00:00", periods=5, freq="h"), [1, 2, 3, 4, 5]),
    gfs_train=makeWeatherFrame(pd.date_range("2024-01-01 01:00:00", periods=5, freq="h"), [10, 20, 30, 40, 50]),
    sample_submission=makeSampleSubmission(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h")),
    ldaps_test=makeWeatherFrame(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"), [6, 7]),
    gfs_test=makeWeatherFrame(pd.date_range("2025-01-01 01:00:00", periods=2, freq="h"), [60, 70]),
    git_commit="abc1234",
    data_manifest_sha256="manifest-sha",
    repeats=2,
    created_at_kst="2026-07-07T09:00:00+09:00",
  )

  assert report["is_reproducible"] is True
  assert report["repeats"] == 2
  assert len({run["submission_sha256"] for run in report["runs"]}) == 1
  assert report["ledger_entry"]["submission_sha256"] == report["runs"][0]["submission_sha256"]
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
pytest tests/test_reproducibility.py -q
```

Expected: import failure for `baram.reproducibility` or missing exported functions.

- [ ] **Step 3: Implement `src/baram/reproducibility.py`**

Implement these public objects:

```python
@dataclass(frozen=True)
class BaselineRunConfig:
  experiment_id: str
  seed: int = 42
  model_params: Mapping[str, Any] | None = None
  notes: str = ""

  def effective_model_params(self) -> dict:
    params = dict(self.model_params or {})
    params["random_state"] = self.seed
    return params

  def as_record(self) -> dict:
    return {
      "experiment_id": self.experiment_id,
      "seed": self.seed,
      "model_params": self.effective_model_params(),
      "notes": self.notes,
    }

  def config_sha256(self) -> str:
    return sha256_text(stable_json_dumps(self.as_record()))
```

Implement helpers:

```python
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
```

```python
def seed_everything(seed):
  random.seed(seed)
  np.random.seed(seed)

def stable_json_dumps(value):
  return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def sha256_text(value):
  return hashlib.sha256(value.encode("utf-8")).hexdigest()

def submission_csv_sha256(submission, encoding="utf-8-sig"):
  csv_text = submission.to_csv(index=False, date_format="%Y-%m-%d %H:%M:%S", lineterminator="\n")
  return hashlib.sha256(csv_text.encode(encoding)).hexdigest()
```

Implement orchestration:

```python
def build_submission_filename(experiment_id, git_commit, created_at_kst):
  date_part = created_at_kst[:10].replace("-", "")
  short_sha = git_commit[:7] if git_commit else "unknown"
  return f"submission_{date_part}_{experiment_id}_{short_sha}.csv"

def build_submission_ledger_entry(...):
  return dict with exactly SUBMISSION_LEDGER_COLUMNS

def ledger_entry_to_frame(entry):
  return pd.DataFrame([entry], columns=SUBMISSION_LEDGER_COLUMNS)

def run_baseline_with_reproducibility(...):
  seed_everything(config.seed)
  baseline_result = run_train_inference(..., model_params=config.effective_model_params())
  ledger_entry = build_submission_ledger_entry(...)
  return {"baseline_result": baseline_result, "ledger_entry": ledger_entry}

def verify_baseline_inference_reproducibility(...):
  runs = []
  for repeat_index in range(repeats):
    result = run_baseline_with_reproducibility(...)
    runs.append({
      "run_index": repeat_index + 1,
      "submission_sha256": result["ledger_entry"]["submission_sha256"],
      "config_sha256": result["ledger_entry"]["config_sha256"],
    })
  return {
    "is_reproducible": all(run["submission_sha256"] == runs[0]["submission_sha256"] for run in runs),
    "repeats": repeats,
    "runs": runs,
    "ledger_entry": result["ledger_entry"],
  }
```

The functions must not write files by default.

- [ ] **Step 4: Export module symbols**

Update `src/baram/__init__.py` to keep package docstring and optionally import nothing else. Tests should import from `baram.reproducibility`, so avoid broad package side effects.

- [ ] **Step 5: Run focused and full tests**

Run:

```bash
pytest tests/test_reproducibility.py -q
pytest -q
```

Expected: all tests pass.

- [ ] **Step 6: Update dashboard**

Create `dev/dashboard/log/2026-07-07-baram-reproducible-submission-ledger.html` with 완료/검증/다음 sections. Update `dev/dashboard/index.html` so the previous NEXT item becomes DONE and the new log card appears above the baseline train/inference card.

- [ ] **Step 7: Create the interpretation notebook**

Create and execute `notebooks/03_reproducible_submission_ledger.ipynb` with:

- Markdown sections for analysis question, executive summary, reproducibility contract, Decision Box, interpretation, and next action.
- Code cells that use synthetic weather/label/sample data to demonstrate config hash, filename safety, canonical submission bytes, ledger entry, and repeated inference SHA256 equality.
- A verification cell that runs `pytest tests/test_reproducibility.py -q` and `pytest -q`.
- No actual submission CSV, model file, or `outputs/` artifact writes.

- [ ] **Step 8: Commit**

Commit only this task's files:

```bash
git add src/baram/reproducibility.py \
  tests/test_reproducibility.py \
  notebooks/03_reproducible_submission_ledger.ipynb \
  docs/superpowers/plans/2026-07-07-baram-reproducible-submission-ledger.md \
  dev/dashboard/index.html \
  dev/dashboard/log/2026-07-07-baram-reproducible-submission-ledger.html
git commit -m "feat(baram): add reproducible submission ledger"
```
