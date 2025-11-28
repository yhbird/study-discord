import discord
from discord.ext import commands

from config import COMMAND_TIMEOUT
from service.weather_utils import *

from bot_logger import log_command, with_timeout

from exceptions.client_exceptions import *


@with_timeout(COMMAND_TIMEOUT)
@log_command(alt_func_name="븜 날씨")
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
    except KakaoNoLocalInfo as e:
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