"""

디스코드 봇에서 주식 관련 명령어를 처리하는 모듈

사용 라이브러리: yfinance, discord.py, bs4, requests

"""
import discord
from yfinance import Ticker
import requests
from bs4 import BeautifulSoup
from discord.ext import commands
from service.common import log_command
from pytz import timezone
from datetime import datetime

from service.common import safe_float, safe_percent
from service.stk_exception import *

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
        raise STK_ERROR_NO_RATE(f"환율 정보를 찾을 수 없어양: {from_currency}")
    else:
        # 환율 정보를 가져오는 데 실패한 경우
        raise STK_ERROR_FETCH_RATE(f"HTTP {response.status_code}: {response.reason}")

@log_command
async def stk_us_stock_price(ctx: commands.Context, ticker: str) -> float:
    """주식 티커에 해당하는 미국 주식의 현재 가격을 반환합니다.

    Args:
        ticker (str): 주식 티커 심볼 (예: 'AAPL', 'GOOGL')

    Returns:
        float: 현재 주식 가격
    """
    try:
        stock = Ticker(ticker)
        previous_close = stock.info.get('regularMarketPreviousClose', '몰라양')
        today_close = stock.info.get('regularMarketPrice', '몰라양')
        if previous_close == '몰라양' or today_close == '몰라양':
            raise STK_ERROR_NO_TICKER(f'티커 {ticker}는 존재하지 않거나, 주식 정보가 없어양!')
        stock_name = stock.info.get('shortName', ticker)
        stock_ticker = stock.info.get('symbol', ticker)
        stock_timezone = stock.info.get('exchangeTimezoneName', 'America/New_York')
        stock_timezone_short = stock.info.get('exchangeTimezoneShortName', 'EST')
        stock_exchange = stock.info.get('fullExchangeName', 'NYSE')
        stock_sector = stock.info.get('sector', '몰라양')
        stock_currency = stock.info.get('financialCurrency', 'USD')
        high_52w = stock.info.get('fiftyTwoWeekHigh', '몰라양')
        high_52w_change_pct = stock.info.get('fiftyTwoWeekHighChangePercent', '몰라양')
        low_52w = stock.info.get('fiftyTwoWeekLow', '몰라양')
        low_52w_change_pct = stock.info.get('fiftyTwoWeekLowChangePercent', '몰라양')

        # KRW 환율 변환
        if stock_currency != 'KRW':
            currency_rate: float = exchange_krw_rate(stock_currency)
            pc_krw = previous_close * currency_rate
            pc_krw_text = f"({pc_krw:,.2f} KRW)"
            tc_krw = today_close * currency_rate
            tc_krw_text = f"({tc_krw:,.2f} KRW)"
            high_52w_krw = high_52w * currency_rate
            high_52w_krw_text = f"({high_52w_krw:,.2f} KRW)"
            low_52w_krw = low_52w * currency_rate
            low_52w_krw_text = f"({low_52w_krw:,.2f} KRW)"
            footer_text_extra = (
                f"\n환율 정보 제공: 네이버 금융 (하나은행)\n"
                f"기준 환율: 1 {stock_currency} -> {currency_rate:.2f} KRW\n"
                f"환율 우대, 거래 수수료에 따라 주식가격이 다를 수 있어양."
            )
        else:
            pc_krw_text = ""
            tc_krw_text = ""
            high_52w_krw_text = ""
            low_52w_krw_text = ""
            footer_text_extra = ""

    except STK_ERROR_NO_TICKER:
        await ctx.send(f"티커 {ticker}는 존재하지 않거나, 주식 정보가 없어양!")
        return
    except STK_ERROR_NO_RATE:
        await ctx.send(f"경고) {stock_currency} 환율 정보를 찾을 수 없어양!")
    except STK_ERROR_FETCH_RATE:
        await ctx.send(f"경고) 환율 정보를 가져오는 데 실패했어양!")
    
    finally:
        # 가장 최근 거래일의 종가를 가져옵니다.
        content_text: str = f"[미국주식] 현재 주식 시세를 알려 드려양!!"
        stock_time = datetime.now(tz=timezone(stock_timezone)).strftime("%Y-%m-%d %H:%M:%S")
        kst_time = datetime.now(tz=timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
        change_pct: float = ((today_close - previous_close) / previous_close) * 100
        stk_us_info = (
            f"거래소: {stock_exchange} \n섹터: {stock_sector}\n"
            f"- **이전 종가:** {safe_float(previous_close)} {stock_currency} {pc_krw_text}\n"
            f"- **현재 가격:** {safe_float(today_close)} {stock_currency} {tc_krw_text}\n"
            f"- **변동률:** {change_pct:.2f} %\n\n"
            f"- **52주 최고가:** {safe_float(high_52w)} {stock_currency} {high_52w_krw_text} ({safe_percent(high_52w_change_pct)})\n"
            f"- **52주 최저가:** {safe_float(low_52w)} {stock_currency} {low_52w_krw_text} ({safe_percent(low_52w_change_pct)})\n"
        )
        footer_text = (
            f"정보 제공: yahoo finance API (최대 15분 지연)\n"
            f"현지 시간: {stock_time} ({stock_timezone_short})\n"
            f"한국 시간: {kst_time} (KST)"
            f"\n--- 환율안내 ---\n"
            f"{footer_text_extra}"
        )
        stock_embed = discord.Embed(
            title=f"{stock_name} ({stock_ticker})",
            description=stk_us_info,
            color=discord.Color.green()
        )
        stock_embed.set_footer(text=footer_text)
        await ctx.send(embed=stock_embed, content=content_text)

