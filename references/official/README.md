# 공식 참조 자료

이 폴더는 공식 baseline, 평가 산식 코드 등 대회 진행 중 기준점으로 삼을 수 있는 참조 자료를 보관합니다.

| 파일 | 원본 | 크기(bytes) | SHA256 | 용도 |
|------|------|------------:|--------|------|
| `notebooks/baseline.ipynb` | `C:\Users\kik32\Downloads\baseline.ipynb` | 149504 | `712b26f4d2748860c94cff1e0100c23810468c983173f8e9ef8d009fe82df48c` | 공식 RandomForest baseline 재현 |
| `notebooks/evaluation_metric.ipynb` | `C:\Users\kik32\Downloads\평가_산식 코드.ipynb` | 2426 | `0a3ab5a57dba0705dbdbda73cd723be37ef39cce388fcb22b1a220ce523a70f9` | 공식 `total_score`, `1-NMAE`, `FICR` 산식 재현 |

운영 원칙:

- 원본 노트북은 공식 기준 보존용으로 두고, 실제 개발 코드는 `src/baram/` 아래에 분리 구현합니다.
- baseline을 수정해 실험할 때는 이 폴더의 파일을 직접 고치지 않습니다.
- 제출 파일 생성에 사용한 코드 버전은 commit SHA, config, seed, 제출 파일 hash와 함께 기록합니다.
