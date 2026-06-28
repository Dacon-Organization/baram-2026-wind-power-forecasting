# 데이터·모델링 설계서: BARAM 2026

> 작성일: 2026-06-28 KST
> 상태: 공식 데이터 공개 전 실행 설계
> 선행 문서: `docs/groundwork/01-strategy-prd.md`
> 보강 문서: `docs/groundwork/02-perplexity-research-synthesis.md`
> 다음 문서: `docs/design/03-operations-master-plan.md`

---

## 0. 목적과 범위

이 문서는 공식 데이터가 공개되기 전에도 준비할 수 있는 데이터 검증, 시점 검증,
피처 설계, validation split, baseline metric 재현, Perplexity 리서치 운영 방식과
Perplexity 리서치 결과 반영 기준을 정의한다.

핵심 원칙은 세 가지다.

1. **공식 데이터 스키마를 상상하지 않는다.**
   공개 전에는 컬럼명, 파일명, 단위, 결측 코드를 단정하지 않고 검증 템플릿만 만든다.

2. **point-in-time 사용 가능성을 먼저 검증한다.**
   모든 피처는 `D-1 14:00 KST` 예측 기준시점 이전에 생성·공개·확정된 정보여야 한다.

3. **Perplexity는 근거 확장 장치로 쓰고, 대회 사실 확정 장치로 쓰지 않는다.**
   Perplexity 결과는 모델링 아이디어, 논문/공식문서 탐색, 질문 생성에 쓰되,
   워크숍/공식 데이터와 충돌하면 공식 데이터를 우선한다.

Perplexity 1회차 결과의 상세 분류는
[Perplexity 리서치 종합](../groundwork/02-perplexity-research-synthesis.md)에 둔다.
이 문서에는 실행 설계에 필요한 결론만 반영한다.

---

## 1. 입력 사실과 불확실성

### 1.1 전략 PRD에서 상속하는 확정 사실

| 항목 | 값 |
|------|----|
| 예측 대상 | `KPX Group 1`, `KPX Group 2`, `KPX Group 3` |
| 설비용량 | Group 1: 21.6MW, Group 2: 21.6MW, Group 3: 21.0MW |
| 터빈 수 | Group 1: 6기, Group 2: 6기, Group 3: 5기 |
| 터빈 모델 | Group 1/2: VESTAS V126, Group 3: UNISON U136 |
| 학습 기상 데이터 | 2022-2024 LDAPS, GFS |
| 학습 label | Group 1/2: 2022-2024, Group 3: 2023-2024 |
| 평가 기상 데이터 | 2025 LDAPS, GFS |
| 평가 SCADA/KPX label | 제공 안 됨 |
| 예측 기준시점 | D-1 14:00 KST |
| 워크숍 판독 리드타임 | 00UTC 기준 `h016~h039` |

### 1.2 공식 공개 후 재검증 항목

| 항목 | 왜 위험한가 | 검증 방법 |
|------|-------------|-----------|
| 파일명/폴더명 | 워크숍 사진만으로 단정 불가 | 파일 inventory 자동 생성 |
| 컬럼명 | 사진상 예시 컬럼은 실제 스키마가 아닐 수 있음 | column inventory 작성 |
| 발전량 단위 | MW, MWh, kW, kWh 혼동 가능 | sample submission과 label 통계 확인 |
| timestamp timezone | UTC/KST 혼용 가능 | min/max, 간격, base/valid time 관계 확인 |
| LDAPS/GFS 리드타임 | `h016~h039` 판독은 공식 파일로 확인 필요 | base time, valid time, lead hour 재계산 |
| 정산금 지표 | Dacon 공식 평가 페이지에서 `정산금획득률` 정의 확인. Public/Private 세부 정산 기준은 추후 공개 | 공식 평가 페이지와 데이터 공개 후 metric 노트북으로 재현 |
| valid-hour 조건 | 실제 구현 단위에 따라 달라질 수 있음 | label 단위 기준 10% threshold 확인 |
| Group 3 2022 label 없음 | 파일 구성상 다르게 제공될 가능성 | group-date availability matrix 작성 |

---

## 2. 공식 데이터 공개 직후 검증 순서

데이터 공개 첫날에는 모델을 만들기보다 아래 순서로 `읽기 가능한 사실`을 잠근다.

1. **파일 inventory**
   - 파일명, 경로, 확장자, 크기, 수정시각, hash
   - 압축 파일 내부 구조
   - train/test/sample submission 구분

2. **스키마 inventory**
   - 파일별 row count, column count
   - 컬럼명, dtype, 결측률, unique count
   - timestamp 후보 컬럼
   - group/turbine/grid/lead/base time 후보 컬럼

3. **시간축 audit**
   - timestamp timezone
   - expected interval: 10분, 1시간, 3시간 등 실제 간격
   - 중복 timestamp, 누락 timestamp, 비정렬 timestamp
   - train label과 forecast valid time 결합 가능성

4. **예보 metadata audit**
   - forecast model: LDAPS/GFS
   - base time, valid time, lead hour
   - grid id, latitude, longitude, height level
   - release/available time이 파일에 있는지 확인

5. **label/SCADA audit**
   - KPX group별 label 기간
   - SCADA 10분 자료와 KPX 시간 단위 label의 집계 관계
   - 발전량 범위: 음수, capacity 초과, zero-run, outlier

6. **sample submission audit**
   - 제출 컬럼 순서
   - row count
   - timestamp 범위
   - 값 허용 범위와 encoding

7. **metric dry-run**
   - train holdout으로 `1-NMAE`, 정산금획득률 계열 지표 계산
   - 공식 리더보드 산식과 일치 여부는 공개 이후 확인

---

## 3. 스키마 검증 템플릿

아래 표들은 실제 CSV/Parquet로 저장할 inventory의 논리 스키마다.
공식 데이터 공개 후 `data_audit` 단계에서 자동 생성한다.

### 3.1 `file_inventory`

| 컬럼 | 설명 | 예시/규칙 |
|------|------|-----------|
| `file_id` | 내부 식별자 | `train_ldaps_001` |
| `path` | 프로젝트 기준 상대 경로 | `data/raw/...` |
| `source_archive` | 압축 파일명 | 없으면 null |
| `role` | train/test/submission/reference | 수동 확인 |
| `extension` | csv, parquet, xlsx 등 | 원본 유지 |
| `size_bytes` | 파일 크기 | integer |
| `sha256` | 원본 hash | 재현성 |
| `rows` | 행 수 | 읽기 가능 파일만 |
| `columns` | 열 수 | 읽기 가능 파일만 |
| `encoding` | UTF-8 등 | CSV 필수 |
| `read_status` | ok/error | 오류 메시지 별도 보관 |
| `notes` | 수동 메모 | 불확실성 기록 |

