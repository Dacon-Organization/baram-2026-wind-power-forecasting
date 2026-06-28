# 운영 마스터플랜: BARAM 2026

> 작성일: 2026-06-28 KST
> 상태: 공식 데이터 공개 전 운영 계획
> 선행 문서: `docs/groundwork/01-strategy-prd.md`, `docs/design/02-data-modeling-spec.md`, `docs/groundwork/04-perplexity-round2-results-synthesis.md`
> 범위: 제출 운영, 실험 추적, 리스크 관리, 2차 검증 준비. 코드 구현, 데이터 수집, 베이스라인 학습은 포함하지 않는다.

---

## 0. 목적과 범위

이 문서는 2026-07-06 10:00 KST 공식 데이터 공개 전 단계에서,
대회 운영 방식을 미리 잠그기 위한 마스터플랜이다.

핵심 목적은 다음 네 가지다.

1. 공식 데이터 공개 전에는 확정 사실과 재검증 항목을 분리한다.
2. 공개 직후 48시간은 모델 성능보다 데이터·평가·제출 형식 검증을 우선한다.
3. 1일 5회 제출 제한과 최종 제출 수동 선택 리스크를 운영 절차로 관리한다.
4. 2차 검증에서 재현 가능한 코드, seed, commit, 데이터 버전, 외부 근거를 설명할 수 있게 준비한다.

이 문서는 운영 계획 문서이며,
데이터 다운로드, 외부 데이터 수집, 모델 학습, baseline 파이프라인 생성으로 넘어가지 않는다.

---

## 1. 대회 전체 운영 원칙

| 원칙 | 내용 | 운영 의미 |
|------|------|-----------|
| 공식 우선 | Dacon 공식 페이지, 규칙, 데이터, 공지, FAQ, 운영자 답변을 최상위 근거로 둔다 | Perplexity, 워크숍, 외부 제도와 충돌하면 공식 기준을 우선 |
| 상태 분리 | `확정`, `워크숍 근거`, `외부`, `충돌`, `재검증`, `추론`을 구분한다 | 문서와 실험 로그에서 근거 상태를 함께 기록 |
| Point-in-time | 모든 피처는 `D-1 14:00 KST` 이전 생성·공개·확정 정보만 사용한다 | 기준시점 이후 예보, 관측, 보정, 재분석 사용 금지 |
| 재현성 | 모든 실험은 seed, commit, 데이터 버전, 환경, 제출 파일 hash를 기록한다 | 2차 검증에서 동일 결과 복원 가능해야 함 |
| 제출 절약 | 하루 5회 제출 제한을 실험 예산으로 관리한다 | Public LB 확인은 검증된 후보에만 사용 |
| Public 과적합 방지 | Public 점수 개선만으로 모델을 최종화하지 않는다 | local validation, 계절 fold, Private 리스크를 함께 본다 |
| 외부 데이터 보류 | 외부 데이터 세부 규칙 공개 전에는 수집·전처리·학습 적용을 보류한다 | 후보 메모와 ledger 템플릿만 유지 |
| 공식 데이터 보호 | 공식 데이터 파일은 업로드 허용 근거가 확인되기 전까지 Perplexity 등 외부 도구에 올리지 않는다 | 세션 리서치는 문서/요약/공식 링크 중심으로 운영 |
| 모델 우선순위 | tabular NWP baseline을 P0 주력으로 두고, Chronos-2는 P1 실험 후보로 둔다 | R2 결과상 Chronos-2 적격성은 확인됐지만 주력 축은 NWP 후처리 |
| 제도 분리 | KPX 실제 제도는 발표 배경으로만 쓰고 Dacon 평가 산식으로 자동 적용하지 않는다 | 정산금 simulator는 공식 기준 공개 전 시나리오로만 관리 |

---

## 2. 단계별 운영 계획

### 2.1 공식 데이터 공개 전

기간: 현재부터 2026-07-06 09:59 KST까지

