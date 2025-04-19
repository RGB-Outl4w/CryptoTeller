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


import requests
from datetime import datetime, timezone
from constants import CMC_API_KEYS, EXCHANGE_RATE_API_KEYS, DEXSCREENER_API_URL

# Global variables for API key rotation
current_api_key_index = 0
current_exchange_rate_api_key_index = 0

def get_crypto_prices(symbols):
    """
    Fetches the latest cryptocurrency prices from CoinMarketCap.

    Args:
        symbols (list): List of cryptocurrency symbols to fetch prices for.

    Returns:
        dict: A dictionary containing the prices and other details for the requested symbols.
    """
    global current_api_key_index
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": ",".join(symbols), "convert": "USD"}
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}

    while True:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            break
        elif response.status_code == 429:
            switch_api_key()
            headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}
        else:
            response.raise_for_status()

    data = response.json()["data"]
    return {symbol: data[symbol]["quote"]["USD"] for symbol in symbols}

def switch_api_key():
    """
    Switches to the next available CoinMarketCap API key.
    """
    global current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(CMC_API_KEYS)

def get_currency_rate(from_currency, to_currency):
    """
    Fetches the currency conversion rate from ExchangeRate-API.

    Args:
        from_currency (str): The source currency code.
        to_currency (str): The target currency code.

    Returns:
        float: The conversion rate, or None if an error occurs.
    """
    global current_exchange_rate_api_key_index

    while True:
        current_api_key = EXCHANGE_RATE_API_KEYS[current_exchange_rate_api_key_index]
        try:
            url = f"https://v6.exchangerate-api.com/v6/{current_api_key}/latest/{from_currency}"
            response = requests.get(url)
            response.raise_for_status()

            data = response.json()
            if "result" in data and data["result"] == "success":
                return float(data['conversion_rates'][to_currency])
            else:
                print(f"Error: ExchangeRate-API request failed. Response: {data}")
                switch_exchange_rate_api_key()

        except requests.exceptions.RequestException as e:
            print(f"Error fetching exchange rate: {e}")
            switch_exchange_rate_api_key()

def switch_exchange_rate_api_key():
    """
    Switches to the next available ExchangeRate-API key.
    """
    global current_exchange_rate_api_key_index
    current_exchange_rate_api_key_index = (current_exchange_rate_api_key_index + 1) % len(EXCHANGE_RATE_API_KEYS)

def format_large_number(num):
    if num >= 1_000_000:
        return f"{num / 1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)

def calculate_age(timestamp_ms):
    if not timestamp_ms:
        return "N/A"
    dt_object = datetime.fromtimestamp(timestamp_ms / 1000, timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt_object
    days = delta.days
    hours = delta.seconds // 3600
    if days > 0:
        return f"{days}d"
    elif hours > 0:
        return f"{hours}h"
    else:
        return "<1h"

def get_ton_token_info(address):
    """Fetches TON token information from DexScreener using a contract address."""
    try:
        api_url = DEXSCREENER_API_URL.format(address=address)
        response = requests.get(api_url)
        response.raise_for_status() # Raise an exception for bad status codes
        data = response.json()

        if data and data.get('pairs'):
            # Filtering for TON pairs specifically
            ton_pairs = [p for p in data['pairs'] if p.get('chainId') == 'ton']
            if not ton_pairs:
                 print(f"No TON pair found for address: {address}")
                 return None, "No TON pair found."

            # Sort by liquidity or volume if needed, here just taking the first TON pair
            pair = ton_pairs[0]

            # Extract data
            base_token = pair.get('baseToken', {})
            token_name = base_token.get('name', 'N/A')
            token_symbol = base_token.get('symbol', 'N/A')
            price_usd_str = pair.get('priceUsd', '0')
            price_usd = float(price_usd_str) if price_usd_str else 0.0
            price_change_h1 = pair.get('priceChange', {}).get('h1', 0)
            price_change_h24 = pair.get('priceChange', {}).get('h24', 0)
            volume_h24 = pair.get('volume', {}).get('h24', 0)
            liquidity_usd = pair.get('liquidity', {}).get('usd', 0)
            market_cap = pair.get('fdv', 0) # Using FDV as Market Cap proxy
            pair_created_at = pair.get('pairCreatedAt') # Timestamp in ms
            dexscreener_url = pair.get('url', '#')

            # Calculate age
            age = calculate_age(pair_created_at)

            response_text = (
                f"💎 *{token_name} (${token_symbol})*\n"
                f"`{address}`\n\n"
                f"⛓️ Chain: TON | ⏳ Age: {age}\n\n"
                f"📊 *Token Stats*\n"
                f" ├─ Price: *${price_usd:.6f}*\n"
                f" ├─ 1H Change: {price_change_h1:+.2f}%\n"
                f" ├─ 24H Change: {price_change_h24:+.2f}%\n"
                f" ├─ Volume (24H): *${format_large_number(volume_h24)}*\n"
                f" ├─ Liquidity: *${format_large_number(liquidity_usd)}*\n"
                f" └─ Market Cap (FDV): *${format_large_number(market_cap)}*\n\n"
                f"🔗 [View on DexScreener]({dexscreener_url})"
            )
            return response_text, None # Success

        else:
            print(f"No pair data found on DexScreener for address: {address}")
            return None, f"⚠️ Could not find token information for address: `{address}`"

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from DexScreener for {address}: {e}")
        return None, "⚠️ Error fetching token data from DexScreener. Please try again later."
    except Exception as e:
        print(f"An unexpected error occurred while processing address {address}: {e}")
        return None, "⚠️ An unexpected error occurred while processing the address."