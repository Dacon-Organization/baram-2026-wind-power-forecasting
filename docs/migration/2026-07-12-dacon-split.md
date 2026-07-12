# Dacon 모노레포 분리 증적

## 범위

- 실행일: 2026-07-12 KST
- 원본: `Dacon-Organization/Dacon`
- 원본 기준 `main`: `1463d1fe13173b9c9163898577877d90d7eae023`
- 원본 경로: `2026-BARAM-Wind-Power-Prediction-AI-Competition/`
- 대상: `Dacon-Organization/baram-2026-wind-power-forecasting`
- 대상 Repository ID: `1297889976` / `R_kgDOTVw6uA`

## 필터 방법

사용자 변경이 있는 원본 worktree를 건드리지 않고 새 mirror clone에서만 실행했습니다.

```powershell
git filter-repo `
  --path "2026-BARAM-Wind-Power-Prediction-AI-Competition/" `
  --path-rename "2026-BARAM-Wind-Power-Prediction-AI-Competition/:" `
  --force
```

`git push --mirror`는 사용하지 않았습니다. 검증한 `main`과 BARAM 명칭의 역사적
브랜치 10개만 명시적으로 push했습니다.

## 불변성 검증

| 항목 | 결과 |
| --- | --- |
| 원본 subtree tree SHA | `dbb9767931d166363df04da35e43b1367cdefc89` |
| 필터된 `main` root tree SHA | `dbb9767931d166363df04da35e43b1367cdefc89` |
| tree 일치 | PASS |
| 원본/필터 `main` BARAM 커밋 | 20 / 20 |
| 원본/필터 추적 파일 | 76 / 76 |
| 원본 Git blob 합계 | 3,008,290 bytes |
| LFS 객체 | 0 |
| 서브모듈 | 0 |
| `git fsck --full --strict` | PASS |

20개 canonical main 커밋의 원본·변환 SHA는
[baram-main-commit-map.tsv](baram-main-commit-map.tsv)에 기록했습니다. 저자, 작성일과
커밋 제목은 보존되고 경로 제거 때문에 commit SHA만 변경됩니다.

## 역사적 브랜치

다음 브랜치는 원본 PR이 모두 병합된 상태지만 squash 이전 commit ref 보존을 위해
함께 이관했습니다. 새 개발의 기준은 `main`이며 이 브랜치에서 신규 PR을 만들지
않습니다.

| 브랜치 | 필터된 tip |
| --- | --- |
| `docs/baram-03-notebook-markdown-fix` | `ed174972e1c03f743aa692391a48b74d591e574e` |
| `docs/baram-final-design` | `76067c3fa0f739faf9bdfbf560ec43dd66bc32fc` |
| `docs/baram-llm-wiki` | `8d4582cf92cc252f287587fce7af2e8e165356e5` |
| `docs/baram-official-data-audit` | `50db60ed6821d71a7b491a934cc4bc01bff9d83d` |
| `feature/baram/baseline-notebook` | `dcd08bdc0f68fcc4e856e7160576b830a7a2e78a` |
| `feature/baram/baseline-train-inference` | `e94b5300d75d7cc660763ce4c0ed5512cb6f8e8c` |
| `feature/baram/metric-notebook-detail` | `aaa51d7ad3021e48435f6cf176f378075b9f6bb7` |
| `feature/baram/metric-reproduction` | `b4ac76a7d978183bd54c8dc22e22512e44ee9ca3` |
| `feature/baram/notebook-story-fix` | `475fd0fbba70275e464952e8c02c962c0db58ac7` |
| `feature/baram/submission-validator-cli` | `6ced2327993d020c80f54caf581dc2bd2393570c` |

과거 PR 객체 21개는 GitHub에서 저장소 사이로 이동할 수 없으므로
[원본 Dacon PR 검색](https://github.com/Dacon-Organization/Dacon/pulls?q=is%3Apr+baram)에
보존됩니다.

## 데이터 경계

로컬 공식 원자료 10개 약 324.96MiB는 원본에서도 Git 미추적 상태였습니다.
`ldaps_train.csv`는 약 123.68MiB로 GitHub 일반 파일 한도를 넘고, 대회 목적 외
재배포 권리도 확인되지 않았습니다. 따라서 원자료는 이관하지 않고 README와
SHA-256 manifest만 보존했습니다.

## CI bootstrap

필터된 초기 `main` SHA는 `0669babb64f17f63062f97b1cb9495a66ac07c79`입니다.
dependency graph snapshot이 없는 최초 PR에만 이 SHA를 비교하는 bootstrap 예외를
적용하며, 이후 PR에서는 GitHub dependency review가 반드시 실행됩니다.

## GitHub 운영 검증

- 운영 기반: [PR #1](https://github.com/Dacon-Organization/baram-2026-wind-power-forecasting/pull/1)
- 공통 CI: [run 29175267519](https://github.com/Dacon-Organization/baram-2026-wind-power-forecasting/actions/runs/29175267519) 전체 통과
- 필수 검사: `CI / gate`, `PR Policy / gate`, `Dependency Review / gate` 통과
- CodeQL 초기 설정: run `29175195607` 통과, Python default setup 활성화
- PR CodeQL: run `29175266663` 통과
- `main-pr-ci` ruleset: Active, 승인 필요 인원 0명, strict 필수 검사 3개

원본 Dacon 저장소의 BARAM 폴더와 레거시 workflow 정리는 PR #1 병합 이후 별도
작업으로 수행합니다. 원본의 기존 필수 검사와 새 저장소의 검증 체계를 동시에
끊지 않기 위한 안전 경계입니다.
