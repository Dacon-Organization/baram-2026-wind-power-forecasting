# Perplexity 2차 재검증 질문 패키지: BARAM 2026

> 작성일: 2026-06-28 KST
> 상태: 공식 데이터 공개 전 2차 Perplexity 재검증용 프롬프트 패키지
> 기반 문서: [전략 PRD](01-strategy-prd.md), [Perplexity 리서치 종합 1회차](02-perplexity-research-synthesis.md), [데이터·모델링 설계서](../design/02-data-modeling-spec.md)
> 범위: 2차 Perplexity 질문 패키지 작성만 포함한다. 운영 마스터플랜 작성, 코드 구현, 모델링 파이프라인 생성은 포함하지 않는다.

---

## 0. 목적

이 문서는 1회차 Perplexity synthesis에서 남긴 재검증 질문 후보를
Perplexity에 바로 투입할 수 있는 세션별 프롬프트로 구체화한다.

핵심 목적은 다음과 같다.

1. 공식 평가 산식과 규칙을 Dacon 공식 출처 기준으로 다시 확인한다.
2. 외부 데이터, Chronos-2, LDAPS/GFS, KPX 정산제도처럼 외부 출처가 필요한 항목을
   대회 공식 사실과 분리한다.
3. Perplexity 답변을 그대로 설계 사실로 승격하지 않고,
   `공식 / 외부 / 충돌 / 재검증 / 추론` 분류표로만 반입한다.

공통 안전 문구:

```text
Perplexity 결과는 대회 공식 사실이 아니며, 공식 데이터/규칙과 충돌 시 공식 기준 우선
```

---

## 1. 공통 실행 원칙

| 항목 | 기본 원칙 |
|------|-----------|
| 권장 Space | `BARAM 2026 Wind Research`를 기본으로 사용하되, 세션별 하위 주제 이름을 붙인다 |
| 권장 모델 | Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델 |
| 공식/1차 출처 우선 | Dacon 공식 대회 페이지, Dacon 규칙/평가/데이터/공지/토론, 공식 GitHub, 공식 model card, 기관 공식 문서, 법령/제도 문서를 우선한다 |
| 금지 | 블로그, 기사, Reddit, Medium, Scribd, LinkedIn, 비공식 mirror를 공식 사실처럼 쓰지 않는다 |
| 충돌 처리 | 공식/워크숍/1차 출처와 Perplexity 주장이 다르면 `충돌`로 표시하고 설계 반영을 보류한다 |
| 미공개 처리 | 데이터 공개 전 단정할 수 없는 항목은 `재검증`으로 표시한다 |
| 결과 언어 | 한국어. 기술 용어와 공식 모델명은 원문 병기 가능 |

### 1.1 업로드 기본 세트

모든 세션은 아래 파일을 기본 업로드한다.

| 파일 | 이유 |
|------|------|
| `docs/groundwork/01-strategy-prd.md` | 워크숍 기반 데이터 팩트 레저와 평가/규정 가정 |
| `docs/groundwork/02-perplexity-research-synthesis.md` | 1회차 Perplexity 재분류와 2차 질문 후보 |
| `docs/design/02-data-modeling-spec.md` | 피처, validation, metric, Perplexity 운영 기준 |
| `README.md` | 대회 개요와 현재 프로젝트 상태 |

세션 R2-3과 R2-4는 보유 중이면 워크숍 원본 사진 또는 `chronos_wind_power_demo.ipynb`를 추가 업로드한다.
공식 데이터 파일은 외부 업로드 규칙이 확정되기 전까지 업로드하지 않는다.

---

## 2. 공통 결과 표 형식

각 세션 결과는 아래 표를 반드시 포함하도록 요구한다.

| claim_id | 검증 항목 | 분류(공식/외부/충돌/재검증/추론) | Perplexity 요약 | 공식/1차 근거 | 보조 근거 | 충돌/불확실성 | 설계 반영 조치 |
|----------|-----------|----------------------------------|-----------------|---------------|-----------|----------------|----------------|
| R2-x-001 | 확인할 주장 | 공식 | 요약 | URL 또는 업로드 문서 위치 | 필요 시 | 없음/있음 | 반영/보류/추가 질의 |

분류 기준:

