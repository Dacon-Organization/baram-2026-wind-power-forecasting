"""노트북을 셀 단위로 실행하며 진행 상황을 즉시 출력하고 매 셀마다 저장한다.

`nbconvert --execute`는 두 가지가 불편하다.

1. 진행률을 볼 수 없다. 노트북의 print는 stdout이 아니라 셀 출력으로 들어가고,
   `--inplace`는 실행이 끝날 때 한 번에 쓴다. 30분짜리 실행이 살아 있는지
   죽었는지 알 방법이 로그에 없다.
2. 중간에 실패하면 그때까지의 출력도 남지 않는다. 늦은 셀에서 터지면
   앞의 비싼 셀을 전부 다시 돌려야 한다.

이 러너는 매 셀이 끝날 때마다 경과 시간을 찍고 노트북을 저장해 두 문제를 없앤다.

사용법:
  python scripts/run_notebook_live.py notebooks/15_gbm_lab.ipynb -o out.ipynb
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError


def formatDuration(seconds):
  if seconds < 60:
    return f"{seconds:5.1f}s"
  return f"{int(seconds // 60):3d}m{int(seconds % 60):02d}s"


def cellHasError(cell):
  return any(output.get("output_type") == "error" for output in cell.get("outputs", []))


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("notebook", type=Path, help="실행할 .ipynb 경로")
  parser.add_argument("-o", "--output", type=Path, help="출력 경로 (생략 시 제자리 실행)")
  parser.add_argument("--timeout", type=int, default=-1, help="셀당 제한 시간 초 (-1은 무제한)")
  arguments = parser.parse_args()

  notebookPath = arguments.notebook.resolve()
  outputPath = (arguments.output or arguments.notebook).resolve()
  notebook = nbformat.read(notebookPath, as_version=4)

  # 커널의 작업 경로를 노트북 위치로 둔다. 노트북의 경로 해석이 cwd에서 거슬러 올라간다.
  client = NotebookClient(
    notebook,
    timeout=arguments.timeout,
    kernel_name="python3",
    resources={"metadata": {"path": str(notebookPath.parent)}},
    allow_errors=True,
  )

  codeIndices = [i for i, cell in enumerate(notebook.cells) if cell.cell_type == "code"]
  print(f"노트북 : {notebookPath.name}")
  print(f"출력   : {outputPath}")
  print(f"code 셀: {len(codeIndices)}개 / 전체 {len(notebook.cells)}개")
  print("-" * 62, flush=True)

  startedAll = time.perf_counter()
  failedIndex = None

  with client.setup_kernel():
    for order, index in enumerate(codeIndices, start=1):
      cell = notebook.cells[index]
      startedCell = time.perf_counter()
      try:
        client.execute_cell(cell, index)
      except CellExecutionError:
        # allow_errors=True 라 보통 여기 오지 않지만, 커널이 죽으면 올라온다.
        pass
      elapsed = time.perf_counter() - startedCell

      # 매 셀마다 저장한다 — 늦은 셀에서 터져도 앞의 결과가 남는다.
      nbformat.write(notebook, outputPath)

      failed = cellHasError(cell)
      marker = "실패" if failed else "  OK"
      firstLine = cell.source.strip().splitlines()[0][:38] if cell.source.strip() else ""
      print(
        f"[{order:2d}/{len(codeIndices)}] 셀 {index:2d}  {marker}  "
        f"{formatDuration(elapsed)}  누적 {formatDuration(time.perf_counter() - startedAll)}"
        f"   {firstLine}",
        flush=True,
      )

      if failed:
        failedIndex = index
        for output in cell.outputs:
          if output.get("output_type") == "error":
            print("-" * 62, flush=True)
            print("\n".join(output.get("traceback", []))[:3000], flush=True)
        break

  print("-" * 62)
  print(f"총 경과: {formatDuration(time.perf_counter() - startedAll)}")
  if failedIndex is not None:
    print(f"셀 {failedIndex}에서 실패했습니다. 여기까지의 출력은 {outputPath}에 저장돼 있습니다.")
    return 1
  print(f"전체 {len(codeIndices)}개 셀 실행 완료 → {outputPath}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
