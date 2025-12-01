from typing import Literal


SENSITIVE_KEYS = {"token", "password", "passwd", "secret", "key", "apikey", "authorization", "cookie", "session", "bearer"}


def safe_float(input_val, digits: int = 2) -> str:
    try:
        return f"{float(input_val):.{digits}f}"
    except (ValueError, TypeError):
        return "몰라양"
    
    
def safe_percent(input_val, digits: int = 2) -> str:
    try:
        return f"{float(input_val) * 100:.{digits}f} %"
    except (ValueError, TypeError):
        return "몰라양"


def preprocess_int_with_korean(input_val: str | int) -> str:
    """숫자로된 문자열을 한글 단위로 변환

    Args:
        input_val (str): 숫자로된 문자열, 예: "209558569"

    Returns:
        str: 한글 단위로 변환된 문자열, 예: "2억 9558만 8569"
    """
    if isinstance(input_val, str) and ',' in input_val:
        input_val: str = input_val.replace(',', '').replace(' ', '')
    if isinstance(input_val, int):
        input_val: str = str(input_val)
    
    # 조, 억, 만, 그 이하 단위 분리
    str_100b: str = f"{input_val[:-12]}조" # 조
    str_100m: str | Literal[""] = f"{input_val[-12:-8]}억" if input_val[-12:-8] != "0000" else "" # 억
    str_10k: str | Literal[""] = f"{input_val[-8:-4]}만" if input_val[-8:-4] != "0000" else "" # 만
    str_floor: str | Literal[""] = f"{input_val[-4:]}" if input_val[-4:] != "0000" else "" # 그 이하

    # 조 단위 처리
    if int(input_val) >= 1_000_000_000_000:
        return f"{str_100b} {str_100m} {str_10k} {str_floor}".strip()
    
    # 억 단위 처리
    elif int(input_val) >= 100_000_000:
        return f"{str_100m} {str_10k} {str_floor}".strip()
    
    # 만 단위 처리
    elif int(input_val) >= 10_000:
        return f"{str_10k} {str_floor}".strip()
    
    # 그 이하 단위 처리
    else:
        return input_val


def preprocess_int_for_stocks(input_val: int) -> str:
    """주식 관련 정보를 위한 큰 숫자의 정수를 영어권 단위로 변환

    Args:
        input_val (int): 변환할 정수 값

    Returns:
        str: 변환된 문자열 (예: 1,234,567,890 -> "1.23B")
    """
    if not isinstance(input_val, int):
        return "몰라양"
    
    if   input_val >= 1_000_000_000_000:
        return f"{input_val / 1_000_000_000_000:.2f}T"
    elif input_val >= 1_000_000_000:
        return f"{input_val / 1_000_000_000:.2f}B"
    elif input_val >= 1_000_000:
        return f"{input_val / 1_000_000:.2f}M"
    elif input_val >= 1_000:
        return f"{input_val / 1_000:.2f}K"
    else:
        return str(input_val)


def rank_to_emoji(rank: int) -> str:
    """순위를 이모지로 변환

    Args:
        rank (int): 순위 (1, 2, 3, ...)

    Returns:
        str: 순위에 해당하는 이모지

    Note:
        4위 이상은 그냥 "4", "5" 형태로 반환
    """
    rank_emojis = {
        1 : "🥇",
        2 : "🥈",
        3 : "🥉",
    }
    return rank_emojis.get(rank, str(rank))