| 분류 | 의미 |
|------|------|
| 공식 | Dacon 공식 페이지, 공식 규칙, 공식 평가 페이지, 공식 공지, 공식 FAQ, 워크숍 원본 자료에서 확인 |
| 외부 | 논문, 기관 문서, 공식 모델 카드, 공식 GitHub, 제도 문서 등 대회 외부 출처에서 확인 |
| 충돌 | 공식/워크숍/1차 출처와 Perplexity 주장 또는 외부 출처가 다름 |
| 재검증 | 데이터 공개, 규칙 공개, FAQ 답변, 파일 메타데이터 확인 전에는 단정 불가 |
| 추론 | 공식값에서 계산하거나 일반 원리를 대회 상황에 적용한 2차 판단 |

---

## 3. 세션 요약

| 세션 | 목적 | 권장 모드 | 심층 리서치 | Computer |
|------|------|-----------|-------------|----------|
| R2-1 | 공식 평가 산식 재확인 | Deep Research 또는 Pro Search | 사용 | 원칙적으로 미사용 |
| R2-2 | 외부 데이터 규칙 추적 | Research mode 또는 Pro Search | 사용 | 필요 시만 사용 |
| R2-3 | 워크숍 자료와 Perplexity 주장 대조 | Research mode | 사용 | 미사용 |
| R2-4 | Chronos-2 공식성 검증 | Pro Search 또는 Deep Research | 사용 | 미사용 |
| R2-5 | LDAPS/GFS 공식 사양 검증 | Deep Research | 사용 | 미사용 |
| R2-6 | KPX 정산제도와 Dacon 평가 산식 분리 | Deep Research 또는 Research mode | 사용 | 필요 시만 사용 |

---

## 4. R2-1 공식 평가 산식 재확인

### 실행 설정

| 항목 | 설정 |
|------|------|
| 권장 Space | `BARAM 2026 Wind Research / R2-1 Official Evaluation` |
| 권장 모드 | Deep Research 우선, 빠른 재확인만 할 때 Pro Search |
| 권장 모델 | Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델 |
| 심층 리서치 사용 여부 | 사용 |
| Computer 도구 사용 여부 | 원칙적으로 미사용. Dacon 공식 페이지가 검색/링크로 열리지 않을 때만 사용 |
| 업로드할 파일 | 기본 업로드 세트 4개 |
| 공식/1차 출처 우선 조건 | Dacon 대회 설명, 평가, 규칙, 데이터, 공지, FAQ/토론의 공식 답변을 최우선으로 사용 |
| 결과 표 형식 | 공통 결과 표 + 평가 산식 세부 표 |

### 프롬프트

```text
당신은 Dacon BARAM 2026 풍력발전량 예측 AI 경진대회의 2차 검증 리서치를 돕고 있습니다.

Perplexity 결과는 대회 공식 사실이 아니며, 공식 데이터/규칙과 충돌 시 공식 기준 우선.

[실행 설정]
- Space: BARAM 2026 Wind Research / R2-1 Official Evaluation
- 권장 모드: Deep Research. 빠른 공식 페이지 재확인만 할 경우 Pro Search
- 권장 모델: Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델
- 심층 리서치 사용 여부: 사용
- Computer 도구 사용 여부: 원칙적으로 사용하지 않음. Dacon 공식 페이지가 검색/링크로 확인되지 않을 때만 사용
- 업로드 파일: 01-strategy-prd.md, 02-perplexity-research-synthesis.md, 02-data-modeling-spec.md, README.md

[목표]
Dacon 공식 대회 페이지를 기준으로 다음 항목을 재확인해 주세요.
1. nMAE 또는 1-NMAE 산식
2. 정산금획득률 정의와 Public/Private Score 산정 기준
3. Total Score 또는 최종 순위 산정 방식
4. 최종 제출 파일 선택 방식
5. 1일 제출 횟수, 사용 가능 언어, 코드 재현성 요구
6. 외부 데이터와 사전학습모델 관련 공식 규칙 중 평가 산식에 영향을 주는 항목

[공식/1차 출처 우선 조건]
- Dacon 공식 대회 설명/평가/규칙/데이터/공지/FAQ/토론의 공식 운영자 답변을 우선하세요.
- 과거 대회, KPX 실제 제도, 블로그, 기사, 커뮤니티 글은 공식 사실로 분류하지 마세요.
- 공식 페이지에서 "추후 공개"라고 되어 있으면 반드시 재검증으로 분류하세요.

[결과 표 형식]
먼저 아래 표를 작성하세요.
| claim_id | 검증 항목 | 분류(공식/외부/충돌/재검증/추론) | Perplexity 요약 | 공식/1차 근거 | 보조 근거 | 충돌/불확실성 | 설계 반영 조치 |

그 다음 평가 산식 세부 표를 작성하세요.
| 항목 | 공식 산식/문구 | 확정 여부 | 출처 URL | 1회차 synthesis와의 차이 | 설계 반영 |

[주의]
- 산식은 임의로 완성하지 말고 공식 문구가 있는 범위만 적으세요.
- 6%/8%, 4%/6% 같은 임계값은 Dacon 공식 평가 기준인지 KPX 제도인지 분리하세요.
- 답변은 한국어로 작성하세요.
```

