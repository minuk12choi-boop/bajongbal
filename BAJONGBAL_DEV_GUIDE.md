# BAJONGBAL 개발 가이드

문서 목적: 이 문서는 `minuk12choi-boop/bajongbal` 저장소에서 Codex가 반드시 따라야 할 기준 문서다.  
목표는 단순 예제나 1차 MVP가 아니라, **KIS API와 DART API를 활용한 급등 직전 종목 감지·분석·검증 시스템의 전체 설계와 구현 기준**을 한 번에 제공하는 것이다.

---

## 0. 절대 원칙

### 0.1 작업 방식

Codex는 다음 방식으로 작업한다.

1. 작은 MVP만 만들고 끝내지 않는다.
2. 가능한 전체 구조를 한 번에 만든다.
3. 기능을 임의로 생략하지 않는다.
4. 불확실한 API 스펙, 필드명, 인증 방식은 추측하지 말고 코드 주석/TODO와 작업 보고에 명확히 남긴다.
5. 사용자가 제공한 환경변수를 활용한다.
6. 환경변수 값은 절대 출력하지 않는다.
7. 자동매수·자동매도는 명시 지시 전까지 구현하지 않는다.
8. 주문 API, 계좌 API는 호출하지 않는다.
9. 모든 설명, PR 본문, 작업 결과 보고는 한국어로 작성한다.
10. 테스트 가능한 구조를 우선한다.
11. 실제 API 호출이 불가능한 환경에서도 mock/fixture 테스트가 가능해야 한다.
12. API 호출 실패, 필드 누락, 빈 응답, 장 휴장, 장 마감 후 실행에도 프로그램이 죽지 않게 한다.

### 0.2 현재 등록된 환경변수

다음 환경변수는 이미 등록되어 있다고 가정한다.

```text
DART_API_KEY
KIS_APP_KEY
KIS_APP_SECRET
KIS_BASE_URL
```

절대 하지 말 것:

```text
print(os.environ["KIS_APP_SECRET"])
README에 실제 키 기록
로그에 토큰 기록
예외 메시지에 인증키 일부 노출
```

### 0.3 추가 환경변수 원칙

이번 시스템은 주문하지 않는 분석/감지 시스템이므로 계좌번호 환경변수는 필수로 요구하지 않는다.

다만 향후 자동주문을 구현하려면 아래 값이 추가로 필요할 수 있다.

```text
KIS_CANO          # 계좌번호 앞자리
KIS_ACNT_PRDT_CD # 계좌상품코드
KIS_IS_PAPER     # 모의/실전 구분
```

이번 구현에서 위 값이 없다고 실패 처리하지 말 것.  
단, README의 “향후 자동주문 확장 시 필요한 정보”에 명시한다.

---

## 1. 시스템 목표

이 프로젝트의 목표는 다음과 같다.

```text
장기 매물대 돌파 직전 종목을 사전에 찾고,
장중 거래량 예열·분봉 압력·기준가 재돌파를 감지하여,
급등 직전 후보를 점수화하고,
그 근거와 매수/손절/목표 가격대를 함께 출력하며,
이후 실제 성과를 백테스트/복기할 수 있게 만드는 시스템
```

핵심은 “무조건 오른다”가 아니다.

핵심은 다음이다.

```text
오래 눌린 종목이
월봉/주봉/일봉의 의미 있는 기준가 근처에 붙어 있고,
기준가를 반복적으로 두드리며,
눌림이 약하고,
거래량/거래대금이 붙기 시작하며,
테마 또는 재료가 살아 있을 때
급등 직전 후보로 분류한다.
```

---

## 2. 매매 방법론 정의

### 2.1 전체 흐름

이 방법론은 다음 순서로 작동한다.

```text
시장 상태 확인
→ 테마 상태 확인
→ 장기 차트 기준가 계산
→ 일봉 박스권/눌림 구조 확인
→ 장중 분봉/거래량 예열 확인
→ 점수화
→ 후보 알림
→ 결과 저장
→ 백테스트/복기
```

### 2.2 시장 상태 확인

시스템은 종목만 보지 않는다.  
먼저 시장이 감당 가능한 상태인지 확인한다.

확인 항목:

```text
코스피/코스닥 등락률
상승 종목 수 / 하락 종목 수
거래대금 상위 테마
지수 급락 여부
외국인/기관 수급 데이터가 있으면 반영
환율/금리/유가/전쟁 등 매크로 이벤트는 수동 메모 또는 외부 데이터로 확장
```

처음 구현에서 외부 매크로 데이터가 부족하면 무리하게 만들지 말고 `market_note` 수동 입력 구조를 둔다.

### 2.3 테마 상태 확인

테마는 자동화가 가장 어려운 영역이다.  
따라서 처음부터 완전 자동 테마 분석을 가정하면 안 된다.

기본 구조:

```text
data/theme_map.csv
code,name,theme,sub_theme
005010,휴스틸,강관,재건
006360,GS건설,건설,재건
064350,현대로템,방산,국방비
263750,펄어비스,게임,신작
```

테마 점수 계산:

```text
같은 theme 안에서 상승 종목 비율
같은 theme 안에서 거래대금 증가 종목 수
theme 대장주가 상승 중인지
theme 내 2등/3등 종목의 후발 움직임 여부
```

테마가 없으면 감지는 가능하되 점수 일부만 제외한다.

---

## 3. 차트 핵심 이론

### 3.1 월봉·주봉 수평 매물대

가장 중요한 기준이다.

시스템은 월봉/주봉/일봉을 각각 계산해야 한다.

찾아야 하는 가격대:

```text
과거 여러 번 막힌 가격
과거 여러 번 반등한 가격
대량 거래가 터진 가격
긴 윗꼬리가 나온 가격
장기 박스권 상단
장기 박스권 하단
최근 52주 고점/저점
```

출력에는 반드시 아래 값이 포함되어야 한다.

```text
nearest_support       # 현재가 아래 가장 가까운 지지선
nearest_resistance    # 현재가 위 또는 근처의 기준 저항선
trigger_price         # 돌파/재돌파 기준 가격
next_resistance       # 다음 목표 저항선
stop_price            # 손절 기준 가격
level_source          # 어떤 기준에서 나온 가격인지: monthly/weekly/daily/box/volume_bin/round_number
```

### 3.2 박스권 상단 돌파

일봉에서 최근 20~60거래일 가격 범위를 계산한다.

박스권 기준:

```text
box_high = 최근 N일 고점권
box_low = 최근 N일 저점권
box_mid = (box_high + box_low) / 2
box_width_pct = (box_high - box_low) / box_low
```

좋은 후보:

```text
현재가가 box_high의 -2% ~ +1% 범위
최근 저점이 상승
거래량이 서서히 증가
위쪽 next_resistance까지 최소 5% 이상 공간
```

### 3.3 지지선 눌림매수

“이하에서 줍줍” 유형이다.

조건:

```text
현재가가 기준 지지선 근처
장기 추세가 완전히 무너지지 않음
최근 급락 후 회복 시도
거래량이 줄며 눌림
기준선 회복 시 거래량 증가
```

### 3.4 거래대금 증가

거래량보다 거래대금이 더 중요할 수 있다.  
저가주와 고가주를 비교할 때 거래량만 보면 왜곡된다.

계산 항목:

```text
avg_volume_20
avg_trading_value_20
today_volume
today_trading_value
volume_ratio_20 = today_volume / avg_volume_20
trading_value_ratio_20 = today_trading_value / avg_trading_value_20
```

당일 장중에는 시간 보정이 필요하다.

예:

```text
현재 시각이 10:30이면 장 전체 시간 대비 약 25~30%만 지난 상태다.
그런데 누적 거래량이 20일 평균의 80%라면 강한 예열이다.
```

따라서 가능하면 시간 보정 비율을 적용한다.

```text
time_adjusted_volume_ratio =
today_volume / (avg_volume_20 * elapsed_market_ratio)
```

### 3.5 위쪽 매물대

매수 후보라도 바로 위에 강한 저항이 있으면 제외하거나 점수를 낮춘다.

좋은 후보:

```text
현재가에서 next_resistance까지 최소 5% 이상
가능하면 8~15% 공간
첫 목표가까지 손익비 1.5 이상
```

---

## 4. 급등 직전 핵심 포인트

### 4.1 핵심 정의

급등 직전 포인트는 다음이다.

```text
장기 매물대 바로 아래에서,
거래량이 붙기 시작하고,
눌림이 약해지고,
기준가를 계속 두드리는 순간
```

### 4.2 장중 예열 신호