### 3.2 `column_inventory`

| 컬럼 | 설명 |
|------|------|
| `file_id` | file inventory 외래키 |
| `column_name` | 원본 컬럼명 |
| `normalized_name` | 내부 표준명 후보 |
| `dtype_raw` | pandas 추론 dtype |
| `semantic_role` | timestamp, target, forecast, grid_id, turbine_id, group_id, metadata, unknown |
| `unit_candidate` | MW, kW, m/s, deg, K, C, Pa 등 |
| `missing_rate` | 결측률 |
| `unique_count` | 고유값 수 |
| `min_value` | 숫자형 최소 |
| `max_value` | 숫자형 최대 |
| `sample_values` | 대표값 3-5개 |
| `status` | 확정, 후보, 검토필요 |

### 3.3 `time_index_audit`

| 컬럼 | 설명 |
|------|------|
| `file_id` | 대상 파일 |
| `time_column` | timestamp 컬럼 |
| `timezone_assumption` | KST, UTC, unknown |
| `min_time` | 최소 시각 |
| `max_time` | 최대 시각 |
| `expected_freq` | 10min, 1h 등 |
| `detected_freq` | 실제 최빈 간격 |
| `duplicate_count` | 중복 timestamp 수 |
| `missing_interval_count` | 누락 구간 수 |
| `non_monotonic_count` | 역순/비정렬 수 |
| `needs_manual_review` | yes/no |

### 3.4 `forecast_metadata_audit`

| 컬럼 | 설명 |
|------|------|
| `forecast_source` | LDAPS 또는 GFS |
| `file_id` | 대상 파일 |
| `base_time_column` | 예보 기준시각 컬럼 |
| `valid_time_column` | 예보 대상시각 컬럼 |
| `lead_column` | lead time 컬럼 |
| `lead_min` | 최소 lead hour |
| `lead_max` | 최대 lead hour |
| `grid_id_column` | 격자 식별자 |
| `lat_column` | 위도 |
| `lon_column` | 경도 |
| `height_level_columns` | 10m, 80m, 100m 등 |
| `available_time_rule` | 파일 제공 시각 또는 보수적 추정 규칙 |
| `cutoff_safe` | 기준시점 전 사용 가능 여부 |

### 3.5 `group_label_availability`

| 컬럼 | 설명 |
|------|------|
| `group_id` | KPX Group 1/2/3 |
| `target_column` | label 컬럼 |
| `capacity_mw` | 설비용량 |
| `min_time` | label 시작 |
| `max_time` | label 종료 |
| `row_count` | label row 수 |
| `missing_rate` | 결측률 |
| `zero_rate` | 0 발전량 비율 |
| `over_capacity_count` | 설비용량 초과 건수 |
| `negative_count` | 음수 발전량 건수 |
| `valid_hour_threshold` | capacity 10% 기준 |

### 3.6 `external_data_ledger`

| 컬럼 | 설명 |
|------|------|
| `dataset_name` | 외부 데이터명 |
| `provider` | 제공 기관 |
| `url` | 원본 URL |
| `license` | 라이선스/약관 |
| `is_public` | 누구나 접근 가능한지 |
| `is_free` | 무료인지 |
| `generated_time_field` | 데이터 생성시각 필드 |
| `published_time_field` | 공개시각 필드 |
| `collected_at_kst` | 수집시각 |
| `prediction_cutoff_safe` | D-1 14:00 기준 안전 여부 |
| `repro_command` | 재수집 명령 |
| `status` | 후보, 승인, 제외 |

### 3.7 `model_registry`

| 컬럼 | 설명 |
|------|------|
| `model_name` | 모델명 |
| `model_type` | tabular, time-series foundation, ensemble 등 |
| `weights_url` | 가중치 다운로드 경로 |
| `license` | 라이선스 |
| `official_release_date` | 공식 가중치 공개일 |
| `allowed_by_rule` | 2026-07-05 이전 공개 여부 |
| `runs_local_weights` | 로컬 가중치 실행 여부 |
| `uses_remote_api` | 원격 추론 API 사용 여부 |
| `status` | 후보, 승인, 제외 |

---

## 4. 시간·리드타임·cutoff 검증 설계

### 4.1 기준 정의

| 개념 | 정의 |
|------|------|
| `target_time_kst` | 예측하려는 발전량의 시간 |
| `prediction_cutoff_kst` | `target_date - 1일 14:00 KST` |
| `forecast_base_time_utc` | 예보가 생성된 기준시각 |
| `forecast_valid_time_kst` | 예보값이 가리키는 실제 대상시각 |
| `lead_hour` | `valid_time - base_time` |
| `available_time_kst` | 해당 데이터가 참가자에게 사용 가능해진 시각 |

### 4.2 cutoff 판정 규칙

```text
사용 가능 조건:
available_time_kst <= prediction_cutoff_kst

주의:
target_time_kst가 prediction_cutoff 이후인 것은 당연하다.
문제는 데이터가 언제 생성/공개/확정되어 참가자가 쓸 수 있었는가이다.
```

### 4.3 예보 데이터 판정 절차

1. `base_time`, `valid_time`, `lead_hour` 컬럼 존재 여부 확인
2. `lead_hour = valid_time - base_time` 직접 재계산
3. 워크숍 판독값 `h016~h039`와 공식 파일 값 비교
4. `base_time 00UTC`가 KST로 어떤 날짜/시간에 해당하는지 변환
5. 파일에 release time이 있으면 사용
6. release time이 없으면 워크숍 설명과 공식 문서 기준으로 보수적 available time 설정
7. `available_time_kst <= D-1 14:00 KST` 검증

### 4.4 SCADA/label 데이터 판정 절차

평가 기간 SCADA/KPX label은 제공되지 않는 것으로 판독된다.
따라서 SCADA는 기본적으로 다음 용도로만 쓴다.

- 학습 기간 power curve 학습
- 터빈/그룹별 정상 운전 패턴 분석
- label 품질 점검
- curtailment/정지 패턴 후보 탐지