| 목표 | 해야 할 일 | 하지 않을 일 | 완료 기준 |
|------|------------|--------------|-----------|
| 운영 기준 고정 | 제출 운영, 실험 로그, 리스크 레지스터, 역할 체크리스트 작성 | 코드 구현, 데이터 다운로드, 외부 데이터 수집 | 이 문서와 대시보드 갱신 |
| 재검증 항목 정리 | nMAE, 정산 임계값, Public/Private, valid-hour, LDAPS/GFS 메타데이터 체크리스트 유지 | 공식 산식 임의 확정 | 공개 직후 확인 목록 확정 |
| 외부 데이터 보류 | 후보만 기록하고 공식 규칙 공개를 기다림 | ERA5, KMA API, DEM, 위성, KPX 데이터 파이프라인 생성 | 후보 상태가 모두 `보류`로 남음 |
| Perplexity 운영 | 기존 R2 세션 결과를 문서화하고 후속 세션 기준 유지 | 공식 데이터 파일 업로드 | 세션 분리 기준 문서화 |
| 제출 준비 | sample submission 공개 후 확인할 체크리스트 준비 | 더미 제출 파일 생성 | 제출 검증 항목만 문서화 |

### 2.2 공식 데이터 공개 직후 48시간

기간: 2026-07-06 10:00 KST부터 2026-07-08 10:00 KST까지

| 시간대 | 운영 초점 | 산출물 | 의사결정 |
|--------|-----------|--------|----------|
| 0-4h | 파일 목록, 원본 hash, 파일 크기, 포맷 확인 | file inventory | 원본 데이터 변경 금지, 읽기 전용 보관 |
| 4-8h | 컬럼, dtype, timestamp, 결측, 단위 확인 | schema inventory | 컬럼명/단위 확정 전 모델링 금지 |
| 8-12h | base time, valid time, lead hour, grid 수, 좌표 확인 | NWP metadata audit | h016~h039, LDAPS 16/GFS 9 판독 검증 |
| 12-18h | sample submission 컬럼, row count, encoding 확인 | submission format checklist | 형식 오류 없는 제출 규격 잠금 |
| 18-24h | 평가 산식 원문, 정산 기준, Public/Private 기준 재확인 | metric decision note | 6/8, 4/6 시나리오 중 공식 기준 확정 여부 판단 |
| 24-36h | label availability, Group 3 기간, capacity 단위 검증 | group-date availability matrix | validation fold 조정 여부 결정 |
| 36-48h | 첫 제출 후보 운영 여부 판단 | first-submission go/no-go note | 제출은 형식 검증과 보수 baseline 확인용으로 제한 |

48시간 원칙:

- 첫 48시간 안에서는 성능 경쟁보다 데이터 이해, 산식 확인, 형식 검증을 우선한다.
- Public 점수가 나오더라도 하루 제출 5회를 모두 소진하지 않는다.
- 공식 데이터 파일을 외부 도구에 올릴 수 있다는 명시 근거가 없으면 Perplexity 업로드를 계속 보류한다.

### 2.3 모델링 기간

기간: 공개 직후 검증 완료 후부터 제출 마감 전 준비 구간까지

| 운영 축 | 원칙 | 산출물 |
|---------|------|--------|
| P0 모델 | LightGBM/CatBoost/XGBoost 계열 tabular NWP baseline을 주력으로 운영 | baseline scorecard, fold별 metric |
| P1 모델 | Chronos-2는 공개일, 라이선스, 로컬 실행, covariate 지원 기록 후 실험 후보로 운영 | model registry, 비교 실험 로그 |
| Feature | 공식 컬럼·단위·cutoff 안전성이 확인된 피처만 승격 | feature decision table |
| Validation | 2024 holdout, 계절 fold, Group 3 민감도 fold를 함께 본다 | validation board |
| Calibration | 정산금 공식 기준 확정 전에는 시나리오 민감도만 수행 | settlement scenario note |
| 제출 | local validation에서 설명 가능한 후보만 제출 | submission ledger |
| 롤백 | Public 점수만 좋아지고 local 검증이 나빠지는 후보는 롤백 후보로 표시 | rollback log |

### 2.4 제출 마감 전

기간: 제출 마감 3일 전부터 2026-08-14 10:00 KST까지

