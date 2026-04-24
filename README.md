# BAJONGBAL 급등직전 감지 시스템

## 프로젝트 목적
네이버증권 테마 분류표(하루 1회), KIS 시세(장중), DART 공시 리스크를 결합해 바종발식 급등 직전 후보를 웹 대시보드에서 보여주는 분석/감지 시스템입니다. 자동주문은 포함하지 않습니다.

## 바종발식 매매 방법론 요약
- 장기 매물대/박스권 근접도
- 기준가 반복 터치 및 재돌파 압력
- 거래량/거래대금 예열
- 분봉 상승 압력
- 333 조정 패턴 보조 필터
- 위쪽 공간/손익비
- 테마 동조 여부
- DART 리스크 반영

## 333 전략 정의
고점 이후 조정 구간에서 `U-D-U-D-U-D-U`(양봉/음봉 그룹 압축) 구조를 만족하는지 탐지하고, STRONG/NORMAL/WEAK/NO_333으로 분류합니다.

## 환경변수 설정 방법
`.env.example`를 복사해 `.env`를 만들고 값을 입력합니다.

## 설치 방법
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 웹 실행 방법
```bash
PYTHONPATH=src python -m bajongbal web --host 0.0.0.0 --port 8000
```

## CLI 실행 방법
```bash
PYTHONPATH=src python -m bajongbal --help
```

## 테마 갱신 방법
- 웹: `[테마 갱신]` 버튼
- CLI: `PYTHONPATH=src python -m bajongbal refresh-themes`

## 조회 방법
- 웹: `[조회]` 버튼
- CLI: `PYTHONPATH=src python -m bajongbal scan --watchlist data/watchlist.example.csv --once`

## watchlist 작성 방법
`data/watchlist.example.csv` 형식(`code,name,market`)을 복사해 사용합니다.

## KIS API 사용 범위
- 현재가
- 기간별 시세(일/주/월/년)
- 당일 분봉
- 일별 분봉

> 주문/계좌/잔고 API는 구현하지 않습니다.

## DART API 사용 범위
- corp_code 매핑 캐시
- 최근 공시 조회
- 기업개황 조회(구조)
- 제목 키워드 기반 리스크 태그

## 네이버증권 테마 수집 방식과 한계
서버 사이드에서 `requests + BeautifulSoup`로 테마 목록/상세를 파싱해 SQLite에 캐시합니다. HTML 구조 변경 시 파서 보정이 필요합니다.

## 자동주문 미포함 안내
본 프로젝트는 자동매수/자동매도 미포함이며, 최종 매매 판단은 사용자가 HTS/MTS에서 직접 수행합니다.

## 감지 결과의 한계
점수는 확률적 보조지표이며 수익을 보장하지 않습니다. 데이터 지연/휴장/외부 API 장애가 있을 수 있습니다.

## 백테스트 방법
```bash
PYTHONPATH=src python -m bajongbal backtest --from 2026-01-01 --to 2026-04-24
```

## 테스트 실행 방법
```bash
PYTHONPATH=src python -m pytest
```

## 보안 주의사항
- 키/토큰 로그 출력 금지
- `.env` 커밋 금지
- 예외 메시지에 민감정보 포함 금지

## 향후 자동주문 구현 시 추가로 필요한 환경변수
- `KIS_CANO`
- `KIS_ACNT_PRDT_CD`
- `KIS_IS_PAPER`
