# BAJONGBAL 개발 가이드

문서 목적: 이 문서는 `minuk12choi-boop/bajongbal` 저장소에서 Codex가 반드시 따라야 할 기준 문서다.  
목표는 단순 예제나 1차 MVP가 아니라, **KIS API, DART API, 네이버증권 테마 수집, FastAPI 웹 대시보드까지 포함한 급등 직전 종목 감지·분석·검증 시스템의 전체 구현 기준**을 한 번에 제공하는 것이다.

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
13. 사용자가 일일이 파일을 만들거나 테마를 수동 분류하지 않아도 되도록 자동 수집·캐시 구조를 만든다.
14. “조회 버튼을 누르면 웹에서 바로 후보가 나오는 시스템”을 기본 사용자 경험으로 설계한다.

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

향후 자동주문을 구현하려면 아래 값이 추가로 필요할 수 있다.

```text
KIS_CANO          # 계좌번호 앞자리
KIS_ACNT_PRDT_CD # 계좌상품코드
KIS_IS_PAPER     # 모의/실전 구분
```

이번 구현에서 위 값이 없다고 실패 처리하지 말 것.  
단, README의 “향후 자동주문 확장 시 필요한 정보”에 명시한다.

### 0.4 이번 구현에서 제외할 것

아래 기능은 이번 구현 범위에서 제외한다.

```text
자동매수
자동매도
계좌 조회
잔고 조회
주문 API 호출
텔레그램 알림 실제 발송
카카오톡 알림
이메일 알림
```

단, 알림 확장을 위한 인터페이스는 만들어도 된다.  
예: `notifiers/base.py`, `notifiers/web.py`, `notifiers/telegram.py`의 TODO 수준.

---

## 1. 시스템 목표

이 프로젝트의 목표는 다음과 같다.

```text
장기 매물대 돌파 직전 종목을 사전에 찾고,
장중 거래량 예열·분봉 압력·기준가 재돌파를 감지하여,
급등 직전 후보를 점수화하고,
그 근거와 매수/손절/목표 가격대를 함께 웹 대시보드에 출력하며,
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

## 2. 전체 서비스 구조

### 2.1 기본 사용자 흐름

사용자는 웹 대시보드에서 아래 흐름으로 사용한다.

```text
1. 웹 서버 실행
2. 브라우저에서 대시보드 접속
3. 하루 1회 [테마 갱신] 클릭
4. 장중 [조회] 클릭
5. 금일 시장/테마 상태 확인
6. 바종발식 급등직전 후보 확인
7. 각 후보 카드에서 시그널 수치·점수·매수/매도 후보가 확인
8. 사용자가 직접 HTS/MTS에서 최종 판단 후 매매
```

### 2.2 웹 기반 확정

이 프로젝트는 CLI만 만드는 도구가 아니다.  
**FastAPI 기반 웹 대시보드가 핵심 UI다.**

필수 UI:

```text
금일 시장/테마 상태 영역
바종발식 급등직전 후보 영역
종목별 시그널 상세 카드
종목별 시그널 지표 테이블
테마 갱신 버튼
조회 버튼
점수 필터
시장/테마/종목 필터
강한 후보 빨간 배지
```

### 2.3 조회 방식

이번 구현은 웹소켓 중심이 아니라 **수동 조회 + 서버 사이드 API 호출** 중심이다.

```text
[조회] 버튼 클릭
→ 서버가 KIS API 호출
→ 저장된 테마 캐시와 결합
→ DART 리스크 조회/캐시와 결합
→ 바종발식 점수 계산
→ 웹 화면에 최신 결과 표시
```

자동 새로고침은 가능하면 구현한다.

```text
자동 새로고침: OFF / 30초 / 60초 / 120초
```

기본값은 OFF다.

---

## 3. 매매 방법론 정의

### 3.1 전체 흐름

이 방법론은 다음 순서로 작동한다.

```text
시장 상태 확인
→ 테마 상태 확인
→ 장기 차트 기준가 계산
→ 일봉 박스권/눌림 구조 확인
→ 장중 분봉/거래량 예열 확인
→ DART 리스크 확인
→ 점수화
→ 후보 표시
→ 결과 저장
→ 백테스트/복기
```

### 3.2 시장 상태 확인

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

### 3.3 테마 상태 확인

테마는 네이버증권에서 하루 1회 수집한 **종목-테마 매핑표**를 기반으로 한다.

핵심 원칙:

```text
네이버증권은 실시간 시세 판단용으로 사용하지 않는다.
네이버증권은 테마 분류표 생성용으로만 사용한다.
장중 테마 강도와 주도주는 KIS 시세 + 테마 매핑표로 직접 계산한다.
```

---

## 4. 네이버증권 테마 수집 기준

### 4.1 역할

네이버증권은 아래 용도로만 사용한다.

```text
테마 목록 수집
테마별 구성 종목 수집
종목코드 ↔ 테마명 매핑 생성
테마 ID 저장
```

네이버증권에서 수집한 가격, 등락률, 거래량은 참고값으로 저장할 수 있으나,  
**시그널 계산의 기준 데이터로 사용하지 않는다.**

시그널 계산의 기준 데이터는 반드시 KIS API다.

### 4.2 테마 갱신 버튼

웹 대시보드에 `[테마 갱신]` 버튼을 둔다.

동작:

```text
[테마 갱신] 클릭
→ 서버에서 네이버증권 테마 페이지 자동 수집
→ page=1부터 순차 수집
→ 테마 목록이 비거나 이전 페이지와 동일하면 중단
→ 각 테마 상세 페이지 자동 수집
→ 테마별 구성 종목 저장
→ SQLite 캐시 갱신
→ 웹 화면에 수집 결과 표시
```

사용자는 URL을 직접 입력하거나 CSV를 직접 만들 필요가 없어야 한다.

### 4.3 수집 시작 URL

기본 시작 URL:

```text
https://finance.naver.com/sise/theme.naver?&page=1
```

페이지는 아래처럼 자동 증가시킨다.

```text
https://finance.naver.com/sise/theme.naver?&page=1
https://finance.naver.com/sise/theme.naver?&page=2
https://finance.naver.com/sise/theme.naver?&page=3
...
```

페이지 수를 하드코딩하지 않는다.

중단 조건:

```text
테마 테이블이 비어 있음
파싱된 테마 수가 0개
이전 페이지와 동일한 테마 목록 반복
HTTP 오류가 일정 횟수 이상 반복
```

### 4.4 테마 상세 페이지

테마 목록에서 상세 링크 또는 theme_id를 추출한다.

예상 상세 URL:

```text
https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}
```

상세 페이지에서 수집할 것:

```text
theme_id
theme_name
code
name
naver_price
naver_change_rate
naver_volume
naver_trading_value
source_url
collected_at
```

`naver_*` 필드는 참고용이다.  
KIS로 다시 조회한 값이 최종 판단 기준이다.

### 4.5 수집 모듈 요구사항

구현 파일 예시:

```text
src/bajongbal/collectors/naver_theme_collector.py
```

필수 함수:

```text
fetch_theme_list_page(page: int) -> str
parse_theme_list_page(html: str) -> list[ThemeSummary]
fetch_theme_detail(theme_id: str) -> str
parse_theme_detail_page(html: str, theme_id: str, theme_name: str) -> list[ThemeConstituent]
refresh_naver_themes() -> ThemeRefreshResult
```

요구사항:

```text
requests + BeautifulSoup 기반 서버 사이드 수집
브라우저에서 네이버 직접 호출 금지
User-Agent, Referer, Accept-Language 헤더 설정
HTTP timeout 설정
재시도 로직
인코딩 깨짐 방지
파싱 실패 시 기존 캐시 유지
수집 결과 요약 반환
```

권장 헤더:

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://finance.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}
```