| 체크 | 운영 방식 |
|------|-----------|
| 후보 동결 | 마감 24시간 전부터 신규 feature, 신규 외부 데이터, 신규 모델 구조 도입 금지 |
| 제출 예산 | 마지막 날 최소 2회 제출 여유를 남겨 형식 오류와 수동 선택 이슈에 대응 |
| 최종 파일 | Public 최고 자동 선택에 맡기지 않고 의도한 제출 파일을 수동 선택 |
| 재현성 | 최종 후보의 seed, commit, 데이터 버전, 환경, 제출 hash를 한 줄로 복원 가능하게 정리 |
| 백업 | 최종 후보 1개, 보수 후보 1개, Public 고득점 후보 1개를 비교표로 보관 |
| 금지 | 마감 직전 Public 점수만 보고 설명 불가능한 scaling을 적용하지 않음 |

### 2.5 2차 검증 단계

기간: 1차 종료 후 Dacon 안내 일정 기준

| 항목 | 준비 내용 |
|------|-----------|
| 코드 재현 | train/inference 분리, 실행 순서, seed, requirements, 환경 정보를 제출 가능 상태로 정리 |
| 데이터 증빙 | 원본 hash, 데이터 버전, 외부 데이터 사용 여부와 근거, 수집 시각을 제출 가능하게 정리 |
| 모델 증빙 | 사전학습모델명, 가중치 URL, 공개일, 라이선스, 로컬 실행 여부 기록 |
| 발표 | 문제 이해, 데이터 분석, 모델 전략, 정산금 관점, 리스크 관리, 재현성 구조를 설명 |
| 금지 | 대회 평가 산식에 KPX 실제 제도를 뒤섞어 설명하지 않음 |
| 질의 대응 | cutoff, 외부 데이터, Public 과적합 방지, 제출 파일 선택 근거를 답변할 수 있게 준비 |

---

## 3. 1일 5회 제출 제한 운영 방식

| 제출 슬롯 | 목적 | 사용 조건 | 사용 금지 조건 |
|-----------|------|-----------|----------------|
| S1 | 형식/파이프라인 smoke 제출 | sample submission 형식, encoding, row count 확인 | 모델 성능 확인 없이 반복 제출 |
| S2 | P0 baseline 확인 | local validation이 통과한 보수 baseline | 단순 Public 탐색 |
| S3 | P0 개선 후보 확인 | fold 평균과 리스크가 설명 가능한 후보 | seed만 바꾼 무계획 제출 |
| S4 | 앙상블/보정 후보 확인 | local validation과 정산 시나리오가 개선된 후보 | Public 점수만 맞춘 후보 |
| S5 | 예비 슬롯 | 제출 오류, 긴급 롤백, 마감 대응 | 평시 소진 금지 |

일일 운영 규칙:

- 매일 제출 전 `submission_ledger`에 제출 목적, 실험 ID, commit, 데이터 버전, seed, 예상 리스크를 기록한다.
- 제출 후 Public score, 제출 파일명, Dacon 제출 ID, 수동 선택 상태를 기록한다.
- 같은 아이디어의 미세 변형으로 제출 슬롯을 소모하지 않는다.
- 하루 마지막 제출 뒤에는 다음 날 첫 후보를 정리하고 멈춘다.
- Public 점수 최고 파일과 최종 선택 파일이 다르면 이유를 남긴다.

---

## 4. 최종 제출 파일 수동 선택 체크리스트

마감 전 최종 파일은 자동 선택에 맡기지 않고 아래 체크리스트로 수동 선택한다.