---

## 5. R2-2 외부 데이터 규칙 추적

### 실행 설정

| 항목 | 설정 |
|------|------|
| 권장 Space | `BARAM 2026 Wind Research / R2-2 External Data Rules` |
| 권장 모드 | Research mode 또는 Pro Search |
| 권장 모델 | Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델 |
| 심층 리서치 사용 여부 | 사용 |
| Computer 도구 사용 여부 | 필요 시만 사용. 공지/FAQ/토론 페이지의 숨은 답변 탐색에 한정 |
| 업로드할 파일 | 기본 업로드 세트 4개 |
| 공식/1차 출처 우선 조건 | Dacon 규칙, 데이터, 공지, FAQ/토론 공식 답변을 최우선으로 사용 |
| 결과 표 형식 | 공통 결과 표 + 외부 데이터 허용/금지 표 |

### 프롬프트

```text
당신은 Dacon BARAM 2026 대회의 외부 데이터 규칙을 추적하는 검증 세션을 수행합니다.

Perplexity 결과는 대회 공식 사실이 아니며, 공식 데이터/규칙과 충돌 시 공식 기준 우선.

[실행 설정]
- Space: BARAM 2026 Wind Research / R2-2 External Data Rules
- 권장 모드: Research mode 또는 Pro Search
- 권장 모델: Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델
- 심층 리서치 사용 여부: 사용
- Computer 도구 사용 여부: 필요 시만 사용. Dacon 공지/FAQ/토론 공식 답변 탐색에 한정
- 업로드 파일: 01-strategy-prd.md, 02-perplexity-research-synthesis.md, 02-data-modeling-spec.md, README.md

[목표]
Dacon 공식 규칙/데이터/공지/FAQ/토론에서 외부 데이터 세부 규칙이 새로 공개되었는지 확인해 주세요.
다음 항목을 반드시 확인하세요.
1. 외부 데이터 사용 가능 여부
2. 공개성, 무료성, 라이선스, 재현성 요구
3. 생성시각/공개시각/수집시각과 D-1 14:00 KST cutoff의 관계
4. 외부 API, 기상 API, 위성/재분석/관측 자료 사용 가능 여부
5. 공식 데이터 파일을 외부 도구 또는 Perplexity에 업로드해도 되는지에 관한 명시 규칙
6. 코드 제출 또는 2차 검증 시 외부 데이터 증빙 요구

[공식/1차 출처 우선 조건]
- Dacon 공식 규칙과 운영자 답변만 공식으로 분류하세요.
- KMA/NOAA/ECMWF 등 기관 자료는 데이터 후보의 외부 근거일 뿐, 대회 허용 규칙이 아닙니다.
- 규칙이 아직 없으면 "허용"으로 추론하지 말고 재검증으로 표시하세요.

[결과 표 형식]
먼저 아래 표를 작성하세요.
| claim_id | 검증 항목 | 분류(공식/외부/충돌/재검증/추론) | Perplexity 요약 | 공식/1차 근거 | 보조 근거 | 충돌/불확실성 | 설계 반영 조치 |

그 다음 외부 데이터 허용/금지 표를 작성하세요.
| 데이터 후보 | 공식 허용 여부 | 필요한 증빙 | cutoff 위험 | 라이선스/약관 위험 | 재현성 요구 | 현재 조치 |

[주의]
- ERA5, KMA API, NOAA 자료, 위성 자료 등은 후보로만 다루고, 공식 허용 전 파이프라인 구현을 제안하지 마세요.
- 공식 데이터 공개 전이므로 실제 대회 데이터 업로드는 보류한다고 명시하세요.
- 답변은 한국어로 작성하세요.
```

