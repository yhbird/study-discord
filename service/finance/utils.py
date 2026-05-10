import asyncio
import re

import requests
import pandas as pd

from bs4 import BeautifulSoup
from yfinance import Ticker

from config import STK_DATA_API_KEY, STK_API_HOME
from service.finance.consts import FinanceConsts, FinanceCurrency
from service.finance.exceptions import *
from typing import Dict, List, Literal


class FinanceUtils:
    def __init__(self):
        pass

    @staticmethod
    def exchange_krw_rate(from_currency: str) -> float:
        return exchange_krw_rate(from_currency)

    @staticmethod
    def exchange_currency_rate(from_currency: str, to_currency: str = FinanceConsts.SERVICE_CURRENCY) -> float:
        f_currency = from_currency.strip().upper()
        t_currency = to_currency.strip().upper()
        if f_currency == t_currency:
            return 1.0

        search_currency = Ticker(f"{f_currency}{t_currency}=X")
        currency_rate = search_currency.info.get("regularMarketPrice")
        return float(currency_rate) or 1.0

    @staticmethod
    def parse_currency_code(text: str) -> tuple[float | int, str]:
        """사용자가 입력한 현지 통화단위를 파싱하는 함수

        Args:
            text (str): 디스코드 메세지에 포함된 통화단위

        Returns:
            (amount, code): 파싱 함수가 인식한 최종 통화단위
        """
        input_text = text.strip().upper()

        # 숫자만 남아 있으면 통화 단위를 알 수 없음 -> 에러 발생시키기
        if input_text.isdigit():
            raise YFI_CURRENCY_PARSE_ERROR("숫자만 입력해서 어떤 통화 단위인지 모르겠어양! 아래에 있는 예시처럼 입력해보세양!"
                                           "예시) `븜 환율 100.23달러`, `븜 환율 200JPY`, `븜 환율 300.15 유럽`\n")

        match = re.match(r"^([\d,\.]+)\s*(.+)$", input_text)
        if not match:
            raise YFI_CURRENCY_PARSE_ERROR("통화 단위를 확인 하는 도중에 에러가 발생했어양! 아래에 있는 예시처럼 입력해보세양!"
                                           "예시) `븜 환율 100.23달러`, `븜 환율 200JPY`, `븜 환율 300.15 유럽`\n")

        # 금액 확인
        amount_str = match.group(1).replace(",","")
        try:
            amount = float(amount_str)
            if amount.is_integer():
                amount = int(amount)
        except ValueError:
            raise YFI_CURRENCY_PARSE_ERROR("금액 부분에 이상한 문자가 포함되어서 에러가 발생했어양!")

        # 통화 단위 확인
        currency_str = match.group(2).replace(" ","").strip().upper()
        currency_code = FinanceCurrency.CURRENCY_CODE_MAP.get(currency_str)

        if not currency_code:
            raise YFI_CURRENCY_NOT_SUPPORT("{currency_code}은 아직 지원하지 않는 통화 단위나 없을수도 있어양...")

        return amount, currency_code