| 체크 | 기준 |
|------|------|
| 파일 식별 | Dacon 제출 ID, 로컬 파일명, sha256, 생성 시각이 일치한다 |
| 수동 선택 | Dacon UI에서 의도한 파일이 최종 선택되어 있다 |
| 추가 제출 영향 | 최종 선택 후 추가 제출이 선택 상태를 초기화하거나 바꾸지 않았는지 확인한다 |
| 형식 | sample submission과 컬럼명, 순서, row count, encoding이 일치한다 |
| 값 범위 | 발전량 예측값이 그룹별 capacity와 물리 범위에 맞게 clipping/검증되어 있다 |
| 재현성 | 제출 파일을 만든 commit, seed, 데이터 버전, config가 기록되어 있다 |
| 검증 | local validation score, Public score, 리스크 메모가 후보 비교표에 남아 있다 |
| 근거 | 왜 Public 최고 파일이 아니라 이 파일을 선택했는지 또는 왜 최고 파일을 선택했는지 설명 가능하다 |
| 백업 | 보수 후보와 최종 후보의 차이를 문서화했다 |
| 마감 | 2026-08-14 10:00 KST 전 선택 완료와 화면 확인을 마쳤다 |

---

## 5. 실험 추적 원칙

### 5.1 실험 로그 필수 필드

| 필드 | 내용 |
|------|------|
| `experiment_id` | 날짜와 순번 기반 고유 ID |
| `run_date_kst` | 실행 또는 결정 일시 |
| `objective` | 실험 목적. 예: P0 tabular baseline, calibration scenario |
| `data_version` | 원본 hash 또는 audit version |
| `code_commit` | 실험 실행 commit SHA |
| `seed` | 전체 seed와 라이브러리별 seed |
| `features` | 사용 피처군과 제외 피처군 |
| `model` | 모델명, 버전, 주요 hyperparameter |
| `validation_split` | fold 정의 |
| `metrics` | local 1-NMAE, settlement scenario, group별 점수 |
| `submission_id` | 제출한 경우 Dacon 제출 ID |
| `decision` | keep, rollback, submit, archive |
| `risk_note` | cutoff, 외부 데이터, Public 과적합, 재현성 위험 |

### 5.2 seed와 재현성

- 실험마다 전역 seed를 하나 정하고 모델별 seed도 함께 기록한다.
- seed만 바꾼 반복 제출은 local validation 분산 확인 용도로만 쓰고, Public 제출에는 신중히 사용한다.
- 최종 후보는 같은 seed와 commit으로 제출 파일을 다시 만들 수 있어야 한다.
- 랜덤성이 큰 AutoML, bagging, ensemble 실험은 재현 실패 가능성을 리스크로 기록한다.

### 5.3 commit과 데이터 버전

- 제출 파일을 생성한 commit은 반드시 기록한다.
- 원본 데이터는 수정하지 않고 hash로 식별한다.
- 전처리 산출물은 원본 hash, 변환 규칙, 생성 시각을 함께 기록한다.
- 공식 데이터가 재업로드되거나 파일이 바뀌면 별도 데이터 버전으로 분리한다.

---

## 6. 외부 데이터와 외부 도구 운영 원칙

### 6.1 외부 데이터 규칙 공개 전 보류

R2-2 결과 기준 외부 데이터 세부 규칙은 아직 추후 공개 상태다.
따라서 공식 허용 규칙이 나오기 전까지 아래 데이터는 후보로만 남긴다.

| 후보 | 현재 조치 |
|------|-----------|
| ERA5, KMA API, NOAA/GFS 원천 자료 | 후보 메모만 유지, 수집·전처리·학습 적용 금지 |
| DEM, 지형, 고도, 위성 자료 | 외부 데이터 규칙 공개 전 사용 금지 |
| KPX 전력 공공 데이터 | 2025 label 누수 가능성이 있어 특히 보류 |
| 공휴일·달력 데이터 | 공개성은 높지만 영향이 낮으므로 P2 후보, 규칙 확인 후 사용 |

외부 데이터 사용을 검토할 때는 공개성, 무료성, 라이선스, 생성시각, 공개시각, 수집시각,
cutoff 안전성, 재현 명령을 모두 기록한다.

### 6.2 공식 데이터 파일 외부 업로드 금지

공식 데이터 파일은 다음 조건이 충족되기 전까지 Perplexity, ChatGPT, 원격 노트북,
외부 파일 분석 도구에 업로드하지 않는다.

1. Dacon 규칙 또는 운영자 답변으로 외부 도구 업로드 가능 여부가 확인된다.
2. 팀 내부에서 업로드 목적, 파일 범위, 익명화 가능성을 검토한다.
3. 업로드 이력, 세션명, 업로드 파일, 날짜, 목적을 기록한다.