### 4.6 네이버 실패 대응

네이버증권은 공식 API가 아니므로 실패 가능성을 전제한다.

실패 대응:

```text
네이버 수집 실패해도 전체 시스템은 죽지 않는다.
기존 캐시가 있으면 기존 캐시를 계속 사용한다.
기존 캐시도 없으면 테마 미분류로 표시한다.
KIS 기반 차트 시그널 계산은 계속 진행한다.
웹 화면에는 “테마 데이터 갱신 실패 / 기존 캐시 사용 중”을 표시한다.
```

---

## 5. 테마 강도와 주도주 계산

### 5.1 핵심 원칙

테마 강도와 주도주는 네이버증권에서 매번 받아오지 않는다.

```text
테마 분류: 네이버증권 하루 1회 갱신
테마 강도: KIS 시세 + 테마 캐시로 실시간 계산
테마 주도주: KIS 시세 + 테마 캐시로 실시간 계산
```

### 5.2 테마 강도 계산

테마별로 아래 값을 계산한다.

```text
theme_name
total_stock_count
up_count
flat_count
down_count
up_ratio
avg_change_rate
median_change_rate
total_trading_value
avg_trading_value_ratio_20
strong_signal_count
leader_candidates
theme_strength_score
```

테마 강도 점수 예시:

```text
상승 종목 비율                 30점
테마 평균 등락률               20점
거래대금 증가율                25점
강한 후보 종목 수              15점
테마 내 주도주 존재            10점
```

### 5.3 테마 주도주 계산

주도주는 네이버의 표시값이 아니라 직접 계산한다.

주도주 점수 예시:

```text
등락률 점수
거래대금 점수
20일 평균 거래대금 대비 증가율
테마 내 상대강도
바종발식 시그널 점수
```

출력 예시:

```text
방산 테마
- 상승 종목 수: 9 / 12
- 상승 비율: 75.0%
- 평균 등락률: +2.1%
- 거래대금 합계: 3,240억
- 20일 평균 거래대금 대비: 1.8배
- 주도주 TOP3: 현대로템, LIG넥스원, 한화에어로스페이스
```

---

## 6. 웹 대시보드 UI 요구사항

### 6.1 기본 화면 순서

대시보드 화면은 아래 순서로 구성한다.

```text
1. 헤더
2. 조작 영역
3. 금일 시장/테마 상태 영역
4. 바종발식 급등직전 후보 영역
5. 종목별 상세 카드 영역
6. 최근 감지 이력 영역
```

### 6.2 헤더

표시 항목:

```text
BAJONGBAL 급등직전 감지기
현재 시각
KIS 연결 상태
DART 연결 상태
네이버 테마 캐시 마지막 갱신 시각
자동주문 미사용 경고
```

### 6.3 조작 영역

필수 버튼/필터:

```text
[테마 갱신]
[조회]
시장: 전체 / KOSPI / KOSDAQ
감시 대상: 관심종목 / 테마 전체 / 거래대금 상위 / 전체 캐시 종목
최소 점수: 60 / 70 / 80 / 90
테마 필터
종목 검색
최대 조회 종목 수
DART 리스크 포함 여부
자동 새로고침: OFF / 30초 / 60초 / 120초
```

### 6.4 금일 시장/테마 상태 영역

상단에 따로 표시한다.

필수 표시:

```text
시장 상태 요약
상승/하락 종목 수
강한 테마 TOP5
약한 테마 TOP5
테마별 상승 비율
테마별 평균 등락률
테마별 거래대금 증가율
테마별 주도주 TOP3
테마별 바종발식 후보 수
```

예시:

```text
[금일 테마 상태]
1. 방산: 상승비율 75.0%, 평균등락률 +2.1%, 거래대금비 1.8배, 주도주 현대로템/LIG넥스원
2. 강관/재건: 상승비율 68.2%, 평균등락률 +1.7%, 거래대금비 2.3배, 주도주 휴스틸/하이스틸
```

### 6.5 바종발식 급등직전 후보 영역

테마 상태 영역과 별도로 둔다.

필수 표시:

```text
강한 후보 수
관심 후보 수
관찰 후보 수
점수순 테이블
점수 80점 이상 빨간 배지
```

테이블 컬럼:

