# Source Map

## 로컬 공식 자료

| 자료 | 위치 | Git 추적 | 설명 |
|------|------|----------|------|
| 공식 배포 데이터 | `data/raw/open/` | 원본 파일 미추적, manifest만 추적 | train/test/sample/info/data_description 로컬 미러 |
| 데이터 manifest | `data/raw/open/MANIFEST.md` | 추적 | 파일 크기와 SHA256 |
| 공식 baseline | `references/official/notebooks/baseline.ipynb` | 추적 | RandomForest baseline |
| 공식 평가 코드 | `references/official/notebooks/evaluation_metric.ipynb` | 추적 | total score, 1-NMAE, FICR |
| 최종 설계서 | `docs/design/04-final-solution-blueprint.md` | 추적 | 공식 데이터 공개 후 실행 설계 |

## 공식/외부 웹 출처

| 출처 | 핵심 내용 | URL |
|------|-----------|-----|
| DACON 개요 | 풍력발전량 예측 과제, 1차/2차 평가 구조, 주최/주관 | https://dacon.io/competitions/official/236727/overview/description |
| DACON 평가 | Score = 0.5 x 1-NMAE + 0.5 x FICR, Public/Private, 제출 자료 | https://dacon.io/competitions/official/236727/overview/evaluation |
| DACON 규칙 | Data Leakage, 외부 데이터, 사전학습모델, API 기반 모델 제한 | https://dacon.io/competitions/official/236727/overview/rules |
| 산업부/KPX 제도 도입 보도 | 하루 전 재생에너지 발전량 예측 제출과 정산금 지급 제도 배경 | https://eiec.kdi.re.kr/policy/materialView.do?num=205187 |
| KPX 전력시장운영규칙 | 재생에너지 예측오차율 정의 확인 후보 | https://marketrule.kpx.or.kr |
| 풍력 예측 연구 | 복잡 지형 풍력 예측, NWP 후처리, ML 기반 발전량 예측 연구 | https://www.mdpi.com/1996-1073/18/2/350 |

## 우선 신뢰 순서

1. 대회 공식 페이지와 공식 배포 파일
2. 공식 평가 코드와 sample submission
3. 전력시장 관련 기관 자료
4. 논문/기관 보고서
5. 기사/블로그/커뮤니티

대회 규칙과 외부 제도 설명이 충돌하면 대회 공식 기준을 우선합니다.
