import time
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
from typing import Any, Dict, List

from kis_api import KISApiClient


# ---------------------------------------------------------
# Realtime auto trading settings
# ---------------------------------------------------------
STOCK_CODE = "005930"
ORDER_QUANTITY = 1

# 실제 주문 전송 여부
# True  -> 실제 주문 API 전송 안 함
# False -> 실제 모의투자 주문 API 전송
DRY_RUN = False

# 반복 간격
POLL_INTERVAL_SECONDS = 60

# 최대 반복 횟수
MAX_CYCLES = 10

# BUY와 SELL이 한 번씩 제출되면 종료할지 여부
STOP_AFTER_ROUND_TRIP = True

# 장 시간 확인
USE_MARKET_TIME_CHECK = True
MARKET_START = dt_time(9, 0)
MARKET_END = dt_time(15, 30)

KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    return datetime.now(KST)


def is_market_time() -> bool:
    current_time = now_kst().time()
    return MARKET_START <= current_time <= MARKET_END


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError):
        return default

def get_tick_size(price: int) -> int:
    """
    국내주식 가격대별 호가단위를 반환한다.
    삼성전자처럼 20만원 이상 50만원 미만 종목은 500원 단위이다.
    """

    if price < 2000:
        return 1
    if price < 5000:
        return 5
    if price < 20000:
        return 10
    if price < 50000:
        return 50
    if price < 200000:
        return 100
    if price < 500000:
        return 500

    return 1000