평가 추론에서 직접 피처로 쓰려면 2025 평가 기간의 같은 정보가 필요하므로,
공식 데이터가 별도 제공하지 않는 한 SCADA lag 피처는 배제한다.

---

## 5. 피처 설계

### 5.1 피처 계층

| 계층 | 피처군 | 공개 전 설계 상태 |
|------|--------|-------------------|
| 시간 | hour, month, season, weekday, holiday 후보 | 사용 가능 |
| 예보 원본 | LDAPS/GFS 원본 변수 | 컬럼 공개 후 확정 |
| 풍향/풍속 변환 | u/v → speed/direction, sin/cos direction | 사용 가능 |
| 허브 높이 보정 | 80m/100m wind, shear, 117m 근사 | 컬럼 공개 후 확정 |
| 공기밀도/풍력물리 | pressure, temperature 기반 air density, wind power density | 컬럼 공개 후 확정 |
| 공간 집계 | nearest, mean, max, std, weighted pooling, gradient | grid 좌표 공개 후 확정 |
| 그룹 정적정보 | capacity, turbine_count, turbine_model, cut-in/rated/cut-out | 사용 가능 |
| SCADA 파생 | power curve, 정상/비정상 운전 label, curtailment 후보 | train 분석용 |
| 정산 최적화 | capacity-normalized error risk, threshold-aware calibration | metric 확정 후 |

Perplexity 1회차 결과는 아래처럼 상태를 낮춰 반영한다.
데이터 관련 항목은 반드시 `확정 / 외부 리서치 / 충돌 / 공식 공개 후 재검증 / 추론` 중 하나로 표시한다.

| 피처 후보 | 상태 | 적용 조건 | 1회차 판단 |
|-----------|------|-----------|------------|
| 풍향 `sin/cos` | 외부 리서치 | 풍향 또는 u/v 성분 제공 | P0 후보. 누수 위험 낮음 |
| u/v 기반 풍속·풍향 | 외부 리서치 | u/v convention 확인 | P0 후보 |
| `wind_speed^2`, `wind_speed^3` | 외부 리서치 | 풍속 컬럼 제공 | power curve 비선형 보강 |
| 공기밀도, wind power density | 외부 리서치 | 온도·기압·습도 단위 확인 | P1 후보 |
| grid mean/std/max/min | 외부 리서치 | 격자별 변수가 제공됨 | P0/P1 후보 |
| nearest/bilinear/IDW | 공식 공개 후 재검증 | grid 좌표와 단지/그룹 좌표 필요 | 좌표 공개 후 선택 |
| `issue_time`, `valid_time`, `lead_hour` | 공식 공개 후 재검증 | 예보 메타데이터 제공 | cutoff validator와 함께 P0 |
| multi-run forecast spread | 공식 공개 후 재검증 | 동일 target에 복수 run 존재 | 미래 issue time 누수 방지 필요 |
| hub-height extrapolation | 추론 | 10m/50m/80m/100m 바람과 허브 높이 확인 | 임의 alpha 금지 |
| wake/terrain/RIX | 충돌/공식 공개 후 재검증 | 터빈 배치, DEM, 외부 데이터 규칙 필요 | 공식 데이터 전 사용 보류 |

### 5.2 시간 피처

| 피처 | 설명 | 누수 위험 |
|------|------|-----------|
| `hour` | 0-23 | 낮음 |
| `month` | 1-12 | 낮음 |
| `season` | 봄/여름/가을/겨울 | 낮음 |
| `hour_sin`, `hour_cos` | 일중 주기 | 낮음 |
| `month_sin`, `month_cos` | 연중 주기 | 낮음 |
| `is_weekend` | 주말 여부 | 낮음 |
| `holiday` | 공휴일 | 외부 데이터 공개성 확인 필요 |

공휴일은 발전량 직접 원인이라기보다 전력시장/운영 패턴 보조 피처일 가능성이 낮으므로 P2 후보로 둔다.

### 5.3 풍속·풍향 변환

공식 컬럼에 u/v 성분이 제공되면 다음 변환을 표준화한다.

```text
wind_speed = sqrt(u^2 + v^2)
wind_dir_rad = atan2(u, v)
wind_dir_sin = sin(wind_dir_rad)
wind_dir_cos = cos(wind_dir_rad)
```

주의: meteorological wind direction convention은 수학적 atan2와 방향 정의가 다를 수 있다.
공식 컬럼 설명을 확인한 뒤 `from-direction`인지 `to-direction`인지 고정한다.

### 5.4 허브 높이 보정

터빈 허브 높이는 워크숍 기준 117m다.
예보 변수에 80m/100m wind가 있으면 다음 우선순위를 둔다.

1. 100m 풍속 직접 사용
2. 80m/100m 풍속 동시 사용
3. 10m/80m 또는 10m/100m 기반 wind shear 추정
4. 117m 보간/외삽 후보 생성

후보식:

```text
alpha = log(v_high / v_low) / log(z_high / z_low)
v_117 = v_ref * (117 / z_ref) ^ alpha
```

단, 풍속 0 또는 결측 구간에서는 alpha가 불안정하므로 clipping과 결측 처리 규칙이 필요하다.

### 5.5 물리 기반 파생 피처

| 피처 | 목적 | 필요 변수 |
|------|------|-----------|
| `wind_speed_cubed` | 출력이 풍속 세제곱에 비례하는 구간 반영 | wind speed |
| `air_density` | 온도/기압에 따른 출력 보정 | pressure, temperature |
| `wind_power_density` | `0.5 * rho * v^3` | air density, wind speed |
| `cut_in_margin` | cut-in 근처 민감도 | turbine spec, wind speed |
| `rated_margin` | rated speed 근처 포화 | turbine spec, wind speed |
| `cut_out_risk` | 강풍 정지 가능성 | turbine spec, wind speed |
| `direction_bin` | 산악지형 풍향 효과 | wind direction |

### 5.6 공간 피처

LDAPS 16개, GFS 9개 격자 제공은 워크숍 근거다.
공식 grid metadata 확인 후 다음 집계를 만든다.

