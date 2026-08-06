# 엑스파일 자동화 프로젝트

가상환경은 반드시 Python 3.13으로 생성하세요 (`/usr/local/bin/python3.13 -m venv .venv`) — 3.14에서는 playwright의 greenlet 의존성이 빌드되지 않습니다.

## 환경 설정

```bash
/usr/local/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

주의: `playwright install chromium`은 macOS 12 이상에서는 지원되지 않습니다. Task 4에서 playwright 기능을 구현할 때 필요한 경우 다시 시도하세요.
