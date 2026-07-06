## Perplexity 세션 결과

- 세션: P3-4 모델링 리서치
- 날짜: 2026-07-06 (KST)
- 모드/모델: Computer (웹 브라우징 + Space 파일 검색 + 학술/웹 리서치)
- 업로드 파일: `04-final-solution-blueprint.md`, `02-data-modeling-spec.md`, `01-strategy-prd.md`, `00-source-map.md`, `01-problem-definition.md`, `02-requirements.md`, `04-versioning-recovery.md`, `03-market-research.md`, `02-perplexity-research-synthesis.md`

---

### 1. 공식 제약 요약

| 제약 | 내용 | 출처 URL 또는 첨부 문서 | 모델링 영향 |
|---|---|---|---|
| 평가 산식 | `Score = 0.5 × (1-NMAE) + 0.5 × FICR` | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) (공식 확인) / `04-final-solution-blueprint.md` | 오차 최소화와 정산 구간 확보를 동시에 최적화하는 이중 목적 |
| NMAE 정의 | 그룹별 `mean(|예측-실제| / 그룹 설비용량)`, `1-NMAE = 1 - 3그룹 NMAE 평균` | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) (공식) | capacity 정규화 → 그룹별 균등 가중, 절대 kWh보다 그룹 상대오차 중요 |
| FICR 정의 | 시간별 NMAE ≤6% → 4원/kWh, 6~8% → 3원/kWh, >8% → 0. `그룹 FICR = 획득정산금/이론상최대정산금`, 3그룹 평균 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) (공식) | 6%·8% 경계 근처 시간대의 오차를 임계값 아래로 밀어넣는 것이 핵심 |
| 평가 필터 | 실제 발전량이 **설비용량 10% 이상**인 시간대만 평가 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) (공식) | 저풍속·발전정지 구간은 점수 무관 → valid-hour 구간에 자원 집중 |
| Public/Private | Public 40% / Private 60%, 1일 최대 5회 제출 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) (공식) | Public 과적합 금지, local CV를 1차 신뢰 지표로 |
| 예측기준시점(cutoff) | D-1 14:00 KST 예시 명시 (`data_available_kst_dtm` 이후 정보 사용 금지) | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) (공식) / `blueprint 2.3` | forecast lead 12~35h. cutoff 이후 예보·실측 사용 시 실격 |
| 원격 API 금지 | OpenAI/Gemini/HF Inference API 등 원격 추론 금지, 로컬 가중치 로드만 허용 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) (공식) | Private 복원 가능한 로컬 train/inference 코드 필수 |
| 사전학습 가중치 | **2026-07-05까지** 공개된 오픈소스 가중치만 허용 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) (공식) | Chronos 등 사용 시 공개일·라이선스 registry 기록 필요 |
| 외부 데이터 | 공개·합법 데이터만 허용, 비공개/내부 데이터 금지, leakage 규칙 준수 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) (공식) | ERA5 등 재분석 자료는 cutoff·재현성 통과 시에만 |
| 데이터 구조 | LDAPS 16격자/시각, GFS 9격자/시각, target kWh, capacity 21,600/21,600/21,000 kWh | `04-final-solution-blueprint.md 2.1~2.3` (공식 배포 후 로컬 확정) | 데이터 탭 상세는 공식 페이지 미노출 → **재검증 필요** |
| 평가기간 SCADA | 평가 입력은 LDAPS/GFS만, **평가기간 SCADA/label 미제공** | `01-problem-definition.md`, `blueprint 5.2` (로컬/워크숍) | SCADA를 추론 입력 피처로 쓰는 전략 금지 |

---

### 2. NWP 피처 엔지니어링 후보

