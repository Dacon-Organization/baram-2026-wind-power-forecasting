I now have all official content confirmed. I have everything needed to produce the final deliverable. Let me note the key verified facts and write up the response.

Key official confirmations from DACON:
- Score = 0.5 × (1-NMAE) + 0.5 × FICR; evaluated only on hours where actual ≥ 10% capacity
- FICR tiers: nMAE ≤6% → 4원/kWh, 6~8% → 3원/kWh, >8% → no settlement
- Public 40% / Private 60% (pre-sampled)
- 2-stage: 1st = Private Score 100% → top 30 (incl. 10 reserve) submit artifacts → verified top 20 → 2nd = 50% Private + 50% presentation → top 10 win
- Presentation scoring: 과제이해도 20, 기술우수성 30, 문제해결력 15, 적용가능성 20, 발표완성도 15
- Host: 한국동서발전, GS E&R, 태백가덕산풍력발전; operated by DACON
- Data leakage rule based on point-in-time availability; train/inference must be separable; PDF presentation (no PPT), 10 min

Now I'll write the final answer.

## Perplexity 세션 결과

- 세션: P3-2 문제 정의와 발표 서사
- 날짜: 2026-07-06 (KST)
- 모드/모델: Perplexity Computer (공식 페이지 브라우징 + Space 로컬 문서 대조)
- 업로드 파일: 01-problem-definition.md, 00-source-map.md, 02-requirements.md, 03-market-research.md, 04-final-solution-blueprint.md, 01-strategy-prd.md, 02-perplexity-research-synthesis.md, 풍력발전량 예측 AI 경진대회.pdf 외

### 1. 공식 사실

