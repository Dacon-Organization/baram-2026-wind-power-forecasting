# 데이터와 공식 자료 출처

## 공식 대회

- 대회: 제3회 풍력발전량 예측 AI 경진대회 - BARAM 2026
- 운영: DACON
- 공식 안내: <https://dacon.io/competitions/official/236727/overview/description>
- 사용 범위: 대회 참여와 허용된 연구·분석 범위

공개 접근 가능 여부와 재배포 권리는 동일하지 않습니다. 공식 대회 원자료의
재배포 권리를 별도로 확인하지 않았으므로 CSV/XLSX 원본은 Git에 포함하지 않습니다.

## 저장소에 포함하지 않는 원자료

`data/raw/open/` 아래의 LDAPS, GFS, SCADA, label, 제출 예시와 설명 파일은 로컬
전용입니다. `.gitignore`가 원본을 차단하며, Git에는 다음 두 파일만 남깁니다.

- `data/raw/open/README.md`: 공식 파일 복구 절차
- `data/raw/open/MANIFEST.md`: 파일 크기와 SHA-256 무결성 값

가장 큰 `ldaps_train.csv`는 약 123.7MiB로 GitHub 일반 파일 한도도 초과합니다.

## 공식 참조 노트북

`references/official/notebooks/`의 두 노트북은 대회가 제공한 기준 자료입니다.
수정하지 않고 hash로 원본성을 확인하며, 실험용 구현은 `src/baram/`과
`notebooks/`에 별도로 둡니다.

| 파일 | SHA-256 |
| --- | --- |
| `baseline.ipynb` | `712b26f4d2748860c94cff1e0100c23810468c983173f8e9ef8d009fe82df48c` |
| `evaluation_metric.ipynb` | `0a3ab5a57dba0705dbdbda73cd723be37ef39cce388fcb22b1a220ce523a70f9` |

권리자나 대회 운영자의 삭제·수정 요청 또는 이용 조건 변경이 확인되면 해당 자료를
제거하고 manifest와 이 문서를 갱신합니다.
