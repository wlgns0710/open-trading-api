import time
from datetime import datetime

from kis_api import KISApiClient
from strategy import analyze_moving_average_strategy
from risk_manager import check_order_permission
from logger import save_trading_log, print_log_saved_message


DRY_RUN = True

# None: 실제 전략 결과 사용
# "BUY": 매수 흐름 테스트
# "SELL": 매도 흐름 테스트
# "HOLD": 주문 차단 흐름 테스트

# ---------------------------------------------------------
# Loop Settings
# ---------------------------------------------------------
# True이면 main.py의 이동평균선 자동매매 흐름을 반복 실행한다.
LOOP_MODE = True

# 몇 번 반복할지 설정한다.
MAX_CYCLES = 10

# 반복 사이 대기 시간
LOOP_INTERVAL_SECONDS = 60

FORCE_TEST_SIGNAL = None

def print_current_price(price_data: dict) -> None:
    output = price_data["output"]

    stock_code = output.get("stck_shrn_iscd")
    current_price = int(output.get("stck_prpr", 0))
    price_change = int(output.get("prdy_vrss", 0))
    change_rate = output.get("prdy_ctrt")

    print("\n[현재가 조회 결과]")
    print(f"종목코드: {stock_code}")
    print(f"현재가: {current_price:,}원")
    print(f"전일 대비: {price_change:,}원")
    print(f"등락률: {change_rate}%")


def print_balance(balance_data: dict) -> None:
    holdings = balance_data.get("output1", [])
    summary = balance_data.get("output2", [{}])[0]

    cash = int(summary.get("dnca_tot_amt", 0))
    stock_value = int(summary.get("scts_evlu_amt", 0))
    total_value = int(summary.get("tot_evlu_amt", 0))
    net_asset = int(summary.get("nass_amt", 0))

    print("\n[계좌 잔고 조회 결과]")
    print(f"예수금: {cash:,}원")
    print(f"주식 평가금액: {stock_value:,}원")
    print(f"총 평가금액: {total_value:,}원")
    print(f"순자산: {net_asset:,}원")

    if not holdings:
        print("보유 종목: 없음")
    else:
        print("\n[보유 종목]")
        for item in holdings:
            stock_name = item.get("prdt_name")
            stock_code = item.get("pdno")
            quantity = item.get("hldg_qty")
            eval_amount = item.get("evlu_amt")
            profit_loss = item.get("evlu_pfls_amt")

            print(
                f"- {stock_name}({stock_code}) | "
                f"수량: {quantity} | "
                f"평가금액: {eval_amount} | "
                f"평가손익: {profit_loss}"
            )

def print_strategy_result(strategy_result: dict) -> None:
    print("\n[이동평균선 전략 분석 결과]")
    print(f"기준일자: {strategy_result.get('date')}")
    print(f"종가: {strategy_result.get('close'):,}원")
    print(f"5일 이동평균선: {strategy_result.get('ma_short'):,}원")
    print(f"20일 이동평균선: {strategy_result.get('ma_long'):,}원")
    print(f"매매 신호: {strategy_result.get('signal')}")
    print(f"판단 이유: {strategy_result.get('reason')}")

def print_risk_result(risk_result: dict) -> None:
    print("\n[위험관리 검사 결과]")
    print(f"주문 허용 여부: {risk_result.get('allowed')}")
    print(f"요청 동작: {risk_result.get('action')}")
    print(f"판단 이유: {risk_result.get('reason')}")
    print(f"예상 주문 금액: {risk_result.get('order_amount'):,}원")
    print(f"현재 예수금: {risk_result.get('cash_balance'):,}원")
    print(f"현재 보유 수량: {risk_result.get('holding_quantity')}")

def print_order_result(order_result: dict) -> None:
    print("\n[주문 처리 결과]")
    print(f"실제 주문 실행 여부: {order_result.get('executed')}")
    print(f"주문 방식: {order_result.get('mode')}")
    print(f"주문 구분: {order_result.get('side')}")
    print(f"종목코드: {order_result.get('stock_code')}")
    print(f"주문 수량: {order_result.get('quantity')}")
    print(f"주문 가격: {order_result.get('price')}")
    print(f"처리 결과: {order_result.get('message')}")

    if order_result.get("api_response"):
        print(f"API 응답: {order_result.get('api_response')}")

