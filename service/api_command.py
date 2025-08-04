"""

디스코드 봇에서 Nexon Open API를 사용하여 메이플스토리 관련 명령어를 처리하는 모듈

Reference: https://openapi.nexon.com/

"""

import discord
from discord.ext import commands

import requests
import io
from bs4 import BeautifulSoup
from urllib.parse import quote

from config import NEXON_API_HOME, NEXON_API_KEY
from service.common import log_command, parse_iso_string, preprocess_int_with_korean

from typing import Optional


def general_request_error_handler(response: requests.Response) -> None:
    """Nexon Open API의 일반적인 요청 오류를 처리하는 함수  
    특수한 오류가 있는 경우를 제외하고, 일반적인 오류에 대한 예외를 발생시킴  
    예외 처리 기준은 아래 Reference 링크를 참고

    Args:
        res (requests.Response): 요청 응답 객체

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14
    """
    response_status_code: str = str(response.status_code)
    exception_msg_prefix: str = f"{response_status_code} : "
    response_data: dict = response.json()
    exception_msg: dict = response_data.get('error')
    if response.status_code == 400:
        default_exception_msg = "Bad Request"
    elif response.status_code == 403:
        default_exception_msg = "Forbidden"
    elif response.status_code == 429:
        default_exception_msg = "Too Many Requests"
    elif response.status_code == 500:
        default_exception_msg = "Internal Server Error"
    else:
        default_exception_msg = "Unknown Error"

    raise Exception(f"{exception_msg_prefix}{str(exception_msg.get('name', default_exception_msg))}")


def general_request_handler(request_url: str, headers: Optional[dict] = None) -> dict:
    """Nexon Open API의 일반적인 요청을 처리하는 함수  
    요청 URL과 헤더를 받아서 GET 요청을 수행하고, 응답 데이터를 반환함

    Args:
        request_url (str): 요청할 URL
        headers (Optional[dict], optional): 요청 헤더. Defaults to None.

    Returns:
        dict: 응답 데이터

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    if headers is None:
        headers = {
            "x-nxopen-api-key": NEXON_API_KEY,
        }
    
    response = requests.get(url=request_url, headers=headers)
    
    if response.status_code != 200:
        general_request_error_handler(response)
    return response.json()

def get_ocid(character_name: str) -> str:
    """character_name의 OCID를 검색

    Args:
        character_name (str): 캐릭터 이름
        캐릭터 이름을 base64로 인코딩하여 Nexon Open API를 통해 OCID를 검색

    Returns:
        str: OCID (string)

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=14

    Raises:
        Reference에 있는 URL 참조
        (예외처리는 함수 밖에서 처리)
    """
    service_url = f"/maplestory/v1/id"
    url_encode_name: str = quote(character_name)
    request_url = f"{NEXON_API_HOME}{service_url}?character_name={url_encode_name}"
    response_data: dict = general_request_handler(request_url)
    
    # 정상적으로 OCID를 찾았을 때
    ocid: str = str(response_data.get('ocid'))
    if ocid:
        return ocid
    else:
        raise Exception("OCID not found in response")


def get_character_popularity(ocid: str) -> str:
    """OCID에 해당하는 캐릭터의 인기도를 가져오는 함수

    Args:
        ocid (str): 캐릭터 OCID

    Returns:
        str: 캐릭터의 인기도

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    service_url = f"/maplestory/v1/character/popularity"
    request_url = f"{NEXON_API_HOME}{service_url}?ocid={ocid}"
    try:
        response_data: dict = general_request_handler(request_url)

        popularity: int = response_data.get('popularity', "몰라양")
        return popularity
    except Exception as e:

        return "몰라양"  # 예외 발생 시 기본값으로 "몰라양" 반환


