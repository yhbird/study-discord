"""

디스코드 봇에서 주식 관련 명령어를 처리하는 모듈

사용 라이브러리: yfinance, discord.py, bs4, requests

"""
import io
import re
import discord
from discord.ext import commands
from bot import BumKkiBot

from matplotlib import pyplot as plt
from matplotlib import dates as mdates
import mplfinance as mpf

from service.finance.consts import FinanceCurrency, FinanceConsts
from service.finance.utils import YahooFinance, FinanceUtils, DataGoAPI
from datetime import datetime
from pytz import timezone

from bot_logger import log_command, with_timeout
from common.text import preprocess_int_with_korean, safe_float, safe_percent, preprocess_int_for_stocks
from common.plot import fp_maplestory_bold, fp_maplestory_light, set_up_matplotlib_korean
from config import COMMAND_TIMEOUT

from typing import Dict, List, Literal
from service.finance.exceptions import *
from common_exceptions.command_exceptions import CommandFailure


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 미국주식v2")
async def stk_us_price_v2(ctx: commands.Context[BumKkiBot], search_ticker: str) -> None:
    """ 주식 티커에 해당하는 미국 주식의 현재 가격을 확인합니다.

    Args:
        ctx: 디스코드 명령어 Context
        search_ticker (str): 주식 티커 심볼 ('AAPL', 'BRK-A')
    """
    service_currency = FinanceConsts.SERVICE_CURRENCY
    service_timezone = FinanceConsts.SERVICE_TIMEZONE
    service_timezone_short = FinanceConsts.SERVICE_TIMEZONE_SHORT

    async with ctx.typing():
        stock = YahooFinance(search_ticker)
        try:
            await stock.get_stock_info()
        except YFI_NO_TICKER as e:
            await ctx.send(str(e))
            raise CommandFailure(f"YFI_NO_TICKER : {search_ticker}")

        stock_info = stock.stock_info
        stock_currency = stock_info.get("currency")
        volume = stock_info.get("volume_regular")
        volume_avg10d = stock_info.get("volume_average_10d")
        dividend_yield = stock_info.get("dividend_yield")
        tc_value = stock_info.get("today_close")
        pc_value = stock_info.get("previous_close")
        high_52w = stock_info.get("high_52w")
        high_52w_pct = stock_info.get("high_52w_pct")
        low_52w = stock_info.get("low_52w")
        low_52w_pct = stock_info.get("low_52w_pct")
        analyst_score = stock_info.get("analyst_score") or "몰라양"
        analyst_score_category = stock_info.get("analyst_score_category") or "의견이 없어양"
        analyst_text = f"{analyst_score_category.replace('_', ' ').upper()} ({analyst_score})"

        pc_krw_text = ""
        tc_krw_text = ""
        h_52w_krw_text = ""
        l_52w_krw_text = ""
        exchange_info_text = ""

        if stock_currency != service_currency:
            try:
                currency_rate: float | None = await stock.get_currency_rate(to_currency=service_currency)
                pc_krw_value = pc_value * currency_rate
                tc_krw_value = tc_value * currency_rate
                h_52w_krw_value = high_52w * currency_rate
                l_52w_krw_value = low_52w * currency_rate
                pc_krw_text = f"({pc_krw_value:,.2f} {service_currency})"
                tc_krw_text = f"({tc_krw_value:,.2f} {service_currency})"
                h_52w_krw_text = f"({h_52w_krw_value:,.2f} {service_currency})"
                l_52w_krw_text = f"({l_52w_krw_value:,.2f} {service_currency})"
                exchange_info_text = FinanceCurrency.CURRENCY_SOURCE_INFO_V2.format(
                    source=stock_currency, target=currency_rate
                )
            except (YFI_NO_RATE_WARNING, YFI_STOCK_FETCH_RATE) as e:
                await ctx.send(str(e))


        change_pct: float = ((tc_value - pc_value) / pc_value) * 100
        market_cap: int | None = stock_info.get("market_cap")
        market_cap_text: str = "시가총액 정보가 없어양"
        if market_cap:
            market_cap_text: str = (
                f"주식 시가총액: {preprocess_int_with_korean(market_cap)} {stock_currency}\n"
                f"\t({service_currency}: {preprocess_int_with_korean(int(market_cap * currency_rate))}원)"
            )

        embed_title = f"{stock_info.get('short_name') or '몰라양'} ({stock_info.get('symbol') or '몰라양'})"
        embed_desc = (
            f"거래소: {stock_info.get('exchange') or '몰라양'}\n"
            f"산업: {stock_info.get('industry') or '몰라양'}\n"
            f"섹터: {stock_info.get('sector') or '몰라양'}\n"
            f"{market_cap_text}\n\n"
            
            f"- **이전 종가:** {safe_float(pc_value)} {stock_currency} {pc_krw_text}\n"
            f"- **현재 가격:** {safe_float(tc_value)} {stock_currency} {tc_krw_text}\n"
            f"- **변동률(%):** {change_pct:.2f} %\n\n"
            
            f"- **52주 최고가:** {safe_float(high_52w)} {stock_currency}"
            f" {h_52w_krw_text} ({safe_percent(high_52w_pct)})\n"
            f"- **52주 최저가:** {safe_float(low_52w)} {stock_currency}"
            f" {l_52w_krw_text} ({safe_percent(low_52w_pct)})\n\n"
            
            f"- **애널리스트 의견:** {analyst_text}\n"
            f"- **거래량:** {preprocess_int_for_stocks(volume) if volume else '몰라양'} "
            f"(평균 10일 거래량: {preprocess_int_for_stocks(volume_avg10d) if volume_avg10d else '몰라양'})\n"
            f"- **PSR:** {safe_float(stock_info.get('psr'))}\n"
            f"- **PBR:** {safe_float(stock_info.get('pbr'))}\n"
            f"- **PER:** {safe_float(stock_info.get('per'))}\n"
            f"- **배당 수익률:** {safe_float(dividend_yield)}\n"
        )

        exchange_now = datetime.now(tz=timezone(stock_info.get("timezone"))).strftime("%Y-%m-%d %H:%M:%S")
        kst_now = datetime.now(tz=timezone(service_timezone)).strftime("%Y-%m-%d %H:%M:%S")
        footer_text = (
            f"{exchange_info_text}\n"
            f"현지 시간: {exchange_now} ({stock_info.get('timezone_short')})\n"
            f"현재 시간: {kst_now} ({service_timezone_short})\n"
            f"{FinanceConsts.BASIC_FOOTER_TEXT}"
        )
        stock_embed = discord.Embed(
            title=embed_title,
            description=embed_desc,
            color=discord.Color.green()
        )
        stock_embed.set_footer(text=footer_text)
        context_text: str = "[미국주식] 현재 미국 주식의 시세 현황을 알려 드려양!"
        await ctx.send(embed=stock_embed, content=context_text)
        return


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 미국차트v2")
async def stk_us_chart_v2(ctx: commands.Context[BumKkiBot], search_ticker: str, period: str = "1주") -> None:
    """미국 주식의 시세 흐름을 차트로 표현합니다. (기본 1주일)
    
    Args:
        ctx (commands.Context): 디스코드 명령어 컨텍스트
        search_ticker (str): 주식 티커
        period (Literal["1주", "1개월", "3개월", "6개월", "1년", "5년", "전체"], optional): 차트 기간. Defaults to "1주".
    """
    service_timezone = FinanceConsts.SERVICE_TIMEZONE
    service_timezone_short = FinanceConsts.SERVICE_TIMEZONE_SHORT
    period_mapping: Dict[str, str] = FinanceConsts.HISTORY_PERIOD_MAPPING

    # 유효한 기간을 입력했는지 확인
    valid_period: List[str] = list(period_mapping.keys())
    if period not in valid_period:
        err_msg = (f"유효하지 않은 기간을 입력했어양!\n"
                    f"다음 중에서 선택해줘양: {', '.join(valid_period)}")
        await ctx.send(err_msg, reference=ctx.message)
        raise CommandFailure(err_msg)
    
    async with ctx.typing():
        stock = YahooFinance(search_ticker)
        try:
            validated_period = period_mapping[period]
            await stock.get_stock_info()
            await stock.get_stock_history(input_period=validated_period)
        except YFI_NO_TICKER as e:
            await ctx.send(str(e))
            raise CommandFailure(f"YFI_NO_TICKER : {search_ticker}")
        except KeyError as e:
            err_msg = (f"유효하지 않은 기간을 입력했어양!\n"
                       f"다음 중에서 선택해줘양: {', '.join(valid_period)}")
            await ctx.send(err_msg, reference=ctx.message)
            raise CommandFailure(f"KeyError - Invalid period: {period}")
        
        stock_info = stock.stock_info
        stock_hist = stock.stock_hist
        stock_name: str = stock_info.get("short_name") or search_ticker
        plot_title: str = f"{stock_name} ({stock_info.get('symbol') or '몰라양'}) - {period} 차트"
        service_datetime_str: str = (
            f"{datetime.now(tz=timezone(service_timezone)).strftime('%Y-%m-%d %H:%M:%S')}"
            f" ({service_timezone_short})"
        )
        tc_value = stock_info.get("today_close")
        stock_currency = stock_info.get("currency")
        content_text: str = (
            f"[미국주식] {stock_name}의 {period} 차트에양! (가격: 종가 기준)\n"
            f"- **현재 가격:** {safe_float(tc_value)} {stock_currency}\n"
            f"- **PSR:** {safe_float(stock_info.get('psr'))}\n"
            f"- **PBR:** {safe_float(stock_info.get('pbr'))}\n"
            f"- **PER:** {safe_float(stock_info.get('per'))}\n"
            f"현재 시간: {service_datetime_str}\n"
            f"{FinanceConsts.BASIC_FOOTER_TEXT}"
        )
        if validated_period in FinanceConsts.HISTORY_PERIOD_SHORT:
            family = set_up_matplotlib_korean("assets/font/Maplestory_Bold.ttf")
            rc = {'font.family': family, 'axes.unicode_minus': False}
            style_kor = mpf.make_mpf_style(base_mpf_style='yahoo', rc=rc)
            buffer = io.BytesIO()
            mpf.plot(
                stock_hist,
                type='candle',
                mav=(5, 20),
                volume=True,
                style=style_kor,
                figratio=(12, 5),
                title=plot_title,
                savefig=dict(fname=buffer, format="png", bbox_inches="tight"),
            )
            buffer.seek(0)
            now_kst: str = datetime.now(timezone('Asia/Seoul')).strftime("%Y%m%d_%H%M%S")
            file = discord.File(buffer, filename=f"{search_ticker}_{now_kst}.png")
            await ctx.send(content=content_text, file=file)
            buffer.close()
            return
        
        # period가 긴 경우, 선차트 생성
        elif validated_period in FinanceConsts.HISTORY_PERIOD_LONG:
            # 디스코드 해상도에 맞게 차트 그리기
            fig, ax = plt.subplots(figsize=(12, 5), dpi=180)
            ax.plot(stock_hist.index, stock_hist["price"], 
                    label="종가", color="#1f77b4", linewidth=2)
            ax.plot(stock_hist.index, stock_hist["MA5"], 
                    label="이동평균선 5일", color="#ff7f0e", linestyle='--', linewidth=1.2)
            ax.plot(stock_hist.index, stock_hist["MA20"], 
                    label="이동평균선 20일", color="#2ca02c", linestyle='--', linewidth=1.2)
            ax.plot(stock_hist.index, stock_hist["MA60"],
                    label="이동평균선 60일", color="#d62728", linestyle='--', linewidth=1.2)

            # X축 날짜 포맷팅
            locator = mdates.AutoDateLocator()
            formatter = mdates.ConciseDateFormatter(locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)

            # Y축 그리드선 설정
            ax.grid(alpha=0.3)
            ax.legend(loc='upper left')

            # 차트 제목 및 레이블 설정
            ax.set_title(plot_title, fontproperties=fp_maplestory_bold, fontsize=16)
            ax.set_xlabel("날짜", fontproperties=fp_maplestory_light, fontsize=12)
            ax.set_ylabel("가격 (USD)", fontproperties=fp_maplestory_light, fontsize=12)

            # 이미지 버퍼에 저장
            buffer = io.BytesIO()
            plt.savefig(buffer, format="png", bbox_inches="tight")
            plt.close(fig)
            buffer.seek(0)

            # 디스코드에 이미지 전송
            now_kst: str = datetime.now(timezone('Asia/Seoul')).strftime("%Y%m%d_%H%M%S")
            file = discord.File(buffer, filename=f"{search_ticker}_{now_kst}.png")
            await ctx.send(content=content_text, file=file)
            buffer.close()
            return
        
        else:
            err_msg = (f"유효하지 않은 기간을 입력했어양!\n"
                       f"다음 중에서 선택해줘양: {', '.join(valid_period)}")
            await ctx.send(err_msg, reference=ctx.message)
            raise CommandFailure(f"Invalid period: {period}")
    

