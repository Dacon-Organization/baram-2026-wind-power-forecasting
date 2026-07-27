# 05. 피처셋 승격과 첫 제출 파이프라인 설계

> 작성일: 2026-07-27 KST
> 버전: v1.0
> 상태: 설계 확정 · 구현 대기
> 선행 문서: [04-final-solution-blueprint.md](04-final-solution-blueprint.md)
> 선행 작업: PR #6 Feature Lab 이관, PR #7 터빈 공간 풀링 피처 실험
> 범위: 노트북 랩에서 검증된 피처 3종을 production 파이프라인으로 승격하고, 첫 리더보드 제출까지.
> 범위 밖: GBM 도입, seasonal fold, metric-aware calibration, 잔여 물리 피처.

---

## 0. 이 설계의 결론

| 항목 | 결론 |
|------|------|
| 문제 | 세 번의 피처 랩이 노트북 안에서만 검증되고 production 파이프라인에 반영되지 않았다 |
| 조치 | 피처셋을 1급 config로 승격하고, 조립기 하나가 train/test를 대칭으로 만든다 |
| 프리셋 | 4종 (`official_mean`, `expanded_vector`, `spatial_idw2_all_group`, `spatial_nearest_own_group`) |
| 지정 방식 | 코드 내 named preset을 기본으로 하고 YAML 부분 오버라이드를 허용 |
| 기본값 | `official_mean` — 인자 없이 호출하면 승격 전과 100% 동일 동작 |
| 재현성 | `PREPROCESSING_CONTRACT`를 config에서 파생하고 metadata sidecar에 피처셋을 각인 |
| 제출 | S1으로 `official_mean` smoke, S2로 채택 후보를 올려 local↔Public 기울기를 측정 |
| 게이트 | golden 회귀 · 노트북 점수 재현 · validator 통과를 모두 넘어야 제출 |

---

## 1. 배경 — 왜 지금 승격인가

### 1.1 누적된 랩 성적 (모두 동일 RandomForest · 2024 time holdout)

| 단계 | 노트북 | features | total score | 누적 Δ |
|------|--------|---------:|------------:|-------:|
| 공식 baseline (grid mean) | 02 | 74 | 0.576938 | 기준 |
| + grid 통계 / lead | 06 | 271 | 0.585265 | +0.008327 |
| + wind vector | 07 | 319 | 0.586482 | +0.009544 |
| + turbine IDW p=2 (all-group) | 08 | 550 | **0.592485** | **+0.015547** |
| + turbine nearest (own-group) | 08 | 396 | 0.589828 | +0.012890 |

### 1.2 그런데 production은 여전히 0.576938

`src/baram/train.py` → `src/baram/baseline.py` 경로는 `groupby("forecast_kst_dtm").mean()` 74개 피처만 사용한다.
`src/baram/features/` 아래 세 모듈은 공개 API로 export되어 있지만 **어떤 실행 경로에서도 호출되지 않는다.**

즉 지금 제출 버튼을 눌러 나오는 파일은 랩에서 검증한 개선분이 하나도 반영되지 않은 공식 baseline이다.

### 1.3 일정 압박

| 항목 | 값 |
|------|-----|
| 대회 마감 | 2026-08-14 10:00 KST |
| 설계 시점 | 2026-07-27 KST |
| 남은 기간 | 18일 |
| 리더보드 제출 이력 | **0회** |
| 제출 한도 | 1일 5회 |

local 점수만 18일 더 올려도 Public/Private과의 기울기를 모르면 최종 파일 선택 근거가 없다.
첫 제출을 이번 작업 안에 넣는 이유다.

---

## 2. 현재 코드가 승격을 막는 지점

승격이 단순 배선이 아닌 이유는 아래 세 가지다.

### 2.1 `build_weather_features` 이름 충돌

| 위치 | 시그니처 | 사용처 |
|------|----------|--------|
| `baram.baseline.build_weather_features` | `(ldaps_frame, gfs_frame)` — mean 고정, 파라미터 없음 | production `train.py` |
| `baram.features.weather_grid.build_weather_features` | `(ldaps_frame, gfs_frame, *, statistics, include_lead, source_prefixes, std_ddof)` | 노트북 랩 |

