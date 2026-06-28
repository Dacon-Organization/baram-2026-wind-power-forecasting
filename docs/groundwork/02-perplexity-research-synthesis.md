# Perplexity 리서치 종합: BARAM 2026 1회차

> 작성일: 2026-06-28 KST
> 상태: 공식 데이터 공개 전 리서치 반영 1회차
> 연결 문서: [전략 PRD](01-strategy-prd.md), [데이터·모델링 설계서](../design/02-data-modeling-spec.md)

---

## 0. 적용 원칙

**Perplexity 결과는 대회 공식 사실이 아니며, 공식 데이터/규칙과 충돌 시 공식 기준 우선**이다.

이번 문서는 사용자가 제공한 Perplexity 결과와 다운로드 원문 보고서를 기존 워크숍 기반 문서와 대조해
다음 상태로 다시 분류한다.

| 상태 | 의미 | 사용 방식 |
|------|------|-----------|
| 확정 | Dacon 공식 페이지, 공식 규칙, 공식 평가 페이지, 워크숍 판독 등 기존 근거와 충돌 없음 | 설계 기준으로 반영 |
| 외부 리서치 | 논문, 기관 문서, 모델 카드, 블로그, 기사 등 대회 외부 근거 | 실험 후보로만 반영 |
| 충돌 | 기존 워크숍/공식 문서와 다르거나 Perplexity 세션끼리 불일치 | 공식 FAQ 또는 데이터 공개 후 확인 |
| 공식 공개 후 재검증 | 대회 데이터/규칙 탭 공개 전에는 단정 위험 | 체크리스트와 질문 목록에 보관 |
| 추론 | 근거에서 파생한 계산, 일반화, 대회 적용 가정 | 반드시 추론으로 표시 |

---

## 1. 검토한 입력 자료

| 입력 | 내용 | 재분류 메모 |
|------|------|-------------|
| P0-1 공식 규정·데이터 누수 보고서 | 공식 페이지, 규칙, 데이터 누수 위험 | 유용하나 일부 과거 대회/포럼 근거가 섞임 |
| P0-2 NWP 후처리 보고서 | MOS, grid bias correction, hub-height, wake, 모델 비교 | 대부분 외부 리서치 후보 |
| P0-3 LDAPS/GFS grid feature 보고서 | LDAPS/GFS 사양, 변수, 격자 매핑, lead time | 대회 제공 변수와 외부 공개 변수 구분 필요 |
| P0-4 Validation 보고서 | rolling-origin, seasonal holdout, LB 과적합 방지 | 설계 반영 가치 높음. 수치 주장은 재검증 |
| P1-1 Chronos 보고서 | Chronos, Chronos-Bolt, Chronos-2 적합성 | Chronos-2 주장 일부는 공식 출처 재확인 필요 |
| P1-2 정산금 보고서 | 정산금획득률, 임계값, 비대칭 손실, 후처리 | 대회 공식 산식과 KPX 실제 제도를 분리해야 함 |
| P2-1 시장 맥락 보고서 | 전력시장, 출력제어, 예측제도, 발표 문장 | 발표 배경용. 풍력 단독 효과 과장 금지 |
| `chronos_wind_power_demo.ipynb` | Chronos-Bolt zero-shot synthetic demo | 실제 대회 데이터 구조 아님. 데모/아이디어로만 사용 |

주의: 사용자가 붙여준 요약에서 P0-1과 P2-1의 내용이 일부 뒤섞여 보인다.
따라서 세션 번호보다 원문 보고서의 실제 주제와 출처 품질을 기준으로 반영했다.

---

## 2. 공식/1차 출처로 확인된 사실

