import os
from typing import Any, Dict

import requests
from dotenv import load_dotenv


class KISApiClient:
    def __init__(self) -> None:
        load_dotenv()

        self.base_url = os.getenv("KIS_BASE_URL")
        self.app_key = os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_APP_SECRET")
        self.account_no = os.getenv("KIS_ACCOUNT_NO")
        self.account_product_code = os.getenv("KIS_ACCOUNT_PRODUCT_CODE", "01")

        self.access_token: str | None = None

        self._validate_env()

    def _validate_env(self) -> None:
        required_values = {
            "KIS_BASE_URL": self.base_url,
            "KIS_APP_KEY": self.app_key,
            "KIS_APP_SECRET": self.app_secret,
            "KIS_ACCOUNT_NO": self.account_no,
            "KIS_ACCOUNT_PRODUCT_CODE": self.account_product_code,
        }

        missing = [key for key, value in required_values.items() if not value]

        if missing:
            raise ValueError(
                "Missing environment variables: "
                + ", ".join(missing)
                + "\nPlease check your .env file."
            )

    def get_access_token(self) -> str:
        url = f"{self.base_url}/oauth2/tokenP"

        headers = {
            "content-type": "application/json",
        }

        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        response = requests.post(url, headers=headers, json=body, timeout=10)
        data = response.json()

        if response.status_code != 200 or "access_token" not in data:
            raise RuntimeError(f"Failed to issue access token: {data}")

        self.access_token = data["access_token"]
        return self.access_token

    def _auth_headers(self, tr_id: str) -> Dict[str, str]:
        if not self.access_token:
            self.get_access_token()

        return {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": tr_id,
            "custtype": "P",
        }

    def get_current_price(self, stock_code: str) -> Dict[str, Any]:
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"

        headers = self._auth_headers("FHKST01010100")

        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code,
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(f"Current price inquiry failed: {data}")

        return data

    def get_balance(self) -> Dict[str, Any]:
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"

        headers = self._auth_headers("VTTC8434R")

        params = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_product_code,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(f"Balance inquiry failed: {data}")

        return data

    def get_daily_prices(self, stock_code: str) -> Dict[str, Any]:
        """
        Get recent daily price data for a domestic stock.

        This function uses the Korea Investment daily price API.
        It returns recent daily stock prices, which are later used
        to calculate moving averages.
        """

        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"

        headers = self._auth_headers("FHKST01010400")

        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": stock_code,
            "fid_period_div_code": "D",
            "fid_org_adj_prc": "1",
        }

        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(f"Daily price inquiry failed: {data}")

        return data
        
    def create_hashkey(self, body: Dict[str, Any]) -> str:
        """
        주문 요청 body를 바탕으로 hashkey를 생성한다.

        한국투자증권 Open API의 POST 주문 요청에서는
        request body에 대한 hashkey가 필요할 수 있으므로,
        주문 실행 전에 hashkey를 먼저 생성한다.
        """

        url = f"{self.base_url}/uapi/hashkey"

        headers = {
            "content-type": "application/json",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
        }

        response = requests.post(url, headers=headers, json=body, timeout=10)
        data = response.json()

        if "HASH" not in data:
            raise RuntimeError(f"Hashkey creation failed: {data}")

        return data["HASH"]

    def place_order(
        self,
        stock_code: str,
        side: str,
        quantity: int,
        price: int = 0,
        order_division: str = "01",
    ) -> Dict[str, Any]:
        """
        모의투자 주식 현금 주문을 실행한다.

        side:
            BUY  -> 매수
            SELL -> 매도

        order_division:
            00 -> 지정가
            01 -> 시장가

        시장가 주문의 경우 price는 0으로 입력한다.
        """

        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"

        if side == "BUY":
            tr_id = "VTTC0802U"
        elif side == "SELL":
            tr_id = "VTTC0801U"
        else:
            raise ValueError("side must be BUY or SELL.")

        body = {
            "CANO": self.account_no,
            "ACNT_PRDT_CD": self.account_product_code,
            "PDNO": stock_code,
            "ORD_DVSN": order_division,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price),
        }

        hashkey = self.create_hashkey(body)

        headers = self._auth_headers(tr_id)
        headers["hashkey"] = hashkey

        response = requests.post(url, headers=headers, json=body, timeout=10)
        data = response.json()

        if data.get("rt_cd") != "0":
            raise RuntimeError(f"Order request failed: {data}")

        return data