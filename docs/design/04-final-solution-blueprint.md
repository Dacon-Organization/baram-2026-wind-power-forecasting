# 최종 설계서: 공식 데이터·평가식·Baseline 반영

> 작성일: 2026-07-06 KST  
> 상태: 공식 배포 데이터와 평가 코드 확인 후 실행 설계  
> 입력 자료: `open/`, `baseline.ipynb`, `평가_산식 코드.ipynb`, 3조 분석 노트북·Short Research Paper, 데이터분석/EDA 강의 노트북  
> 범위: 데이터 분석 구조, 모델링 파이프라인, 평가 최적화, 발표·산출물 구성. 실제 학습 코드 구현은 다음 작업으로 분리한다.

---

## 0. 이번 설계의 결론

공식 데이터와 baseline이 공개되면서 이전 문서의 `공식 공개 후 재검증` 항목 중 핵심은 아래처럼 확정한다.

| 항목 | 최종 판단 |
|------|-----------|
| 데이터 구조 | `train/`, `test/`, `sample_submission.csv`, `info.xlsx`, `data_description.md` 구조 확정 |
| 예측 대상 | 2025년 8,760시간의 `kpx_group_1/2/3` 발전량 |
| 단위 | target은 `kWh`, capacity는 1시간 기준 `21,600/21,600/21,000 kWh` |
| 기상 격자 | LDAPS는 시각당 16개 격자, GFS는 시각당 9개 격자 |
| 예보 사용 가능 시각 | `data_available_kst_dtm` 제공. 각 24시간 forecast block은 전일 13:00 KST 사용 가능 |
| forecast lead | `forecast_kst_dtm - data_available_kst_dtm` 기준 12~35시간 |
| label 기간 | Group 1/2는 2022-2024 중심, Group 3은 2023-2024만 유효 |
| 평가 산식 | `0.5 * (1-NMAE) + 0.5 * FICR` 공식 코드로 확정 |
| 평가 필터 | 실제 발전량이 그룹 capacity의 10% 이상인 시간만 평가 |
| FICR 구간 | 시간별 error rate `<=6%: 4원/kWh`, `<=8%: 3원/kWh`, 그 외 0 |

전략의 중심은 `기상예보 후처리 + 그룹별 발전량 변환 + 정산 구간 보정`이다. baseline의 RandomForest는 제출 형식 확인용으로 재현하되, 최종 경쟁 모델의 기준선은 LightGBM/CatBoost 계열 tabular NWP 모델과 metric-aware calibration으로 둔다.

---

## 1. 벤치마킹한 구조를 BARAM에 옮기는 방식

### 1.1 3조 분석 노트북에서 가져올 것

3조 노트북의 강점은 분석을 코드 나열이 아니라 `Decision Box -> 검증 -> robustness -> 결론`으로 닫는 구조다. BARAM 노트북도 같은 틀을 쓴다.

| 3조 구조 | BARAM 적용 |
|----------|------------|
| 연구 질문과 목차를 먼저 제시 | "어떤 기상예보 후처리가 발전량과 정산점수를 동시에 올리는가"로 질문 고정 |
| Decision Box로 설계 선택 기록 | grid aggregation, cutoff, validation, model, calibration 선택마다 결정표 작성 |
| 파일럿 검증 후 전체 실행 | 작은 기간/일부 fold smoke test 후 전체 학습 |
| 품질 진단과 lineage 검증 | 파일 hash, timestamp, grid 수, lead hour, 결측, capacity 초과 진단 |
| parameter sweep과 robustness | aggregation 방식, hub-height 보정, validation fold, 보정 계수 sweep |
| Short Research Paper형 결론 | 발표 PDF는 문제-데이터-방법-결과-적용 가능성 흐름으로 구성 |

### 1.2 데이터분석 강의 노트북에서 가져올 것

EDA 노트북의 `데이터 파악 -> 전처리 -> 속성 탐색 -> 시각화 -> 해석` 순서를 BARAM 공식 분석 노트북의 기본 장 구조로 삼는다.

| 강의 구조 | BARAM 적용 |
|-----------|------------|
| 데이터 출처·크기·컬럼 확인 | 배포 파일 inventory와 schema audit |
| 결측치, dtype, 기술통계 | label/SCADA/weather 결측률, 범위, capacity violation |
| value_counts와 그룹별 집계 | grid 수, lead hour, 월/시간/그룹별 발전량 분포 |
| 간단한 시각화 후 문장 해석 | power curve, wind rose, 계절·시간 heatmap마다 해석 문단 작성 |
| 스토리텔링 | 발표는 배경-문제-해결-검증-적용 순서로 압축 |

