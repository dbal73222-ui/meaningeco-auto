# 지원자 경력 데이터 보강 — 설계 문서

작성일: 2026-08-24

## 배경 및 목적

기존 "추천 보기" 기능(`2026-08-11-selection-recommendation-view-design.md`)은 참여횟수(`participation_count`)를 정렬/그룹 기준에서 명시적으로 제외했다 — 미닝에코 내부 참여 이력만 반영하고 실제 경력을 담지 못해 잘못된 우선순위를 줄 위험이 있었기 때문이다.

2026-08-23 브레인스토밍에서 `expile-backend`에 이미 진짜 경력 데이터 모델과 서버사이드 정렬이 존재한다는 걸 확인했다:
- `agentUser.careers` 배열, `careerCount = careers.length`
- `GET /business/job-applications/:jobPostingId?sortBy=career&sortOrder=desc` — MongoDB가 `careers` 배열 크기 기준으로 이미 정렬해서 응답함(자체 정렬 로직 불필요)

이 문서는 이 API를 `meaningeco-automation`에 연동해, "추천 보기" 화면에 실제 경력(`careerCount`)과 슈퍼바이저 후보 여부를 참고용으로 추가하는 설계다.

## 원칙 (기존 프로젝트 전체에 적용되는 안전장치, 변경 없음)

- **100% 참고용.** 이 기능은 어떤 승인/거절 액션도 수행하지 않는다. 최종 결정은 사람이 엑스파일에서 직접 한다.
- 기존 Playwright/CSV 스크래핑 흐름(일정 그룹핑, 커스텀옵션 등)은 그대로 유지한다 — 대체하지 않고 보강만 한다.

## 범위

**포함**
- `expile-backend` business API 로그인 및 공고별 지원자+경력 데이터 조회
- 전화번호 기준으로 기존 CSV 기반 `Applicant`와 API 응답 매칭
- `Applicant`에 `career_count: int` 필드 추가
- 슈퍼바이저 후보 여부 표시(`career_count >= 임계값`) — 임계값은 `.env` 설정값
- "추천 보기" 화면에 경력·슈퍼바이저 후보 컬럼 추가

**제외**
- 실제 승인/거절 등 쓰기 액션 (원칙 유지)
- 슈퍼바이저 판별 임계값의 실제 숫자 확정 — 대표님 확인 필요, 이 설계에서는 설정값 자리만 마련
- 기존 CSV/Playwright 흐름을 API로 완전 대체하는 것 (별도 검토 대상, 이번 범위 아님) — API 응답에는 `선택일정`(`selected_schedule`) 정보가 없어 기존 그룹핑 기능을 대체할 수 없음을 확인함

## API 연동 상세

### 인증
`POST {XFILE_API_BASE_URL}/business/auth/login`
```json
{ "email": "...", "password": "..." }
```
응답: `{ accessToken, refreshToken }` — 이후 요청에 `Authorization: Bearer {accessToken}` 헤더로 사용.

**확인 필요(구현 중 검증)**: 이 로그인이 기존 `.env`의 `XFILE_USERNAME`/`XFILE_PASSWORD`(Playwright 관리자 로그인)와 같은 계정인지. `/business/auth/login`이 "기업회원 로그인"이고 관리자 화면도 이 계정 체계를 쓸 가능성이 높지만, 실제 호출로 검증 전까지는 가정일 뿐이다. 같은 계정이면 새 시크릿 없이 재사용, 다르면 별도 `.env` 변수 필요.

### 지원자 + 경력 조회
`GET {XFILE_API_BASE_URL}/business/job-applications/{jobPostingId}?sortBy=career&sortOrder=desc&page=1&limit=200`

- `page`/`limit`은 서버에서 optional이지만 값이 없으면 페이지네이션 계산이 깨질 수 있어(NaN) **항상 명시적으로 전달**한다. `limit=200`은 미닝에코 공고당 지원자 규모를 고려한 여유값이며, 실제 공고당 지원자 수가 이를 넘는지 첫 실행 시 확인 필요.
- 응답의 `agentUser.careers` 배열 길이를 `career_count`로 사용한다 (서버가 이미 `careerCount`로 계산해 내려주는 별도 필드는 이 엔드포인트 응답에는 없음 — `careers` 배열 자체로 직접 계산).
- 권한: 로그인한 계정이 해당 공고의 소유 business 계정이거나 ADMIN 역할이어야 함(403 가능성 있음 — 에러 처리 대상).

