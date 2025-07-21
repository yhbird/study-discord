import discord
from discord.ext import commands
from discord.ui import View, Button

import requests
from urllib.parse import quote

from config import NEXON_API_HOME, NEXON_API_KEY_LIVE
from service.common import log_command

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
    res = requests.get(
        url=request_url,
        headers=request_headers
    )
    result_data: dict = res.json()

    # 예외 처리 (자세한 내용은 Reference 참고)
    res_status_code: str = str(res.status_code)
    exception_msg_prefix: str = f"{res_status_code} : "
    if res.status_code == 400:
        error_message: dict = result_data.get('error')
        default_error_message = "Bad Request"
        raise Exception(f"{exception_msg_prefix}{str(error_message.get('name', default_error_message))}")
    elif res.status_code == 403:
        error_message: dict = result_data.get('error')
        default_error_message = "Forbidden"
        raise Exception(f"{exception_msg_prefix}{str(error_message.get('name', default_error_message))}")
    elif res.status_code == 429:
        error_message: dict = result_data.get('error')
        default_error_message = "Too Many Requests"
        raise Exception(f"{exception_msg_prefix}{str(error_message.get('name', default_error_message))}")
    elif res.status_code == 500:
        error_message: dict = result_data.get('error')
        default_error_message = "Internal Server Error"
        raise Exception(f"{exception_msg_prefix}{str(error_message.get('name', default_error_message))}")

    # 정상적으로 OCID를 찾았을 때
    if res.status_code == 200:
        ocid: str = str(result_data.get('ocid'))
        if ocid:
            return ocid
        else:
            raise Exception("OCID not found in response")

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
    res = requests.get(
        url=request_url,
        headers=request_headers
    )
    result_data: dict = res.json()

    # 예외 처리 (자세한 내용은 Reference 참고)
    res_status_code: str = str(res.status_code)
    exception_msg_prefix: str = f"{res_status_code} : "
    if res.status_code == 400:
        error_message: dict = result_data.get('error')
        default_error_message = "Bad Request"
        raise Exception(f"{exception_msg_prefix}{str(error_message.get('name', default_error_message))}")
    elif res.status_code == 403:
        error_message: dict = result_data.get('error')
        default_error_message = "Forbidden"
        raise Exception(f"{exception_msg_prefix}{str(error_message.get('name', default_error_message))}")
    elif res.status_code == 429:
        error_message: dict = result_data.get('error')
        default_error_message = "Too Many Requests"
        raise Exception(f"{exception_msg_prefix}{str(error_message.get('name', default_error_message))}")
    elif res.status_code == 500:
        error_message: dict = result_data.get('error')
        default_error_message = "Internal Server Error"
        raise Exception(f"{exception_msg_prefix}{str(error_message.get('name', default_error_message))}")
    
    # 정상적으로 캐릭터 기본 정보를 찾았을 때
    if res.status_code == 200:
        # 캐릭터 기본 정보 1 - 캐릭터 이름
        character_name: str = result_data.get('character_name')
        if not character_name:
            await ctx.send(f"캐릭터 '{character_name}'의 기본 정보를 찾을 수 없어양!")
            raise Exception(f"Character basic info not found for: {character_name}")
        # 캐릭터 기본 정보 2 - 캐릭터 레벨
        character_level: int = result_data.get('character_level', 0)
        # 캐릭터 기본 정보 3 - 캐릭터 소속월드
        character_world: str = result_data.get('world_name', '알 수 없음')
        # 캐릭터 기본 정보 4 - 캐릭터 성별
        character_gender: str = result_data.get('character_gender', '알 수 없음')
        # 캐릭터 기본 정보 5 - 캐릭터 직업(차수)
        character_class: str = result_data.get('character_class', '알 수 없음')
        character_class_level: str = result_data.get('character_class_level', '알 수 없음')
        # 캐릭터 기본 정보 6 - 경험치
        character_exp: int = result_data.get('character_exp', 0)
        character_exp_rate: str = result_data.get('character_exp_rate', "0.000%")
        # 캐릭터 기본 정보 7 - 소속길드
        character_guild_name: str = result_data.get('character_guild_name', '알 수 없음')
        # 캐릭터 기본 정보 8 - 캐릭터 외형 이미지 (기본값에 기본 이미지가 들어가도록 수정예정)
        character_image: str = result_data.get('character_image', '알 수 없음')
        # 캐릭터 기본 정보 9 - 캐릭터 생성일 "2023-12-21T00:00+09:00"
        character_date_create: str = result_data.get('character_date_create', '알 수 없음')
        # 캐릭터 기본 정보 10 - 캐릭터 최근 접속 여부 (7일 이내 접속 여부)
        character_access_flag: str = result_data.get('access_flag', '알 수 없음')
        # 캐릭터 기본 정보 11 - 캐릭터 해방 퀘스트 완료 여부
        character_liberation_quest_clear: str = result_data.get('liberation_quest_clear', '알 수 없음')

    # Basic Info 전처리 후
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

    character_image_url: str = f"{character_image}?action=A00.2&emotion=E00&width=200&height=200"
    
    # Embed 메시지 생성
    embed_title: str = f"{character_world}월드의 '{character_name}' 용사님의 기본 정보에양!!"
    maple_scouter_url: str = f"https://maplescouter.com/info?name={character_name_quote}"
    embed_description: str = f"[🔗 환산 사이트 이동]({maple_scouter_url})\n"
    embed_description += f"**이름:** {character_name}\n"
    embed_description += f"**레벨:** {character_level} ({character_exp_rate}%)\n"
    embed_description += f"**직업:** {character_class} ({character_class_level}차 전직)\n"
    embed_description += f"**길드:** {character_guild_name}\n"
    embed_description += f"**경험치: ** {character_exp_str}\n"
    embed_footer: str = f"생성일: {character_date_create_str}\n"
    embed_footer += f"해방 퀘스트 진행상황: {character_liberation_quest_clear}\n"
    embed_footer += f"({character_access_flag})"
    embed = discord.Embed(title=embed_title, description=embed_description)
    embed.set_image(url=character_image_url)
    embed.set_footer(text=embed_footer)
    embed.colour = discord.Colour.from_rgb(255, 204, 0)
    await ctx.send(embed=embed)
