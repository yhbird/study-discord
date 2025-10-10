import requests
from bs4 import BeautifulSoup

from exceptions.client_exceptions import *

def exchange_krw_rate(from_currency: str) -> float:
    """
    환율을 검색해서 (KRW)로 변환하는데 도움을 줍니다.

    Args:
        from_currency (str): 변환할 통화의 코드 (예: 'USD', 'EUR')
        amount (float): 변환할 금액

    Returns:
        float: 변환된 금액 (원화)

    Raises:
        Exception: 환율 정보를 가져오는 중 오류가 발생한 경우
    """
    from_currency = from_currency.strip().upper()
    if from_currency == 'KRW':
        return 1
    else:
        url = f"https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_{from_currency}KRW"
        response = requests.get(url)
        html = BeautifulSoup(response.text, 'html.parser')

    if response.status_code == 200:
        # 환율 정보를 가져오는 데 성공한 경우
        options = html.select("select.selectbox-source option")
        for opt in options:
            if from_currency in opt.text:
                rate: float = float(opt.get("value"))
                return rate
        raise YFI_NO_RATE_WARNING(f"환율 정보를 찾을 수 없어양: {from_currency}")
    else:
        # 환율 정보를 가져오는 데 실패한 경우
        raise YFI_STOCK_FETCH_RATE(f"HTTP {response.status_code}: {response.reason}")