class YahooFinance:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self._stock_info: Dict[str, str | float | int | None] = {}
        self._currency_rate: float = 1.0

    async def get_stock_info(self):
        stock = Ticker(self.ticker)
        info = stock.info

        if not info or "regularMarketPrice" not in info:
            raise YFI_NO_TICKER(f"티커 {self.ticker}에 대한 정보를 찾을 수 없어양!")

        symbol: str = info.get("symbol") or self.ticker
        timezone: str | Literal["America/New_York"] = info.get("exchangeTimezoneName") or "America/New_York"
        timezone_short: str | Literal["EST"] = info.get("exchangeTimezoneShortName") or "EST"
        currency: str | Literal["USD"] = info.get("currency") or "USD"
        stock_info: Dict[str, str | float | int | None ] = {
            "short_name": info.get("shortName"),
            "symbol": symbol,
            "exchange": info.get("fullExchangeName"),
            "timezone": timezone,
            "timezone_short": timezone_short,
            "industry": info.get("industry"),
            "sector": info.get("sector"),
            "currency": currency,
            "previous_close": info.get("regularMarketPreviousClose"),
            "today_close": info.get("regularMarketPrice"),
            "high_52w": info.get("fiftyTwoWeekHigh"),
            "high_52w_pct": info.get("fiftyTwoWeekHighChangePercent"),
            "low_52w": info.get("fiftyTwoWeekLow"),
            "low_52w_pct": info.get("fiftyTwoWeekLowChangePercent"),
            "volume_regular": info.get("regularMarketVolume"),
            "volume_average_10d": info.get("averageVolume10days"),
            "market_cap": info.get("marketCap"),
            "psr": info.get("priceToSalesTrailing12Months"),
            "pbr": info.get("priceToBook"),
            "per": info.get("trailingPE"),
            "dividend_yield": info.get("dividendYield"),
            "analyst_score": info.get("recommendationMean"),
            "analyst_score_category": info.get("recommendationKey"),
        }

        self._stock_info = stock_info

    async def get_stock_history(self, input_period: str) -> pd.DataFrame:
        def _load_stock_history() -> pd.DataFrame:
            return Ticker(self.ticker).history(
                period=input_period, interval="1d", auto_adjust=False
            )
        hist: pd.DataFrame = await asyncio.to_thread(_load_stock_history)

        if hist.empty:
            raise YFI_NO_TICKER(f"티커 {self.ticker}에 대한 차트 데이터를 찾을 수 없어양!")
        
        if "Adj Close" in hist.columns:
            price = hist["Adj Close"].copy()
        else:
            price = hist["Close"].copy()

        return_df = pd.DataFrame({
            "Date": hist["Date"] if "Date" in hist.columns else hist.index,
            "Open": hist["Open"],
            "High": hist["High"],
            "Low": hist["Low"],
            "Close": hist["Close"],
            "Volume": hist["Volume"],
            "price": price
        })
        return_df["MA5"] = return_df["price"].rolling(window=5).mean()
        return_df["MA20"] = return_df["price"].rolling(window=20).mean()
        return_df["MA60"] = return_df["price"].rolling(window=60).mean()
        return_df["ChangePct"] = return_df["price"].pct_change() * 100
        if not isinstance(return_df["Date"].iloc[0], pd.Timestamp):
            return_df["Date"] = pd.to_datetime(return_df["Date"])
        return_df.set_index("Date", inplace=True)
        self._stock_hist = return_df.dropna(how="all")


    async def get_currency_rate(self, to_currency: str = FinanceConsts.SERVICE_CURRENCY) -> float:
        from_currency = self._stock_info.get("currency") or "USD"
        if not from_currency or from_currency == to_currency:
            self._currency_rate = 1.0
            return 1.0

        currency = Ticker(f'{from_currency}{to_currency}=X')
        currency_rate: float | None = currency.info.get("regularMarketPrice")

        if currency_rate is None:
            raise YFI_NO_RATE_WARNING("환율 정보를 가져오는데 실패했어양!")

        self._currency_rate = currency_rate
        return currency_rate


    @property
    def stock_info(self):
        return self._stock_info

    @property
    def currency_rate(self):
        return self._currency_rate
    
    @property
    def stock_hist(self):
        return self._stock_hist

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
        raise YFI_STOCK_FETCH_RATE(f"환율 정보 통신 중 에러 발생: HTTP {response.status_code}: {response.reason}")


