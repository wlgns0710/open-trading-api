import csv
import os
from datetime import datetime
from typing import Dict


def save_trading_log(
    strategy_result: Dict,
    risk_result: Dict,
    order_result: Dict,
    log_path: str = "logs/trading_log.csv",
) -> None:
    """
    자동매매 실행 결과를 CSV 파일로 저장한다.

    저장 내용:
    - 실행 시각
    - 전략 신호
    - 위험관리 결과
    - 주문 처리 결과
    - 주문 대상 종목
    - 주문 수량과 가격
    """

    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    file_exists = os.path.exists(log_path)

    row = {
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "strategy_date": strategy_result.get("date"),
        "stock_code": order_result.get("stock_code"),
        "close_price": strategy_result.get("close"),
        "ma_short": strategy_result.get("ma_short"),
        "ma_long": strategy_result.get("ma_long"),
        "strategy_signal": strategy_result.get("signal"),
        "strategy_reason": strategy_result.get("reason"),
        "risk_allowed": risk_result.get("allowed"),
        "risk_reason": risk_result.get("reason"),
        "order_executed": order_result.get("executed"),
        "order_mode": order_result.get("mode"),
        "order_side": order_result.get("side"),
        "order_quantity": order_result.get("quantity"),
        "order_price": order_result.get("price"),
        "order_message": order_result.get("message"),
    }

    with open(log_path, mode="a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=row.keys())

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


def print_log_saved_message(log_path: str = "logs/trading_log.csv") -> None:
    """
    log 저장 완료 메시지를 출력한다.
    """

    print("\n[거래 기록 저장 결과]")
    print(f"거래 기록 저장 파일: {log_path}")
    print("자동매매 실행 결과가 CSV 파일에 저장되었습니다.")