---

## 6. R2-3 워크숍 자료와 Perplexity 주장 대조

### 실행 설정

| 항목 | 설정 |
|------|------|
| 권장 Space | `BARAM 2026 Wind Research / R2-3 Workshop Crosscheck` |
| 권장 모드 | Research mode |
| 권장 모델 | Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델 |
| 심층 리서치 사용 여부 | 사용 |
| Computer 도구 사용 여부 | 미사용 |
| 업로드할 파일 | 기본 업로드 세트 4개. 보유 시 워크숍 원본 사진과 `chronos_wind_power_demo.ipynb` 추가 |
| 공식/1차 출처 우선 조건 | 업로드한 워크숍 원본 자료와 Dacon 공식 페이지를 우선하고, Perplexity 1회차 주장은 재검증 대상으로 취급 |
| 결과 표 형식 | 공통 결과 표 + 워크숍/Perplexity 대조표 |

### 프롬프트

```text
당신은 BARAM 2026 사전 워크숍 자료와 Perplexity 1회차 주장을 대조하는 검증 세션을 수행합니다.

Perplexity 결과는 대회 공식 사실이 아니며, 공식 데이터/규칙과 충돌 시 공식 기준 우선.

[실행 설정]
- Space: BARAM 2026 Wind Research / R2-3 Workshop Crosscheck
- 권장 모드: Research mode
- 권장 모델: Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델
- 심층 리서치 사용 여부: 사용
- Computer 도구 사용 여부: 사용하지 않음
- 업로드 파일: 01-strategy-prd.md, 02-perplexity-research-synthesis.md, 02-data-modeling-spec.md, README.md
- 추가 업로드 가능 파일: 보유 중인 워크숍 원본 사진, chronos_wind_power_demo.ipynb

[목표]
업로드 문서를 기준으로 워크숍 판독값과 Perplexity 1회차 주장을 대조해 주세요.
다음 항목을 반드시 확인하세요.
1. D-1 14:00 KST 예측 기준시점
2. 00UTC 기준 h016~h039 리드타임 판독
3. LDAPS 16개 격자, GFS 9개 격자 판독
4. Group 1/2/3 설비용량, 터빈 수, 터빈 모델
5. Group 1/2 label 2022-2024, Group 3 label 2023-2024 판독
6. SCADA/KPX label의 평가 기간 제공 여부
7. Public/Private 40:60, 정산금 임계값 등 공식 페이지와 워크숍 사이의 상태 차이

[공식/1차 출처 우선 조건]
- 업로드한 워크숍 원본 사진과 Dacon 공식 페이지를 1차 근거로 우선하세요.
- 사진에서 판독이 흐리거나 문구가 일부만 보이면 확정하지 말고 재검증 또는 충돌로 분류하세요.
- Perplexity 1회차 주장은 공식 근거가 아니라 비교 대상입니다.

[결과 표 형식]
먼저 아래 표를 작성하세요.
| claim_id | 검증 항목 | 분류(공식/외부/충돌/재검증/추론) | Perplexity 요약 | 공식/1차 근거 | 보조 근거 | 충돌/불확실성 | 설계 반영 조치 |

그 다음 워크숍/Perplexity 대조표를 작성하세요.
| 항목 | 워크숍/공식 기준 | Perplexity 1회차 주장 | 일치 여부 | 불확실성 | 다음 확인 |

[주의]
- 워크숍 사진에서 확인되지 않는 컬럼명이나 변수명은 만들지 마세요.
- 데모 노트북의 synthetic 데이터 구조를 실제 대회 데이터 구조로 승격하지 마세요.
- 답변은 한국어로 작성하세요.
```

---

## 7. R2-4 Chronos-2 공식성 검증

### 실행 설정

| 항목 | 설정 |
|------|------|
| 권장 Space | `BARAM 2026 Wind Research / R2-4 Chronos Eligibility` |
| 권장 모드 | Pro Search 또는 Deep Research |
| 권장 모델 | Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델 |
| 심층 리서치 사용 여부 | 사용 |
| Computer 도구 사용 여부 | 미사용 |
| 업로드할 파일 | `02-perplexity-research-synthesis.md`, `02-data-modeling-spec.md`, 보유 시 `chronos_wind_power_demo.ipynb`, 기본 세트의 규칙 관련 문서 |
| 공식/1차 출처 우선 조건 | Amazon Science 공식 GitHub, Hugging Face 공식 model card, AutoGluon 공식 문서/릴리스 노트, Dacon 공식 규칙을 우선 |
| 결과 표 형식 | 공통 결과 표 + 모델 적격성 판단표 |