| 방식 | 설명 | 우선순위 |
|------|------|----------|
| 전체 평균 | grid 변수 평균 | P0 |
| 전체 표준편차 | 공간 불확실성/경사 proxy | P0 |
| max/min | 국지 강풍/약풍 후보 | P1 |
| nearest grid | 단지 중심 또는 그룹 중심 최근접 | P1 |
| distance-weighted mean | 좌표 기반 가중 평균 | P1 |
| group-color cluster pooling | Group 1/2/3 색상 위치와 가까운 격자 집계 | P2 |
| spatial gradient | 동서/남북/고도 proxy | P2 |

그룹별 정확 위치/지명은 불확실하므로,
초기 모델은 group별 독립 공간 가중치를 학습하거나 전체 grid 통계를 사용한다.

### 5.7 SCADA 활용 경계

| 사용 방식 | 허용 후보 | 이유 |
|-----------|-----------|------|
| 학습 기간 power curve 추정 | 예 | train label과 SCADA로 그룹별 변환 학습 |
| 이상치/정지 탐지 | 예 | label 품질 관리 |
| 2025 평가기간 lag SCADA | 기본 제외 | 평가 SCADA 미제공 판독 |
| target day 실측 보정 | 금지 | 기준시점 이후/평가 실측 정보 |
| 터빈별 정적 특성 | 예 | 워크숍 스펙 기반 |

---

## 6. Validation split 설계

### 6.1 금지 split

| 방식 | 금지 이유 |
|------|-----------|
| random row split | 시간 누수와 계절 분포 왜곡 |
| 2025 평가 데이터 기반 split | label 없음, 제출 목적 외 사용 위험 |
| Group 1/2 2022 정보를 Group 3 2022 label처럼 취급 | Group 3 label 미제공 판독 |
| target day 이후 관측을 포함한 rolling feature | 예측 기준시점 위반 |

### 6.2 기본 backtest

| Fold | Train | Valid | 목적 |
|------|-------|-------|------|
| F0 | 2022-2023 Group 1/2, 2023 Group 3 | 2024 전체 | 2025 유사 1년 holdout |
| F1 | 2022-2023 | 2024 겨울/봄 | 계절별 성능 |
| F2 | 2022-2023 | 2024 여름/가을 | 계절별 성능 |
| F3 | 2023 상반기 | 2023 하반기 | Group 3 짧은 기간 민감도 |
| F4 | 2023 하반기 | 2024 상반기 | rolling stability |

공식 데이터 공개 후 실제 label 범위가 다르면 이 표를 재계산한다.

### 6.3 Public 과적합 방지

워크숍 판독으로 Public/Private가 2025년 내부에서 계절성을 고려해 분할된다는 설명이 있었지만,
Dacon 공식 평가 페이지는 Public/Private 정산 기준을 추후 공개 대상으로 둔다.
따라서 40:60 같은 수치는 공식 사실로 쓰지 않고, Public 점수에 맞춰 특정 계절/월 bias를
과하게 조정하지 않는 운영 원칙만 채택한다.

운영 원칙:

- local validation 평균이 나빠지는 Public 개선은 보류
- Public 제출은 하루 5회 제한을 실험 설계에 반영
- 제출 전후 실험 조건을 기록하고, 최고 Public 파일 자동선택 여부를 별도 확인
- CV 기반 최적 모델과 Public LB 최고 모델이 다르면, 차이를 리더보드 과적합 신호로 기록
- lag/rolling feature를 쓰는 실험은 forecast horizon보다 짧은 lag를 금지하고, 필요하면 fold 경계에 embargo gap을 둔다

---

## 7. Metric 재현 설계

### 7.1 상수

```text
capacity = {
  "KPX Group 1": 21.6,
  "KPX Group 2": 21.6,
  "KPX Group 3": 21.0
}
```

### 7.2 NMAE

```text
valid_mask_g = y_true_g >= 0.10 * capacity_g
nmae_g = mean(abs(y_true_g - y_pred_g) / capacity_g over valid_mask_g)
score_1_nmae = 1 - mean(nmae_g for g in groups)
```

주의:

- 발전량 단위가 MW가 아니면 capacity도 같은 단위로 변환한다.
- valid mask가 그룹별로 다를 수 있으므로 그룹별 계산 후 평균한다.
- label이 없는 test에서는 valid mask를 알 수 없으므로 validation에서만 재현한다.

### 7.3 정산금획득률 계열 지표

Dacon 공식 평가 페이지에서 확정된 것은 정산금획득률의 큰 정의다.

```text
settlement_rate = captured_settlement_amount / theoretical_max_settlement_amount * 100
```

Public/Private Score의 세부 정산 기준은 공식 페이지에서 추후 공개 대상으로 남아 있다.
따라서 local simulator는 아래처럼 복수 시나리오를 지원하도록 설계한다.

| 시나리오 | 상태 | 임계값/단가 | 사용 목적 |
|----------|------|-------------|-----------|
| 워크숍 기준 | 워크숍 근거/추론 | 6% 이하 4원, 6~8% 3원, 8% 초과 0원 | 기존 워크숍 판독 재현 |
| 최신 KPX 후보 | 외부 리서치/충돌 | 4%/6% 계열 강화 기준 | 제도 변화 민감도 분석 |
| 공식 BARAM 기준 | 공식 공개 후 재검증 | 데이터/평가 탭 공개 후 확정 | 최종 metric 구현 |

워크숍 기준 simulator 초안:

```text
hourly_error_rate_g = abs(y_true_g - y_pred_g) / capacity_g
if hourly_error_rate_g <= 0.06:
  unit_price = 4
elif hourly_error_rate_g <= 0.08:
  unit_price = 3
else:
  unit_price = 0

captured_settlement_g = sum(unit_price * y_true_energy_g over valid hours)
theoretical_max_g = sum(4 * y_true_energy_g over valid hours)
scr_g = captured_settlement_g / theoretical_max_g
ficr_or_scr = mean(scr_g for g in groups)
```

재검증 필요:

- 발전량이 MW 평균인지 MWh 에너지인지에 따라 `y_true_energy_g` 계산이 달라진다.
- 공식 산식이 실제 발전량이 아니라 설비용량/시간 기준으로 최대 정산금을 계산할 수 있다.
- valid-hour 10% 조건이 BARAM 공식 산식에 그대로 적용되는지 확인해야 한다.
- `FICR`, `SCR` 같은 내부 표기는 문서에서는 `정산금획득률`로 통일한다.

### 7.4 Total Score

워크숍 사진 기준:

