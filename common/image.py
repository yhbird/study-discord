import httpx
import requests
import io
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, UnidentifiedImageError
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


async def async_upscale_emoji_image(image_url: str, target_size: int = 160) -> tuple[io.BytesIO, str]:
    """
    이모지 이미지 URL을 받아서 이미지를 업스케일링 하는 함수

    Args:
        image_url (str): 이모지 이미지 URL
        target_size (int, optional): 목표 크기. Defaults to 160.

    Returns:
        tuple[io.BytesIO, str]: 업스케일링된 이미지 바이트와 형식
    """
    # CDN에서 고해상도 소스를 가져오기 위해 size 파라미터 추가
    separator = '&' if '?' in image_url else '?'
    hq_url = f"{image_url}{separator}size=256"
    image_data: io.BytesIO = await async_convert_image_url_into_bytes(hq_url)
    image = Image.open(image_data)
    is_animated = getattr(image, "is_animated", False)
    output_buffer = io.BytesIO()

    if is_animated:
        frames = []
        durations = []

        try:
            while True:
                frame = image.copy()
                if frame.mode != 'RGBA':
                    frame = frame.convert("RGBA")

                if max(frame.size) != target_size:
                    scale_factor = target_size / max(frame.size)
                    new_size = tuple(int(dim * scale_factor) for dim in frame.size)
                    frame = frame.resize(new_size, resample=Image.Resampling.LANCZOS)
                    
                    if max(image.size) < target_size:
                        enhancer = ImageEnhance.Sharpness(frame)
                        frame = enhancer.enhance(1.2)

                frames.append(frame)
                durations.append(image.info.get('duration', 100))
                image.seek(image.tell() + 1)

        except EOFError:
            pass

        frames[0].save(
            output_buffer,
            format='GIF',
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            optimize=True,
            disposal=2
        )
        output_buffer.seek(0)
        return output_buffer, "gif"
            
    else:
        if image.mode != 'RGBA':
            image = image.convert("RGBA")

        if max(image.size) != target_size:
            scale_factor = target_size / max(image.size)
            new_size = tuple(int(dim * scale_factor) for dim in image.size)
            image = image.resize(new_size, resample=Image.Resampling.LANCZOS)
            
            if max(Image.open(image_data).size) < target_size:
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(1.2)

        image.save(output_buffer, format='PNG', optimize=True)
        output_buffer.seek(0)
        return output_buffer, "png"


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
                content = await response.read()
                image = Image.open(io.BytesIO(content)).convert("RGBA")
                return image
            except (httpx.HTTPError, UnidentifiedImageError):
                return None