### 프롬프트

```text
당신은 BARAM 2026 대회에서 Chronos-2 또는 Chronos 계열 모델을 사용할 수 있는지 공식성/적격성을 검증합니다.

Perplexity 결과는 대회 공식 사실이 아니며, 공식 데이터/규칙과 충돌 시 공식 기준 우선.

[실행 설정]
- Space: BARAM 2026 Wind Research / R2-4 Chronos Eligibility
- 권장 모드: Pro Search 또는 Deep Research
- 권장 모델: Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델
- 심층 리서치 사용 여부: 사용
- Computer 도구 사용 여부: 사용하지 않음
- 업로드 파일: 02-perplexity-research-synthesis.md, 02-data-modeling-spec.md, 01-strategy-prd.md, README.md
- 추가 업로드 가능 파일: chronos_wind_power_demo.ipynb

[목표]
Amazon Chronos, Chronos-Bolt, Chronos-2, AutoGluon-TimeSeries의 공식 자료를 기준으로
BARAM 2026 사용 적격성을 검증해 주세요.
다음 항목을 반드시 확인하세요.
1. Chronos-2가 공식적으로 존재하는 모델/패키지/가중치인지
2. 공식 가중치 공개일이 2026-07-05 이전인지
3. 라이선스와 상업/대회 사용 가능성
4. 로컬 또는 참가자 관리 서버에서 가중치를 직접 로드해 실행 가능한지
5. 원격 API 기반 추론이 필요한지 여부
6. covariate 또는 multivariate forecasting 지원 여부
7. AutoGluon에서 어떤 버전/문서로 지원되는지
8. LightGBM/CatBoost 같은 tabular NWP baseline 대비 위험

[공식/1차 출처 우선 조건]
- Amazon Science 공식 GitHub, 공식 논문/README, Hugging Face 공식 model card, AutoGluon 공식 문서, PyPI/릴리스 노트를 우선하세요.
- 블로그, 예시 노트북, 커뮤니티 글은 보조 근거로만 쓰세요.
- Dacon 규칙의 "2026-07-05 이전 공식 공개 오픈소스 가중치"와 "원격 API 추론 금지"에 맞춰 판단하세요.

[결과 표 형식]
먼저 아래 표를 작성하세요.
| claim_id | 검증 항목 | 분류(공식/외부/충돌/재검증/추론) | Perplexity 요약 | 공식/1차 근거 | 보조 근거 | 충돌/불확실성 | 설계 반영 조치 |

그 다음 모델 적격성 판단표를 작성하세요.
| 모델 | 공식 출처 | 가중치 공개일 | 라이선스 | 로컬 실행 가능 | 원격 API 필요 여부 | covariate 지원 | 대회 규칙 적격성 | 사용/보류 판단 |

[주의]
- "Chronos-2가 좋다" 같은 성능 주장을 공식 적격성과 섞지 마세요.
- 공식 공개일 또는 라이선스가 불명확하면 재검증으로 표시하세요.
- 답변은 한국어로 작성하세요.
```

---

## 8. R2-5 LDAPS/GFS 공식 사양 검증

### 실행 설정

| 항목 | 설정 |
|------|------|
| 권장 Space | `BARAM 2026 Wind Research / R2-5 NWP Official Specs` |
| 권장 모드 | Deep Research |
| 권장 모델 | Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델 |
| 심층 리서치 사용 여부 | 사용 |
| Computer 도구 사용 여부 | 미사용 |
| 업로드할 파일 | 기본 업로드 세트 4개 |
| 공식/1차 출처 우선 조건 | 기상청/KMA 공식 자료, NOAA/NCEP/NWS 공식 GFS 문서, 공식 parameter table, Dacon 공식/워크숍 자료를 우선 |
| 결과 표 형식 | 공통 결과 표 + LDAPS/GFS 사양표 |

### 프롬프트

