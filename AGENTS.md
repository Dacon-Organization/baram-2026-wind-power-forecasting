# BARAM 2026 Agent 운영 규칙

이 파일은 이 저장소의 작업 정본입니다. `CLAUDE.md`는 이 파일을 import하며,
규칙 변경은 항상 `AGENTS.md`에서만 수행합니다.

## 작업 흐름

1. 최신 `main`을 pull합니다.
2. `feature|fix|docs|refactor|test|chore|ci/<github-id>-<description>` 형식의
   개인 브랜치를 만듭니다.
3. 한 작업만 수행하고 아래 필수 검증을 실행합니다.
4. 관련 파일만 stage하고 한국어 커밋을 작성합니다.
5. 브랜치를 push하고 PR을 만듭니다.
6. 필수 gate 통과 후 GitHub native squash auto-merge를 사용합니다.
7. 프로젝트 대시보드를 갱신하고 한 작업 완료 후 멈춰 보고합니다.

`main` 직접 push와 강제 push는 금지합니다. 현재 solo 모드는 required review가
0이지만 PR, CI와 최종 diff 확인을 생략하지 않습니다.

## 이름 규칙

- 브랜치: `feature/mygithub05253-weather-features`
- 커밋: `✨ Feat: 기상 예보 피처 파이프라인 추가`
- PR: `[feat] 기상 예보 피처 파이프라인 추가`
- 커밋 prefix: `✨ Feat`, `🐛 Fix`, `📝 Docs`, `🎨 Style`, `♻️ Refactor`,
  `✅ Test`, `🔧 Chore`

## 필수 검증

```powershell
python -m pip install --disable-pip-version-check -r requirements-ci.txt
python -m pytest -q
python scripts/check_notebook_integrity.py
```

변경 범위에 따라 train/inference CLI의 `--help`도 확인합니다.

## 데이터·보안

- `data/raw/open/`의 공식 CSV/XLSX는 대회 참여 목적으로만 로컬에 두고 Git에
  커밋하지 않습니다.
- 원자료 대신 `MANIFEST.md`의 크기와 SHA-256만 관리합니다.
- 모델, 제출물, 실행 artifact와 `.env`·토큰·개인정보는 커밋하지 않습니다.
- 직접 작성한 코드·문서에는 MIT License를 적용하고, 공식 데이터·노트북 등
  제3자 자료는 원 이용 조건을 따릅니다.
- 외부 GitHub Action과 중앙 reusable workflow는 전체 commit SHA로 고정합니다.
- 워크플로 기본 권한은 `contents: read`이며 secret을 CI에 전달하지 않습니다.

## 문서·대시보드

- 대화, 문서, 주석, 커밋과 PR은 한국어로 작성합니다.
- 들여쓰기는 2 spaces를 사용합니다.
- 작업 종료 시 `dev/dashboard/log/YYYY-MM-DD-<slug>.html`과
  `dev/dashboard/index.html`을 갱신합니다.
- 데이터 출처나 권리가 바뀌면 `DATA_SOURCES.md`와 `NOTICE.md`를 함께 수정합니다.