def get_notice(target_event: str = None) -> list[dict]:
    """Nexon Open API를 통해 메이플스토리 공지사항을 가져오는 함수

    Args:
        target_event (str, optional): 특정 이벤트에 대한 공지사항을 필터링할 수 있음. 기본값은 None.

    Returns:
        list[dict]: 공지사항 목록

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴

    Reference:
        https://openapi.nexon.com/ko/game/maplestory/?id=24
    """
    service_url = f"/maplestory/v1/notice-event"
    request_url = f"{NEXON_API_HOME}{service_url}"
    response_data: dict = general_request_handler(request_url)
    notices: list = response_data.get('event_notice', [])
    if target_event is None:
        notice_filter = None
    elif target_event == "pcbang":
        notice_filter = "PC방"
    elif target_event == "sunday":
        notice_filter = "썬데이"

    # 특정 이벤트에 대한 공지사항 필터링
    if target_event:
        notices = [notice for notice in notices if notice_filter in notice.get('title', '')]

    return notices


def get_notice_details(notice_id: str) -> dict:
    """Nexon Open API를 통해 특정 공지사항의 상세 정보를 가져오는 함수

    Args:
        notice_id (str): 공지사항 ID

    Returns:
        dict: 공지사항 상세 정보

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    service_url = f"/maplestory/v1/notice-event/detail"
    request_url = f"{NEXON_API_HOME}{service_url}?notice_id={notice_id}"
    response_data: dict = general_request_handler(request_url)
    return response_data


def get_image_bytes(image_url: str) -> bytes:
    """이미지 URL로부터 이미지 바이트를 가져오는 함수

    Args:
        image_url (str): 이미지 URL

    Returns:
        bytes: 이미지 바이트

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    response = requests.get(image_url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch image from {image_url}")
    else:
        image_bytes = io.BytesIO(response.content)
    
    return image_bytes

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
    except Exception as e:
        if '400' in str(e):
            await ctx.send(f"캐릭터 '{character_name}'을 찾을 수 없어양!")
            raise Exception(f"Character '{character_name}' not found")
        if '403' in str(e):
            await ctx.send("Nexon Open API 접근 권한이 없어양!")
            raise Exception("Forbidden access to API")
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
    
    service_url: str = f"/maplestory/v1/character/basic"
    request_url: str = f"{NEXON_API_HOME}{service_url}?ocid={character_ocid}"
    # 예외 처리 (자세한 내용은 Reference 참고)
    try:
        response_data: dict = general_request_handler(request_url)
    except Exception as e:
        if '400' in str(e):
            await ctx.send(f"캐릭터 '{character_name}'의 기본 정보를 찾을 수 없어양!")
            raise Exception(f"Character '{character_name}' basic info not found")
        if '403' in str(e):
            await ctx.send("Nexon Open API 접근 권한이 없어양!")
            raise Exception("Forbidden access to API")
        if '429' in str(e):
            await ctx.send("API 요청이 너무 많아양! 잠시 후 다시 시도해보세양")
            raise Exception("Too many requests to API")
        if '500' in str(e):
            await ctx.send("Nexon Open API 서버에 오류가 발생했거나 점검중이에양")
            raise Exception("Nexon Open API Internal server error")

    # 정상적으로 캐릭터 기본 정보를 찾았을 때
    # 캐릭터 기본 정보 1 - 캐릭터 이름
    character_name: str = response_data.get('character_name')
    if not character_name:
        await ctx.send(f"캐릭터 이름이 '{character_name}'인 캐릭터가 없어양!")
        raise Exception(f"Character basic info not found for: {character_name}")
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
        - 캐릭터 능력치: 스탯 공격력
        - 캐릭터 능력치: 스탯수치
        - 캐릭터 능력치: 전투 능력치(보공, 크뎀, 방무, 벞지, 쿨감, 미사용)
        - 캐릭터 능력치: 전투력

    Args:
        ctx (commands.Context): Discord 명령어 컨텍스트
        character_name (str): 캐릭터 이름 -> OCID 변환

    Returns:
        discord.ui.View: 캐릭터의 상세 정보를 보여주는 View 객체

    Raises:
        Exception: 요청 오류에 대한 예외를 발생시킴
    """
    # 캐릭터의 OCID 조회
    try:
        character_ocid: str = get_ocid(character_name)
    except Exception as e:
        if '400' in str(e):
            await ctx.send(f"캐릭터 '{character_name}'을 찾을 수 없어양!")
            raise Exception(f"Character '{character_name}' not found")
        if '403' in str(e):
            await ctx.send("Nexon Open API 접근 권한이 없어양!")
            raise Exception("Forbidden access to API")
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