```text
total_score = 0.5 * score_1_nmae + 0.5 * ficr_or_scr
```

공식 세부 정산 기준 공개 후 동일하게 재현되는지 확인한다.

---

## 8. 모델링 로드맵

### 8.1 P0: 데이터/metric baseline

목적은 점수가 아니라 제출과 재현성이다.

| 모델 | 설명 | 산출물 |
|------|------|--------|
| seasonal climatology | group, month, hour 평균 | 제출 형식 검증 |
| simple power curve | forecast wind speed → 발전량 | 물리 직관 baseline |
| linear/ridge | 핵심 날씨 피처 소수 | feature sanity check |
| LightGBM small | tabular baseline | 첫 local leaderboard |

### 8.2 P1: 본 모델 후보

| 모델 | 장점 | 리스크 |
|------|------|--------|
| LightGBM/CatBoost group별 모델 | 강력한 tabular 성능, 해석 용이 | group별 데이터 부족 |
| global model + group static feature | 데이터 공유 가능 | 그룹 특성 희석 |
| multi-output regression | 그룹 간 동시 예측 | 구현/해석 복잡 |
| quantile model | 불확실성/보정 활용 | metric과 직접 연결 필요 |
| ensemble | Public/Private 안정성 | 실험 관리 복잡 |

### 8.3 P1/P2: Time-series foundation 후보

Chronos 계열은 워크숍 데모와 외부 공식 자료 기준 후보로 남긴다.
단, 대회 규정상 로컬에서 공개 가중치를 직접 로드해야 하며 원격 inference API는 사용할 수 없다.

| 후보 | 우선순위 | 사용 목적 | 확인 필요 |
|------|----------|-----------|-----------|
| `chronos-2` | P1 | NWP known future covariate 지원 가능성 검증 | 공식 가중치 공개일, 라이선스, 로컬 실행, 입력 포맷 |
| `chronos-bolt-small` | P2 | 빠른 zero-shot/데모 baseline | 공개일, 라이선스, CPU 가능성 |
| `chronos-bolt-base` | P2 | 앙상블 다양성 확보 | prediction length, 로컬 실행 환경 |
| AutoGluon-TimeSeries + Chronos | P2 | 빠른 비교 실험 | `num_val_windows`, stacking leakage, seed 재현성 |

Foundation model은 처음부터 주력으로 두지 않는다.
이 대회는 기상예보 다변량 피처와 물리/정산 최적화가 중요하므로,
tabular NWP post-processing 모델을 기준선으로 놓고 foundation model은 앙상블 후보로 평가한다.

Perplexity 1회차 보고서는 Chronos-2를 1순위로 제안했지만,
현재 설계에서는 `LightGBM/CatBoost tabular NWP baseline → Chronos-2 covariate 실험 → 앙상블`
순서를 유지한다. `chronos_wind_power_demo.ipynb`는 synthetic 10분 데이터 zero-shot 예시이므로,
실제 대회 적합성의 증거가 아니라 사용법 참고로만 둔다.

### 8.4 Calibration

| 방법 | 목적 |
|------|------|
| capacity clipping | 음수/설비용량 초과 방지 |
| group bias correction | 그룹별 평균 편향 조정 |
| season/hour bias correction | 계절·시간대별 편향 조정 |
| threshold-aware adjustment | 6%, 8% 정산 구간 근처 보정 |
| monotonic sanity check | 풍속 증가 구간에서 출력이 비상식적으로 감소하는지 점검 |

---

## 9. Perplexity 리서치 운영 설계

### 9.1 Space 구성

Space 이름:

```text
BARAM 2026 Wind Power Forecasting Lab
```

Space 설명:

```text
Purpose: Research and design support for Dacon BARAM 2026 wind power forecasting competition.
Do not treat web findings as competition facts unless verified against official Dacon data/rules or workshop materials.
Always separate: official fact, workshop-derived fact, external research, inference, unresolved uncertainty.
Prefer primary sources: official docs, model cards, academic papers, government/agency reports.
Output in Korean, but keep technical terms and equations in English when useful.
```

업로드 후보:

| 자료 | 업로드 여부 | 주의 |
|------|-------------|------|
| 전략 PRD Markdown/PDF | 권장 | 내부 설계 기준 제공 |
| 워크숍 사진 | 선택 | 공유 가능성/약관 확인 후 |
| 데모 노트북 | 권장 | Chronos demo 맥락 |
| 공식 대회 페이지 링크 | 권장 | 최신 규정 확인 |
| 공식 데이터 파일 | 데이터 공개 후 보류 | 대회 규정과 외부 업로드 가능성 확인 전 업로드 금지 |

### 9.2 세션 운영 원칙

- 세션 하나에는 질문 하나의 목적만 둔다.
- 첫 프롬프트에는 `대회 규정상 원격 API 추론 금지`, `D-1 14:00 cutoff`, `공식 데이터 공개 전 불확실성`을 명시한다.
- 결과는 그대로 복사하지 않고 `findings / citations / contradictions / actions / risks` 형식으로 가져온다.
- Perplexity 결과가 워크숍 자료와 충돌하면 `충돌`로 남기고 사용자 또는 공식 FAQ로 확인한다.

### 9.3 모델/도구 선택 가이드

Perplexity 내 모델명과 기능은 계정/시점에 따라 바뀔 수 있으므로,
아래는 세션을 시작할 때의 선택 기준이다.

| 작업 | 권장 모드 | 권장 모델 성향 | Computer/Deep Research |
|------|-----------|----------------|------------------------|
| 공식 규정/FAQ 확인 | Pro Search | 출처 추적이 강한 최신 검색 모델 | Computer 불필요 |
| 논문/기관 보고서 조사 | Deep Research | 긴 문서 종합이 강한 모델 | Deep Research 권장 |
| 피처 설계 아이디어 | Pro Search | 추론/표 정리가 강한 모델 | 필요 시 Deep Research |
| Chronos/AutoGluon 사용법 | Pro Search | 코드/공식 문서 이해가 강한 모델 | Computer 불필요 |
| 공식 데이터 공개 후 스키마 표 만들기 | Space + Computer 또는 파일 분석 도구 | 코드/표 처리 강한 모델 | 업로드 가능성 확인 후 |
| 발표 배경/시장 조사 | Deep Research | 보고서형 종합 모델 | Deep Research 권장 |

모델 선택 예:

- `Claude Sonnet 계열`: 긴 문서 비교, 요구사항 정리, 위험 분류
- `GPT 계열`: 구조화된 표, 코드 설계, 검증 절차 생성
- `Gemini 계열`: 넓은 웹 검색, 긴 컨텍스트 자료 비교

정확한 모델명은 Perplexity UI에서 당일 제공 목록을 보고 선택한다.

### 9.4 세션별 프롬프트

#### Session P0-1: 공식 규정·데이터 누수 재확인

권장:

- Space 사용
- Pro Search
- Computer 불필요

프롬프트:

```text
You are helping with Dacon BARAM 2026 wind power forecasting competition.

Task:
Verify the competition constraints that matter for data leakage and model eligibility.

Known workshop facts:
- Prediction cutoff is D-1 14:00 KST.
- Evaluation period is 2025.
- Evaluation SCADA/KPX labels are not provided.
- Remote API-based model inference is prohibited.
- Only open-source pretrained model weights officially public by 2026-07-05 are allowed.

Please produce:
1. Verified official facts with source links.
2. Unverified or ambiguous items that must be checked on the official Dacon page/FAQ.
3. Practical do/don't rules for feature engineering.
4. A checklist for code validation.

Output in Korean.
Separate "official fact", "workshop-derived fact", "inference", and "uncertain".
```

후속 프롬프트:

```text
Convert the answer into a table with columns:
rule_id, rule_summary, allowed, prohibited, source_url, risk_if_wrong, implementation_check.
Do not add facts that were not sourced.
```

#### Session P0-2: NWP post-processing와 복잡 지형 풍력 예측

권장:

- Deep Research
- 논문/기관 보고서 우선
- Computer 불필요

프롬프트:

```text
Research short-term wind power forecasting using Numerical Weather Prediction post-processing,
especially for complex terrain and wind farms.

Context:
- Target: hourly wind power for 3 wind farm groups.
- Forecast sources: LDAPS-like local NWP and GFS-like global NWP.
- Important variables: wind speed/direction, u/v components, temperature, humidity, pressure, 80m/100m wind.
- Hub height: 117m.
- Need methods that can be implemented locally in Python, without remote model APIs.

Please find primary sources, review papers, NREL/NOAA/KMA/ECMWF-like institutional sources if available.

Return:
1. Top 10 feature engineering practices.
2. Top 5 validation practices.
3. Known pitfalls in complex terrain wind forecasting.
4. Which ideas are realistic for a 6-week competition.
5. Citations with links.

Output in Korean with English technical terms preserved.
```

후속 프롬프트:

```text
Turn the findings into an implementation backlog.
For each item include: expected impact, leakage risk, data requirement, implementation difficulty, first experiment design.
```

#### Session P0-3: LDAPS/GFS grid feature 설계

권장:

- Space 사용
- Pro Search
- 필요 시 Deep Research

프롬프트:

```text
Design feature engineering for gridded weather forecasts in wind power prediction.

Competition assumptions to respect:
- LDAPS: local high-resolution NWP, workshop says around 16 grid points.
- GFS: global NWP, workshop says around 9 grid points.
- Need to predict 3 KPX groups, but exact group coordinates are uncertain.
- Do not assume actual official column names.

Please propose:
1. Grid aggregation methods before exact coordinates are known.
2. Methods after grid coordinates are known.
3. How to handle wind direction and u/v components.
4. How to combine LDAPS and GFS without overfitting.
5. What to validate first after data release.

Output as a practical design table in Korean.
```

후속 프롬프트:

```text
Create a minimal P0 feature set, a P1 feature set, and a P2 feature set.
Each feature must state whether it is safe before target time and what official columns are required.
```

#### Session P0-4: Validation split와 Public/Private 과적합 방지

권장:

- Pro Search 또는 Deep Research
- Computer 불필요

프롬프트:

```text
We need validation design for a wind power forecasting competition.

Known structure:
- Training weather data: 2022-2024.
- Group 1 and 2 labels: 2022-2024.
- Group 3 labels: 2023-2024.
- Test weather data: 2025.
- Public/Private samples are hidden and approximately 40:60, said to reflect full 2025 seasonality.
- Random split is not acceptable.

Please design robust validation schemes:
1. rolling-origin split,
2. year holdout,
3. seasonal block validation,
4. group-aware validation,
5. public leaderboard overfitting guardrails.

Return a recommended validation protocol and rationale.
Output in Korean.
```

후속 프롬프트:

```text
Convert this validation protocol into exact fold definitions using only years and seasons,
without assuming unavailable 2025 labels.
Add what each fold is meant to catch.
```

#### Session P1-1: Chronos/Chronos-Bolt/Chronos-2 적합성

권장:

- Pro Search
- 공식 GitHub, Hugging Face model card, AutoGluon 문서 우선
- Computer 불필요

프롬프트:

```text
Evaluate whether Amazon Chronos, Chronos-Bolt, Chronos-2, and AutoGluon-TimeSeries are suitable
for a wind power forecasting competition with multivariate NWP covariates.

Constraints:
- Remote inference APIs are prohibited.
- Only open-source model weights officially public by 2026-07-05 are allowed.
- Must run locally or on participant-managed compute.
- Need reproducible train/inference code.
- Forecast target: hourly wind power for 3 groups.

Please verify:
1. Which Chronos variants support covariates/multivariate forecasting.
2. Local installation and inference requirements.
3. License and model weight availability.
4. How to use them as baselines or ensemble members.
5. Risks compared with LightGBM/CatBoost tabular NWP models.

Use official sources first. Output in Korean.
```

후속 프롬프트:

```text
Create a decision table:
model, allowed_by_competition_rule, local_run_possible, covariate_support, expected_compute, integration_plan, exclude_reason_if_any.
Mark any unknowns explicitly.
```

#### Session P1-2: 정산금 지표 최적화

권장:

- Deep Research
- 논문/대회 사례 조사

프롬프트:

```text
Research methods for optimizing forecasts when the score combines normalized MAE and incentive/settlement thresholds.

Competition-like metric:
- Group-wise NMAE normalized by capacity.
- Valid hours may require actual generation >= 10% capacity.
- Incentive tiers may be <=6% error and <=8% error.
- Final score may combine 1-NMAE and settlement capture rate.

Please find methods or principles for:
1. threshold-aware calibration,
2. quantile/median choice,
3. bias correction by season/hour/group,
4. avoiding over-optimization to public leaderboard,
5. validation metrics to track.

Output in Korean with citations.
```

