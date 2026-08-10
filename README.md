# 엑스파일 자동화 프로젝트

가상환경은 반드시 Python 3.13으로 생성하세요 (`/usr/local/bin/python3.13 -m venv .venv`) — 3.14에서는 playwright의 greenlet 의존성이 빌드되지 않습니다.

## 설치

```bash
/usr/local/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -e .
```

주의: `playwright==1.50.0`은 Python 3.13과 macOS 12에서 모두 정상 작동하는 버전으로 고정되어 있습니다 (`pyproject.toml` 참고). 더 새로운 버전은 macOS 12 지원이 중단되었으므로 임의로 올리지 마세요.

## 환경 설정

`.env.example`을 `.env`로 복사한 뒤 값을 채웁니다.

- `XFILE_POSTING_URLS`: 수집할 공고가 여러 개면 콤마(`,`)로 구분해 나열합니다.
- `XFILE_HEADLESS=false`: 처음 실행할 때는 브라우저 동작을 눈으로 확인할 수 있도록 권장합니다.

## 실행

저장소 루트에서 `.env`가 있는 상태로 실행합니다.

```bash
.venv/bin/python -m agent_selection.main
```

## 결과물

`output/YYYYMMDD_HHMMSS.json`, `output/YYYYMMDD_HHMMSS.csv` (현재 작업 디렉터리 기준, `XFILE_OUTPUT_DIR`로 경로 변경 가능)에 저장됩니다.

## 결과 보기

가장 최근 수집 결과를 표로 보기 좋게 보여주는 화면을 브라우저로 엽니다.

```bash
.venv/bin/python -m agent_selection.view
```

- 공고별 필터 버튼과 이름/전화번호 검색으로 걸러볼 수 있습니다.
- 읽기 전용 화면입니다 — 여기서 클릭해도 엑스파일 사이트에는 어떤 영향도 없습니다.
- 아직 수집 결과가 없으면 안내 메시지가 뜹니다. 먼저 `python -m agent_selection.main`을 실행하세요.

## 참고

`xfile_client.py`의 셀렉터와 컬럼 라벨은 실사이트 소스 접근 없이 추정한 값이라 첫 실사이트 실행 후 조정이 필요할 수 있습니다. 자세한 내용은 계획 문서의 Task 4 노트를 참고하세요.
