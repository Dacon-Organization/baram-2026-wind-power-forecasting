Now I have everything I need. Let me deliver the complete report in the required Markdown format.

## Perplexity 세션 결과

- 세션: P3-3 시장 및 제도 조사
- 날짜: 2026-07-06 (KST)
- 모드/모델: Perplexity Computer (리서치 파트너 모드)
- 업로드 파일: 03-market-research.md, 01-problem-definition.md, 01-strategy-prd.md, 풍력발전량 예측 AI 경진대회.pdf, 2026 BARAM 경진대회 워크숍.md (Space 파일 참고)

핵심 발견 요약: DACON 대회의 FICR 정산 구간(6%/8% → 4원/3원)은 **2020년 도입 당시의 옛 제도 기준**과 일치하며, **현행 KPX 제도는 2025년 개정으로 4%/6%로 강화**되어 태양광은 2025-06-01, **풍력·혼합자원은 2026-06-01부터 강화 기준을 적용**받습니다. 즉 대회 지표는 실제 제도의 구조를 차용하되 개정 전 구간으로 단순화되어 있습니다.

---

### 1. 공식/기관 근거 요약

| 주제 | 핵심 내용 | 출처 URL | 발표 활용도 |
|---|---|---|---|
| 예측제도 도입 취지 | "재생에너지 확대에 따른 출력 변동성 대응"을 위해 20MW 이상 태양광·풍력이 하루 전 발전량을 예측·제출하고 일정 오차율 이내 이행 시 정산금 지급 (2020.09.18 산업부·KPX) | [KDI 경제정보센터 (산업부 원자료)](https://eiec.kdi.re.kr/policy/materialView.do?num=205187) · [정책브리핑](https://m.korea.kr/briefing/pressReleaseView.do?newsId=156411699) | 높음 (제도 기원·명분) |
| 계통운영 중요성 | "재생에너지 설비규모가 확대됨에 따라 안정적 계통 운영을 위한 정확한 재생에너지 발전량 예측의 중요성이 점차 커지고 있음. IEA도 개별 태양광·풍력 발전기의 예측발전량 확보를 권고" | [KDI 경제정보센터](https://eiec.kdi.re.kr/policy/materialView.do?num=205187) | 높음 (도입부 슬라이드) |
| 예측오차율 법적 정의 | 전력시장운영규칙: "예측오차율이라 함은 보유자원 내 주요자원의 설비용량에 대한 보유자원 예측발전량과 전력거래량의 차이의 절댓값의 백분율(%)" (제14.5.1.1조·별표2) | [KPX 전력시장운영규칙](https://marketrule.kpx.or.kr/lmxsrv/law/joHistoryContent.do?SEQ=2&SEQ_CONTENTS=21489&DATE_START=20210501&DATE_END=20231230) | 높음 (NMAE 정의 근거) |
| 제도 정산 구간 강화(개정) | 2025년 개정으로 오차율 기준 2%p 강화: 기존 6%/8% → 4%/6%. 태양광 2025-06-01, 풍력·혼합자원 2026-06-01 시행 | [해줌 공식 공지(2025-04-02)](https://blog.haezoom.com/notice_05/) · [에너지정책 총정리](https://odori540.tistory.com/entry/6%EC%9B%94-%EC%97%90%EB%84%88%EC%A7%80-%EC%A0%95%EC%B1%85-%EB%B3%80%ED%99%94-%EC%B4%9D%EC%A0%95%EB%A6%AC%F0%9F%8C%B1) | 높음 (대회 vs 현행 구분) |
| 풍력의 실증 난점 | 1차 실증사업에서 태양광 3개사 전원 합격, 풍력 5개사 전원 탈락. "풍력단지 중 83%가 예측 오차율 10%를 넘어섬" | [전기신문 (네이버 블로그)](https://blog.naver.com/electimes533/223753872228) | 매우 높음 (풍력 난이도 근거) |

주의: DACON 개요/평가/규칙 3개 페이지에는 KPX·SCADA·LDAPS·GFS 용어가 직접 등장하지 않으며, "3개 그룹" 풍력단지가 평가 단위임만 명시됩니다. 그룹·데이터 세부는 데이터 탭/워크숍 자료 기준으로 별도 검증이 필요합니다.

---

### 2. 전력계통 운영 관점의 중요성

| 근거 | 설명 | 출처 | 대회 문제와의 연결 |
|---|---|---|---|
| 예비력·계통 안정성 | 풍력·태양광은 전통 급전발전기 대비 본질적으로 변동성·불확실성이 크며, 예측 정확도가 필요 예비력 규모를 좌우함 | [NREL Myths & Misperceptions](https://docs.nrel.gov/docs/fy15osti/63045.pdf) | 정확한 D-1 예측이 곧 계통 편익 → 대회의 실무적 의미 |
| 하루 전 예측의 역할 | "day-ahead 발전 예측이 다른 발전기 스케줄링 규모를 결정"하며, 남은 오차는 실시간 예비력으로 처리 | [IEA Wind Task 25 - Balancing](https://iea-wind.org/wp-content/uploads/2025/02/Task25-FactS-Balancing-February2025.pdf) | 대회의 D-1 예측 프레임과 직접 대응 |
| 램프 이벤트 리스크 | 대규모 풍력의 시간당 변동은 통상 설비용량의 ±10% 이내지만, 극단 상황(폭풍→cut-out)에서 시간당 30% 초과 가능 | [IEA Wind Task 25 - Variability](https://iea-wind.org/wp-content/uploads/2025/02/Task25-FactS-Variability-February2025.pdf) | cut-out·급변 구간이 FICR 손실의 핵심 |
| 집합(aggregation) 효과 | 반경 500km 내 다수 풍력 단지를 집합하면 예측오차가 약 절반으로 감소 | [IEA Wind Task 25 - Variability](https://iea-wind.org/wp-content/uploads/2025/02/Task25-FactS-Variability-February2025.pdf) | 그룹 단위 평가·grid pooling 설계 명분 |
| 국내 제도 명분 | 안정적 계통 운영을 위해 개별 태양광·풍력의 예측발전량 확보가 필요 (IEA 권고 인용) | [KDI 경제정보센터](https://eiec.kdi.re.kr/policy/materialView.do?num=205187) | 대회 문제의 정책적 정당성 |

---

### 3. 예측오차와 정산/인센티브 연결

| 제도 항목 | 내용 | 출처 | DACON FICR와의 관계 |
|---|---|---|---|
| 정산금 지급 조건 | 예측오차율 8% 이내 & 설비이용률 10% 이상 시간대만 정산금 지급 (전력거래소 중앙예측 오차율 약 8% 감안) | [정책브리핑](https://m.korea.kr/briefing/pressReleaseView.do?newsId=156411699) · [KT 표준제안서(PDF)](https://enterprise.kt.com/entpf/images/techissue/thumbnail/2023090114181500597556.pdf) | DACON도 "발전량 ≥ 설비용량 10%" 시간대만 평가 → 구조 일치 |
| 옛 정산단가 구간 | 오차율 6% 이하 4원/kWh, 6~8% 3원/kWh, 8% 초과 0원 (2020 도입~2025 개정 전) | [tkiee 학술지](http://www.tkiee.org/kiee/XmlViewer/f415504) · [엔라이튼](https://enlighten.kr/exchange) | **DACON FICR 구간과 동일 (4원/3원/0원, 6%/8%)** |
| 개정 정산 구간 | 2025 개정: 오차율 4% 이하 4원, 4~6% 3원으로 2%p 강화 (해줌 공지에 "4% 이하 3원" 표기는 오타로 판단, 4원이 정합) | [해줌 공식 공지](https://blog.haezoom.com/notice_05/) | DACON은 개정 전 6%/8% 구간 사용 → 현행 풍력 제도와 상이 (재검증 필요) |
| 풍력 강화 시행일 | 태양광 2025-06-01, 풍력·혼합자원은 1년 유예로 **2026-06-01** 적용 | [해줌 공식 공지](https://blog.haezoom.com/notice_05/) | 대회 시점(2026-07~08)엔 현행 풍력이 이미 4%/6% 적용 → 대회는 옛 기준 |
| 오차율 산정 방식 | 예측오차율 = |발전량 − 예측량| / 설비용량 ×100(%), 1·2차 제출값 산술평균 적용 | [SNU 학위논문(PDF)](https://s-space.snu.ac.kr/bitstream/10371/193147/1/000000174780.pdf) · [KPX 규칙](https://marketrule.kpx.or.kr/lmxsrv/law/joHistoryContent.do?SEQ=2&SEQ_CONTENTS=21489&DATE_START=20210501&DATE_END=20231230) | DACON NMAE 분모(그룹 설비용량)와 동일한 정규화 방식 |
| 등록시험·페널티 | 1개월 평균 오차율 10% 이하여야 참여, 3개월 평균 10% 초과 시 등록 제외 | [KPX 규칙 제14.3.5조](https://marketrule.kpx.or.kr/lmxsrv/law/joHistoryContent.do?SEQ=2&SEQ_CONTENTS=7960&DATE_START=20210501&DATE_END=20231230) | DACON 지표엔 미반영 (대회용 단순화) |

---

### 4. 풍력 예측의 특수성

물리/모델링 난이도 차이와 제도상 차등을 분리하여 정리합니다.

| 구분 | 풍력의 난점 | 태양광과의 차이 | 출처 |
|---|---|---|---|
| 물리 - 비선형성 | 발전량이 풍속의 3제곱에 비례하는 구간 존재 → 허브고도 풍속 10% 오차가 출력 30% 오차로 증폭 | 태양광은 "clear-sky curve"라는 명확한 물리 상한이 있어 문제가 구름량 예측으로 단순화됨 | [howtostoreelectricity(업계)](https://howtostoreelectricity.com/ai-wind-power-forecasting/) · [WES/Copernicus 논문](https://wes.copernicus.org/articles/6/131/2021/) |
| 물리 - 램프 이벤트 | 전선·저기압 통과로 인한 급변(ramp)의 타이밍·크기를 결정론 모델이 정확히 못 맞춤 | 태양광 변동은 실시간에 가까워질수록 급감하나 풍력 변동은 그렇지 않음 | [arXiv 램프 예측](https://arxiv.org/pdf/2502.12807.pdf) · [UPM 리뷰](https://oa.upm.es/40379/1/INVE_MEM_2015_204980.pdf) |
| 물리 - 지형/후류 | 산악 복잡지형이 방향별 난류·가속을 만들고 wake effect·cut-out이 출력을 왜곡 | 태양광은 지형 영향이 상대적으로 작고 맑은 지역일수록 오차 낮음 | [NREL Forecasting Wind(PDF)](https://docs.nrel.gov/docs/fy16osti/66383.pdf) |
| 정확도 실측치 | day-ahead 단일 풍력단지 nMAE 약 12~20%, 대규모 램프 오차 50% 초과 | 좋은 day-ahead 태양광 예측은 정규화오차 약 8~15% 수준 | [NREL(PDF)](https://docs.nrel.gov/docs/fy16osti/66383.pdf) · [howtostoreelectricity](https://howtostoreelectricity.com/ai-wind-power-forecasting/) |
| 국내 실증 격차 | 1차 실증사업에서 풍력 5개사 전원 탈락, 풍력단지 83%가 오차율 10% 초과 (단 하나도 등록기준 통과 못함) | 태양광 참여사(KT·솔라커넥트·SK E&S)는 전원 합격 | [전기신문](https://blog.naver.com/electimes533/223753872228) |
| 제도상 차등 여부 | 정산단가·오차율 구간은 태양광·풍력 동일 적용 (물리적 차등은 있으나 단가 차등 없음). 단 강화기준 **시행일만 차등**(풍력 1년 유예) | 태양광은 2025-06-01, 풍력은 2026-06-01 강화기준 적용 | [해줌 공식 공지](https://blog.haezoom.com/notice_05/) · [tkiee](http://www.tkiee.org/kiee/XmlViewer/f415504) |

핵심 구분: **정산단가 자체의 태양광/풍력 차등은 없음**(물리 난이도만 다름). 제도상 유일한 차등은 강화기준의 **시행 시점 유예**입니다.

---

### 5. DACON 지표 해석

| 항목 | 실제 제도와 유사한 점 | 대회용 단순화 가능성 | 재검증 필요 여부 |
|---|---|---|---|
| FICR 구간(6%/8%, 4원/3원/0원) | 2020~2025 개정 전 실제 정산 구조와 **정확히 일치** | 2025 개정(4%/6%) 미반영 → 대회 시점 현행 풍력 기준과 상이. 옛 기준 채택은 대회용 선택으로 추정 | 재검증 필요 (개정 별표2 원문·시행 여부 2026-07-06 확인) |
| 정규화 분모(그룹 설비용량) | 실제 오차율도 |발전량−예측량|/설비용량으로 정규화 → **동일 원리** | 그룹 3개 단순 평균은 대회용 집계로 추정 | 낮음 |
| 이용률 10% 하한 | 실제 제도의 설비이용률 10% 이상 시간대만 정산과 **동일** | 대회는 "실제 발전량 ≥ 설비용량 10%" 시간대만 평가 → 구조 일치 | 낮음 |
| 1일 2회 제출·산술평균 | 실제 제도는 10시/17시 2회 제출값 평균 | 대회는 D-1 단일 예측(2회 제출 로직 없음) → 단순화 | 재검증 필요 (데이터 탭 예측기준시점 확인) |
| 등록시험·페널티(10%) | 실제 제도 참여요건 | 대회 지표엔 미반영 (평균오차 임계 페널티 없음) | 낮음 (대회 단순화 확정적) |
| 1-NMAE 절반 결합 | 실제 제도엔 "1-NMAE 50% + FICR 50%" 결합식 없음 | **대회 고유 설계** — 평균오차와 정산성과를 동시 평가하려는 대회용 종합점수 | 낮음 (DACON 평가식으로 확정) |

주의: "1-NMAE + FICR" 결합식과 40/60 Public/Private 분할은 DACON 평가 페이지에서 확인된 **대회 규정**이며, 실제 KPX 제도가 아닙니다. 발표 시 반드시 분리 설명하세요.

---

### 6. 발표용 근거 문장

| 문장 | 사용할 슬라이드 | 근거 출처 | 주의 표현 |
|---|---|---|---|
| "재생에너지 확대에 따른 출력 변동성 대응을 위해, 정확한 발전량 예측은 안정적 계통 운영의 전제 조건입니다." | 문제 배경(1p) | [KDI 경제정보센터](https://eiec.kdi.re.kr/policy/materialView.do?num=205187) | 공식 출처 인용 (2020.09.18 기준) |
| "하루 전 발전 예측은 다른 발전기 스케줄링 규모를 결정하고, 남은 오차는 실시간 예비력으로 처리됩니다." | 계통 중요성(2p) | [IEA Wind Task 25](https://iea-wind.org/wp-content/uploads/2025/02/Task25-FactS-Balancing-February2025.pdf) | 국제기구 1차 출처 |
| "풍력 출력은 풍속의 3제곱에 비례해, 풍속 10% 오차가 출력 30% 오차로 증폭됩니다." | 풍력 난이도(3p) | [WES/Copernicus](https://wes.copernicus.org/articles/6/131/2021/) · [howtostoreelectricity](https://howtostoreelectricity.com/ai-wind-power-forecasting/) | 정량 수치는 업계·학술 혼합, "일반적으로"로 표현 |
| "국내 1차 실증사업에서 태양광 참여사는 전원 합격했으나 풍력단지의 83%가 오차율 10%를 넘겨 전원 탈락했습니다." | 풍력 난이도(3p) | [전기신문](https://blog.naver.com/electimes533/223753872228) | 언론 보도 — "보도에 따르면"으로 표기, 원문 날짜 재확인 필요 |
| "이 대회의 FICR은 실제 예측제도의 정산 구조(오차율 구간별 단가)를 그대로 차용했습니다." | 지표 설명(4p) | [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) · [tkiee](http://www.tkiee.org/kiee/XmlViewer/f415504) | 대회 구간은 개정 전(6%/8%) 기준임을 명시 |
| "다만 실제 풍력 제도는 2026년 6월부터 4%/6%로 기준이 강화되어, 대회 지표보다 더 엄격합니다." | 실무 연결(5p) | [해줌 공식 공지](https://blog.haezoom.com/notice_05/) | "외부 리서치 기반, 개정 별표2 원문 재검증 필요" 표기 |
| "즉 우리 모델은 대회 최적화(6%/8%)를 넘어 현행 제도(4%/6%)에서도 정산금을 확보할 수 있어야 실무 활용성이 높습니다." | 결론·활용성(마지막) | [해줌 공식 공지](https://blog.haezoom.com/notice_05/) · [DACON 평가](https://dacon.io/competitions/official/236727/overview/evaluation) | 추론(대회↔실무 연결 주장)임을 명시 |

---

### 7. 다음 Codex 반영 작업

| 작업 | 반영 위치 | 우선순위 |
|---|---|---|
| FICR 구간(6%/8%)이 "개정 전 KPX 기준"임을 명시하고, 현행 4%/6%와의 차이를 각주로 추가 | 03-market-research.md, 02-data-modeling-spec.md | P0 |
| "정산단가 태양광/풍력 차등 없음, 시행일만 유예 차등" 사실을 제도 섹션에 반영 | 03-market-research.md | P0 |
| 발표용 근거 문장 6~7개를 슬라이드 매핑과 함께 발표 스크립트 초안에 삽입 | 04-final-solution-blueprint.md (발표 섹션) | P1 |
| 이용률 10% 하한이 실제 제도(설비이용률 10%)와 일치함을 point-in-time 설계 근거로 명시 | 01-problem-definition.md | P1 |
| "1-NMAE+FICR 결합식·40/60 분할은 대회 고유 규정(제도 아님)" 경고문 추가 | 02-data-modeling-spec.md | P1 |
| KPX 별표2 개정 원문(2025) 직접 확보 후 4%/6% 단가 정합성 재검증 (해줌 공지 오타 검증) | 00-source-map.md 재검증 항목 | P2 |
| DACON 데이터 탭에서 KPX 그룹/SCADA/LDAPS/GFS 실제 명시 여부 및 예측기준시점 확정 | 01-strategy-prd.md 검증 리스트 | P2 |

---

### 8. 출처 목록

| 번호 | 출처명 | URL | 신뢰도 |
|---|---|---|---|
| 1 | DACON 대회 개요 | [dacon.io/.../description](https://dacon.io/competitions/official/236727/overview/description) | 공식/1차 |
| 2 | DACON 평가 (FICR·1-NMAE·40/60) | [dacon.io/.../evaluation](https://dacon.io/competitions/official/236727/overview/evaluation) | 공식/1차 |
| 3 | DACON 규칙 (data leakage·외부데이터) | [dacon.io/.../rules](https://dacon.io/competitions/official/236727/overview/rules) | 공식/1차 |
| 4 | KDI 경제정보센터 (산업부 예측제도 도입 원자료, 2020.09.18) | [eiec.kdi.re.kr/policy/materialView.do?num=205187](https://eiec.kdi.re.kr/policy/materialView.do?num=205187) | 공식/1차 |
| 5 | 대한민국 정책브리핑 (참고자료 원문) | [korea.kr/.../156411699](https://m.korea.kr/briefing/pressReleaseView.do?newsId=156411699) | 공식/1차 |
| 6 | KPX 전력시장운영규칙 (정산단가·예측오차율 정의) | [marketrule.kpx.or.kr/.../21489](https://marketrule.kpx.or.kr/lmxsrv/law/joHistoryContent.do?SEQ=2&SEQ_CONTENTS=21489&DATE_START=20210501&DATE_END=20231230) | 공식/1차 |
| 7 | KPX 전력시장운영규칙 (등록제외 제14.3.5조) | [marketrule.kpx.or.kr/.../7960](https://marketrule.kpx.or.kr/lmxsrv/law/joHistoryContent.do?SEQ=2&SEQ_CONTENTS=7960&DATE_START=20210501&DATE_END=20231230) | 공식/1차 |
| 8 | 해줌 공식 공지 (2025 정산기준 강화, 풍력 2026-06-01) | [blog.haezoom.com/notice_05](https://blog.haezoom.com/notice_05/) | 업계 1차 (개정 별표2 원문 재검증 필요) |
| 9 | IEA Wind Task 25 - Variability | [iea-wind.org/.../Task25-Variability](https://iea-wind.org/wp-content/uploads/2025/02/Task25-FactS-Variability-February2025.pdf) | 국제기구/1차 |
| 10 | IEA Wind Task 25 - Balancing | [iea-wind.org/.../Task25-Balancing](https://iea-wind.org/wp-content/uploads/2025/02/Task25-FactS-Balancing-February2025.pdf) | 국제기구/1차 |
| 11 | NREL Forecasting Wind | [docs.nrel.gov/.../66383.pdf](https://docs.nrel.gov/docs/fy16osti/66383.pdf) | 기관/1차 |
| 12 | NREL Myths & Misperceptions | [docs.nrel.gov/.../63045.pdf](https://docs.nrel.gov/docs/fy15osti/63045.pdf) | 기관/1차 |
| 13 | 전기신문 (풍력 실증 탈락·83% 초과) | [blog.naver.com/electimes533/223753872228](https://blog.naver.com/electimes533/223753872228) | 언론 (날짜 재확인 필요) |
| 14 | tkiee 학술지 (정산단가 표) | [tkiee.org/kiee/XmlViewer/f415504](http://www.tkiee.org/kiee/XmlViewer/f415504) | 학술 |
| 15 | SNU 학위논문 (오차율·정산 산식) | [s-space.snu.ac.kr/.../000000174780.pdf](https://s-space.snu.ac.kr/bitstream/10371/193147/1/000000174780.pdf) | 학술 |
| 16 | WES/Copernicus (램프·비선형성) | [wes.copernicus.org/articles/6/131/2021](https://wes.copernicus.org/articles/6/131/2021/) | 학술/1차 |
| 17 | howtostoreelectricity (풍력 vs 태양광 정확도) | [howtostoreelectricity.com/ai-wind-power-forecasting](https://howtostoreelectricity.com/ai-wind-power-forecasting/) | 업계 블로그 (보조) |
| 18 | 엔라이튼/KT (정산단가·이용률 실무 기준) | [enlighten.kr/exchange](https://enlighten.kr/exchange) | 업계 (보조) |

---

주요 재검증 항목 (2026-07-06 기준):
1. 해줌 공지의 "변경 후 4% 이하 3원" 표기는 옛 패턴상 4원의 오타로 추정 — KPX 별표2 개정 원문 직접 확인 필요.
2. 풍력 강화기준(4%/6%) 2026-06-01 시행 여부는 제도 변경 가능성이 있으므로 대회·발표 직전 재확인 권장.
3. 전기신문 실증 탈락 기사의 정확한 게재일과 실증 회차는 원문 재확인 필요.