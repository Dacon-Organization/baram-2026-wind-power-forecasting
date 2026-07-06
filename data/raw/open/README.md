# BARAM 2026 공식 배포 데이터 로컬 미러

이 폴더는 `C:\Users\kik32\Downloads\open\`의 공식 배포 데이터를 프로젝트 작업 경로로 복사해 둔 로컬 미러입니다.

중요 원칙:

- 본 데이터는 `제3회 풍력발전량 예측 AI 경진대회 - BARAM 2026` 참여 목적으로만 사용합니다.
- 원본 CSV/XLSX 파일은 Git에 커밋하지 않습니다.
- Git에는 이 README와 `MANIFEST.md`의 파일 크기·SHA256만 남겨 복구와 무결성 확인에 사용합니다.
- 데이터가 손상되거나 제출 파일 복구가 필요하면 `MANIFEST.md`의 hash와 원본 다운로드 파일을 대조합니다.

로컬 기대 구조:

```text
data/raw/open/
├── train/
│   ├── ldaps_train.csv
│   ├── gfs_train.csv
│   ├── train_labels.csv
│   ├── scada_vestas_train.csv
│   └── scada_unison_train.csv
├── test/
│   ├── ldaps_test.csv
│   └── gfs_test.csv
├── sample_submission.csv
├── info.xlsx
└── data_description.md
```

복구 절차:

1. 공식 데이터 ZIP을 다시 내려받아 `data/raw/open/`에 압축 해제합니다.
2. `MANIFEST.md`의 파일 크기와 SHA256이 일치하는지 확인합니다.
3. 불일치하면 해당 데이터 버전을 별도 폴더로 분리하고 제출/학습에 사용하지 않습니다.