후속 프롬프트:

```text
Turn this into a calibration experiment plan with 5 experiments.
Each experiment should include local validation metric, expected effect, and failure mode.
```

#### Session P2-1: 발표/시장 맥락

권장:

- Deep Research
- 정부/전력시장/기관 자료 우선

프롬프트:

```text
Research the market and policy context for renewable energy generation forecasting incentives,
with focus on Korea if possible and wind power forecasting globally.

We need presentation material, not unsourced claims.

Return:
1. Why wind power forecasting matters for grid stability.
2. How forecast accuracy relates to settlement/incentives.
3. Why wind is harder than solar.
4. Real-world examples of NWP + ML forecasting.
5. Source-backed figures only.

Output in Korean. Mark uncertain or non-Korea examples clearly.
```

후속 프롬프트:

```text
Create 5 presentation slide claims.
Each claim must have one source, one caveat, and one way our modeling plan addresses it.
```

### 9.5 Perplexity 결과 반입 포맷

Perplexity 결과를 Codex 작업으로 가져올 때는 아래 형식으로 붙인다.

```markdown
## Perplexity Session Result

- Space:
- Session:
- Date:
- Mode/Model:
- Uploaded files:

### Findings
1.
2.
3.

### Citations
| Claim | Source | Reliability | Notes |
|-------|--------|-------------|-------|

### Contradictions / Uncertainties
| Item | Perplexity says | Workshop/Official says | Action |
|------|-----------------|------------------------|--------|

### Implementation Candidates
| Candidate | Data required | Leakage risk | Expected impact | Priority |
|-----------|---------------|--------------|-----------------|----------|

### Follow-up Prompts Needed
1.
2.
```

### 9.6 사용하지 않을 Perplexity 방식

| 방식 | 제외 이유 |
|------|-----------|
| Perplexity 답변을 그대로 PRD 사실로 반영 | 대회 공식 사실과 외부 정보가 섞일 위험 |
| 공식 데이터 파일을 무조건 업로드 | 대회 데이터 외부 업로드 규정 확인 전 위험 |
| Perplexity가 생성한 코드를 검증 없이 실행 | 재현성/누수/버그 위험 |
| 원격 API 모델 성능 비교 | 대회 API 추론 금지와 충돌 |

### 9.7 Perplexity 기능 확인 출처

