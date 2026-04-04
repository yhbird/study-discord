import discord
from discord.ext import commands

from service.neoplednf.utils import *
from exceptions.command_exceptions import CommandFailure

from bot_logger import log_command, with_timeout
from utils.time import kst_format_now
from config import COMMAND_TIMEOUT


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 던파정보")
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
    
    # 캐릭터 고유 ID 조회 -> 캐릭터 정보 조회
    try:
        server_id, character_id = (
            await get_dnf_server_id(server_name),
            await get_dnf_character_id(server_name, character_name)
        )
        character_info: dict = await get_dnf_character_info(server_id, character_id)
    except NeopleAPIInvalidId as e:
        await ctx.send(f"네오플 API 요청에 오류가 발생했어양!!!")
        raise CommandFailure("Invalid ID")
    except NeopleAPILimitExceed as e:
        await ctx.send(f"네오플 API 요청 제한에 걸렸어양...")
        raise CommandFailure("API limit exceeded")
    except NeopleAPIInvalidParams as e:
        await ctx.send(f"네오플 API 요청 파라미터가 잘못되었어양...")
        raise CommandFailure("Invalid parameters")
    except NeopleDNFInvalidServerID as e:
        await ctx.send(f"서버명이 잘못 입력 되었어양...")
        raise CommandFailure("Invalid server name")
    except NeopleDNFInvalidCharacterInfo as e:
        await ctx.send(f"캐릭터 '{character_name}'을(를) 찾을 수 없어양...")
        raise CommandFailure(f"Character '{character_name}' not found")
    except NeopleDNFInvalidRequestParams as e:
        await ctx.send(f"네오플 API 요청 파라미터에 오류가 발생했어양!!!")
        raise CommandFailure("Invalid request parameters")
    except NeopleDNFSystemMaintenance as e:
        await ctx.send(f"현재 던전앤파이터 서비스 점검 중이에양!")
        raise CommandFailure("System maintenance")
    except NeopleDNFSystemError as e:
        await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        raise CommandFailure("System error")
    except NeopleAPIError as e:
        await ctx.send(f"네오플 API 요청에 오류가 발생했어양!!!")
        raise CommandFailure("Neople API error")
    except DNFCIDNotFound as e:
        await ctx.send(f"{server_name}서버 '{character_name}'의 고유ID를 찾을 수 없어양...")
        raise CommandFailure(f"Character ID not found")
    except DNFCharacterNotFound as e:
        await ctx.send(f"{server_name}서버 '{character_name}'을(를) 찾을 수 없어양...")
        raise CommandFailure(f"Character '{character_name}' not found")
    except Exception as e:
        await ctx.send(f"던전앤파이터 API 통신 중 알 수 없는 오류가 발생했어양!")
        raise CommandFailure("Unknown error")

    # 모험단 이름 추출
    adventure_name: str | Literal["몰라양"] = character_info.get("adventure_name")
    # 캐릭터 레벨 추출
    character_level: int | Literal[0] = character_info.get("level")
    # 캐릭터 클래스 추출
    character_job_name: str | Literal["모름"] = character_info.get("job_name")
    # 캐릭터 전직명 추출
    character_job_grow_name: str | Literal["모름"] = character_info.get("job_grow")
    # 캐릭터 명성 추출
    character_fame: int | Literal[0] = character_info.get("fame")
    # 캐릭터 길드 추출
    character_guild: str | Literal["길드가 없어양!"] = character_info.get("guild_name")

    dundam_url = f"https://dundam.xyz/character?server={server_id}&key={character_id}"
    dfgear_url_c = f"https://dfgear.xyz/character?sId={server_id}&cId={character_id}&cName={character_name}"
    if adventure_name != "몰라양":
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
        f"**명성:** {character_fame:,}\n"
        f"**길드:** {character_guild}\n"
    )
    embed_footer: str = (
        f"캐릭터 선택창에 나갔다 오면 빨리 갱신되양!\n"
        f"powered by Neople API"
    )

    # 캐릭터 이미지 URL추출
    character_image_bytes: io.BytesIO = await get_dnf_character_image(server_id, character_id)
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
    return


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 던파장비")
async def api_dnf_equipment(ctx: commands.Context, server_name: str, character_name: str) -> None:
    """던전앤파이터 캐릭터 장비 정보 조회

    Args:
        ctx (commands.Context): Discord context
        server_name (str): 서버 이름
        character_name (str): 캐릭터 이름

    Raises:
        NeopleAPIError: 던전앤파이터 API 요청 중 발생하는 오류

    Note:
        - 115레벨 (중천 시즌) 장비 기준으로 정보 조회
        - 융합석 장착 정보 포함
        - 세트 옵션 정보 포함
    """
    # 캐릭터 고유 ID 조회 -> 캐릭터 정보 조회
    character_image = None
    try:
        server_id, character_id = (
            await get_dnf_server_id(server_name),
            await get_dnf_character_id(server_name, character_name)
        )
        character_info = await get_dnf_character_info(server_id, character_id)
        equipment_info = await get_dnf_character_equipment(server_id, character_id)
        character_image = await get_dnf_character_image(server_id, character_id)
    
    except NeopleAPIInvalidId as e:
        await ctx.send(f"네오플 API 요청에 오류가 발생했어양!!!")
        raise CommandFailure("Invalid ID")
    except NeopleAPILimitExceed as e:
        await ctx.send(f"네오플 API 요청 제한에 걸렸어양...")
        raise CommandFailure("API limit exceeded")
    except NeopleAPIInvalidParams as e:
        await ctx.send(f"네오플 API 요청 파라미터가 잘못되었어양...")
        raise CommandFailure("Invalid parameters")
    except NeopleDNFInvalidServerID as e:
        await ctx.send(f"서버명이 잘못 입력 되었어양...")
        raise CommandFailure("Invalid server name")
    except NeopleDNFInvalidCharacterInfo as e:
        await ctx.send(f"캐릭터 '{character_name}'을(를) 찾을 수 없어양...")
        raise CommandFailure(f"Character '{character_name}' not found")
    except NeopleDNFInvalidRequestParams as e:
        await ctx.send(f"네오플 API 요청 파라미터에 오류가 발생했어양!!!")
        raise CommandFailure("Invalid request parameters")
    except NeopleDNFSystemMaintenance as e:
        await ctx.send(f"현재 던전앤파이터 서비스 점검 중이에양!")
        raise CommandFailure("System maintenance")
    except NeopleDNFSystemError as e:
        await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        raise CommandFailure("System error")
    except NeopleAPIError as e:
        await ctx.send(f"네오플 API 요청에 오류가 발생했어양!!!")
        raise CommandFailure("Neople API error")
    except DNFCIDNotFound as e:
        await ctx.send(f"{server_name}서버 '{character_name}'의 고유ID를 찾을 수 없어양...")
        raise CommandFailure(f"Character ID not found")
    except DNFCharacterNotFound as e:
        await ctx.send(f"{server_name}서버 '{character_name}'을(를) 찾을 수 없어양...")
        raise CommandFailure(f"Character '{character_name}' not found")
    except Exception as e:
        await ctx.send(f"던전앤파이터 API 통신 중 알 수 없는 오류가 발생했어양!")
        raise CommandFailure("Unknown error")
    
    if locals().get('equipment_info') is None:
        await ctx.send(f"{server_name}서버 '{character_name}'의 장비 정보를 찾을 수 없어양...")
        raise CommandFailure("Equipment data not found")
    
    if len(equipment_info) == 0:
        await ctx.send(f"{server_name}서버 '{character_name}'의 장비 정보가 없어양...")
        raise CommandFailure("Equipment data not found")
    
    slots = [
        "무기", "칭호",
        "머리어깨", "상의", "벨트", "하의", "신발",
        "팔찌", "목걸이", "반지",
        "보조장비", "귀걸이", "마법석",
    ]

    # 장비 데이터 파싱
    slot_info_text_list = []
    character_set_items = {}  # 세트 아이템 정보 집계용
    plus_setname = "고유 장비"
    character_set_items[plus_setname] = 0 # 고유 장비 세트 포인트
    total_plus_setpoint = 0
    equipment_icon: Dict[str, str] = {}

    for slot in slots:
        equipment_data = equipment_info.get(slot)
        if equipment_data is None:
            slot_info_text = f"{slot}: 없음 (비어있음)\n"
            equipment_icon[slot] = None
        else:
            plus_setpoint = 0
            item_id: str = equipment_data.get("item_id", "몰라양")
            if item_id != "몰라양":
                equipment_icon[slot] = item_id
            else:
                equipment_icon[slot] = None
            item_rare: str = equipment_data.get("item_rarity", "몰라양")
            item_name: str = equipment_data.get("item_name", "몰라양")
            # 조율 정보
            tune_level: int = equipment_data.get("tune_level", 0)
            tune_text: str = (
                f"[{tune_level}조율] " if tune_level > 0 else ""
            )

            # 강화 정보
            item_reinforce: int = equipment_data.get("item_reinforce", 0)
            item_reinforce_type: str = equipment_data.get("item_reinforce_type", "강화")
            item_refine: int = equipment_data.get("item_refine", 0)
            item_refine_text: str = f"({item_refine})" if item_refine > 0 else ""
            reinforce_text: str = (
                f"+{item_reinforce}{item_reinforce_type}{item_refine_text}"
                if slot != "칭호" else ""
            )

            # 세트 옵션 정보
            set_item_name: str = equipment_data.get("set_item_name", "없음")
            tune_setpoint: int = equipment_data.get("tune_setpoint", 0)
            fusion_setpoint: int = equipment_data.get("fusion_setpoint", 0)
            final_setpoint: int = equipment_data.get("final_setpoint", 0)
            fusion_setpoint_text: str = (
                f" + {fusion_setpoint}pt" if fusion_setpoint > 0 else ""
            )
            if set_item_name != "없음":
                set_info_text = f"\n\t({set_item_name} + {tune_setpoint}pt{fusion_setpoint_text})"
            elif set_item_name == "없음" and "고유 - " in item_name: # 고유장비 특수 처리
                # 고유 장비를 장착 하고 있는 경우 (가장 높은 세트의 포인트에 합산됨)
                if item_rare == "유니크":
                    plus_setpoint = 115
                elif item_rare == "레전더리":
                    plus_setpoint = 165
                elif item_rare == "에픽":
                    plus_setpoint = 215
                else:
                    plus_setpoint = 0
                set_info_text = f"\n\t(고유 장비 세트 포인트 + {plus_setpoint}pt{fusion_setpoint_text})"
            else:
                set_info_text = ""

            # 세트 아이템 정보 집계
            if set_item_name != "없음":
                if set_item_name in character_set_items:
                    character_set_items[set_item_name] += final_setpoint
                else:
                    character_set_items[set_item_name] = final_setpoint
            elif set_item_name == "없음" and "고유 - " in item_name:  # 고유장비 특수 처리
                total_plus_setpoint += plus_setpoint
                if plus_setname in character_set_items:
                    character_set_items[plus_setname] += plus_setpoint
                else:
                    character_set_items[plus_setname] = plus_setpoint
            else:
                pass # 세트 아이템 아님

            # 슬롯별 장비 정보 문자열 생성
            slot_info_text = (
                f"{slot}: {dnf_convert_grade_text(item_rare)} {tune_text}{reinforce_text} {item_name}{set_info_text}\n"
            )
        slot_info_text_list.append(slot_info_text)

    set_info = equipment_info.get("set_item_info", {})

    if set_info != {}:
        set_item_name: str = set_info.get("set_item_name", "몰라양")
        set_item_rare: str = set_info.get("set_item_rarity", "몰라양")
        set_point_info: Dict[str, int] = set_info.get("set_item_setpoint", {})
        current_setpoint: int = set_point_info.get("current", 0)
        best_setname_text: str = f"{dnf_convert_grade_text(set_item_rare)} {set_item_name}"
        best_setpoint_text: str = check_setpoint_bonus(current_setpoint)
        best_set_text: str = f"**{best_setname_text} {best_setpoint_text}**"
    else:
        best_set, best_setpoint = calculate_final_setpoint(character_set_items)
        best_setname_text: str = f"{best_set}"
        best_setpoint_text = check_setpoint_bonus(best_setpoint)
        best_set_text: str = f"**{best_setname_text} {best_setpoint_text}**"

    slot_info_text: str = "\n".join(slot_info_text_list)

    # Discord Embed 객체 생성
    # 장비 아이콘 이미지 생성
    equipment_board_image = build_equipment_board(equipment_icon, character_image)
    kst_now: str = kst_format_now().strftime("%Y%m%d%H%M")
    image_file_name: str = f"{server_id}_{character_id}_equipment_{kst_now}.png"
    equipment_board_image_file: discord.File = discord.File(equipment_board_image, filename=image_file_name)

    # 모험단 이름 추출
    adventure_name: str | Literal["몰라양"] = character_info.get("adventure_name")
    # 캐릭터 레벨 추출
    character_level: int | Literal[0] = character_info.get("level")
    # 캐릭터 클래스 추출
    character_job_name: str | Literal["모름"] = character_info.get("job_name")
    # 캐릭터 전직명 추출
    character_job_grow_name: str | Literal["모름"] = character_info.get("job_grow")
    # 캐릭터 명성 추출
    character_fame: int | Literal[0] = character_info.get("fame")

    dundam_url = f"https://dundam.xyz/character?server={server_id}&key={character_id}"

    msg_content: str = (
        f"**세트:** {best_set_text}\n\n"
        f"{slot_info_text}"
    )

    embed_title: str = f"{server_name}서버 '{character_name}' 모험가님의 장비 정보에양!"
    embed_description: str = (
        f"[🔗 던담 사이트 이동]({dundam_url})\n"
        f"**모험단:** {adventure_name}\n"
        f"**레벨:** {character_level}\n"
        f"**직업:** {character_job_name}\n"
        f"**전직:** {character_job_grow_name}\n"
        f"**명성:** {character_fame:,}\n"
        f"\n{msg_content}"
    )
    embed_footer: str = (
        f"시즌 패치 기준: 2025년 10월 2월 (중천)\n"
        f"캐릭터 선택창에 나갔다 오면 빨리 갱신되양!\n"
        f"powered by Neople API"
    )
    embed = discord.Embed(
        title=embed_title,
        description=embed_description,
        color=discord.Color.blue()
    )
    embed.set_footer(text=embed_footer)
    await ctx.send(file=equipment_board_image_file, embed=embed)
    return


