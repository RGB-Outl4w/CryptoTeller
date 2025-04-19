# .------------------------------------------------------------------------------------------------------------.
# |                                                                                                            |
# |                                                                                                            |
# |                        ██████╗  ██████╗ ██████╗    ██████╗ ███████╗██╗   ██╗                               |
# |                        ██╔══██╗██╔════╝ ██╔══██╗   ██╔══██╗██╔════╝██║   ██║                               |
# |                        ██████╔╝██║  ███╗██████╔╝   ██║  ██║█████╗  ██║   ██║                               |
# |                        ██╔══██╗██║   ██║██╔══██╗   ██║  ██║██╔══╝  ╚██╗ ██╔╝                               |
# |                        ██║  ██║╚██████╔╝██████╔╝██╗██████╔╝███████╗ ╚████╔╝                                |
# |                        ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝╚═════╝ ╚══════╝  ╚═══╝                                 |
# |                                                                                                            |
# |                                                                                                            |
# |                                                                                                            |
# |    █████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗█████╗        |
# |    ╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝╚════╝        |
# |                                                                                                            |
# |                                                                                                            |
# |                                                                                                            |
# |     ██████╗██████╗ ██╗   ██╗██████╗ ████████╗ ██████╗ ████████╗███████╗██╗     ██╗     ███████╗██████╗     |
# |    ██╔════╝██╔══██╗╚██╗ ██╔╝██╔══██╗╚══██╔══╝██╔═══██╗╚══██╔══╝██╔════╝██║     ██║     ██╔════╝██╔══██╗    |
# |    ██║     ██████╔╝ ╚████╔╝ ██████╔╝   ██║   ██║   ██║   ██║   █████╗  ██║     ██║     █████╗  ██████╔╝    |
# |    ██║     ██╔══██╗  ╚██╔╝  ██╔═══╝    ██║   ██║   ██║   ██║   ██╔══╝  ██║     ██║     ██╔══╝  ██╔══██╗    |
# |    ╚██████╗██║  ██║   ██║   ██║        ██║   ╚██████╔╝   ██║   ███████╗███████╗███████╗███████╗██║  ██║    |
# |     ╚═════╝╚═╝  ╚═╝   ╚═╝   ╚═╝        ╚═╝    ╚═════╝    ╚═╝   ╚══════╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝    |
# |                                                                                                            |
# |                                                                                                            |
# '------------------------------------------------------------------------------------------------------------'


# CoinMarketCap API keys (replace with your own keys)
CMC_API_KEYS = [
    "your_coinmarketcap_api_key_1",
    "your_coinmarketcap_api_key_2",
    # Add more keys as needed
]

# ExchangeRate-API keys (replace with your own keys)
EXCHANGE_RATE_API_KEYS = [
    "your_exchangerate_api_key_1",
    "your_exchangerate_api_key_2",
    # Add more keys as needed
]

# Sponsors and donators (replace with your own sponsors/donators)
SPONSORS_AND_DONATORS = (
    "[Sponsor Name](https://example.com)",  # Example sponsor
    # Add more sponsors/donators as needed
)

# Currency pages for pagination
CURRENCY_PAGES = [
    ["TON", "BTC", "ETH", "SUI", "USDT", "SOL"],
    ["NOT", "PUNK", "ARBUZ", "DOGE", "SHIT", "DOGS"],
    ["REDO", "DUREV", "WALL", "STON", "GRAM", "RAFF"]
]

# Supported currencies for conversion
SUPPORTED_CURRENCIES = [
    "USD", "RUB", "EUR", "GBP", "JPY", "KZT", "UAH",
    "TON", "BTC", "ETH", "DOGE", "DOGS", "NOT", "SOL", "STON", "GRAM", "SUI"
]

# Cryptocurrency symbols
CRYPTO_SYMBOLS = ["TON", "BTC", "ETH", "DOGE", "DOGS", "NOT", "SOL", "STON", "GRAM", "SUI"]

# Regex for TON contract addresses (adjust as needed)
# Matches Base64url (EQ/UQ prefix) and the 48-char format
TON_ADDRESS_REGEX = r"\b(?:(?:EQ|UQ)[A-Za-z0-9_\-]{46}|[A-Za-z0-9]{48})\b"

# DexScreener API endpoint
DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/search?q={address}"

# Cooldown times for commands (in seconds)
COOLDOWN_TIME_CRYPTO = 10  # Cooldown for /crypto command
COOLDOWN_TIME_TOP = 3600   # Cooldown for /top command