같은 이름의 두 함수가 다른 계약을 가진다. 조립 계층 없이는 섞을 수 없고, 한쪽을 지우면 기존 테스트가 깨진다.

**결정:** 둘 다 유지한다. `baram.baseline` 쪽은 `official_mean` 경로 전용 legacy로 남기고,
새 조립기는 `baram.features.weather_grid` 쪽만 호출한다. legacy 함수에 deprecation 주석만 남긴다.

### 2.2 터빈 좌표 로더가 `src`에 없다

`fit_turbine_spatial_pooler(train_weather, turbine_locations, ...)`는
`("turbine_id", "group_id", "latitude", "longitude", "capacity_mw")` 컬럼을 가진 DataFrame을 요구한다.

그런데 `info.xlsx`를 읽어 DMS 좌표를 십진수로 변환하고 17기·3그룹으로 정규화하는 코드는
**노트북 08 셀 안에 인라인으로만 존재한다.** `src` 어디에도 없다.

**결정:** `src/baram/features/turbine_metadata.py`로 승격한다. 로더 없이는 공간 피처 프리셋을 실행할 수 없다.

### 2.3 `PREPROCESSING_CONTRACT`가 하드코딩이다

`src/baram/registry.py:32`의 상수 dict에 `"statistics": ["mean"]`이 박혀 있다.
이 dict의 SHA-256이 `preprocessing_sha256`로 model metadata와 run registry에 기록된다.

피처를 바꾸고 이 상수를 그대로 두면 **전처리가 달라졌는데 hash는 같은** 상태가 된다.
재현성 레이어 전체가 거짓 신호를 내는 지점이므로 승격과 동시에 반드시 고쳐야 한다.

**결정:** `build_preprocessing_contract(config)`로 파생시키고,
`official_mean` config가 기존 dict와 **바이트 동일**함을 golden 테스트로 잠근다.

### 2.4 (own-group 선택으로 추가된 이슈) bundle이 단일 feature 목록만 가진다

`RandomForestBaselineBundle.feature_columns`는 리스트 하나이고, 세 target이 이를 공유한다.
그러나 own-group 프리셋은 target마다 다른 컬럼 집합을 쓴다.

| scope | 공통 | 그룹별 | target별 사용 컬럼 |
|-------|-----:|-------:|-------------------:|
| all-group | 319 | 231 (77 × 3그룹) | 550 (세 target 동일) |
| own-group | 319 | 77 (자기 그룹만) | 396 (target마다 다름) |

**결정:** superset 접근을 쓴다.

- `build_feature_pipeline`은 scope와 무관하게 **항상 all-group superset(550)** matrix를 만든다.
- bundle에 `target_feature_columns: dict[str, tuple[str, ...]]`를 추가한다.
- `all_group` scope면 세 target 모두 superset 전체를 가리킨다 → **기존 동작과 완전히 동일**.
- `own_group` scope면 target별로 공통 + 자기 그룹 컬럼만 가리킨다.
- imputer는 superset에 fit한다. median은 컬럼 단위 통계라 부분집합에 fit한 결과와 값이 같다.
  이 등가성은 테스트로 잠근다.

---

## 3. 목표와 비목표

### 3.1 목표

1. 검증된 피처 3종을 CLI 한 줄로 선택 가능한 production 경로로 만든다.
2. 승격 전 동작을 회귀 없이 보존한다.
3. 노트북 08의 2024 holdout 점수를 production 코드로 재현한다.
4. 제출 CSV를 만들어 리더보드 신호 2점(smoke, 채택 후보)을 확보한다.
5. 어떤 제출물이 어떤 피처셋에서 나왔는지 metadata로 추적 가능하게 한다.

### 3.2 비목표

| 항목 | 이유 |
|------|------|
| GBM(LightGBM/CatBoost) 도입 | 별도 모델 계층 작업. 피처셋 config가 선행되어야 실험 조합이 폭발하지 않는다 |
| seasonal/time fold (F1~F4) | 별도 validation 작업 |
| metric-aware calibration | 모델·fold가 잠긴 뒤 |
| hub-height·air density 등 잔여 물리 피처 | 피처 랩 4번째 주제 |
| dependabot PR #2~#5 머지 | 9절 참조 |