```text
순위
등급
점수
종목명
종목코드
테마
현재가
등락률
거래대금
기준가
기준가 거리 %
지지선
다음 저항선
위쪽 여유 %
손절가
거래량비
거래대금비
분봉 기준
분봉 분석 시간대
터치 횟수
DART 리스크
판정 유형
```

### 6.6 종목별 상세 카드

종목이 추려졌을 때는 각 종목 상단에 사람이 바로 이해할 수 있는 요약 문장이 있어야 한다.

필수 요약 형식:

```text
[종목명]은 현재가 N원이 장기 기준가 N원에 X% 이내로 접근했고,
N분봉 기준 HH:MM~HH:MM 구간에서 저점이 A → B → C로 상승했습니다.
당일 거래량은 20일 평균 대비 X배, 거래대금은 20일 평균 대비 Y배로 증가했습니다.
다음 저항선 N원까지 Z% 여유가 있어 바종발식 기준으로 상승 예상 후보로 감지됩니다.
```

매매 계획은 반드시 별도 표시한다.

```text
공격형 매수 후보:
- N원~N원 지지 확인 시 분할 관심

보수형 매수 후보:
- N원 돌파 후 N원 재지지 확인 시 관심

손절 기준:
- N원 이탈
- 또는 N분봉 기준 거래량 동반 장대음봉

예상 분할 매도 후보:
- 1차: N원
- 2차: N원
- 3차: N원~N원
```

주의 문구:

```text
자동매매가 아니며, 최종 매수/매도는 사용자가 직접 판단한다.
```

### 6.7 시그널 지표 상세 테이블

종목 카드 안에는 점수의 근거가 되는 모든 지표를 표시한다.

필수 지표:

```text
장기 매물대 근접 점수
반복 터치 점수
거래량 예열 점수
거래대금 예열 점수
분봉 저점 상승 점수
분봉 고점 상승 점수
VWAP 위 유지 여부
5분봉 20선 위 유지 여부
테마 강도 점수
테마 주도주 점수
333 조정 패턴 점수
333 감지 봉 기준
333 패턴 구조
333 음봉 집단 1/2/3 기간
333 마지막 양봉 날짜·가격·거래량비
DART 리스크 점수
리스크 패널티
총점
```

분봉 관련 지표는 반드시 검증 가능한 형태로 표시한다.

나쁜 예:

```text
최근 5개 분봉 저점 상승
```

좋은 예:

```text
3분봉 기준 10:21~10:36
최근 5개 저점: 5,620 → 5,650 → 5,660 → 5,680 → 5,690
최근 5개 고점: 5,700 → 5,710 → 5,730 → 5,750 → 5,760
판정: 저점 상승 Y, 고점 상승 Y
```

---

## 7. 차트 핵심 이론

