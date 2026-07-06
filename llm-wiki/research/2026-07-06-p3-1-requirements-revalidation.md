## Perplexity 세션 결과

- 세션: P3-1 요구사항 정의 재검증
- 날짜: 2026-07-06 (KST)
- 모드/모델: Computer (공식 페이지 브라우징 + 첨부 문서 대조)
- 업로드 파일: `01-problem-definition.md`, `02-requirements.md`, `04-final-solution-blueprint.md`, `04-versioning-recovery.md`, `00-source-map.md`, `01-strategy-prd.md`, `02-data-modeling-spec.md`, `02-perplexity-research-synthesis.md`, `03-market-research.md`, `2026 BARAM 경진대회 워크숍.md`, `풍력발전량 예측 AI 경진대회.pdf`

> 대회 데이터(open.zip)를 외부에 업로드했다고 가정하지 않았습니다. 아래 데이터 관련 수치(행 수, 컬럼)는 첨부 로컬 문서(`04-final-solution-blueprint.md`)의 로컬 감사 결과이며 공식 페이지 원문이 아닙니다. 공식 페이지에서 새로 확인된 사실은 별도 표기했습니다.

---

### 1. 공식 사실

| 항목 | 내용 | 출처 URL 또는 첨부 문서 | 설계 영향 |
|---|---|---|---|
| 평가 산식 | `Score = 0.5 × (1-NMAE) + 0.5 × FICR` | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | `metrics.py` 재현 기준 확정 |
| NMAE 정의 | 그룹별 NMAE = 평균(\|예측−실제\| / **그룹 설비용량**), 1-NMAE = 1 − 3개 그룹 NMAE 평균 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 정규화 분모는 그룹 capacity 고정 |
| 유효 시간대 | **실제 발전량이 설비용량의 10% 이상**인 시간대만 평가 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | actual 기준 valid mask (test에서는 미지) |
| FICR 정산 구간 | nMAE ≤6% → 4원/kWh, 6%<nMAE≤8% → 3원/kWh, >8% → 0원 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | FICR simulator 단가 확정 (6/8 기준, 4/3/0원) |
| FICR 정의 | 그룹별 FICR = 획득 정산금 / 이론상 최대 정산금, FICR = 3개 그룹 평균 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 이론상 최대 = 모든 유효시간 4원/kWh 가정 |
| **Public/Private 분할** | **Public = 사전 샘플링 40%, Private = 나머지 60%** | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 40:60 **공식 확정** (기존 "추론/추후공개"에서 승격) |
| 1차 최종 평가 | 리더보드 **Private Score 100%** | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | Public 과적합 방지가 필수 |
| **2차 진출 구조** | Private 상위 **30팀(예비 10 포함)** 산출물 제출 → 검증 통과 **상위 20팀** 오프라인 발표 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 상위 30 진입 시 산출물 완비 필요 |
| 최종 수상 | 1차 Private 50% + 2차 발표 50% 합산 상위 10팀 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | Private과 발표 모두 관리 |
| train/inference 분리 | Private Score 복원 가능한 코드 필수, **학습·추론 코드 반드시 분리**(.py/.ipynb) | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | FR-02 공식 근거 확정 |
| 코드 인코딩 | 코드·주석 **UTF-8**, 모든 코드 오류 없이 실행, OS·라이브러리 버전 기재 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 환경 명세 문서화 필수 |
| 발표 자료 | 10분 분량 **PDF만 허용(PPT 불가)** | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 산출물은 PDF로 고정 |
| **참가자격 증빙** | 재학/휴학증명서 등 팀원 전체 서류, 취준생은 건강보험자격득실확인서 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | **신규**: 산출물에 서류 포함 |
| Data Leakage 원칙 | 예측기준시점 이전에 **생성·공개·확정되어 실제 활용 가능**했던 정보만 사용, 파생·통계·보간값도 동일 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) | cutoff는 "대상 시각"이 아닌 "활용 가능 시각" 기준 |
| 외부 데이터 | 법적 제약 無 + 공개 접근 가능 + 라이선스 준수 + leakage 규칙 준수 시 허용, 재현 의무·출처·수집시점 제출 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) | **조건부 허용 확정** (기존 "추후 공개/보류"에서 승격) |
| 사전학습 모델 | **2026-07-05까지** 공식 가중치 공개된 오픈소스만 사용 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) | model registry 필수, 공개일 기록 |
| API 추론 금지 | OpenAI/Gemini/HF Inference API 등 원격 추론 금지, 로컬 가중치 로드만 허용 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) | MODEL-06 확정 |
| 제출 운영 | Python만, **1일 5회**, CSV UTF-8, 최종 채점 파일 1개 직접 선택 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) | 제출 ledger + 최종 파일 선택 확인 |
| 팀 규칙 | **최대 3명**, 동일인 중복 등록 불가, 팀 병합 마감 **08.07** | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) · [개요](https://dacon.io/competitions/official/236727/overview/description) | 팀 구성은 8/7 이전 확정 |
| 제출 파일 | sample_submission.csv, **8,760행**, 컬럼: `forecast_id`(forecast_0001~8760), `forecast_kst_dtm`, `kpx_group_1/2/3` | [DACON 데이터](https://dacon.io/competitions/official/236727/data) | 컬럼명·순서·행수 계약 확정 |
| **제출 시작 시각** | sample_submission 시작이 **2024-12-31 08:00**로 표기됨 | [DACON 데이터](https://dacon.io/competitions/official/236727/data) | 평가기간 시각 정의 재검증 필요(아래 6번) |
| 일정 | 대회 07.06~08.14 10:00 마감, **산출물 제출 ~08.17 10:00**, 검증 ~08.21, 발표 08.28, 시상 09.04 | [DACON 개요](https://dacon.io/competitions/official/236727/overview/description) · [평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 마감·산출물 이중 데드라인 관리 |
| 주최/상금 | 주최 한국동서발전·GS E&R·태백가덕산풍력발전, 운영 데이콘, 상금 2,000만 원 | [DACON 개요](https://dacon.io/competitions/official/236727/overview/description) | 발표 배경 서술용 |

---

### 2. 로컬 프로젝트 결정과 비교

| 현재 결정 | 유지/수정/보류 | 근거 | 필요한 후속 작업 |
|---|---|---|---|
| FICR 6/8%·4/3/0원, 유효시간 10% (`04-final-solution-blueprint.md` §0) | **유지 (공식 확정으로 승격)** | 공식 평가 페이지와 완전 일치 | `metrics.py`에 상수 하드코딩 + 출처 주석 |
| Public/Private를 "40:60 추론/추후공개"로 표기 (`02-perplexity-research-synthesis.md` §4, `02-data-modeling-spec.md` §6.3) | **수정 → 공식 확정** | 공식 평가 페이지 40:60 명시 | 문서 전반의 "추후 공개/추론" 라벨을 "공식 확정"으로 갱신 |
| 정산 임계 "6/8 vs 4/6 두 시나리오 보관" (`02-perplexity-research-synthesis.md` §3.4) | **수정 → 6/8·4/3/0원 단일 확정** | 공식 페이지가 6/8%·4/3/0원으로 확정 | 4/6 시나리오 코드/문서 제거 또는 폐기 표시 |
| 외부 데이터 "규칙 공개 전 보류" (`02-requirements.md` DATA-05, `02-perplexity-research-synthesis.md`) | **수정 → 조건부 허용** | 공식 규칙 4항이 공개 데이터 조건부 허용 명시 | 외부 데이터 ledger(출처·수집시점·라이선스·활용가능시각·재현경로) 실제 운영 시작 |
| train/inference 분리 (FR-02) | **유지 (공식 필수 확정)** | 공식 평가 페이지 산출물 요건 | `train.py`/`inference.py` 진입점 분리 완료 |
| forecast lead를 `forecast_kst_dtm − data_available_kst_dtm` = 12~35h (`04-final-solution-blueprint.md` §2.3) | **유지 + 재검증** | 로컬 파일 감사 결과이며 공식 data_description 원문 미확인 | 공식 `data_description.md`로 lead·cutoff 정의 대조 |
| 평가 대상 8,760 = "2025년" (`01-problem-definition.md`, blueprint) | **재검증** | 공식 sample_submission 시작이 **2024-12-31 08:00**로 표기 → "2025년 전체"와 불일치 가능 | 실제 `forecast_kst_dtm` 범위(시작·종료·시간대) 로컬 확인 필요 |
| Group 3 2022 결측·capacity 초과 38건 (blueprint §2.2) | **유지** | 로컬 label 감사 결과 | validation fold 분리·capacity_violation_flag 유지 |
| baseline RandomForest는 제출 smoke용, 주력은 LightGBM/CatBoost (MODEL-01/02) | **유지** | 로컬 전략 결정, 규칙과 무충돌 | metric 재현 후 baseline .py 분리 |
| 1일 5회·최종 파일 1개 선택·Private 100% (SUB-01/04, MODEL-04) | **유지 (공식 확정)** | 공식 규칙·평가 페이지 일치 | 제출 ledger + "최종 선택 파일" 컬럼 운영 |
| 산출물 대상 = "상위권"으로만 서술 | **수정 → 구체화** | 공식: 상위 30팀(예비 10)→검증 20팀 | 목표를 "Private 30위 이내 진입 + 산출물 완비"로 명문화 |

---

### 3. 필수 요구사항

| 영역 | 요구사항 | 검증 방법 | 우선순위 |
|---|---|---|---|
| 평가 재현 | 공식 산식(0.5·(1-NMAE)+0.5·FICR)을 `metrics.py`로 구현, 그룹 capacity 정규화·10% 유효마스크·6/8%·4/3/0원 반영 | 공식 `평가_산식 코드.ipynb`와 동일 입력에서 오차 범위 내 일치(단위 테스트) | P0 |
| 학습/추론 분리 | `train.py`(모델 산출) ↔ `inference.py`(test→submission) 완전 분리, 공유 로직은 `src/baram/` | 두 진입점 독립 실행, 중간 산출물(model, config)만 인터페이스 | P0 |
| 제출 형식 계약 | 컬럼 `forecast_id, forecast_kst_dtm, kpx_group_1/2/3`, 8,760행, UTF-8, `forecast_id` 순서 = sample_submission | submission validator(행수·컬럼명·순서·인코딩·NaN·음수·capacity 초과 검사) | P0 |
| Data Leakage 방지 | 모든 피처가 "예측기준시점 이전 활용가능 정보"만 사용, 파생·통계·보간값 포함 | cutoff validator(피처별 활용가능시각 ≤ 예측기준시점) + leakage 체크리스트 | P0 |
| 재현성 기록 | 실험별 config·seed·git commit·데이터 SHA256, OS·라이브러리 버전 명세 | `outputs/experiments/<id>/config.yaml` + `MANIFEST.md` + `environment` 파일 존재 확인 | P0 |
| 물리 범위 점검 | 예측값 0~그룹 capacity clipping, 음수/초과 0건 | inference 후 자동 assert + 로그 | P1 |
| 모델 자격 준수 | 사전학습 모델은 2026-07-05 이전 공개 가중치만, API 추론 없음 | model registry(모델·가중치·라이선스·공개일·다운로드경로·로컬실행여부) | P1 |
| 외부 데이터 재현 | 사용 시 출처·수집시점·라이선스·활용가능시각·재현경로 기록, 코드만으로 재현 | external data ledger + 재현 스크립트 | P1 (사용 시) |
| 산출물 패키지 | Private 복원 코드+모델, 외부데이터, 발표 PDF, 참가자격 증빙서류 세트 | 산출물 체크리스트 dry-run(마감 08.17 10:00 기준) | P1 |
| Public 과적합 방지 | 최종 파일은 local time-based validation 우선, Public 단독 최적화 보류 | CV↔Public 괴리 추적 로그, 최종 후보 선택 규칙 문서화 | P1 |

---

### 4. 제출 및 복구 리스크

| 리스크 | 발생 조건 | 영향 | 예방/복구 방안 |
|---|---|---|---|
| 제출 파일 형식 오류 | 컬럼명/순서/행수/인코딩 불일치, `forecast_id` 정렬 어긋남 | 제출 실패 또는 오채점, 하루 5회 슬롯 낭비 | 제출 전 validator 강제 실행, sample_submission 스키마와 diff |
| 시각 정의 오해 | sample_submission 시작이 **2024-12-31 08:00**인데 "2025년 전체"로 가정 | test 매핑·유효기간·lead 계산 오류 → 점수 붕괴 | 실제 `forecast_kst_dtm` 범위 확인 후 test↔submission 조인 검증 |
| Private 복원 실패 | seed·config·데이터 hash·환경 미기록, 학습/추론 결합 코드 | 2차 산출물 검증 탈락(상위 30팀이라도) | commit+config+seed+MANIFEST 3중 기록, 클린 환경 재실행 리허설 |
| Leakage 실격 | 예측기준시점 이후 예보/실측/재분석·통계값 사용 | 즉시 실격 또는 평가 제외 | cutoff validator 자동화, 피처별 활용가능시각 소명표 준비 |
| 유효마스크 오재현 | valid mask를 예측값 기준으로 잘못 적용(공식은 actual 기준) | local score와 리더보드 괴리, 잘못된 튜닝 | metric 재현 시 actual 기준 마스크 명시, test는 마스크 미지 처리 |
| FICR 이론상 최대 오해 | 이론상 최대 정산금 정의를 잘못 구현 | FICR 과대/과소평가로 최적화 왜곡 | 공식 코드와 동일 입력에서 FICR 수치 일치 검증 |
| 산출물 마감 누락 | 08.14 마감과 **08.17 10:00 산출물 마감**을 혼동, 증빙서류·PDF 누락 | 검증 탈락, 발표 불가 | 이중 데드라인 캘린더 + 산출물 체크리스트(코드·모델·외부데이터·PDF·서류) |
| 최종 파일 미선택 | 자동 최고점 파일 ≠ 의도한 파일 | 원치 않는 파일 채점 | 마감 전 제출 창에서 최종 1개 수동 선택·스크린샷 |
| 팀 병합 마감 초과 | 08.07 이후 팀 변경 시도 | 팀 구성 확정 불가 | 팀 구성을 08.07 이전 완료 |
| 데이터 커밋 사고 | 원본 open.zip을 Git에 커밋 | 데이터 사용 제한 위반 | `.gitignore`+`data/README.md`, 원본 로컬 보관 |

---

### 5. 다음 72시간 백로그

| 순위 | 작업 | 완료 기준 | 관련 문서/코드 |
|---|---|---|---|
| 1 | `metrics.py` + `01_metric_reproduction.ipynb`로 공식 산식 재현 | 공식 `평가_산식 코드.ipynb`와 동일 입력에서 total/1-NMAE/FICR 오차범위 내 일치 | FR-01, blueprint §9 |
| 2 | 제출 시각 정의 재검증(`forecast_kst_dtm` 실제 범위·시간대·8,760 매핑) | 시작/종료 시각과 test 조인 규칙 문서화, 2024-12-31 08:00 표기 해석 확정 | 공식 데이터 페이지, blueprint §2.1 |
| 3 | submission validator 구현(컬럼·순서·행수·UTF-8·NaN·음수·capacity) | 잘못된 CSV 6종 자동 검출 통과 | FR-03, `04-versioning-recovery.md` |
| 4 | cutoff/leakage validator 초안(피처별 활용가능시각 ≤ 예측기준시점) | P0 피처 전부 통과, 소명표 컬럼 생성 | DATA-02, 규칙 3항 |
| 5 | train/inference 골격 분리 + baseline RandomForest 이식 | `train.py`→모델, `inference.py`→8,760행 제출, 2회 실행 동일 결과 | FR-02, MODEL-01 |
| 6 | 재현성 기록 체계 구축(config/seed/commit/SHA256/env, submission_ledger.csv) | 실험 1건이 클린 환경에서 재실행되어 동일 산출물 | FR-05/06, `04-versioning-recovery.md` |
| 7 | 로컬 문서 상태 갱신(Public/Private 40:60·FICR 6/8·외부데이터 조건부·2차 30/20팀) | 승격/수정 항목이 각 .md에 반영 | §2 표 전체 |
| 8 | 산출물·일정 체크리스트 작성(08.14/08.17/증빙서류/PDF) | 이중 데드라인·서류 목록 캘린더화 | 공식 평가·개요 |

---

### 6. 재검증 필요 항목

| 항목 | 왜 불확실한가 | 확인할 출처 |
|---|---|---|
| 평가 기간 실제 시각 범위 | sample_submission 시작이 **2024-12-31 08:00**로 표기되어 로컬 문서의 "2025년 8,760시간"과 불일치 가능 | 공식 `data_description.md`, 실제 `sample_submission.csv` `forecast_kst_dtm`, `test/ldaps_test.csv` |
| forecast lead·cutoff 정의 | blueprint의 "12~35h, `data_available_kst_dtm`"은 로컬 감사 결과이며 공식 원문 미대조 | 공식 `data_description.md`, `info.xlsx` |
| 파일 행수·컬럼 수 | 420,864/236,736행 등은 로컬 감사값(공식 페이지 미명시) | 배포 데이터 실측(외부 미업로드) |
| FICR "이론상 최대 정산금" 정확한 구현 | 공식은 정의만 제시, 유효시간·에너지 단위(kWh) 계산 세부는 코드 확인 필요 | 공식 `평가_산식 코드.ipynb` |
| info.xlsx 좌표·터빈 메타 | grid 매핑·hub-height 보정에 필요하나 실제 컬럼 미확인 | 공식 `info.xlsx` |
| KPX 실제 정산제도 vs 대회 산식 | 외부 KPX 제도(4/6 등)와 대회 6/8·4/3/0원 상이 가능 | 공식 대회 산식 우선, [KPX 규칙](https://marketrule.kpx.or.kr) 참고 |

---

### 7. 출처 목록

| 번호 | 출처명 | URL | 신뢰도 |
|---|---|---|---|
| 1 | DACON 대회 개요(배경·일정·주최·참가자격) | [dacon.io/236727/overview/description](https://dacon.io/competitions/official/236727/overview/description) | 공식/1차 |
| 2 | DACON 평가(산식·유효시간·FICR·40:60·2차 구조·산출물) | [dacon.io/236727/overview/evaluation](https://dacon.io/competitions/official/236727/overview/evaluation) | 공식/1차 |
| 3 | DACON 규칙(leakage·외부데이터·사전학습·API·제출) | [dacon.io/236727/overview/rules](https://dacon.io/competitions/official/236727/overview/rules) | 공식/1차 |
| 4 | DACON 데이터(파일 구조·컬럼·8,760행) | [dacon.io/236727/data](https://dacon.io/competitions/official/236727/data) | 공식/1차 |
| 5 | 로컬: 최종 설계서(데이터 감사·아키텍처) | `04-final-solution-blueprint.md` | 로컬 결정 |
| 6 | 로컬: 요구사항 정의(FR/DATA/MODEL/SUB) | `02-requirements.md` | 로컬 결정 |
| 7 | 로컬: 버전·복구 정책 | `04-versioning-recovery.md` | 로컬 결정 |
| 8 | 로컬: 문제 정의 | `01-problem-definition.md` | 로컬 결정 |
| 9 | 로컬: Perplexity 1회차 synthesis(상태 분류) | `02-perplexity-research-synthesis.md` | 외부 리서치/로컬 |
| 10 | 로컬: 데이터·모델링 설계서 | `02-data-modeling-spec.md` | 로컬 결정 |
| 11 | KPX 시장운영규칙(제도 참고) | [marketrule.kpx.or.kr](https://marketrule.kpx.or.kr) | 외부 리서치 |

---

핵심 요약: 이번 공개로 기존에 "추론/추후공개"였던 **Public/Private 40:60**, **FICR 6/8%·4/3/0원**, **외부 데이터 조건부 허용**, **train/inference 분리·UTF-8 복원**이 모두 공식 확정되었고, 신규로 **2차 진출 구조(30→20팀)**, **산출물 마감 08.17**, **참가자격 증빙 서류**, **발표 PDF 전용**이 확인되었습니다. 가장 주의할 재검증 포인트는 sample_submission 시작 시각이 **2024-12-31 08:00**으로 표기되어 로컬 문서의 "2025년 전체" 가정과 충돌할 수 있다는 점으로, 실제 `forecast_kst_dtm` 범위 확인을 최우선 백로그(2순위)로 두었습니다.

이 결과를 Space 파일로 저장해 둘까요? 원하시면 `03-requirements-revalidation.md`로 업로드하겠습니다.