---

## 4. 아키텍처

### 4.1 모듈 구성

```text
src/baram/
├── feature_config.py          [신규] FeatureSetConfig, 프리셋 4종, YAML 해석기
├── feature_pipeline.py        [신규] build_feature_pipeline 조립기
├── features/
│   ├── turbine_metadata.py    [신규] info.xlsx → 터빈 좌표/용량 로더
│   ├── weather_grid.py        [변경 없음]
│   ├── wind_vector.py         [변경 없음]
│   └── turbine_spatial.py     [변경 없음]
├── baseline.py                [수정] bundle에 target_feature_columns 추가
├── registry.py                [수정] contract 파생 + metadata schema 1.1
├── train.py                   [수정] --feature-set / --feature-set-config
└── inference.py               [수정] metadata에서 피처셋 자동 복원

configs/feature_sets/          [신규] YAML 오버라이드 보관 (선택 사용)

notebooks/
├── 09_feature_set_contract_lab.ipynb        [신규] 계약 검증
├── 10_feature_pipeline_assembly_lab.ipynb   [신규] 조립·등가성 검증
└── 11_promotion_scoreboard.ipynb            [신규] 점수 재현·제출 후보
```

### 4.2 `FeatureSetConfig` 스키마

```python
@dataclass(frozen=True)
class SpatialPoolingConfig:
  methods: tuple[str, ...]      # ("nearest",) | ("idw",) | ("nearest", "idw")
  idw_power: float              # methods에 "idw"가 없으면 무시하지 않고 검증만 통과
  scope: str                    # "all_group" | "own_group"

@dataclass(frozen=True)
class FeatureSetConfig:
  name: str
  statistics: tuple[str, ...]   # SPATIAL_STATISTICS 부분집합, 순서 고정
  include_lead: bool
  wind_vector: bool
  spatial: SpatialPoolingConfig | None
  calendar: bool = True
```

검증 규칙:

- `statistics`는 `("mean", "std", "min", "max")` 순서를 유지한 부분집합만 허용한다. 순서가 바뀌면 컬럼 순서가 바뀌어 재현이 깨진다.
- `spatial is not None`이면 터빈 좌표가 반드시 필요하다. 없으면 **조용히 건너뛰지 않고 즉시 실패**한다.
- 알 수 없는 필드는 생성 시점에 거부한다.

### 4.3 프리셋 4종

| preset 이름 | statistics | lead | vector | spatial | scope | features | 랩 total | 역할 |
|-------------|-----------|:----:|:------:|---------|-------|---------:|---------:|------|
| `official_mean` | mean | ✗ | ✗ | 없음 | — | 74 | 0.576938 | 통제군 · 기본값 · 회귀 기준 |
| `expanded_vector` | mean/std/min/max | ✓ | ✓ | 없음 | — | 319 | 0.586482 | 직전 단계 통제군 |
| `spatial_idw2_all_group` | mean/std/min/max | ✓ | ✓ | idw p=2 | all_group | 550 | **0.592485** | **채택 후보** |
| `spatial_nearest_own_group` | mean/std/min/max | ✓ | ✓ | nearest | own_group | 396 | 0.589828 | 축소·강건성 대안 |

랩에서 비교한 IDW p=1, own-group IDW p=2는 프리셋으로 승격하지 않는다.
필요하면 4.4의 YAML 오버라이드로 재현할 수 있다.

### 4.4 YAML 오버라이드 규약

프리셋이 기본이고, YAML은 **기존 프리셋을 상속해 일부만 덮어쓰는 용도**로만 쓴다.
YAML만으로 처음부터 config를 정의하는 것은 허용하지 않는다 — 검증 표면을 좁게 유지하기 위해서다.

```yaml
# configs/feature_sets/spatial_idw1.yaml
extends: spatial_idw2_all_group
overrides:
  spatial:
    idw_power: 1.0
```

