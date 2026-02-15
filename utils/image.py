import httpx
import requests
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from exceptions.base import BotBaseException
from exceptions.client_exceptions import GeneralRequestError


def convert_image_url_into_bytes(image_url: str) -> io.BytesIO:
    """
    이미지 URL로부터 이미지 바이트를 가져오는 함수

    Args:
        image_url (str): 이미지 URL

    Returns:
        bytes: 이미지 바이트

    Raises:
        GeneralRequestError: 요청 오류에 대한 예외를 발생시킴
    """
    response = requests.get(image_url)
    if response.status_code != 200:
        # Error 메세지 출력후 예외 발생
        traceback = response.text
        print(f"Error fetching image from {image_url}: {response.status_code}\n{traceback}")
        raise GeneralRequestError(f"Failed to fetch image from {image_url}")
    else:
        image_bytes = io.BytesIO(response.content)
    
    image_bytes.seek(0)
    return image_bytes


async def async_convert_image_url_into_bytes(image_url: str) -> io.BytesIO:
    """
    비동기적으로 이미지 URL로부터 이미지 바이트를 가져오는 함수
    
    (동기함수와 동일하게 동작)

    Args:
        image_url (str): 이미지 URL

    Returns:
        bytes: 이미지 바이트

    Raises:
        GeneralRequestError: 요청 오류에 대한 예외를 발생시킴
    """
    async with aiohttp.ClientSession() as client:
        async with client.get(image_url) as response:
            if response.status != 200:
                # Error 메세지 출력후 예외 발생
                traceback = await response.text()
                print(f"Error fetching image from {image_url}: {response.status}\n{traceback}")
                raise GeneralRequestError(f"Failed to fetch image from {image_url}")
            else:
                content = await response.read()

    image_bytes = io.BytesIO(content)

    image_bytes.seek(0)
    return image_bytes


class ImageBaseConfig:
    """이미지 처리에 필요한 기본 설정 클래스"""
    MAPLE_FONT_BASIC : str = "./assets/font/Maplestory_Light.ttf"
    MAPLE_FONT_BOLD  : str = "./assets/font/Maplestory_Bold.ttf"
    DEFAULT_FONT     : str = "./assets/font/NanumGothic.ttf"


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