### 7.1 월봉·주봉 수평 매물대

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
라운드 넘버
```

출력에는 반드시 아래 값이 포함되어야 한다.

```text
nearest_support       # 현재가 아래 가장 가까운 지지선
nearest_resistance    # 현재가 위 또는 근처의 기준 저항선
trigger_price         # 돌파/재돌파 기준 가격
next_resistance       # 다음 목표 저항선
stop_price            # 손절 기준 가격
level_source          # monthly/weekly/daily/box/volume_bin/round_number
```

### 7.2 박스권 상단 돌파

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

### 7.3 지지선 눌림매수

“이하에서 줍줍” 유형이다.

조건:

```text
현재가가 기준 지지선 근처
장기 추세가 완전히 무너지지 않음
최근 급락 후 회복 시도
거래량이 줄며 눌림
기준선 회복 시 거래량 증가
```

### 7.4 거래대금 증가

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

```text
time_adjusted_volume_ratio =
today_volume / (avg_volume_20 * elapsed_market_ratio)
```

### 7.5 위쪽 매물대

매수 후보라도 바로 위에 강한 저항이 있으면 제외하거나 점수를 낮춘다.

좋은 후보:

```text
현재가에서 next_resistance까지 최소 5% 이상
가능하면 8~15% 공간
첫 목표가까지 손익비 1.5 이상
```

---

## 8. 급등 직전 핵심 포인트

### 8.1 핵심 정의

급등 직전 포인트는 다음이다.

```text
장기 매물대 바로 아래에서,
거래량이 붙기 시작하고,
눌림이 약해지고,
기준가를 계속 두드리는 순간
```

### 8.2 장중 예열 신호

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

### 8.3 반복 터치

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

### 8.4 눌림 약함

눌림이 약한 종목은 아래 특징이 있다.

```text
지수가 빠지는데 종목은 덜 빠짐
같은 테마가 쉬는데 종목은 버팀
분봉상 음봉이 작음
하락 거래량이 작음
아래꼬리가 반복됨
기준선 아래로 내려가도 빠르게 회복
```

### 8.5 세력 손익분기점 해석

“세력 손익분기점”은 정확히 검증할 수 없는 표현이다.  
시스템에서는 이를 추측하지 말고, 다음과 같은 기술적 대체 변수로 계산한다.

```text
장기 대량거래 가격대
박스권 상단
이전 급락 시작점
전고점
거래량 집중 가격대
```

---

## 9. 매매 유형 분류

시스템은 후보를 아래 4개 유형 중 하나로 분류한다.

### A형: 지지선 눌림매수형

```text
type = SUPPORT_PULLBACK
action_hint = 기준가 근처 분할 관심
```

조건:

```text
현재가가 지지선 근처
최근 하락 후 기준선 회복 시도
거래량은 과열 전
위쪽 목표 공간 존재
```

### B형: 돌파 확인형

```text
type = BREAKOUT_CONFIRM
action_hint = 돌파/재지지 확인
```

조건:

```text
현재가가 저항선 바로 아래
기준가 반복 터치
분봉 저점 상승
돌파 시 거래량 증가
```

### C형: 급등 후 눌림 지지형

```text
type = POST_SPIKE_PULLBACK
action_hint = 지지선 이탈 여부 중심 관찰
```

조건:

```text
전일 또는 당일 급등
현재 눌림
중요 지지선 방어
테마 유지
```

### D형: 장기 박스권 맥점형

```text
type = LONG_BOX_TRIGGER
action_hint = 장기 매물대 돌파 직전 후보
```

조건:

```text
월봉/주봉 장기 박스권
현재가가 장기 박스권 상단 근처
거래대금 증가
위 매물대 소화 가능성
```

---

## 10. 점수화 기준

### 10.1 총점

총점은 100점 기준이다.

```text
장기 매물대/박스권 근접도        18점
기준가 반복 터치/재돌파 압력      15점
거래량/거래대금 예열             20점
분봉 상승 압력                   12점
333 조정 패턴                    10점
위쪽 공간/손익비                 10점
테마 동조/대장주 후발성           10점
DART 재료/공시 안정성             5점
리스크 패널티                    -0~-30점
```

### 10.2 등급

```text
90점 이상: S급, 매우 강한 후보
80~89점: A급, 강한 후보
70~79점: B급, 관찰/조건부 후보
60~69점: C급, 약한 후보
60점 미만: 제외
```

웹 표시:

```text
90점 이상: 진한 빨간 배지
80~89점: 빨간 배지
70~79점: 주황 배지
60~69점: 노란 배지
```

### 10.3 리스크 패널티

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

## 11. KIS API 활용 기준

### 11.1 반드시 구현할 KIS 기능

KIS 관련 모듈은 다음 기능을 제공해야 한다.

```text
접근 토큰 발급
토큰 캐시/재사용
국내주식 현재가 조회
국내주식 기간별 시세 조회: 일/주/월/년
국내주식 당일 분봉 조회
국내주식 일별 분봉 조회
종목정보파일 또는 종목마스터 로딩 구조
API 호출 재시도
호출 제한 대응
응답 필드 안전 파싱
```

### 11.2 필요한 데이터

필수 데이터:

```text
현재가
등락률
거래량
거래대금
일봉 OHLCV
주봉 OHLCV
월봉 OHLCV
당일 분봉 OHLCV
일별 분봉 OHLCV
```

OHLCV는 Open, High, Low, Close, Volume을 의미한다.

### 11.3 구현 원칙

```text
KIS_APP_KEY, KIS_APP_SECRET, KIS_BASE_URL은 환경변수에서 읽는다.
토큰은 로그에 남기지 않는다.
KIS_BASE_URL은 실전/모의 URL 차이를 외부에서 제어하기 위한 값으로 사용한다.
HTTP timeout을 반드시 둔다.
API 오류는 사용자 친화적 한국어 메시지로 변환한다.
호출 제한을 고려하여 캐시와 max_symbols 옵션을 둔다.
```

### 11.4 실시간 웹소켓

이번 전체 구조에는 실시간 웹소켓 확장 지점을 만들어둔다.

단, 이번 구현의 기본은 REST polling이다.

```text
REST polling으로 조회 버튼/자동 새로고침 동작 완성
웹소켓은 realtime/ 모듈 인터페이스 또는 TODO로 남김
```

---

## 12. DART API 활용 기준

### 12.1 DART의 역할

DART는 급등 직전 타이밍 자체보다 다음 역할에 사용한다.

```text
최근 공시 확인
악재성 공시 리스크 제거
기업 기본정보 확인
재무 안전성 보조 점수
테마/재료 연결 보조
최근 주요사항보고서/단일판매공급계약/증자/전환사채 등 확인
```

### 12.2 반드시 구현할 DART 기능

```text
corp_code 다운로드/캐시
종목코드 → corp_code 매핑
최근 공시 검색
기업개황 조회
주요 재무정보 조회 가능 구조
공시 제목 기반 리스크 태그
```

### 12.3 DART 점수화

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

## 13. 데이터 저장 구조

### 13.1 기본 저장소

처음부터 DB 구조를 둔다.  
SQLite를 기본값으로 사용하고, 추후 PostgreSQL/MySQL로 확장 가능하게 한다.

권장 경로:

```text
data/bajongbal.sqlite3
```

### 13.2 주요 테이블

```text
stocks
- code
- name
- market
- is_active

theme_snapshots
- id
- collected_at
- theme_id
- theme_name
- source_url
- raw_change_rate
- raw_summary_json

theme_constituents
- id
- collected_at
- theme_id
- theme_name
- code
- name
- naver_price
- naver_change_rate
- naver_volume
- naver_trading_value
- source_url

stock_theme_map
- code
- name
- theme_id
- theme_name
- first_collected_at
- last_collected_at
- is_active

theme_strengths
- calculated_at
- theme_id
- theme_name
- total_stock_count
- up_count
- flat_count
- down_count
- up_ratio
- avg_change_rate
- median_change_rate
- total_trading_value
- avg_trading_value_ratio_20
- strong_signal_count
- leader_json
- theme_strength_score

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
- interval_min
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
- theme_names
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
- time_adjusted_volume_ratio
- touch_count
- minute_interval
- minute_window_start
- minute_window_end
- minute_lows_json
- minute_highs_json
- minute_trend
- vwap
- is_above_vwap
- theme_score
- dart_score
- risk_score
- has_333_pattern
- pattern_333_timeframe
- pattern_333_grade
- score_333
- pattern_333_summary
- reason_json
- trade_plan_json

pattern_333
- id
- code
- name
- timeframe
- detected_at
- pattern_start_date
- pattern_end_date
- pattern_sequence
- pattern_grade
- down_group_1_json
- down_group_2_json
- down_group_3_json
- last_up_group_json
- pattern_high
- pattern_low
- correction_pct
- last_up_volume_ratio
- next_resistance
- upside_room_pct
- stop_price
- score_333
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

### 13.3 CSV 출력

DB와 별도로 사람이 바로 볼 수 있는 CSV도 저장한다.

```text
outputs/signals_YYYYMMDD.csv
outputs/daily_candidates_YYYYMMDD.csv
outputs/theme_strength_YYYYMMDD.csv
outputs/backtest_result_YYYYMMDD.csv
```

`outputs/`는 기본적으로 gitignore 처리한다.

---

## 14. 프로젝트 구조

권장 구조:

```text
bajongbal/
├─ README.md
├─ BAJONGBAL_DEV_GUIDE.md
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
│     ├─ __main__.py
│     ├─ config.py
│     ├─ cli.py
│     ├─ web/
│     │  ├─ __init__.py
│     │  ├─ app.py
│     │  ├─ routes.py
│     │  ├─ schemas.py
│     │  ├─ templates/
│     │  │  ├─ base.html
│     │  │  ├─ dashboard.html
│     │  │  └─ partials/
│     │  │     ├─ theme_status.html
│     │  │     ├─ signal_table.html
│     │  │     └─ signal_card.html
│     │  └─ static/
│     │     ├─ app.css
│     │     └─ app.js
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
│     ├─ collectors/
│     │  ├─ __init__.py
│     │  └─ naver_theme_collector.py
│     ├─ market/
│     │  ├─ __init__.py
│     │  ├─ universe.py
│     │  ├─ themes.py
│     │  ├─ theme_strength.py
│     │  └─ market_state.py
│     ├─ strategy/
│     │  ├─ __init__.py
│     │  ├─ levels.py
│     │  ├─ boxes.py
│     │  ├─ pattern_333.py
│     │  ├─ intraday.py
│     │  ├─ scoring.py
│     │  ├─ signal_types.py
│     │  ├─ trade_plan.py
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
│     ├─ notifiers/
│     │  ├─ __init__.py
│     │  ├─ base.py
│     │  └─ web.py
│     └─ backtest/
│        ├─ __init__.py
│        ├─ engine.py
│        └─ metrics.py
└─ tests/
   ├─ fixtures/
   ├─ test_levels.py
   ├─ test_scoring.py
   ├─ test_intraday.py
   ├─ test_trade_plan.py
   ├─ test_naver_theme_parser.py
   ├─ test_theme_strength.py
   ├─ test_pattern_333.py
   ├─ test_dart_risk_tags.py
   └─ test_kis_parsers.py
```

---

## 15. CLI 요구사항

웹이 핵심이지만 CLI도 제공한다.

### 15.1 명령어

```bash
python -m bajongbal init-db
python -m bajongbal refresh-themes
python -m bajongbal sync-dart
python -m bajongbal build-candidates --date 2026-04-24
python -m bajongbal scan --watchlist data/watchlist.example.csv --once
python -m bajongbal scan --watchlist data/watchlist.example.csv --interval-seconds 30
python -m bajongbal web --host 0.0.0.0 --port 8000
python -m bajongbal backtest --from 2026-01-01 --to 2026-04-24
python -m bajongbal report --date 2026-04-24
```

### 15.2 옵션

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
--host
--port
```

`--dry-run`은 주문이 아니라 API 호출 최소화/샘플 데이터 기반 실행을 의미한다.

---

## 16. 웹 API 요구사항

FastAPI 라우트 예시:

```text
GET  /
GET  /dashboard
POST /api/themes/refresh
GET  /api/themes/status
GET  /api/themes/today
POST /api/scan
GET  /api/signals/recent
GET  /api/health
```

### 16.1 `/api/themes/refresh`

동작:

```text
네이버증권 테마 자동 수집
SQLite 캐시 갱신
수집 결과 반환
```

반환 예시:

```json
{
  "ok": true,
  "collected_at": "2026-04-24T08:45:12",
  "theme_count": 182,
  "constituent_count": 3120,
  "used_cache": false,
  "message": "테마 갱신 완료"
}
```

### 16.2 `/api/scan`

동작:

```text
KIS 현재가/기간별시세/분봉 조회
테마 캐시 결합
DART 리스크 결합
시그널 계산
결과 저장
결과 반환
```

반환에는 반드시 아래가 포함되어야 한다.

```text
market_summary
theme_strengths
signals
errors
warnings
```

---

## 17. 출력 예시

### 17.1 웹 카드 요약 예시

```text
[휴스틸] 🔴 A급 강한 후보 / 86점

현재가 5,710원이 장기 기준가 5,700원에 0.18% 이내로 접근했습니다.
3분봉 기준 10:21~10:36 구간에서 저점이 5,620 → 5,650 → 5,660 → 5,680 → 5,690으로 상승했습니다.
당일 거래량은 20일 평균 대비 1.82배, 거래대금은 2.11배로 증가했습니다.
다음 저항선 6,170원까지 8.05% 여유가 있어 바종발식 기준으로 상승 예상 후보로 감지됩니다.
최근 7일 내 DART 악재성 공시는 감지되지 않았습니다.

