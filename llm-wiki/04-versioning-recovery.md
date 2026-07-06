# 버전 관리와 제출 복구 규칙

## 기본 원칙

제출 실패나 최종 선택 오류가 발생해도 같은 파일을 다시 만들 수 있어야 합니다. 이를 위해 제출 파일은 데이터 버전, 코드 commit, config, seed, 모델 파일, 후처리 버전을 함께 묶어 관리합니다.

## 추적해야 할 단위

| 항목 | 기록 위치 | 예시 |
|------|-----------|------|
| 원본 데이터 버전 | `data/raw/open/MANIFEST.md` | 파일 SHA256 |
| 공식 코드 버전 | `references/official/README.md` | baseline/metric notebook SHA256 |
| 코드 버전 | Git commit | `git rev-parse HEAD` |
| 실험 설정 | `outputs/experiments/<experiment_id>/config.yaml` | model, features, seed |
| 모델 파일 | `outputs/models/<experiment_id>/` | fold별 model pickle |
| 제출 파일 | `outputs/submissions/` | CSV + SHA256 |
| 제출 로그 | `outputs/submissions/submission_ledger.csv` | 제출 ID, Public score, 선택 상태 |

## 제출 파일명 규칙

```text
submission_<YYYYMMDD>_<experiment_id>_<git_short_sha>.csv
```

예:

```text
submission_20260708_lgbm_p0_f0f4_e1937cf.csv
```

## 제출 전 체크리스트

- `forecast_id`와 `forecast_kst_dtm`이 sample submission과 완전히 일치한다.
- row count가 8,760이다.
- target 컬럼은 `kpx_group_1`, `kpx_group_2`, `kpx_group_3` 순서다.
- encoding은 UTF-8 또는 `utf-8-sig`로 저장한다.
- 예측값은 음수가 아니며 그룹별 capacity를 크게 벗어나지 않는다.
- 제출 파일 SHA256을 기록했다.
- 생성 commit과 config를 기록했다.
- Dacon 제출 후 제출 ID와 Public score, 최종 선택 상태를 기록했다.

## 복구 절차

1. `submission_ledger.csv`에서 복구할 제출 행을 찾습니다.
2. 해당 행의 commit으로 체크아웃하거나 새 worktree를 만듭니다.
3. `data/raw/open/MANIFEST.md`와 로컬 데이터 hash를 대조합니다.
4. 기록된 config와 seed로 inference를 다시 실행합니다.
5. 새 CSV의 SHA256이 기존 제출 파일과 일치하는지 확인합니다.
6. 불일치하면 환경 버전, 모델 파일, 후처리 버전, 데이터 hash 순서로 원인을 좁힙니다.

## Git 운영

- `main`에 직접 커밋하지 않습니다.
- 작업별 브랜치를 만들고 PR을 올립니다.
- 대용량 원본 데이터, 모델, 제출 CSV는 Git에 올리지 않습니다.
- 문서, manifest, config template, 재현 스크립트는 Git에 올립니다.
- PR 본문에는 변경 사항, 변경 이유, 검증 방법을 남깁니다.