@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 한국주식v2")
async def stk_kr_price_v2(ctx: commands.Context[BumKkiBot], search_target: str) -> None:
    """한국주식 가격을 조회하는 함수v2

    Args:
        ctx (commands.Context): 디스코드 명령어 컨텍스트
        search_target (str): 검색 대상 (예: 주식 종목 코드 또는 이름)
    """
    async with ctx.typing():
        # search_target이 종목 코드인지 이름인지 판단
        if re.fullmatch(r"\d{6}", search_target):
            krx_search_method: Literal["code"] = "code"
        else:
            krx_search_method: Literal["name"] = "name"

        data_go_api = DataGoAPI(search_text=search_target)
        try:
            krx_stock_info: Dict = await data_go_api.search_stock_ticker(krx_search_method)
            krx_symbol: str = krx_stock_info.get("item_code") or None
            krx_name: str = krx_stock_info.get("item_name") or search_target
            krx_corp_name: str = krx_stock_info.get("corp_name") or search_target
            krx_market_code: str = krx_stock_info.get("market_code") or "N/A"
            krx_market_name: str = krx_stock_info.get("market_name") or "N/A"

        except STK_KRX_SEARCH_NO_RESULT as e:
            await ctx.send(f"한국 주식({search_target}) 종목정보를 찾을 수 없어양!")
            raise CommandFailure(str(e))
        
        except YFI_KRX_SEARCH_ERROR as e:
            await ctx.send(f"한국 주식({search_target}) 종목정보 확인에 실패했어양!")
            raise CommandFailure(str(e))
        
        if not krx_symbol:
            err_msg = f"한국 주식({search_target}) 종목정보를 찾을 수 없어양!"
            await ctx.send(err_msg, reference=ctx.message)
            raise CommandFailure(err_msg)
        
        else:
            stock = YahooFinance(krx_symbol)

        try:
            await stock.get_stock_info()

        except YFI_NO_TICKER as e:
            await ctx.send(str(e))
            raise CommandFailure(f"YFI_NO_TICKER : {search_target}")

        stock_info = stock.stock_info
        stock_currency = stock_info.get("currency")
        volume = stock_info.get("volume_regular")
        volume_avg10d = stock_info.get("volume_average_10d")
        dividend_yield = stock_info.get("dividend_yield")
        tc_value = stock_info.get("today_close")
        pc_value = stock_info.get("previous_close")
        high_52w = stock_info.get("high_52w")
        high_52w_pct = stock_info.get("high_52w_pct")
        low_52w = stock_info.get("low_52w")
        low_52w_pct = stock_info.get("low_52w_pct")
        analyst_score = stock_info.get("analyst_score") or "몰라양"
        analyst_score_category = stock_info.get("analyst_score_category") or "의견이 없어양"
        analyst_text = f"{analyst_score_category.replace('_', ' ').upper()} ({analyst_score})"

        pc_krw_text = ""
        tc_krw_text = ""
        h_52w_krw_text = ""
        l_52w_krw_text = ""
        exchange_info_text = ""

        change_pct: float = ((tc_value - pc_value) / pc_value) * 100
        market_cap: int | None = stock_info.get("market_cap")
        market_cap_text: str = "시가총액 정보가 없어양"
        if market_cap:
            market_cap_text: str = (
                f"주식 시가총액: {preprocess_int_with_korean(market_cap)} {stock_currency}"
            )

        embed_title = f"{krx_corp_name or '몰라양'} ({krx_symbol or '몰라양'})"
        embed_desc = (
            f"거래소: {krx_market_name}\n"
            f"산업: {stock_info.get('industry') or '몰라양'}\n"
            f"섹터: {stock_info.get('sector') or '몰라양'}\n"
            f"{market_cap_text}\n\n"
            f"- **이전 종가:** {int(pc_value):,} {stock_currency} {pc_krw_text}\n"
            f"- **현재 가격:** {int(tc_value):,} {stock_currency} {tc_krw_text}\n"
            f"- **변동률(%):** {change_pct:.2f} %\n\n"
            
            f"- **52주 최고가:** {int(high_52w):,} {stock_currency}"
            f" {h_52w_krw_text} ({safe_percent(high_52w_pct)})\n"
            f"- **52주 최저가:** {int(low_52w):,} {stock_currency}"
            f" {l_52w_krw_text} ({safe_percent(low_52w_pct)})\n\n"
            
            f"- **애널리스트 의견:** {analyst_text}\n"
            f"- **거래량:** {preprocess_int_for_stocks(volume) if volume else '몰라양'} "
            f"(평균 10일 거래량: {preprocess_int_for_stocks(volume_avg10d) if volume_avg10d else '몰라양'})\n"
            f"- **PSR:** {safe_float(stock_info.get('psr'))}\n"
            f"- **PBR:** {safe_float(stock_info.get('pbr'))}\n"
            f"- **PER:** {safe_float(stock_info.get('per'))}\n"
            f"- **배당 수익률:** {safe_float(dividend_yield)}\n"
        )

        exchange_now = datetime.now(tz=timezone(stock_info.get("timezone"))).strftime("%Y-%m-%d %H:%M:%S")
        footer_text = (
            f"{exchange_info_text}\n"
            f"현재 시간: {exchange_now} ({stock_info.get('timezone_short')})\n"
            f"{FinanceConsts.BASIC_FOOTER_TEXT}"
        )
        stock_embed = discord.Embed(
            title=embed_title,
            description=embed_desc,
            color=discord.Color.green()
        )
        stock_embed.set_footer(text=footer_text)
        context_text: str = f"[한국주식] 현재 {krx_name} 주식의 시세 현황을 알려 드려양!"
        await ctx.send(embed=stock_embed, content=context_text)
        return


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 한국차트v2")
async def stk_kr_chart_v2(ctx: commands.Context[BumKkiBot], search_target: str, period: str = "1주") -> None:
    """한국주식의 시세흐름을 차트로 표현합니다. (기본 1주일)

    Args:
        ctx (commands.Context): 디스코드 명령어 컨텍스트
        search_target (str): 검색 대상 (예: 주식 종목 코드 또는 이름)
        period (Literal["1주", "1개월", "3개월", "6개월", "1년", "5년", "전체"]): 기간. Defaults to "1주".
    """
    # 기간 매핑
    period_mapping: Dict[str, str] = FinanceConsts.HISTORY_PERIOD_MAPPING
    valid_period: List[str] = list(period_mapping.keys())
    if period not in valid_period:
        err_msg = (f"유효하지 않은 기간을 입력했어양!\n"
                   f"다음 중에서 기간을 선택해주세양!: {', '.join(valid_period)}")
        await ctx.send(err_msg, reference=ctx.message)
        raise CommandFailure(err_msg)
    else:
        validated_period = period_mapping[period]

    async with ctx.typing():
        # 한국주식 기능과 동일하게 KRX 종목 코드 조회
        if re.fullmatch(r"\d{6}", search_target):
            krx_search_method: Literal["code"] = "code"
        else:
            krx_search_method: Literal["name"] = "name"

        data_go_api = DataGoAPI(search_text=search_target)
        try:
            krx_stock_info: Dict = await data_go_api.search_stock_ticker(krx_search_method)
            krx_symbol: str = krx_stock_info.get("item_code") or None
            krx_name: str = krx_stock_info.get("corp_name") or None
            krx_corp_name: str = krx_stock_info.get("corp_name") or search_target
            krx_market_code: str = krx_stock_info.get("market_code") or "N/A"
            krx_market_name: str = krx_stock_info.get("market_name") or "N/A"

        except STK_KRX_SEARCH_NO_RESULT as e:
            err_msg = f"한국 주식 '{search_target}'의 종목 정보를 찾을 수 없어양!"
            await ctx.send(err_msg, reference=ctx.message)
            raise CommandFailure(f"{str(e)}: {search_target}")

        except YFI_KRX_SEARCH_ERROR as e:
            err_msg = f"한국 주식 조회 API 실행 중에 오류가 발생했어양!"
            await ctx.send(err_msg, reference=ctx.message)
            raise CommandFailure(f"{str(e)}: {search_target}")

        if not krx_symbol:
            err_msg = f"한국 주식의 검색 티커(symbol)를 찾을 수 없어양!"
            await ctx.send(err_msg, reference=ctx.message)
            raise CommandFailure(err_msg)

        else:
            stock = YahooFinance(ticker=krx_symbol)
            await stock.get_stock_info()
            await stock.get_stock_history(input_period=validated_period)
            stock_info = stock.stock_info
            stock_hist = stock.stock_hist
            stock_name: str = krx_name or stock_info.get("short_name") or search_target
            plot_title: str = (
                    f"{krx_corp_name or stock_name} ({krx_symbol or stock_info.get('symbol')}) - {period} 차트"
            )
            tc_value: float = stock_info.get("today_close") or 0.0
            service_datetime_str: str = (
                f"{datetime.now(tz=timezone(FinanceConsts.SERVICE_TIMEZONE)).strftime('%Y-%m-%d %H:%M:%S')}"
                f" ({FinanceConsts.SERVICE_TIMEZONE_SHORT})"
            )
            content_text: str = (
                f"[한국주식] {stock_name}의 {period} 차트를 보여드릴게양!\n"
                f"- **현재 가격:** {int(tc_value):,} KRW (종가 기준)\n"
                f"- **PSR:** {safe_float(stock_info.get('psr'))}\n"
                f"- **PBR:** {safe_float(stock_info.get('pbr'))}\n"
                f"- **PER:** {safe_float(stock_info.get('per'))}\n"
                f"현재 시간: {service_datetime_str}\n"
                f"{FinanceConsts.BASIC_FOOTER_TEXT}"
            )

            # 짧은 기간의 차트 생성 요청 -> 버블차트 생성
            if validated_period in FinanceConsts.HISTORY_PERIOD_SHORT:
                fam = set_up_matplotlib_korean("assets/font/Maplestory_Bold.ttf")
                rc = {'font.family': fam, 'axes.unicode_minus': False}
                style_kor = mpf.make_mpf_style(base_mpf_style='yahoo', rc=rc)
                buffer = io.BytesIO()
                mpf.plot(
                    stock_hist,
                    type='candle',
                    mav=(5, 20),
                    volume=True,
                    style=style_kor,
                    figratio=(12, 5),
                    title=plot_title,
                    savefig=dict(fname=buffer, format="png", bbox_inches="tight"),
                )
                buffer.seek(0)
                now_kst: str = datetime.now(timezone('Asia/Seoul')).strftime("%Y%m%d_%H%M%S")
                file = discord.File(buffer, filename=f"{krx_symbol}_{now_kst}.png")
                await ctx.send(content=content_text, file=file)
                buffer.close()
                return
            # 긴 기간의 차트 생성 요청 -> 선차트 생성
            elif validated_period in FinanceConsts.HISTORY_PERIOD_LONG:
                # 디스코드 해상도에 맞게 차트 그리기
                fig, ax = plt.subplots(figsize=(12, 5), dpi=180)
                ax.plot(stock_hist.index, stock_hist["price"],
                        label="종가", color="#1f77b4", linewidth=2)
                ax.plot(stock_hist.index, stock_hist["MA5"],
                        label="이동평균선 5일", color="#ff7f0e", linestyle='--', linewidth=1.2)
                ax.plot(stock_hist.index, stock_hist["MA20"],
                        label="이동평균선 20일", color="#2ca02c", linestyle='--', linewidth=1.2)
                ax.plot(stock_hist.index, stock_hist["MA60"],
                        label="이동평균선 60일", color="#d62728", linestyle='--', linewidth=1.2)

                # X축 날짜 포맷팅
                locator = mdates.AutoDateLocator()
                formatter = mdates.ConciseDateFormatter(locator)
                ax.xaxis.set_major_locator(locator)
                ax.xaxis.set_major_formatter(formatter)

                # Y축 그리드선 설정
                ax.grid(alpha=0.3)
                ax.legend(loc='upper left')

                # 차트 제목 및 레이블 설정
                ax.set_title(plot_title, fontproperties=fp_maplestory_bold, fontsize=16)
                ax.set_xlabel("날짜", fontproperties=fp_maplestory_light, fontsize=12)
                ax.set_ylabel("가격 (USD)", fontproperties=fp_maplestory_light, fontsize=12)

                # 이미지 버퍼에 저장
                buffer = io.BytesIO()
                plt.savefig(buffer, format="png", bbox_inches="tight")
                plt.close(fig)
                buffer.seek(0)

                # 디스코드에 이미지 전송
                now_kst: str = datetime.now(timezone('Asia/Seoul')).strftime("%Y%m%d_%H%M%S")
                file = discord.File(buffer, filename=f"{search_target}_{now_kst}.png")
                await ctx.send(content=content_text, file=file)
                buffer.close()
                return

            else:
                err_msg = (f"유효하지 않은 기간을 입력했어양!\n"
                           f"다음 중에서 선택해줘양: {', '.join(valid_period)}")
                await ctx.send(err_msg, reference=ctx.message)
                raise CommandFailure(f"Invalid period: {period}")



