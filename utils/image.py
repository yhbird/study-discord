import httpx
import requests
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from exceptions.base import BotBaseException

from typing import Dict, Tuple


def get_image_bytes(image_url: str) -> io.BytesIO:
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
        raise BotBaseException(f"Failed to fetch image from {image_url}")
    else:
        image_bytes = io.BytesIO(response.content)
    
    return image_bytes


class ImageBaseConfig:
    """이미지 처리에 필요한 기본 설정 클래스"""
    MAPLE_FONT_BASIC : str = "./assets/font/Maplestory_Light.ttf"
    MAPLE_FONT_BOLD  : str = "./assets/font/Maplestory_Bold.ttf"
    DEFAULT_FONT     : str = "./assets/font/NanumGothic.ttf"


class MapleCodiHistoryConfig(ImageBaseConfig):
    """코디 히스토리 이미지 처리에 필요한 설정 클래스"""
    # 이미지 보드 설정
    IMAGE_SIZE        : int = 180
    CAPTION_HEIGHT    : int = 28
    IMAGE_GRID_COLS   : int = 4
    IMAGE_GRID_ROWS   : int = 2
    CELL_PADDING_SIZE : int = 16
    BOARD_MARGIN      : int = 24
    CELL_RADIUS       : int = 10

    # 색상 설정
    BG_COLOR          : Tuple[int, int, int, int] = (255, 255, 255, 255)
    FG_COLOR          : Tuple[int, int, int, int] = (33, 37, 41, 255)
    CELL_BG_COLOR     : Tuple[int, int, int, int] = (255, 255, 255, 255)
    CELL_SHADOW_COLOR : Tuple[int, int, int, int] = (0, 0, 0, 40)
    SHADOW_OFFSET     : Tuple[int, int] = (0, 2)

    # 폰트 설정
    TITLE_FONT_PATH        : str = ImageBaseConfig.MAPLE_FONT_BOLD
    CAPTION_FONT_PATH      : str = ImageBaseConfig.MAPLE_FONT_BASIC
    DEFAULT_FONT_PATH      : str = ImageBaseConfig.DEFAULT_FONT
    FONT_SIZE              : int = 18
    TITLE_FONT_PADDING     : int = 12
    PLACEHOLDER_IMAGE_PATH : str = "./assets/image/maple_chara_placeholder.png"


class MapleEquipmentViewerConfig(ImageBaseConfig):
    """캐릭터 장착 장비 이미지 처리에 필요한 설정 클래스"""
    # 좌표 설정
    START_X_LEFT   : int =  13 # 좌측 아이템 그룹 시작 좌표
    START_X_RIGHT  : int = 195 # 우측 아이템 그룹 시작 좌표, 캐릭터 표시 부분 skip
    START_X_CENTER : int =  80 # 무보엠(무기, 보조무기, 엠블럼) 표시
    START_Y_TOP    : int =  35 # 맨 윗줄 Y 좌표
    START_Y_CENTER : int = 260 # 무보엠 Y 좌표

    # 크기 설정
    SLOT_SIZE    : int = 32
    SLOT_BG_SIZE : int = 44
    SLOT_MARGIN  : int =  1

    # 간격 설정
    X_GAP : int = SLOT_BG_SIZE + SLOT_MARGIN # 가로 간격 (SLOT_BG_SIZE 44 + MARGIN 1)
    Y_GAP : int = SLOT_BG_SIZE + SLOT_MARGIN # 세로 간격 (SLOT_BG_SIZE 44 + MARGIN 1)

    # 폰트 설정
    COLOR_STARFORCE_TEXT = (255, 204,   0, 255) # 노란색
    COLOR_STARFORCE_BG   = (  0,   0,   0, 180) # 가독성 위한 반투명 검정색 

    # 등급별 색상 (테두리, 마커)
    GRADE_COLORS: Dict[str, Tuple[int, int, int, int]] = {
        "R" : (  0, 153, 255, 255),  # 레어(하늘색)
        "E" : (119,   0, 238, 255),  # 에픽(보라색)
        "U" : (255, 102, 204, 255),  # 유니크(노란색)
        "L" : (255, 153,   0, 255),  # 레전드리(초록색)
    }

    # 장비창 배경 이미지 경로 (없으면 단색 배경 대체)
    VIEWER_BG_PATH = "./assets/image/equipment_viewer_bg.png"

    SLOT_POSITIONS = {}