매매 계획:
- 공격형 매수: 5,650~5,720원 지지 확인 시 분할 관심
- 보수형 매수: 5,720원 돌파 후 5,700원 재지지 확인 시 관심
- 손절: 5,520원 이탈
- 1차 매도: 6,000원
- 2차 매도: 6,170원
- 3차 매도: 6,400~6,500원
```

### 17.2 콘솔 출력 예시

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
분봉 기준: 3분봉
분석 시간대: 10:21~10:36
분봉 저점: 5,620 → 5,650 → 5,660 → 5,680 → 5,690
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

## 18. 백테스트 요구사항

### 18.1 목적

감지 신호가 실제로 유효했는지 검증한다.

### 18.2 검증 기준

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

### 18.3 백테스트 결과 요약

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

## 19. 테스트 요구사항

최소 테스트:

```text
네이버 테마 목록 파싱 테스트
네이버 테마 상세 종목 파싱 테스트
테마 수집 실패 시 기존 캐시 사용 테스트
theme_strength 계산 테스트
level detector가 지지선/저항선을 찾는지
box detector가 박스권 상단을 찾는지
scoring이 조건별로 점수를 계산하는지
intraday detector가 반복 터치/저점 상승을 감지하는지
trade_plan이 매수가/손절가/목표가를 산출하는지
333 전략이 U-D-U-D-U-D-U 구조와 실패 구조를 구분하는지
333 전략이 고점 이후 조정 조건, 마지막 양봉, 거래량 증가를 점수화하는지
DART risk tag가 위험 공시 제목을 감지하는지
KIS parser가 문자열 숫자/빈 값/쉼표를 안전 변환하는지
API 오류 시 예외가 안전하게 처리되는지
FastAPI 라우트가 mock 데이터로 정상 응답하는지
```

실제 KIS/DART/네이버 외부 호출 테스트는 기본 단위 테스트에서 제외한다.  
필요하면 `integration` 마커를 붙인다.

---

## 20. README 필수 내용

README에는 반드시 포함한다.

```text
프로젝트 목적
매매 방법론 요약
환경변수 설정 방법
설치 방법
웹 실행 방법
CLI 실행 방법
테마 갱신 방법
조회 방법
watchlist 작성 방법
KIS API 사용 범위
DART API 사용 범위
네이버증권 테마 수집 방식과 한계
자동주문 미포함 안내
감지 결과의 한계
백테스트 방법
테스트 실행 방법
보안 주의사항
```

---

## 21. gitignore 필수

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
.naver_theme_cache*
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

## 22. Codex 작업 완료 기준

Codex는 작업 완료 후 아래를 한국어로 보고한다.

```text
변경 파일 목록
구현한 기능
사용한 환경변수
실행 방법
웹 대시보드 접속 방법
테마 갱신 방법
조회 방법
테스트 결과
실제 API 호출 여부
구현하지 못한 사항
추가로 사용자에게 필요한 정보
다음 수정 권장 사항
```

PR을 만들 수 있으면 PR까지 만든다.  
PR 제목과 본문은 한국어로 작성한다.

---

## 23. 추가 정보가 필요한 경우 반드시 물어볼 것

아래 정보가 없으면 임의로 결정하지 말고, 기본값/예시를 만들되 보고서에 “사용자 확인 필요”로 남긴다.

```text
감시할 기본 종목 리스트
기본 조회 시장: KOSPI/KOSDAQ/전체
테마 갱신 주기
KIS 호출 제한 기준
실전/모의 KIS BASE URL의 실제 의미
손절률 기본값
익절률 기본값
거래대금 최소 기준
제외할 종목군: ETF/ETN/SPAC/우선주/관리종목 등
분봉 기준: 1분/3분/5분 중 기본값
자동 새로고침 기본값
DART 조회 기간 기본값
```

---

## 24. 구현 우선순위

작업을 쪼개서 MVP로 끝내지 말고, 아래 전체를 가능한 한 한 번에 구현한다.

우선순위 1:

```text
프로젝트 구조
환경변수 설정
FastAPI 웹 대시보드
SQLite 스키마
네이버 테마 수집/캐시
KIS 클라이언트
DART 클라이언트
기술적 레벨 계산
테마 강도 계산
급등 직전 점수화
333 조정 패턴 감지/점수화
종목별 매매계획 생성
웹 카드/테이블 출력
CLI
DB/CSV 저장
테스트
README
```

우선순위 2:

```text
백테스트
DART 리스크 태그 고도화
리포트 생성
자동 새로고침
최근 감지 이력
```

우선순위 3:

```text
웹소켓 실시간 체결
텔레그램/카카오톡 알림
자동주문
```

우선순위 3은 가능하면 확장 포인트만 만든다.  
자동주문은 사용자 명시 지시 전까지 구현하지 않는다.  
텔레그램 알림은 이번 구현에서 제외한다.

---


## 25. 333 전략 정의 및 자동 감지 기준

### 25.1 333 전략의 위치

333 전략은 독립적인 최종 매수 신호가 아니라, **고점 이후 조정이 3번에 걸쳐 정리되고 있는지 확인하는 보조 패턴 필터**다.

즉, 기존 바종발식 조건인 아래 항목들과 함께 판단한다.

```text
장기 매물대 근접
기준가 반복 터치
거래량/거래대금 예열
눌림 약함
테마 강도
DART 리스크 없음
333 조정 패턴 감지
```

333 전략이 감지되더라도 다른 조건이 약하면 강한 후보로 분류하지 않는다.  
반대로 장기 매물대, 거래대금, 테마 강도가 강한 종목에서 333 전략까지 감지되면 신뢰도를 높이는 보조 점수로 사용한다.

### 25.2 핵심 정의

333 전략은 **비교적 고점에서 하락 조정이 진행될 때** 보는 캔들 패턴이다.

핵심 구조는 다음과 같다.

```text
양봉 그룹
→ 음봉 집단 1
→ 양봉 그룹
→ 음봉 집단 2
→ 양봉 그룹
→ 음봉 집단 3
→ 마지막 양봉 그룹
```

압축 구조:

```text
U-D-U-D-U-D-U
```

의미:

```text
U = 양봉 그룹
D = 음봉 그룹
```

그룹은 캔들 1개일 수도 있고 여러 개일 수도 있다.

예시:

```text
양봉 - 음봉음봉 - 양봉 - 음봉음봉음봉 - 양봉 - 음봉음봉 - 양봉
양봉양봉 - 음봉 - 양봉 - 음봉음봉 - 양봉양봉 - 음봉음봉음봉 - 양봉
```

### 25.3 필수 감지 조건

333 전략 감지는 아래 조건을 모두 만족해야 한다.

```text
1. 비교적 고점 이후 하락 조정 구간이어야 한다.
2. 첫 그룹은 양봉 그룹이어야 한다.
3. 마지막 그룹도 양봉 그룹이어야 한다.
4. 중간에 음봉 그룹이 정확히 3개 있어야 한다.
5. 각 음봉 그룹은 양봉 그룹으로 분리되어 있어야 한다.
6. 마지막 양봉은 3번째 음봉 집단 이후에 나타나야 한다.
```

통과 구조:

```text
U-D-U-D-U-D-U
```

실패 구조 예시:

```text
U-D-D-U-D-U
U-D-U-D-D-U
D-U-D-U-D-U
U-D-U-D-U-D
U-D-U-D-U-D-D
```

### 25.4 실전 해석

333 전략은 아래 구조로 해석한다.

```text
1차 하락
→ 기술적 반등
→ 2차 하락
→ 기술적 반등
→ 3차 하락
→ 마지막 반전 양봉
```

따라서 333 전략은 **3파 조정 후 반등 시도 패턴**으로 본다.

실전적으로 의미가 커지는 조건:

```text
고점 이후 충분히 조정받은 상태
3번째 음봉 집단에서 더 이상 크게 밀리지 않음
마지막 양봉이 지지선 근처에서 출현
마지막 양봉에 거래량 증가 동반
마지막 양봉이 단기 이동평균선을 회복
마지막 양봉 이후 기준가 재돌파 가능성 존재
```

### 25.5 분석 봉 기준

333 전략은 여러 시간 프레임에서 감지할 수 있어야 한다.

지원 기준:

```text
일봉
주봉
월봉
년봉
```

기본 우선순위:

```text
1순위: 주봉 333
2순위: 월봉 333
3순위: 일봉 333
4순위: 년봉 333
```

바종발식 매매법은 장기 매물대와 조정 구조를 중요하게 보기 때문에, 단기 분봉 333은 기본 감지 대상에서 제외한다.  
분봉은 333 전략보다 장중 예열, 저점 상승, 기준가 반복 터치 감지에 사용한다.

### 25.6 코드화 규칙

캔들 색상 분류:

```text
close > open  → U
close < open  → D
close == open → N
```

도지 처리:

```text
N은 기본적으로 직전 그룹에 흡수한다.
N이 연속 2개 이상 나오면 중립성이 강하므로 333 신뢰도를 낮춘다.
도지 때문에 구조가 애매하면 detected=False, weak_match=True로 처리한다.
```

그룹 압축 예시:

```text
원본: U U D D D U D D U U D U U
압축: U-D-U-D-U-D-U
```

기본 탐색 범위:

```text
일봉: 최근 20~80봉
주봉: 최근 20~80봉
월봉: 최근 12~60봉
년봉: 최근 8~30봉
```

### 25.7 고점 이후 조정 조건

333 전략은 아무 위치에서나 감지하면 안 된다.  
반드시 비교적 고점 이후 조정 구간이어야 한다.

조건:

```text
패턴 시작점 근처가 최근 N봉 고점권이어야 한다.
패턴 전체 구간 중 최고가가 시작부 30% 이내에 있어야 한다.
현재가는 패턴 최고가 대비 일정 비율 이상 조정받은 상태여야 한다.
```

기본값:

```text
일봉: 최근 고점 대비 -8% 이상 조정
주봉: 최근 고점 대비 -12% 이상 조정
월봉: 최근 고점 대비 -20% 이상 조정
년봉: 최근 고점 대비 -25% 이상 조정
```

이 조건을 만족하지 않으면 333 전략으로 분류하지 않는다.

### 25.8 마지막 양봉 조건

333 전략에서 가장 중요한 것은 마지막 양봉이다.

마지막 양봉은 다음 조건 중 일부를 만족할수록 신뢰도가 높다.

```text
3번째 음봉 집단의 저점을 깨지 않고 출현
직전 음봉의 고가 일부를 회복
단기 이동평균선 회복
지지선 또는 장기 이동평균선 근처에서 출현
거래량이 직전 음봉 평균보다 증가
아래꼬리가 있거나 저점 방어 흔적 존재
다음 기준가 또는 저항선까지 상승 여유 존재
```

마지막 양봉이 약하면 333 전략은 감지되더라도 `weak_333=True`로 표시한다.

### 25.9 점수화 기준

333 전략은 총점 100점 중 최대 10점의 보조 점수로 반영한다.

점수 구조:

```text
333 구조 일치: 4점
고점 이후 충분한 조정: 2점
마지막 양봉 위치 양호: 2점
마지막 양봉 거래량 증가: 1점
다음 저항선까지 상승 여유 존재: 1점
```

333 전략이 감지되지 않아도 다른 조건이 강하면 후보가 될 수 있다.  
333 전략이 감지되면 후보 신뢰도를 높이는 보조 요소로 사용한다.

### 25.10 333 등급

333 전략 자체에도 별도 등급을 부여한다.

```text
STRONG_333:
- U-D-U-D-U-D-U 구조 명확
- 고점 이후 충분한 조정
- 마지막 양봉 거래량 증가
- 지지선 또는 이동평균선 근처에서 출현
- 다음 저항선까지 5% 이상 여유

