"""

디스코드 봇에서 Nexon Open API를 사용하여 메이플스토리 관련 명령어를 처리하는 모듈

Reference: https://openapi.nexon.com/

"""

import discord
import hashlib
from discord.ext import commands

from bs4 import BeautifulSoup
from urllib.parse import quote
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

from service.common import log_command, parse_iso_string, preprocess_int_with_korean
from service.api_utils import *
from config import NEXON_API_HOME

@log_command
async def api_basic_info(ctx: commands.Context, character_name: str) -> None:
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
    # 캐릭터의 OCID 조회
    try:
        character_ocid: str = get_ocid(character_name)
    except NexonAPIBadRequest:
        await ctx.send(f"캐릭터 '{character_name}'을 찾을 수 없어양!")
    except NexonAPIForbidden:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
    except NexonAPITooManyRequests:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
    except NexonAPIServiceUnavailable:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
    except NexonAPIOCIDNotFound:
        await ctx.send(f"캐릭터 '{character_name}'의 OCID를 찾을 수 없어양!")

    service_url: str = f"/maplestory/v1/character/basic"
    request_url: str = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}"
    # 예외 처리 (자세한 내용은 Reference 참고)
    try:
        response_data: dict = general_request_handler_nexon(request_url)
    except NexonAPIBadRequest:
        await ctx.send(f"캐릭터 '{character_name}'의 기본 정보를 찾을 수 없어양!")
    except NexonAPIForbidden:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
    except NexonAPITooManyRequests:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
    except NexonAPIServiceUnavailable:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")

    # 정상적으로 캐릭터 기본 정보를 찾았을 때
    # 캐릭터 기본 정보 1 - 캐릭터 이름
    character_name: str = response_data.get('character_name')
    if not character_name:
        await ctx.send(f"캐릭터 이름이 '{character_name}'인 캐릭터가 없어양!")
    # 캐릭터 기본 정보 2 - 캐릭터 레벨
    character_level: int = (
        int(response_data.get('character_level'))
        if response_data.get('character_level') is not None
        else 0
    )
    # 캐릭터 기본 정보 3 - 캐릭터 소속월드
    character_world: str = (
        str(response_data.get('world_name')).strip()
        if response_data.get('world_name') is not None
        else '알 수 없음'
    )
    # 캐릭터 기본 정보 4 - 캐릭터 성별
    character_gender: str = (
        str(response_data.get('character_gender')).strip()
        if response_data.get('character_gender') is not None
        else '기타(제로)'
    )
    # 캐릭터 기본 정보 5 - 캐릭터 직업(차수)
    character_class: str = (
        str(response_data.get('character_class')).strip()
        if response_data.get('character_class') is not None
        else '알 수 없음'
    )
    character_class_level: str = (
        str(response_data.get('character_class_level')).strip()
        if response_data.get('character_class_level') is not None
        else '알 수 없음'
    )
    # 캐릭터 기본 정보 6 - 경험치
    character_exp: int = (
        int(response_data.get('character_exp'))
        if response_data.get('character_exp') is not None
        else 0
    )
    character_exp_rate: str = (
        str(response_data.get('character_exp_rate')).strip()
        if response_data.get('character_exp_rate') is not None
        else "0.000%"
    )
    # 캐릭터 기본 정보 7 - 소속길드
    character_guild_name_json = response_data.get('character_guild_name')
    if character_guild_name_json is None:
        character_guild_name = '길드가 없어양!'
    else:
        character_guild_name = character_guild_name_json
    # 캐릭터 기본 정보 8 - 캐릭터 외형 이미지 (기본값에 기본 이미지가 들어가도록 수정예정)
    character_image: str = (
        str(response_data.get('character_image'))
        if response_data.get('character_image') is not None
        else '알 수 없음'
    )
    # 캐릭터 기본 정보 9 - 캐릭터 생성일 "2023-12-21T00:00+09:00"
    character_date_create: str = (
        str(response_data.get('character_date_create')).strip()
        if response_data.get('character_date_create') is not None
        else '알 수 없음'
    )
    # 캐릭터 기본 정보 10 - 캐릭터 최근 접속 여부 (7일 이내 접속 여부)
    character_access_flag: str = (
        str(response_data.get('access_flag'))
        if response_data.get('access_flag') is not None
        else '알 수 없음'
    )
    # 캐릭터 기본 정보 11 - 캐릭터 해방 퀘스트 완료 여부
    character_liberation_quest_clear: str = (
        str(response_data.get('liberation_quest_clear'))
        if response_data.get('liberation_quest_clear') is not None
        else '알 수 없음'
    )

    # Basic Info 데이터 전처리
    if character_date_create != '알 수 없음':
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
    if character_access_flag == "true":
        character_access_flag = "최근 7일 이내 접속함"
    else:
        character_access_flag = "최근 7일 이내 접속하지 않음"
    
    if character_liberation_quest_clear == "0":
        character_liberation_quest_clear = "제네시스 해방 퀘스트 미완료"
    elif character_liberation_quest_clear == "1":
        character_liberation_quest_clear = "제네시스 해방 퀘스트 완료"
    elif character_liberation_quest_clear == "2":
        character_liberation_quest_clear = "데스티니 1차 해방 퀘스트 완료"
    else:
        character_liberation_quest_clear = "해방 퀘스트 진행 여부 알 수 없음"

    if character_image != '알 수 없음':
        character_image_url: str = f"{character_image}?action=A00.2&emotion=E00&wmotion=W00&width=200&height=200"

    # Embed 메시지 생성
    maple_scouter_url: str = f"https://maplescouter.com/info?name={character_name_quote}"
    
    embed_title: str = f"{character_world}월드 '{character_name}' 용사님의 기본 정보에양!!"
    embed_description: str = (
        f"[🔗 환산 사이트 이동]({maple_scouter_url})\n"
        f"**월드:** {character_world}\n"
        f"**이름:** {character_name}\n"
        f"**레벨:** {character_level} ({character_exp_rate}%)\n"
        f"**인기도:** {get_character_popularity(character_ocid)}\n"
        f"**직업:** {character_class} ({character_class_level}차 전직)\n"
        f"**길드:** {character_guild_name}\n"
        f"**경험치:** {character_exp_str}\n"
    )
    embed_footer: str = (
        f"생성일: {character_date_create_str}\n"
        f"{character_liberation_quest_clear}\n"
        f"({character_access_flag})"
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

@log_command
async def api_pcbang_notice(ctx: commands.Context) -> None:
    """메이플스토리 PC방 이벤트 공지사항을 가져오는 명령어

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=24
    """
    try:
        notice_data: dict = get_notice(target_event="pcbang")
    except Exception as e:
        if '400' in str(e):
            await ctx.send(f"PC방 이벤트 공지사항을 찾을 수 없어양!")
            raise Exception("PC Bang notice not found")
        if '403' in str(e):
            await ctx.send("Nexon Open API 접근 권한이 없어양!")
            raise Exception("Forbidden access to API")
        if '429' in str(e):
            await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
            raise Exception("Too many requests to API")
        if '500' in str(e):
            await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
            raise Exception("Nexon Open API Internal server error")
        
    # 공지사항 데이터 전처리
    if notice_data:
        notice_data: dict = notice_data[0]  # 가장 최근 공지사항 1개

        # 공지사항 제목, 링크, 내용(HTML)
        notice_title: str = (
            str(notice_data.get('title')).strip()
            if notice_data.get('title') is not None
            else '알 수 없음'
        )
        notice_url: str = (
            str(notice_data.get('url')).strip()
            if notice_data.get('url') is not None
            else '알 수 없음'
        )
        notice_id: str = (
            str(notice_data.get('notice_id')).strip()
            if notice_data.get('notice_id') is not None
            else '알 수 없음'
        )

        # 공지사항 날짜 정보 예시 "2025-07-17T10:00+09:00" -> "2025년 7월 17일 10:00 (KST)"
        notice_date: str = (
            str(notice_data.get('date')).strip()
            if notice_data.get('date') is not None
            else '알 수 없음'
        )
        notice_start_date: str = (
            str(notice_data.get('date_event_start')).strip()
            if notice_data.get('date_event_start') is not None
            else '알 수 없음'
        )
        notice_end_date: str = (
            str(notice_data.get('date_event_end')).strip()
            if notice_data.get('date_event_end') is not None
            else '알 수 없음'
        )

        footer_notice_date: str = parse_iso_string(notice_date)
        footer_notice_start_date: str = parse_iso_string(notice_start_date)
        footer_notice_end_date: str = parse_iso_string(notice_end_date)
        footer_notice_text: str = (
            f"공지사항 날짜: {footer_notice_date}\n"
        )

        # 공지사항 이미지 URL 추출
        notice_detail_data: dict = get_notice_details(notice_id)
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
            f"**이벤트 시작일:** {footer_notice_start_date}\n"
            f"**이벤트 종료일:** {footer_notice_end_date}\n"
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

@log_command
async def api_sunday_notice(ctx: commands.Context) -> None:
    """메이플스토리 썬데이 이벤트 공지사항을 가져오는 명령어

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=24
    """
    try:
        notice_data: dict = get_notice(target_event="sunday")
    except Exception as e:
        if '400' in str(e):
            await ctx.send(f"썬데이 이벤트 공지사항을 찾을 수 없어양!")
            raise Exception("Sunday event notice not found")
        if '403' in str(e):
            await ctx.send("Nexon Open API 접근 권한이 없어양!")
            raise Exception("Forbidden access to API")
        if '429' in str(e):
            await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
            raise Exception("Too many requests to API")
        if '500' in str(e):
            await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
            raise Exception("Nexon Open API Internal server error")

    # 공지사항 데이터 전처리
    if notice_data:
        notice_data: dict = notice_data[0] # 가장 최근 공지사항 1개

        # 공지사항 제목, 링크, 내용(HTML)
        notice_title: str = (
            str(notice_data.get('title')).strip()
            if notice_data.get('title') is not None
            else '알 수 없음'
        )
        notice_url: str = (
            str(notice_data.get('url')).strip()
            if notice_data.get('url') is not None
            else '알 수 없음'
        )
        notice_id: str = (
            str(notice_data.get('notice_id')).strip()
            if notice_data.get('notice_id') is not None
            else '알 수 없음'
        )

        # 공지사항 날짜 정보 예시 "2025-07-17T10:00+09:00" -> "2025년 7월 17일 10:00 (KST)"
        notice_date: str = (
            str(notice_data.get('date')).strip()
            if notice_data.get('date') is not None
            else '알 수 없음'
        )
        notice_start_date: str = (
            str(notice_data.get('date_event_start')).strip()
            if notice_data.get('date_event_start') is not None
            else '알 수 없음'
        )
        notice_end_date: str = (
            str(notice_data.get('date_event_end')).strip()
            if notice_data.get('date_event_end') is not None
            else '알 수 없음'
        )

        footer_notice_date: str = parse_iso_string(notice_date)
        footer_notice_start_date: str = parse_iso_string(notice_start_date)
        footer_notice_end_date: str = parse_iso_string(notice_end_date)
        footer_notice_text: str = (
            f"공지사항 날짜: {footer_notice_date}\n"
        )

        # 공지사항 이미지 URL 추출
        notice_detail_data: dict = get_notice_details(notice_id)
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
            f"**이벤트 시작일:** {footer_notice_start_date}\n"
            f"**이벤트 종료일:** {footer_notice_end_date}\n"
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

@log_command
async def api_detail_info(ctx: commands.Context, character_name: str) -> None:
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
    # 캐릭터의 OCID 조회
    try:
        character_ocid: str = get_ocid(character_name)
    except NexonAPIError as e:
        if '400' in str(e):
            await ctx.send(f"캐릭터 '{character_name}'을 찾을 수 없어양!")
            raise NexonAPIBadRequest(f"Character '{character_name}' not found")
        if '403' in str(e):
            await ctx.send("Nexon Open API 접근 권한이 없어양!")
            raise NexonAPIForbidden("Forbidden access to API")
        if '429' in str(e):
            await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
            raise Exception("Too many requests to API")
        if '500' in str(e):
            await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
            raise Exception("Nexon Open API Internal server error")

    # OCID 데이터값 검증
    if not character_ocid:
        await ctx.send(f"캐릭터 '{character_name}'의 OCID를 찾을 수 없어양!")
        raise Exception(f"OCID not found for character: {character_name}")
    
    basic_info_service_url: str = f"/maplestory/v1/character/basic"
    detail_info_service_url: str = f"/maplestory/v1/character/stat"
    basic_info_request_url: str = f"{NEXON_API_HOME}{basic_info_service_url}?ocid={character_ocid}"
    detail_info_request_url: str = f"{NEXON_API_HOME}{detail_info_service_url}?ocid={character_ocid}"

    # 예외 처리 (자세한 내용은 Reference 참고)
    try:
        basic_info_response_data: dict = general_request_handler_nexon(basic_info_request_url)
        detail_info_response_data: dict = general_request_handler_nexon(detail_info_request_url)
    except Exception as e:
        if '400' in str(e):
            await ctx.send(f"캐릭터 '{character_name}'의 상세 정보를 찾을 수 없어양!")
            raise Exception(f"Character '{character_name}' detail info not found")
        if '403' in str(e):
            await ctx.send("Nexon Open API 접근 권한이 없어양!")
            raise Exception("Forbidden access to API")
        if '429' in str(e):
            await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
            raise Exception("Too many requests to API")
        if '500' in str(e):
            await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
            raise Exception("Nexon Open API Internal server error")
    
    # 캐릭터 상세 정보 1 - 캐릭터 이름
    character_name: str = basic_info_response_data.get('character_name')
    if not character_name:
        await ctx.send(f"캐릭터 이름이 '{character_name}'인 캐릭터가 없어양!")
        raise Exception(f"Character detail info not found for: {character_name}")
    # 캐릭터 상세 정보 2 - 캐릭터 레벨
    character_level: int = (
        int(basic_info_response_data.get('character_level', 0))
        if basic_info_response_data.get('character_level') is not None
        else 0
    )
    # 캐릭터 상세 정보 3 - 캐릭터 소속월드
    character_world: str = (
        str(basic_info_response_data.get('world_name')).strip()
        if basic_info_response_data.get('world_name') is not None
        else '알 수 없음'
    )
    # 캐릭터 상세 정보 4 - 캐릭터 성별
    character_gender: str = (
        str(basic_info_response_data.get('character_gender')).strip()
        if basic_info_response_data.get('character_gender') is not None
        else '알 수 없음'
    )
    # 캐릭터 상세 정보 5 - 캐릭터 직업(차수)
    character_class: str = (
        str(basic_info_response_data.get('character_class')).strip()
        if basic_info_response_data.get('character_class') is not None
        else '알 수 없음'
    )
    character_class_level: str = (
        str(basic_info_response_data.get('character_class_level')).strip()
        if basic_info_response_data.get('character_class_level') is not None
        else '알 수 없음'
    )
    # 캐릭터 상세 정보 6 - 경험치
    character_exp: int = (
        int(basic_info_response_data.get('character_exp'))
        if basic_info_response_data.get('character_exp') is not None
        else 0
    )
    character_exp_rate: str = (
        str(basic_info_response_data.get('character_exp_rate')).strip()
        if basic_info_response_data.get('character_exp_rate') is not None
        else "0.000%"
    )
    # 캐릭터 상세 정보 7 - 소속길드
    character_guild_name: str = (
        str(basic_info_response_data.get('character_guild_name')).strip()
        if basic_info_response_data.get('character_guild_name') is not None
        else '길드가 없어양!'
    )
    # 캐릭터 상세 정보 8 - 캐릭터 외형 이미지 (기본값에 기본 이미지가 들어가도록 수정예정)
    character_image: str = (
        str(basic_info_response_data.get('character_image')).strip()
        if basic_info_response_data.get('character_image') is not None
        else '알 수 없음'
    )
    if character_image != '알 수 없음':
        character_image_url: str = f"{character_image}?action=A00.2&emotion=E00&wmotion=W00&width=200&height=200"
    # 캐릭터 상세 정보 9 - 캐릭터 생성일 "2023-12-21T00:00+09:00"
    character_date_create: str = (
        str(basic_info_response_data.get('character_date_create')).strip()
        if basic_info_response_data.get('character_date_create') is not None
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
    # 캐릭터 상세 정보 10 - 캐릭터 최근 접속 여부 (7일 이내 접속 여부)
    character_access_flag: str = (
        str(basic_info_response_data.get('access_flag')).strip()
        if basic_info_response_data.get('access_flag') is not None
        else '알 수 없음'
    )
    if character_access_flag == "true":
        character_access_flag = "최근 7일 이내 접속함"
    elif character_access_flag == "false":
        character_access_flag = "최근 7일 이내 접속하지 않음"
    else:
        character_access_flag = "최근 접속 여부 알 수 없음"
    
    # detail_info_response_data 전처리
    stat_list: list[dict] = detail_info_response_data.get('final_stat', [])
    if not stat_list:
        await ctx.send(f"캐릭터 '{character_name}'의 상세 정보를 찾을 수 없어양!")
        raise Exception(f"Character '{character_name}' detail info not found")
    else:
        stat_info: dict = {}
        for stat in stat_list:
            stat_name: str = stat.get('stat_name')
            stat_value: str = stat.get('stat_value', '몰라양')
            stat_info[stat_name] = stat_value
    
    # 캐릭터 상세 정보 11 - 캐릭터 능력치: 스탯 공격력 "209558569" -> 억 만 단위 변환
    character_stat_attack: str = (
        str(stat_info.get('최대 스탯공격력')).strip()
        if stat_info.get('최대 스탯공격력') is not None
        else '몰라양')
    if character_stat_attack != '몰라양':
        character_stat_attack = preprocess_int_with_korean(character_stat_attack)
    # 캐릭터 상세 정보 12 - 캐릭터 능력치: 데미지(%) "175.00" -> "175.00%"
    character_stat_damage: str = (
        str(stat_info.get('데미지')).strip()
        if stat_info.get('데미지') is not None
        else '0.00%'
    )
    if character_stat_damage != '0.00%':
        character_stat_damage = f"{character_stat_damage}%"
    # 캐릭터 상세 정보 13 - 캐릭터 능력치: 보스 공격력(%) "50.00" -> "50.00%"
    character_stat_boss_attack: str = (
        str(stat_info.get('보스 몬스터 데미지')).strip()
        if stat_info.get('보스 몬스터 데미지') is not None
        else '0.00%'
    )
    if character_stat_boss_attack != '0.00%':
        character_stat_boss_attack = f"{character_stat_boss_attack}%"
    # 캐릭터 상세 정보 14 - 캐릭터 능력치: 크리티컬 데미지(%) "50.00" -> "50.00%"
    character_stat_critical_damage: str = (
        str(stat_info.get('크리티컬 데미지')).strip()
        if stat_info.get('크리티컬 데미지') is not None
        else '0.00%'
    )
    if character_stat_critical_damage != '0.00%':
        character_stat_critical_damage = f"{character_stat_critical_damage}%"
    # 캐릭터 상세 정보 15 - 캐릭터 능력치: 방어율 무시(%) "50.00" -> "50.00%"
    character_stat_ignore_defense: str = (
        str(stat_info.get('방어율 무시')).strip()
        if stat_info.get('방어율 무시') is not None
        else '0.00%'
    )
    if character_stat_ignore_defense != '0.00%':
        character_stat_ignore_defense = f"{character_stat_ignore_defense}%"
    # 캐릭터 상세 정보 16 - 캐릭터 능력치: 스타포스
    character_stat_starforce: str = (
        str(stat_info.get('스타포스')).strip()
        if stat_info.get('스타포스') is not None
        else '0'
    )
    if character_stat_starforce != '0':
        character_stat_starforce = f"총합 {character_stat_starforce}성"
    # 캐릭터 상세 정보 17 - 캐릭터 능력치: 아케인포스
    character_stat_arcaneforce: str = (
        str(stat_info.get('아케인포스')).strip()
        if stat_info.get('아케인포스') is not None
        else '0'
    )
    # 캐릭터 상세 정보 18 - 캐릭터 능력치: 어센틱포스
    character_stat_authenticforce: str = (
        str(stat_info.get('어센틱포스')).strip()
        if stat_info.get('어센틱포스') is not None
        else '0'
    )
    # 캐릭터 상세 정보 19 - 캐릭터 능력치: 스탯(힘, 덱, 인트, 럭) "1000" -> "1,000"
    stat_str: int = (
        int(stat_info.get('STR'))
        if stat_info.get('STR') is not None
        else 0
    )
    stat_dex: int = (
        int(stat_info.get('DEX'))
        if stat_info.get('DEX') is not None
        else 0
    )
    stat_int: int = (
        int(stat_info.get('INT'))
        if stat_info.get('INT') is not None
        else 0
    )
    stat_luk: int = (
        int(stat_info.get('LUK'))
        if stat_info.get('LUK') is not None
        else 0
    )
    stat_hp: int = (
        int(stat_info.get('HP'))
        if stat_info.get('HP') is not None
        else 0
    )
    stat_mp: int = (
        int(stat_info.get('MP'))
        if stat_info.get('MP') is not None
        else 0
    )
    if stat_mp == 0:
        stat_mp = 0
    stat_ap_str: int = (
        int(stat_info.get('AP 배분 STR', '0'))
        if stat_info.get('AP 배분 STR') is not None
        else 0
    )
    stat_ap_dex: int = (
        int(stat_info.get('AP 배분 DEX', '0'))
        if stat_info.get('AP 배분 DEX') is not None
        else 0
    )
    stat_ap_int: int = (
        int(stat_info.get('AP 배분 INT', '0'))
        if stat_info.get('AP 배분 INT') is not None
        else 0
    )
    stat_ap_luk: int = (
        int(stat_info.get('AP 배분 LUK', '0'))
        if stat_info.get('AP 배분 LUK') is not None
        else 0
    )
    stat_ap_hp: int = (
        int(stat_info.get('AP 배분 HP', '0'))
        if stat_info.get('AP 배분 HP') is not None
        else 0
    )
    if stat_ap_hp < 0:
        stat_ap_hp = 0
    stat_ap_mp: int = (
        int(stat_info.get('AP 배분 MP', '0'))
        if stat_info.get('AP 배분 MP') is not None
        else 0
    )
    if stat_ap_mp < 0:
        stat_ap_mp = 0
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
    character_stat_ap_str: str = f"{stat_ap_str:,}"
    character_stat_ap_dex: str = f"{stat_ap_dex:,}"
    character_stat_ap_int: str = f"{stat_ap_int:,}"
    character_stat_ap_luk: str = f"{stat_ap_luk:,}"
    character_stat_ap_hp: str = f"{stat_ap_hp:,}"
    character_stat_ap_mp: str = (
        f"{stat_ap_mp:,}"
        if stat_mp > 0
        else "X"
    )
    # 캐릭터 상세 정보 20 - 캐릭터 능력치: 드메
    character_stat_drop: str = stat_info.get('아이템 드롭률', '0%')
    if character_stat_drop != '0%':
        character_stat_drop = f"{character_stat_drop}%"
    character_stat_meso: str = stat_info.get('메소 획득량', '0%')
    if character_stat_meso != '0%':
        character_stat_meso = f"{character_stat_meso}%"
    # 캐릭터 상세 정보 21 - 캐릭터 능력치: 쿨감
    character_stat_cooldown_pct: str = stat_info.get('재사용 대기시간 감소 (%)', '0%')
    if character_stat_cooldown_pct != '0%':
        character_stat_cooldown_pct = f"{character_stat_cooldown_pct}%"
    character_stat_cooldown_sec: str = stat_info.get('재사용 대기시간 감소 (초)', '0초')
    if character_stat_cooldown_sec != '0초':
        character_stat_cooldown_sec = f"{character_stat_cooldown_sec}초"
    character_stat_cooldown: str = f"{character_stat_cooldown_pct} | {character_stat_cooldown_sec}"
    # 캐릭터 상세 정보 22 - 캐릭터 능력치: 공격력/마력
    character_stat_attack_power: str = f"{int(stat_info.get('공격력', '0')):,}"
    character_stat_magic_power: str = f"{int(stat_info.get('마력', '0')):,}"
    # 캐릭터 상세 정보 23 - 캐릭터 능력치: 전투력 "억 만 단위 변환"
    character_stat_battle_power: str = stat_info.get('전투력', '0')
    character_stat_battle_power = preprocess_int_with_korean(character_stat_battle_power)

    # Embed 메시지 생성
    maple_scouter_url: str = f"https://maplescouter.com/info?name={quote(character_name)}"
    embed_title: str = f"{character_world}월드 '{character_name}' 용사님의 상세 정보에양!!"
    embed_description: str = (
        f"[🔗 환산 사이트 이동]({maple_scouter_url})\n"
        f"**월드:** {character_world}\n"
        f"**이름:** {character_name}\n"
        f"**레벨:** {character_level} ({character_exp_rate}%)\n"
        f"**인기도:** {get_character_popularity(character_ocid)}\n"
        f"**직업:** {character_class} ({character_class_level}차 전직)\n"
        f"**길드:** {character_guild_name}\n"
        f"\n**\-\-\- 상세 정보 \-\-\-**\n"
        f"**전투력**: {character_stat_battle_power}\n"
        f"**보스 공격력**: {character_stat_boss_attack}\n"
        f"**크리티컬 데미지**: {character_stat_critical_damage}\n"
        f"**방어율 무시**: {character_stat_ignore_defense}\n"
        f"**드랍/메획 증가**: {character_stat_drop} / {character_stat_meso}\n"
        f"\n**\-\-\- 능력치 \-\-\-**\n"
        f"**STR**: {character_stat_str} ({character_stat_ap_str})\n"
        f"**DEX**: {character_stat_dex} ({character_stat_ap_dex})\n"
        f"**INT**: {character_stat_int} ({character_stat_ap_int})\n"
        f"**LUK**: {character_stat_luk} ({character_stat_ap_luk})\n"
        f"**HP**: {character_stat_hp} ({character_stat_ap_hp})\n"
        f"**MP**: {character_stat_mp} ({character_stat_ap_mp})\n"
        f"**재사용 대기시간 감소**: {character_stat_cooldown}\n"
        f"\n**\-\-\- 포스정보 \-\-\-**\n"
        f"**스타포스**: {character_stat_starforce}\n"
        f"**아케인포스**: {character_stat_arcaneforce}\n"
        f"**어센틱포스**: {character_stat_authenticforce}\n"
    )
    embed_footer: str = (
        f"생성일: {character_date_create_str}\n"
        f"({character_access_flag})"
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
        embed.colour = discord.Colour.from_rgb(128, 128, 128)
    await ctx.send(embed=embed)

@log_command
async def api_ability_info(ctx: commands.Context, character_name: str) -> None:
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
        ocid = get_ocid(character_name)
        if ocid is not None:
            ability_info: dict = get_character_ability_info(ocid)
            basic_info_service_url: str = f"/maplestory/v1/character/basic"
            basic_info_request_url: str = f"{NEXON_API_HOME}{basic_info_service_url}?ocid={ocid}"
            basic_info: dict = general_request_handler_nexon(basic_info_request_url)
            character_name: str = basic_info.get('character_name', character_name)
            character_world: str = (
                str(basic_info.get('world_name')).strip()
                if basic_info.get('world_name') is not None else '모르는'
            )

    except NexonAPIOCIDNotFound:
        await ctx.send(f"캐릭터 '{character_name}'의 어빌리티 정보를 찾을 수 없어양!")
        return
    except Exception as e:
        await ctx.send(f"캐릭터 '{character_name}'의 어빌리티 정보를 가져오는 중에 오류가 발생했어양!")
        return


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

@log_command
async def api_weather(ctx: commands.Context, location_name: str) -> None:
    """현재 지역의 날씨 정보, 예보 정보를 가져오는 명령어

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트
        location_name (str): 지역 이름/주소

    Raises:
        Exception : 지역정보 조회, 날씨 조회 실패 시 발생

    Reference:
        [지역 정보 조회 API (KAKAO developers)](https://developers.kakao.com/docs/latest/ko/local/dev-guide#search-by-address)
        [날씨 조회 API (Data.go.kr)](https://www.data.go.kr/data/15084084/openapi.do)
    """
    if ctx.message.author.bot:
        return
    
    try:
        # 지역 정보 조회
        location_data = get_local_info(local_name=location_name)
        local_type = location_data.get('address_type')
        if local_type == "REGION":
            local_address_name = location_data.get('address_name')
            local_x: str = location_data.get('x')
            local_y: str = location_data.get('y')
        else:
            local_road_address: dict = location_data.get('road_address')
            local_address_1 = local_road_address.get('region_1depth_name')
            local_address_2 = local_road_address.get('region_2depth_name')
            local_address_3 = local_road_address.get('region_3depth_name')
            local_address_name = f"{local_address_1} {local_address_2} {local_address_3}"
            local_x: str = local_road_address.get('x')
            local_y: str = local_road_address.get('y')
    except KKO_LOCAL_API_ERROR as e:
        await ctx.send(f"해당 지역의 정보를 검색하는 중에 오류가 발생했어양!")
        raise KakaoAPIError(str(e))
    except KKO_NO_LOCAL_INFO as e:
        await ctx.send(f"해당 지역의 정보를 찾을 수 없어양!")
        raise KakaoAPIError(str(e))
    
    try:
        # 날씨 정보 조회
        weather_info = get_weather_info(local_x, local_y)
    except WTH_API_INTERNAL_ERROR:
        await ctx.send(f"날씨 정보를 가져오는 중에 오류가 발생했어양!")
        raise WeatherAPIError("Internal server error")
    except WTH_API_DATA_ERROR:
        await ctx.send(f"날씨 API 데이터에 문제가 발생했어양!")
        raise WeatherAPIError("Data error")
    except WTH_API_DATA_NOT_FOUND:
        await ctx.send(f"해당 지역의 날씨 정보를 찾을 수 없어양!")
        raise WeatherAPIError("Data not found")
    except WTH_API_HTTP_ERROR:
        await ctx.send(f"날씨 API 요청 중에 오류가 발생했어양!")
        raise WeatherAPIError("HTTP error")
    except WTH_API_TIMEOUT:
        await ctx.send(f"날씨 데이터 가져오는데 시간이 초과되었어양!")
        raise WeatherAPIError("Timeout error")
    except WTH_API_INVALID_PARAMS:
        await ctx.send(f"날씨 API 요청 파라미터가 잘못되었어양!")
        raise WeatherAPIError("Invalid params")
    except WTH_API_INVALID_REGION:
        await ctx.send(f"해당 지역은 날씨 API에서 지원하지 않아양!")
        raise WeatherAPIError("Invalid region")
    except WTH_API_DEPRECATED:
        await ctx.send(f"더 이상 지원되지 않는 기능이에양!")
        raise WeatherAPIError("Deprecated feature")
    except WTH_API_UNAUTHORIZED:
        await ctx.send(f"날씨 API 서비스 접근 권한이 없어양!")
        raise WeatherAPIError("Unauthorized access to API")
    except WTH_API_KEY_TEMP_ERROR:
        await ctx.send(f"날씨 API 키가 임시로 제한되었어양!")
        raise WeatherAPIError("Temporary API key restriction")
    except WTH_API_KEY_LIMIT_EXCEEDED:
        await ctx.send(f"날씨 API 키의 요청 한도를 초과했어양!")
        raise WeatherAPIError("API key request limit exceeded")
    except WTH_API_KEY_INVALID:
        await ctx.send(f"날씨 API 키가 유효하지 않아양!")
        raise WeatherAPIError("Invalid API key")
    except WTH_API_KEY_EXPIRED:
        await ctx.send(f"날씨 API 키가 만료되었어양!")
        raise WeatherAPIError("Expired API key")
    except WeatherAPIError:
        await ctx.send(f"날씨 API 요청 중에 오류가 발생했어양!")
        raise WeatherAPIError("Weather API error")
    except Exception as e:
        await ctx.send(f"날씨 정보를 가져오는 중에 알 수 없는 오류가 발생했어양!")
        raise WeatherAPIError(str(e))

    # 날씨 데이터 전처리 - 실황 정보
    kst_now: datetime = datetime.now(tz=timezone("Asia/Seoul"))
    ncst_info: dict = weather_info.get("ncst")
    ncst_time: str = ncst_info.get("ncst_time", "몰라양")

    # 현재 온도
    val_temperature: str = ncst_info.get("temperature")
    if "알수없음" in val_temperature:
        current_temp: str = "몰라양"
    else:
        current_temp: str = f"{val_temperature.strip()}"
    
    # 현재 습도
    val_humidity: str = ncst_info.get("humidity")
    if "알수없음" in val_humidity:
        current_humidity: str = "몰라양"
    else:
        current_humidity: str = f"{val_humidity.strip()}"

    # 현재 풍속
    val_wind_speed: str = ncst_info.get("wind_speed") # 0.0 m/s
    if "알수없음" in val_wind_speed:
        wind_speed_text: str = "몰라양"
    else:
        wind_speed_text: str = f"{val_wind_speed.strip()}"
        val_wind_speed_float: float = float(val_wind_speed.replace("m/s", "").strip())
        if val_wind_speed_float >= 4.0 and val_wind_speed_float < 9.0:
            wind_speed_text: str = f"{val_wind_speed.strip()} (약간 강한 바람)"
        elif val_wind_speed_float >= 9.0 and val_wind_speed_float < 14.0:
            wind_speed_text: str = f"{val_wind_speed.strip()} (강한 바람)"
        elif val_wind_speed_float >= 14.0 and val_wind_speed_float < 20.0:
            wind_speed_text: str = f"{val_wind_speed.strip()} (매우 강한 바람)"
        elif val_wind_speed_float >= 20.0:
            wind_speed_text: str = f"{val_wind_speed.strip()} (폭풍 수준의 바람)"
            
    # 현재 풍향
    val_wind_direction: str = ncst_info.get("wind_direction")
    if "알수없음" in val_wind_direction:
        current_wind_direction: str = "몰라양"
    else:
        current_wind_direction: str = f"{val_wind_direction.strip()}"

    # 현재 강수 형태
    val_rain_type: str = ncst_info.get("rainsnow_type")
    if "알수없음" in val_rain_type:
        current_rain_type: str = "몰라양"
    else:
        current_rain_type: str = f"{val_rain_type.strip()}"

    # 현재 1시간 강수량 (비 또는 눈이 오는 경우 제공)
    if val_rain_type in ["없음", "알수없음"]:
        current_rain_flag: bool = False
    else:
        current_rain_flag: bool = True

    if current_rain_flag:
        val_rain_1h: str = ncst_info.get("rain_1h_value")
        val_rain_1h_desc: str = ncst_info.get("rain_1h_desc")
        val_rain_1h_float: float = float(val_rain_1h)
        if val_rain_1h_float >= 30.0 and val_rain_1h_float < 50.0:
            val_rain_1h_float_text = "들풍과 천둥, 번개를 동반한 비가 내릴 수 있어양."
        elif val_rain_1h_float >= 50.0 and val_rain_1h_float < 70.0:
            val_rain_1h_float_text = "도로가 침수될 수 있고, 차량 운행이 어려울 수 있어양."
        elif val_rain_1h_float >= 70.0:
            val_rain_1h_float_text = "심각한 피해가 발생할 수 있어양. 이불 밖은 위험해양!"
        else:
            val_rain_1h_float_text = "우산을 챙기세양. 비가 내릴 수 있어양."

        current_rain_text: str = (
            f"현재 1시간 강수량이 {val_rain_1h}mm 이에양.\n"
            f"{val_rain_1h_float_text}"
        )
        current_rain_type: str = f"비 ({val_rain_1h_desc})"
    else:
        current_rain_text: str = ""
    # 실황 정보 메세지 생성
    ncst_hhmm: str = kst_now.strftime("%H:%M")
    ncst_head: str = f"📍 현재 날씨 정보 ({ncst_hhmm})\n" # HH:MM
    ncst_text: str = (
        f"{ncst_head}"
        f"**현재 기온**: {current_temp}\n"
        f"**현재 습도**: {current_humidity}\n"
        f"**현재 풍속**: {current_wind_direction}풍 {wind_speed_text}\n"
        f"**강수 형태**: {current_rain_type}\n"
    )

    # 날씨 데이터 전처리 - 예보 정보
    fcst_info: dict = weather_info.get("fcst")
    fcst_time: str = fcst_info.get("fcst_time", "몰라양")

    # N시간 후 예보 정보 설정
    time_interval_hour_t1: int = 2
    time_interval_hour_t2: int = 4

    fcst_base_time: datetime = kst_now.replace(minute=0, second=0, microsecond=0)
    after_t1_time: datetime = fcst_base_time + timedelta(hours=time_interval_hour_t1)
    after_t1_time_str: str = after_t1_time.strftime("%Y%m%d-%H%M")
    after_t2_time: datetime = fcst_base_time + timedelta(hours=time_interval_hour_t2)
    after_t2_time_str: str = after_t2_time.strftime("%Y%m%d-%H%M")

    # "SKY" : 하늘상태 (0~5: 맑음, 6~8: 구름많음, 9~10: 흐림)
    fcst_sky: list[dict] = fcst_info.get("SKY", [])
    if fcst_sky:
        fcst_sky_text_t1: str = ""
        fcst_sky_text_t2: str = ""
        for sky in fcst_sky:
            fcst_datetime_str: str = sky.get("fcst_datetime_str")
            # t1/t2 시간 후 예보만 추출
            if fcst_datetime_str == after_t1_time_str:
                val_sky_t1: str = sky.get("value", "몰라양")
                imo_sky_t1: str = get_sky_icon(val_sky_t1)
                fcst_sky_text_t1: str = f"**하늘 상태**: {imo_sky_t1}\n"
            elif fcst_datetime_str == after_t2_time_str:
                val_sky_t2: str = sky.get("value", "몰라양")
                imo_sky_t2: str = get_sky_icon(val_sky_t2)
                fcst_sky_text_t2: str = f"**하늘 상태**: {imo_sky_t2}\n"
    else:
        fcst_sky_text_t1: str = ""
        fcst_sky_text_t2: str = ""

    # T1H : 기온 (단위: ℃)
    fcst_t1h: list[dict] = fcst_info.get("T1H", [])
    if fcst_t1h:
        fcst_t1h_text_t1: str = ""
        fcst_t1h_text_t2: str = ""
        for t1h in fcst_t1h:
            fcst_datetime_str: str = t1h.get("fcst_datetime_str")
            # t1/t2 시간 후 예보만 추출
            if fcst_datetime_str == after_t1_time_str:
                val_t1h_t1: str = t1h.get("value", "몰라양")
                fcst_t1h_text_t1 = f"**기온**: {val_t1h_t1}℃\n"
            elif fcst_datetime_str == after_t2_time_str:
                val_t1h_t2: str = t1h.get("value", "몰라양")
                fcst_t1h_text_t2 = f"**기온**: {val_t1h_t2}℃\n"
    else:
        fcst_t1h_text_t1: str = ""
        fcst_t1h_text_t2: str = ""

    # REH : 습도 (단위: %)
    fcst_reh: list[dict] = fcst_info.get("REH", [])
    if fcst_reh:
        fcst_reh_text_t1: str = ""
        fcst_reh_text_t2: str = ""
        for reh in fcst_reh:
            fcst_datetime_str: str = reh.get("fcst_datetime_str")
            # t1/t2 시간 후 예보만 추출
            if fcst_datetime_str == after_t1_time_str:
                val_reh_t1: str = reh.get("value", "몰라양")
                fcst_reh_text_t1 = f"**습도**: {val_reh_t1}%\n"
            elif fcst_datetime_str == after_t2_time_str:
                val_reh_t2: str = reh.get("value", "몰라양")
                fcst_reh_text_t2 = f"**습도**: {val_reh_t2}%\n"
    else:
        fcst_reh_text_t1: str = ""
        fcst_reh_text_t2: str = ""

    # VEC / WSD : 풍향 / 풍속
    fcst_vec: list[dict] = fcst_info.get("VEC", [])
    fcst_wsd: list[dict] = fcst_info.get("WSD", [])
    if fcst_vec and fcst_wsd:
        fcst_wind_text_t1: str = ""
        fcst_wind_text_t2: str = ""
        for vec, wsd in zip(fcst_vec, fcst_wsd):
            fcst_datetime_str: str = vec.get("fcst_datetime_str")
            # t1/t2 시간 후 예보만 추출
            if fcst_datetime_str == after_t1_time_str:
                val_vec_t1: str = vec.get("value", "몰라양")
                val_vec_t1_text: str = f"{get_wind_direction(val_vec_t1)}"
                val_wsd_t1: str = wsd.get("value", "몰라양") # 단위: m/s
                val_wsd_t1_float: float = float(val_wsd_t1)
                if val_wsd_t1_float >= 4.0 and val_wsd_t1_float < 9.0:
                    val_wsd_t1_text: str = f"{val_wsd_t1}m/s (약간 강한 바람)"
                elif val_wsd_t1_float >= 9.0 and val_wsd_t1_float < 14.0:
                    val_wsd_t1_text: str = f"{val_wsd_t1}m/s (강한 바람)"
                elif val_wsd_t1_float >= 14.0 and val_wsd_t1_float < 20.0:
                    val_wsd_t1_text: str = f"{val_wsd_t1}m/s (매우 강한 바람)"
                elif val_wsd_t1_float >= 20.0:
                    val_wsd_t1_text: str = f"{val_wsd_t1}m/s (폭풍 수준의 바람)"
                else:
                    val_wsd_t1_text: str = f"{val_wsd_t1}m/s"
                fcst_wind_text_t1 = f"**풍속**: {val_vec_t1_text}풍 {val_wsd_t1_text}\n"
            elif fcst_datetime_str == after_t2_time_str:
                val_vec_t2: str = vec.get("value", "몰라양")
                val_vec_t2_text: str = f"{get_wind_direction(val_vec_t2)}"
                val_wsd_t2: str = wsd.get("value", "몰라양")
                val_wsd_t2_float: float = float(val_wsd_t2)
                if val_wsd_t2_float >= 4.0 and val_wsd_t2_float < 9.0:
                    val_wsd_t2_text: str = f"{val_wsd_t2}m/s (약간 강한 바람)"
                elif val_wsd_t2_float >= 9.0 and val_wsd_t2_float < 14.0:
                    val_wsd_t2_text: str = f"{val_wsd_t2}m/s (강한 바람)"
                elif val_wsd_t2_float >= 14.0 and val_wsd_t2_float < 20.0:
                    val_wsd_t2_text: str = f"{val_wsd_t2}m/s (매우 강한 바람)"
                elif val_wsd_t2_float >= 20.0:
                    val_wsd_t2_text: str = f"{val_wsd_t2}m/s (폭풍 수준의 바람)"
                else:
                    val_wsd_t2_text: str = f"{val_wsd_t2}m/s"
                fcst_wind_text_t2 += f"**풍속**: {val_vec_t2_text}풍 {val_wsd_t2_text}\n"
    else:
        fcst_wind_text_t1: str = ""
        fcst_wind_text_t2: str = ""

    if fcst_sky_text_t1 == "" and fcst_t1h_text_t1 == "" and fcst_reh_text_t1 == "" and fcst_wind_text_t1 == "":
        after_text_t1: str = f"--- {time_interval_hour_t1}시간 후 예보 정보가 없어양 ---\n"
    else:
        after_head_t1_time: str = (
            after_t1_time.strftime("%H:%M") 
            if fcst_base_time.day == after_t1_time.day
            else after_t1_time.strftime("%m/%d %H:%M")
        )
        after_head_t1: str = f"--- {time_interval_hour_t1}시간 후 예보 ({after_head_t1_time}) ---\n"
        after_text_t1: str = (
            f"{after_head_t1}"
            f"{get_fcst_text(fcst_sky_text_t1)}"
            f"{get_fcst_text(fcst_t1h_text_t1)}"
            f"{get_fcst_text(fcst_reh_text_t1)}"
            f"{get_fcst_text(fcst_wind_text_t1)}"
        )
    if fcst_sky_text_t2 == "" and fcst_t1h_text_t2 == "" and fcst_reh_text_t2 == "" and fcst_wind_text_t2 == "":
        after_text_t2: str = f"--- {time_interval_hour_t2}시간 후 예보 정보가 없어양 ---\n"
    else:
        after_head_t2_time: str = (
            after_t2_time.strftime("%H:%M") 
            if fcst_base_time.day == after_t2_time.day
            else after_t2_time.strftime("%m/%d %H:%M")
        )
        after_head_t2: str = f"--- {time_interval_hour_t2}시간 후 예보 ({after_head_t2_time}) ---\n"
        after_text_t2: str = (
            f"{after_head_t2}"
            f"{get_fcst_text(fcst_sky_text_t2)}"
            f"{get_fcst_text(fcst_t1h_text_t2)}"
            f"{get_fcst_text(fcst_reh_text_t2)}"
            f"{get_fcst_text(fcst_wind_text_t2)}"
        )

    # embed 메시지 생성
    embed_title: str = f"{local_address_name}의 날씨 정보에양!"
    embed_description: str = (
        f"{ncst_text}\n"
        f"{after_text_t1}\n"
        f"{after_text_t2}"
    )
    embed_footer: str = (
        f"위치/날씨 정보 제공: Kakao Local API / 기상청 API (Data.go.kr)\n"
        f"현재 날씨 시간: {ncst_time}\n"
        f"예보 발표 시간: {fcst_time}\n"
        "(날씨 정보는 10분 단위, 예보 정보는 30분 단위로 갱신해양)"
    )

    embed = discord.Embed(
        title=embed_title,
        description=embed_description,
        color=discord.Colour.from_rgb(135, 206, 235)  # 하늘색
    )
    embed.set_footer(text=embed_footer)

    if current_rain_flag:
        await ctx.send(embed=embed, content=current_rain_text)
    else:
        await ctx.send(embed=embed)

@log_command
async def api_dnf_characters(ctx: commands.Context, server_name: str, character_name: str) -> None:
    """던전앤파이터 캐릭터 정보 조회

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트
        server_name (str): 서버 이름 (한글)
        character_name (str): 캐릭터 이름 (특수문자 가능)

    Returns:
        던전앤파이터 캐릭터 정보 (dict) -> Embed 생성

    Raises:
        NeopleAPIError: 던전앤파이터 API 요청 중 발생하는 오류
    """
    if ctx.message.author.bot:
        return
    
    # 캐릭터 고유 ID 조회
    try:
        character_id = neople_dnf_get_character_id(server_name, character_name)
        server_id = neople_dnf_server_parse(server_name)
    except NeopleAPIError as e:
        if "API001" in str(e):
            await ctx.send(f"네오플 API 요청에 오류가 발생했어양!!!")
        elif "API002" in str(e):
            await ctx.send(f"네오플 API 요청 제한에 걸렸어양...")
        elif "API006" in str(e):
            await ctx.send(f"네오플 API 요청 파라미터가 잘못되었어양...")
        elif "DNF000" in str(e):
            await ctx.send(f"서버명이 잘못 입력 되었어양...")
        elif "DNF001" in str(e):
            await ctx.send(f"캐릭터 '{character_name}'을(를) 찾을 수 없어양...")
        elif "DNF900" in str(e):
            await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        elif "DNF901" in str(e):
            await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        elif "DNF980" in str(e):
            await ctx.send(f"현재 던전앤파이터 서비스 점검 중이에양!")
        elif "DNF999" in str(e):
            await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        else:
            await ctx.send(f"던전앤파이터 API에서 알 수 없는 오류가 발생했어양!")
        raise NeopleAPIError(str(e))

    # 캐릭터 정보 조회
    try:
        request_url = f"{NEOPLE_API_HOME}/df/servers/{server_id}/characters/{character_id}?apikey={NEOPLE_API_KEY}"
        character_info: dict = general_request_handler_neople(request_url)
    except NeopleAPIError as e:
        if "API001" in str(e):
            await ctx.send(f"네오플 API 요청에 오류가 발생했어양!!!")
        elif "API002" in str(e):
            await ctx.send(f"네오플 API 요청 제한에 걸렸어양...")
        elif "API006" in str(e):
            await ctx.send(f"네오플 API 요청 파라미터가 잘못되었어양...")
        elif "DNF000" in str(e):
            await ctx.send(f"서버명이 잘못 입력 되었어양...")
        elif "DNF001" in str(e):
            await ctx.send(f"캐릭터 '{character_name}'을(를) 찾을 수 없어양...")
        elif "DNF900" in str(e):
            await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        elif "DNF901" in str(e):
            await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        elif "DNF980" in str(e):
            await ctx.send(f"현재 던전앤파이터 서비스 점검 중이에양!")
        elif "DNF999" in str(e):
            await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        else:
            await ctx.send(f"던전앤파이터 API에서 알 수 없는 오류가 발생했어양!")
        raise NeopleAPIError(str(e))

    # 모험단 이름 추출
    adventure_name: str = (
        str(character_info.get("adventureName")).strip()
        if character_info.get("adventureName") is not None
        else "adventureNameNotFound"
    )
    # 캐릭터 레벨 추출
    character_level: int = (
        int(character_info.get("level"))
        if character_info.get("level") is not None
        else 0
    )
    # 캐릭터 클래스 추출
    character_job_name: str = (
        str(character_info.get("jobName")).strip()
        if character_info.get("jobName") is not None
        else "몰라양"
    )
    # 캐릭터 전직명 추출
    character_job_grow_name: str = (
        str(character_info.get("jobGrowName")).strip()
        if character_info.get("jobGrowName") is not None
        else "몰라양"
    )
    # 캐릭터 명성 추출
    character_fame: int = (
        int(character_info.get("fame"))
        if character_info.get("fame") is not None
        else 0
    )
    # 캐릭터 길드 추출
    character_guild: str = (
        str(character_info.get("guildName")).strip()
        if character_info.get("guildName") is not None
        else "길드가 없어양!"
    )

    dundam_url = f"https://dundam.xyz/character?server={server_id}&key={character_id}"
    dfgear_url_c = f"https://dfgear.xyz/character?sId={server_id}&cId={character_id}&cName={character_name}"
    if adventure_name != "adventureNameNotFound":
        dfgear_url_a = f"https://dfgear.xyz/adventure?cName={adventure_name}"
        dfgear_url_desc = (
            f"[🔗 DFGEAR 사이트 이동 (캐릭터)]({dfgear_url_c})\n"
            f"[🔗 DFGEAR 사이트 이동 (모험단)]({dfgear_url_a})\n"
        )
    else:
        dfgear_url_desc = f"[🔗 DFGEAR 사이트 이동]({dfgear_url_c})\n"

    embed_description: str = (
        f"[🔗 던담 사이트 이동]({dundam_url})\n"
        f"{dfgear_url_desc}"
        f"**모험단:** {adventure_name}\n"
        f"**레벨:** {character_level}\n"
        f"**직업:** {character_job_name}\n"
        f"**전직:** {character_job_grow_name}\n"
        f"**명성:** {character_fame}\n"
        f"**길드:** {character_guild}\n"
    )
    embed_footer: str = (
        f"캐릭터 선택창에 나갔다 오면 빨리 갱신되양!\n"
        f"powered by Neople API"
    )

    # 캐릭터 이미지 URL추출
    character_image_url = f"https://img-api.neople.co.kr/df/servers/{server_id}/characters/{character_id}?zoom=1"
    character_image_bytes: io.BytesIO = get_image_bytes(character_image_url)
    today_date_str: str = datetime.now().strftime("%Y%m%d%H%M")
    character_image_filename = f"{server_id}_{character_id}_{today_date_str}.png"
    buffer = discord.File(character_image_bytes, filename=character_image_filename)
    # Discord Embed 객체 생성
    if character_job_name == "마법사(여)":
        embed_color = discord.Colour.from_rgb(255, 0, 0)  # red
    else:
        embed_color = discord.Colour.from_rgb(128, 128, 128)  # grey
    embed = discord.Embed(
        title=f"{server_name}서버 '{character_name}' 모험가님의 정보에양!",
        description=embed_description
    )
    embed.set_footer(text=embed_footer)
    embed.colour = embed_color
    embed.set_image(url=f"attachment://{character_image_filename}")

    # Discord Embed 전송
    await ctx.send(embed=embed, file=buffer)
    buffer.close()

@log_command
async def api_dnf_timeline_weekly(ctx: commands.Context, server_name: str, character_name: str) -> None:
    """던전앤파이터 캐릭터 주간 타임라인 조회 (이번주 기준)

    Args:
        ctx (commands.Context): Discord context
        server_name (str): 서버 이름
        character_name (str): 캐릭터 이름

    Raises:
        NexonAPIBadRequest: 잘못된 요청
        NexonAPIForbidden: 접근 금지
        Exception: API 요청 오류
        Exception: API 응답 오류
        Exception: 데이터 처리 오류
        Exception: 기타 오류
        Exception: 알 수 없는 오류

    Note:
        타임라인 기간: 이번주 목요일 오전 6시 ~ 현재시간 (최대 차주 목요일까지)
    """
    try:
        timeline_data: dict = get_dnf_weekly_timeline(server_name, character_name)
    except NeopleAPIError as e:
        if "API001" in str(e):
            await ctx.send(f"네오플 API 요청에 오류가 발생했어양!!!")
        elif "API002" in str(e):
            await ctx.send(f"네오플 API 요청 제한에 걸렸어양...")
        elif "API006" in str(e):
            await ctx.send(f"네오플 API 요청 파라미터가 잘못되었어양...")
        elif "DNF000" in str(e):
            await ctx.send(f"서버명이 잘못 입력 되었어양...")
        elif "DNF001" in str(e):
            await ctx.send(f"캐릭터 '{character_name}'을(를) 찾을 수 없어양...")
        elif "DNF900" in str(e):
            await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        elif "DNF901" in str(e):
            await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        elif "DNF980" in str(e):
            await ctx.send(f"현재 던전앤파이터 서비스 점검 중이에양!")
        elif "DNF999" in str(e):
            await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        else:
            await ctx.send(f"던전앤파이터 API에서 알 수 없는 오류가 발생했어양!")
        raise NeopleAPIError(str(e))
    except NeopleDNFInvalidTimelineParams as e:
        await ctx.send(f"타임라인을 불러오는데 문제가 발생했어양!")
        raise Exception(str(e))
    except NeopleDNFInvalidCharacterInfo as e:
        await ctx.send(f"캐릭터 '{character_name}'을(를) 찾을 수 없어양...")

    character_timeline: dict = timeline_data.get("timeline")
    timeline_rows: List[Dict[str, Any]] = character_timeline.get("rows")
    if len(timeline_rows) == 0:
        await ctx.send(f"이번주에 레전더리 이상 등급의 득템 기록이나, 레이드/레기온 클리어 기록이 없어양!")
        return
    
    else:
        # timeline 시간 내림차순으로 데이터가 정렬되어 있음

        # 캐릭터 기본 정보 추출
        adventure_name: str = timeline_data.get("adventureName", "몰라양")
        level: int = timeline_data.get("level", 0)
        job_name: str = timeline_data.get("jobName", "몰라양")
        job_grow_name: str = timeline_data.get("jobGrowName", "몰라양")
        fame: int = timeline_data.get("fame", 0)

        # timeline 데이터 생성
        timeline_title: str = f"{server_name}서버 '{character_name}' 모험가님의 이번주 주간던파에양!"
        timeline_highlight: str = ""
        get_legendary_count: int = 0
        get_epic_count: int = 0
        get_epic_up_count: int = 0 # 융합석 장비 업그레이드 횟수
        get_primeval_count: int = 0
        clear_raid_twilight_flag: bool = False
        clear_raid_nabel_flag: bool = False
        clear_raid_mu_flag: bool = False
        clear_raid_region_flag: bool = False

        # 타임라인 데이터 파싱
        for row in timeline_rows:
            timeline_code: int = row.get("code")
            timeline_name: str = row.get("name")
            timeline_date: str = row.get("date") #YYYY-MM-DD HH:MM
            timeline_data: dict[str, Any] = row.get("data")

            # 아이템 획득
            if 600 > timeline_code >= 500:
                item_name: str = timeline_data.get("itemName", "몰라양")
                item_rare: str = timeline_data.get("itemRarity", "몰라양")

                # 태초 아이템 획득 시 하이라이트 메시지 생성
                if timeline_code != 513 and item_rare == "태초":
                    channel_name = timeline_data.get("channelName", "알수없음")
                    channel_no = timeline_data.get("channelNo", "알수없음")
                    get_primeval_count += 1
                    timeline_highlight += (
                        f"{channel_name} {channel_no}채널에서 {dnf_convert_grade_text(item_rare)}{item_name} 아이템을 획득했어양! ({timeline_date})\n"
                    )

                if timeline_code == 513 and item_rare == "태초":
                    # 던전 카드 보상에서 태초 아이템 획득 시
                    dungeon_name: str = timeline_data.get("dungeonName", "몰라양")
                    get_primeval_count += 1
                    timeline_highlight += (
                        f"던전 {dungeon_name}에서 카드 보상으로 {dnf_convert_grade_text(item_rare)}{item_name} 아이템을 획득했어양! ({timeline_date})\n"
                    )

                # 융합석 업그레이드 획득 시 (에픽 획득 집계 미포함)
                if timeline_code == 511 and item_rare == "에픽":
                    get_epic_up_count += 1
                    timeline_highlight += (
                        f"융합석 업글레이드를 통해 {dnf_convert_grade_text(item_rare)}{item_name} 아이템을 획득했어양! ({timeline_date})\n"
                    )
                
                # 에픽 아이템 획득
                if item_rare == "에픽":
                    get_epic_count += 1

                # 레전더리 아이템 획득
                if item_rare == "레전더리":
                    get_legendary_count += 1

            if timeline_code == 209:
                # 레기온 클리어
                region_name: str = timeline_data.get("regionName", "몰라양")
                if region_name == "베누스":
                    clear_raid_region_flag = True
                    clear_raid_region_date = timeline_date

            if timeline_code == 201:
                # 레이드 클리어
                raid_name: str = timeline_data.get("raidName", "몰라양")
                if raid_name == "이내 황혼전":
                    clear_raid_twilight_flag = True
                    clear_raid_twilight_date = timeline_date
                if raid_name == "만들어진 신 나벨":
                    clear_raid_nabel_flag = True
                    clear_raid_nabel_date = timeline_date
                if raid_name == "아스라한":
                    clear_raid_mu_flag = True
                    clear_raid_mu_date = timeline_date

            # 아이템 증폭
            if timeline_code == 402:
                if "증폭" in timeline_name:
                    up_type = "증폭"
                elif "강화" in timeline_name:
                    up_type = "강화"
                elif "제련" in timeline_name:
                    up_type = "제련"
                else:
                    raise Exception("Invalid upgrade type in timeline data")
                
                up_item_rare: str = timeline_data.get("itemRarity", "몰라양")
                up_item_name: str = timeline_data.get("itemName", "몰라양")
                up_item_before: int = timeline_data.get("before", 0)
                up_item_after: int = timeline_data.get("after", 0)
                up_item_result: bool = timeline_data.get("result", False)
                up_item_safe: bool = timeline_data.get("safe", False)

                # 보호권 사용 여부 텍스트
                if up_item_safe:
                    up_safe_text: str = "증폭/강화 보호권 사용"
                else:
                    up_safe_text: str = "증폭/강화 보호권 미사용"

                if up_item_before >= 10:
                    # 10강 이상 증폭/강화 시 하이라이트 메시지 생성
                    timeline_highlight += (
                        f"{dnf_convert_grade_text(up_item_rare)} {up_item_name} {up_item_after} {up_type}에 "
                        f"{'성공' if up_item_result else '실패'} 했어양! ({timeline_date})\n"
                    )
                
                if up_item_after == 8 and up_type =="제련" and up_item_result:
                    # 8제련 성공 시 하이라이트 메시지 생성
                    timeline_highlight += (
                        f"{dnf_convert_grade_text(up_item_rare)} {up_item_name} 8 제련에 "
                        f"성공 했어양! ({timeline_date})\n"
                    )

        # 타임라인 요약 메시지 생성
        if timeline_highlight != "":
            timeline_highlight_str: str = f"**\-\-\- 주간 하이라이트 \-\-\-**\n{timeline_highlight}\n"
        else:
            timeline_highlight_str: str = ""

        clear_raid_twilight = dnf_get_clear_flag(clear_raid_twilight_flag, locals().get('clear_raid_twilight_date'))
        clear_raid_nabel = dnf_get_clear_flag(clear_raid_nabel_flag, locals().get('clear_raid_nabel_date'))
        clear_raid_mu = dnf_get_clear_flag(clear_raid_mu_flag, locals().get('clear_raid_mu_date'))
        clear_raid_region = dnf_get_clear_flag(clear_raid_region_flag, locals().get('clear_raid_region_date'))

        timeline_summary: str = (
            f"모험단명: {adventure_name}\n"
            f"레벨: {level}\n"
            f"직업: {job_name}, {job_grow_name}\n"
            f"명성: {fame:,}\n\n"
            f"**\-\-\- 이번주 장비 획득 \-\-\-**\n"
            f"🟢 태초 획득: {get_primeval_count}개\n"
            f"🟡 에픽 획득: {get_epic_count}개 (융합석 업글 {get_epic_up_count}회)\n"
            f"🟠 레전 획득: {get_legendary_count}개\n\n"
            f"**\-\-\- 레이드 및 레기온 클리어 현황 \-\-\-**\n"
            f"이내 황혼전 클리어: {clear_raid_twilight}\n"
            f"만들어진 신 나벨 클리어: {clear_raid_nabel}\n"
            f"아스라한 클리어: {clear_raid_mu}\n"
            f"베누스 레기온 클리어: {clear_raid_region}\n"
            f"\n{timeline_highlight_str}"
        )

        timeline_footer: str = (
            f"목요일 오전 6시 이후 집계\n"
            f"융합석 업그레이드는 에픽 획득에 포함되지 않아양\n"
            f"powered by Neople API"
        )

        # Discord Embed 객체 생성
        embed = discord.Embed(
            title=timeline_title,
            description=timeline_summary
        )
        embed.set_footer(text=timeline_footer)
        embed.colour = discord.Colour.from_rgb(128, 0, 128)  # purple
        await ctx.send(embed=embed)


@log_command
async def api_maple_fortune_today(ctx: commands.Context, character_name: str) -> None:
    """MapleStory 오늘의 운세 기능

    Args:
        ctx (commands.Context): Discord context
        character_name (str): 캐릭터 이름 -> OCID 변환

    Note:
        - today + OCID 조합으로 랜덤 고정 시드를 생성합니다
    """
    # 캐릭터 OCID 조회
    try:
        character_ocid: str = get_ocid(character_name)
    except NexonAPIError as e:
        if '400' in str(e):
            await ctx.send(f"캐릭터 '{character_name}'을 찾을 수 없어양!")
            raise NexonAPIBadRequest(f"Character '{character_name}' not found")
        if '403' in str(e):
            await ctx.send("Nexon Open API 접근 권한이 없어양!")
            raise NexonAPIForbidden("Forbidden access to API")
        if '429' in str(e):
            await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
            raise Exception("Too many requests to API")
        if '500' in str(e):
            await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
            raise Exception("Nexon Open API Internal server error")
    
    # OCID 데이터값 검증
    if not character_ocid:
        await ctx.send(f"캐릭터 '{character_name}'의 OCID를 찾을 수 없어양!")
        raise Exception(f"OCID not found for character: {character_name}")
    
    # 캐릭터 월드/생성일 확인
    try:
        basic_info_service_url: str = f"/maplestory/v1/character/basic"
        basic_info_request_url: str = f"{NEXON_API_HOME}{basic_info_service_url}?ocid={character_ocid}"
        basic_info_response_data: dict = general_request_handler_nexon(basic_info_request_url)
    except Exception as e:
        if '400' in str(e):
            await ctx.send(f"캐릭터 '{character_name}'의 상세 정보를 찾을 수 없어양!")
            raise Exception(f"Character '{character_name}' detail info not found")
        if '403' in str(e):
            await ctx.send("Nexon Open API 접근 권한이 없어양!")
            raise Exception("Forbidden access to API")
        if '429' in str(e):
            await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
            raise Exception("Too many requests to API")
        if '500' in str(e):
            await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
            raise Exception("Nexon Open API Internal server error")
    character_world: str = (
        str(basic_info_response_data.get('world_name')).strip()
        if basic_info_response_data.get('world_name') is not None
        else '알 수 없음'
    )
    character_date_create: str = (
        str(basic_info_response_data.get('character_date_create')).strip()
        if basic_info_response_data.get('character_date_create') is not None
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
    embed_footer: str = f"--- 주의 ---\n운세는 재미로만 확인해주세양!"

    embed = discord.Embed(
        title=embed_title,
        description=embed_description,
        color=discord.Colour.from_rgb(255, 215, 0)  # gold
    )
    embed.set_footer(text=embed_footer)
    await ctx.send(embed=embed)

@log_command
async def api_maple_xp_history(ctx: commands.Context, character_name: str) -> None:
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
        character_ocid: str = get_ocid(character_name)
    except NexonAPIBadRequest:
        await ctx.send(f"캐릭터 '{character_name}'을 찾을 수 없어양!")
    except NexonAPIForbidden:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
    except NexonAPITooManyRequests:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
    except NexonAPIServiceUnavailable:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
    except NexonAPIOCIDNotFound:
        await ctx.send(f"캐릭터 '{character_name}'의 OCID를 찾을 수 없어양!")

    xp_history_data: List[Tuple[str, int, str]] = []
    service_url: str = f"/maplestory/v1/character/basic"
    request_url: str = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}"

    try:
        response_data: dict = general_request_handler_nexon(request_url)
        xp_history_data: List[Tuple[str, int, str]] = get_weekly_xp_history(character_ocid)
    except NexonAPIBadRequest:
        await ctx.send(f"캐릭터 '{character_name}'의 기본 정보를 찾을 수 없어양!")
    except NexonAPIForbidden:
        await ctx.send("Nexon Open API 접근 권한이 없어양!")
    except NexonAPITooManyRequests:
        await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
    except NexonAPIServiceUnavailable:
        await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")

    # 캐릭터의 이름, 월드, 생성일 추출
    character_world: str = (
        str(response_data.get('world_name')).strip()
        if response_data.get('world_name') is not None
        else '알 수 없음'
    )
    character_date_create: str = (
        str(response_data.get('character_date_create')).strip()
        if response_data.get('character_date_create') is not None
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
            ax.bar(xi, bar_h, width=0.6, linewidth=0, zorder=2, alpha=0.7, color='#8FD19E')

            # 경험치 퍼센트 라벨 (실제 값 표시)
            ax.annotate(f"{yi:.3f}%", xy=(xi, bar_h), xytext=(0, 5),
                        textcoords="offset points",
                        ha="center", va="bottom",
                        fontsize=8, weight='bold', zorder=3)
            
            # 레벨 라벨
            ax.annotate(f"Lv.{lvl}", xy=(xi, bar_h), xytext=(0, -11),
                        textcoords="offset points",
                        ha="center", va="bottom",
                        fontsize=7, zorder=3)
            
        # 축/격자 스타일 설정
        ax.set_xticks(x, labels, fontsize=9)
        ylim_top = max(75.0, float(y.max())) * 1.35 + ylim_btm
        ax.set_ylim(0, ylim_top)
        ax.set_yticks([])
        ax.grid(axis="y", which="major", linewidth=0.6, alpha= 0.15, zorder=1)
        ax.axhline(0, linewidth=0.8, color="#666666", alpha=0.4)

        # 프레임 스타일 설정
        for spine in ["top", "right", "left"]:
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_alpha(0.4)
        ax.set_title(plot_title, fontsize=12, pad=8)

        buffer = io.BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight")
        plt.close(fig)
        buffer.seek(0)

        # Discord Embed 메시지 생성
        now_kst: str = datetime.now(tz=timezone("Asia/Seoul")).strftime("%Y%m%d")
        file = discord.File(buffer, filename=f"{character_ocid}_{now_kst}.png")
        await ctx.send(content=f"캐릭터 생성일: {character_date_create_str}", file=file)
        buffer.close()