from typing import Dict


def get_cash_balance(balance_data: Dict) -> int:
    """
    잔고 조회 응답에서 예수금을 추출한다.
    """

    output2 = balance_data.get("output2", [])

    if not output2:
        return 0

    return int(output2[0].get("dnca_tot_amt", 0))


def get_holding_quantity(balance_data: Dict, stock_code: str) -> int:
    """
    잔고 조회 응답에서 특정 종목의 보유 수량을 확인한다.
    보유하지 않은 종목이면 0을 반환한다.
    """

    holdings = balance_data.get("output1", [])

    for item in holdings:
        if item.get("pdno") == stock_code:
            return int(item.get("hldg_qty", 0))

    return 0


def check_order_permission(
    signal: str,
    stock_code: str,
    current_price: int,
    quantity: int,
    balance_data: Dict,
    max_order_amount: int = 500000,
) -> Dict:
    """
    전략 신호를 실제 주문으로 연결해도 되는지 검사한다.

    BUY 조건:
    - 매매 신호가 BUY여야 한다.
    - 주문 금액이 최대 주문 금액보다 작거나 같아야 한다.
    - 예수금이 주문 금액보다 충분해야 한다.
    - 이미 해당 종목을 보유하고 있으면 중복 매수를 막는다.

    SELL 조건:
    - 매매 신호가 SELL이어야 한다.
    - 해당 종목을 보유하고 있어야 한다.

    HOLD 조건:
    - 주문을 실행하지 않는다.
    """

    order_amount = current_price * quantity
    cash_balance = get_cash_balance(balance_data)
    holding_quantity = get_holding_quantity(balance_data, stock_code)

    if signal == "HOLD":
        return {
            "allowed": False,
            "action": "HOLD",
            "reason": "전략 신호가 HOLD이므로 주문을 실행하지 않습니다.",
            "order_amount": order_amount,
            "cash_balance": cash_balance,
            "holding_quantity": holding_quantity,
        }

    if signal == "BUY":
        if order_amount > max_order_amount:
            return {
                "allowed": False,
                "action": "BUY",
                "reason": "주문 금액이 최대 주문 가능 금액을 초과했습니다.",
                "order_amount": order_amount,
                "cash_balance": cash_balance,
                "holding_quantity": holding_quantity,
            }

        if cash_balance < order_amount:
            return {
                "allowed": False,
                "action": "BUY",
                "reason": "예수금이 부족하여 매수 주문을 실행할 수 없습니다.",
                "order_amount": order_amount,
                "cash_balance": cash_balance,
                "holding_quantity": holding_quantity,
            }

        if holding_quantity > 0:
            return {
                "allowed": False,
                "action": "BUY",
                "reason": "이미 해당 종목을 보유하고 있어 중복 매수를 방지합니다.",
                "order_amount": order_amount,
                "cash_balance": cash_balance,
                "holding_quantity": holding_quantity,
            }

        return {
            "allowed": True,
            "action": "BUY",
            "reason": "위험관리 조건을 모두 통과하여 매수 주문이 가능합니다.",
            "order_amount": order_amount,
            "cash_balance": cash_balance,
            "holding_quantity": holding_quantity,
        }

    if signal == "SELL":
        if holding_quantity <= 0:
            return {
                "allowed": False,
                "action": "SELL",
                "reason": "보유 수량이 없어 매도 주문을 실행할 수 없습니다.",
                "order_amount": order_amount,
                "cash_balance": cash_balance,
                "holding_quantity": holding_quantity,
            }

        return {
            "allowed": True,
            "action": "SELL",
            "reason": "보유 수량이 확인되어 매도 주문이 가능합니다.",
            "order_amount": order_amount,
            "cash_balance": cash_balance,
            "holding_quantity": holding_quantity,
        }

    return {
        "allowed": False,
        "action": signal,
        "reason": "알 수 없는 매매 신호입니다.",
        "order_amount": order_amount,
        "cash_balance": cash_balance,
        "holding_quantity": holding_quantity,
    }