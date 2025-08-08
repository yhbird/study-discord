"""

디스코드 봇에서 Nexon Open API를 사용하여 메이플스토리 관련 명령어를 처리하는 모듈

Reference: https://openapi.nexon.com/

"""

import discord
from discord.ext import commands

from bs4 import BeautifulSoup
from urllib.parse import quote

from service.common import log_command, parse_iso_string, preprocess_int_with_korean
from service.api_utils import *
from config import NEXON_API_HOME

@log_command
async def api_basic_info(ctx: commands.Context, character_name: str):
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
        response_data: dict = general_request_handler(request_url)
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
    character_level: int = response_data.get('character_level', 0)
    # 캐릭터 기본 정보 3 - 캐릭터 소속월드
    character_world: str = response_data.get('world_name', '알 수 없음')
    # 캐릭터 기본 정보 4 - 캐릭터 성별
    character_gender: str = response_data.get('character_gender', '알 수 없음')
    # 캐릭터 기본 정보 5 - 캐릭터 직업(차수)
    character_class: str = response_data.get('character_class', '알 수 없음')
    character_class_level: str = response_data.get('character_class_level', '알 수 없음')
    # 캐릭터 기본 정보 6 - 경험치
    character_exp: int = response_data.get('character_exp', 0)
    character_exp_rate: str = response_data.get('character_exp_rate', "0.000%")
    # 캐릭터 기본 정보 7 - 소속길드
    character_guild_name: str = response_data.get('character_guild_name', '알 수 없음')
    # 캐릭터 기본 정보 8 - 캐릭터 외형 이미지 (기본값에 기본 이미지가 들어가도록 수정예정)
    character_image: str = response_data.get('character_image', '알 수 없음')
    # 캐릭터 기본 정보 9 - 캐릭터 생성일 "2023-12-21T00:00+09:00"
    character_date_create: str = response_data.get('character_date_create', '알 수 없음')
    # 캐릭터 기본 정보 10 - 캐릭터 최근 접속 여부 (7일 이내 접속 여부)
    character_access_flag: str = response_data.get('access_flag', '알 수 없음')
    # 캐릭터 기본 정보 11 - 캐릭터 해방 퀘스트 완료 여부
    character_liberation_quest_clear: str = response_data.get('liberation_quest_clear', '알 수 없음')

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
        character_liberation_quest_clear = "알 수 없음"

    if character_image != '알 수 없음':
        character_image_url: str = f"{character_image}?action=A00.2&emotion=E00&width=200&height=200"
    
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
async def api_pcbang_notice(ctx: commands.Context):
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
        notice_title: str = notice_data.get('title', '알 수 없음')
        notice_url: str = notice_data.get('url', '알 수 없음')
        notice_id: str = notice_data.get('notice_id', '알 수 없음')

        # 공지사항 날짜 정보 예시 "2025-07-17T10:00+09:00" -> "2025년 7월 17일 10:00 (KST)"
        notice_date: str = notice_data.get('date', '알 수 없음')
        notice_start_date: str = notice_data.get('date_event_start', '알 수 없음')
        notice_end_date: str = notice_data.get('date_event_end', '알 수 없음')

        footer_notice_date: str = parse_iso_string(notice_date)
        footer_notice_start_date: str = parse_iso_string(notice_start_date)
        footer_notice_end_date: str = parse_iso_string(notice_end_date)
        footer_notice_text: str = (
            f"공지사항 날짜: {footer_notice_date}\n"
        )

        # 공지사항 이미지 URL 추출
        notice_detail_data: dict = get_notice_details(notice_id)
        notice_contents: str = notice_detail_data.get('contents', '알 수 없음')
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
            notice_image_bytes: bytes = get_image_bytes(image_url)
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

    # 공지사항이 없을 때
    else:
        await ctx.send("PC방 이벤트 공지사항이 없어양!")

