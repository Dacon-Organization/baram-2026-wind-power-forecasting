# Perplexity 추가 조사 브리프

> 현재 Codex 세션에서는 Perplexity 커넥터가 없으므로, 공식 웹 출처 확인과 Perplexity용 프롬프트 패키지 작성까지 수행했다. 다음 세션 또는 사용자가 직접 Perplexity Space에서 아래 프롬프트를 실행한다.

## 업로드 또는 첨부 권장 자료

공식 데이터 파일 업로드는 대회 규정과 팀 판단을 확인한 뒤에만 수행합니다. 우선은 아래 문서만 사용합니다.

- `docs/design/04-final-solution-blueprint.md`
- `llm-wiki/00-source-map.md`
- `llm-wiki/01-problem-definition.md`
- `llm-wiki/02-requirements.md`
- `llm-wiki/03-market-research.md`
- 공식 DACON URL 3개: overview, evaluation, rules

## Session P3-1: 요구사항 정의 재검증

```text
You are helping with the DACON BARAM 2026 wind power forecasting competition.

Use only official DACON pages, the attached project docs, and primary/public institutional sources.

Task:
Now that official data, baseline, and evaluation metric code are available, refine the requirements definition.

Return in Korean:
1. Functional requirements for train/inference, metric reproduction, submission generation, experiment tracking.
2. Data governance requirements for official raw data, external data, point-in-time validation, and reproducibility.
3. Risks that can cause disqualification or score recovery failure.
4. A prioritized backlog for the next 72 hours.

Clearly separate official facts, local project decisions, and recommendations.
```

## Session P3-2: 문제 정의와 발표 서사

```text
Build a presentation-ready problem definition for DACON BARAM 2026.

Context:
- Forecast hourly wind power for 3 KPX groups in 2025.
- Inputs: LDAPS/GFS forecast grids, train labels, train SCADA.
- Score: 0.5 * 1-NMAE + 0.5 * FICR.
- Evaluation excludes hours where actual generation is below 10% of capacity.
- Need train/inference reproducibility and final presentation.

Return in Korean:
1. One-sentence problem definition.
2. Why this is not just a generic regression problem.
3. The three core technical challenges.
4. The three operational/reproducibility challenges.
5. Five slide titles with one key message each.
```

## Session P3-3: 시장·제도 조사

```text
Research the Korean renewable energy generation forecasting system and wind power forecasting market context.

Use official/institutional sources first:
- MOTIE, KPX, KDI, KMA, IEA, NREL, academic reviews.

Return in Korean:
1. Why day-ahead renewable generation forecasting matters for grid operation.
2. How settlement/incentive systems connect forecast error to revenue.
3. Whether wind forecasting has different difficulty or policy treatment from solar.
4. How DACON's FICR metric relates to but may differ from the real system.
5. Source-backed claims suitable for a 10-minute presentation.

Mark uncertain or non-official information explicitly.
```

## Session P3-4: 모델링 리서치

```text
Research short-term wind power forecasting methods using NWP data and turbine SCADA.

Competition constraints:
- No remote inference APIs.
- Evaluation period SCADA is unavailable.
- Need point-in-time safe features.
- Need reproducible local Python code.

Return in Korean:
1. Best practices for gridded NWP feature engineering.
2. How to use train SCADA without leakage.
3. Validation schemes for 2022-2024 train and 2025 hidden test.
4. Calibration ideas for threshold-based FICR.
5. Which methods are realistic for a 6-week competition.
```

## 반입 포맷

Perplexity 결과를 가져올 때는 아래 형식을 유지합니다.

```markdown
## Perplexity Session Result

- Session:
- Date:
- Mode/Model:
- Uploaded files:

### Official Facts

### External Research Findings

### Project Decisions To Update

### Risks / Uncertainties

### Next Actions
```