| 규칙 | 내용 |
|------|------|
| `extends` | 필수. 프리셋 이름이 아니면 실패 |
| `overrides` | 선택. `FeatureSetConfig` 필드명만 허용 |
| 알 수 없는 키 | **즉시 실패**. 조용한 무시는 오타를 잠복시킨다 |
| 중첩 병합 | `spatial`만 dict 부분 병합. 나머지는 전체 치환 |
| `name` | 오버라이드하면 그 값, 아니면 `<extends>+<파일 stem>` |
| 파서 | PyYAML `safe_load`만 사용 |

### 4.5 조립 순서 계약 (재현의 핵심)

노트북 08과 컬럼 **이름과 순서**가 모두 같아야 RandomForest(`max_features="sqrt"`)가 같은 점수를 낸다.
따라서 순서를 계약으로 고정한다.

```text
raw LDAPS / GFS grid 행
   │
   ├─ ① derive_wind_vector_features(source=...)     # raw 행 단위에 speed·wind-from sin/cos 추가
   │     (config.wind_vector == True 일 때만)
   │
   ├─ ② aggregate_weather_grid(statistics, include_lead)  # forecast 시각 단위 집계
   │     LDAPS 먼저, GFS 다음
   │
   ├─ ③ TurbineSpatialPooler.transform(...)          # ①의 결과 raw 행에서 그룹별 pooling
   │     (config.spatial is not None 일 때만)
   │     컬럼 순서: raw_feature → group_id → method
   │
   └─ ④ calendar_features(forecast_kst_dtm)          # 최종 concat 시 맨 앞
```

최종 feature matrix 컬럼 순서: `calendar → ldaps 집계 → gfs 집계 → ldaps pooling → gfs pooling`

**공간 pooling은 ①의 wind vector 파생이 끝난 raw 행을 입력으로 받는다.**
집계 결과가 아니라 raw 행이다. 순서를 바꾸면 pooling 대상 변수 집합이 달라져 재현이 깨진다.

### 4.6 fit / transform 경계

| 대상 | fit 범위 | 비고 |
|------|----------|------|
| `TurbineSpatialPooler` | train weather의 grid geometry | transform 시 geometry drift 검사 |
| median imputer | train feature matrix (superset) | test는 transform만 |
| RandomForest | target별 non-null mask | 기존 계약 유지 |

label, holdout, test 통계는 어떤 fit에도 사용하지 않는다.

---

## 5. 재현성 레이어 변경

### 5.1 `PREPROCESSING_CONTRACT` 파생

`build_preprocessing_contract(config) -> dict`로 대체한다. config에서 파생되는 항목:

| contract 키 | 파생 소스 |
|-------------|-----------|
| `weather_aggregation.statistics` | `config.statistics` |
| `lead_feature` | `config.include_lead` (False면 키 자체를 뺀다) |
| `wind_vector` | `config.wind_vector` + 사용한 `WindVectorSpec` 목록 |
| `spatial_pooling` | `config.spatial`의 methods · idw_power · scope · 터빈 수 · 그룹 용량 |
| `calendar_features` | 기존 9개 고정 |
| `missing_values` / `target_training` / `prediction_bounds` | 기존 값 유지 |

**불변 조건:** `build_preprocessing_contract(FEATURE_SETS["official_mean"])`의 직렬화 결과가
현재 `PREPROCESSING_CONTRACT`와 바이트 단위로 동일해야 한다. → G2 golden 테스트.

### 5.2 metadata sidecar 확장

`MODEL_METADATA_SCHEMA_VERSION`을 `"1.0"` → `"1.1"`로 올리고 블록을 추가한다.

```json
"feature_set": {
  "name": "spatial_idw2_all_group",
  "source": "preset",
  "resolved_sha256": "<정규화 JSON의 sha256>",
  "scope": "all_group",
  "feature_count": 550,
  "target_feature_counts": {"kpx_group_1": 550, "kpx_group_2": 550, "kpx_group_3": 550}
}
```

하위 호환: schema 1.0 sidecar를 읽으면 `official_mean` · `source: "legacy"`로 간주한다.

### 5.3 `config_sha256` 정규화 규칙