@log_command
async def api_sunday_notice(ctx: commands.Context):
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
        notice_title: str = notice_data.get('title', '알 수 없음')
        notice_url: str = notice_data.get('url', '알 수 없음')
        notice_id: str = notice_data.get('notice_id', '알 수 없음')

        # 공지사항 날짜 정보 예시 "2025-07-17T10:00+09:00" -> "2025년 7월 17일 10:00 (KST)"
        notice_date: str = notice_data.get('date', '알 수 없음')
        notice_start_date: str = notice_data.get('date_event_start', '알 수 없음')
        notice_end_date: str = notice_data.get('date_event_end', '알 수 없음')

        footer_notice_date: str = parse_iso_string(notice_date)
        footer_notice_start_date: str = parse_iso_string(notice_start_date)
        footer_notice_end_date: str = parse_iso_string(notice_end_date)
        footer_notice_text: str = (
            f"공지사항 날짜: {footer_notice_date}\n"
        )

        # 공지사항 이미지 URL 추출
        notice_detail_data: dict = get_notice_details(notice_id)
        notice_contents: str = notice_detail_data.get('contents', '알 수 없음')
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
            notice_image_bytes: bytes = get_image_bytes(image_url)
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

    # 공지사항이 없을 때
    else:
        await ctx.send("썬데이 이벤트 공지사항이 아직 없어양!!\n매주 금요일 오전 10시에 업데이트 되니 참고해양!!")

