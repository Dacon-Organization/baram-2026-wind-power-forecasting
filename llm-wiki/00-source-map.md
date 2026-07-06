# Source Map

## 로컬 공식 자료

| 자료 | 위치 | Git 추적 | 설명 |
|------|------|----------|------|
| 공식 배포 데이터 | `data/raw/open/` | 원본 파일 미추적, manifest만 추적 | train/test/sample/info/data_description 로컬 미러 |
| 데이터 manifest | `data/raw/open/MANIFEST.md` | 추적 | 파일 크기와 SHA256 |
| 공식 baseline | `references/official/notebooks/baseline.ipynb` | 추적 | RandomForest baseline |
| 공식 평가 코드 | `references/official/notebooks/evaluation_metric.ipynb` | 추적 | total score, 1-NMAE, FICR |
| 최종 설계서 | `docs/design/04-final-solution-blueprint.md` | 추적 | 공식 데이터 공개 후 실행 설계 |

## 로컬 리서치 원문

| 자료 | 위치 | 설명 |
|------|------|------|
| P3-1 요구사항 재검증 | `llm-wiki/research/2026-07-06-p3-1-requirements-revalidation.md` | 공식 평가·규칙 공개 후 요구사항, 리스크, 72시간 백로그 재분류 |
| P3-2 문제 정의와 발표 서사 | `llm-wiki/research/2026-07-06-p3-2-problem-narrative.md` | 단순 회귀와 다른 점, 10분 발표 흐름, 피해야 할 표현 |
| P3-3 시장 및 제도 조사 | `llm-wiki/research/2026-07-06-p3-3-market-policy.md` | KPX 예측제도, FICR와 실제 제도 차이, 풍력 예측 난점 |
| P3-4 모델링 리서치 | `llm-wiki/research/2026-07-06-p3-4-modeling-research.md` | NWP 피처, SCADA 활용 안전선, validation, FICR 보정 후보 |

## 공식/외부 웹 출처

| 출처 | 핵심 내용 | URL |
|------|-----------|-----|
| DACON 개요 | 풍력발전량 예측 과제, 1차/2차 평가 구조, 주최/주관 | https://dacon.io/competitions/official/236727/overview/description |
| DACON 평가 | Score = 0.5 x 1-NMAE + 0.5 x FICR, Public/Private, 제출 자료 | https://dacon.io/competitions/official/236727/overview/evaluation |
| DACON 규칙 | Data Leakage, 외부 데이터, 사전학습모델, API 기반 모델 제한 | https://dacon.io/competitions/official/236727/overview/rules |
| 산업부/KPX 제도 도입 보도 | 하루 전 재생에너지 발전량 예측 제출과 정산금 지급 제도 배경 | https://eiec.kdi.re.kr/policy/materialView.do?num=205187 |
| KPX 전력시장운영규칙 | 재생에너지 예측오차율 정의 확인 후보 | https://marketrule.kpx.or.kr |
| IEA Wind Task 25 | day-ahead 풍력 예측, 계통 균형, 변동성·aggregation 근거 | https://iea-wind.org |
| NREL 풍력 예측 자료 | 풍력 예측 오차, 램프 이벤트, 계통 운영 참고 | https://docs.nrel.gov |
| 해줌 제도 변경 공지 | 2025 예측제도 오차율 기준 강화 참고. KPX 원문 재검증 필요 | https://blog.haezoom.com/notice_05/ |
| 풍력 예측 연구 | 복잡 지형 풍력 예측, NWP 후처리, ML 기반 발전량 예측 연구 | https://www.mdpi.com/1996-1073/18/2/350 |

## 우선 신뢰 순서

1. 대회 공식 페이지와 공식 배포 파일
2. 공식 평가 코드와 sample submission
3. 전력시장 관련 기관 자료
4. 논문/기관 보고서
5. 기사/블로그/커뮤니티

대회 규칙과 외부 제도 설명이 충돌하면 대회 공식 기준을 우선합니다.