### 1.3 Baseline에서 유지할 것과 버릴 것

| 항목 | 유지 | 개선 |
|------|------|------|
| 데이터 로드 | `utf-8-sig`, 공식 경로, target/capacity 상수 | 경로 config화, 원본 hash 기록 |
| 피처 | LDAPS/GFS 시각별 집계, calendar sin/cos | mean만 쓰지 않고 std/min/max/nearest/IDW 추가 |
| 모델 | 그룹별 label 유효기간에 맞춰 별도 학습 | LightGBM/CatBoost, fold별 OOF, ensemble 추가 |
| 후처리 | 0~capacity clipping | valid-hour/FICR 기준 bias calibration 추가 |
| 제출 | sample submission 형식 유지 | train/inference 분리, submission ledger/hash 기록 |
| 한계 | 빠른 제출 가능 | validation, metric 재현, SCADA 활용, 설명 가능성이 부족 |

---

## 2. 공식 데이터 판독 결과

### 2.1 파일과 행 수

| 파일 | 행 수 | 열 수 | 핵심 의미 |
|------|------:|------:|-----------|
| `train/ldaps_train.csv` | 420,864 | 35 | 2022-2024 LDAPS, 시각당 16개 grid |
| `train/gfs_train.csv` | 236,736 | 40 | 2022-2024 GFS, 시각당 9개 grid |
| `train/train_labels.csv` | 26,304 | 4 | 2022-01-01 01:00부터 2025-01-01 00:00까지 시간별 label |
| `train/scada_vestas_train.csv` | 157,819 | 37 | VESTAS 12기 10분 단위 power/ws/wd |
| `train/scada_unison_train.csv` | 105,264 | 16 | UNISON 5기 10분 단위 power/ws/wd |
| `test/ldaps_test.csv` | 140,160 | 35 | 2025 LDAPS, 시각당 16개 grid |
| `test/gfs_test.csv` | 78,840 | 40 | 2025 GFS, 시각당 9개 grid |
| `sample_submission.csv` | 8,760 | 5 | 2025년 시간별 제출 양식 |

### 2.2 label 품질에서 바로 반영할 사실

| 그룹 | non-null | 결측 | 최댓값 | capacity 초과 | 평가 대상 후보 `>=10%` |
|------|---------:|-----:|-------:|--------------:|------------------------:|
| Group 1 | 26,200 | 104 | 21,275.305 | 0 | 15,915 |
| Group 2 | 26,201 | 103 | 21,362.084 | 0 | 15,891 |
| Group 3 | 17,538 | 8,766 | 21,130.674 | 38 | 9,414 |

설계 결정:

- Group 3의 2022년 결측은 학습 제외하고, Group 3 fold는 2023-2024 중심으로 별도 관리한다.
- Group 3의 capacity 초과 38건은 label 오류로 단정하지 않고 `capacity_violation_flag`로 기록한다. metric 계산의 actual은 공식 코드처럼 그대로 쓰되, 학습 target clipping 여부는 실험으로 비교한다.
- 평가 필터가 actual 기준이므로 validation에서는 `actual >= 0.1 * capacity` 구간 점수를 별도 추적한다.

### 2.3 forecast metadata 결정

| 항목 | 확정값 |
|------|--------|
| LDAPS grid 수 | 모든 forecast 시각에서 16 |
| GFS grid 수 | 모든 forecast 시각에서 9 |
| train/test forecast lead | 12~35시간 |
| 사용 가능 시각 | `data_available_kst_dtm` |
| 제출 예측 시각 | `forecast_kst_dtm` |

이전 문서의 `h016~h039` 판독은 공식 파일 기준으로 더 이상 우선하지 않는다. 실제 구현에서는 `data_available_kst_dtm`과 `forecast_kst_dtm`의 차이로 lead를 계산한다.

---

## 3. 최종 노트북 설계

3조 노트북처럼 실행 결과와 의사결정이 남는 분석 노트북을 먼저 만들고, 제출용 코드는 별도 `.py`로 분리한다.

