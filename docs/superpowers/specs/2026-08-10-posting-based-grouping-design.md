# 공고별 지원자 관리 전환 — 설계 문서

## 배경

Phase 1(요원 선발 자동화, 2026-08-06)은 "커스텀옵션1 = 역할타입(A/B/C)"이라는 전제로 설계됐다. 실사이트 검증(2026-08-10) 과정에서 이 전제가 실제 업무 방식과 맞지 않는다는 것이 확인됐다:

- 미닝에코는 역할(미화/다회용기/슈퍼바이저 등)마다 **공고를 완전히 분리해서** 등록한다. 한 공고 안에 여러 역할 선택지를 넣지 않는다.
- 이유: (1) 선택지가 많아지면 공고가 복잡해짐, (2) 노무법 리스크 — 고시된 업무/임금과 실제 근무가 다르면 인당 약 500만원 규모의 법적 리스크가 있음.
- 즉 "역할타입"은 공고 내부의 필드가 아니라 **공고 자체**로 이미 구분되어 있다.
- 커스텀옵션1/2(역할타입/참여횟수)은 현재 대부분 비어있고, 팀에서 당장 활용할 계획이 없다.

이에 따라 "역할타입으로 지원자를 검증/집계"하던 로직을 "공고로 지원자를 그룹핑"하는 방식으로 전환한다.

## 범위

**포함**: 커스텀옵션1/2 검증 제거(패스스루로 변경), 공고 제목 자동 수집, 결과 화면/요약을 공고 기준으로 재편.

**제외**: 커스텀옵션 필드 자체를 데이터에서 삭제(값이 있으면 여전히 표시), 승인/거절 등 쓰기 기능, 공고 제목 외 추가 메타데이터(카테고리, 급여 등) 수집.

## 컴포넌트별 변경

### `applicant_parser.py`
- `ROLE_TYPES`, `VALID_ROLE_TYPES`, `ApplicantParseError` 제거 — 더 이상 검증해서 걸러낼 대상이 없으므로 사용처가 없어짐
- `Applicant.role_type: str` — `custom_option_1`을 검증 없이 그대로 저장(빈 문자열 허용)
- `Applicant.participation_count: str` — 기존에는 `int`였으나 숫자 검증을 없애므로 `str`로 변경(빈 문자열 허용)
- `Applicant.posting_title: str` — 신규 필드, 어느 공고에서 왔는지 사람이 읽을 수 있는 이름
- `parse_applicant_row(row: dict[str, str], posting_url: str, posting_title: str) -> Applicant` — 예외를 던지지 않는 순수 변환 함수로 단순화
- `parse_applicant_rows(rows: list[dict[str, str]], posting_url: str, posting_title: str) -> list[Applicant]` — 단순 매핑(더 이상 per-row 실패를 스킵할 필요 없음, 실패할 수 없는 변환이므로)

### `xfile_client.py`
- `scrape_posting_applicants(page: Page, posting_url: str) -> tuple[str, list[dict[str, str]]]` — 반환 타입이 `(공고 제목, 지원자 행 목록)` 튜플로 변경
- 공고 제목은 `page.locator(".text-lg.font-semibold").first.inner_text().strip()`로 추출 (실사이트 확인 결과 이 클래스 조합의 div에 제목이 들어있음 — Tailwind 유틸리티 클래스 기반이라 사이트 스타일이 바뀌면 깨질 수 있음, 향후 문제 발생 시 재확인 필요)
- CSV 다운로드/파싱 로직 자체는 변경 없음(2026-08-10 오전 수정분 그대로 유지)

### `output.py`
- `print_summary(applicants: list[Applicant]) -> None` — `ROLE_TYPES` 기준 집계 대신, `applicants`에 존재하는 고유 `posting_title` 값 기준으로 그룹핑해서 "공고명: N명" 형태로 출력
- `save_results`는 변경 없음(딕셔너리 직렬화라 필드 추가/타입 변경에 자동으로 대응됨)

### `main.py`
- `scrape_posting_applicants` 반환값이 튜플로 바뀌므로 호출부 수정: `posting_title, raw_rows = scrape_posting_applicants(page, posting_url)`
- `parse_applicant_rows(raw_rows, posting_url, posting_title)` 호출로 변경

### `view.py`
- 표시 컬럼: 이름 / 전화번호 / **공고명** / 역할타입 / 참여횟수 / 지원상태 / 지원일시 (7개, 공고명 추가)
- 필터 버튼: 고정된 A/B/C 대신, 렌더링 시점에 데이터에 존재하는 고유 `posting_title` 값들로 동적 생성 ("전체" + 공고별 버튼)
- 검색 대상(이름/전화번호)은 기존과 동일하게 유지

## 데이터 흐름

1. `main.py`가 각 `posting_url`에 대해 `scrape_posting_applicants` 호출 → `(posting_title, raw_rows)` 획득
2. `parse_applicant_rows(raw_rows, posting_url, posting_title)`로 `Applicant` 목록 생성(모든 행이 그대로 통과, 실패 없음)
3. 여러 공고의 `Applicant`를 하나의 리스트로 합쳐 `save_results`/`print_summary`/`render_html`에 전달
4. `render_html`은 `Applicant.posting_title` 기준으로 필터 버튼을 동적 생성하고, 각 행에 공고명 컬럼을 표시

## 에러 처리

- 공고 제목 요소를 못 찾으면(구조가 또 바뀐 경우) `XfilePageError`로 감싸서 해당 공고를 스킵(기존 CSV 다운로드 실패와 동일한 처리 방식) — "제목을 찾을 수 없습니다" 같은 부분 실패로 전체 실행이 죽지 않게 함
- 그 외 에러 처리(로그인 실패, CSV 컬럼 불일치 등)는 기존 그대로 유지

## 테스트 전략

- `applicant_parser.py`: `parse_applicant_row`/`parse_applicant_rows`가 `posting_title`을 포함해 올바르게 `Applicant`를 생성하는지, 커스텀옵션이 비어있어도 걸러지지 않는지 검증
- `output.py`: `print_summary`가 공고별로 올바르게 집계해서 출력하는지(여러 공고가 섞인 리스트로 테스트)
- `view.py`: `render_html`이 공고명 컬럼을 포함하고, 데이터에 존재하는 공고 수만큼 필터 버튼을 생성하는지 검증
- `xfile_client.py`는 기존과 동일하게 실사이트 대상 수동 통합 테스트로 검증(Playwright 실제 상호작용은 단위 테스트 대상 아님, 기존 프로젝트 컨벤션 유지)
