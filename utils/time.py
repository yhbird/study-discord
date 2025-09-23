import logging
from dateutil import parser

from pytz import timezone
from datetime import datetime


class KstFormatter(logging.Formatter):
    """logging.Formatter이 KST 포맷을 사용하도록 커스텀

    Args:
        logging (Formatter): 기본 logging.Formatter 클래스
        dtformat (str): 날짜 포맷 문자열, 기본값은 '%Y-%md-%d %H:%M:%S'

    Returns:
        str: KST로 포맷된 날짜 문자열
    """
    def format_time(self, record, dtformat=None):
        kst = timezone('Asia/Seoul')
        dt = datetime.fromtimestamp(record.created, tz=kst)
        if dtformat:
            return dt.strftime(dtformat)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        

def kst_format_now() -> str:
    """현재 시각을 KST로 포맷팅

    Returns:
        str: KST로 포맷된 현재 시각 문자열
    """
    kst = timezone('Asia/Seoul')
    return datetime.now(tz=kst).strftime('%Y-%m-%d %H:%M:%S')


def parse_iso_string(iso_string: str) -> str:
    """국제기준(ISO) 날짜 문자열을 KST로 변환

    Args:
        date_str (str): 변환할 날짜 문자열

    Returns:
        str: KST로 변환된 날짜 문자열

    Example:
        ```python
        date_str = "2025-07-21T17:30+09:00"
        kst_date = date_to_kst(date_str)
        print(kst_date)  # "2025-07-21 17:30:00"
        ```"
    """
    dt = parser.isoparse(iso_string)
    kst = timezone('Asia/Seoul')
    return_string = f"{dt.year}년 {dt.month}월 {dt.day}일 {dt.hour}:{dt.minute:02d} (KST)"
    return return_string