## 컴포넌트별 변경

### 신규: `xfile_api_client.py`
- `login(base_url: str, email: str, password: str) -> str` — accessToken 반환. 실패 시 `XfileApiAuthError` 발생.
- `fetch_applicants_with_career(base_url: str, token: str, job_posting_id: str) -> dict[str, int]` — 전화번호(`phoneNo`) → `career_count` 매핑 딕셔너리 반환. 페이지네이션 응답에 `total`이 `limit`보다 크면 경고 로그만 남기고 가진 페이지만 사용(전체 실패시키지 않음).
- 네트워크/인증 실패는 `XfileApiError`로 감싸서 상위에 전파 — CSV 스크래핑과 마찬가지로 이 단계가 실패해도 **기존 CSV 기반 결과는 그대로 살아있어야 함** (경력 보강은 선택적 부가 정보이지 필수 경로가 아님).

### `applicant_parser.py`
- `Applicant.career_count: int | None` 필드 추가 (매칭 실패 시 `None`, 화면에는 "정보 없음"으로 표시)

### `main.py`
- CSV 스크래핑 완료 후, 공고별로 `xfile_api_client`를 호출해 `career_count`를 채워 넣는 단계 추가
- 이 단계 전체가 실패해도(API 서버 문제, 로그인 실패 등) 기존 흐름은 중단시키지 않고 `career_count=None`으로 계속 진행 (경고 로그만 남김)

### `config.py` / `.env.example`
- `XFILE_API_BASE_URL` 추가
- `XFILE_SUPERVISOR_CAREER_THRESHOLD` 추가 (정수, 기본값 없음 — 대표님 확인 전까지는 비워두고, 값이 없으면 슈퍼바이저 후보 표시 기능 자체를 끔)

### `view.py`
- 표시 컬럼에 "경력"(`career_count`, 없으면 "정보 없음") 추가
- `XFILE_SUPERVISOR_CAREER_THRESHOLD`가 설정되어 있고 `career_count >= 임계값`이면 "슈퍼바이저 후보" 배지 표시
- 정렬/그룹 로직 자체는 변경 없음 (기존처럼 지원일시 오름차순 유지) — 경력은 표시용 정보이지 정렬 기준이 아님. 참여횟수를 정렬에서 뺐던 것과 같은 이유로, 경력만으로 자동 우선순위를 매기는 건 이번 범위에서 하지 않는다.

## 데이터 흐름

1. 기존과 동일하게 Playwright로 각 공고 CSV 스크래핑 → `Applicant` 목록 생성
2. 공고별로 `xfile_api_client.login()` → `fetch_applicants_with_career()` 호출해 `{전화번호: career_count}` 맵 획득
3. `Applicant.phone`으로 맵에서 조회해 `career_count` 채움 (매칭 안 되면 `None`)
4. `save_results`/`view.py`에 `career_count` 필드가 함께 저장·표시됨

## 에러 처리

- API 로그인 실패: 경고 로그, 전체 실행은 계속(경력 데이터 없이 진행)
- 특정 공고 조회 실패(403/404 등): 해당 공고만 `career_count=None` 처리, 다른 공고는 영향 없음
- 전화번호 매칭 실패(형식 차이 등): 개별 지원자만 `career_count=None`, 나머지는 정상 처리

## 테스트 전략

- `xfile_api_client.py`: 로그인 성공/실패, 지원자 조회 성공/권한없음/네트워크실패 각각 mock으로 단위 테스트
- `applicant_parser.py`: `career_count` 필드가 매칭 성공/실패 케이스에서 올바르게 채워지는지
- `view.py`: 경력 컬럼 표시, 임계값 설정 여부에 따른 슈퍼바이저 배지 표시/미표시, 정렬 순서가 경력과 무관하게 유지되는지(회귀 방지)
- 기존 CSV 스크래핑 관련 테스트는 전부 그대로 유지 — 이번 변경이 기존 흐름에 영향 없음을 확인

## 미확정 항목 (구현 전 확인 필요)

1. **슈퍼바이저 임계값 숫자** — 대표님 확인 필요. 확인 전까지는 `.env` 비워두고 기능 자동 비활성.
2. **API 로그인 계정이 기존 Playwright 로그인과 동일한지** — 구현 착수 시 첫 번째로 검증.
3. **공고당 지원자 수가 `limit=200`을 넘을 가능성** — 넘는 공고가 실제로 있는지 확인 후 페이지네이션 루프 필요 여부 결정.
