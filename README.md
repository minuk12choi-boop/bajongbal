# BAJONGBAL 급등직전 감지 시스템

## 빠른 실행 (PowerShell)
```powershell
$env:PYTHONPATH="src"

python --version
python -m pip install -r requirements.txt
python -m pytest -q
python -m bajongbal init-db
python -m bajongbal web --host 127.0.0.1 --port 8000
```
- 기본 실행은 로컬 기본 `python` 명령 기준입니다.
- `.venv` 사용은 선택 사항입니다.

## 조회 범위
대시보드의 **조회 범위**는 아래 3가지입니다.
- 관심그룹에서 조회
- 전체 테마 종목 조회
- 선택 테마 종목 조회

테마 갱신 후에는 화면에서 `/api/themes/status`, `/api/themes/list`를 재조회해 상단 상태와 테마 목록을 즉시 갱신합니다.

## 테마 종목 리스트 페이지
- 경로: `/theme-stocks`
- 테마/종목코드/종목명 필터 지원
- 컬럼: 테마명, 코드, 종목명, 현재가, 등락률, 거래량, 거래대금, 시가총액, 시장구분, 마지막 시세 조회 시각, KIS 상태
- 컬럼 헤더 클릭으로 다중 정렬(우선순위) 지원
- 행의 별(☆) 아이콘 클릭으로 관심그룹에 바로 추가 가능

## 관심그룹 관리
- 대시보드/테마종목리스트의 별 아이콘 → 관심그룹 선택 모달로 추가
- 별도 관리 페이지: `/watchlists`

## 데모 모드
- 데모 모드는 **개발/테스트 전용**이며 일반 화면 조작 영역에는 기본 노출하지 않습니다.
- 데모 모드 OFF에서는 더미 10000원 후보를 생성하지 않습니다.

## KIS 파싱 실패 진단
- KIS 호출 실패(API_FAILED)와 파싱 실패(PARSE_FAILED)를 구분합니다.
- diagnostics에 `response_keys`, `output_type`, `output_length`, `missing_required_fields` 요약을 포함합니다.
- 민감정보(API 키/토큰/헤더 값)는 출력하지 않습니다.

## CLI 예시
```powershell
$env:PYTHONPATH="src"
python -m bajongbal themes
python -m bajongbal theme-stocks --theme-name "2차전지" --limit 100
python -m bajongbal scan --scope selected_theme --theme-name "2차전지" --once --score-threshold 0
python -m bajongbal scan --scope all_theme_stocks --once --score-threshold 0
python -m bajongbal scan --scope watchlist_group --watchlist-group-id 1 --once --score-threshold 0
```

## 안내
- 자동매수/자동매도/주문/계좌/잔고 API는 구현하지 않습니다.