NORMAL_333:
- U-D-U-D-U-D-U 구조 확인
- 마지막 양봉 출현
- 거래량 또는 지지선 조건 일부 부족

WEAK_333:
- 구조는 유사하지만 도지/혼합 캔들로 애매함
- 마지막 양봉이 약함
- 고점 이후 조정폭이 부족함

NO_333:
- 구조 불일치
```

### 25.11 UI 표시 기준

웹 대시보드의 종목 카드에는 333 전략 정보를 반드시 표시한다.

표시 예시:

```text
333 전략: 감지됨
등급: STRONG_333
분석 봉: 주봉
패턴 구조: U-D-U-D-U-D-U
해석: 고점 이후 3개의 음봉 조정 집단이 양봉으로 분리되었고, 마지막 양봉이 출현했습니다.
현재 위치: 3번째 조정 이후 반전 양봉 구간
```

상세 수치:

```text
패턴 시작일
패턴 종료일
분석 봉 기준
음봉 집단 1 기간
음봉 집단 2 기간
음봉 집단 3 기간
마지막 양봉 날짜
패턴 최고가
패턴 최저가
고점 대비 조정률
마지막 양봉 거래량 / 직전 5봉 평균 거래량
다음 저항선까지 여유
```

요약 문장 예시:

```text
이 종목은 주봉 기준 333 조정 패턴이 감지되었습니다.
최근 고점 이후 세 번의 음봉 조정 집단이 양봉으로 분리되었고,
마지막 양봉이 2026-04-13 주봉에서 출현했습니다.
현재가는 장기 지지선 13,800원 위에서 회복 중이며,
다음 저항선 18,800원까지 약 9.3% 상승 여유가 있습니다.
따라서 바종발식 기준으로는 조정 마무리 후 반등 시도 구간으로 분류됩니다.
```

### 25.12 매수·손절·매도 가격 산출 방식

333 전략이 감지된 종목의 가격 산출은 다음을 따른다.

매수 후보가:

```text
공격형 매수 후보가:
- 마지막 양봉의 종가 부근
- 또는 마지막 양봉의 중간값 이상에서 지지 확인