YAML 포맷 차이가 hash를 흔들면 안 되므로, hash는 **해석이 끝난 최종 config**에서 계산한다.

| 규칙 | 내용 |
|------|------|
| 직렬화 | `json.dumps(..., sort_keys=True, ensure_ascii=False, separators=(",", ":"))` |
| float | `repr()` 대신 `format(value, ".10g")`로 고정 |
| tuple | list로 변환하되 순서 보존 |
| 결과 | 같은 최종 config면 preset 경로든 YAML 경로든 **동일 hash** |

---

## 6. CLI 인터페이스

### 6.1 `train.py` 추가 인자

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--feature-set` | `official_mean` | 프리셋 이름 |
| `--feature-set-config` | 없음 | YAML 오버라이드 경로. `--feature-set`와 동시 지정 시 실패 |
| `--info-xlsx` | 없음 | 공식 `info.xlsx` 경로. 공간 프리셋이면 필수 |

### 6.2 `inference.py`

피처셋을 **수동 지정하지 않는다.** model metadata sidecar의 `feature_set` 블록에서 복원한다.
`--info-xlsx`만 추가로 받는다(공간 프리셋일 때 필수).

복원한 config로 만든 feature 컬럼 목록이 bundle의 `feature_columns`와 다르면 즉시 실패한다.
train/inference 피처셋 불일치는 조용히 지나가면 안 되는 사고다.

### 6.3 실행 예시

```bash
python -m baram.train --run --feature-set spatial_idw2_all_group --info-xlsx data/raw/open/info.xlsx
```

worktree에는 원자료가 없으므로(`.gitignore`) 경로는 메인 저장소의 `data/raw/open/`를 가리킨다.

---

## 7. 검증 계획

### 7.1 TDD 순서

기존 랩과 동일하게 RED → GREEN으로 간다. 공개 API를 `NotImplementedError` 스텁으로 먼저 두고,
계약 테스트가 전부 실패하는 것을 확인한 뒤 최소 구현한다.

테스트 대상 계약:

| 영역 | 검사 항목 |
|------|-----------|
| config | 프리셋 4종 필드값, statistics 순서 위반 거부, 알 수 없는 필드 거부 |
| YAML | `extends` 누락·오타 키·잘못된 프리셋 이름 거부, 부분 병합, hash 동등성 |
| 조립기 | 컬럼 이름·순서 계약, train/test 대칭, 입력 프레임 불변 |
| 공간 | 터빈 좌표 없이 공간 프리셋 실행 시 실패 |
| own-group | target별 컬럼 집합, superset median == 부분집합 median |
| contract | `official_mean` 파생 결과 == 기존 상수 (바이트 동일) |
| metadata | schema 1.1 왕복, 1.0 하위 호환 |
| CLI | 인자 조합 검증, train/inference 피처셋 불일치 감지 |

### 7.2 제출 전 게이트

| ID | 게이트 | 통과 기준 |
|----|--------|-----------|
| G1 | 전체 테스트 | `python -m pytest -q` — 기존 105건 + 신규 전부 통과 |
| G2 | golden 회귀 | `official_mean`의 feature 컬럼 목록 · `preprocessing_sha256` · submission SHA-256이 승격 전과 동일 |
| G3 | 점수 재현 | `spatial_idw2_all_group`의 2024 holdout total score가 노트북 08의 `0.592485`와 일치 |
| G4 | 노트북 무결성 | `python scripts/check_notebook_integrity.py` 00~08 통과 |
| G5 | 제출물 검증 | submission validator 통과 + run registry에 run·submission hash 기록 |

**G3가 실패하면 제출하지 않고 정지한다.** 재현 실패는 조립 순서 계약 위반이라는 뜻이고,
그 상태의 제출물은 무엇을 측정하는지 알 수 없다.

허용 오차: RandomForest는 seed 고정 시 `n_jobs`와 무관하게 결정론적이므로 `1e-9`를 넘는 차이는 실패로 본다.

### 7.3 검증 노트북 — 단계별 분리

`.py` 단위 테스트는 계약이 깨졌는지만 알려준다. 왜 그렇게 설계했고 어떤 근거로 채택했는지는
실행 결과가 남는 분석 노트북에 기록한다. 이는 03조 노트북 서사 구조를 BARAM 표준으로 채택한
`04-final-solution-blueprint.md` 1.1절 결정의 연장이다.

**한 노트북에 전 과정을 담지 않는다.** 단계별로 분리해 각 노트북이 하나의 질문만 닫는다.

| 노트북 | 닫는 질문 | Decision Box |
|--------|-----------|--------------|
| `09_feature_set_contract_lab.ipynb` | 피처셋을 config로 표현하면 재현성 계약이 유지되는가 | ①~⑤ |
| `10_feature_pipeline_assembly_lab.ipynb` | 조립 순서와 fit 경계가 train/test 대칭을 보장하는가 | ⑥~⑩ |
| `11_promotion_scoreboard.ipynb` | 승격한 파이프라인이 랩 점수를 재현하고 제출 가능한가 | ⑪~⑮ |

서사 규약:

| 규약 | 내용 |
|------|------|
| 도입 | 첫 셀에 연구 질문과 목차를 제시한다 |
| Decision Box | 노트북을 가로질러 ①부터 연속 번호를 매긴다. 선택지·근거·채택을 함께 적는다 |
| 소제목 | 결과 절의 제목은 주장문으로 쓴다. "① 재현성 계약 결과"가 아니라 "official_mean은 파생 후에도 같은 hash를 유지한다" |
| 파일럿 → 전체 | 작은 표본으로 먼저 검증하고 전체를 실행한다 |
| robustness | 채택 근거가 파라미터 하나에 의존하면 sweep 절을 덧붙인다 |
| 해석 | 모든 코드 셀 뒤에 관찰·해석·다음 판단 문단을 둔다 |
| 종합 결론 | 마지막에 연구 질문 / 단계별 요약 / 주요 발견 / 시사점 / 한계 / 요약 6소절 |

무결성 제약(`scripts/check_notebook_integrity.py`):

- `consecutive_code_pairs == 0` — **코드 셀이 연달아 오면 실패한다.** 해석 마크다운이 반드시 사이에 있어야 한다.
- `missing_execution == 0`, `error_outputs == 0` — 실제로 실행해 출력이 남은 상태로 저장해야 한다.
- `replacement_chars == 0`, `triple_question_runs == 0` — 한글 인코딩 깨짐 금지.

---

## 8. 제출 운영

`03-operations-master-plan.md`의 슬롯 규칙을 따른다.

| 슬롯 | 피처셋 | 목적 | 판단 |
|------|--------|------|------|
| S1 | `official_mean` | 형식·인코딩·행수·파이프라인 smoke | Public 점수가 나오는지, 형식 오류가 없는지 |
| S2 | `spatial_idw2_all_group` | 채택 후보 | S1 대비 Public Δ가 local Δ(+0.015547)와 같은 방향인지 |

두 점을 얻으면 local↔Public 기울기를 처음으로 추정할 수 있다.
같은 날 두 슬롯을 쓰되, S3~S5는 이번 작업에서 소모하지 않는다.

제출 전 `submission_ledger`에 목적·실험 ID·commit·데이터 버전·seed·예상 리스크를 기록하고,
제출 후 Public score·파일명·Dacon 제출 ID를 registry에 채운다.

**제출 버튼은 사용자가 직접 누른다.** 에이전트는 검증을 통과한 CSV와 ledger 행까지만 준비한다.

---

## 9. 리스크와 완화

| ID | 리스크 | 영향 | 완화 |
|----|--------|------|------|
| R1 | 노트북 점수 재현 실패 | 제출물이 무엇을 측정하는지 불명 | G3 게이트에서 정지. 컬럼 순서를 노트북과 1:1 대조 |
| R2 | 기존 파이프라인 회귀 | 되돌릴 기준선을 잃음 | 기본값 `official_mean` + G2 golden 테스트 |
| R3 | own-group bundle 스키마 변경 | 기존 테스트·저장된 모델 호환성 | all-group일 때 superset 전체를 가리켜 동작 동일. metadata 1.0 하위 호환 유지 |
| R4 | 550 feature RF 학습 시간 | 반복 실험 지연 | 먼저 dry-run으로 측정. 필요하면 `--n-estimators` 조정하되 제출 후보는 공식 파라미터 유지 |
| R5 | 2025 test의 LDAPS 47개 forecast-variable 쌍 전 grid 결측 | 예측 품질 저하 | 기존 계약 유지 — NaN 보존 후 train-fit median. 공간 pooling으로 복원하지 않는다 |
| R6 | `info.xlsx`가 CI에 없음 | 공간 테스트 불가 | 계약 테스트는 fixture 좌표로 수행. 실제 로더 테스트는 파일 존재 시에만 실행 |
| R7 | `PyYAML`·`openpyxl`이 `requirements-ci.txt`에 없음 | CI 실패 | 두 의존성을 CI 요구사항에 추가 (버전 고정) |
| R8 | dependabot PR #2~#5 (pandas 3.0.3, numpy 2.5.1, sklearn 1.9.0, pytest 9.1.1) | 마감 18일 전 대규모 breaking change | **마감까지 보류.** pandas 3.0은 dtype·copy 의미가 바뀌어 랩 재현값이 흔들릴 수 있다. 대회 종료 후 일괄 처리 |
| R9 | GFS는 17기 전부 같은 grid가 nearest | 공간 피처의 GFS 기여가 제한적 | 랩에서 이미 기록된 한계. 이번 작업에서 해결하지 않고 계승 |

---

## 10. 롤백과 버전 관리 전략

문제 발생 시 복원 가능성을 최우선으로 둔다.

### 10.1 3중 안전장치

| 층 | 장치 | 복원 방법 |
|----|------|-----------|
| 코드 | 기본값이 `official_mean` | CLI 인자를 빼면 승격 전과 동일 동작 |
| 테스트 | G2 golden 회귀 | 회귀가 생기면 CI에서 즉시 잡힘 |
| Git | 8개 독립 커밋 | 문제 커밋만 `git revert` |

### 10.2 브랜치와 커밋 분할

브랜치: `feature/mygithub05253-feature-set-promotion`

| # | 커밋 | 동작 변화 | 단독 revert |
|---|------|-----------|-------------|
| 1 | `✨ Feat: FeatureSetConfig와 프리셋 4종 추가` | 없음 (호출부 없음) | 가능 |
| 2 | `✨ Feat: YAML 피처셋 오버라이드 해석기 추가` | 없음 | 가능 |
| 3 | `✨ Feat: 터빈 메타데이터 로더 승격` | 없음 | 가능 |
| 4 | `✨ Feat: 피처 파이프라인 조립기 추가` | 없음 | 가능 |
| 5 | `♻️ Refactor: bundle에 target별 feature 컬럼 도입` | 없음 (all-group 경로 동일) | 가능 |
| 6 | `✨ Feat: preprocessing contract 파생과 metadata schema 1.1` | hash 계산 경로 변경, 값은 동일 | 가능 |
| 7 | `✨ Feat: train/inference CLI 피처셋 연결` | **여기서 처음 동작 변화** | 가능 |
| 8 | `✅ Test: official_mean golden 회귀와 점수 재현 검증` | 없음 | — |
| 9 | `📝 Docs: 검증 노트북 09·10·11 추가` | 없음 | 가능 |
| 10 | `📝 Docs: 설계서 05 버전업과 대시보드 로그` | 없음 | — |

7번 커밋 이전까지는 production 경로가 전혀 바뀌지 않는다.
문제가 생기면 7번만 되돌려도 승격 전 상태로 복귀한다.

### 10.3 문서 버전 규칙

- 이 문서는 구현 중 버전을 올리지 않는다. 스펙 변경은 13절 결정 로그에 누적한다.
- 작업 완료 후 Minor(v1.1) 또는 Major(v2.0) 판단 후 **한 번에** 버전업한다.
- `docs/design/README.md` 색인을 함께 갱신한다.

---

## 11. 작업 순서

| 단계 | 내용 | 산출물 |
|------|------|--------|
| 1 | 계약 테스트 작성 (RED) | `tests/test_feature_config.py`, `tests/test_feature_pipeline.py`, `tests/test_turbine_metadata.py` |
| 2 | config·YAML·로더 구현 (GREEN) | 커밋 1~3 |
| 3 | 조립기·bundle 확장 구현 | 커밋 4~5 |
| 4 | contract 파생·metadata 1.1 | 커밋 6 |
| 5 | CLI 연결 | 커밋 7 |
| 6 | G1~G2 게이트 실행 | 커밋 8 |
| 7 | 검증 노트북 09·10·11 작성과 실행 | 커밋 9 |
| 8 | G3~G5 게이트 실행 | — |
| 9 | 제출 CSV 생성 + ledger 준비 | `outputs/submissions/` (미커밋) |
| 10 | 대시보드 로그 + 설계서 버전업 | 커밋 10 |

---

## 12. 다음 작업 후보 (기록만)

R3 원칙에 따라 아래는 이번 작업에서 착수하지 않는다.

| 우선순위 | 후보 | 선행 조건 |
|----------|------|-----------|
| P1 | seasonal/time fold(F1~F4)에서 프리셋 4종 민감도 확인 | 이번 승격 완료 |
| P2 | LightGBM/CatBoost 도입 (블루프린트 M2) | 피처셋 config 존재 |
| P3 | metric-aware calibration (M6) | 모델·fold 확정 |
| P4 | 잔여 물리 피처 — hub-height, air density, wind power density, LDAPS↔GFS source spread | — |
| P5 | dependabot PR #2~#5 일괄 처리 | 대회 종료 후 |

---

## 13. 결정 로그

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-07-27 | 다음 작업을 피처 승격 + 첫 제출로 확정 | GBM·fold·calibration이 모두 피처셋 config를 전제로 하고, 리더보드 신호가 0점이라 최종 파일 선택 근거가 없다 |
| 2026-07-27 | 프리셋 기본값을 `official_mean`으로 고정 | 인자 없는 호출이 승격 전과 동일해야 회귀 판단 기준이 남는다 |
| 2026-07-27 | preset을 기본으로 하고 YAML은 상속·부분 오버라이드로 제한 | 블루프린트의 `configs/*.yaml` 구조를 따르되 검증 표면을 좁게 유지 |
| 2026-07-27 | 프리셋을 4종으로 한정 | 통제군 2 + 채택 후보 1 + 강건성 대안 1. 나머지 랩 후보는 YAML로 재현 가능 |
| 2026-07-27 | own-group을 superset + target별 컬럼 슬라이스로 구현 | 파이프라인을 한 번만 돌리고, all-group일 때 기존 동작을 그대로 보존하기 위해 |
| 2026-07-27 | `PREPROCESSING_CONTRACT`를 config에서 파생 | 하드코딩 상수를 두면 전처리가 바뀌어도 hash가 같아 재현성 레이어가 거짓 신호를 낸다 |
| 2026-07-27 | inference는 피처셋을 metadata에서 자동 복원 | train/inference 피처셋 불일치를 수동 인자에 맡기지 않는다 |
| 2026-07-27 | `config_sha256`를 정규화 JSON에서 계산 | YAML 포맷 차이가 hash를 흔들지 않게 한다 |
| 2026-07-27 | S1 smoke → S2 채택 후보 2회 제출 | 두 점이 있어야 local↔Public 기울기를 추정할 수 있다 |
| 2026-07-27 | dependabot PR #2~#5를 마감까지 보류 | pandas 3.0 등 breaking change가 랩 재현값을 흔들 수 있고, 남은 기간이 18일이다 |
| 2026-07-27 | 검증을 `.py` 테스트와 분석 노트북 두 층으로 나눔 | 단위 테스트는 계약 위반만 알려주고 채택 근거를 남기지 않는다. 발표 자료로 재사용할 표와 해석이 필요하다 |
| 2026-07-27 | 노트북을 09·10·11 세 개로 분리 | 참고한 03조 노트북은 전 과정을 한 파일에 담았으나, 단계별로 나눠야 각 노트북이 질문 하나만 닫고 재실행 비용도 줄어든다 |
