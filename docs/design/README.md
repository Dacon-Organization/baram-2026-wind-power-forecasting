# 설계 문서

이 폴더는 전략 PRD 이후의 실행 설계를 보관합니다.

## 문서 목록

| 문서 | 목적 |
|------|------|
| [02-data-modeling-spec.md](02-data-modeling-spec.md) | 공식 데이터 공개 전 준비 가능한 스키마 검증, cutoff, 피처, 검증, 모델 후보, Perplexity 운영 설계 |
| [03-operations-master-plan.md](03-operations-master-plan.md) | 공식 데이터 공개 전 리더보드 제출, 실험 추적, 산출물 검증, 발표 평가 준비 |
| [04-final-solution-blueprint.md](04-final-solution-blueprint.md) | 공식 데이터·평가 코드·baseline 공개 후 최종 데이터 분석, 모델링, 발표 산출물 설계 · 7.1절 M0~M3 완료, 작업 모델 `lgbm_pooled`, 다음은 M6 calibration |
| [05-feature-set-promotion.md](05-feature-set-promotion.md) | 노트북 랩에서 검증된 피처 3종의 production 승격, 피처셋 config 레이어, 첫 리더보드 제출 설계 · v1.1 구현 완료(G1~G5 통과) · 제출 대기 |
| [06-preprocessing-guardrails.md](06-preprocessing-guardrails.md) | 전처리 허용 범위와 금지 항목, fit 경계 규칙, 과적합 위험 평가, 용어 사용 규범, 자가 점검 체크리스트 · v1.4 판정표 첫째 칸에도 부호 조건(크기가 문턱을 넘어도 부호가 흔들리면 미확정) |

## 작성 전제

2026-07-06 공식 데이터 공개 전 문서는 가정과 재검증 항목을 분리하고,
공개 후 문서는 실제 파일명, 컬럼명, 단위, 결측 패턴, 타임스탬프 기준을 확인한 뒤 작성합니다.
사전 워크숍 사진에서 얻은 정보는 출발점일 뿐, 공식 데이터 스키마보다 우선하지 않습니다.