@log_command(alt_func_name="븜 주간던파")
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
    if ctx.message.author.bot:
        return
    
    # 캐릭터 고유 ID 조회
    try:
        server_id, character_id = (
            await get_dnf_server_id(server_name),
            await get_dnf_character_id(server_name, character_name)
        )
        set_item_info: Dict[str, Any] = await get_dnf_character_set_equipment_info(server_id, character_id)
        timeline_data: dict = await get_dnf_weekly_timeline(server_id, character_id)
    except NeopleAPIInvalidId as e:
        await ctx.send(f"네오플 API 요청에 오류가 발생했어양!!!")
        raise CommandFailure("Invalid ID")
    except NeopleAPILimitExceed as e:
        await ctx.send(f"네오플 API 요청 제한에 걸렸어양...")
        raise CommandFailure("API limit exceeded")
    except NeopleAPIInvalidParams as e:
        await ctx.send(f"네오플 API 요청 파라미터가 잘못되었어양...")
        raise CommandFailure("Invalid parameters")
    except NeopleDNFInvalidServerID as e:
        await ctx.send(f"서버명이 잘못 입력 되었어양...")
        raise CommandFailure("Invalid server name")
    except NeopleDNFInvalidCharacterInfo as e:
        await ctx.send(f"캐릭터 '{character_name}'을(를) 찾을 수 없어양...")
        raise CommandFailure(f"Character '{character_name}' not found")
    except NeopleDNFInvalidRequestParams as e:
        await ctx.send(f"네오플 API 요청 파라미터에 오류가 발생했어양!!!")
        raise CommandFailure("Invalid request parameters")
    except NeopleDNFSystemMaintenance as e:
        await ctx.send(f"현재 던전앤파이터 서비스 점검 중이에양!")
        raise CommandFailure("System maintenance")
    except NeopleDNFSystemError as e:
        await ctx.send(f"던전앤파이터 API에서 오류가 발생했어양!")
        raise CommandFailure("System error")
    except NeopleAPIError as e:
        await ctx.send(f"네오플 API 요청에 오류가 발생했어양!!!")
        raise CommandFailure("Neople API error")
    except DNFCIDNotFound as e:
        await ctx.send(f"{server_name}서버 '{character_name}'의 고유ID를 찾을 수 없어양...")
        raise CommandFailure(f"Character ID not found")
    except DNFCharacterNotFound as e:
        await ctx.send(f"{server_name}서버 '{character_name}'을(를) 찾을 수 없어양...")
        raise CommandFailure(f"Character '{character_name}' not found")
    except Exception as e:
        await ctx.send(f"던전앤파이터 API 통신 중 알 수 없는 오류가 발생했어양!")
        raise CommandFailure("Unknown error")

    if locals().get('timeline_data') is None:
        await ctx.send(f"{server_name}서버 '{character_name}'의 주간 타임라인 데이터를 찾을 수 없어양...")
        raise CommandFailure("Timeline data not found")
    
    character_timeline: dict = timeline_data.get("timeline")
    timeline_rows: List[Dict[str, Any]] = character_timeline.get("rows")
    character_set_item_id: str = set_item_info.get("set_item_id") # 세트 아이템 ID
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
        clear_raid_diregie_flag: bool = False
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
            if 500 <= timeline_code < 600:
                item_id: str = timeline_data.get("itemId", "몰라양")
                item_setid: str = await get_set_item_id(item_id)
                item_name: str = timeline_data.get("itemName", "몰라양")
                item_rare: str = timeline_data.get("itemRarity", "몰라양")

                # 태초 아이템 획득 시 하이라이트 메시지 생성
                tl_cond: bool = (item_rare == "태초") or (item_setid == character_set_item_id and item_rare == "에픽")
                if tl_cond and timeline_code != dnf_timeline_codes.upgrade_stone:

                    # 던전 카드 보상에서 태초 아이템 획득 시 or 세트 아이템 에픽 획득 시
                    if timeline_code == dnf_timeline_codes.reward_clear_dungeon_card:
                        dungeon_name: str = timeline_data.get("dungeonName", "몰라양")

                        timeline_highlight += (
                            f"아이템 획득: {dnf_convert_grade_text(item_rare)}{item_name}"
                            f" ({dungeon_name} 카드보상, {timeline_date})\n"
                        )

                    # 레이드 카드 보상에서 태초 아이템 획득 시
                    elif timeline_code == dnf_timeline_codes.reward_clear_raid_card:
                        timeline_highlight += (
                            f"아이템 획득: {dnf_convert_grade_text(item_rare)}{item_name}"
                            f" (레이드 카드 보상, {timeline_date})\n"
                        )

                    elif timeline_code == dnf_timeline_codes.reward_promise_card:
                        timeline_highlight += (
                            f"아이템 획득: {dnf_convert_grade_text(item_rare)}{item_name}"
                            f" (레이드 카드 보상, {timeline_date})\n"
                        )

                    # 항아리&상자 보상에서 태초 아이템 획득 시
                    elif timeline_code == dnf_timeline_codes.reward_pot_and_box:
                        timeline_highlight += (
                            f"아이템 획득: {dnf_convert_grade_text(item_rare)}{item_name}"
                            f" (항아리&상자 개봉, {timeline_date})\n"
                        )

                    elif timeline_code == dnf_timeline_codes.reward_promise_pot_and_box:
                        timeline_highlight += (
                            f"서약 획득: {dnf_convert_grade_text(item_rare)}{item_name}"
                            f" (항아리&상자 개봉, {timeline_date})\n"
                        )

                    elif timeline_code == dnf_timeline_codes.item_scroll:
                        timeline_highlight += (
                            f"아이템 교환: {dnf_convert_grade_text(item_rare)}{item_name} ({timeline_date})\n"
                        )

                    # 기타 종말의 숭배자 등에서 아이템 획득
                    else:
                        channel_name = timeline_data.get("channelName", "알수없음")
                        channel_no = timeline_data.get("channelNo", "알수없음")
                        timeline_highlight += (
                            f"아이템 획득: {dnf_convert_grade_text(item_rare)}{item_name} @{channel_name} {channel_no}채널"
                            f" ({timeline_date})\n"
                        )
                    
                no_count_conditions: bool = (
                    timeline_code in (dnf_timeline_codes.item_scroll, dnf_timeline_codes.upgrade_stone)
                )
                # 장비 업그레이드 (에픽 획득 집계 미포함)
                if timeline_code == dnf_timeline_codes.upgrade_stone:
                    get_epic_up_count += 1
                    timeline_highlight += (
                        f"장비 업글: {dnf_convert_grade_text(item_rare)}{item_name} ({timeline_date})\n"
                    )
                
                # 태초 아이템 획득
                if item_rare == "태초":
                    get_primeval_count += 0 if no_count_conditions else 1

                # 에픽 아이템 획득
                if item_rare == "에픽":
                    get_epic_count += 0 if no_count_conditions else 1

                # 레전더리 아이템 획득
                if item_rare == "레전더리":
                    get_legendary_count += 0 if no_count_conditions else 1

            if timeline_code == dnf_timeline_codes.clear_region:
                # 레기온 클리어
                region_name: str = timeline_data.get("regionName", "몰라양")
                if region_name == "베누스":
                    clear_raid_region_flag = True
                    clear_raid_region_date = timeline_date

            if timeline_code == dnf_timeline_codes.clear_raid:
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
                if raid_name == "디레지에 레이드":
                    clear_raid_diregie_flag = True
                    clear_raid_diregie_date = timeline_date

            # 아이템 증폭
            if timeline_code == dnf_timeline_codes.item_upgrade:
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

        clear_raid_diregie = dnf_get_clear_flag(clear_raid_diregie_flag, locals().get('clear_raid_diregie_date'))
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
            f"🟡 에픽 획득: {get_epic_count}개 (장비 업글 {get_epic_up_count}회)\n"
            f"🟠 레전 획득: {get_legendary_count}개\n\n"
            f"**\-\-\- 레이드 및 레기온 클리어 현황 \-\-\-**\n"
            f"디레지에 레이드 클리어: {clear_raid_diregie}\n"
            f"이내 황혼전 클리어: {clear_raid_twilight}\n"
            f"만들어진 신 나벨 클리어: {clear_raid_nabel}\n"
            f"베누스 레기온 클리어: {clear_raid_region}\n"
            f"\n{timeline_highlight_str}"
        )

        timeline_footer: str = (
            f"패치 시즌: 천해천 (2026.03.26)\n"
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
        return
