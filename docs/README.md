# BARAM 문서 인덱스

이 폴더는 BARAM 2026 풍력발전량 예측 대회의 전략, 데이터, 모델링, 운영 문서를 관리합니다.

## 문서 구조

| 폴더 | 역할 |
|------|------|
| `groundwork/` | 사전 워크숍, 공식 안내, 시장/제도 맥락 기반 전략 문서 |
| `design/` | 데이터·모델링·실험·운영 설계 문서 |
| `../llm-wiki/` | 다음 세션 LLM이 바로 읽을 수 있는 source map, 문제 정의, 요구사항, 시장 조사, 복구 규칙, handoff |

## 작성 원칙

- 공식 데이터 공개 전 항목은 `확정`, `판독 불확실`, `공식 공개 후 재검증`, `추론`을 분리합니다.
- 사진에서 판독한 정보는 원본 파일명 또는 워크숍 슬라이드 맥락을 함께 적습니다.
- 외부 리서치는 모델 아이디어나 시장조사에는 사용할 수 있지만, 대회 데이터 사실로 승격하지 않습니다.
- 원격 API 기반 모델 추론은 규정상 금지되므로 설계 후보에서 제외합니다.

## 현재 문서

| 문서 | 상태 | 설명 |
|------|------|------|
| [01-strategy-prd.md](groundwork/01-strategy-prd.md) | 작성 완료 | 문제 정의, 데이터 팩트 레저, 평가/규정, 전략 요구사항 |
| [02-perplexity-research-synthesis.md](groundwork/02-perplexity-research-synthesis.md) | 작성 완료 | Perplexity 1회차 결과를 공식/외부/충돌/재검증/추론으로 재분류 |
| [03-perplexity-round2-question-pack.md](groundwork/03-perplexity-round2-question-pack.md) | 작성 완료 | 2차 Perplexity 재검증을 위한 R2-1~R2-6 세션별 프롬프트 패키지 |
| [04-perplexity-round2-results-synthesis.md](groundwork/04-perplexity-round2-results-synthesis.md) | 작성 완료 | R2-1~R2-6 재검증 결과 반입, 설계 반영 결정, 후속 세션 운영 가이드 |
| [02-data-modeling-spec.md](design/02-data-modeling-spec.md) | 작성 완료 | 스키마 검증, cutoff, 피처, validation, metric, Perplexity 운영 설계 |
| [03-operations-master-plan.md](design/03-operations-master-plan.md) | 작성 완료 | 공식 데이터 공개 전 제출 운영, 실험 추적, 외부 데이터 보류, 2차 검증 준비 계획 |
| [04-final-solution-blueprint.md](design/04-final-solution-blueprint.md) | 작성 완료 | 공식 데이터·평가 코드·baseline 공개 후 최종 데이터 분석, 모델링, 발표 산출물 설계 |
| [LLM Wiki](../llm-wiki/README.md) | 작성 완료 | 공식 데이터 미러, official notebook, 요구사항, 문제 정의, 시장 조사, 제출 복구, Perplexity 브리프, handoff |
| [P3 Perplexity 리서치 원문](../llm-wiki/research/README.md) | 작성 완료 | 요구사항 재검증, 발표 서사, 시장·제도 조사, 모델링 리서치 결과 원문 |

## 다음 문서 후보

1. 평가 산식 재현 코드와 metric 노트북 작성
   공식 `평가_산식 코드.ipynb`를 `src/baram/metrics.py`와 `01_metric_reproduction.ipynb`로 포팅

2. baseline RandomForest train/inference 분리
   공식 baseline을 재현 가능한 제출 파이프라인으로 정리
