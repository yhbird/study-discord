import requests
import io
from exceptions.base import BotBaseException

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