분봉에서 감지해야 할 항목:

```text
최근 3~5개 분봉 저점 상승
최근 3~5개 분봉 고점 상승
양봉 거래량 > 음봉 거래량
기준가 근처에서 거래량 증가
눌림이 짧고 회복이 빠름
VWAP 위 유지
5분봉 20선 위 유지
돌파 후 기준가 아래로 오래 머물지 않음
```

VWAP는 Volume Weighted Average Price, 거래량 가중 평균가격이다.  
장중 평균 매수 단가에 가까운 기준이므로, 현재가가 VWAP 위에 있으면 매수세 우위로 볼 수 있다.

### 4.3 반복 터치

급등 직전에는 기준가를 한 번만 건드리지 않는다.  
여러 번 두드린다.

감지 방식:

```text
최근 M개 분봉 중 trigger_price 근처에 접근한 횟수
touch_count >= 2 또는 3이면 가점
touch 후 하락폭이 작으면 가점
touch 사이 저점이 높아지면 가점
```

예:

```text
저항선: 10,000
접근 허용 범위: ±0.3%
최근 30분 안에 9,970~10,030 구간을 3회 이상 터치
각 터치 후 저점이 9,750 → 9,850 → 9,920으로 상승
```

이 경우 “매물대를 계속 두드리는데 아래로 안 밀리는 상태”로 판단한다.

### 4.4 눌림 약함

눌림이 약한 종목은 아래 특징이 있다.

```text
지수가 빠지는데 종목은 덜 빠짐
같은 테마가 쉬는데 종목은 버팀
분봉상 음봉이 작음
하락 거래량이 작음
아래꼬리가 반복됨
기준선 아래로 내려가도 빠르게 회복
```

### 4.5 세력 손익분기점 해석

“세력 손익분기점”은 정확히 검증할 수 없는 표현이다.  
시스템에서는 이를 추측하지 말고, 다음과 같은 기술적 대체 변수로 계산한다.

```text
장기 대량거래 가격대
박스권 상단
이전 급락 시작점
전고점
거래량 집중 가격대
```

이 가격 위로 올라가면 기존 매물대가 수익권/본전권으로 바뀔 가능성이 있으므로 `trigger_price` 후보로 사용한다.

---

## 5. 매매 유형 분류

시스템은 후보를 아래 4개 유형 중 하나로 분류한다.

### A형: 지지선 눌림매수형

조건:

```text
현재가가 지지선 근처
최근 하락 후 기준선 회복 시도
거래량은 과열 전
위쪽 목표 공간 존재
```

출력:

```text
type = SUPPORT_PULLBACK
action_hint = 기준가 근처 분할 관심
```

### B형: 돌파 확인형

조건:

```text
현재가가 저항선 바로 아래
기준가 반복 터치
분봉 저점 상승
돌파 시 거래량 증가
```

출력:

```text
type = BREAKOUT_CONFIRM
action_hint = 돌파/재지지 확인
```

### C형: 급등 후 눌림 지지형

조건:

```text
전일 또는 당일 급등
현재 눌림
중요 지지선 방어
테마 유지
```

출력:

```text
type = POST_SPIKE_PULLBACK
action_hint = 지지선 이탈 여부 중심 관찰
```

### D형: 장기 박스권 맥점형

조건:

```text
월봉/주봉 장기 박스권
현재가가 장기 박스권 상단 근처
거래대금 증가
위 매물대 소화 가능성
```

출력:

```text
type = LONG_BOX_TRIGGER
action_hint = 장기 매물대 돌파 직전 후보
```

---

## 6. 점수화 기준

### 6.1 총점

총점은 100점 기준이다.

```text
장기 매물대/박스권 근접도        20점
기준가 반복 터치/재돌파 압력      15점
거래량/거래대금 예열             20점
분봉 상승 압력                   15점
위쪽 공간/손익비                 10점
테마 동조/대장주 후발성           10점
DART 재료/공시 안정성             5점
리스크 패널티                    -0~-30점
```

### 6.2 등급

```text
90점 이상: S급, 매우 강한 후보
80~89점: A급, 강한 후보
70~79점: B급, 관찰/조건부 후보
60~69점: C급, 약한 후보
60점 미만: 제외
```

### 6.3 리스크 패널티

아래 조건은 감점한다.