| 순서 | 노트북 | 목적 | 핵심 Decision Box |
|------|--------|------|-------------------|
| 00 | `00_official_data_audit.ipynb` | 파일·스키마·시간·grid·label 품질 잠금 | 원본 데이터 보관, label 결측/초과 처리 |
| 01 | `01_metric_reproduction.ipynb` | 평가 코드 포팅과 holdout score 검증 | valid mask, FICR 단가, capacity 단위 |
| 02 | `02_eda_weather_scada_labels.ipynb` | label/SCADA/weather 관계 탐색 | SCADA를 학습 보조로만 쓰는 범위 |
| 03 | `03_feature_lab.ipynb` | P0/P1 피처 후보 비교 | grid pooling, hub-height, air density |
| 04 | `04_modeling_scoreboard.ipynb` | baseline부터 앙상블까지 fold scorecard | 모델 후보, fold 평균과 그룹별 안정성 |
| 05 | `05_submission_and_calibration.ipynb` | 정산금 보정, clipping, 제출 파일 생성 | 최종 파일 선택과 Public 과적합 방지 |

각 노트북은 마지막 셀에 `결정 로그`, `검증 결과`, `다음 실험`을 남긴다. 발표 자료에는 노트북의 표와 그림을 그대로 재사용한다.

---

## 4. 코드 아키텍처

제출 검증 요구 때문에 train과 inference는 반드시 분리한다.

```text
baram-2026-wind-power-forecasting/
├── notebooks/
│   ├── 00_official_data_audit.ipynb
│   ├── 01_metric_reproduction.ipynb
│   ├── 02_eda_weather_scada_labels.ipynb
│   ├── 03_feature_lab.ipynb
│   ├── 04_modeling_scoreboard.ipynb
│   └── 05_submission_and_calibration.ipynb
├── src/
│   └── baram/
│       ├── config.py
│       ├── io.py
│       ├── schema.py
│       ├── metrics.py
│       ├── validation.py
│       ├── features/
│       │   ├── calendar.py
│       │   ├── weather_grid.py
│       │   ├── wind_physics.py
│       │   └── scada.py
│       ├── models/
│       │   ├── baseline_random_forest.py
│       │   ├── gbm.py
│       │   └── ensemble.py
│       ├── train.py
│       └── inference.py
├── configs/
│   ├── baseline_rf.yaml
│   ├── lgbm_p0.yaml
│   └── ensemble_final.yaml
├── outputs/
│   ├── audit/
│   ├── experiments/
│   ├── models/
│   └── submissions/
└── reports/
    ├── figures/
    └── final_presentation_outline.md
```

원본 대회 데이터는 사용 제한이 있으므로 Git에 커밋하지 않는다. `data/`가 필요하면 `.gitignore`와 `data/README.md`만 두고, 실제 CSV/XLSX는 로컬에 보관한다.

---

## 5. 피처 설계

### 5.1 P0: baseline을 바로 이기는 안전 피처

| 피처군 | 내용 | 이유 |
|--------|------|------|
| Calendar | hour/month/dayofweek/weekend, sin/cos | baseline 유지 |
| Lead | `lead_hour = forecast - available` | 12~35시간 예보 오차 구조 반영 |
| LDAPS/GFS grid stats | 변수별 mean/std/min/max/q25/q75 | mean만 쓰는 baseline 개선 |
| Wind speed | u/v 성분별 `sqrt(u^2+v^2)` | 풍력 변환의 핵심 |
| Wind direction | u/v 기반 sin/cos, 원형 평균 | 방향 discontinuity 방지 |
| Source spread | LDAPS와 GFS 같은 물리량 차이 | 모델 간 forecast disagreement |
| Capacity/group static | capacity, group id, turbine type | 그룹별 모델 또는 pooled 모델 선택용 |

### 5.2 P1: 물리·공간 피처

| 피처군 | 내용 | 주의 |
|--------|------|------|
| Nearest/IDW grid | `info.xlsx` 터빈 좌표와 grid 좌표 거리 기반 pooling | 좌표 변환 검증 필요 |
| Hub-height wind | 80m/100m 또는 10m/50m 기반 117m 보정 | 0풍속 clipping, alpha 안정화 필요 |
| Air density | 온도, 기압, 습도 기반 | 단위 K/Pa 확인 |
| Wind power density | `0.5 * rho * v^3` | 이상치 clipping |
| Terrain proxy | grid 고도, 공간 gradient | 외부 DEM 없이 제공 변수만 사용 |
| SCADA power curve | train SCADA와 label 관계로 그룹별 curve 학습 | 평가 기간 SCADA lag 사용 금지 |