허용 전에는 공식 데이터 대신 다음 자료만 외부 리서치에 사용한다.

- 공개 문서 링크
- 직접 작성한 요약표
- 컬럼명을 제거한 구조적 질문
- synthetic 예시
- 워크숍/공식 페이지에서 이미 공개된 내용

---

## 7. 모델 운영 원칙

| 우선순위 | 모델군 | 운영 판단 |
|----------|--------|-----------|
| P0 | tabular NWP baseline | LightGBM/CatBoost/XGBoost 계열. LDAPS/GFS, 시간, 공간, 물리 피처를 직접 활용하므로 주력 |
| P1 | Chronos-2 | R2-4에서 공개일, 라이선스, 로컬 실행, covariate 지원 확인. 단, local CV로 유효성을 확인한 뒤 후보화 |
| P2 | Chronos-Bolt/Chronos T5 | native covariate 한계로 zero-shot 또는 보조 baseline |
| P2 | AutoGluon-TimeSeries | validation window, stacking leakage, seed 재현성 확인 후 제한적 사용 |

운영 규칙:

- Chronos-2가 적격하다는 사실과 주력 모델이라는 판단은 다르다.
- P0 tabular baseline이 설명 가능성과 재현성의 기준선이다.
- 원격 API 기반 추론은 사용하지 않는다.
- 사전학습모델은 2026-07-05 이전 공식 공개 가중치, 라이선스, 로컬 실행 가능성을 `model_registry`에 기록한다.
- 모델 선택은 Public score가 아니라 local validation, 그룹별 안정성, 2차 검증 설명 가능성을 함께 본다.

---

## 8. LDAPS UM/KIM 전환 리스크 운영

R2-5 결과 기준 기상청 LDAPS는 UM 기반에서 KIM 단독 운영으로 전환된 리스크가 있다.
대회 제공 파일이 일반 KMA 자료 흐름을 그대로 반영하는지는 공식 데이터 공개 후 확인해야 한다.

| 리스크 | 확인 계획 | 운영 조치 |
|--------|-----------|-----------|
| train/test 간 LDAPS 모델 버전 차이 | 파일명, 메타데이터, 문서, 변수 목록 확인 | 2022-2024 train과 2025 test의 분포 shift로 기록 |
| 해상도 차이 | grid 좌표, projection, 격자 간격 확인 | LDAPS 16개 판독을 파일 기준으로 재검증 |
| 연직층/변수 차이 | 10m/80m/100m wind, pressure level, surface 변수 확인 | 변수별 availability matrix 작성 |
| base/valid time 차이 | lead hour 직접 계산 | D-1 14:00 cutoff 검증에 반영 |
| GFS와의 결합 차이 | GFS 9개 grid, 80m/100m 바람 포함 여부 확인 | LDAPS/GFS feature set을 분리 관리 |

데이터 공개 후 메타데이터 확인 항목:

1. 파일 포맷과 magic bytes
2. forecast source, model version, base time, valid time, lead hour
3. grid_id, latitude, longitude, projection
4. 변수명, 단위, 높이 레벨
5. train/test 기간별 변수 availability
6. 2026년 KIM 전환이 대회 2025 평가 데이터에 어떤 방식으로 반영됐는지

---

## 9. 정산금 simulator 운영

Dacon 공식 평가 기준이 공개되기 전까지 정산금 simulator는 확정 산식이 아니라 시나리오 비교 도구다.

| 시나리오 | 근거 상태 | 사용 방식 |
|----------|-----------|-----------|
| Scenario A: 6%/8% | 워크숍·유사 대회 근거, Dacon 공식 기준은 재검증 | Dacon 기준 후보로 분리 보관 |
| Scenario B: 4%/6% | KPX 실제 제도 변화 후보, 대회 산식 아님 | 발표 배경과 민감도 참고용으로만 보관 |

운영 원칙:

- Dacon 공식 기준이 공개되기 전에는 어느 시나리오도 공식값으로 고정하지 않는다.
- 6/8과 4/6 결과는 같은 표에 섞지 않고 별도 컬럼 또는 별도 파일로 분리한다.
- KPX 제도는 발표 배경과 문제의 현실성을 설명하는 데만 사용한다.
- Dacon 평가 산식, valid-hour 조건, 단가, theoretical max 정의가 공개되면 simulator 기준을 다시 잠근다.

---

## 10. Perplexity 후속 세션 운영 기준

| 상황 | 권장 방식 | 이유 |
|------|-----------|------|
| 같은 R2-x 답변의 표 정리, 출처 URL 보강, 표현 보수화 | 기존 세션 | claim lineage와 문맥 유지 |
| 같은 claim의 누락 근거 확인 | 기존 세션 | 출처 추적이 끊기지 않음 |
| 평가 산식에서 KPX 제도처럼 주제가 바뀜 | 새 세션 | 대회 기준과 외부 제도 혼용 방지 |
| 공식 페이지, FAQ, 데이터 파일이 업데이트됨 | 새 세션 | 날짜별 증거 분리 |
| 다른 모드/모델로 교차검증 | 새 세션 | 답변 품질과 출처 차이 추적 |
| 공식 데이터 파일 또는 스키마 분석 | 새 세션, 단 업로드 허용 확인 후 | 파일 업로드 리스크와 목적 분리 |
| Perplexity가 공식 사실과 추론을 섞기 시작함 | 새 세션 | 오염된 맥락 차단 |

공통 규칙:

- Space는 `BARAM 2026 Wind Research`를 유지한다.
- 세션명은 `R2-<번호> <주제> YYYY-MM-DD` 형식을 쓴다.
- 결과 반입 시 세션명, 날짜, 모드, 모델, 업로드 파일, 출처를 기록한다.
- 공식 데이터 파일은 업로드 허용 확인 전까지 올리지 않는다.

---

## 11. 리스크 레지스터

| ID | 리스크 | 영향 | 조기 신호 | 대응 |
|----|--------|------|-----------|------|
| R-01 | 기준시점 이후 데이터 사용 | 실격 가능 | available time 불명확, target 이후 관측 포함 | cutoff audit와 feature 승인표 운영 |
| R-02 | 공식 평가 산식 오해 | local score와 LB 괴리 | nMAE, valid-hour, 정산 기준 미공개 | 공개 직후 metric decision note 작성 |
| R-03 | 외부 데이터 규칙 미확정 상태에서 구현 | 규정 위반, 재현 실패 | 외부 API/DEM/위성 적용 요구 | 공식 규칙 전 보류, ledger만 유지 |
| R-04 | 공식 데이터 외부 업로드 | 규정/보안 리스크 | Perplexity 파일 분석 요구 | 업로드 허용 전 금지, 요약표만 사용 |
| R-05 | Public LB 과적합 | Private 하락 | local validation 악화에도 Public 개선 | fold score와 rollback log 병행 |
| R-06 | 제출 5회 제한 소진 | 후보 검증 실패 | 오전에 슬롯 대부분 사용 | S5 예비 슬롯 유지 |
| R-07 | 최종 파일 자동 선택 오류 | 의도와 다른 제출 채점 | 수동 선택 미확인, 추가 제출 후 상태 변경 | 마감 전 수동 선택 체크리스트 실행 |
| R-08 | Chronos-2 과신 | 주력 baseline 지연 | P1 모델에 제출 슬롯 과다 사용 | P0 tabular baseline 우선 |
| R-09 | LDAPS UM/KIM 전환 미반영 | train/test 분포 shift | 2025 예보 변수/해상도 차이 | NWP metadata audit와 기간별 score 분석 |
| R-10 | KPX 제도와 Dacon 산식 혼용 | 잘못된 simulator 최적화 | 4/6을 공식값처럼 사용 | 6/8, 4/6 시나리오 분리 |
| R-11 | seed/commit 누락 | 2차 재현 실패 | 제출 파일 생성 경로 불명확 | submission ledger 필수화 |
| R-12 | Group 3 label 기간 오해 | 검증 왜곡 | 2022 label 처리 불명확 | group-date availability matrix 작성 |