def get_stock_info(ticker: str) -> Dict[str, str | float | int | None]:
    """주식의 현재시점 정보를 가져오는 함수

    Args:
        ticker (str): 주식 티커 심볼

    Returns:
        Dict[str, str | float | int | None]: 주식 정보 딕셔너리
    """
    stock = Ticker(ticker)
    stock_info = stock.info
    if not stock_info or "regularMarketPrice" not in stock_info:
        raise YFI_NO_TICKER(f"티커 {ticker}에 대한 정보를 찾을 수 없어양!")
    
    short_name: str | None = stock_info.get("shortName", None)
    symbol: str = stock_info.get("symbol", ticker)
    stock_timezone: str = stock_info.get("exchangeTimezoneName", "America/New_York")
    stock_timezone_short: str = stock_info.get("exchangeTimezoneShortName", "EST")
    stock_exchange: str | None = stock_info.get("fullExchangeName", None)
    stock_sector: str | None = stock_info.get("sector", None)
    stock_currency: str | None = stock_info.get("currency", "USD")
    stock_previous_close: float | None = stock_info.get("regularMarketPreviousClose", None)
    stock_today_close: float | None = stock_info.get("regularMarketPrice", None)
    stock_high_52w: float | None = stock_info.get("fiftyTwoWeekHigh", None)
    stock_high_52w_pct: float | None = stock_info.get("fiftyTwoWeekHighChangePercent", None)
    stock_low_52w: float | None = stock_info.get("fiftyTwoWeekLow", None)
    stock_low_52w_pct: float | None = stock_info.get("fiftyTwoWeekLowChangePercent", None)
    stock_volume_regular: int | None = stock_info.get("regularMarketVolume", None)
    stock_volume_average_10d: int | None = stock_info.get("averageVolume10days", None)
    stock_market_cap: int | None = stock_info.get("marketCap", None)
    stock_psr: float | None = stock_info.get("priceToSalesTrailing12Months", None)
    stock_dividend_yield: float | None = stock_info.get("dividendYield", None)
    stock_recommend_mean: float | None = stock_info.get("recommendationMean", None)
    stock_recommend_key: str | None = stock_info.get("recommendationKey", None)

    return_data: Dict[str, str | float | int | None] = {
        "short_name": short_name,
        "symbol": symbol,
        "exchange": stock_exchange,
        "timezone": stock_timezone,
        "timezone_short": stock_timezone_short,
        "sector": stock_sector,
        "currency": stock_currency,
        "previous_close": stock_previous_close,
        "today_close": stock_today_close,
        "high_52w": stock_high_52w,
        "high_52w_pct": stock_high_52w_pct,
        "low_52w": stock_low_52w,
        "low_52w_pct": stock_low_52w_pct,
        "volume_regular": stock_volume_regular,
        "volume_average_10d": stock_volume_average_10d,
        "market_cap": stock_market_cap,
        "psr": stock_psr,
        "dividend_yield": stock_dividend_yield,
        "recommend_mean": stock_recommend_mean,
        "recommend_key": str(stock_recommend_key).replace("_", " ").upper() if stock_recommend_key is not None else None,
    }

    return return_data


async def get_stock_history(ticker: str, period: str) -> pd.DataFrame:
    """주식의 히스토리 데이터를 가져오는 함수

    Args:
        ticker (str): 주식 티커 심볼
        period (str): 기간 (예: '1mo', '3mo', '1y', '5y', 'max')

    Returns:
        pd.DataFrame: 주식 히스토리 데이터
    """
    # 비동기적으로 yfinance의 Ticker.history 메서드를 호출
    def _load() -> pd.DataFrame:
        yf_ticker = Ticker(ticker)
        hist = yf_ticker.history(period=period, interval="1d", auto_adjust=False)
        return hist

    hist = await asyncio.to_thread(_load)

    if hist.empty:
        raise YFI_NO_TICKER(f"티커 {ticker}에 대한 차트 데이터를 찾을 수 없어양!")

    if "Adj Close" in hist.columns:
        price = hist["Adj Close"].copy()
    else:
        price = hist["Close"].copy()

    return_df = pd.DataFrame({
        "Date": hist["Date"] if "Date" in hist.columns else hist.index,
        "Open": hist["Open"],
        "High": hist["High"],
        "Low": hist["Low"],
        "Close": hist["Close"],
        "Volume": hist["Volume"],
        "price": price
    })
    # 이동평균선 MA5, MA20, 등락률 계산
    return_df["MA5"] = return_df["price"].rolling(window=5).mean()
    return_df["MA20"] = return_df["price"].rolling(window=20).mean()
    return_df["ChangePct"] = return_df["price"].pct_change() * 100
    if not isinstance(return_df["Date"].iloc[0], pd.Timestamp):
        return_df["Date"] = pd.to_datetime(return_df["Date"])
    return_df.set_index("Date", inplace=True)
    return return_df.dropna(how="all")