| 후보 | 설명 | 기대 효과 | 구현 난이도 | leakage 위험 |
|---|---|---|---|---|
| Wind speed 크기 | u/v 성분에서 `sqrt(u²+v²)` 산출 | 풍속-발전 변환의 1차 핵심 변수 ([TU Delft NWP 후처리](https://repository.tudelft.nl/file/File_2482d5fa-436a-4634-aced-5a663de6d44d?preview=1)) | 낮음 | 없음 |
| Wind direction sin/cos | u/v 기반 `atan2` → sin/cos 인코딩 | 방향 불연속(0/360°) 제거, 지형·wake 방향성 반영 | 낮음 | 없음 |
| Hub-height 보정(117m) | 80m/100m(또는 10m) 로그/멱법칙 shear로 117m 외삽 | NWP hub-height 미표현 오차 보정, 발전량 상관 강화 ([Wiley hub-height 후처리](https://onlinelibrary.wiley.com/doi/full/10.1002/ese3.928)) | 중간 | 없음 (alpha clip 필요) |
| Wind power density | `0.5·ρ·v³` (air density × 풍속³) | 물리적 발전 잠재량 직접 표현 ([Heliyon WPD 피처](https://pmc.ncbi.nlm.nih.gov/articles/PMC10746462/)) | 중간 | 없음 (이상치 clip) |
| Air density | 기온·기압·습도 기반 ρ 산출 | 계절·고도별 발전 효율 차이 반영 | 중간 | 없음 (단위 K/Pa 확인) |
| Grid 통계 pooling | 16/9 격자의 mean/std/min/max/q25/q75 | baseline의 mean-only 대비 공간 변동성 포착 | 낮음 | 없음 |
| Nearest/IDW 격자 | `info.xlsx` 터빈 좌표 거리 기반 가중 | 단지 위치 대표성↑ ([Mendeley GFS 격자 GBM](https://data.mendeley.com/datasets/wg9pkrp3rv/1)) | 중간 | 없음 (좌표 변환 검증) |
| LDAPS/GFS spread | 두 모델 동일 물리량 차이 | 예보 불확실성·신뢰도 대리변수 ([Gilbert 2019 다중해상도](http://pierrepinson.com/docs/Gilbertetal2019.pdf)) | 낮음 | 없음 |
| Lead-hour 피처 | `forecast - available` (12~35h) | 리드별 예보오차 구조 반영 | 낮음 | 없음 (cutoff 검증 필수) |
| Calendar sin/cos | hour/month/season 주기 인코딩 | 계절·일주기 발전 패턴 | 낮음 | 없음 |
| Terrain proxy | 격자 고도·공간 gradient (제공 변수만) | 복잡지형 국지 가속 반영 | 높음 | 없음 (외부 DEM은 규칙 검증 후) |

---

### 3. SCADA 활용 후보

| 후보 | 학습에서의 활용 | 추론에서의 활용 가능성 | leakage 위험 | 권고 |
|---|---|---|---|---|
| 그룹별 power curve (풍속→출력) | train SCADA/label로 그룹 출력곡선 적합 → NWP 풍속을 발전량으로 물리 변환하는 baseline·피처 | **불가** (평가기간 SCADA 미제공). NWP 풍속을 curve에 입력하는 방식만 가능 | 낮음 (train 학습·NWP 입력 시) | ✅ 권고: NWP 풍속 → curve 변환 피처/baseline |
| 이상치·curtailment 정제 | 색맵/사분위/변화점 기법으로 정지·curtail·outlier 제거 후 curve 적합 품질↑ ([SciDirect 이상탐지](https://www.sciencedirect.com/science/article/abs/pii/S0960148121017134), [Sage 베이지안](https://journals.sagepub.com/doi/abs/10.1177/09576509221119563)) | 정제 로직은 train 단계 전용 | 낮음 | ✅ 권고: train 품질 향상용 |
| SCADA 유효구간/품질 플래그 | curve 적합 신뢰구간, 결측·zero-run 제외 규칙 도출 | 규칙만 이관, SCADA 값은 이관 불가 | 낮음 | ✅ 권고 |
| 물리적 상·하한 도출 | SCADA로 cut-in(3m/s)·rated·cut-out(22~22.5m/s) 구간 확인 → 예측 clip 상·하한 | 상수화된 상·하한만 추론 적용 | 낮음 | ✅ 권고 |
| SCADA lag/rolling 피처 | 최근 SCADA 실측을 지연 피처로 학습 | **평가기간 SCADA 없음 → 추론 불가** | **매우 높음** | ⛔ 금지 (추론 입력 사용) |
| SCADA를 직접 입력 피처 | train에서만 존재하는 실측 풍속/출력 | 평가기간 부재로 재현 불가 | **매우 높음** | ⛔ 금지 |

---

### 4. Validation 전략

| 전략 | 장점 | 단점 | Private 복원성 | 권고 순위 |
|---|---|---|---|---|
| 연도 holdout (2024 → 2025 대리) | 2025 숨김기간과 가장 유사한 1년 분포 검증 | fold 1개로 분산 추정 약함 | 높음 | **1순위** |
| Rolling-origin / expanding window | 시간순서 보존, leakage 방지, 리드별 오차 안정성 ([rolling-origin CV](https://blog.truegeometry.com/api/exploreHTML/a80154333135b9c850aeccd64d554e05.exploreHTML)) | 계산량↑, fold 설계 복잡 | 높음 | **2순위** |
| 계절 블록(겨울/봄, 여름/가을) | 태풍·장마·강풍 등 극한 분포 강건성 점검 | 그룹×계절 조합 데이터 희소 | 높음 | 3순위 |
| Group 3 focus (2023→2024) | Group 3 label 짧음(2022 결측) 대응 | Group 3만 편향 위험 | 중간 | 3순위 |
| Public LB 과적합 가드레일 | local↔Public 괴리 모니터, conservative scaling | Public 5회/일 제약, 신호 약함 | Public≠최종 | 보조 |
| Random K-Fold | (사용 금지) | 시간·리드·cutoff 무시 → **leakage** | 낮음 | ⛔ 금지 |

- 공통 규칙: fold 간 시간 순서 유지, lag/rolling 피처는 forecast horizon 이상 embargo gap 부여, valid mask(actual ≥ 10% capacity) 구간 점수를 별도 추적.

---

### 5. FICR 최적화 및 후처리

| 아이디어 | 1-NMAE 영향 | FICR 영향 | 검증 방법 | 리스크 |
|---|---|---|---|---|
| Capacity clipping (0~capacity) | 소폭 개선 | 소폭 개선 | fold별 clip 전후 비교 | 낮음 |
| 그룹·계절·시간대 bias 보정 | 개선 | 개선 | fold 내부 OOF로만 fit ([Chile QRF 보정](https://www.academia.edu/113356532/Post_processing_methods_for_calibrating_the_wind_speed_forecasts_in_central_regions_of_Chile)) | OOF 외 fit 시 leakage |
| Threshold-aware 보정 (6%/8% 경계) | 중립~소폭 악화 가능 | **개선(핵심)** | local 정산 simulator로 경계 이동 효과 측정 | Public 과최적화 |
| Isotonic 보정 (단조 유지) | 개선 | 개선 | OOF isotonic fit, 단조성 sanity check ([Isotonic 후처리](https://rdrr.io/github/tidymodels/probably/man/cal_estimate_isotonic.html)) | 소규모 fold 과적합 |
| Quantile/pinball 최적점 선택 | median 근처 중립 | 경계구간 개선 ([NABQR 시간적응 QR](https://arxiv.org/html/2501.14805v3), [PSCC 극한 quantile GBT](https://pscc-central.epfl.ch/repo/papers/2020/225.pdf)) | quantile grid 탐색 필요 | 계산량·튜닝 부담 |
| 그룹 가중 앙상블 | 그룹 최소점수 개선 | 그룹 FICR 평균 개선 | fold OOF 앙상블 | 특정 그룹 희생 주의 |
| Local 정산 simulator | 지표 대리 | FICR 직접 근사 | 공식 `평가_산식 코드`와 결과 일치 확인 | simulator 오구현 시 오판 |

- 핵심: FICR는 6%·8% 경계에서 계단형으로 급변하므로, **경계 바로 위 시간대를 아래로 밀어내는 보정**이 nMAE 손해를 감수해도 유리할 수 있음 → 반드시 local simulator로 총점 기준 검증.

---

### 6. 6주 구현 로드맵

| 단계 | 방법 | 산출물 | 완료 기준 |
|---|---|---|---|
| W1 | 데이터 audit + metric 재현 (`01_metric_reproduction`) | `metrics.py`, audit 노트북 | 공식 `평가_산식 코드`와 total/1-NMAE/FICR 일치 |
| W1 | baseline RandomForest를 train/inference `.py` 분리 | `train.py`, `inference.py`, submission smoke | sample_submission 형식 통과, Private 복원 구조 |
| W2 | P0 피처 (grid stats, wind speed/dir, lead, calendar) + LightGBM/CatBoost | `feature_lab`, GBM 스코어보드 | baseline 대비 local total score 개선 |
| W2~3 | time-based validation (연도 holdout + rolling) 구축 | `validation.py`, fold scorecard | random split 제거, valid-hour 점수 추적 |
| W3 | P1 물리 피처 (hub-height 117m, air density, WPD, IDW, source spread) | 피처 카탈로그 | 그룹별 최소점수 동반 개선 |
| W3~4 | SCADA power curve(정제 포함) 기반 변환 피처/baseline | `scada.py`, power curve 산출물 | leakage 없음(추론 SCADA 미사용) 검증 |
| W4 | 그룹별/pooled 모델 + fold OOF 앙상블 | `ensemble.py` | fold 평균·그룹 안정성 개선 |
| W5 | metric-aware calibration (capacity clip, bias, threshold-aware, isotonic) | calibration 노트북 | local simulator에서 FICR·total 개선 |
| W5~6 | Public 제출 관리(ledger/hash), 최종 후보 선택 규칙 적용 | submission ledger | local↔Public 괴리 점검, 과적합 후보 배제 |
| W6 | 재현성 패키징 + Short Research Paper/발표 | 발표 PDF, README, MANIFEST | seed/commit/config로 Private 복원 가능 |

---

### 7. 연구 후보로만 둘 항목

| 항목 | 이유 | 재검증 조건 |
|---|---|---|
| Chronos/Chronos-2/AutoGluon 시계열 foundation | 로컬 실행 가능하나 6주 내 tabular 대비 우위 불확실, covariate·라이선스·2026-07-05 공개일 검증 필요 | model registry에 공개일·라이선스·로컬 추론 검증 완료 시 앙상블 멤버로 |
| 외부 재분석 데이터(ERA5, KMA API 등) | 공개·합법·cutoff·재현성 통과 여부 불명 | 규칙상 공개데이터·leakage 규칙·재현 경로 확인 후 |
| 외부 DEM/RIX 지형 지수 | 규칙 검증 전이며 6주 내 효과 대비 비용 큼 | 공개 라이선스·재현성 확인 및 제공 변수만으론 부족 확인 시 |
| 신경망(TCN/BiGRU/Attention) 계열 | 표형 NWP 대비 튜닝·재현 부담, 데이터 규모 대비 이득 불확실 ([Sci Reports 하이브리드](https://pmc.ncbi.nlm.nih.gov/articles/PMC13022443/)) | GBM 상한 도달 후 시간 여유 시 |
| 시간적응 quantile regression(TAQR/NABQR) | 확률예측 고급기법, 구현·검증 시간 큼 ([NABQR](https://arxiv.org/html/2501.14805v3)) | FICR 경계 보정이 단순 quantile로 한계 도달 시 |

---

### 8. 다음 Codex 반영 작업

| 작업 | 반영 위치 | 우선순위 |
|---|---|---|
| `metrics.py` + metric 재현 노트북 (공식 산식 일치) | `src/baram/metrics.py`, `notebooks/01_metric_reproduction.ipynb` | P0 |
| cutoff validator (`data_available_kst_dtm` 기준 lead 검증) | `src/baram/features/`, audit 노트북 | P0 |
| baseline RandomForest train/inference 분리 | `src/baram/train.py`, `inference.py` | P0 |
| P0 피처 모듈 (grid stats, wind speed/dir, lead, calendar) | `src/baram/features/weather_grid.py`, `calendar.py` | P0 |
| time-based validation fold 정의 | `src/baram/validation.py` | P1 |
| SCADA power curve (정제+변환, 추론 미사용 가드) | `src/baram/features/scada.py` | P1 |
| local 정산 simulator + threshold-aware calibration | `notebooks/05_submission_and_calibration.ipynb` | P1 |
| submission ledger/hash + MANIFEST 재현성 | `outputs/submissions/`, `data/raw/open/MANIFEST.md` | P1 |

---

### 9. 출처 목록

| 번호 | 출처명 | URL | 신뢰도 |
|---|---|---|---|
| 1 | DACON 개요 (공식) | https://dacon.io/competitions/official/236727/overview/description | 공식/1차 |
| 2 | DACON 평가 (공식, 산식·FICR·Public/Private 확인) | https://dacon.io/competitions/official/236727/overview/evaluation | 공식/1차 |
| 3 | DACON 규칙 (공식, cutoff·API·가중치·외부데이터) | https://dacon.io/competitions/official/236727/overview/rules | 공식/1차 |
| 4 | 로컬 최종 설계서 (배포 후 데이터 확정) | 첨부 `04-final-solution-blueprint.md` | 로컬 확정(재검증 권장) |
| 5 | TU Delft — NWP 후처리 하이브리드 신경망 | https://repository.tudelft.nl/file/File_2482d5fa-436a-4634-aced-5a663de6d44d?preview=1 | 외부 리서치 |
| 6 | Wiley — hub-height 풍속 후처리 신경망 | https://onlinelibrary.wiley.com/doi/full/10.1002/ese3.928 | 외부 리서치 |
| 7 | Heliyon — LightGBM+ANN, WPD 피처 | https://pmc.ncbi.nlm.nih.gov/articles/PMC10746462/ | 외부 리서치 |
| 8 | Mendeley — GFS 격자 GBM 다운스케일 | https://data.mendeley.com/datasets/wg9pkrp3rv/1 | 외부 리서치 |
| 9 | Gilbert 2019 — 다중해상도 예보 피처 | http://pierrepinson.com/docs/Gilbertetal2019.pdf | 외부 리서치 |
| 10 | ScienceDirect — SCADA power curve 이상탐지 정제 | https://www.sciencedirect.com/science/article/abs/pii/S0960148121017134 | 외부 리서치 |
| 11 | Sage — 베이지안 변화점·사분위 이상데이터 정제 | https://journals.sagepub.com/doi/abs/10.1177/09576509221119563 | 외부 리서치 |
| 12 | rolling-origin 시계열 CV / leakage 방지 | https://blog.truegeometry.com/api/exploreHTML/a80154333135b9c850aeccd64d554e05.exploreHTML | 외부 리서치 |
| 13 | arXiv NABQR — 시간적응 quantile 오차보정 | https://arxiv.org/html/2501.14805v3 | 외부 리서치 |
| 14 | Chile QRF — 풍속 예보 통계보정 | https://www.academia.edu/113356532/Post_processing_methods_for_calibrating_the_wind_speed_forecasts_in_central_regions_of_Chile | 외부 리서치 |
| 15 | PSCC — 풍력 극한 quantile GBT | https://pscc-central.epfl.ch/repo/papers/2020/225.pdf | 외부 리서치 |
| 16 | tidymodels — isotonic 회귀 보정 | https://rdrr.io/github/tidymodels/probably/man/cal_estimate_isotonic.html | 외부 리서치 |

---

주요 확인·주의사항:
- 공식 페이지에서 평가 산식(0.5×(1-NMAE)+0.5×FICR), FICR 단가(6%↓ 4원·8%↓ 3원), 10% 필터, Public 40/Private 60, cutoff(D-1 14:00 예시), API 금지, 가중치 2026-07-05 기준일을 **공식 확인**했습니다. 데이터 컬럼·격자 수·리드시간 세부는 공식 개요 페이지에 미노출이라 로컬 blueprint 기반이며 **데이터 탭에서 재검증** 권장입니다.
- 평가기간 SCADA 부재를 근거로, SCADA를 **추론 입력 피처/지연 피처로 쓰는 전략은 금지(매우 위험)** 로 표시했습니다.
- Random split·cutoff 무시 검증은 leakage로 명시했습니다.

메모리에 이 프로젝트 맥락을 저장할까요? 원하시면 이 보고서를 Space 파일로도 업로드해 드리겠습니다.