| 항목 | 상태 | 근거 | 설계 반영 |
|------|------|------|-----------|
| 대회 주제는 기상청 기상예보 데이터와 풍력발전량 데이터 기반 예측 | 확정 | [Dacon 대회 설명](https://dacon.io/competitions/official/236727/overview/description) | 문제 정의 유지 |
| 대회 기간은 2026-07-06 10:00 ~ 2026-08-14 10:00 | 확정 | [Dacon 대회 설명](https://dacon.io/competitions/official/236727/overview/description) | README/PRD 일정 유지 |
| 1차 온라인 평가는 평균 예측오차율(nMAE)과 정산금획득률 기반 | 확정 | [Dacon 대회 설명](https://dacon.io/competitions/official/236727/overview/description) | metric 설계에 두 지표 병행 |
| 정산금획득률 정의는 `정산금획득금액 / 이론상최대정산가능금액 * 100` | 확정 | [Dacon 평가 페이지](https://dacon.io/competitions/official/236727/overview/evaluation) | local simulator 인터페이스에 반영 |
| Public/Private Score의 정산 기준은 추후 공개 | 공식 공개 후 재검증 | [Dacon 평가 페이지](https://dacon.io/competitions/official/236727/overview/evaluation) | 6/8, 4/6 기준 모두 시나리오로 보관 |
| 데이터는 2026-07-06 10:00 공개 예정 | 확정 | [Dacon 데이터 페이지](https://dacon.io/competitions/official/236727/data) | 컬럼/기간 단정 금지 |
| Python만 허용, 1일 최대 제출 5회, CSV UTF-8 제출 | 확정 | [Dacon 규칙 페이지](https://dacon.io/competitions/official/236727/overview/rules) | 제출 운영 원칙 유지 |
| 외부 데이터 관련 사항은 추후 공개 | 공식 공개 후 재검증 | [Dacon 규칙 페이지](https://dacon.io/competitions/official/236727/overview/rules) | 외부 데이터 파이프라인 보류 |
| 2026-07-05 이전 공개 오픈소스 가중치만 사전학습모델로 사용 가능 | 확정 | [Dacon 규칙 페이지](https://dacon.io/competitions/official/236727/overview/rules) | model registry 필수 |
| API 기반 원격 모델 추론 금지 | 확정 | [Dacon 규칙 페이지](https://dacon.io/competitions/official/236727/overview/rules) | Hugging Face Inference API 등 제외 |
| Private 랭킹은 최종 순위가 아님 | 확정 | [Dacon 규칙 페이지](https://dacon.io/competitions/official/236727/overview/rules) | 코드 재현성과 발표 평가까지 관리 |

---

## 3. 외부 리서치 기반 모델링 아이디어

### 3.1 피처 설계

| 후보 | 상태 | 필요 조건 | 반영 판단 |
|------|------|-----------|-----------|
| `wind_dir_sin`, `wind_dir_cos` | 외부 리서치 | 풍향 또는 u/v 제공 | P0 후보. 누수 위험 낮음 |
| u/v 성분 기반 `wind_speed`, `wind_direction` | 외부 리서치 | u/v 컬럼 제공, 방향 convention 확인 | P0 후보 |
| `wind_speed^2`, `wind_speed^3` | 외부 리서치 | 풍속 컬럼 제공 | P0 후보. power curve 구간 학습용 |
| `temperature`, `pressure`, `humidity` 기반 `air_density` | 외부 리서치 | 단위 확인 필요 | P1 후보 |
| `wind_power_density = 0.5 * rho * v^3` | 외부 리서치 | 공기밀도 계산 가능 | P1 후보 |
| grid `mean/std/max/min` | 외부 리서치 | LDAPS/GFS 격자별 변수 제공 | P0/P1 후보 |
| nearest/bilinear/IDW 매핑 | 외부 리서치 | grid 좌표와 단지/그룹 좌표 필요 | 좌표 공개 후 적용 |
| `lead_hour`, `issue_time`, `valid_time` | 외부 리서치 | 예보 기준시각/대상시각 제공 | cutoff 검증과 함께 P0 |
| multi-run forecast spread | 외부 리서치 | 동일 target에 복수 run 존재 | 미래 issue time 누수 검증 후 P1 |
| hub-height extrapolation | 외부 리서치 | 10m/50m/80m/100m 바람, 허브 높이 확인 | 임의 alpha 금지 |
| wake effect, terrain/RIX | 공식 공개 후 재검증 | 터빈 배치/DEM/좌표 필요 | 공식 데이터 전 사용 보류 |

### 3.2 Validation

| 후보 | 상태 | 반영 판단 |
|------|------|-----------|
| Rolling-origin expanding window | 외부 리서치 | 기본 CV 후보로 반영 |
| 2024 전체 holdout | 추론 | 2025 평가와 유사한 1년 holdout proxy |
| 계절별 fold | 외부 리서치 | Public/Private 계절성 불확실성 대응 |
| Purged/embargo gap | 외부 리서치 | lag/rolling feature 사용 시 보조 실험 |
| Random K-Fold 금지 | 확정/외부 리서치 | 워크숍 cutoff 원칙과 시계열 인과성상 금지 |
| Public LB 점수 단독 최적화 금지 | 확정/외부 리서치 | 제출 5회 제한, Private/2차 검증 구조상 필요 |

### 3.3 Chronos/AutoGluon

| 후보 | 상태 | 판단 |
|------|------|------|
| Chronos-Bolt zero-shot | 외부 리서치 | 데모 baseline 가능. NWP 외생변수 직접 반영 한계 |
| Chronos-Bolt + covariate regressor | 외부 리서치 | AutoGluon 버전별 지원 확인 후 P1/P2 |
| Chronos-2 | 외부 리서치/공식 공개 후 재검증 | covariate 지원 후보이나 가중치 공개일, 라이선스, 로컬 실행성 재확인 필요 |
| AutoGluon-TimeSeries | 외부 리서치 | 내부 validation window와 stacking 누수 확인 필요 |
| LightGBM/CatBoost/XGBoost | 외부 리서치 | NWP tabular baseline의 1차 주력 유지 |

`chronos_wind_power_demo.ipynb`는 synthetic 10분 발전량을 만든 뒤 Chronos-Bolt로 24시간 zero-shot을 수행하는 데모다.
실제 BARAM 데이터의 그룹별 NWP/SCADA/KPX 구조를 검증하지 않으므로, 모델 적합성 증거가 아니라 워크숍 예시로만 본다.

### 3.4 정산금 최적화

| 후보 | 상태 | 반영 판단 |
|------|------|-----------|
| local nMAE 구현 | 확정 | 공식 산식과 단위 공개 후 구현 |
| 정산금획득률 simulator | 공식 공개 후 재검증 | 공식 정산 기준 공개 후 구현 확정 |
| 6%/8% 임계 시나리오 | 워크숍 근거/추론 | 기존 워크숍 판독 기준으로 보관 |
| 4%/6% 임계 시나리오 | 외부 리서치/충돌 | 최신 KPX 제도 후보. 대회 적용 여부 미확정 |
| capacity clipping | 외부 리서치 | 물리 범위 보정으로 P0 |
| quantile/pinball loss | 외부 리서치 | 정산 기준 공개 후 P1 |
| conservative scaling | 외부 리서치 | CV 기반으로만 결정. LB 기반 튜닝 금지 |
| bias correction/isotonic calibration | 외부 리서치 | OOF 기반 학습. test 통계 사용 금지 |

---

## 4. 충돌 또는 주의해야 할 항목

| 항목 | Perplexity 주장 | 기존/공식 기준 | 조치 |
|------|-----------------|----------------|------|
| P0-1 요약 내용 | 시장/발표 맥락으로 작성됨 | P0-1은 공식 규정·누수 확인 세션이어야 함 | 세션 라벨 혼선으로 기록 |
| Public/Private 40:60 | 워크숍 판독 또는 Perplexity 주장 | Dacon 공식 평가 페이지는 정산 기준 추후 공개 | 공식 사실로 쓰지 않음 |
| 외부 데이터 사용 가능성 | ERA5, KMA API, 위성 등 후보 | Dacon 규칙은 외부 데이터 추후 공개 | 파이프라인 보류 |
| 정산금 임계값 | 6/8 또는 4/6 기준 혼재 | Dacon은 기준 추후 공개, 워크숍은 6/8로 판독 | 두 시나리오 모두 준비 |
| Chronos-2 1순위 주장 | NWP covariate 지원으로 최우선 | 기존 설계는 tabular NWP 모델 1차 주력 | Chronos-2는 P1 후보로 낮춤 |
| LDAPS UM->KIM/LDPS 전환 | Open-Meteo 등 외부 근거 | 대회 제공 데이터가 무엇인지는 미공개 | 공식 파일 메타로 확인 |
| LDAPS/GFS 변수명 | KMA/NOAA 공개 데이터 변수 목록 | 대회 제공 컬럼과 다를 수 있음 | 실제 컬럼 공개 후 매핑 |
| Scribd/Medium/Reddit/LinkedIn 근거 | 공식 또는 준공식처럼 인용 | 1차 출처로 부적합한 경우 많음 | 외부 리서치 또는 참고로 강등 |
| 발전소 위치/터빈 메타데이터 외부 추정 | 모델링에 유용할 수 있음 | 외부 데이터 규칙 미공개 | 워크숍 제공 스펙 외 사용 보류 |

---

## 5. 2차 Perplexity 질문 후보

아래 세션은 기존 워크숍 자료와 이번 synthesis 문서를 업로드한 뒤 수행한다.
Computer 도구는 공식 페이지/PDF 탐색이 검색만으로 실패할 때만 사용한다.

| 세션 | 권장 모드/모델 | 심층 리서치 | Computer | 질문 목적 |
|------|----------------|------------|----------|-----------|
| R2-1 공식 평가 산식 재확인 | Research mode 또는 Pro Search, 최신 reasoning 모델 | 사용 | 원칙적으로 미사용 | Dacon 평가 페이지의 nMAE, 정산금획득률, Public/Private 기준 추후 공개 상태 확인 |
| R2-2 외부 데이터 규칙 추적 | Research mode 또는 Pro Search | 사용 | 필요 시만 사용 | 규칙 탭/FAQ/토론에서 외부 데이터 세부 공지가 새로 나왔는지 확인 |
| R2-3 워크숍 자료 대조 | Research mode, 긴 문서 비교 강한 모델 | 사용 | 미사용 | D-1 14:00, h016~h039, grid 수, group label 기간과 Perplexity 주장 충돌 확인 |
| R2-4 Chronos-2 공식성 검증 | Pro Search, 코드/공식 문서 강한 모델 | 사용 | 미사용 | 가중치 공개일, 라이선스, covariate 지원, AutoGluon 지원 버전 확인 |
| R2-5 LDAPS/GFS 공식 사양 검증 | Research mode, 기관 문서 우선 | 사용 | 미사용 | KMA/NOAA 1차 출처만으로 사양과 변수 정리 |
| R2-6 정산금 기준 제도 대회 적용성 | Research mode, 공식/법령 문서 우선 | 사용 | 필요 시만 사용 | KPX 최신 제도와 Dacon 대회 평가 산식의 차이 분리 |

### R2-1 프롬프트 초안

```text
[실행 설정]
- Space: BARAM 2026 Wind Research
- 모드: Research mode 또는 Deep Research
- 모델: Sonar Deep Research가 있으면 사용, 없으면 최신 reasoning 모델
- Computer 도구: 사용하지 않음. Dacon 공식 페이지가 검색으로 확인되지 않을 때만 사용
- 업로드: 01-strategy-prd.md, 02-data-modeling-spec.md, 02-perplexity-research-synthesis.md

질문:
DACON BARAM 2026 공식 평가 페이지와 규칙 페이지를 기준으로,
nMAE, 정산금획득률, Public/Private Score 기준, 최종 순위 산정, 외부 데이터 규칙을 재확인해 주세요.

반드시 구분:
1. 공식 페이지 원문으로 확인된 사실
2. 사전 워크숍 자료에서만 확인된 사실
3. 과거 대회 또는 KPX 실제 제도에서 가져온 참고 정보
4. 아직 추후 공개 또는 미확정인 항목

표에는 항목, 상태(확정/외부 리서치/충돌/공식 공개 후 재검증/추론), 근거 URL, 설계 반영 주의사항을 포함하세요.
```

---

## 6. 설계 문서 반영 결정

| 반영 위치 | 결정 |
|-----------|------|
| `02-data-modeling-spec.md` 목적 | Perplexity 1회차 synthesis 링크 추가 |
| 피처 설계 | wind direction sin/cos, speed power, air density, spatial stats, lead features를 후보로 보강 |
| validation | rolling-origin + seasonal holdout + public overfit guardrail을 강화 |
| Chronos/AutoGluon | Chronos-2는 P1 후보, Chronos-Bolt는 보조 baseline으로 재분류 |
| metric | 정산금획득률 공식 정의만 확정으로 두고, 임계값은 시나리오 처리 |
| 외부 출처 주의 | 비공식 미러/블로그/소셜 링크는 공식 근거로 승격하지 않음 |

---

## 7. 결정 로그

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-06-28 | Perplexity 결과를 공식 사실이 아닌 리서치 후보로 재분류 | 워크숍 자료 없이 수행된 리서치라 충돌 가능성이 큼 |
| 2026-06-28 | Chronos-2를 1순위 주력이 아닌 P1 실험 후보로 둠 | tabular NWP baseline이 대회 구조에 더 직접적이고 재현성이 높음 |
| 2026-06-28 | 정산금 임계값은 6/8, 4/6 시나리오 모두 보관 | Dacon 공식 Public/Private 기준이 추후 공개 상태 |
| 2026-06-28 | 외부 데이터 파이프라인은 규칙 공개 전 보류 | 외부 데이터 규칙이 공식적으로 미확정 |