def search_krx_stock_info(search_target: str, serach_method: str) -> Dict[str, str]:
    """한국 주식 코드를 검색하는 함수

    Args:
        search_target (str): 검색할 종목 이름

    Returns:
        Dict[str, str]: 검색된 종목 정보 (종목명, 종목코드, 법인명, 거래소 코드)

    Note:
        KS = KOSPI, KQ = KOSDAQ
    """

    # 종목명, 종목코드로 검색
    if serach_method == "name":
        request_url = f"{STK_API_HOME}/getItemInfo"
        request_params = {
            "ServiceKey" : STK_DATA_API_KEY,
            "likeCorpNm" : search_target,
            "numOfRows" : 10,
        }

    elif serach_method == "code":
        request_url = f"{STK_API_HOME}/getItemInfo"
        request_params = {
            "ServiceKey" : STK_DATA_API_KEY,
            "likeSrtnCd" : search_target,
            "numOfRows" : 10,
        }

    else:
        raise STK_KRX_SEARCH_ERROR("serach_method는 'name' 또는 'code'여야 합니다.")
    
    response = requests.get(request_url, params=request_params)

    if response.status_code == 200:
        # XML Parsing
        xml_data = BeautifulSoup(response.text, 'xml')
        items = xml_data.find_all("item")
        found = None

        for item in items:
            item_name: str = str(item.find("itmsNm").text).strip()
            item_code: str = str(item.find("srtnCd").text).replace("A", "")
            corp_name: str = str(item.find("corpNm").text).strip()
            mrkt_code: str = str(item.find("mrktCtg").text).strip()

            if "홀딩스" in item_name and "홀딩스" not in search_target:
                continue

            found = item
            break

        # 종목명, 종목코드, 법인명, 거래소 조회
        if found is None:
            raise STK_KRX_SEARCH_NO_RESULT(f"검색어 '{search_target}'에 대한 결과가 없습니다.")

        if mrkt_code == "KOSPI":
            market_code = "KS"
        else:
            market_code = "KQ"

        return_data: Dict[str, str] = {
            "item_name": item_name,
            "corp_name": corp_name,
            "item_code": f"{item_code}.{market_code}",
            "market_name": mrkt_code,
            "market_code": market_code
        }
        return return_data
    else:
        raise STK_KRX_SEARCH_ERROR(f"HTTP {response.status_code}: {response.reason}")


def get_krx_stock_info(stock_info: Dict[str, str]) -> Dict[str, str | float | int | None]:
    """한국 주식의 현재시점 정보를 가져오는 함수

    Args:
        stock_info (Dict[str, str]): 한국 주식 종목 정보 딕셔너리

    Returns:
        Dict[str, str | float | int | None]: 주식 정보 딕셔너리
    
    Note:
        기존 get_stock_info 함수를 실행하고 종목명을 한국 주식 종목명으로 대체합니다.
    """
    ticker: str = stock_info["item_code"]
    stock_info_result = get_stock_info(ticker)
    stock_info_result["short_name"] = stock_info["corp_name"]
    stock_info_result["symbol"] = stock_info["item_code"]
    stock_info_result["exchange"] = f"{stock_info['market_name']} ({stock_info['market_code']})"
    return stock_info_result


def test():
    test_ticker = "AAPL"
    stock = Ticker(test_ticker)
    stock_info = stock.info
    print(stock_info)


if __name__ == "__main__":
    test()