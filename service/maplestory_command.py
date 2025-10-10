import asyncio
import discord
from discord.ext import commands

import pandas as pd
import numpy as np
import io
from matplotlib import pyplot as plt
from bs4 import BeautifulSoup

from service.maplestory_utils import *
from service.maplestory_resolver import AsyncCharacterOCIDResolver

from bot_logger import log_command, with_timeout
from utils.image import get_image_bytes
from utils.text import preprocess_int_with_korean
from utils.time import kst_format_now
from utils.plot import fp_maplestory_light, fp_maplestory_bold
from config import COMMAND_TIMEOUT, NEXON_CHARACTER_IMAGE_URL

from exceptions.client_exceptions import *
from exceptions.command_exceptions import *

ocid_resolver = AsyncCharacterOCIDResolver(get_ocid, ttl_sec=3600, negative_ttl_sec=60)


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 기본정보")
async def maple_basic_info(ctx: commands.Context, character_name: str) -> None:
    """메이플스토리 캐릭터의 기본 정보(basic_info) 를 가져오는 명령어

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트
        character_name (str): 캐릭터 이름 -> OCID 변환

    Returns:
        discord.ui.View: 캐릭터의 기본 정보를 보여주는 View 객체

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14

    Raises:
        Reference에 있는 URL 참조
    """
    if ctx.message.author.bot:
        return 
    
    try:
        character_ocid: str = await ocid_resolver.ocid_resolve(character_name)
        basic_info, character_popularity = await asyncio.gather(
            get_basic_info(character_ocid),
            get_popularity(character_ocid) 
        )
    except NexonAPICharacterNotFound:
        await ctx.send(f"캐릭터 '{character_name}'을 찾을 수 없어양!")
        return
    except NexonAPIBadRequest:
        await ctx.send(f"캐릭터 '{character_name}'의 기본 정보를 찾을 수 없어양!")
        raise CommandFailure("Character basic info not found")
    except NexonAPIForbidden:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
        raise CommandFailure("Forbidden access to API")
    except NexonAPITooManyRequests:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
        raise CommandFailure("Too many requests to API")
    except NexonAPIServiceUnavailable:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
        raise CommandFailure("Nexon Open API Internal server error")
    except NexonAPIError:
        await ctx.send(f"캐릭터 '{character_name}'의 기본 정보를 찾을 수 없어양!")
        raise CommandFailure("Character basic info not found")
    
    # 캐릭터 기본 정보 0 - 캐릭터 OCID (추가 데이터 조회용)
    character_ocid: str = basic_info.get('character_ocid')

    # 캐릭터 기본 정보 1 - 캐릭터 이름
    character_name: str = basic_info.get('character_name')
    if not character_name:
        await ctx.send(f"캐릭터 이름이 '{character_name}'인 캐릭터가 없어양!")
        return
    
    # 캐릭터 기본 정보 2 - 캐릭터 레벨
    character_level: int = basic_info.get('character_level')

    # 캐릭터 기본 정보 3 - 캐릭터 소속월드
    character_world: str | Literal["알수없음"] = basic_info.get('character_world')

    # 캐릭터 기본 정보 4 - 캐릭터 성별
    character_gender: str | Literal["제로"] = basic_info.get('character_gender')

    # 캐릭터 기본 정보 5 - 캐릭터 직업(차수)
    character_job: str | Literal["알수없음"] = basic_info.get('character_job')

    # 캐릭터 기본 정보 6 - 경험치
    character_exp: int = basic_info.get('character_exp')
    character_exp_rate: str | Literal["0.000%"] = basic_info.get('character_exp_rate')

    # 캐릭터 기본 정보 7 - 소속길드
    character_guild_name: str | Literal["길드가 없어양!"] = basic_info.get('character_guild_name')

    # 캐릭터 기본 정보 8 - 캐릭터 외형 이미지 (기본값에 기본 이미지가 들어가도록 수정예정)
    character_image: str | Literal[""] = basic_info.get('character_image')
    if character_image != '알 수 없음':
        character_image_look: str = character_image.split("/character/look/")[-1]
        character_image_url: str = f"{NEXON_CHARACTER_IMAGE_URL}{character_image_look}.png"

    # 캐릭터 기본 정보 9 - 캐릭터 생성일 "2023-12-21T00:00+09:00"
    character_date_create: str | Literal["알수없음"] = basic_info.get('character_date_create')
    
    # 캐릭터 기본 정보 10 - 캐릭터 최근 접속 여부 (7일 이내 접속 여부)
    character_access_flag: bool | Literal["알수없음"] = basic_info.get('character_access_flag')

    # 캐릭터 기본 정보 11 - 캐릭터 해방 퀘스트 완료 여부
    character_liberation_quest_clear: str | Literal["알수없음"] = basic_info.get('liberation_quest_clear')

    # Basic Info 데이터 전처리
    if character_date_create != '알수없음':
        character_date_create = character_date_create.split("T")[0]  # "2023-12-21" 형태로 변환
        character_date_create_ymd = character_date_create.split("-")
        character_date_create_str: str = (
            f"{int(character_date_create_ymd[0])}년 "
            f"{int(character_date_create_ymd[1])}월 "
            f"{int(character_date_create_ymd[2])}일"
        )

    if character_exp >= 1000:
        character_exp_str: str = f"{character_exp:,}"
    else:
        character_exp_str: str = str(character_exp)
    
    character_name_quote: str = quote(character_name)

    if character_access_flag:
        character_access_flag_str = "최근 7일 이내 접속함"
    else:
        character_access_flag_str = "최근 7일 이내 접속하지 않음"
    
    if character_liberation_quest_clear == "0":
        liberation_quest_clear_str = "제네시스 해방 퀘스트 미완료"
    elif character_liberation_quest_clear == "1":
        liberation_quest_clear_str = "제네시스 해방 퀘스트 완료"
    elif character_liberation_quest_clear == "2":
        liberation_quest_clear_str = "데스티니 1차 해방 퀘스트 완료"
    else:
        liberation_quest_clear_str = "해방 퀘스트 진행 여부 알 수 없음"


    # Embed 메시지 생성
    maple_scouter_url: str = f"https://maplescouter.com/info?name={character_name_quote}"
    
    embed_title: str = f"{character_world}월드 '{character_name}' 용사님의 기본 정보에양!!"
    embed_description: str = (
        f"[🔗 환산 사이트 이동]({maple_scouter_url})\n"
        f"**월드:** {character_world}\n"
        f"**이름:** {character_name}\n"
        f"**레벨:** {character_level} ({character_exp_rate}%)\n"
        f"**인기도:** {character_popularity:,}\n"
        f"**직업:** {character_job}\n"
        f"**길드:** {character_guild_name}\n"
        f"**경험치:** {character_exp_str}\n"
    )
    embed_footer: str = (
        f"생성일: {character_date_create_str}\n"
        f"{liberation_quest_clear_str}\n"
        f"({character_access_flag_str})\n"
        f"Data Based on Nexon Open API"
    )
    embed = discord.Embed(title=embed_title, description=embed_description)
    if character_image_url != '알 수 없음':
        embed.set_image(url=character_image_url)
    embed.set_footer(text=embed_footer)
    if character_gender in ["남성", "남"]:
        embed.colour = discord.Colour.from_rgb(0, 128, 255)
    elif character_gender in ["여성", "여"]:
        embed.colour = discord.Colour.from_rgb(239, 111, 148)
    else:
        embed.colour = discord.Colour.from_rgb(128, 128, 128)
    await ctx.send(embed=embed)


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 피씨방")
async def maple_pcbang_notice(ctx: commands.Context) -> None:
    """메이플스토리 PC방 이벤트 공지사항을 가져오는 명령어

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=24
    """
    try:
        notice_data: dict = await get_notice(target_event="pcbang")
    except NexonAPIBadRequest as e:
        await ctx.send(f"PC방 이벤트 공지사항을 찾을 수 없어양!")
        raise CommandFailure("PC Bang notice not found")
    except NexonAPIForbidden as e:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
        raise CommandFailure("Forbidden access to API")
    except NexonAPITooManyRequests as e:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
        raise CommandFailure("Too many requests to API")
    except NexonAPIServiceUnavailable as e:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
        raise CommandFailure("Nexon Open API Internal server error")
    except NexonAPIError as e:
        await ctx.send(f"PC방 이벤트 공지사항을 찾을 수 없어양!")
        raise CommandFailure("PC Bang notice not found")
        
    # 공지사항 데이터 전처리
    if notice_data:
        # 공지사항 제목, 링크, 내용(HTML)
        notice_title: str = notice_data.get("notice_title")
        notice_url: str = notice_data.get("notice_url")
        notice_id: str = notice_data.get("notice_id")

        # 공지사항 날짜 정보 예시 "2025-07-17T10:00+09:00" -> "2025년 7월 17일 10:00 (KST)"
        notice_date: str = notice_data.get("notice_date")
        notice_start_date: str = notice_data.get("notice_start_date")
        notice_end_date: str = notice_data.get("notice_end_date")

        footer_notice_text: str = (
            f"공지사항 날짜: {notice_date}\n"
        )

        # 공지사항 이미지 URL 추출
        notice_detail_data: dict = await get_notice_details(notice_id)
        notice_contents: str = (
            str(notice_detail_data.get('contents', '알 수 없음'))
            if notice_detail_data.get('contents') is not None
            else '알 수 없음'
        )
        if notice_contents != '알 수 없음':
            bs4_contents = BeautifulSoup(notice_contents, 'html.parser')
            image_src = bs4_contents.find('img')['src'] if bs4_contents.find('img') else '알 수 없음'
            image_url = f"{image_src}" if image_src != '알 수 없음' else '알 수 없음'
        else:
            image_url = '알 수 없음'

        # 메시지 생성
        content_text: str = (
            f"**이벤트 시작일:** {notice_start_date}\n"
            f"**이벤트 종료일:** {notice_end_date}\n"
        )
        notice_image_name: str = f"{notice_id}.png"
        if image_url != '알 수 없음':
            notice_image_bytes: io.BytesIO = get_image_bytes(image_url)
            notice_image_file = discord.File(fp=notice_image_bytes, filename=notice_image_name)
        notice_embed = discord.Embed(
            url=notice_url,
            color=discord.Colour.from_rgb(239, 111, 148)
        )
        notice_embed.title = notice_title
        notice_embed.set_footer(text=footer_notice_text)
        await ctx.send(
            embed=notice_embed,
            file=notice_image_file if image_url != '알 수 없음' else None,
            content=content_text
        )
        notice_image_bytes.close()

    # 공지사항이 없을 때
    else:
        await ctx.send("PC방 이벤트 공지사항이 없어양!")


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 썬데이")
async def maple_sunday_notice(ctx: commands.Context) -> None:
    """메이플스토리 썬데이 이벤트 공지사항을 가져오는 명령어

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=24
    """
    try:
        notice_data: dict = await get_notice(target_event="sunday")
    except NexonAPIBadRequest as e:
        await ctx.send(f"썬데이 이벤트 공지사항을 찾을 수 없어양!")
        raise CommandFailure("Sunday event notice not found")
    except NexonAPIForbidden as e:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
        raise CommandFailure("Forbidden access to API")
    except NexonAPITooManyRequests as e:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
        raise CommandFailure("Too many requests to API")
    except NexonAPIServiceUnavailable as e:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
        raise CommandFailure("Nexon Open API Internal server error")
    except NexonAPISundayEventNotFound as e:
        await ctx.send("썬데이 이벤트 공지사항이 아직 없어양!!\n매주 금요일 오전 10시에 업데이트 되니 참고해양!!")
        return
    except NexonAPIError as e:
        await ctx.send(f"썬데이 이벤트 공지사항을 찾을 수 없어양!")
        raise CommandFailure("Sunday event notice not found")

    # 공지사항 데이터 전처리
    if notice_data:
        # 공지사항 제목, 링크, 내용(HTML)
        notice_title: str = notice_data.get("notice_title")
        notice_url: str = notice_data.get("notice_url")
        notice_id: str = notice_data.get("notice_id")

        # 공지사항 날짜 정보 예시 "2025-07-17T10:00+09:00" -> "2025년 7월 17일 10:00 (KST)"
        notice_date: str = notice_data.get("notice_date")
        notice_start_date: str = notice_data.get("notice_start_date")
        notice_end_date: str = notice_data.get("notice_end_date")

        footer_notice_text: str = (
            f"공지사항 날짜: {notice_date}\n"
        )
        # 공지사항 이미지 URL 추출
        notice_detail_data: dict = await get_notice_details(notice_id)
        notice_contents: str = (
            str(notice_detail_data.get('contents')).strip()
            if notice_detail_data.get('contents') is not None
            else '알 수 없음'
        )
        if notice_contents != '알 수 없음':
            bs4_contents = BeautifulSoup(notice_contents, 'html.parser')
            image_src = bs4_contents.find('img')['src'] if bs4_contents.find('img') else '알 수 없음'
            image_url = f"{image_src}" if image_src != '알 수 없음' else '알 수 없음'
        else:
            image_url = '알 수 없음'

        # 메시지 생성
        content_text: str = (
            f"**이벤트 시작일:** {notice_start_date}\n"
            f"**이벤트 종료일:** {notice_end_date}\n"
        )
        notice_image_name: str = f"{notice_id}.png"
        if image_url != '알 수 없음':
            notice_image_bytes: io.BytesIO = get_image_bytes(image_url)
            notice_image_file = discord.File(fp=notice_image_bytes, filename=notice_image_name)
        notice_embed = discord.Embed(
            url=notice_url,
            color=discord.Colour.from_rgb(239, 111, 148)
        )
        notice_embed.title = notice_title
        notice_embed.set_footer(text=footer_notice_text)
        await ctx.send(
            embed=notice_embed,
            file=notice_image_file if image_url != '알 수 없음' else None,
            content=content_text
        )
        notice_image_bytes.close()

    # 공지사항이 없을 때
    else:
        await ctx.send("썬데이 이벤트 공지사항이 아직 없어양!!\n매주 금요일 오전 10시에 업데이트 되니 참고해양!!")


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 상세정보")
async def maple_detail_info(ctx: commands.Context, character_name: str) -> None:
    """메이플스토리 캐릭터의 상세 정보(detail_info)를 가져오는 명령어

    <수집 항목>
        - 캐릭터 이름
        - 캐릭터 레벨
        - 캐릭터 월드
        - 캐릭터 성별
        - 캐릭터 직업(차수)
        - 캐릭터 경험치 (비율)
        - 캐릭터 인기도
        - 캐릭터 소속 길드
        - 캐릭터 외형 이미지
        - 캐릭터 생성일
        - 캐릭터 최근 접속 여부 (7일 이내 접속 여부)
        - 캐릭터 능력치: 스탯수치
        - 캐릭터 능력치: 전투 능력치(보공, 크뎀, 방무, 쿨감)
        - 캐릭터 능력치: 전투력

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트
        character_name (str): 캐릭터 이름 -> OCID 변환

    Returns:
        discord.ui.View: 캐릭터의 상세 정보를 보여주는 View 객체

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14
    """
    try:
        character_ocid = await ocid_resolver.ocid_resolve(character_name)
        basic_info, stat_info, character_popularity = await asyncio.gather(
            get_basic_info(character_ocid),
            get_stat_info(character_ocid),
            get_popularity(character_ocid)
        )
    except NexonAPICharacterNotFound:
        await ctx.send(f"캐릭터 '{character_name}'을 찾을 수 없어양!")
        return
    except NexonAPIBadRequest:
        await ctx.send(f"캐릭터 '{character_name}'의 정보를 찾을 수 없어양!")
        raise CommandFailure("Character basic info not found")
    except NexonAPIForbidden:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
        raise CommandFailure("Forbidden access to API")
    except NexonAPITooManyRequests:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
        raise CommandFailure("Too many requests to API")
    except NexonAPIServiceUnavailable:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
        raise CommandFailure("Nexon Open API Internal server error")

    # 캐릭터 기본 정보 0 - 캐릭터 OCID (추가 데이터 조회용)
    character_ocid: str = basic_info.get('character_ocid')
    if not character_ocid:
        await ctx.send(f"캐릭터 이름이 '{character_name}'인 캐릭터가 없어양!")
        raise NexonAPIOCIDNotFound("Character OCID not found")

    # 캐릭터 기본 정보 1 - 캐릭터 이름
    character_name: str = basic_info.get('character_name')
    if not character_name:
        await ctx.send(f"캐릭터 이름이 '{character_name}'인 캐릭터가 없어양!")
        raise CommandFailure(f"Character name '{character_name}' not found")
    
    # 캐릭터 기본 정보 2 - 캐릭터 레벨
    character_level: int = basic_info.get('character_level')

    # 캐릭터 기본 정보 3 - 캐릭터 소속월드
    character_world: str | Literal["알수없음"] = basic_info.get('character_world')

    # 캐릭터 기본 정보 4 - 캐릭터 성별
    character_gender: str | Literal["제로"] = basic_info.get('character_gender')

    # 캐릭터 기본 정보 5 - 캐릭터 직업(차수)
    character_job: str | Literal["알수없음"] = basic_info.get('character_job')

    # 캐릭터 기본 정보 6 - 경험치
    character_exp: int = basic_info.get('character_exp')
    character_exp_rate: str | Literal["0.000%"] = basic_info.get('character_exp_rate')

    # 캐릭터 기본 정보 7 - 소속길드
    character_guild_name: str | Literal["길드가 없어양!"] = basic_info.get('character_guild_name')

    # 캐릭터 기본 정보 8 - 캐릭터 외형 이미지 (기본값에 기본 이미지가 들어가도록 수정예정)
    character_image: str | Literal[""] = basic_info.get('character_image')
    if character_image != '알 수 없음':
        character_image_look: str = character_image.split("/character/look/")[-1]
        character_image_url: str = f"{NEXON_CHARACTER_IMAGE_URL}{character_image_look}.png"

    # 캐릭터 기본 정보 9 - 캐릭터 생성일 "2023-12-21T00:00+09:00"
    character_date_create: str | Literal["알수없음"] = basic_info.get('character_date_create')
    
    # 캐릭터 기본 정보 10 - 캐릭터 최근 접속 여부 (7일 이내 접속 여부)
    character_access_flag: bool | Literal["알수없음"] = basic_info.get('character_access_flag')

    # 캐릭터 기본 정보 11 - 캐릭터 해방 퀘스트 완료 여부
    character_liberation_quest_clear: str | Literal["알수없음"] = basic_info.get('liberation_quest_clear')

    # Basic Info 데이터 전처리
    if character_date_create != '알수없음':
        character_date_create = character_date_create.split("T")[0]  # "2023-12-21" 형태로 변환
        character_date_create_ymd = character_date_create.split("-")
        character_date_create_str: str = (
            f"{int(character_date_create_ymd[0])}년 "
            f"{int(character_date_create_ymd[1])}월 "
            f"{int(character_date_create_ymd[2])}일"
        )

    if character_exp >= 1000:
        character_exp_str: str = f"{character_exp:,}"
    else:
        character_exp_str: str = str(character_exp)
    
    character_name_quote: str = quote(character_name)

    if character_access_flag:
        character_access_flag_str = "최근 7일 이내 접속함"
    else:
        character_access_flag_str = "최근 7일 이내 접속하지 않음"
    
    if character_liberation_quest_clear == "0":
        liberation_quest_clear_str = "제네시스 해방 퀘스트 미완료"
    elif character_liberation_quest_clear == "1":
        liberation_quest_clear_str = "제네시스 해방 퀘스트 완료"
    elif character_liberation_quest_clear == "2":
        liberation_quest_clear_str = "데스티니 1차 해방 퀘스트 완료"
    else:
        liberation_quest_clear_str = "해방 퀘스트 진행 여부 알 수 없음"

    
    # 캐릭터 상세 정보 12 - 캐릭터 능력치: 데미지(%) "175.00" -> "175.00%"
    character_stat_damage: str | Literal["알수없음"] = stat_info.get("stat_damage")
    if character_stat_damage != "알수없음":
        character_stat_damage_str: str = f"{character_stat_damage}%"
    else:
        character_stat_damage_str: str = "몰라양"

    # 캐릭터 상세 정보 13 - 캐릭터 능력치: 보스 공격력(%) "50.00" -> "50.00%"
    character_stat_boss_damage: str | Literal["알수없음"] = stat_info.get("stat_boss_damage")
    if character_stat_boss_damage != "알수없음":
        character_stat_boss_damage_str: str = f"{character_stat_boss_damage}%"
    else:
        character_stat_boss_damage_str: str = "몰라양"

    # 최종 데미지 항목 추가 (2025.10.04)
    character_final_damage: str | Literal["알수없음"] = stat_info.get("stat_final_damage")
    if character_final_damage != "알수없음":
        character_final_damage_str: str = f"{character_final_damage}%"
    else:
        character_final_damage_str: str = "몰라양"

    # 캐릭터 상세 정보 14 - 캐릭터 능력치: 크리티컬 데미지(%) "50.00" -> "50.00%"
    character_stat_critical_damage: str | Literal["알수없음"] = stat_info.get("stat_crit_damage")
    if character_stat_critical_damage != "알수없음":
        character_stat_critical_damage_str: str = f"{character_stat_critical_damage}%"
    else:
        character_stat_critical_damage_str: str = "몰라양"

    # 캐릭터 상세 정보 15 - 캐릭터 능력치: 방어율 무시(%) "50.00" -> "50.00%"
    character_stat_ignore_defense: str | Literal["알수없음"] = stat_info.get("stat_ignore_def")
    if character_stat_ignore_defense != "알수없음":
        character_stat_ignore_defense_str: str = f"{character_stat_ignore_defense}%"
    else:
        character_stat_ignore_defense_str: str = "몰라양"

    # 캐릭터 상세 정보 16 - 캐릭터 능력치: 스타포스
    character_stat_starforce: str | Literal["알수없음"] = stat_info.get("stat_starforce")
    if character_stat_starforce != "알수없음":
        character_stat_starforce_str: str = f"총합 {character_stat_starforce}성"
    else:
        character_stat_starforce_str: str = "몰라양"

    # 캐릭터 상세 정보 17 - 캐릭터 능력치: 아케인포스
    character_stat_arcane_force: str | Literal["알수없음"] = stat_info.get("stat_arcane_force")
    if character_stat_arcane_force != "알수없음":
        character_stat_arcane_force_str: str = f"{character_stat_arcane_force}"
    else:
        character_stat_arcane_force_str: str = "몰라양"

    # 캐릭터 상세 정보 18 - 캐릭터 능력치: 어센틱포스
    character_stat_authentic_force: str | Literal["알수없음"] = stat_info.get("stat_authentic_force")
    if character_stat_authentic_force != "알수없음":
        character_stat_authentic_force_str: str = f"{character_stat_authentic_force}"
    else:
        character_stat_authentic_force_str: str = "몰라양"

    # 캐릭터 상세 정보 19 - 캐릭터 능력치: 스탯(힘, 덱, 인트, 럭) "1000" -> "1,000"
    stat_str: int = stat_info.get("stat_str")
    stat_dex: int = stat_info.get("stat_dex")
    stat_int: int = stat_info.get("stat_int")
    stat_luk: int = stat_info.get("stat_luk")
    stat_hp: int = stat_info.get("stat_hp")
    stat_mp: int = stat_info.get("stat_mp")
    stat_str_ap: int = stat_info.get("stat_str_ap")
    stat_dex_ap: int = stat_info.get("stat_dex_ap")
    stat_int_ap: int = stat_info.get("stat_int_ap")
    stat_luk_ap: int = stat_info.get("stat_luk_ap")
    stat_hp_ap: int = stat_info.get("stat_hp_ap")
    stat_mp_ap: int = stat_info.get("stat_mp_ap")

    if stat_hp_ap < 0:
        stat_hp_ap = 0

    if stat_mp_ap < 0:
        stat_mp_ap = 0

    character_stat_str: str = f"{stat_str:,}"
    character_stat_dex: str = f"{stat_dex:,}"
    character_stat_int: str = f"{stat_int:,}"
    character_stat_luk: str = f"{stat_luk:,}"
    character_stat_hp: str = f"{stat_hp:,}"
    character_stat_mp: str = (
        f"{stat_mp:,}"
        if stat_mp > 0
        else "MP를 사용하지 않는 캐릭터에양"
    )
    character_stat_str_ap: str = f"{stat_str_ap:,}"
    character_stat_dex_ap: str = f"{stat_dex_ap:,}"
    character_stat_int_ap: str = f"{stat_int_ap:,}"
    character_stat_luk_ap: str = f"{stat_luk_ap:,}"
    character_stat_hp_ap: str = f"{stat_hp_ap:,}"
    character_stat_mp_ap: str = (
        f"{stat_mp_ap:,}"
        if stat_mp > 0
        else "X"
    )

    # 캐릭터 상세 정보 20 - 캐릭터 능력치: 드메
    character_stat_drop: str | Literal["알수없음"] = stat_info.get('stat_item_drop')
    if character_stat_drop != "알수없음":
        character_stat_drop_str: str = f"{character_stat_drop}%"
    else:
        character_stat_drop_str: str = "몰라양"
    character_stat_meso: str | Literal["알수없음"] = stat_info.get('stat_meso')
    if character_stat_meso != "알수없음":
        character_stat_meso_str: str = f"{character_stat_meso}%"
    else:
        character_stat_meso_str: str = "몰라양"

    # 캐릭터 상세 정보 21 - 캐릭터 능력치: 쿨감
    character_stat_cooldown_pct: str | Literal["알수없음"] = stat_info.get('stat_cooltime_reduction_per')
    if character_stat_cooldown_pct != "알수없음":
        character_stat_cooldown_pct_str: str = f"{character_stat_cooldown_pct}%"
    else:
        character_stat_cooldown_pct_str: str = "몰라양"
    character_stat_cooldown_sec: str | Literal["알수없음"] = stat_info.get('stat_cooltime_reduction_sec')
    if character_stat_cooldown_sec != "알수없음":
        character_stat_cooldown_sec_str: str = f"{character_stat_cooldown_sec}초"
    else:
        character_stat_cooldown_sec_str = "몰라양"
    character_stat_cooldown: str = f"{character_stat_cooldown_pct_str} | {character_stat_cooldown_sec_str}"

    # 캐릭터 상세 정보 22 - 캐릭터 능력치: 공격력/마력
    character_stat_attack_power: str = f"{int(stat_info.get('stat_attack', '0')):,}"
    character_stat_magic_power: str = f"{int(stat_info.get('stat_magic', '0')):,}"

    # 캐릭터 상세 정보 23 - 캐릭터 능력치: 전투력 "억 만 단위 변환"
    character_stat_battle_power: str = stat_info.get('stat_battle_power', '0')
    character_stat_battle_power = preprocess_int_with_korean(character_stat_battle_power)

    # Embed 메시지 생성
    maple_scouter_url: str = f"https://maplescouter.com/info?name={quote(character_name)}"

    embed_title: str = f"{character_world}월드 '{character_name}' 용사님의 상세 정보에양!!"
    embed_description: str = (
        f"[🔗 환산 사이트 이동]({maple_scouter_url})\n"
        f"**월드:** {character_world}\n"
        f"**이름:** {character_name}\n"
        f"**레벨:** {character_level} ({character_exp_rate}%)\n"
        f"**인기도:** {character_popularity:,}\n"
        f"**직업:** {character_job}\n"
        f"**길드:** {character_guild_name}\n"
        f"\n**\-\-\- 상세 정보 \-\-\-**\n"
        f"**전투력**: {character_stat_battle_power}\n"
        f"**공격력/마력**: {character_stat_attack_power} / {character_stat_magic_power}\n"
        f"**데미지**: {character_stat_damage_str}\n"
        f"**최종 데미지**: {character_final_damage_str}\n"
        f"**보스 공격력**: {character_stat_boss_damage_str}\n"
        f"**크리티컬 데미지**: {character_stat_critical_damage_str}\n"
        f"**방어율 무시**: {character_stat_ignore_defense_str}\n"
        f"**드랍/메획 증가**: {character_stat_drop_str} / {character_stat_meso_str}\n"
        f"\n**\-\-\- 능력치 \-\-\-**\n"
        f"**STR**: {character_stat_str} ({character_stat_str_ap})\n"
        f"**DEX**: {character_stat_dex} ({character_stat_dex_ap})\n"
        f"**INT**: {character_stat_int} ({character_stat_int_ap})\n"
        f"**LUK**: {character_stat_luk} ({character_stat_luk_ap})\n"
        f"**HP**: {character_stat_hp} ({character_stat_hp_ap})\n"
        f"**MP**: {character_stat_mp} ({character_stat_mp_ap})\n"
        f"**재사용 대기시간 감소**: {character_stat_cooldown}\n"
        f"\n**\-\-\- 포스정보 \-\-\-**\n"
        f"**스타포스**: {character_stat_starforce_str}\n"
        f"**아케인포스**: {character_stat_arcane_force_str}\n"
        f"**어센틱포스**: {character_stat_authentic_force_str}\n"
    )
    embed_footer: str = (
        f"생성일: {character_date_create_str}\n"
        f"{liberation_quest_clear_str}\n"
        f"({character_access_flag_str})\n"
        f"Data Based on Nexon Open API"
    )
    embed = discord.Embed(title=embed_title, description=embed_description)
    if character_image_url != '알 수 없음':
        embed.set_image(url=character_image_url)
    embed.set_footer(text=embed_footer)
    if character_gender in ["남성", "남"]:
        embed.colour = discord.Colour.from_rgb(0, 128, 255)
    elif character_gender in ["여성", "여"]:
        embed.colour = discord.Colour.from_rgb(255, 105, 180)
    else:
        embed.colour = discord.Colour.from_rgb(128, 128, 128) # 제로일 경우 회색
    await ctx.send(embed=embed)


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 어빌리티")
async def maple_ability_info(ctx: commands.Context, character_name: str) -> None:
    """캐릭터의 어빌리티 정보 조회

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트
        character_name (str): 메이플스토리 캐릭터 이름

    Returns:
        discord.ui.Embed: 캐릭터 어빌리티 정보를 담은 Embed 객체 (add_field 사용)

    Raises:
        Exception: 캐릭터 정보 조회 실패 시 발생
    """
    if ctx.message.author.bot:
        return
    
    try:
        character_ocid = await ocid_resolver.ocid_resolve(character_name)
        
        # 동기 함수 병렬 실행
        ability_info, basic_info = await asyncio.gather(
            get_ability_info(character_ocid),
            get_basic_info(character_ocid)
        )

        character_name: str = basic_info.get('character_name', character_name)
        character_world: str = (
            str(basic_info.get('world_name')).strip()
            if basic_info.get('world_name') is not None else '모르는'
        )

    except NexonAPICharacterNotFound:
        await ctx.send(f"캐릭터 '{character_name}'의 어빌리티 정보를 찾을 수 없어양!")
        return
    except NexonAPIBadRequest:
        await ctx.send(f"캐릭터 '{character_name}'의 어빌리티 정보를 찾을 수 없어양!")
        raise CommandFailure("Character ability info not found")
    except NexonAPIForbidden:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
        raise CommandFailure("Forbidden access to API")
    except NexonAPITooManyRequests:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
        raise CommandFailure("Too many requests to API")
    except NexonAPIServiceUnavailable:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
        raise CommandFailure("Nexon Open API Internal server error")

    # 캐릭터의 남은 명성 조회
    ability_fame: int = (
        int(ability_info.get('remain_fame'))
        if ability_info.get('remain_fame') is not None else 0
    )

    # 캐릭터가 현재 사용중인 어빌리티 정보 조회
    current_ability_info: list[dict] = ability_info.get("ability_info")
    if current_ability_info is None or len(current_ability_info) == 0:
        await ctx.send(f"아직 어빌리티를 획득하지 않았거나 정보를 조회할 수 없어양!")
        return
    else:
        # 어빌리티 전체 등급
        current_ability_grade: str = (
            str(ability_info.get('ability_grade')).strip()
            if ability_info.get('ability_grade') is not None else "몰라양"
        )
        current_ability_grade_symbol: str = maple_convert_grade_text(current_ability_grade)
        current_ability_preset_no: int = (
            int(ability_info.get('preset_no'))
            if ability_info.get('preset_no') is not None else 0
        )
        current_ability_text = ability_info_parse(ability_info=current_ability_info)

        # embed 객체 생성
        if current_ability_grade == "레전드리":
            embed_color: discord.Color = discord.Color.green()
        elif current_ability_grade == "유니크":
            embed_color: discord.Color = discord.Color.orange()
        elif current_ability_grade == "에픽":
            embed_color: discord.Color = discord.Color.purple()
        elif current_ability_grade == "레어":
            embed_color: discord.Color = discord.Color.blue()

        embed = discord.Embed(
            title=f"{character_world}월드 '{character_name}' 어빌리티 정보에양",
            description=f"현재 보유 명성: {ability_fame:,} \n",
            color=embed_color
        )

        # embed에 현재 사용중인 어빌리티 정보 추가
        current_embed_value: str = f"{current_ability_text}"
        embed.add_field(
            name=(
                f"현재 사용중인 어빌리티에양\n"
                f"({current_ability_grade_symbol} {current_ability_preset_no}번 프리셋 사용중)"
            ),
            value=current_embed_value
        )
        # # 캐릭터 이미지 썸네일 추출
        # if character_img_url != '몰라양':
        #     character_image_url: str = f"{character_img_url}?action=A00.2&emotion=E00&wmotion=W00"
        #     embed.set_image(url=character_image_url)

        # current_ability_preset_no번 프리셋를 제외한 다른 프리셋 호출
        preset_idx_list = [1, 2, 3]
        preset_idx_list.remove(current_ability_preset_no)
        for preset_idx in preset_idx_list:
            preset_ability: dict = ability_info.get(f'ability_preset_{preset_idx}')
            preset_ability_grade: str = (
                str(preset_ability.get('ability_preset_grade')).strip()
                if preset_ability.get('ability_preset_grade') is not None else "몰라양"
            )
            preset_ability_grade_symbol: str = maple_convert_grade_text(preset_ability_grade)
            preset_ability_info: list[dict] = preset_ability.get('ability_info')
            preset_ability_text: str = ability_info_parse(ability_info=preset_ability_info)
            preset_embed_name = f"\[{preset_ability_grade_symbol} 프리셋 {preset_idx}번 어빌리티 정보\]"
            preset_embed_value = preset_ability_text
            embed.add_field(name=preset_embed_name, value=preset_embed_value, inline=False)

        embed.set_footer(text=f"어빌리티 최대값은 숫자 뒤 괄호안에 표시되어 있어양")
        await ctx.send(embed=embed)


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 운세")
async def maple_fortune_today(ctx: commands.Context, character_name: str) -> None:
    """MapleStory 오늘의 운세 기능

    Args:
        ctx (commands.Context): Discord context
        character_name (str): 캐릭터 이름 -> OCID 변환

    Note:
        - today + OCID 조합으로 랜덤 고정 시드를 생성합니다
    """
    # 캐릭터 OCID 조회
    try:
        character_ocid: str = await asyncio.to_thread(ocid_resolver.ocid_resolve, character_name)

    except NexonAPIBadRequest as e:
        await ctx.send(f"캐릭터 '{character_name}'을 찾을 수 없어양!")
        raise CommandFailure(f"Character '{character_name}' not found")
    except NexonAPIForbidden as e:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
        raise CommandFailure("Forbidden access to API")
    except NexonAPITooManyRequests as e:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
        raise CommandFailure("Too many requests to API")
    except NexonAPIServiceUnavailable as e:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
        raise CommandFailure("Nexon Open API Service unavailable")
    except NexonAPIOCIDNotFound:
        await ctx.send(f"캐릭터 '{character_name}'의 OCID를 찾을 수 없어양!")
        raise CommandFailure(f"OCID not found for character: {character_name}")
    
    # OCID 데이터값 검증
    if not character_ocid:
        await ctx.send(f"캐릭터 '{character_name}'의 OCID를 찾을 수 없어양!")
        raise CommandFailure(f"OCID not found for character: {character_name}")
    
    # 캐릭터 월드/생성일 확인
    try:
        basic_info: dict = await asyncio.to_thread(get_basic_info, character_ocid)
    except NexonAPIBadRequest as e:
        await ctx.send(f"캐릭터 '{character_name}'의 상세 정보를 찾을 수 없어양!")
        raise CommandFailure(f"Character '{character_name}' detail info not found")
    except NexonAPIForbidden as e:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
        raise CommandFailure("Forbidden access to API")
    except NexonAPITooManyRequests as e:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
        raise CommandFailure("Too many requests to API")
    except NexonAPIServiceUnavailable as e:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
        raise CommandFailure("Nexon Open API Service unavailable")
    character_world: str = (
        str(basic_info.get('character_world')).strip()
        if basic_info.get('character_world') is not None
        else '알 수 없음'
    )
    character_date_create: str = (
        str(basic_info.get('character_date_create')).strip()
        if basic_info.get('character_date_create') is not None
        else '알 수 없음'
    )
    if character_date_create != '알 수 없음':
        character_date_create = character_date_create.split("T")[0]  # "2023-12-21" 형태로 변환
        character_date_create_ymd = character_date_create.split("-")
        character_date_create_str: str = (
            f"{int(character_date_create_ymd[0])}년 "
            f"{int(character_date_create_ymd[1])}월 "
            f"{int(character_date_create_ymd[2])}일"
        )

    # 시드 생성
    base_today_text: str = f"{datetime.now().strftime('%Y-%m-%d')}"
    base_ocid: str = character_ocid
    base_seed: str = f"{base_today_text}-{base_ocid}".encode('utf-8')
    h = hashlib.md5(base_seed).hexdigest()
    seed = int(h, 16) # 128-bit 정수형 변환

    embed_title: str = f"{character_world}월드 '{character_name}' 용사님의 오늘의 운세에양!"
    fortune_text: str = maple_pick_fortune(seed=seed)
    embed_description: str = (
        f"캐릭터 생년월일: {character_date_create_str}생\n"
        f"오늘의 날짜: {datetime.now().strftime('%Y년 %m월 %d일')}\n"
        f"\n{fortune_text}"
    )
    embed_footer: str = (
        f"주의: 운세는 재미로만 확인해주세양!\n"
        f"Data Based on Nexon Open API"
    )

    embed = discord.Embed(
        title=embed_title,
        description=embed_description,
        color=discord.Colour.from_rgb(255, 215, 0)  # gold
    )
    embed.set_footer(text=embed_footer)
    await ctx.send(embed=embed)


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 경험치")
async def maple_xp_history(ctx: commands.Context, character_name: str) -> None:
    """MapleStory 캐릭터 경험치 히스토리 조회

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트
        character_name (str): 메이플스토리 캐릭터 이름

    Returns:
        ctx.send: matplotlib로 생성한 경험치 히스토리 그래프 이미지 첨부

    Raises:
        Exception: 캐릭터 정보 조회 실패 시 발생
    """
    # 캐릭터 OCID 조회
    try:
        character_ocid: str = await ocid_resolver.ocid_resolve(character_name)
        character_basic_info = await get_basic_info(character_ocid)
    except NexonAPICharacterNotFound:
        await ctx.send(f"캐릭터 '{character_name}'을 찾을 수 없어양!")
        raise CommandFailure("Character not found")
    except NexonAPIBadRequest:
        await ctx.send(f"캐릭터 '{character_name}'의 기본 정보를 찾을 수 없어양!")
        raise CommandFailure(f"Character '{character_name}' not found")
    except NexonAPIForbidden:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
        raise CommandFailure("Forbidden access to API")
    except NexonAPITooManyRequests:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
        raise CommandFailure("Too many requests to API")
    except NexonAPIServiceUnavailable:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
        raise CommandFailure("Nexon Open API Service unavailable")
    except NexonAPIOCIDNotFound:
        await ctx.send(f"캐릭터 '{character_name}'의 OCID를 찾을 수 없어양!")
        raise CommandFailure(f"OCID not found for character: {character_name}")

    xp_history_data: List[Tuple[str, int, str]] = []

    # 오전 6시 이전에는 2일전 날짜부터 조회
    kst_now = kst_format_now()
    if kst_now.hour < 6:
        time_offset: int = 2
    else:
        time_offset: int = 1

    try:
        xp_history_data: List[Tuple[str, int, str]] = await get_weekly_xp_history(character_ocid, time_offset)
    except NexonAPIBadRequest:
        await ctx.send(f"캐릭터 '{character_name}'의 기본 정보를 찾을 수 없어양!")
        raise CommandFailure(f"Character '{character_name}' basic info not found")
    except NexonAPIForbidden:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
        raise CommandFailure("Forbidden access to API")
    except NexonAPITooManyRequests:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
        raise CommandFailure("Too many requests to API")
    except NexonAPIServiceUnavailable:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
        raise CommandFailure("Nexon Open API Service unavailable")

    # 캐릭터의 이름, 월드, 생성일 추출
    character_world: str = (
        str(character_basic_info.get('character_world')).strip()
        if character_basic_info.get('character_world') is not None
        else '알 수 없음'
    )
    character_date_create: str = (
        str(character_basic_info.get('character_date_create')).strip()
        if character_basic_info.get('character_date_create') is not None
        else '알 수 없음'
    )
    if character_date_create != '알 수 없음':
        character_date_create = character_date_create.split("T")[0]
        character_date_create_ymd = character_date_create.split("-")
        character_date_create_str: str = (
            f"{int(character_date_create_ymd[0])}년 "
            f"{int(character_date_create_ymd[1])}월 "
            f"{int(character_date_create_ymd[2])}일"
        )
    else:
        character_date_create_str = "알 수 없음"

    if not xp_history_data or len(xp_history_data) == 0:
        await ctx.send(f"캐릭터 '{character_name}'의 경험치 히스토리 정보를 찾을 수 없어양!")
        return
    
    else:
        # 경험치 히스토리 그래프 제목 생성
        plot_title: str = f"{character_world}월드 '{character_name}' 용사님의 1주간 경험치 추세"

        # 경험치 히스토리 데이터 전처리
        plot_data = []
        for date, lvl, exp in xp_history_data:
            exp_rate = float(exp.replace("%", ""))
            plot_data.append({"date": date, "level": lvl, "exp_rate": exp_rate})

        df = pd.DataFrame(plot_data)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df.sort_values("date")

        # label 설정
        labels = [f"{d.month}월 {d.day}일" for d in df["date"]]
        x = np.arange(len(df))
        y = df["exp_rate"].astype(float).to_numpy()
        lv = df["level"].astype(int).to_numpy()

        fig = plt.figure(figsize=(8, 3), dpi=160)
        ax = plt.gca()
        ylim_btm: float = 12.5  # 최소 높이 보정용 픽셀값

        for xi, yi, lvl in zip(x, y, lv):
            bar_h = yi + ylim_btm

            # bar 생성
            ax.bar(xi, bar_h, width=0.6, linewidth=0, zorder=2, alpha=0.7, color='#8FD19E',)

            # 경험치 퍼센트 라벨 (실제 값 표시)
            ax.annotate(f"{yi:.3f}%", xy=(xi, bar_h), xytext=(0, 5),
                        textcoords="offset points",
                        ha="center", va="bottom",
                        fontsize=8, weight='bold', zorder=3)
            
            # 레벨 라벨
            ax.annotate(f"Lv.{lvl}", xy=(xi, bar_h), xytext=(0, -11),
                        textcoords="offset points",
                        ha="center", va="bottom",
                        fontsize=6, zorder=3)
            
        # 축/격자 스타일 설정
        ax.set_xticks(x, labels, fontproperties=fp_maplestory_light, fontsize=8)
        ylim_top = max(75.0, float(y.max())) * 1.35 + ylim_btm
        ax.set_ylim(0, ylim_top)
        ax.set_yticks([])
        ax.grid(axis="y", which="major", linewidth=0.6, alpha= 0.15, zorder=1)
        ax.axhline(0, linewidth=0.8, color="#666666", alpha=0.4)

        # 프레임 스타일 설정
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_alpha(0.4)

        # 제목 설정
        ax.set_title(plot_title, fontproperties=fp_maplestory_bold, fontsize=16, pad=8)

        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight")
        plt.close(fig)
        buffer.seek(0)

        # Discord Embed 메시지 생성
        now_kst: str = datetime.now(tz=timezone("Asia/Seoul")).strftime("%Y%m%d")
        file = discord.File(buffer, filename=f"{character_ocid}_{now_kst}.png")
        await ctx.send(content=f"캐릭터 생성일: {character_date_create_str}", file=file)
        buffer.close()


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 코디")
async def maple_cash_equipment_info(ctx: commands.Context, character_name: str) -> None:
    """캐릭터의 장착중인 장착효과 및 외형 캐시 아이템 조회

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트
        character_name (str): 캐릭터 이름
    """
    if ctx.message.author.bot:
        return
    
    # 캐릭터 basic 정보 조회 (OCID 포함)
    try:
        character_ocid: str = await ocid_resolver.ocid_resolve(character_name)
        basic_info, cash_equipment_info, beauty_equipment_info = await asyncio.gather(
            get_basic_info(character_ocid),
            get_cash_equipment_info(character_ocid),
            get_beauty_equipment_info(character_ocid)
        )
    except NexonAPICharacterNotFound:
        await ctx.send(f"캐릭터 '{character_name}'를 찾을 수 없어양!")
        return
    except NexonAPIBadRequest:
        await ctx.send(f"캐릭터 '{character_name}'의 코디 정보를 찾을 수 없어양!")
        raise CommandFailure("Character cash equipment info not found")
    except NexonAPIForbidden:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
        raise CommandFailure("Forbidden access to API")
    except NexonAPITooManyRequests:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
        raise CommandFailure("Too many requests to API")
    except NexonAPIServiceUnavailable:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
        raise CommandFailure("Nexon Open API Internal server error")
    
    character_name: str = basic_info.get('character_name', character_name)
    character_world: str = (
        str(basic_info.get('character_world')).strip()
        if basic_info.get('character_world') is not None else '알수없음'
    )
    character_image: str | Literal[""] = basic_info.get('character_image')
    if character_image != '알 수 없음':
        character_image_url: str = f"{character_image}?emotion=E00&width=150&height=150"

    character_class: str | Literal["기타"] = cash_equipment_info.get('character_class', '기타')
    if cash_equipment_info.get("current_preset_no") is None:
        preset_not_found_msg: str = "프리셋 정보를 찾을 수 없어 1번 프리셋으로 조회할게양!"
        preset_no: int = 1
    else:
        preset_no: int = cash_equipment_info.get('current_preset_no')
        if preset_no not in [1, 2, 3]:
            preset_no = 1

    if character_class == "제로":
        # 제로일 경우 알파와 베타의 base 코디 정보도 같이 표시
        alpha_equip_base: List[Dict[str, Any]] = cash_equipment_info.get('cash_item_equipment_base', [])
        beta_equip_base: List[Dict[str, Any]] = cash_equipment_info.get('additional_cash_item_equipment_base', [])

