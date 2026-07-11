"""BARAM 분석 노트북의 실행 상태와 한글 마크다운 무결성을 검사한다."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"


def _cell_source(cell):
  source = cell.get("source", "")
  return "".join(source) if isinstance(source, list) else str(source)


def inspect_notebook(path):
  notebook = json.loads(path.read_text(encoding="utf-8"))
  cells = notebook.get("cells", [])
  markdown_cells = [cell for cell in cells if cell.get("cell_type") == "markdown"]
  code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
  markdown_text = "\n".join(_cell_source(cell) for cell in markdown_cells)
  cell_types = [cell.get("cell_type") for cell in cells]
  return {
    "notebook": path.name,
    "markdown_cells": len(markdown_cells),
    "code_cells": len(code_cells),
    "missing_execution": sum(cell.get("execution_count") is None for cell in code_cells),
    "error_outputs": sum(
      output.get("output_type") == "error"
      for cell in code_cells
      for output in cell.get("outputs", [])
    ),
    "replacement_chars": markdown_text.count(chr(0xFFFD)),
    "triple_question_runs": len(re.findall(r"\?{3,}", markdown_text)),
    "consecutive_code_pairs": sum(
      left == "code" and right == "code"
      for left, right in zip(cell_types, cell_types[1:])
    ),
  }


def main():
  notebook_paths = sorted(NOTEBOOK_DIR.glob("*.ipynb"))
  if not notebook_paths:
    print("검사할 BARAM 노트북이 없습니다.", file=sys.stderr)
    return 1

  rows = [inspect_notebook(path) for path in notebook_paths]
  fields = [
    "notebook",
    "markdown_cells",
    "code_cells",
    "missing_execution",
    "error_outputs",
    "replacement_chars",
    "triple_question_runs",
    "consecutive_code_pairs",
  ]
  print("\t".join(fields))
  for row in rows:
    print("\t".join(str(row[field]) for field in fields))

  failures = []
  for row in rows:
    for field in [
      "missing_execution",
      "error_outputs",
      "replacement_chars",
      "triple_question_runs",
      "consecutive_code_pairs",
    ]:
      if row[field] != 0:
        failures.append(f"{row['notebook']}: {field}={row[field]}")
  if failures:
    print("노트북 무결성 검사 실패:", file=sys.stderr)
    for failure in failures:
      print(f"- {failure}", file=sys.stderr)
    return 1
  print(f"노트북 무결성 검사 통과: {len(rows)}개")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