### 5.3 P2: 고급 실험

| 후보 | 조건 |
|------|------|
| Group pooled model + group embedding | 그룹별 데이터 부족과 공통 패턴을 함께 잡을 때 |
| Quantile ensemble | FICR 임계값 주변 bias를 조정할 때 |
| Chronos/AutoGluon 보조 baseline | 로컬 실행, 공개일, 라이선스, covariate 지원을 model registry에 기록한 뒤 |
| 외부 데이터 | 공식 허용 규칙, 공개시각, 재현 경로가 확인된 뒤 |

---

## 6. Validation과 Scoreboard

random split은 금지한다. 모든 validation은 시간 순서를 지킨다.

| Fold | Train | Valid | 목적 |
|------|-------|-------|------|
| F0 Year Holdout | 2022-01-01 ~ 2023-12-31 | 2024 전체 | 2025 유사 1년 holdout |
| F1 Winter/Spring | 2022-01-01 ~ 2023-12-31 | 2024-01-01 ~ 2024-05-31 | 겨울·봄 저온/강풍 패턴 |
| F2 Summer/Fall | 2022-01-01 ~ 2023-12-31 | 2024-06-01 ~ 2024-10-31 | 장마·태풍·저풍속 패턴 |
| F3 Group 3 Focus | 2023-01-01 ~ 2023-12-31 | 2024 전체 | Group 3 label 짧음 대응 |
| F4 Recent Rolling | 2023-01-01 ~ 2024-06-30 | 2024-07-01 ~ 2024-12-31 | 최신 분포 안정성 |

**2026-07-27 정정.** F1·F2의 train을 "2022-2023 + 2024 일부 제외"로 적었던 초판은 valid가
2024 앞부분인데 train에 2024 뒷부분이 들어가 위 문장("모든 validation은 시간 순서를 지킨다")과
충돌했다. 미래로 과거를 예측하는 fold이며 설계서 06 2.1절의 절대 금지 항목이다.
fold별 **목적은 유지**하고 **구간만** 시간 순서를 지키도록 재계산했다
(노트북 13 Decision Box ⑲). Group 3 라벨이 2023-01-01 시작임을 확인해 F4의 train 시작도
2023-01-01로 맞췄다. F0에 있던 "Group 3은 2023" 단서는 코드가 `notna()` 마스크로
자동 처리하므로 표에서 뺐다.

Group 3 라벨이 2023부터라 **검증 구간을 2023으로 옮기는 fold는 만들 수 없다.**
따라서 위 다섯 fold의 valid는 전부 2024 안에 있으며, "다른 해에서도 순위가 유지되는가"는
이 데이터로 답할 수 없는 질문으로 남는다.

scoreboard는 아래 지표를 모두 기록한다.

- `total_score`, `one_minus_nmae`, `ficr`
- 그룹별 NMAE/FICR
- valid-hour score와 전체-hour MAE
- 월별/시간대별 error
- `<=6%`, `6~8%`, `>8%` 비율
- capacity clipping 전후 차이
- Public 제출 여부, 제출 hash, Dacon submission id

---

## 7. 모델링 로드맵

### 7.1 단계별 모델

| 단계 | 모델 | 목적 | 상태 |
|------|------|------|------|
| M0 | baseline RandomForest 재현 | 공식 baseline과 제출 형식 확인 | 완료 |
| M1 | Ridge/ElasticNet | 피처 sanity check와 과적합 감지 | 완료 |
| M2 | LightGBM/CatBoost 그룹별 모델 | 1차 주력 | **완료 — 채택하지 않음** |
| M3 | pooled GBM + group id | 그룹 간 공통 기상 반응 학습 | **완료 — `lgbm_pooled` 채택** |
| M4 | P1 물리·공간 피처 포함 GBM | 성능 개선 후보 | 미착수 |
| M5 | fold OOF 기반 ensemble | 그룹·계절 안정성 확보 | 미착수 |
| M6 | metric-aware calibration | FICR 구간과 capacity normalized error 보정 | **진행 중 — 노트북 16 실행 대기** |