def adjust_price_to_tick(price: int, side: str) -> int:
    """
    주문 가격을 호가단위에 맞게 조정한다.

    BUY:
        너무 높은 가격으로 주문하지 않도록 아래 호가로 내림

    SELL:
        매도 주문이 호가단위 오류 없이 들어가도록 위 호가로 올림
    """

    tick_size = get_tick_size(price)

    if side == "BUY":
        return (price // tick_size) * tick_size

    if side == "SELL":
        return ((price + tick_size - 1) // tick_size) * tick_size

    return price

def get_current_price_value(price_data: Dict[str, Any]) -> int:
    output = price_data.get("output", {})
    return safe_int(output.get("stck_prpr"))


def get_available_cash(balance_data: Dict[str, Any]) -> int:
    output2 = balance_data.get("output2", [])

    if not output2:
        return 0

    summary = output2[0]

    # dnca_tot_amt: 예수금
    return safe_int(summary.get("dnca_tot_amt"))


def get_holding_quantity(balance_data: Dict[str, Any], stock_code: str) -> int:
    holdings: List[Dict[str, Any]] = balance_data.get("output1", [])

    for item in holdings:
        item_code = item.get("pdno") or item.get("PDNO")

        if item_code == stock_code:
            return safe_int(item.get("hldg_qty"))

    return 0


def print_balance_snapshot(balance_data: Dict[str, Any], stock_code: str) -> None:
    available_cash = get_available_cash(balance_data)
    holding_quantity = get_holding_quantity(balance_data, stock_code)

    print("\n[계좌 스냅샷]")
    print(f"예수금: {available_cash:,}원")
    print(f"{stock_code} 보유 수량: {holding_quantity}주")


def submit_order(
    client: KISApiClient,
    side: str,
    stock_code: str,
    quantity: int,
    price: int,
) -> Dict[str, Any]:
    print(f"\n[{side} 주문 요청]")
    print(f"종목코드: {stock_code}")
    print(f"주문수량: {quantity}")
    print(f"주문가격: {price}")

    if DRY_RUN:
        print("DRY_RUN 모드이므로 실제 주문은 전송하지 않습니다.")

        return {
            "success": True,
            "dry_run": True,
            "side": side,
            "stock_code": stock_code,
            "quantity": quantity,
            "price": price,
            "message": "DRY_RUN order simulated.",
        }

    # 지정가 주문: order_division="00"
    # 시장가 주문: order_division="01", price=0
    result = client.place_order(
        stock_code=stock_code,
        side=side,
        quantity=quantity,
        price=price,
        order_division="00",
    )

    print(f"{side} 주문 요청 성공")
    print(result)

    return {
        "success": True,
        "dry_run": False,
        "side": side,
        "stock_code": stock_code,
        "quantity": quantity,
        "price": price,
        "response": result,
    }


def main() -> None:
    print("KIS 실시간 자동매매 trader를 시작합니다.")
    print(f"대상 종목: {STOCK_CODE}")
    print(f"주문 수량: {ORDER_QUANTITY}")
    print(f"DRY_RUN: {DRY_RUN}")
    print(f"반복 간격: {POLL_INTERVAL_SECONDS}초")
    print(f"최대 반복 횟수: {MAX_CYCLES}")

    if USE_MARKET_TIME_CHECK and not is_market_time():
        print("\n현재는 장 운영 시간이 아닙니다.")
        print("실제 주문 테스트는 장 운영 시간에 실행하는 것이 안전합니다.")
        print("프로그램을 종료합니다.")
        return

    client = KISApiClient()

    print("\n[1] OAuth access token 발급 중...")
    client.get_access_token()
    print("Access token 발급 성공")
    print("보안을 위해 token 값은 출력하지 않습니다.")

    buy_submitted = False
    sell_submitted = False

    for cycle in range(1, MAX_CYCLES + 1):
        print("\n" + "=" * 60)
        print(f"[Cycle {cycle}] {now_kst().strftime('%Y-%m-%d %H:%M:%S')} KST")
        print("=" * 60)

        if USE_MARKET_TIME_CHECK and not is_market_time():
            print("장 운영 시간이 종료되어 자동매매를 중단합니다.")
            break

        # ---------------------------------------------------------
        # 1. Current price
        # ---------------------------------------------------------
        print("\n[현재가 조회 중...]")
        price_data = client.get_current_price(STOCK_CODE)
        current_price = get_current_price_value(price_data)

        print(f"현재가: {current_price:,}원")

        time.sleep(1.5)

        # ---------------------------------------------------------
        # 2. Balance before order
        # ---------------------------------------------------------
        print("\n[주문 전 계좌 조회 중...]")
        balance_before = client.get_balance()
        print_balance_snapshot(balance_before, STOCK_CODE)

        available_cash = get_available_cash(balance_before)
        holding_quantity = get_holding_quantity(balance_before, STOCK_CODE)

        time.sleep(1.5)

        # ---------------------------------------------------------
        # 3. Trading decision
        # ---------------------------------------------------------
        if holding_quantity <= 0:
            side = "BUY"
            order_price = adjust_price_to_tick(current_price, "BUY")

            print("\n[자동 판단]")
            print("보유 수량이 없으므로 BUY 주문을 시도합니다.")

            if available_cash < current_price * ORDER_QUANTITY:
                print("예수금이 부족하여 BUY 주문을 실행하지 않습니다.")
                continue

        else:
            side = "SELL"
            order_price = adjust_price_to_tick(current_price, "SELL")

            print("\n[자동 판단]")
            print("보유 수량이 있으므로 SELL 주문을 시도합니다.")

            if holding_quantity < ORDER_QUANTITY:
                print("보유 수량이 주문 수량보다 적어 SELL 주문을 실행하지 않습니다.")
                continue

        # ---------------------------------------------------------
        # 4. Submit order
        # ---------------------------------------------------------
        try:
            order_result = submit_order(
                client=client,
                side=side,
                stock_code=STOCK_CODE,
                quantity=ORDER_QUANTITY,
                price=order_price,
            )

            if side == "BUY" and order_result.get("success"):
                buy_submitted = True

            if side == "SELL" and order_result.get("success"):
                sell_submitted = True

        except Exception as e:
            print("\n주문 요청 중 오류가 발생했습니다.")
            print(f"error: {e}")

        time.sleep(2.0)

        # ---------------------------------------------------------
        # 5. Balance after order
        # ---------------------------------------------------------
        print("\n[주문 후 계좌 재조회 중...]")
        try:
            balance_after = client.get_balance()
            print_balance_snapshot(balance_after, STOCK_CODE)
        except Exception as e:
            print("주문 후 계좌 재조회 실패")
            print(f"error: {e}")

        # ---------------------------------------------------------
        # 6. Stop condition
        # ---------------------------------------------------------
        if STOP_AFTER_ROUND_TRIP and buy_submitted and sell_submitted:
            print("\nBUY와 SELL 주문 요청이 모두 한 번씩 제출되었습니다.")
            print("안전을 위해 자동매매를 종료합니다.")
            break

        print(f"\n다음 cycle까지 {POLL_INTERVAL_SECONDS}초 대기합니다.")
        time.sleep(POLL_INTERVAL_SECONDS)

    print("\nKIS 실시간 자동매매 trader가 종료되었습니다.")


if __name__ == "__main__":
    main()