```text
관리종목/거래정지/투자주의/경고/위험: 강한 감점 또는 제외
최근 급등률 20% 이상 후 추격 상태: 감점
위쪽 저항까지 3% 미만: 감점
거래량 없는 돌파: 감점
장대 윗꼬리 반복: 감점
DART상 최근 악재성 공시: 감점
감사의견 비적정/상장폐지 사유/불성실공시 등: 제외 또는 강한 감점
```

---

## 7. KIS API 활용 기준

### 7.1 반드시 구현할 KIS 기능

KIS 관련 모듈은 다음 기능을 제공해야 한다.

```text
접근 토큰 발급
토큰 캐시/재사용
국내주식 현재가 조회
국내주식 기간별 시세 조회: 일/주/월/년
국내주식 당일 분봉 조회
종목정보파일 또는 종목마스터 로딩 구조
API 호출 재시도
호출 제한 대응
응답 필드 안전 파싱
```

### 7.2 구현 원칙

```text
KIS_APP_KEY, KIS_APP_SECRET, KIS_BASE_URL은 환경변수에서 읽는다.
토큰은 로그에 남기지 않는다.
KIS_BASE_URL은 실전/모의 URL 차이를 외부에서 제어하기 위한 값으로 사용한다.
HTTP timeout을 반드시 둔다.
API 오류는 사용자 친화적 한국어 메시지로 변환한다.
```

### 7.3 실시간 웹소켓

이번 전체 구조에는 실시간 웹소켓 확장 지점을 만들어둔다.

단, 웹소켓 접속키 발급과 실시간 체결 구독은 구현 난이도와 호출 제한이 있으므로 다음 중 하나로 처리한다.

1. 구현 가능하면 `realtime/` 모듈로 구현한다.
2. 불가능하면 인터페이스와 TODO를 남기고 REST polling 기반 감지를 완성한다.

REST polling만으로도 30초~60초 단위 감지는 가능해야 한다.

---

## 8. DART API 활용 기준

### 8.1 DART의 역할

DART는 급등 직전 타이밍 자체보다 다음 역할에 사용한다.

```text
최근 공시 확인
악재성 공시 리스크 제거
기업 기본정보 확인
재무 안전성 보조 점수
테마/재료 연결 보조
최근 주요사항보고서/단일판매공급계약/증자/전환사채 등 확인
```

### 8.2 반드시 구현할 DART 기능

```text
corp_code 다운로드/캐시
종목코드 → corp_code 매핑
최근 공시 검색
기업개황 조회
주요 재무정보 조회 가능 구조
공시 제목 기반 리스크 태그
```

### 8.3 DART 점수화

DART는 총점에서 5점 가점 또는 리스크 감점으로 사용한다.

가점 후보:

```text
최근 수주/공급계약/신사업/투자/실적 관련 긍정 공시
재무 안정성 양호
최근 공시가 테마와 연결됨
```

감점 후보:

```text
감사의견 관련 이슈
상장폐지/관리종목/불성실공시
대규모 유상증자
전환사채/신주인수권부사채 남발
소송/횡령/배임
영업정지
```

공시 감정 판단은 과장하지 말고, 제목 키워드 기반의 “리스크 태그” 수준으로 처리한다.  
LLM 판단이나 감성분석은 이번 구현의 필수 사항이 아니다.

---

## 9. 데이터 저장 구조

### 9.1 기본 저장소

처음부터 DB 구조를 둔다.  
SQLite를 기본값으로 사용하고, 추후 PostgreSQL/MySQL로 확장 가능하게 한다.

권장 경로:

```text
data/bajongbal.sqlite3
```

### 9.2 주요 테이블

```text
stocks
- code
- name
- market
- theme
- sub_theme
- is_active

price_daily
- code
- date
- open
- high
- low
- close
- volume
- trading_value

price_minute
- code
- datetime
- open
- high
- low
- close
- volume
- trading_value

levels
- code
- calculated_at
- nearest_support
- nearest_resistance
- trigger_price
- next_resistance
- stop_price
- level_source
- memo

signals
- detected_at
- code
- name
- signal_type
- signal_grade
- score
- current_price
- trigger_price
- nearest_support
- nearest_resistance
- next_resistance
- stop_price
- volume_ratio
- trading_value_ratio
- touch_count
- minute_trend
- theme_score
- dart_score
- risk_score
- reason_json

dart_filings
- code
- corp_code
- rcept_no
- report_nm
- rcept_dt
- risk_tags
- raw_json
```

