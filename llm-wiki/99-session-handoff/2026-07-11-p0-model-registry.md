# 다음 세션 핸드오프: Weather Feature Lab

아래 프롬프트를 다음 Codex 세션 첫 메시지로 그대로 사용한다.

```text
작업 저장소:
Dacon-Organization/baram-2026-wind-power-forecasting

우리는 DACON "제3회 풍력발전량 예측 AI 경진대회 - BARAM 2026" 프로젝트를 진행 중이다.
직전 세션은 P0 model metadata sidecar와 run registry 작업을 완료했다. 이 작업을 다시 만들거나 범위를 섞지 말고, 먼저 PR과 main 반영 상태를 확인한 뒤 다음 한 작업만 진행한다.

반드시 먼저 확인할 운영 상태:
1. AGENTS.md를 읽고 R1 Git 플로우, R2 dashboard, R3 1작업-1정지를 따른다.
2. `git status --short --branch`, `git fetch origin --prune`, 현재 P0 PR 상태와 BARAM CI 상태를 확인한다.
3. P0 PR이 아직 merge 전이면 새 구현을 시작하지 말고 상태·review·check를 먼저 판단한다.
4. P0 PR이 merge됐다면 최신 main을 pull하고 `feature/mygithub05253-weather-feature-lab` 브랜치를 만든다.
5. 저장소 밖 사용자 작업 폴더와 로컬 자동화 상태는 건드리지 않는다.

직전 세션 완료 내용:
- `src/baram/registry.py`: 입력 파일 SHA256, label/weather/feature profile, preprocessing/data/schema hash, model bytes와 JSON sidecar, CSV run registry 구현.
- `src/baram/train.py`: 명시 실행 시 model+sidecar+registry를 함께 생성. 기본 실행은 dry-run.
- `src/baram/inference.py`: registry에 등록된 model/sidecar hash와 feature 순서를 검증한 뒤 inference. validator 통과 canonical submission hash만 run registry에 연결.
- `notebooks/05_model_metadata_and_run_registry.ipynb`: 실제 공식 train 데이터 read-only 분석, 5단계 방법론, 2024 holdout smoke, Decision Box, 실패 사례, 실행 결과 저장.
- `scripts/check_notebook_integrity.py`: 00~05 실행 상태, error output, UTF-8 replacement, 연속 물음표 치환, 연속 code cell 검사.
- `.github/workflows/ci.yml`: 공통 reusable workflow 기반 pytest와 노트북 무결성 CI.
- 마지막 로컬 검증 기준: `python -m pytest -q` 47 passed, 노트북 6개 무결성 통과, 실제 model/submission/outputs 미생성.

먼저 읽을 파일:
1. AGENTS.md
2. docs/design/04-final-solution-blueprint.md
3. data/raw/open/data_description.md
4. notebooks/00_official_data_audit.ipynb
5. notebooks/01_metric_reproduction.ipynb
6. notebooks/02_official_baseline_reproduction.ipynb
7. notebooks/05_model_metadata_and_run_registry.ipynb
8. references/official/notebooks/baseline.ipynb
9. src/baram/baseline.py
10. src/baram/registry.py
11. tests/test_baseline.py
12. tests/test_model_registry.py

이번 세션에서 수행할 단 하나의 작업:
"Weather grid feature lab: 공식 mean baseline과 P0 공간 통계 feature를 데이터 파악·전처리 중심으로 비교"

핵심 연구 질문:
1. LDAPS 16개 grid와 GFS 9개 grid를 단순 평균할 때 어떤 공간 정보가 사라지는가?
2. 변수별 mean에 std/min/max를 더하면 2024 time holdout total score, 1-NMAE, FICR가 일관되게 개선되는가?
3. lead hour와 source별 결측을 유지하면서 train/inference feature schema를 완전히 동일하게 만들 수 있는가?
4. Group 3의 짧은 label 기간에서도 개선 방향이 유지되는가?

구현 후보:
- `src/baram/features/__init__.py`
- `src/baram/features/weather_grid.py`
- 필요하면 `src/baram/baseline.py`는 기존 API 호환을 유지하는 최소 연결만 수정
- `tests/test_weather_features.py`
- `notebooks/06_weather_feature_lab.ipynb`
- `dev/dashboard/log/YYYY-MM-DD-baram-weather-feature-lab.html`

TDD 요구:
구현 전에 최소 아래 실패 사례를 테스트로 만들고 RED를 확인한다.
1. 필수 metadata 컬럼 누락
2. `data_available_kst_dtm > forecast_kst_dtm` cutoff 위반
3. 한 forecast의 grid 수가 source 계약(LDAPS 16, GFS 9)과 다름
4. 같은 forecast 안에서 lead hour가 둘 이상으로 불일치
5. 숫자형 weather feature가 없음
6. train/test feature column 이름 또는 순서 drift
7. 전체 grid가 결측인 forecast에서 imputation 전 결측이 숨겨짐
8. source prefix 충돌 또는 중복 feature 이름

데이터 파악과 전처리 원칙:
- 공식 raw CSV/XLSX는 읽기 전용이며 Git stage 금지.
- label, LDAPS, GFS의 행 수·기간·grid 수·lead·결측을 먼저 다시 확인한다.
- Group 3의 2022 결측은 0으로 채우지 않고 target별 non-null mask를 유지한다.
- weather 결측은 test 정보를 보지 않는 train-fit deterministic 처리만 허용한다.
- `grid_id`, latitude, longitude, availability metadata를 값 feature 평균에 섞지 않는다.
- std의 `ddof`, all-NaN 처리, column naming/order를 명시적 계약으로 고정한다.
- P0 비교는 `mean` 대 `mean+std/min/max+lead`까지만 한다. quantile, IDW, hub-height, air density, GBM은 이번 작업 범위 밖이다.

비교 실험:
- validation은 random split 금지, 2024 holdout을 기본으로 사용한다.
- 모델·seed·target mask·imputer·metric·clipping은 두 feature set에서 동일하게 유지한다.
- score는 total score 하나로 끝내지 말고 total_score, one_minus_nmae, FICR, target별 valid NMAE, 6%/8% 안착률을 기록한다.
- 개선 판단은 전체 평균과 Group 3이 함께 악화되지 않는지 본다.
- actual label은 metric 계산에서 원본을 유지하고 prediction만 0~capacity clip한다.
- model artifact와 registry entry는 메모리에서만 만들어 preprocessing/schema hash가 feature set마다 달라지는지 확인한다.

06 노트북 필수 구조:
1. 연구 질문과 안전 경계
2. 기존 00~05 및 공식 baseline 벤치마킹 표
3. 데이터 파악
4. 전처리/가공 전후
5. 속성 탐색
6. 시각화
7. 결과 해석
8. 실패 사례와 robustness
9. Decision Box
10. 다음 판단

모든 주요 code cell 사이에는 목적 또는 `관찰 → 해석 → 다음 판단` 마크다운을 둔다. 노트북 마지막에는 실행된 테스트 결과와 `scripts/check_notebook_integrity.py` 결과를 남긴다. 한국어 replacement 문자와 연속 물음표 치환, 연속 code cell을 0으로 유지한다.

안전 조건:
- 기본 실행에서 실제 모델 파일, 제출 CSV, run registry CSV, `outputs/`를 만들지 않는다.
- notebook은 메모리 계산과 read-only 공식 데이터만 사용한다.
- 실제 제출이나 Dacon 업로드를 하지 않는다.
- 기존 P0 registry schema를 깨는 변경은 하지 않는다. 필요하면 schema version migration을 별도 다음 작업으로 남긴다.

완료 기준:
- RED→GREEN TDD 증거 확보
- `python -m pytest -q` 통과
- `python scripts/check_notebook_integrity.py` 통과
- `06_weather_feature_lab.ipynb` 실행 완료, error output 0
- 실제 model/submission/outputs 미생성 확인
- `dev/dashboard/` 갱신
- 관련 파일만 stage/commit/push
- PR 생성 후 BARAM CI 확인
- PM 1명 승인 조건을 유지한 채 squash auto-merge 예약
- 한 작업만 끝내고 멈춰 결과와 다음 후보를 보고
```
