# 엑스파일 자동화 프로젝트

가상환경은 반드시 Python 3.13으로 생성하세요 (`/usr/local/bin/python3.13 -m venv .venv`) — 3.14에서는 playwright의 greenlet 의존성이 빌드되지 않습니다.

## 환경 설정

```bash
/usr/local/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

주의: `requirements.txt`의 `playwright==1.50.0`은 Python 3.13과 macOS 12에서 모두 정상 작동하는 버전입니다. 더 새로운 버전은 macOS 12 지원이 중단되었으므로 이 버전 고정이 필요합니다.