보수형 매수 후보가:
- 마지막 양봉 이후 직전 단기 저항선 돌파
- 돌파 후 재지지 확인 가격
```

손절가:

```text
1차 손절가:
- 마지막 양봉의 저가 이탈

2차 손절가:
- 3번째 음봉 집단의 최저가 이탈

보수적 손절가:
- 333 패턴 전체 최저가 이탈
```

매도 후보가:

```text
1차 매도:
- 가장 가까운 단기 저항선
- 또는 라운드 넘버

2차 매도:
- 패턴 중간부 매물대
- 또는 직전 고점

3차 매도:
- 패턴 시작부 고점
- 또는 장기 저항선
```

### 25.13 333 전략과 3분할 매매의 구분

333 전략은 “3분할 매수/3분할 매도”와 다르다.

```text
333 전략:
- 캔들 패턴 분석
- 고점 이후 3개의 음봉 조정 집단을 보는 방식

3분할 매수/매도:
- 자금 관리 방식
- 매수와 매도를 3번에 나눠 실행하는 방식
```

시스템에서는 두 개를 분리해서 표시한다.

```text
333 패턴 감지 여부: YES/NO
3분할 매수계획 제공 여부: YES/NO
3분할 매도계획 제공 여부: YES/NO
```

### 25.14 구현 파일과 함수

구현 파일:

```text
src/bajongbal/strategy/pattern_333.py
```

주요 함수:

```text
classify_candle_color()
compress_candle_groups()
detect_333_pattern()
score_333_pattern()
summarize_333_pattern()
build_333_trade_plan()
```

역할:

```text
classify_candle_color:
- open, close 기준으로 U/D/N 분류

compress_candle_groups:
- 연속된 같은 색 캔들을 그룹으로 압축

detect_333_pattern:
- U-D-U-D-U-D-U 구조 탐지

score_333_pattern:
- 구조 명확성, 조정폭, 마지막 양봉, 거래량, 상승 여유를 점수화

summarize_333_pattern:
- UI에 표시할 한국어 요약 문장 생성

build_333_trade_plan:
- 매수 후보가, 손절가, 1차/2차/3차 매도 후보가 산출
```

### 25.15 저장 구조

`pattern_333` 테이블에 아래 정보를 저장한다.

```text
id
code
name
timeframe
detected_at
pattern_start_date
pattern_end_date
pattern_sequence
pattern_grade
down_group_1_json
down_group_2_json
down_group_3_json
last_up_group_json
pattern_high
pattern_low
correction_pct
last_up_volume_ratio
next_resistance
upside_room_pct
stop_price
score_333
reason_json
```

`signals` 테이블에는 아래 정보를 추가하거나 `reason_json` 안에 포함한다.

```text
has_333_pattern
pattern_333_timeframe
pattern_333_grade
score_333
pattern_333_summary
```

### 25.16 테스트 요구사항

테스트 파일:

```text
tests/test_pattern_333.py
```

필수 테스트:

```text
U-D-U-D-U-D-U 구조를 감지하는지
첫 그룹이 D면 감지하지 않는지
마지막 그룹이 D면 감지하지 않는지
음봉 그룹이 2개면 감지하지 않는지
음봉 그룹이 4개면 감지하지 않는지
도지 캔들을 안전하게 처리하는지
고점 이후 조정 조건이 없으면 감지하지 않는지
마지막 양봉 거래량 증가 시 점수가 상승하는지
weak_333과 strong_333을 구분하는지
```

예시 테스트 케이스:

```text
OK:
U U / D D / U / D D D / U U / D / U

OK:
U / D / U / D / U / D / U

FAIL:
D / U / D / U / D / U

FAIL:
U / D / U / D / U / D / D

FAIL:
U / D / U / D / U
```

### 25.17 Codex 구현 지시사항

Codex는 333 전략을 구현할 때 아래 원칙을 따른다.

```text
1. 333 전략은 단독 매수 신호로 사용하지 않는다.
2. 333 전략은 바종발식 급등직전 점수의 보조 패턴 점수로 사용한다.
3. 333 전략과 3분할 매수/매도는 명확히 구분한다.
4. 일봉/주봉/월봉/년봉 중 최소 주봉과 월봉 기준 감지는 구현한다.
5. 구현 시간이 부족하면 주봉 기준을 우선 구현하고, 나머지는 확장 가능한 구조로 둔다.
6. UI에는 333 전략 감지 여부, 분석 봉, 패턴 구조, 등급, 근거 수치를 표시한다.
7. “333 감지됨”만 표시하지 말고 실제 어떤 캔들 구간이 1번/2번/3번 음봉 집단인지 보여준다.
8. 사용자가 차트에서 교차검증할 수 있도록 날짜, 가격, 거래량 비율을 반드시 표시한다.
9. 333 전략의 원문 정의가 완전히 공식화된 것은 아니므로 README에는 “사용자 제공 예시 기반으로 정형화한 규칙”이라고 명시한다.
10. 자동매수·자동매도는 구현하지 않는다.
```

### 25.18 핵심 한 줄

333 전략은 다음 문장을 코드로 구현하는 보조 패턴이다.

```text
고점 이후 하락 조정이 3개의 음봉 집단으로 나뉘어 진행되고,
각 음봉 집단이 양봉으로 분리된 뒤,
마지막 양봉이 출현하면 조정 마무리 후 반등 시도 구간으로 본다.
```


## 26. 핵심 한 줄

이 시스템은 다음 문장을 코드로 구현하는 프로젝트다.

```text
네이버증권으로 하루 1회 테마 분류표를 만들고,
KIS 시세로 장중 테마 강세와 주도주를 계산하며,
DART로 공시 리스크를 걸러내고,
장기 매물대 바로 아래에서 기준가를 반복적으로 두드리고 눌림이 약하며 거래량과 거래대금이 붙기 시작하고, 필요 시 333 조정 패턴까지 감지되는 종목을 웹 대시보드에서 자동으로 찾아낸다.
```