def main() -> None:
    print("KIS 자동매매 시스템 1차 연결 테스트를 시작합니다.")

    client = KISApiClient()

    print("\n[1] OAuth access token 발급 중...")
    client.get_access_token()
    print("Access token 발급 성공")
    print("보안을 위해 token 값은 출력하지 않습니다.")

    print("\n[2] 현재가 조회 중...")
    price_data = client.get_current_price("005930")
    print_current_price(price_data)

    print("\nAPI 요청 제한을 피하기 위해 잠시 대기합니다...")
    time.sleep(1.5)

    print("\n[3] 계좌 잔고 조회 중...")
    balance_data = client.get_balance()
    print_balance(balance_data)

    print("\nAPI 요청 제한을 피하기 위해 잠시 대기합니다...")
    time.sleep(1.5)

    print("\n[4] 일봉 데이터 조회 중...")
    daily_price_data = client.get_daily_prices("005930")
    print("일봉 데이터 조회 성공")

    print("\n[5] 이동평균선 전략 분석 중...")
    strategy_result = analyze_moving_average_strategy(daily_price_data)
    print_strategy_result(strategy_result)

    if FORCE_TEST_SIGNAL is not None:
        print("\n[TEST MODE] Strategy signal is manually overridden.")
        print(f"original signal: {strategy_result['signal']}")
        print(f"forced signal: {FORCE_TEST_SIGNAL}")

        strategy_result["signal"] = FORCE_TEST_SIGNAL
        strategy_result["reason"] = (
            f"테스트를 위해 {FORCE_TEST_SIGNAL} 신호를 강제로 적용했습니다. "
            "실제 전략 신호가 아니라 테스트용 신호입니다."
        )

    print("\n[6] 위험관리 조건 검사 중...")
    current_price = int(price_data["output"].get("stck_prpr", 0))
    risk_result = check_order_permission(
        signal=strategy_result.get("signal"),
        stock_code="005930",
        current_price=current_price,
        quantity=1,
        balance_data=balance_data,
        max_order_amount=500000,
    )
    print_risk_result(risk_result)

    print("\n[7] 주문 처리 단계 진입...")
    if not risk_result.get("allowed"):
        order_result = {
            "executed": False,
            "mode": "BLOCKED_BY_RISK_MANAGER",
            "side": risk_result.get("action"),
            "stock_code": "005930",
            "quantity": 1,
            "price": current_price,
            "message": risk_result.get("reason"),
            "api_response": None,
        }
    elif DRY_RUN:
        order_result = {
            "executed": False,
            "mode": "DRY_RUN",
            "side": risk_result.get("action"),
            "stock_code": "005930",
            "quantity": 1,
            "price": current_price,
            "message": "dry_run 모드이므로 실제 주문은 전송하지 않았습니다.",
            "api_response": None,
        }
    else:
        try:
            print("\nAPI 요청 제한을 피하기 위해 주문 전 잠시 대기합니다...")
            time.sleep(2.0)

            api_response = client.place_order(
                stock_code="005930",
                side=risk_result.get("action"),
                quantity=1,
                price=0,
                order_division="01",
            )

            order_result = {
                "executed": True,
                "mode": "LIVE_VIRTUAL_ORDER",
                "side": risk_result.get("action"),
                "stock_code": "005930",
                "quantity": 1,
                "price": 0,
                "message": "모의투자 주문 요청을 전송했습니다.",
                "api_response": api_response,
            }

        except RuntimeError as error:
            order_result = {
                "executed": False,
                "mode": "ORDER_REQUEST_FAILED",
                "side": risk_result.get("action"),
                "stock_code": "005930",
                "quantity": 1,
                "price": 0,
                "message": str(error),
                "api_response": None,
            }

    print_order_result(order_result)

    print("\n[8] 거래 기록 저장 중...")
    save_trading_log(
        strategy_result=strategy_result,
        risk_result=risk_result,
        order_result=order_result,
    )
    print_log_saved_message()

    print("\n5차 거래 기록 저장 테스트 완료")


def run_loop() -> None:
    print("KIS 이동평균선 자동매매 loop 실행을 시작합니다.")
    print(f"LOOP_MODE: {LOOP_MODE}")
    print(f"DRY_RUN: {DRY_RUN}")
    print(f"FORCE_TEST_SIGNAL: {FORCE_TEST_SIGNAL}")
    print(f"MAX_CYCLES: {MAX_CYCLES}")
    print(f"LOOP_INTERVAL_SECONDS: {LOOP_INTERVAL_SECONDS}")

    for cycle in range(1, MAX_CYCLES + 1):
        print("\n" + "=" * 60)
        print(f"[Loop Cycle {cycle}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        try:
            main()

        except KeyboardInterrupt:
            print("\n사용자가 프로그램을 중단했습니다.")
            break

        except Exception as e:
            print("\n자동매매 실행 중 오류가 발생했습니다.")
            print(f"error: {e}")
            print("오류가 발생했지만 loop는 중단하지 않고 다음 cycle로 넘어갑니다.")

        if cycle < MAX_CYCLES:
            print(f"\n다음 cycle까지 {LOOP_INTERVAL_SECONDS}초 대기합니다.")
            time.sleep(LOOP_INTERVAL_SECONDS)

    print("\nKIS 이동평균선 자동매매 loop 실행이 종료되었습니다.")


if __name__ == "__main__":
    if LOOP_MODE:
        run_loop()
    else:
        main()