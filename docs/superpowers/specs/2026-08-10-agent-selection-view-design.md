# 지원자 데이터 보기 화면 — 설계 문서

## 배경

요원 선발 자동화 Phase 1(`agent_selection.main`)은 엑스파일 관리자 페이지에서 지원자 데이터를 수집해 `output/{timestamp}.json`, `output/{timestamp}.csv`로 저장한다. 현재는 콘솔 요약 출력과 raw JSON/CSV 파일만 있어, 비개발자인 사용자가 결과를 바로 훑어보기 어렵다. 이 기능은 가장 최근 수집 결과를 브라우저에서 보기 좋은 표로 보여주는 로컬 뷰어를 추가한다.

## 범위

**포함**: 가장 최근 수집 결과 1건을 정적 HTML로 렌더링, 역할타입 필터, 이름/전화번호 검색, 명령어 한 번으로 브라우저 자동 오픈.

**제외**: 과거 이력 열람, 승인/거절 등 쓰기 동작(Phase 1은 읽기 전용 원칙 유지), 실시간 재수집, 서버 프로세스 상시 구동.

## 아키텍처

`agent_selection` 패키지에 신규 모듈 `view.py`를 추가한다. 기존 `main.py`(수집)와 완전히 분리된 별도 진입점으로, 수집 로직에는 영향을 주지 않는다.

```
python -m agent_selection.view
        │
        ▼
  load_config()  ← 기존 config.py 재사용 (XFILE_OUTPUT_DIR)
        │
        ▼
  find_latest_result(output_dir) → Path | None
        │
        ├─ None → "데이터 없음" 안내 HTML 생성
        │
        ▼
  load_applicants(json_path) → list[dict]
        │
        ▼
  render_html(applicants, collected_at) → str
        │
        ▼
  output/view.html 저장 + webbrowser.open()
```

## 컴포넌트

**`find_latest_result(output_dir: Path) -> Path | None`**
`output_dir`에서 `*.json` 파일 중 파일명(타임스탬프 문자열, `YYYYMMDD_HHMMSS`)이 가장 큰 것을 반환. 파일이 없으면 `None`.

**`load_applicants(json_path: Path) -> list[dict]`**
JSON 파일을 읽어 파싱. 파싱 실패 시 예외를 발생시키고, 호출부(`main` 함수)가 잡아서 한국어 에러 메시지 출력 후 종료(브라우저는 열지 않음).

**`render_html(applicants: list[dict], collected_at: str) -> str`**
표시 항목(이름/전화번호/역할타입/참여횟수/지원상태/지원일시)만 골라 HTML 문자열을 생성. 데이터는 `<script>` 안에 JSON으로 임베드하고, 필터/검색은 순수 자바스크립트로 클라이언트 사이드에서 처리(서버 없음). 상단에 "총 N명 · 수집 시각" 요약 포함.

**`main() -> int`**
`view.py`의 진입점. `load_config()` → `find_latest_result()` → 없으면 안내 HTML, 있으면 `load_applicants()` + `render_html()` → `output/view.html` 저장 → `webbrowser.open()`. 기존 `main.py`의 `run()`과 동일한 반환 규약(성공 0 / 실패 1)을 따른다.

## 데이터 흐름

1. 사용자가 `python -m agent_selection.view` 실행
2. `.env`에서 `XFILE_OUTPUT_DIR` 읽기 (기존 `load_config()` 재사용)
3. 해당 폴더에서 최신 `*.json` 탐색
4. 없으면: "아직 수집된 데이터가 없습니다. 먼저 `python -m agent_selection.main` 을 실행해주세요" 안내 HTML 생성 후 오픈
5. 있으면: JSON 로드 → HTML 렌더링 → `output/view.html`에 저장 → 기본 브라우저로 자동 오픈

## 화면 내용

- 표시 컬럼: 이름 / 전화번호 / 역할타입 / 참여횟수 / 지원상태 / 지원일시 (6개, 핵심만 — 전체 14개 항목 중 축약)
- 상단 역할타입 필터 버튼: 전체 / A / B / C
- 검색창: 이름 또는 전화번호로 실시간 필터링 (새로고침 없음)
- 상단 요약: "총 N명 · 수집 시각 YYYY-MM-DD HH:MM"
- 읽기 전용 — 어떤 클릭도 승인/거절 등 액션을 트리거하지 않음 (Phase 1 원칙 유지)

## 에러 처리

- `output/` 폴더가 없거나 비어 있음 → 안내 HTML(데이터 없음 메시지) 생성, 정상 종료(exit 0)
- JSON 파일은 있으나 파싱 실패(손상된 파일 등) → 콘솔에 한국어 에러 메시지 출력, 브라우저 열지 않고 종료(exit 1)
- `ConfigError`(`.env` 미설정 등) → 기존 `main.py`와 동일한 패턴으로 에러 메시지 출력 후 exit 1

## 테스트 전략

- `find_latest_result`: 파일 여러 개 중 최신 선택, 파일 없을 때 `None` 반환
- `load_applicants`: 정상 JSON 파싱, 손상된 JSON에서 예외 발생
- `render_html`: 입력 데이터가 출력 HTML 문자열에 올바르게 반영되는지(값 포함 여부), 데이터 없을 때 안내 문구 포함 여부
- 실제 브라우저 오픈(`webbrowser.open`)은 단위 테스트 대상에서 제외 — `main()`에서 이 호출만 분리해 목으로 대체 가능하게 구성

## 전제

- `agent_selection.main`을 통해 최소 1회 이상 수집이 완료된 상태(로컬 개발/테스트 시에는 더미 JSON 픽스처로 대체)
- 기존 `config.py`, `applicant_parser.py`의 `Applicant` 필드명 규약을 그대로 따름(추가 매핑 불필요)