---

## 12. 역할/산출물 체크리스트

소규모 팀 또는 1인 운영이라도 역할은 분리해서 체크한다.

| 역할 | 책임 | 산출물 체크 |
|------|------|-------------|
| 운영 PM | 일정, 제출 슬롯, 최종 선택 관리 | 운영 캘린더, submission ledger, 최종 선택 체크리스트 |
| 데이터 스튜어드 | 파일 inventory, schema, hash, cutoff, 외부 데이터 ledger | file inventory, schema inventory, NWP metadata audit |
| 모델링 리드 | P0/P1 모델 우선순위와 validation 판단 | experiment log, validation board, model registry |
| 제출 캡틴 | 제출 파일 검증, Dacon 제출 ID 기록, 수동 선택 확인 | submission ledger, final submission note |
| 재현성 리드 | seed, commit, 환경, 데이터 버전 복원성 확인 | reproducibility sheet, final run manifest |
| 리서치 리드 | Perplexity/외부 리서치 분류, 출처 품질 관리 | session log, claim classification table |
| 발표 리드 | 문제 배경, 제도 맥락, 모델 설명, 2차 검증 대응 | presentation outline, Q&A sheet |

### 산출물 완료 체크

| 산출물 | 공개 전 | 공개 직후 | 마감 전 | 2차 검증 |
|--------|---------|-----------|---------|----------|
| 운영 마스터플랜 | 작성 완료 | 필요 시 갱신 | 최종 선택 절차 반영 | 제출 패키지 근거로 사용 |
| file/schema inventory | 템플릿만 | 작성 | 동결 | 증빙 |
| NWP metadata audit | 템플릿만 | 작성 | 갱신 | 설명 자료 |
| experiment log | 규칙 확정 | 운영 시작 | 최종 후보 고정 | 재현 자료 |
| submission ledger | 규칙 확정 | 첫 제출부터 운영 | 최종 선택 기록 | 제출 근거 |
| external data ledger | 템플릿만 | 규칙 확인 후 사용 | 최종 증빙 | 제출 자료 |
| model registry | 규칙 확정 | P1 모델 등록 | 최종 모델 증빙 | 제출 자료 |
| presentation outline | 골격 작성 | 데이터 사실 반영 | 최종 모델 반영 | 발표 PDF |

---

## 13. 결정 로그

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-06-28 | 운영 마스터플랜은 공식 데이터 공개 전 문서로 작성하고 코드 구현은 하지 않음 | R3 한 작업-한 정지와 사용자 범위 준수 |
| 2026-06-28 | 하루 제출 5회를 슬롯 기반으로 관리 | Public 탐색성 제출을 줄이고 예비 제출 여유 확보 |
| 2026-06-28 | 최종 제출은 수동 선택 체크리스트로 관리 | Public 최고 자동 선택과 추가 제출 후 선택 상태 리스크 방지 |
| 2026-06-28 | 공식 데이터 파일은 Perplexity 등 외부 도구 업로드 보류 | R2-2에서 명시 허용 근거가 없다고 판단 |
| 2026-06-28 | Chronos-2는 P1 후보, tabular NWP baseline은 P0 주력으로 유지 | R2-4 적격성 확인과 대회 데이터 구조를 함께 반영 |
| 2026-06-28 | LDAPS UM/KIM 전환 리스크를 공개 직후 NWP metadata audit 핵심 항목으로 둠 | R2-5에서 모델 전환 가능성이 확인됨 |
| 2026-06-28 | 정산금 simulator는 6/8, 4/6 시나리오를 분리 보관 | Dacon 기준 미공개와 KPX 제도 혼용 방지 |
| 2026-06-28 | KPX 제도는 발표 배경 전용으로 제한 | 대회 평가 산식으로 자동 적용하는 오류 방지 |

---

## 14. 다음 작업

다음 작업은 공식 데이터 공개 후 스키마·평가 산식 재검증이다.

그 전까지는 이 문서를 기준으로 제출 운영, 실험 추적, 외부 데이터 보류,
Perplexity 세션 운영, 2차 검증 준비 원칙을 유지한다.