@log_command
async def api_detail_info(ctx: commands.Context, character_name: str):
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
        basic_info_response_data: dict = general_request_handler(basic_info_request_url)
        detail_info_response_data: dict = general_request_handler(detail_info_request_url)
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
    character_level: int = basic_info_response_data.get('character_level', 0)
    # 캐릭터 상세 정보 3 - 캐릭터 소속월드
    character_world: str = basic_info_response_data.get('world_name', '알 수 없음')
    # 캐릭터 상세 정보 4 - 캐릭터 성별
    character_gender: str = basic_info_response_data.get('character_gender', '알 수 없음')
    # 캐릭터 상세 정보 5 - 캐릭터 직업(차수)
    character_class: str = basic_info_response_data.get('character_class', '알 수 없음')
    character_class_level: str = basic_info_response_data.get('character_class_level', '알 수 없음')
    # 캐릭터 상세 정보 6 - 경험치
    character_exp: int = basic_info_response_data.get('character_exp', 0)
    character_exp_rate: str = basic_info_response_data.get('character_exp_rate', "0.000%")
    # 캐릭터 상세 정보 7 - 소속길드
    character_guild_name: str = basic_info_response_data.get('character_guild_name', '알 수 없음')
    # 캐릭터 상세 정보 8 - 캐릭터 외형 이미지 (기본값에 기본 이미지가 들어가도록 수정예정)
    character_image: str = basic_info_response_data.get('character_image', '알 수 없음')
    if character_image != '알 수 없음':
        character_image_url: str = f"{character_image}?action=A00.2&emotion=E00&width=200&height=200"
    # 캐릭터 상세 정보 9 - 캐릭터 생성일 "2023-12-21T00:00+09:00"
    character_date_create: str = basic_info_response_data.get('character_date_create', '알 수 없음')
    if character_date_create != '알 수 없음':
        character_date_create = character_date_create.split("T")[0]  # "2023-12-21" 형태로 변환
        character_date_create_ymd = character_date_create.split("-")
        character_date_create_str: str = (
            f"{int(character_date_create_ymd[0])}년 "
            f"{int(character_date_create_ymd[1])}월 "
            f"{int(character_date_create_ymd[2])}일"
        )
    # 캐릭터 상세 정보 10 - 캐릭터 최근 접속 여부 (7일 이내 접속 여부)
    character_access_flag: str = basic_info_response_data.get('access_flag', '알 수 없음')
    if character_access_flag == "true":
        character_access_flag = "최근 7일 이내 접속함"
    else:
        character_access_flag = "최근 7일 이내 접속하지 않음"
    
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
    character_stat_attack: str = stat_info.get('최대 스탯공격력', '몰라양')
    if character_stat_attack != '몰라양':
        character_stat_attack = preprocess_int_with_korean(character_stat_attack)
    # 캐릭터 상세 정보 12 - 캐릭터 능력치: 데미지(%) "175.00" -> "175.00%"
    character_stat_damage: str = stat_info.get('데미지', '0.00%')
    if character_stat_damage != '0.00%':
        character_stat_damage = f"{character_stat_damage}%"
    # 캐릭터 상세 정보 13 - 캐릭터 능력치: 보스 공격력(%) "50.00" -> "50.00%"
    character_stat_boss_attack: str = stat_info.get('보스 몬스터 데미지', '0.00%')
    if character_stat_boss_attack != '0.00%':
        character_stat_boss_attack = f"{character_stat_boss_attack}%"
    # 캐릭터 상세 정보 14 - 캐릭터 능력치: 크리티컬 데미지(%) "50.00" -> "50.00%"
    character_stat_critical_damage: str = stat_info.get('크리티컬 데미지', '0.00%')
    if character_stat_critical_damage != '0.00%':
        character_stat_critical_damage = f"{character_stat_critical_damage}%"
    # 캐릭터 상세 정보 15 - 캐릭터 능력치: 방어율 무시(%) "50.00" -> "50.00%"
    character_stat_ignore_defense: str = stat_info.get('방어율 무시', '0.00%')
    if character_stat_ignore_defense != '0.00%':
        character_stat_ignore_defense = f"{character_stat_ignore_defense}%"
    # 캐릭터 상세 정보 16 - 캐릭터 능력치: 스타포스
    character_stat_starforce: str = stat_info.get('스타포스', '0')
    if character_stat_starforce != '0':
        character_stat_starforce = f"총합 {character_stat_starforce}성"
    # 캐릭터 상세 정보 17 - 캐릭터 능력치: 아케인포스
    character_stat_arcaneforce: str = stat_info.get('아케인포스', '0')
    # 캐릭터 상세 정보 18 - 캐릭터 능력치: 어센틱포스
    character_stat_authenticforce: str = stat_info.get('어센틱포스', '0')
    # 캐릭터 상세 정보 19 - 캐릭터 능력치: 스탯(힘, 덱, 인트, 럭) "1000" -> "1,000"
    character_stat_str: str = f"{int(stat_info.get('STR', '0')):,}"
    character_stat_dex: str = f"{int(stat_info.get('DEX', '0')):,}"
    character_stat_int: str = f"{int(stat_info.get('INT', '0')):,}"
    character_stat_luk: str = f"{int(stat_info.get('LUK', '0')):,}"
    character_stat_hp: str = f"{int(stat_info.get('HP', '0')):,}"
    character_stat_mp: str = f"{int(stat_info.get('MP', '0')):,}"
    character_stat_ap_str: str = f"{int(stat_info.get('AP 배분 STR', '0')):,}"
    character_stat_ap_dex: str = f"{int(stat_info.get('AP 배분 DEX', '0')):,}"
    character_stat_ap_int: str = f"{int(stat_info.get('AP 배분 INT', '0')):,}"
    character_stat_ap_luk: str = f"{int(stat_info.get('AP 배분 LUK', '0')):,}"
    character_stat_ap_hp : str = stat_info.get('AP 배분 HP', '0')
    if int(character_stat_ap_hp) < 0:
        character_stat_ap_hp: str = '0'
    character_stat_ap_hp = f"{int(character_stat_ap_hp):,}"
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
    # 캐릭터 상세 정보 22 - 캐릭터 능력치: 공마
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
        f"\n**\-\-\- 능력치 \-\-\-**\n"
        f"**STR**: {character_stat_str} ({character_stat_ap_str})\n"
        f"**DEX**: {character_stat_dex} ({character_stat_ap_dex})\n"
        f"**INT**: {character_stat_int} ({character_stat_ap_int})\n"
        f"**LUK**: {character_stat_luk} ({character_stat_ap_luk})\n"
        f"**HP**: {character_stat_hp} ({character_stat_ap_hp})\n"
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
async def api_weather_v1(message: discord.Message):
    """현재 지역의 날씨 정보를 가져오는 명령어 v1

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트
        location_name (str): 날씨 정보를 가져올 지역명/주소

    Returns:
        discord.ui.Embed: 날씨 정보를 담은 Embed 객체

    Raises:
        Exception : 지역정보 조회, 날씨 조회 실패 시 발생

    Reference:
        [지역 정보 조회 API (KAKAO developers)](https://developers.kakao.com/docs/latest/ko/local/dev-guide#search-by-address)
        [날씨 조회 API (Data.go.kr)](https://www.data.go.kr/data/15084084/openapi.do)
    """
    command_prefix: str = "븜 날씨 "
    if message.author.bot:
        return
    
    if message.content.startswith(command_prefix):
        location_name: str = message.content[len(command_prefix):]
    
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
        await message.channel.send(f"해당 지역의 정보를 검색하는 중에 오류가 발생했어양!")
        raise KakaoAPIError(str(e))
    except KKO_NO_LOCAL_INFO as e:
        await message.channel.send(f"해당 지역의 정보를 찾을 수 없어양!")
        raise KakaoAPIError(str(e))

    try:
        # 날씨 정보 조회
        weather_info = get_weather_info(local_x, local_y)
    except WTH_API_INTERNAL_ERROR:
        await message.channel.send(f"날씨 정보를 가져오는 중에 오류가 발생했어양!")
    except WTH_API_DATA_ERROR:
        await message.channel.send(f"날씨 API 데이터에 문제가 발생했어양!")
    except WTH_API_DATA_NOT_FOUND:
        await message.channel.send(f"해당 지역의 날씨 정보를 찾을 수 없어양!")
    except WTH_API_HTTP_ERROR:
        await message.channel.send(f"날씨 API 요청 중에 오류가 발생했어양!")
    except WTH_API_TIMEOUT:
        await message.channel.send(f"날씨 데이터 가져오는데 시간이 초과되었어양!")
    except WTH_API_INVALID_PARAMS:
        await message.channel.send(f"날씨 API 요청 파라미터가 잘못되었어양!")
    except WTH_API_INVALID_REGION:
        await message.channel.send(f"해당 지역은 날씨 API에서 지원하지 않아양!")
    except WTH_API_DEPRECATED:
        await message.channel.send(f"더 이상 지원되지 않는 기능이에양!")
    except WTH_API_UNAUTHORIZED:
        await message.channel.send(f"날씨 API 서비스 접근 권한이 없어양!")
    except WTH_API_KEY_TEMP_ERROR:
        await message.channel.send(f"날씨 API 키가 임시로 제한되었어양!")
    except WTH_API_KEY_LIMIT_EXCEEDED:
        await message.channel.send(f"날씨 API 키의 요청 한도를 초과했어양!")
    except WTH_API_KEY_INVALID:
        await message.channel.send(f"날씨 API 키가 유효하지 않아양!")
    except WTH_API_KEY_EXPIRED:
        await message.channel.send(f"날씨 API 키가 만료되었어양!")
    except WeatherAPIError:
        await message.channel.send(f"날씨 API 요청 중에 오류가 발생했어양!")
    except Exception as e:
        await message.channel.send(f"날씨 정보를 가져오는 중에 알 수 없는 오류가 발생했어양!")
        raise WeatherAPIError(str(e))

    # 날씨 데이터 전처리
    weather_data = process_weather_data(weather_info)
    current_date = weather_data.get('기준시간', '몰라양')
    current_temp = weather_data.get('기온', '몰라양')
    current_humidity = weather_data.get('습도', '몰라양')
    current_wind_speed = weather_data.get('풍속', '몰라양')
    current_wind_direction = weather_data.get('풍향', '몰라양')
    current_rain_1h = weather_data.get('1시간강수량_수치')
    if current_rain_1h == "0":
        current_rain_flag: bool = False
    else:
        current_rain_flag: bool = True
    
    # 비가오는 경우 강수 정보 메세지 생성
    if current_rain_flag:
        current_rain_type: str = weather_data.get('1시간강수량_정성')
        current_rain_show: str = weather_data.get('1시간강수량_표시')
        current_rain_float: float = float(current_rain_1h)
        if current_rain_float >= 30 and current_rain_float < 50:
            current_rain_float_text = "들풍과 천둥, 번개를 동반한 비가 내릴 수 있어양."
        elif current_rain_float >= 50 and current_rain_float < 70:
            current_rain_float_text = "도로가 침수될 수 있고, 차량 운행이 어려울 수 있어양."
        elif current_rain_float >= 70:
            current_rain_float_text = "심각한 피해가 발생할 수 있어양. 이불 밖은 위험해양!"
        else:
            current_rain_float_text = "우산을 챙기세양. 비가 내릴 수 있어양."
        current_rain_desc: str = (
            f"현재 1시간 강수량이 {current_rain_1h}mm 이에양.\n"
            f"{current_rain_float_text}"
        )
        current_rain: str = (
            f"**1시간 강수량**: {current_rain_type} ({current_rain_show})\n"
        )
    else:
        current_rain_desc: str = ""
        current_rain: str = f""

    # Embed 메시지 생성
    embed_title: str = f"{local_address_name}의 현재 날씨 정보에양!"
    embed_description: str = (
        f"**현재 기온**: {current_temp}\n"
        f"**현재 습도**: {current_humidity}\n"
        f"**현재 풍속**: ({current_wind_direction}풍) {current_wind_speed}\n"
        f"**강수 여부**: {weather_data['강수형태']}\n"
        f"{current_rain}"
    )
    embed_footer: str = (
        f"정보 제공: Kakao Local API | Data.go.kr\n"
        f"제공 날짜: {current_date}\n(날씨 정보 10분 단위 갱신)\n"
    )

    embed = discord.Embed(
        title=embed_title,
        description=embed_description,
        color=discord.Colour.from_rgb(135, 206, 235)  # 하늘색
    )
    embed.set_footer(text=embed_footer)
    
    if current_rain_flag:
        await message.channel.send(embed=embed, content=current_rain_desc)
    else:
        await message.channel.send(embed=embed)
