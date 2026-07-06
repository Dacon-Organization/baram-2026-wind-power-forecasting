# 요구사항 정의

## 2026-07-06 P3 재검증 확정 사항

- Public/Private 분할은 40%/60%로 공식 확정되었습니다.
- 1차 평가는 Private Score 100%이며, 상위 30팀(예비 10팀 포함)이 산출물을 제출하고 검증 통과 상위 20팀이 발표 대상입니다.
- 최종 평가는 Private 50%와 발표 50% 합산입니다.
- 학습 코드와 추론 코드는 분리되어야 하며, Private Score를 오차 범위 내에서 복원할 수 있어야 합니다.
- 발표 자료는 10분 분량 PDF만 허용됩니다.
- 참가자격 증빙서류가 산출물 패키지에 포함됩니다.
- 외부 데이터는 공개성, 합법성, 라이선스, 활용 가능 시각, 재현 경로를 소명할 때만 후보로 둡니다.
- sample submission의 시작 시각이 `2024-12-31 08:00`로 표기되어 평가 기간 범위는 실제 파일 기준으로 재검증합니다.

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

## 다음 72시간 P0 백로그

1. 공식 평가 산식을 `src/baram/metrics.py`와 metric 재현 노트북으로 구현합니다.
2. `forecast_kst_dtm` 실제 범위와 test 조인 규칙을 검증합니다.
3. submission validator로 컬럼, 순서, 행 수, UTF-8, NaN, 음수, capacity 초과를 검사합니다.
4. cutoff validator로 모든 피처의 활용 가능 시각을 검증합니다.
5. baseline RandomForest를 `train.py`와 `inference.py`로 분리합니다.

P3 요구사항 원문: [P3-1 요구사항 정의 재검증](research/2026-07-06-p3-1-requirements-revalidation.md)
