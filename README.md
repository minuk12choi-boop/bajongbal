# BAJONGBAL 급등직전 감지 시스템

## 프로젝트 목적
네이버증권 테마 분류(하루 1회) + KIS 시세(장중) + DART 공시 리스크를 결합하여 바종발식 급등 직전 후보를 웹 대시보드에서 확인하는 분석/감지 시스템입니다.

## 중요한 원칙
- 본 프로젝트는 **실제 외부 라이브러리(FastAPI/requests/bs4/uvicorn 등)** 를 사용합니다.
- `src/` 아래에 `fastapi/requests/bs4` 같은 mock 패키지를 두지 않습니다.
- 외부 API 테스트는 기본 단위테스트에서 제외하고 `tests/fixtures`, `tests/fakes`, monkeypatch 기반으로 검증합니다.
- 자동매수/자동매도/주문/계좌/잔고 조회는 구현하지 않습니다.

## 바종발식 매매 방법론 요약
- 장기 매물대/박스권 근접도
- 기준가 반복 터치 압력
- 거래량/거래대금 예열
- 분봉 상승 압력
- 333 패턴 보조 필터
- 위쪽 공간/손익비
- 테마 동조 + DART 리스크 반영

## 333 전략 정의
고점 이후 조정 구간에서 `U-D-U-D-U-D-U` 구조를 감지하고 `STRONG_333 / NORMAL_333 / WEAK_333 / NO_333`로 분류합니다.

## 설치
### macOS/Linux
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows (PowerShell 실행 정책 이슈 우회)
PowerShell에서 `Activate.ps1` 실행이 막히면 아래처럼 venv 파이썬을 직접 사용합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m bajongbal web --host 127.0.0.1 --port 8000
```

## 환경변수
`.env.example`를 복사하여 `.env`를 작성하세요.
- `DART_API_KEY`
- `KIS_APP_KEY`
- `KIS_APP_SECRET`
- `KIS_BASE_URL`

`.env`는 반드시 `KEY=value` 형식이어야 합니다.

## 웹 실행 방법
```bash
PYTHONPATH=src python -m bajongbal web --host 0.0.0.0 --port 8000
```
브라우저에서 `http://127.0.0.1:8000` 접속.

## CLI 실행 방법
```bash
PYTHONPATH=src python -m bajongbal --help
PYTHONPATH=src python -m bajongbal init-db
PYTHONPATH=src python -m bajongbal refresh-themes
PYTHONPATH=src python -m bajongbal scan --watchlist data/watchlist.example.csv --once
```

## 테마 갱신 방법
- 웹: 대시보드 `[테마 갱신]` 버튼
- CLI: `PYTHONPATH=src python -m bajongbal refresh-themes`

## 조회 방법
- 웹: 대시보드 `[조회]` 버튼
- CLI: `PYTHONPATH=src python -m bajongbal scan --watchlist data/watchlist.example.csv --once`

## KIS/DART 연동 전 사용자 확인 필요 사항
### KIS
- 실전/모의 계정별 OAuth 경로
- 현재가/일봉/분봉 조회 TR_ID
- 분봉/일봉 응답 필드명(환경별 차이)

### DART
- corpCode ZIP 다운로드 정책/호출 제한
- 공시 목록(list.json) 파라미터와 조회 기간 정책
- 기업개황(company.json) 응답 필드 사용 범위

## 네이버 테마 수집 방식과 한계
- 서버사이드 `requests + BeautifulSoup`로 페이지 순회 수집
- HTML 구조 변경 시 파서 수정 필요
- 수집 실패 시 기존 SQLite 캐시 유지

## 테스트
```bash
python -m pytest -q
```
- 외부 API 직접 호출 없이 fixture/mocking 기반으로 검증합니다.

## 트러블슈팅: `python-dotenv could not parse statement`
1. `.env` 파일 첫 줄이 깨지지 않았는지 확인
2. 반드시 `KEY=value` 형식으로 수정
3. OS 환경변수를 사용 중이면 `.env`를 삭제해도 동작

## 자동주문 미포함 안내
본 프로젝트는 자동주문 시스템이 아니며, 최종 매매 판단은 사용자가 직접 수행합니다.


## 로컬 환경변수 설정 (중요)
- Codex 실행 환경에 등록된 환경변수와 **로컬 PC 환경변수는 별개**입니다.
- 로컬에서 웹/CLI 실행 시에는 반드시 로컬 PC에도 환경변수를 설정해야 합니다.

PowerShell (현재 세션)
```powershell
$env:KIS_APP_KEY="..."
$env:KIS_APP_SECRET="..."
$env:KIS_BASE_URL="..."
$env:DART_API_KEY="..."
```

Windows 영구 설정
```powershell
setx KIS_APP_KEY "..."
setx KIS_APP_SECRET "..."
setx KIS_BASE_URL "..."
setx DART_API_KEY "..."
```

> README에는 실제 키 값을 절대 기록하지 마세요.

## KIS 미설정 / 데모 모드 동작
- KIS 환경변수가 미설정이거나 인증 실패 시 **실제 후보가 나오지 않는 것이 정상**입니다.
- 기본값은 데모 모드 OFF이며, 이때는 10000원 같은 더미 후보를 생성하지 않습니다.
- 데모 모드는 명시적으로 ON 했을 때만 동작하며, 결과에 `데모 데이터` 표시가 붙습니다.


## 데모 시그널 정리
```bash
PYTHONPATH=src python -m bajongbal clear-demo-signals
```
- 최근 감지 이력 API(`/api/signals/recent`)는 기본적으로 데모(is_demo=1) 데이터를 숨깁니다.
