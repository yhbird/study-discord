import discord
from discord.ext import commands
from discord.ui import View, Button

import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

from config import NEXON_API_HOME, NEXON_API_KEY_LIVE, NEXON_API_KEY_TEST
from service.common import log_command, parse_iso_string

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
    """
    service_url = f"/maplestory/v1/id"
    url_encode_name = quote(character_name)
    request_url = f"{NEXON_API_HOME}{service_url}?character_name={url_encode_name}"
    request_headers = {
        "x-nxopen-api-key": NEXON_API_KEY_LIVE,
    }
    response = requests.get(
        url=request_url,
        headers=request_headers
    )
    response_data: dict = response.json()

    # 예외 처리 (자세한 내용은 Reference 참고)
    if response.status_code != 200:
        general_request_error_handler(response)
    
    # 정상적으로 OCID를 찾았을 때
    else:
        ocid: str = str(response_data.get('ocid'))
        if ocid:
            return ocid
        else:
            raise Exception("OCID not found in response")


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
    request_headers = {
        "x-nxopen-api-key": NEXON_API_KEY_TEST,
    }
    response = requests.get(
        url=request_url,
        headers=request_headers
    )
    
    # 예외 처리 (자세한 내용은 Reference 참고)
    if response.status_code != 200:
        general_request_error_handler(response)
    else:
        response_data: dict = response.json()
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
    request_headers = {
        "x-nxopen-api-key": NEXON_API_KEY_TEST,
    }
    response = requests.get(
        url=request_url,
        headers=request_headers
    )
    
    if response.status_code != 200:
        general_request_error_handler(response)

    return response.json()

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
    request_headers = {
        "x-nxopen-api-key": NEXON_API_KEY_LIVE,
    }
    response = requests.get(
        url=request_url,
        headers=request_headers
    )
    response_data: dict = response.json()

    # 정상적으로 캐릭터 기본 정보를 찾았을 때
    if response.status_code == 200:
        # 캐릭터 기본 정보 1 - 캐릭터 이름
        character_name: str = response_data.get('character_name')
        if not character_name:
            await ctx.send(f"캐릭터 '{character_name}'의 기본 정보를 찾을 수 없어양!")
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
    # 예외 처리 (자세한 내용은 Reference 참고)
    else:
        general_request_error_handler(response)

    # Basic Info 데이터 전처리
    if character_date_create != '알 수 없음':
        character_date_create = character_date_create.split("T")[0]  # "2023-12-21" 형태로 변환
        character_date_create_ymd = character_date_create.split("-")
        character_date_create_str: str = ""
        character_date_create_str += f"{int(character_date_create_ymd[0])}년 "
        character_date_create_str += f"{int(character_date_create_ymd[1])}월 "
        character_date_create_str += f"{int(character_date_create_ymd[2])}일"

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
        f"**직업:** {character_class} ({character_class_level}차 전직)\n"
        f"**길드:** {character_guild_name}\n"
        f"**경험치: ** {character_exp_str}\n"
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
        await ctx.send(f"PC방 이벤트 공지사항을 가져오는 데 실패했어양!")
        raise Exception(f"Failed to load pcbang notice: {str(e)}")
    
    # 공지사항 데이터 전처리
    print(notice_data)
    if notice_data:
        notice_data: dict = notice_data[0]  # 가장 최근 공지사항 1개

        # 공지사항 제목, 링크, 내용(HTML)
        notice_title: str = notice_data.get('title', '알 수 없음')
        notice_url: str = notice_data.get('url', '알 수 없음')
        notice_description: str = "프리미엄 PC방 이벤트 공지사항이에양!!!\n"
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

        # Embed 메시지 생성
        embed_description: str = (
            f"{notice_description}\n"
            f"[🔗 공지사항 이동]({notice_url})\n"
            f"[🔗 이미지 원본 (이미지가 잘 안보이면 클릭!)]({image_url})\n"
            f"**이벤트 시작일:** {footer_notice_start_date}\n"
            f"**이벤트 종료일:** {footer_notice_end_date}\n"
        )
        embed = discord.Embed(title=notice_title, description=embed_description)
        if image_url != '알 수 없음':
            embed.set_image(url=image_url)
        embed.url = notice_url
        embed.set_footer(text=footer_notice_text)
        embed.colour = discord.Colour.from_rgb(239, 111, 148)
        await ctx.send(embed=embed)

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
        await ctx.send(f"썬데이 이벤트 공지사항을 가져오는 데 실패했어양!")
        raise Exception(f"Failed to load sunday notice: {str(e)}")

    # 공지사항 데이터 전처리
    if notice_data:
        notice_data: dict = notice_data[0] # 가장 최근 공지사항 1개

        # 공지사항 제목, 링크, 내용(HTML)
        notice_title: str = notice_data.get('title', '알 수 없음')
        notice_url: str = notice_data.get('url', '알 수 없음')
        notice_description: str = "썬데이 이벤트 공지사항이에양!!!\n"
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

        # Embed 메시지 생성
        embed_description: str = (
            f"{notice_description}\n"
            f"[🔗 공지사항 이동]({notice_url})\n"
            f"[🔗 이미지 원본 (이미지가 잘 안보이면 클릭!)]({image_url})\n"
            f"**이벤트 시작일:** {footer_notice_start_date}\n"
            f"**이벤트 종료일:** {footer_notice_end_date}\n"
        )
        embed = discord.Embed(title=notice_title, description=embed_description)
        if image_url != '알 수 없음':
            embed.set_image(url=image_url)
        embed.url = notice_url
        embed.set_footer(text=footer_notice_text)
        embed.colour = discord.Colour.from_rgb(239, 111, 148)
        await ctx.send(embed=embed)

    # 공지사항이 없을 때
    else:
        await ctx.send("썬데이 이벤트 공지사항이 아직 없어양!!\n매주 금요일 오전 10시에 업데이트 되니 참고해양!!")