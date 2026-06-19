from typing import Dict, List

import pandas as pd


def extract_close_prices(daily_price_data: Dict) -> pd.DataFrame:
    """
    한국투자증권 일봉 조회 API 응답에서 날짜와 종가만 추출한다.

    KIS API의 일봉 데이터는 보통 최신 날짜가 먼저 오는 역순 구조이므로,
    이동평균선을 계산하기 전에 날짜 기준 오름차순으로 정렬한다.
    """

    output = daily_price_data.get("output", [])

    if not output:
        raise ValueError("Daily price data is empty.")

    rows: List[Dict] = []

    for item in output:
        date = item.get("stck_bsop_date")
        close_price = item.get("stck_clpr")

        if date is None or close_price is None:
            continue

        rows.append(
            {
                "date": date,
                "close": int(close_price),
            }
        )

    df = pd.DataFrame(rows)

    if df.empty:
        raise ValueError("No valid close price data found.")

    df = df.sort_values("date").reset_index(drop=True)

    return df


def add_moving_averages(
    df: pd.DataFrame,
    short_window: int = 5,
    long_window: int = 20,
) -> pd.DataFrame:
    """
    종가 데이터에 5일 이동평균선과 20일 이동평균선을 추가한다.
    """

    if len(df) < long_window:
        raise ValueError(
            f"Not enough data to calculate {long_window}-day moving average."
        )

    df = df.copy()
    df["ma_short"] = df["close"].rolling(window=short_window).mean()
    df["ma_long"] = df["close"].rolling(window=long_window).mean()

    return df


def generate_signal(df: pd.DataFrame) -> Dict:
    """
    이동평균선 교차 여부를 이용해 BUY / SELL / HOLD 신호를 생성한다.

    BUY 조건:
    이전 날에는 5일선이 20일선보다 아래 또는 같았고,
    현재는 5일선이 20일선보다 위에 있는 경우

    SELL 조건:
    이전 날에는 5일선이 20일선보다 위 또는 같았고,
    현재는 5일선이 20일선보다 아래에 있는 경우

    HOLD 조건:
    뚜렷한 교차 신호가 없는 경우
    """

    valid_df = df.dropna().reset_index(drop=True)

    if len(valid_df) < 2:
        return {
            "signal": "HOLD",
            "reason": "이동평균선 판단에 필요한 데이터가 부족합니다.",
        }

    previous = valid_df.iloc[-2]
    current = valid_df.iloc[-1]

    prev_short = previous["ma_short"]
    prev_long = previous["ma_long"]
    curr_short = current["ma_short"]
    curr_long = current["ma_long"]

    if prev_short <= prev_long and curr_short > curr_long:
        signal = "BUY"
        reason = "5일 이동평균선이 20일 이동평균선을 아래에서 위로 돌파했습니다."
    elif prev_short >= prev_long and curr_short < curr_long:
        signal = "SELL"
        reason = "5일 이동평균선이 20일 이동평균선을 위에서 아래로 돌파했습니다."
    else:
        signal = "HOLD"
        reason = "이동평균선 교차 신호가 발생하지 않았습니다."

    return {
        "signal": signal,
        "reason": reason,
        "date": str(current["date"]),
        "close": int(current["close"]),
        "ma_short": round(float(curr_short), 2),
        "ma_long": round(float(curr_long), 2),
    }


def analyze_moving_average_strategy(daily_price_data: Dict) -> Dict:
    """
    일봉 API 응답을 받아 이동평균선 전략 결과를 반환한다.

    전체 흐름:
    1. 일봉 응답에서 종가 추출
    2. 5일·20일 이동평균선 계산
    3. BUY / SELL / HOLD 신호 생성
    """

    df = extract_close_prices(daily_price_data)
    df = add_moving_averages(df)
    signal = generate_signal(df)

    return signal