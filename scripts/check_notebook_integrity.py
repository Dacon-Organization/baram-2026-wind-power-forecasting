"""BARAM 분석 노트북의 실행 상태와 한글 마크다운 무결성을 검사한다.

실행 출력이 남아 있는지 보는 것이 이 검사의 핵심이다(설계서 06 7절 자가 점검).
다만 학습이 무거운 랩 노트북은 코드를 완성한 시점과 실행이 끝나는 시점이 다르므로,
`notebooks/pending_execution.txt`에 **명시적으로 등록한 노트북만** 실행 출력 검사를
면제한다. 게이트를 없애는 것이 아니라 면제 대상을 코드 리뷰에 드러내는 것이다.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"
PENDING_FILE = NOTEBOOK_DIR / "pending_execution.txt"

# 실행 전에도 의미가 있는 검사. 실행 대기 노트북에도 그대로 적용한다.
ALWAYS_CHECKED = [
  "error_outputs",
  "replacement_chars",
  "triple_question_runs",
  "consecutive_code_pairs",
]


def load_pending():
  """실행 대기 등록부를 읽어 {파일명: 이유}로 돌려준다."""
  if not PENDING_FILE.is_file():
    return {}
  pending = {}
  for raw_line in PENDING_FILE.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#"):
      continue
    name, _, reason = line.partition("#")
    pending[name.strip()] = reason.strip()
  return pending


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

  pending = load_pending()
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
  print("\t".join(fields + ["상태"]))
  for row in rows:
    state = "실행 대기" if row["notebook"] in pending else "실행됨"
    print("\t".join([str(row[field]) for field in fields] + [state]))

  failures = []
  for row in rows:
    checked = list(ALWAYS_CHECKED)
    if row["notebook"] in pending:
      # 등록부는 양방향 계약이다. 실행이 끝났는데 줄이 남아 있으면 목록이 낡은 것이다.
      if row["missing_execution"] == 0:
        failures.append(
          f"{row['notebook']}: 실행이 끝났는데 pending_execution.txt에 등록된 채로 남아 있다"
          " — 해당 줄을 지우세요"
        )
    else:
      checked.append("missing_execution")
    for field in checked:
      if row[field] != 0:
        failures.append(f"{row['notebook']}: {field}={row[field]}")

  known = {row["notebook"] for row in rows}
  for name in pending:
    if name not in known:
      failures.append(f"pending_execution.txt: 없는 노트북이 등록돼 있다 — {name}")

  if failures:
    print("노트북 무결성 검사 실패:", file=sys.stderr)
    for failure in failures:
      print(f"- {failure}", file=sys.stderr)
    return 1

  waiting = [row["notebook"] for row in rows if row["notebook"] in pending]
  print(f"노트북 무결성 검사 통과: {len(rows)}개", end="")
  if waiting:
    print(f" (실행 대기 {len(waiting)}개 — {', '.join(waiting)})")
    for name in waiting:
      print(f"  실행 대기 사유  {name}: {pending[name]}")
  else:
    print()
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