**M2·M3 결과 (2026-07-27, 노트북 15).** 후보 6종을 사전 등록해 아홉 fold에서 채점한
결과, 그룹별 GBM(M2)과 pooled GBM(M3)의 **점수 차이는 문턱의 0.23배로 확정할 수 없었다.**
갈린 것은 부호다 — pooled 둘만 챔피언 대비 9/9 양수였고, 그룹별 둘은 F5·F8에서 음수로
내려가 설계서 06 5.4절 셋째 칸에 걸렸다. 그래서 M2는 완료하되 채택하지 않는다.

작업 모델은 **`lgbm_pooled`**다. `cat_pooled`와 점수가 구분되지 않는데(문턱의 0.08배)
학습이 4.56배 싸다. `cat_pooled`는 최종 제출 후보로만 남긴다.
XGBoost는 후보 수를 누르기 위해 M2에서 제외했다(노트북 15 Decision Box ㉔).

**M6 착수 (2026-07-27, 노트북 16).** 보정 후보 6종을 사전 등록하고 `src/baram/calibration.py`로
구현했다. `none`(통제군) · `bias_mae` · `bias_metric` · `affine_metric` · `binned_metric` ·
`isotonic`이며 전부 **설비용량 정규화 공간**에서 정의된다 — 그래야 설비용량이 다른 세 그룹이
파라미터를 공유하고, Group 3 라벨이 0행인 학습 창(`W_2022`)에서도 보정이 정의된다.

세 가지를 노트북 16의 Decision Box로 못 박았다.

- **㉗ fit 범위**: 학습 창 내부 expanding-window 3분할 OOF에서만 fit한다. 검증 구간 직접
  fit(`oracle_fit`)은 상한 진단으로만 쓰고 표에 누수임을 명시한다. 블록 수를 늘리는 대신
  같은 OOF를 "3블록 전체 / 마지막 블록만"으로 다시 fit해 **추가 학습 0회로 민감도를 보인다.**
- **㉘ 목적함수**: FICR 단독이 아니라 `total_score`다. FICR은 6% 안에서 완전히 평평하므로
  FICR만 보면 이미 안전한 행의 정확도를 얼마든지 버려도 손실이 없고, 그 손실은 1-NMAE에만
  나타난다. 7.2절의 후보 선택 규칙을 목적함수 단계에서 지키는 선택이다.
- **㉙ 채택 조건**: 결과를 보기 전에 다섯 조건을 등록했다 — 부호 9/9 · Δ 평균 > 0.0036 ·
  OOF 분할 민감도 판정 일치 · F0 재현 게이트 · terms·프레임 경로 일치. 하나라도 어긋나면
  채택하지 않는다. **5.4절 둘째 칸의 "잠정 채택"도 M6에서는 채택으로 보지 않는다** —
  보정은 파이프라인에 상시 붙는 변환이라 되돌리기 비용이 피처 하나를 넣고 빼는 것과 다르다.

노트북 16은 **후보 성적보다 오라클 상한을 먼저 잰다.** 보정은 파라미터가 1~5개뿐이라 Δ가
작게 나올 것이 거의 확실하고, 그때 "방향 자체가 무력한 것"과 "후보가 약한 것"을 구분할
장치가 없으면 어느 쪽으로도 결론을 낼 수 없다. 상한이 문턱보다 작으면 후보 성적을 볼
필요 없이 M6는 기각이다.

**M2 이후의 채점 조건 (2026-07-27 추가).** M2부터 후보 수가 수십 개로 늘어나므로
채점 fold를 먼저 고정한다. `src/baram/folds.py`의 **F0~F8 아홉 fold**를 쓰고 판정은
설계서 06 5.4절 규칙을 따른다. 노트북 14가 2024만 검증하는 fold 세트는 "부호 전부 일치"라는
가짜 확신을 발급한다는 것을 실측으로 보였으므로, **검증 연도 둘 이상을 덮지 않는 부호
일치는 근거로 쓰지 않는다.** 역방향 fold(F6·F8)는 순위 탐침으로만 쓰고 점수 수준은 쓰지 않는다.

### 7.2 최종 후보 선택 규칙

최종 제출은 Public 최고 점수만으로 고르지 않는다.

| 조건 | 선택 기준 |
|------|-----------|
| local total score 개선 | fold 평균과 그룹별 최소 점수가 함께 개선되어야 함 |
| FICR 개선 | 1-NMAE가 과도하게 악화되면 제외 |
| Group 3 개선 | Group 1/2를 크게 희생하면 별도 ensemble 후보 |
| Public 개선 | local 악화와 동반되면 과적합 후보로 보류 |
| 보정 적용 | fold 내부 OOF로 fit한 보정만 허용 |

