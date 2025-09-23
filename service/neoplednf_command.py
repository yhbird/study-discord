import discord
from discord.ext import commands

import io

from service.neoplednf_utils import *

from bot_logger import log_command
from utils.image import get_image_bytes


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