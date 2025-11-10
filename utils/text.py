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

    if int(input_val) >= 100_000_000:
        str_100b: str = f"{input_val[:-12]}조" # 조
        str_100m: str = f"{input_val[-12:-8]}억" # 억
        str_10k: str = f"{input_val[-8:-4]}만" # 만
        str_floor: str = f"{input_val[-4:]}" # 그 이하
        if str_100m == "0000억":
            str_100m = ""
        if str_10k == "0000만":
            str_10k = ""
        if str_floor == "0000":
            str_floor = ""
        return f"{str_100m} {str_10k} {str_floor}".strip()
    elif int(input_val) >= 10_000:
        str_10k: str = f"{input_val[:-4]}만"
        str_floor: str = f"{input_val[-4:]}" # 그 이하
        if str_floor == "0000":
            str_floor = ""
        return f"{str_10k} {str_floor}".strip()
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


SENSITIVE_KEYS = {"token", "password", "passwd", "secret", "key", "apikey", "authorization", "cookie", "session", "bearer"}