```text
당신은 BARAM 2026에서 언급된 LDAPS와 GFS 기상예보 자료의 공식 사양을 1차 출처로 검증합니다.

Perplexity 결과는 대회 공식 사실이 아니며, 공식 데이터/규칙과 충돌 시 공식 기준 우선.

[실행 설정]
- Space: BARAM 2026 Wind Research / R2-5 NWP Official Specs
- 권장 모드: Deep Research
- 권장 모델: Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델
- 심층 리서치 사용 여부: 사용
- Computer 도구 사용 여부: 사용하지 않음
- 업로드 파일: 01-strategy-prd.md, 02-perplexity-research-synthesis.md, 02-data-modeling-spec.md, README.md

[목표]
KMA/기상청의 LDAPS 또는 관련 국지예보모델 자료와 NOAA/NCEP/NWS의 GFS 공식 자료를 기준으로
다음 항목을 검증해 주세요.
1. LDAPS의 일반적 해상도, 예보 주기, 주요 변수, 높이 레벨, 파일/격자 특성
2. GFS의 공식 해상도, 예보 주기, 주요 변수, 높이 레벨, 파일/격자 특성
3. 풍력 예측에 중요한 u/v wind, wind speed, wind direction, temperature, pressure, humidity, 80m/100m wind 관련 공식 변수
4. KMA 공개 LDAPS/GFS 사양과 Dacon 제공 데이터 사양을 동일시하면 안 되는 항목
5. 공식 데이터 공개 후 확인해야 할 file metadata 목록

[공식/1차 출처 우선 조건]
- 기상청/KMA 공식 문서, NOAA/NCEP/NWS 공식 문서, 공식 GRIB parameter table, 모델 공식 기술 문서를 우선하세요.
- Open-Meteo, 블로그, 튜토리얼, 비공식 데이터 포털은 보조 근거로만 쓰세요.
- 대회 제공 LDAPS/GFS의 실제 변수와 격자 수는 공식 데이터 공개 전까지 재검증으로 두세요.

[결과 표 형식]
먼저 아래 표를 작성하세요.
| claim_id | 검증 항목 | 분류(공식/외부/충돌/재검증/추론) | Perplexity 요약 | 공식/1차 근거 | 보조 근거 | 충돌/불확실성 | 설계 반영 조치 |

그 다음 LDAPS/GFS 사양표를 작성하세요.
| 자료 | 사양 항목 | 공식 일반 사양 | Dacon/워크숍 판독 | 대회 적용 확정 여부 | 공식 데이터 공개 후 확인 |

[주의]
- "일반 LDAPS/GFS 사양"과 "대회 제공 파일 사양"을 분리하세요.
- 변수명은 공식 데이터 공개 전까지 내부 컬럼명으로 단정하지 마세요.
- 답변은 한국어로 작성하세요.
```

---

## 9. R2-6 KPX 정산제도와 Dacon 평가 산식 분리

### 실행 설정

| 항목 | 설정 |
|------|------|
| 권장 Space | `BARAM 2026 Wind Research / R2-6 Settlement Separation` |
| 권장 모드 | Deep Research 또는 Research mode |
| 권장 모델 | Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델 |
| 심층 리서치 사용 여부 | 사용 |
| Computer 도구 사용 여부 | 필요 시만 사용. KPX/전력시장 공식 PDF 또는 법령 페이지 탐색에 한정 |
| 업로드할 파일 | 기본 업로드 세트 4개 |
| 공식/1차 출처 우선 조건 | Dacon 평가 페이지를 대회 산식의 최상위 기준으로 두고, KPX/전력시장 공식 제도 문서는 외부 제도 배경으로만 분리 |
| 결과 표 형식 | 공통 결과 표 + Dacon/KPX 분리표 |

### 프롬프트

