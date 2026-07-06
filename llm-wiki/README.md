# BARAM 2026 LLM Wiki

이 폴더는 다음 세션의 LLM 또는 팀원이 바로 이어서 작업할 수 있도록 만든 압축 지식베이스입니다.

읽는 순서:

1. [00-source-map.md](00-source-map.md): 공식 데이터, baseline, 평가 코드, 외부 출처 위치
2. [01-problem-definition.md](01-problem-definition.md): 문제 정의와 성공 기준
3. [02-requirements.md](02-requirements.md): 데이터·모델·제출·재현성 요구사항
4. [03-market-research.md](03-market-research.md): 시장/제도 맥락과 발표용 근거
5. [04-versioning-recovery.md](04-versioning-recovery.md): 제출 실패 복구와 버전 관리 규칙
6. [90-perplexity-research-brief.md](90-perplexity-research-brief.md): Perplexity 추가 조사 프롬프트
7. [research/README.md](research/README.md): P3-1~P3-4 Perplexity 리서치 결과 원문
8. [99-session-handoff/2026-07-06-prep.md](99-session-handoff/2026-07-06-prep.md): 다음 세션 시작 프롬프트

주의:

- 원본 대회 데이터는 `data/raw/open/`에 로컬로만 보관하고 Git에는 넣지 않습니다.
- 공식 기준 변경 가능성이 있는 내용은 날짜와 출처를 같이 적습니다.
- LLM Wiki는 실행 코드가 아니라 의사결정, 맥락, 검증 기준을 고정하는 문서입니다.
- P3 리서치 원문은 `research/`에 보존하고, 실제 작업 우선순위는 `02-requirements.md`와 `docs/design/04-final-solution-blueprint.md`를 기준으로 합니다.