### 9.3 CSV 출력

DB와 별도로 사람이 바로 볼 수 있는 CSV도 저장한다.

```text
outputs/signals_YYYYMMDD.csv
outputs/daily_candidates_YYYYMMDD.csv
outputs/backtest_result_YYYYMMDD.csv
```

`outputs/`는 기본적으로 gitignore 처리한다.

---

## 10. 프로젝트 구조

권장 구조:

```text
bajongbal/
├─ README.md
├─ pyproject.toml
├─ .gitignore
├─ .env.example
├─ data/
│  ├─ watchlist.example.csv
│  └─ theme_map.example.csv
├─ outputs/
├─ src/
│  └─ bajongbal/
│     ├─ __init__.py
│     ├─ config.py
│     ├─ cli.py
│     ├─ kis/
│     │  ├─ __init__.py
│     │  ├─ client.py
│     │  ├─ auth.py
│     │  ├─ parsers.py
│     │  └─ errors.py
│     ├─ dart/
│     │  ├─ __init__.py
│     │  ├─ client.py
│     │  ├─ corp_codes.py
│     │  ├─ filings.py
│     │  └─ risk_tags.py
│     ├─ market/
│     │  ├─ __init__.py
│     │  ├─ universe.py
│     │  ├─ themes.py
│     │  └─ market_state.py
│     ├─ strategy/
│     │  ├─ __init__.py
│     │  ├─ levels.py
│     │  ├─ boxes.py
│     │  ├─ intraday.py
│     │  ├─ scoring.py
│     │  ├─ signal_types.py
│     │  └─ risk.py
│     ├─ storage/
│     │  ├─ __init__.py
│     │  ├─ db.py
│     │  ├─ schema.py
│     │  └─ repositories.py
│     ├─ scanner/
│     │  ├─ __init__.py
│     │  ├─ daily_builder.py
│     │  ├─ intraday_scanner.py
│     │  └─ reporter.py
│     └─ backtest/
│        ├─ __init__.py
│        ├─ engine.py
│        └─ metrics.py
└─ tests/
   ├─ fixtures/
   ├─ test_levels.py
   ├─ test_scoring.py
   ├─ test_intraday.py
   ├─ test_dart_risk_tags.py
   └─ test_kis_parsers.py
```

---

## 11. CLI 요구사항

### 11.1 명령어

아래 명령어를 제공한다.

```bash
python -m bajongbal init-db
python -m bajongbal sync-dart
python -m bajongbal build-candidates --date 2026-04-24
python -m bajongbal scan --watchlist data/watchlist.example.csv --once
python -m bajongbal scan --watchlist data/watchlist.example.csv --interval-seconds 30
python -m bajongbal backtest --from 2026-01-01 --to 2026-04-24
python -m bajongbal report --date 2026-04-24
```

### 11.2 옵션

```text
--watchlist
--theme-map
--score-threshold
--interval-seconds
--once
--output
--use-dart
--no-dart
--max-symbols
--dry-run
```

`--dry-run`은 주문이 아니라 API 호출 최소화/샘플 데이터 기반 실행을 의미한다.

---

## 12. 출력 예시

콘솔 출력은 다음처럼 사람이 바로 판단할 수 있어야 한다.

```text
[급등직전 후보 감지]

시각: 2026-04-24 10:42:31
종목: 휴스틸(005010)
유형: LONG_BOX_TRIGGER
등급: A
점수: 86

현재가: 5,710
기준가: 5,710
지지선: 5,530
다음 저항선: 6,170
손절 기준: 5,420

거래량비율: 1.82배
거래대금비율: 2.11배
기준가 터치 횟수: 3회
분봉 저점 상승: Y
VWAP 위 유지: Y
테마: 강관/재건
DART 리스크: 없음

판단 근거:
- 월봉/주봉 장기 박스권 상단 근처
- 기준가를 반복 터치하면서 저점 상승
- 거래대금이 20일 평균 대비 빠르게 증가
- 다음 저항선까지 약 8.1% 공간
```

---

## 13. 백테스트 요구사항

### 13.1 목적

감지 신호가 실제로 유효했는지 검증한다.

### 13.2 검증 기준

신호 발생 후 다음 기간의 성과를 계산한다.