---

## 8. 발표·Short Research Paper 구조

첨부한 3조 Short Research Paper의 장점을 그대로 가져와 발표 PDF도 "모델 자랑"보다 "문제 해결 서사"로 만든다.

| 발표 섹션 | 내용 | 대응 평가 항목 |
|-----------|------|----------------|
| 1. 문제 이해 | 풍력 예측이 어려운 이유, D-1 13/14시 사용 가능성, FICR 구조 | 과제 이해도 |
| 2. 데이터 진단 | LDAPS/GFS grid, SCADA, label availability, Group 3 결측, capacity | 과제 이해도, 문제 해결력 |
| 3. Baseline 재현 | 공식 RandomForest baseline과 한계 | 기술 우수성 |
| 4. Feature Engineering | grid stats, wind physics, hub-height, SCADA power curve | 기술 우수성 |
| 5. Validation | time split, Group 3 focus, metric reproduction | 문제 해결력 |
| 6. Model & Ensemble | GBM, pooled/group models, calibration | 기술 우수성 |
| 7. 정산금 관점 | 6%/8% 구간별 error 관리, FICR 개선 | 적용 가능성 |
| 8. 재현성과 운영 | train/inference 분리, seed, commit, submission ledger | 적용 가능성 |
| 9. 한계와 후속 연구 | 외부 데이터 보류, SCADA 평가 미제공, 지형 proxy 한계 | 발표 완성도 |

발표의 핵심 문장은 다음으로 둔다.

> "우리는 단순 평균오차 최소화가 아니라, 예보 사용 가능 시각을 지키는 기상 후처리와 정산 구간 보정을 결합해 Private 점수와 실무 적용 가능성을 함께 최적화했다."

---

## 9. 다음 한 작업

R3 원칙상 다음 작업은 하나만 고른다.

권장 다음 작업:

1. `src/baram/metrics.py`와 `01_metric_reproduction.ipynb`를 먼저 만든다.
2. 공식 `평가_산식 코드.ipynb`와 동일한 total score, 1-NMAE, FICR 결과를 train holdout에서 재현한다.
3. 이후 baseline RandomForest를 `.py` train/inference 구조로 분리한다.

이 순서가 좋은 이유는 metric이 먼저 잠겨야 baseline 개선이 실제 점수 개선인지 판단할 수 있기 때문이다.

---

## 10. 결정 로그

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-07-06 | 공식 평가 코드를 기준 산식으로 승격 | `metric(answer_df, pred_df)` 코드가 공개됨 |
| 2026-07-06 | forecast lead는 공식 파일의 `data_available_kst_dtm` 기준 12~35시간으로 사용 | 실제 파일 audit 결과와 data description이 일치 |
| 2026-07-06 | baseline은 제출 smoke 기준선으로만 사용 | validation과 metric-aware 보정이 없음 |
| 2026-07-06 | 3조 노트북의 Decision Box 구조를 BARAM 분석 노트북 표준으로 채택 | 설계 선택과 검증 근거를 발표 자료로 재사용하기 좋음 |
| 2026-07-06 | 첫 구현 작업은 metric reproduction으로 제한 | 모델보다 평가 재현이 후속 실험의 기준선이기 때문 |
| 2026-07-27 | M6 보정 후보를 6종으로 사전 등록하고 목적함수를 `total_score`로 고정 | 보정은 함수 형태 × 목적함수 × 그리드 폭으로 후보가 곱으로 불어난다. FICR 단독 최대화는 7.2절 규칙을 목적함수 단계에서 위반한다 (노트북 16 Decision Box ㉗·㉘) |
| 2026-07-27 | M6 채택 조건을 결과 이전에 등록하고 "잠정 채택"을 채택으로 보지 않기로 함 | 계단 지표에서 사후에 규칙을 고르면 거의 항상 "무언가는 개선됐다"고 말할 수 있다. 보정은 상시 변환이라 되돌리기 비용이 피처와 다르다 (노트북 16 Decision Box ㉙) |
| 2026-07-27 | 실행 전 노트북을 `notebooks/pending_execution.txt` 등록제로 머지 허용 | 학습 30회짜리 랩은 코드 완성 시점과 실행 시점이 다르다. 게이트를 없애는 대신 면제 대상을 코드 리뷰에 드러내고, 실행 후 등록이 남아 있으면 실패시켜 목록이 낡지 않게 했다 |
