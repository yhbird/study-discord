import httpx
import requests
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from exceptions.base import BotBaseException

from typing import Dict, Tuple

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
        raise BotBaseException(f"Failed to fetch image from {image_url}")
    else:
        image_bytes = io.BytesIO(response.content)
    
    return image_bytes


class ImageBaseConfig:
    """이미지 처리에 필요한 기본 설정 클래스"""
    MAPLE_FONT_BASIC = "./assets/font/Maplestory_Light.ttf"
    MAPLE_FONT_BOLD = "./assets/font/Maplestory_Bold.ttf"
    DEFAULT_FONT = "./assets/font/NanumGothic.ttf"


class MapleCodiHistoryConfig(ImageBaseConfig):
    """코디 히스토리 이미지 처리에 필요한 설정 클래스"""
    # 이미지 보드 설정
    IMAGE_SIZE        = 180
    CAPTION_HEIGHT    = 28
    IMAGE_GRID_COLS   = 4
    IMAGE_GRID_ROWS   = 2
    CELL_PADDING_SIZE = 16
    BOARD_MARGIN      = 24
    CELL_RADIUS       = 10

    # 색상 설정
    BG_COLOR          = (255, 255, 255, 255)
    FG_COLOR          = (33, 37, 41, 255)
    CELL_BG_COLOR     = (255, 255, 255, 255)
    CELL_SHADOW_COLOR = (0, 0, 0, 40)
    SHADOW_OFFSET     = (0, 2)

    # 폰트 설정
    TITLE_FONT_PATH   = ImageBaseConfig.MAPLE_FONT_BOLD
    CAPTION_FONT_PATH = ImageBaseConfig.MAPLE_FONT_BASIC
    DEFAULT_FONT_PATH = ImageBaseConfig.DEFAULT_FONT
    FONT_SIZE = 18
    TITLE_FONT_PADDING = 12
    PLACEHOLDER_IMAGE_PATH = "./assets/image/maple_chara_placeholder.png"


class MapleEquipmentViewerConfig(ImageBaseConfig):
    """캐릭터 장착 장비 이미지 처리에 필요한 설정 클래스"""
    # 크기 설정
    SLOT_SIZE    = 32
    SLOT_BG_SIZE = 44

    # 폰트 설정
    COLOR_STARFORCE_TEXT = (255, 204, 0, 255) # 노란색
    COLOR_STARFORCE_BG   = (0, 0, 0, 180)     # 가독성 위한 반투명 검정색 

    # 등급별 색상 (테두리, 마커)
    GRADE_COLORS: Dict[str, Tuple[int, int, int, int]] = {
        "R" : (0  , 153, 255, 255),  # 레어(하늘색)
        "E" : (119, 0  , 238, 255),  # 에픽(보라색)
        "U" : (255, 102, 204, 255),  # 유니크(노란색)
        "L" : (255, 153, 0  , 255),  # 레전드리(초록색)
    }

    # 장비창 배경 이미지 경로 (없으면 단색 배경 대체)
    VIEWER_BG_PATH = "./assets/image/equipment_viewer_bg.png"


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
            img (Image.Image): 원본 이미지
            radius (int): 둥근 모서리의 반지름

        Returns:
            Image.Image: 둥근 모서리 이미지
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