```text
당신은 KPX 실제 정산제도와 Dacon BARAM 2026 평가 산식이 섞이지 않도록 분리 검증합니다.

Perplexity 결과는 대회 공식 사실이 아니며, 공식 데이터/규칙과 충돌 시 공식 기준 우선.

[실행 설정]
- Space: BARAM 2026 Wind Research / R2-6 Settlement Separation
- 권장 모드: Deep Research 또는 Research mode
- 권장 모델: Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델
- 심층 리서치 사용 여부: 사용
- Computer 도구 사용 여부: 필요 시만 사용. KPX/전력시장 공식 PDF 또는 법령 페이지 탐색에 한정
- 업로드 파일: 01-strategy-prd.md, 02-perplexity-research-synthesis.md, 02-data-modeling-spec.md, README.md

[목표]
Dacon 대회 평가 산식과 KPX 실제 재생에너지 발전량 예측 정산제도를 분리해 주세요.
다음 항목을 반드시 확인하세요.
1. Dacon 공식 평가 페이지가 말하는 정산금획득률 정의
2. Dacon Public/Private Score의 세부 정산 기준 공개 여부
3. 워크숍 자료의 6%/8% 임계값 판독 상태
4. KPX 최신 제도의 4%/6% 또는 다른 임계값이 실제 제도인지
5. 실제 KPX 제도 내용을 대회 평가 산식으로 오해하면 생기는 위험
6. 발표 배경으로 사용할 수 있는 제도 맥락과 모델 학습 산식으로 쓰면 안 되는 항목

[공식/1차 출처 우선 조건]
- Dacon 공식 평가 페이지와 공식 규칙을 대회 산식의 최상위 기준으로 두세요.
- KPX, 전력거래소, 전력시장운영규칙, 산업부 등 공식 제도 문서는 외부 제도 배경으로 분류하세요.
- Dacon 산식과 KPX 제도가 다르면 대회 모델링에는 Dacon 기준을 우선한다고 명시하세요.

[결과 표 형식]
먼저 아래 표를 작성하세요.
| claim_id | 검증 항목 | 분류(공식/외부/충돌/재검증/추론) | Perplexity 요약 | 공식/1차 근거 | 보조 근거 | 충돌/불확실성 | 설계 반영 조치 |

그 다음 Dacon/KPX 분리표를 작성하세요.
| 항목 | Dacon 대회 기준 | KPX 실제 제도 기준 | 관계 | 모델링 반영 | 발표 반영 | 재검증 필요 |

[주의]
- KPX 제도를 찾더라도 Dacon 평가 산식으로 자동 적용하지 마세요.
- 대회 공식 평가 기준이 추후 공개 상태이면 local simulator는 시나리오로만 유지한다고 제안하세요.
- 답변은 한국어로 작성하세요.
```

---

## 10. 결과 반입 체크리스트

2차 Perplexity 결과를 Codex 작업으로 가져올 때는 아래 조건을 확인한다.

| 체크 | 기준 |
|------|------|
| 세션 정보 | Space, 세션 ID, 날짜, 모드, 모델, 업로드 파일을 기록 |
| 출처 | 공식/1차 출처 URL이 없는 주장은 공식으로 분류하지 않음 |
| 충돌 | 워크숍/공식/1차 출처와 다른 주장은 충돌 표에 남김 |
| 재검증 | 공식 데이터 공개 후 확인할 항목을 별도 액션으로 분리 |
| 설계 반영 | 공식 또는 낮은 위험의 외부 리서치만 설계 후보로 반영 |
| 범위 제한 | 운영 마스터플랜 작성, 코드 구현, 모델링 파이프라인 생성으로 넘어가지 않음 |

### 10.1 반입 템플릿

```markdown
## Perplexity Round 2 Session Result

- Space:
- Session:
- Date:
- Mode/Model:
- Deep Research:
- Computer:
- Uploaded files:

### Classification Table
| claim_id | 검증 항목 | 분류(공식/외부/충돌/재검증/추론) | Perplexity 요약 | 공식/1차 근거 | 보조 근거 | 충돌/불확실성 | 설계 반영 조치 |
|----------|-----------|----------------------------------|-----------------|---------------|-----------|----------------|----------------|

### Citations
| Claim | Source | Reliability | Notes |
|-------|--------|-------------|-------|

### Follow-up Actions
1.
2.
3.
```

---

## 11. 결정 로그

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-06-28 | 2차 Perplexity 질문 패키지를 별도 groundwork 문서로 분리 | 1회차 synthesis 문서가 길어져 실제 실행 프롬프트를 분리 관리하기 위함 |
| 2026-06-28 | 모든 세션에 모델/모드/심층 리서치/Computer/업로드 파일/출처 우선 조건을 반복 명시 | Perplexity 세션별 실행 설정 누락 방지 |
| 2026-06-28 | 결과 표를 `공식/외부/충돌/재검증/추론` 분류로 고정 | Perplexity 답변을 공식 사실로 오인하지 않기 위함 |
| 2026-06-28 | 이번 문서는 질문 패키지 작성에서 멈춤 | AGENTS.md R3 `1작업-1정지` 준수 |