# 슬롯 이미지 좌표 (x, y) 계산
def _setup_positions():
    cfg = MapleEquipmentViewerConfig

    def get_slot_position(slot_group: str, col: int, row: int) -> Tuple[int, int]:
        if slot_group == "LEFT":
            start_x = cfg.START_X_LEFT
            start_y = cfg.START_Y_TOP
        elif slot_group == "RIGHT":
            start_x = cfg.START_X_RIGHT
            start_y = cfg.START_Y_TOP
        elif slot_group == "CENTER":
            start_x = cfg.START_X_CENTER
            start_y = cfg.START_Y_CENTER
        else:
            raise BotBaseException(f"Invalid slot group: {slot_group}")

        return start_x + (col * cfg.X_GAP), start_y + (row * cfg.Y_GAP)

    return {
        # [좌측 1열] (바깥쪽) : 반지4 부터 포켓까지
        "RING4"    : get_slot_position(slot_group = "LEFT", col = 0, row = 0),
        "RING3"    : get_slot_position(slot_group = "LEFT", col = 0, row = 1),
        "RING2"    : get_slot_position(slot_group = "LEFT", col = 0, row = 2),
        "RING1"    : get_slot_position(slot_group = "LEFT", col = 0, row = 3),
        "BELT"     : get_slot_position(slot_group = "LEFT", col = 0, row = 4),
        "POCKET"   : get_slot_position(slot_group = "LEFT", col = 0, row = 5),

        # [좌측 2열] (안쪽) : 얼굴장식부터 펜던트까지
        "FACE_ACC" : get_slot_position(slot_group = "LEFT", col = 1, row = 0),
        "EYE_ACC"  : get_slot_position(slot_group = "LEFT", col = 1, row = 1),
        "EARRING"  : get_slot_position(slot_group = "LEFT", col = 1, row = 2),
        "PENDANT2" : get_slot_position(slot_group = "LEFT", col = 1, row = 3),
        "PENDANT1" : get_slot_position(slot_group = "LEFT", col = 1, row = 4),

        # [중앙 하단] (캐릭터 이미지 바로 아래) : 무보엠
        "WEAPON"     : get_slot_position(slot_group = "CENTER", col = 0, row = 0),
        "SUB_WEAPON" : get_slot_position(slot_group = "CENTER", col = 1, row = 0),
        "EMBLEM"     : get_slot_position(slot_group = "CENTER", col = 2, row = 0),

        # [우측 1열] (안쪽) : 모자부터 안드로이드까지
        "CAP"      : get_slot_position(slot_group = "RIGHT", col = 0, row = 0),
        "TOP"      : get_slot_position(slot_group = "RIGHT", col = 0, row = 1),
        "BOTTOM"   : get_slot_position(slot_group = "RIGHT", col = 0, row = 2),
        "SHOULDER" : get_slot_position(slot_group = "RIGHT", col = 0, row = 3),
        "ANDROID"  : get_slot_position(slot_group = "RIGHT", col = 0, row = 4),

        # [우측 2열] (바깥쪽) : 망토부터 벳지까지
        "CAPE"     : get_slot_position(slot_group = "RIGHT", col = 1, row = 0),
        "GLOVES"   : get_slot_position(slot_group = "RIGHT", col = 1, row = 1),
        "SHOES"    : get_slot_position(slot_group = "RIGHT", col = 1, row = 2),
        "MEDAL"    : get_slot_position(slot_group = "RIGHT", col = 1, row = 3),
        "HEART"    : get_slot_position(slot_group = "RIGHT", col = 1, row = 4),
        "BADGE"    : get_slot_position(slot_group = "RIGHT", col = 1, row = 5),
    }

# 딕서너리 할당
MapleEquipmentViewerConfig.SLOT_POSITIONS = _setup_positions()

class ImageTools:
    """이미지 처리를 위한 정적 메서드 모음 클래스"""

    @staticmethod
    def load_font(font_path: str, font_size: int) -> ImageFont.FreeTypeFont:
        """폰트 로드 함수

        Args:
            font_path (str): 폰트 파일 경로
            font_size (int): 폰트 크기

        Returns:
            ImageFont.FreeTypeFont: 로드된 폰트 객체
        """
        try:
            return ImageFont.truetype(font_path, font_size)
        except OSError:
            return ImageFont.load_default()
        
    @staticmethod
    def make_rounded(img: Image.Image, radius: int) -> Image.Image:
        """이미지를 둥근 모서리로 만드는 함수

        Args:
            img (Image.Image): 원본 이미지 객체
            radius (int): 둥근 모서리의 반지름

        Returns:
            Image.Image: 둥근 모서리 이미지 객체
        """
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        w, h = img.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), (w, h)], radius=radius, fill=255)

        rounded_img = Image.new("RGBA", (w, h))
        rounded_img.paste(img, (0, 0), mask=mask)
        return rounded_img
    
    @staticmethod
    async def fetch_image(url: str) -> Image.Image | None:
        """비동기적으로 이미지 URL에서 이미지를 가져오는 함수

        Args:
            url (str): 이미지 URL

        Returns:
            Image.Image | None: 가져온 이미지 객체 또는 None
        """
        async with aiohttp.ClientSession() as client:
            try:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                image = Image.open(io.BytesIO(response.content)).convert("RGBA")
                return image
            except (httpx.HTTPError, UnidentifiedImageError):
                return None