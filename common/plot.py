import os
import sys
import matplotlib

from matplotlib import font_manager
from pathlib import Path

# 상황에 맞게 matplotlib 폰트 오버라이드 설정
fp_maplestory_light = font_manager.FontProperties(fname="assets/font/Maplestory_Light.ttf")
fp_maplestory_bold = font_manager.FontProperties(fname="assets/font/Maplestory_Bold.ttf")

# matplotlib 한글 폰트 설정
def set_up_matplotlib_korean(font_path: str = "assets/font/NanumGothic.ttf"):
    """matplotlib에서 한글 폰트를 설정하는 함수

    Args:
        font_path (str, optional): 한글 폰트 파일 경로. Defaults to "assets/font/NanumGothic.ttf".
    """
    os.environ.setdefault("MPLCONFIGDIR", "./tmp/matplotlib")
    font_path = Path(font_path).resolve()

    if not Path(font_path).is_file():
        print(f"Font file not found: {font_path}")
        sys.exit(1)

    # 런타임 등록
    font_manager.fontManager.addfont(str(font_path))
    prop = font_manager.FontProperties(fname=str(font_path))
    family = prop.get_name()

    # 전역 설정
    matplotlib.rcParams['font.family'] = family
    matplotlib.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지

    try:
        import matplotlib.pyplot as plt
    except Exception:
        matplotlib.use('Agg')

    return family

