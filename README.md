# BAJONGBAL 급등직전 감지 시스템

## 실행 (PowerShell)
```powershell
$env:PYTHONPATH="src"

python --version
python -m pip install -r requirements.txt
python -m pytest -q
python -m bajongbal init-db
python -m bajongbal web --host 127.0.0.1 --port 8000
```
- 기본 `python` 명령 기준 안내입니다.
- `.venv`는 선택 사항입니다.

## UI 페이지 구조
- `/dashboard` : 대시보드(조회 범위, 후보, 상세패널, 최근 이력)
- `/theme-stocks` : 테마 종목 리스트(필터, 다중정렬, 실패상태)
- `/watchlists` : 관심그룹(좌측 그룹 목록 + 우측 종목 테이블)

## 조회 범위
- 관심그룹에서 조회
- 전체 테마 종목 조회
- 선택 테마 종목 조회

## 테마 종목 리스트 사용법
- 테마명/종목코드/종목명 포함 검색 지원
- 컬럼 헤더 클릭 시 다중 정렬(desc→asc→off)
- 실패 행(INVALID_CODE/API_FAILED/PARSE_FAILED/NO_DATA)은 하단 고정

## 조회 실패 상태 의미
- `INVALID_CODE`: 6자리 숫자 종목코드 아님
- `API_FAILED`: KIS 호출 실패
- `PARSE_FAILED`: KIS 응답 파싱 실패
- `RATE_LIMITED`: 호출 제한
- `NO_DATA`: 조회 데이터 없음

## 문자 깨짐 조치
- 문자 깨짐이 보이면 테마 캐시를 초기화 후 재갱신하세요.
```powershell
python -m bajongbal clear-theme-cache
python -m bajongbal refresh-themes --force
```

## 관심그룹 사용법
- 후보/테마목록에서 별 아이콘으로 관심그룹에 추가
- 그룹 관리는 `/watchlists`에서 수행

## DART 아이콘/점수
- 대시보드 후보의 ⓓ 아이콘으로 DART 패널 확인
- 영향치 점수는 -100~100 범위(양수=긍정, 음수=부정)

## 참고
- UI에서는 등급 표시를 제거하고 점수 중심으로 표시합니다.
- 자동매수/자동매도/주문/계좌/잔고 API는 구현하지 않습니다.