@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 환율")
async def get_concurrency(ctx: commands.Context[BumKkiBot], text: str | None) -> None:
    """
    입력한 가격과 외화 단위에 맞춰 KRW로 환산하여 표시합니다.

    yahoo finance API를 활용하여 환율정보를 검색하고 전달합니다.

    Notes:
        아무것도 입력하지 않은 경우 전체 환율 표시 (현지환율 -> KRW)

    Args:
        ctx: Discord 명령어 Context
        text: KRW으로 환산하기 위한 현지 통화 입력 (미입력시 CURRENCY_CODE_MAP에 모든 환율 출력)
    """
    service_currency = FinanceConsts.SERVICE_CURRENCY
    service_currency_name = FinanceConsts.SERVICE_CURRENCY_KO
    async with ctx.typing():
        #사용자가 "븜 환율" 명령어를 입력한 경우
        if text is None:
            currency_map = FinanceCurrency.CURRENCY_NAME_MAP
            tip_msg = "참고: `븜 환율 100달러` 으로 입력하면 예상 금액을 알려줘양!"
            currency_list = currency_map.keys()
            embed_title = "[환율] 현재 환율 가격을 알려드려양!"
            currency_text = []
            for currency_code in currency_list:
                currency_rate = FinanceUtils.exchange_currency_rate(currency_code, service_currency)
                flag_100: bool = (currency_code in FinanceCurrency.CURRENCY_AMOUNT_100) or (currency_rate <= 15)
                base_amount: Literal[1, 100] = 100 if flag_100 else 1
                text = (f"{currency_map.get(currency_code)}: {base_amount} {currency_code} "
                        f"-> {safe_float(base_amount * currency_rate)} {service_currency}\n")
                currency_text.append(text)

            currency_embed = discord.Embed(
                title=embed_title,
                description="".join(currency_text),
                color=discord.Color.green()
            )
            footer_text = FinanceCurrency.CURRENCY_NOTICE_ALT
            currency_embed.set_footer(text=footer_text)
            await ctx.send(embed=currency_embed, content=tip_msg, reference=ctx.message)
            return
        #사용자가 "븜 환율 NNN{화폐단위}" 명령어를 입력한 경우
        else:
            parsed_amount, parsed_currency = FinanceUtils.parse_currency_code(text)
            currency_rate = FinanceUtils.exchange_currency_rate(parsed_currency, service_currency)
            flag_100: bool = (parsed_currency in FinanceCurrency.CURRENCY_AMOUNT_100) or (currency_rate <= 15)
            base_amount: Literal[1, 100] = 100 if flag_100 else 1
            source_ticker = f"({parsed_currency}/{service_currency})"
            target_amount = parsed_amount * currency_rate
            # 매매기준 + 카드결제 예상 수수료 추가
            transfer_rate = currency_rate * (1 + FinanceCurrency.CURRENCY_TRANSFER_FEE)
            transfer_amount = parsed_amount * transfer_rate
            total_amount = transfer_amount * (1 + FinanceCurrency.CARD_FEE_MARGIN)
            tip_msg = "참고: `븜 환율`으로 입력하면 현재 븜미가 알려줄 수 있는 환율들을 모두 알려줘양!"
            embed_title = f"[환율] {parsed_amount} {parsed_currency} 환율 계산 결과에양!"
            embed_text = (f"{parsed_amount} {parsed_currency} = {safe_float(target_amount)} {service_currency}\n"
                          f"({preprocess_int_with_korean(int(target_amount))} {service_currency_name})\n\n"
                          f"수수료를 고려한 예상 가격\n"
                          f"{safe_float(total_amount,2)} {service_currency}\n"
                          f"({preprocess_int_with_korean(int(total_amount))} {service_currency_name})")
            embed = discord.Embed(
                title=embed_title,
                description=embed_text,
                color=discord.Color.green()
            )
            footer_text = FinanceCurrency.CURRENCY_NOTICE.format(
                ticker=source_ticker,
                base_amount=base_amount,
                source=parsed_currency,
                target=base_amount * currency_rate,
                service=service_currency
            )
            embed.set_footer(text=footer_text)
            await ctx.send(embed=embed, content=tip_msg, reference=ctx.message)
            return

# 테스트 코드
def main():
    from_currency = "JPY"
    to_currency = "KRW"
    currency_rate = FinanceUtils.exchange_currency_rate(from_currency, to_currency)
    print(currency_rate)

if __name__ == "__main__":
    main()
