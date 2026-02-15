# 현실적인 최대 금액 제한 (1경)
MAX_AMOUNT_LIMIT = 10_000_000_000_000_000

# 카드 수수료 마진 (약 2.3%)
CARD_FEE_MARGIN = 1.023

# Resolve TTL 설정
CACHE_POSITIVE_TTL = 60
CACHE_NEGATIVE_TTL = 600

CURRENCY_CODE_MAP = {
    # 미국 달러 (USD)
    "달러": "USD", "미국": "USD", "USD": "USD", "$": "USD",
    # 유럽 유로 (EUR)
    "유로": "EUR", "유럽": "EUR", "EUR": "EUR", "€": "EUR",
    # 일본 엔 (JPY)
    "엔": "JPY", "엔화": "JPY", "일본": "JPY", "JPY": "JPY", "¥": "JPY",
    # 중국 위안 (CNY)
    "위안": "CNY", "중국": "CNY", "CNY": "CNY", "위안화": "CNY",
    # 영국 파운드 (GBP)
    "파운드": "GBP", "영국": "GBP", "GBP": "GBP", "£": "GBP",
}
