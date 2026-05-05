class FinanceConsts:
    SERVICE_CURRENCY = "KRW"
    SERVICE_TIMEZONE = "Asia/Seoul"
    SERVICE_TIMEZONE_SHORT = "KST"

class FinanceCurrency:
    SERVICE_CURRENCY = FinanceConsts.SERVICE_CURRENCY

    # 현실적인 최대 금액 제한 (1경 KRW)
    MAX_AMOUNT_LIMIT = 10_000_000_000_000_000

    # 카드 수수료 마진 (약 2.3%)
    CARD_FEE_MARGIN = 0.023
    # 외화 송금 금액 (TT Selling)
    CURRENCY_TRANSFER_FEE = 0.01

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
        # 캐나다 달러 (CAD)
        "캐나다": "CAD", "캐나다달러": "CAD"
    }

    CURRENCY_NAME_MAP = {
        "USD": "미국 달러",
        "EUR": "유럽 유로화",
        "GBP": "영국 파운드화",
        "JPY": "일본 엔화",
        "CNY": "중국 위안화",
        "CAD": "캐나다 달러"
    }

    CURRENCY_SOURCE_INFO = (
        f"\n--- 환율안내 ---\n"
        f"환율 정보 제공: 네이버 금융 (하나은행)\n"
        "기준 환율: 1 {source} -> {target:.2f} KRW\n"
        f"환율 우대, 거래 수수료에 따라 주식가격이 다를 수 있어양.\n"
    )

    CURRENCY_SOURCE_INFO_V2 = (
        f"\n--- 환율안내 ---\n"
        f"환율 정보 제공: Yahoo Finance\n"
        "기준 환율: 1 {source} -> {target:.2f} KRW\n"
        f"환율 우대, 거래 수수료에 따라 주식가격이 다를 수 있어양.\n"
    )

    CURRENCY_NOTICE = (
        "\n--- 환율안내 ---\n"
        "환율 정보 제공: Yahoo Finance {ticker}\n"
        "기준 환율: {base_amount} {source} -> {target:.2f} {service}\n"
        "매매기준 금액에 환전 수수료 1%, 해외 카드 결제 수수료 2.3% 기준 예상금액이며\n"
        "세금, 관세, 카드사 결제 수수료 및 혜택에 따라 최종 가격이 다를 수 있어양."
    )

    CURRENCY_NOTICE_ALT = (
        "\n--- 환율안내 ---\n"
        "환율 정보 제공: Yahoo Finance \n"
        "제시된 환율은 매매기준 기준 예상금액이며\n"
        "세금, 거래 은행 우대 환율에 따라서 가격이 다를 수 있어양."
    )