| 항목 | 확인 출처 | 설계 반영 |
|------|-----------|-----------|
| Spaces | [Perplexity Help: What are Spaces?](https://www.perplexity.ai/help-center/en/articles/10352961-what-are-spaces) | Space 단위 파일, 지침, thread, Computer 작업 맥락 관리 |
| Pro Search | [Perplexity Help: What is Pro Search?](https://www.perplexity.ai/help-center/en/articles/10352903-what-is-pro-search) | 빠른 공식 문서/웹 검증 세션에 사용 |
| Research mode | [Perplexity Help: What is Research mode?](https://www.perplexity.ai/help-center/en/articles/10738684-what-is-research-mode) | 긴 보고서형 조사와 심층 리서치에 사용, 모델 수동 선택 불가로 표기 |
| Advanced Deep Research | [Perplexity Help: What's New in Advanced Deep Research](https://www.perplexity.ai/help-center/en/articles/13600190-what-s-new-in-advanced-deep-research) | 더 많은 출처 교차검증, 문서 처리, 코드 sandbox 가능성 반영 |
| Computer | [Perplexity Help: What is Computer?](https://www.perplexity.ai/help-center/en/articles/13837784-what-is-computer) | 공식 데이터 공개 후 파일/표 처리 후보로 분류 |
| Prompt tips | [Perplexity Help: Tips for Getting Better Answers](https://www.perplexity.ai/help-center/en/articles/13645819-tips-for-getting-better-answers-from-perplexity) | 집중 질문, 후속 질문, 세션 분리 원칙 반영 |

---

## 10. Perplexity 리서치 결과 반영 1회차

상세 분류는 [Perplexity 리서치 종합](../groundwork/02-perplexity-research-synthesis.md)을 기준으로 한다.

**Perplexity 결과는 대회 공식 사실이 아니며, 공식 데이터/규칙과 충돌 시 공식 기준 우선**이다.
이번 1회차 반영은 운영 마스터플랜이나 코드 구현으로 넘어가지 않고,
데이터·모델링 설계서의 후보와 재검증 질문을 보강하는 범위로 제한한다.

### 10.1 공식 사실로 반영한 항목

| 항목 | 상태 | 반영 |
|------|------|------|
| 1차 온라인 평가는 nMAE와 정산금획득률 기반 | 확정 | metric 설계에서 두 지표 병행 |
| 정산금획득률 정의 | 확정 | simulator 인터페이스에 반영 |
| Public/Private 정산 기준 추후 공개 | 공식 공개 후 재검증 | 임계값 시나리오 복수 유지 |
| 외부 데이터 규칙 추후 공개 | 공식 공개 후 재검증 | 외부 데이터 파이프라인 보류 |
| 사전학습모델 공개일/원격 API 금지 | 확정 | model registry와 로컬 실행 검증 |

### 10.2 피처 설계 보강

Perplexity 리서치에서 반복 확인된 범용 후보는 아래 우선순위로 둔다.

| 우선순위 | 피처군 | 상태 | 주의 |
|----------|--------|------|------|
| P0 | 풍향 sin/cos, u/v 기반 풍속, 풍속 제곱/세제곱 | 외부 리서치 | 공식 컬럼과 단위 확인 |
| P0 | grid mean/std/max/min | 외부 리서치 | LDAPS/GFS 격자 구조 확인 |
| P0 | issue/valid/lead time | 공식 공개 후 재검증 | cutoff validator와 함께 구현 |
| P1 | air density, wind power density | 외부 리서치 | 온도/기압/습도 단위 확인 |
| P1 | forecast spread, multi-run stats | 공식 공개 후 재검증 | 미래 issue time 누수 금지 |
| 보류 | wake effect, terrain/RIX, 외부 DEM | 충돌/공식 공개 후 재검증 | 외부 데이터 규칙 전 사용 금지 |

### 10.3 Validation split 보강

- 기본은 rolling-origin expanding window로 유지한다.
- 2024 전체 holdout과 계절별 fold를 함께 두어 2025 평가 분포 shift를 모사한다.
- Group 3의 짧은 label 기간은 별도 fold에서 민감도를 본다.
- `lag < forecast horizon`은 금지한다.
- Public LB만 좋아지는 후처리나 conservative scaling은 롤백 후보로 기록한다.

### 10.4 Chronos/AutoGluon 후보 판단

| 후보 | 상태 | 판단 |
|------|------|------|
| LightGBM/CatBoost | 외부 리서치 | 1차 주력 baseline 유지 |
| Chronos-2 | 외부 리서치/공식 공개 후 재검증 | covariate 지원 후보. P1 실험 |
| Chronos-Bolt | 외부 리서치 | zero-shot/앙상블 보조. NWP 직접 반영 한계 |
| AutoGluon-TimeSeries | 외부 리서치 | `num_val_windows`, stacking leakage, seed 재현성 확인 후 사용 |

### 10.5 정산금 최적화 실험 후보

| 실험 | 상태 | 조건 |
|------|------|------|
| capacity clipping | 외부 리서치 | 단위와 capacity 확인 후 P0 |
| local settlement simulator | 공식 공개 후 재검증 | 공식 임계값 공개 후 확정 |
| 6/8, 4/6 임계값 시나리오 비교 | 추론/충돌 | 공식 기준 전 민감도 분석 |
| quantile/pinball loss | 외부 리서치 | local CV 기반으로만 선택 |
| conservative scaling | 외부 리서치 | Public LB 직접 튜닝 금지 |
| OOF bias/isotonic calibration | 외부 리서치 | train fold 내부에서만 fit |

### 10.6 2차 Perplexity 질문

다음 Perplexity 세션은 기존 워크숍 자료와 이번 synthesis 문서를 업로드한 뒤 수행한다.
각 세션은 모델/모드/Computer 사용 여부를 프롬프트 상단에 명시한다.

1. Dacon 공식 평가 페이지의 nMAE, 정산금획득률, Public/Private 기준 추후 공개 상태 재확인
2. 외부 데이터 규칙이 새로 공개되었는지 규칙/FAQ/토론 탭 확인
3. 워크숍 자료의 D-1 14:00, h016~h039, LDAPS/GFS grid 수와 Perplexity 주장 대조
4. Chronos-2 공식 가중치 공개일, 라이선스, covariate 지원, 로컬 실행성 확인
5. KMA/NOAA 1차 출처만으로 LDAPS/GFS 사양과 변수 재정리
6. KPX 최신 정산제도와 Dacon 대회 평가 산식의 차이 분리

---

## 11. 실험 우선순위

### 11.1 공개 전 준비 가능

| 우선순위 | 작업 | 산출물 |
|----------|------|--------|
| P0 | schema inventory 스크립트 설계 | `file_inventory`, `column_inventory` 템플릿 |
| P0 | cutoff validator 설계 | base/valid/available time 규칙 |
| P0 | metric 함수 인터페이스 설계 | `score_1_nmae`, `scr`, `total_score` |
| P0 | Perplexity Space/세션 프롬프트 준비 | 세션별 질문지 |
| P1 | feature catalog 초안 | 시간/예보/물리/공간/그룹 피처 |
| P1 | validation fold 정의 | 2024 holdout, seasonal block |
| P2 | Chronos/AutoGluon 후보 조사 | model registry |

### 11.2 공개 직후 48시간

| 시간 | 작업 | 완료 기준 |
|------|------|-----------|
| 0-4h | 압축 해제, hash, file inventory | 모든 파일 read_status 기록 |
| 4-8h | column/time/forecast metadata audit | timestamp, lead, grid 구조 확인 |
| 8-12h | sample submission dry-run | 형식 오류 없는 dummy submission |
| 12-24h | metric holdout 구현 | local validation score 산출 |
| 24-36h | P0 baseline 3종 | climatology, power curve, LightGBM small |
| 36-48h | 첫 제출 후보 | Public 확인용 보수 제출 |

---

## 12. 산출물 구조 제안

공식 데이터 공개 후 아래 구조로 확장한다.

```text
2026-BARAM-Wind-Power-Prediction-AI-Competition/
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── audit/
├── notebooks/
│   ├── 00-data-audit.ipynb
│   ├── 01-metric-reproduction.ipynb
│   └── 02-baseline-models.ipynb
├── src/
│   ├── data_audit.py
│   ├── time_cutoff.py
│   ├── features.py
│   ├── metrics.py
│   ├── train.py
│   └── inference.py
└── submissions/
```

파일 생성은 공식 데이터 공개 후 진행한다.
지금은 설계 문서만 유지한다.

---

## 13. 결정 로그

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-06-28 | 데이터·모델링 설계서는 공식 스키마 단정 없이 검증 템플릿 중심으로 작성 | 데이터 공개 전 환각 방지 |
| 2026-06-28 | SCADA lag 피처는 기본 제외 | 2025 평가 SCADA 미제공 판독 |
| 2026-06-28 | tabular NWP post-processing 모델을 1차 주력으로 설정 | 다변량 기상예보와 물리 피처를 직접 활용하기 좋음 |
| 2026-06-28 | Chronos 계열은 보조 baseline/앙상블 후보로 유지 | 데모와 공식 자료가 있으나 대회 데이터 구조에는 탭ular 모델이 안전 |
| 2026-06-28 | Perplexity Space/세션/프롬프트 운영표를 설계서에 내장 | 리서치 결과가 실험 설계로 바로 이어지게 하기 위함 |
| 2026-06-28 | Perplexity 1회차 결과를 공식/외부/충돌/재검증/추론으로 재분류 | 워크숍 자료 없이 수행된 리서치라 공식 사실로 승격하지 않기 위함 |

---

## 14. 다음 작업

다음 작업은 이번 1회차 반영 이후 사용자가 선택할 수 있다.

1. **2차 Perplexity 질문 수행 후 설계 보강**
   공식 평가 산식, 외부 데이터 규칙, Chronos-2, LDAPS/GFS 1차 출처를 재확인한다.

2. **운영 마스터플랜 작성**
   제출 횟수, 실험 로그, 산출물 검증, 2차 발표 준비를 일정표로 고정한다.

R3 원칙에 따라 이번 작업은 Perplexity 리서치 결과 반영 1회차에서 멈춘다.