| 항목 | 내용 | 출처 URL 또는 첨부 문서 | 발표 영향 |
|---|---|---|---|
| 평가 산식 | Score = 0.5 × 평균 예측오차율(1-NMAE) + 0.5 × 정산금획득률(FICR) | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 정확도와 정산 관점을 동시 최적화하는 이중 목표 서사의 근거 |
| 평가 대상 시간대 | 실제 발전량이 설비용량의 10% 이상인 시간대만 평가 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 저발전 구간 제외 → valid-mask 재현이 점수 재현의 전제 |
| NMAE 정의 | 그룹별 NMAE = 평균(\|예측−실제\| / 그룹 설비용량); 1-NMAE = 1 − 3개 그룹 NMAE 평균 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 용량 정규화·그룹 평균 구조가 그룹별 균형 최적화를 요구 |
| FICR 정의 | 그룹별 FICR = 획득 정산금 / 이론상 최대 정산금; FICR = 3개 그룹 평균 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 구간형(비연속) 목표 → 임계값 인지 보정 필요 |
| FICR 정산 단가 | nMAE ≤6% → 4원/kWh, 6% 초과~8% 이하 → 3원/kWh, 8% 초과 → 정산 없음 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 6%·8% 문턱이 점수 급락 지점 |
| Public/Private 분할 | Public = 사전 샘플링된 40%, Private = 나머지 60% | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | Public 과적합 위험 → 시계열 검증 필요 |
| 2단계 평가 | 1차: Private 100% → 상위 30팀(예비 10 포함) 산출물 제출 → 검증 통과 상위 20팀이 2차; 2차: Private 50% + 발표 50% → 최종 상위 10팀 수상 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 발표가 최종 점수의 절반 → 서사 품질이 순위를 좌우 |
| 발표 배점 | 과제 이해도 20 / 기술 우수성 30 / 문제 해결력 15 / 적용 가능성 20 / 발표 완성도 15 (합 100) | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 슬라이드 구성을 배점에 맞춰 시간 배분 |
| 산출물·재현성 | train/inference 코드 분리 필수, .py 또는 .ipynb, UTF-8, 오차 범위 내 Private Score 복원 가능해야 함, 개발환경·라이브러리 버전 기재 | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | "재현성" 슬라이드의 공식 근거 |
| 발표 형식 | 10분 분량 자유 양식, 솔루션 PDF로 제출·발표(PPT 불허) | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 최종 산출물은 PDF로 준비 |
| Data Leakage 규칙 | 예측기준시점 이전에 생성·공개·확정되어 실제 활용 가능했던 정보만 사용; 예보는 예보 생성/공개 시각, 실측은 관측/확정 시각 기준; 사후 보정·재분석 자료 사용 불가 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) | 평가기간 SCADA·실제 발전량 사용 금지의 공식 근거 |
| 외부 데이터 | 공개·합법·라이선스 준수 시 허용, 재현 가능해야 하고 활용 가능 시점 소명 필요 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) | 외부 NWP 등 사용 시 시점 소명 필수 |
| 사전학습모델/API | 2026-07-05까지 가중치 공개된 오픈소스만 허용; 외부 추론 API(OpenAI, Gemini, HF Inference 등) 금지, 자체 환경에서 가중치 직접 로드만 허용 | [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules) | Chronos 등은 로컬 실행 전제로 설계 |
| 배경·목적 | 발전량 예측 정확도가 전력계통 운영 안정성 및 재생에너지 예측제도 정산금 확보와 직접 연결됨 | [DACON 개요](https://dacon.io/competitions/official/236727/overview/description) | "단순 회귀가 아니다" 서사의 공식 근거 |
| 주최/주관 | 주최/주관 한국동서발전·GS E&R·태백가덕산풍력발전, 운영 데이콘 | [DACON 개요](https://dacon.io/competitions/official/236727/overview/description) | 실무 발전사 주최 → 적용 가능성 강조 근거 |
| 예측 대상 | 3개 KPX 그룹, 시간 단위 발전량; 로컬 문서 기준 용량 kpx_group_1/2 = 21.6MW, kpx_group_3 = 21.0MW | [01-problem-definition.md] (첨부) | 그룹별 용량 정규화 이해의 근거(공식 페이지 미표기, 아래 재검증 필요) |

### 2. 한 문장 문제 정의

기상예보(LDAPS·GFS)만 주어지는 2025년 평가 기간에 대해, 학습 기간의 발전량 라벨과 SCADA 실측을 데이터 누수 없이 지식으로만 활용하여 KPX 3개 그룹의 시간별 풍력 발전량을 예측하고, 평균 예측오차율(1-NMAE)과 정산금획득률(FICR)을 동시에 최적화하면서 예측 기준시점 이후 정보를 쓰지 않는 재현 가능한 파이프라인을 만드는 문제입니다. ([DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation), [DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules))

### 3. 일반 회귀 문제와 다른 점

| 차별점 | 설명 | 발표에서 강조할 이유 |
|---|---|---|
| 이중·비연속 목표함수 | 단일 MAE가 아니라 연속형 1-NMAE와 6%/8% 문턱을 가진 구간형 FICR을 5:5로 합산 ([DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation)) | 문턱을 넘기면 정산 단가가 4→3→0원으로 계단식 급락 → MAE만 낮춰도 점수가 안 오를 수 있음을 시각화 |
| 조건부 평가 마스크 | 실제 발전량 ≥ 설비용량 10% 시간대만 평가 ([DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation)) | 저발전 구간을 잘못 다루면 로컬 검증과 리더보드가 어긋남 → valid-mask 재현이 필수 |
| 학습/평가 입력 비대칭 + 누수 제약 | 평가 기간엔 예보만 제공, SCADA·실제 발전량 없음; 예측기준시점 이후 정보 사용 금지 ([DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules)) | 일반 tabular처럼 전 구간 feature를 쓰면 실격 위험 → point-in-time 설계가 핵심 |
| 물리·도메인 변환이 필요 | 예보 격자를 허브 높이 풍속·공기밀도·풍력밀도 등 발전량으로 변환하는 비선형 물리(풍속 세제곱 근처 반응)를 요구 ([03-market-research.md] 첨부, [DACON 개요](https://dacon.io/competitions/official/236727/overview/description)) | 순수 통계 회귀 대비 도메인 후처리가 성능을 가른다는 서사 |
| 재현성·운영이 채점 대상 | train/inference 분리, 오차범위 내 Private 복원, 발표 50%가 공식 채점 ([DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation)) | "모델 점수"만이 아니라 재현성·운영 적용성이 순위를 결정 |

### 4. 핵심 기술 과제

| 과제 | 왜 어려운가 | 해결 방향 (설계 문서 기반) |
|---|---|---|
| 예보 격자 후처리 | LDAPS 16격자·GFS 9격자의 해상도·lead time에 따라 오차 특성이 다름 | grid pooling(mean/std/IDW), source별 feature, forecast spread, lead hour feature ([04-final-solution-blueprint.md], [02-perplexity-research-synthesis.md] 첨부) |
| 풍속→발전량 비선형 변환 | 특정 구간에서 풍속 세제곱 반응, cut-in/cut-out, 지형 난류 | 허브 높이 풍속 보정, 공기밀도, 풍력밀도(0.5·ρ·v³), 방향 sin/cos, SCADA power curve 학습 ([04-final-solution-blueprint.md] 첨부) |
| 그룹 간 균형 최적화 | 점수가 3개 그룹 평균 → 한 그룹 붕괴가 전체를 끌어내림; Group 3는 2022 라벨 부재 | 그룹 pooled 모델 + 그룹 임베딩, 그룹별 bias 보정, Group 3 전용 fold ([04-final-solution-blueprint.md], [01-strategy-prd.md] 첨부) |
| FICR 임계값 인지 보정 | 6%/8% 문턱 근처에서 미세 오차가 정산 단가 급변 유발 | OOF calibration, capacity clipping, 문턱 인지형 튜닝, quantile/bias 보정 ([03-market-research.md], [02-perplexity-research-synthesis.md] 첨부) — 재검증 필요(대회 평가 코드 기준) |
| 검증-리더보드 정합 | Public 40%가 사전 샘플링 → 랜덤 CV는 과적합 위험 | rolling-origin/seasonal holdout, 2025 1개월 holdout proxy, valid-mask·FICR 로컬 재현 ([02-perplexity-research-synthesis.md] 첨부) |

### 5. 운영/재현성 과제

| 과제 | 실패 시 영향 | 대응 방향 |
|---|---|---|
| Private Score 복원 | 오차범위 내 복원 실패 시 2차 평가 대상에서 탈락 | seed·commit·config·hash 고정, train/inference 분리, submission ledger ([DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation), [02-requirements.md] 첨부) |
| Data Leakage 차단 | 예측기준시점 이후 정보 사용 시 실격/평가 제외 | cutoff validator, 평가기간 SCADA·실제 발전량 배제, 파생·집계값도 시점 검증 ([DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules)) |
| SCADA의 안전한 활용 | 평가기간 미제공 SCADA를 직접 feature화하면 누수 | SCADA는 학습 기간 power curve 학습·품질검증 보조로만 제한 ([03-market-research.md] 첨부) |
| 외부 데이터/모델 소명 | 시점·라이선스 소명 부족 시 평가 제외 | 외부 NWP 등 공개·재현 가능성·활용 시점 문서화; 사전학습 모델은 2026-07-05 이전 공개분·로컬 로드만 ([DACON 규칙](https://dacon.io/competitions/official/236727/overview/rules)) |
| 제출 형식·인코딩 | CSV 형식/인코딩 오류 시 채점 실패 | UTF-8, sample_submission 스키마 일치, 최종 채점 파일 명시 선택 ([DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation)) |

### 6. 10분 발표 구성안

배점(과제 이해 20 / 기술 30 / 문제해결 15 / 적용 20 / 완성도 15)에 맞춰 시간을 배분했습니다.

| 슬라이드 | 제목 | 핵심 메시지 | 근거/시각화 아이디어 |
|---|---|---|---|
| 1 | 문제 한 줄 정의 | 예보만 주어진 2025년의 3그룹 시간별 발전량을, 누수 없이, 정확도+정산을 동시에 예측하는 문제 | 입력·출력·제약을 한 장 다이어그램 |
| 2 | 왜 단순 회귀가 아닌가 | 이중 목표·조건부 마스크·입력 비대칭·물리 변환·재현성 채점의 5가지 특성 | 5개 아이콘 카드 |
| 3 | 평가식 해부 | Score = 0.5(1-NMAE) + 0.5 FICR, 10% 마스크, 6/8% 문턱 | FICR 계단형 정산 단가(4→3→0원) 그래프 |
| 4 | 데이터와 누수 제약 | 학습=예보+라벨+SCADA, 평가=예보만; SCADA는 지식으로만 | point-in-time 타임라인, cutoff 표시 |
| 5 | 기술: 예보 후처리 | 격자 pooling·허브풍속·공기밀도·풍력밀도로 물리 반영 | 격자→단지 변환, power curve 곡선 |
| 6 | 기술: 그룹·정산 최적화 | 그룹 균형 + FICR 문턱 인지 보정 | 그룹별 오차 분포, 문턱 근처 보정 효과 |
| 7 | 검증 전략 | rolling-origin·seasonal holdout으로 Public 40% 과적합 방지 | 시간 분할 fold 다이어그램 |
| 8 | 문제 해결 과정 | 베이스라인→피처→보정 단계별 개선과 의사결정 | 스코어보드(1-NMAE/FICR 추이) |
| 9 | 재현성·운영 적용성 | train/inference 분리·seed/hash·ledger로 Private 복원; 발전사 실무 연계 | 파이프라인·재현 체크리스트 |
| 10 | 요약·한계·확장 | 성과 요약, 남은 한계, 후속 연구 방향(단정 지양) | 3줄 요약 + 한계 명시 |

### 7. 발표에서 피해야 할 표현

| 표현 | 문제점 | 안전한 대체 표현 |
|---|---|---|
| "FICR은 KPX 정산제도와 동일하다" | 공식 페이지는 대회 평가 산식만 규정, 실제 제도와 동일하다는 근거 없음 | "실제 예측제도의 문제의식을 반영한 대회용 근사/모사 지표로 이해했습니다" |
| "이 모델은 실무에 바로 투입 가능하다" | 적용 가능성은 평가 항목일 뿐 실증되지 않음 | "실무 활용 관점을 고려해 설계했고, 추가 검증이 필요합니다" |
| "SCADA를 활용해 정확도를 높였다"(모호) | 평가기간 SCADA 사용으로 오해되면 누수 의심 | "학습 기간 SCADA는 power curve 학습·품질검증 보조로만 사용했습니다" |
| "MAE를 최소화하면 1등" | FICR 문턱·마스크를 무시한 과장 | "1-NMAE와 FICR을 함께, 특히 6/8% 문턱을 의식해 최적화했습니다" |
| "우리 검증 점수 = 최종 점수" | Public/Private·발표 50% 구조 무시 | "로컬 검증으로 Private 정합을 관리했고 최종은 발표 평가와 합산됩니다" |
| "가장 정확한 예측 모델" 등 최상급 단정 | 근거 없는 최상급은 감점 요인 | "본 데이터·평가 기준에서 관측한 개선 결과" |

### 8. 출처 목록

| 번호 | 출처명 | URL | 신뢰도 |
|---|---|---|---|
| 1 | DACON 대회 개요(배경·주제·주최·일정) | [dacon.io/.../description](https://dacon.io/competitions/official/236727/overview/description) | 공식/1차 |
| 2 | DACON 평가(Score·NMAE·FICR·Public/Private·2단계·발표배점·산출물) | [dacon.io/.../evaluation](https://dacon.io/competitions/official/236727/overview/evaluation) | 공식/1차 |
| 3 | DACON 규칙(Data Leakage·외부데이터·사전학습·API·유의사항) | [dacon.io/.../rules](https://dacon.io/competitions/official/236727/overview/rules) | 공식/1차 |
| 4 | 문제 정의(로컬) | 01-problem-definition.md (첨부) | 내부 설계 문서 |
| 5 | 최종 솔루션 블루프린트(로컬) | 04-final-solution-blueprint.md (첨부) | 내부 설계 문서 |
| 6 | 시장 조사·제도 맥락(로컬) | 03-market-research.md (첨부) | 내부 설계 문서 |
| 7 | 요구사항(로컬) | 02-requirements.md (첨부) | 내부 설계 문서 |
| 8 | 산업부/KPX 예측제도 도입 자료 | [eiec.kdi.re.kr/.../num=205187](https://eiec.kdi.re.kr/policy/materialView.do?num=205187) | 외부 리서치(재검증 필요) |
| 9 | 풍력 예측 연구 리뷰 | [mdpi.com/1996-1073/18/2/350](https://www.mdpi.com/1996-1073/18/2/350) | 외부 리서치 |

주의(재검증 필요): (1) 그룹별 설비용량(21.6/21.6/21.0MW)과 kWh 표기는 로컬 문서·워크숍 자료 기준이며 공식 개요/평가 페이지 본문에는 수치가 명시되지 않았습니다 — 실제 배포된 info/data_description으로 확인 필요. (2) FICR이 현행 KPX 제도와 동일한지는 공식 근거가 없어 "대회용 근사/모사 지표"로 표기했습니다. (3) FICR 관련 보정 전략은 대회 평가 코드(evaluation_metric.ipynb) 기준으로 반드시 재현·검증하세요.

원하시면 이 내용을 발표용 PDF(10분, DACON 규정상 PDF 제출)나 슬라이드 아웃라인 문서로 만들어 드리겠습니다.