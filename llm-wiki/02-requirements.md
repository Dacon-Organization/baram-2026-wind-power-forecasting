# 요구사항 정의

## 필수 기능 요구사항

| ID | 요구사항 | 이유 |
|----|----------|------|
| FR-01 | 공식 평가 산식을 `src/baram/metrics.py`로 재현 | 모든 실험의 기준 |
| FR-02 | train과 inference를 별도 진입점으로 분리 | 2차 산출물 필수 요건 |
| FR-03 | sample submission의 컬럼, 순서, 행 수를 유지 | 제출 오류 방지 |
| FR-04 | 모든 예측값을 그룹별 물리 범위로 점검 | capacity 초과/음수 방지 |
| FR-05 | 실험별 config, seed, commit, 데이터 hash를 기록 | 재현성과 복구 |
| FR-06 | 제출 파일마다 SHA256과 생성 로그를 남김 | 최종 선택 파일 복구 |

## 데이터 요구사항

| ID | 요구사항 |
|----|----------|
| DATA-01 | 원본 데이터는 `data/raw/open/`에 로컬 보관하고 Git에 커밋하지 않는다. |
| DATA-02 | `data_available_kst_dtm` 기준으로 cutoff 안전성을 검증한다. |
| DATA-03 | Group 3 2022 결측은 학습 제외하고 별도 fold로 관리한다. |
| DATA-04 | SCADA는 학습 보조와 power curve 분석에 쓰되, 평가 기간 lag 피처로 쓰지 않는다. |
| DATA-05 | 외부 데이터는 공개성, 라이선스, 수집시점, 생성/공개시점, 재현 경로를 기록한 뒤 사용한다. |

## 모델 요구사항

| ID | 요구사항 |
|----|----------|
| MODEL-01 | baseline RandomForest를 먼저 재현한다. |
| MODEL-02 | 주력 모델은 LightGBM/CatBoost/XGBoost 계열 tabular NWP 후처리로 둔다. |
| MODEL-03 | 모든 모델은 time-based validation으로 평가한다. |
| MODEL-04 | Public score만 개선되고 local validation이 악화되는 모델은 최종 후보에서 보류한다. |
| MODEL-05 | 사전학습모델은 2026-07-05까지 공개된 오픈소스 가중치만 후보화한다. |
| MODEL-06 | 원격 API 기반 추론은 금지한다. |

## 제출 요구사항

| ID | 요구사항 |
|----|----------|
| SUB-01 | 하루 5회 제출 제한을 ledger로 관리한다. |
| SUB-02 | 최종 선택 파일은 Dacon 제출 창에서 수동 확인한다. |
| SUB-03 | 제출 파일명은 `submission_<experiment_id>_<short_sha>.csv` 패턴을 사용한다. |
| SUB-04 | 제출 후 Public score, 제출 ID, 선택 상태, local score를 기록한다. |
| SUB-05 | 마감일에는 예비 제출 슬롯을 남기고, 마지막 신규 실험 도입을 금지한다. |
