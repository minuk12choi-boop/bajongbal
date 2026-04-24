# BAJONGBAL 급등직전 감지 시스템

## 프로젝트 목적
네이버증권 테마 분류 + KIS 시세 + DART 공시 리스크를 결합해 바종발식 급등 직전 후보를 감지하는 웹/CLI 도구입니다.

## 중요한 원칙
- 자동매수/자동매도/주문/계좌/잔고 API는 구현하지 않습니다.
- 실제 API 실패 시 mock 후보를 생성하지 않습니다(데모 모드 제외).
- demo 데이터는 `is_demo`로 분리되고 최근 감지 이력 기본 조회에서 제외됩니다.

## 빠른 실행 (PowerShell)
```powershell
$env:PYTHONPATH="src"

python --version
python -m pip install -r requirements.txt
python -m pytest -q
python -m bajongbal init-db
python -m bajongbal web --host 127.0.0.1 --port 8000
```

- 기본 안내는 로컬 PC의 기본 `python` 명령 기준입니다.
- 버전 문제가 나면 `python --version`으로 먼저 확인하세요.
- `.venv` 사용은 선택 사항입니다.

## 환경변수 / .env
`.env.example`를 복사해 프로젝트 루트 `.env`를 사용할 수 있습니다.

예시 경로:
`C:\Users\dkrt\OneDrive\바탕 화면\bajongbal-codex-implement-bajongbal-detection-system\.env`

권장 형식:
```env
DART_API_KEY=실제값
KIS_APP_KEY=실제값
KIS_APP_SECRET=실제값
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
KIS_TIMEOUT_SECONDS=20
KIS_MAX_RETRIES=1
DART_REPORT_PREVIEW_CARD_LIMIT=3
DART_DOCUMENT_ENRICHMENT_MAX_ITEMS=1
```

허용 형식:
```env
DART_API_KEY = 실제값
KIS_APP_KEY="실제값"
KIS_APP_SECRET='실제값'
```

잘못된 형식:
```env
DART_API_KEY : 실제값
KIS_APP_SECRET:
등호가 없는 줄
```

> 실제 환경변수 값은 화면/로그/README 어디에도 출력하지 마세요.

PowerShell에서 **키 이름 존재 여부만** 확인:
```powershell
"KIS_APP_KEY","KIS_APP_SECRET","KIS_BASE_URL","DART_API_KEY" | ForEach-Object {
  if (Test-Path "Env:$_") { "$_=Y" } else { "$_=N" }
}
```

## CLI 주요 명령
```powershell
$env:PYTHONPATH="src"

python -m bajongbal --help
python -m bajongbal init-db
python -m bajongbal refresh-themes
python -m bajongbal scan --watchlist data/watchlist.example.csv --once
python -m bajongbal scan --watchlist-group-id 1 --once --score-threshold 0
python -m bajongbal scan --target-mode 테마\ 전체 --theme-id 123 --once --score-threshold 0
python -m bajongbal watchlist-groups
python -m bajongbal watchlist-create --name "그룹명"
python -m bajongbal watchlist-items --group-id 1
python -m bajongbal watchlist-add --group-id 1 --code 005930 --name 삼성전자
python -m bajongbal watchlist-remove --group-id 1 --code 005930
python -m bajongbal watchlist-delete --group-id 1
python -m bajongbal clear-demo-signals
```

## 트러블슈팅
- `.env`가 없어도 앱은 기동됩니다.
- `.env` 형식 오류가 있어도 앱은 죽지 않고, `/api/config/status`에서 형식 오류 줄 번호를 확인할 수 있습니다.
- 환경파일 탐색 우선순위:
  1) `BAJONGBAL_ENV_FILE`
  2) 현재 작업 디렉터리 `.env`
  3) `src/bajongbal/config.py` 기준 상위 경로들 `.env`
  4) 저장소 루트 `.env`

## 자동주문 미포함 안내
본 프로젝트는 분석/감지용이며 최종 매매 판단은 사용자 책임입니다.
