"""

디스코드 봇에서 주식 관련 명령어를 처리하는 모듈

사용 라이브러리: yfinance, discord.py, bs4, requests

"""
import discord
import yfinance as yf
from discord.ext import commands
from service.common import log_command
from pytz import timezone
from datetime import datetime
from service.common import safe_float, safe_percent

@log_command
async def stk_us_stock_price(ctx: commands.Context, ticker: str) -> float:
    """주식 티커에 해당하는 미국 주식의 현재 가격을 반환합니다.

    Args:
        ticker (str): 주식 티커 심볼 (예: 'AAPL', 'GOOGL')

    Returns:
        float: 현재 주식 가격
    """
    try:
        stock = yf.Ticker(ticker)
        previous_close = stock.info.get('regularMarketPreviousClose', '몰라양')
        today_close = stock.info.get('regularMarketPrice', '몰라양')
        if previous_close == '몰라양' or today_close == '몰라양':
            raise Exception("STK_ERROR_NO_TICKER")
        stock_name = stock.info.get('shortName', ticker)
        stock_ticker = stock.info.get('symbol', ticker)
        stock_timezone = stock.info.get('exchangeTimezoneName', 'America/New_York')
        stock_timezone_short = stock.info.get('exchangeTimezoneShortName', 'EST')
        stock_exchange = stock.info.get('fullExchangeName', 'NYSE')
        stock_sector = stock.info.get('sector', '몰라양')
        stock_currency = stock.info.get('financialCurrency', 'USD')
        stock_52w_high = stock.info.get('fiftyTwoWeekHigh', '몰라양')
        stock_52w_high_change_pct = stock.info.get('fiftyTwoWeekHighChangePercent', '몰라양')
        stock_52wk_low = stock.info.get('fiftyTwoWeekLow', '몰라양')
        stock_52wk_low_change_pct = stock.info.get('fiftyTwoWeekLowChangePercent', '몰라양')

        # 가장 최근 거래일의 종가를 가져옵니다.
        content_text = f"[미국주식] 현재 주식 시세를 알려 드려양!!"
        stock_time = datetime.now(tz=timezone(stock_timezone)).strftime("%Y-%m-%d %H:%M:%S")
        kst_time = datetime.now(tz=timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
        change_pct = ((today_close - previous_close) / previous_close) * 100
        stk_us_info = (
            f"거래소: {stock_exchange} \n섹터: {stock_sector}\n"
            f"- **이전 종가:** {safe_float(previous_close)} {stock_currency}\n"
            f"- **현재 가격:** {safe_float(today_close)} {stock_currency}\n"
            f"- **변동률:** {change_pct:.2f} %\n"
            f"- **52주 최고가:** {safe_float(stock_52w_high)} {stock_currency} ({safe_percent(stock_52w_high_change_pct)})\n"
            f"- **52주 최저가:** {safe_float(stock_52wk_low)} {stock_currency} ({safe_percent(stock_52wk_low_change_pct)})\n"
        )
        footer_text = (
            f"정보 제공: yahoo finance API (최대 15분 지연)\n"
            f"현지 시간: {stock_time} ({stock_timezone_short})\n"
            f"한국 시간: {kst_time} (KST)"
        )
        stock_embed = discord.Embed(
            title=f"{stock_name} ({stock_ticker})",
            description=stk_us_info,
            color=discord.Color.green()
        )
        stock_embed.set_footer(text=footer_text)
        await ctx.send(embed=stock_embed, content=content_text)

    except Exception as e:
        if str(e) == "STK_ERROR_NO_TICKER":
            error_message = f"티커 '{ticker}'는 존재하지 않거나, 주식 정보가 없어양!"
        else:
            error_message = f"주식 정보를 가져오는 중 오류가 발생했어양"
        await ctx.send(error_message)
        raise Exception(str(e))