```text
+10분
+30분
+60분
당일 종가
1거래일 후
3거래일 후
5거래일 후
```

계산 항목:

```text
max_return_after_signal
min_return_after_signal
close_return_after_signal
hit_3pct
hit_5pct
hit_10pct
stop_hit
time_to_peak
```

### 13.3 백테스트 결과 요약

```text
신호 수
평균 수익률
중앙값 수익률
승률
3% 도달률
5% 도달률
손절 도달률
유형별 성과
테마별 성과
점수 구간별 성과
```

---

## 14. 테스트 요구사항

최소 테스트:

```text
level detector가 지지선/저항선을 찾는지
box detector가 박스권 상단을 찾는지
scoring이 조건별로 점수를 계산하는지
intraday detector가 반복 터치/저점 상승을 감지하는지
DART risk tag가 위험 공시 제목을 감지하는지
KIS parser가 문자열 숫자/빈 값/쉼표를 안전 변환하는지
API 오류 시 예외가 안전하게 처리되는지
```

실제 KIS/DART API 호출 테스트는 기본 단위 테스트에서 제외한다.  
필요하면 `integration` 마커를 붙인다.

---

## 15. README 필수 내용

README에는 반드시 포함한다.

```text
프로젝트 목적
매매 방법론 요약
환경변수 설정 방법
설치 방법
실행 방법
watchlist 작성 방법
theme_map 작성 방법
KIS API 사용 범위
DART API 사용 범위
자동주문 미포함 안내
감지 결과의 한계
백테스트 방법
테스트 실행 방법
보안 주의사항
```

---

## 16. gitignore 필수

아래 항목은 반드시 제외한다.

```text
.env
*.sqlite3
outputs/
alerts.csv
signals.csv
data/watchlist.csv
data/theme_map.csv
.kis_token*
.dart_cache*
__pycache__/
.pytest_cache/
.venv/
```

example 파일은 커밋한다.

```text
data/watchlist.example.csv
data/theme_map.example.csv
.env.example
```

---

## 17. Codex 작업 완료 기준

Codex는 작업 완료 후 아래를 한국어로 보고한다.

```text
변경 파일 목록
구현한 기능
사용한 환경변수
실행 방법
테스트 결과
실제 API 호출 여부
구현하지 못한 사항
추가로 사용자에게 필요한 정보
다음 수정 권장 사항
```

PR을 만들 수 있으면 PR까지 만든다.  
PR 제목과 본문은 한국어로 작성한다.

---

## 18. 추가 정보가 필요한 경우 반드시 물어볼 것

아래 정보가 없으면 임의로 결정하지 말고, 기본값/예시를 만들되 보고서에 “사용자 확인 필요”로 남긴다.

```text
감시할 기본 종목 리스트
테마 매핑 기준
알림 방식: 콘솔/CSV/텔레그램/카카오톡/이메일
실전/모의 KIS BASE URL의 실제 의미
호출 제한 기준
자동주문 여부
자동주문 시 계좌번호/상품코드
손절률 기본값
익절률 기본값
거래대금 최소 기준
제외할 종목군: ETF/ETN/SPAC/우선주/관리종목 등
```

---

## 19. 구현 우선순위

작업을 쪼개서 MVP로 끝내지 말고, 아래 전체를 가능한 한 한 번에 구현한다.

우선순위 1:

```text
프로젝트 구조
환경변수 설정
KIS 클라이언트
DART 클라이언트
기술적 레벨 계산
급등 직전 점수화
CLI
DB/CSV 저장
테스트
README
```

우선순위 2:

```text
백테스트
테마 점수화
DART 리스크 태그
리포트 생성
```

우선순위 3:

```text
웹소켓 실시간 체결
텔레그램/카카오톡 알림
웹 대시보드
자동주문
```

우선순위 3은 가능하면 확장 포인트만 만든다.  
자동주문은 사용자 명시 지시 전까지 구현하지 않는다.

---

## 20. 핵심 한 줄

이 시스템은 다음 문장을 코드로 구현하는 프로젝트다.

```text
장기 매물대 바로 아래에서,
기준가를 반복적으로 두드리고,
눌림이 약하며,
거래량과 거래대금이 붙기 시작하고,
위쪽 목표 공간이 남아 있는 종목을 자동으로 찾아낸다.
```
