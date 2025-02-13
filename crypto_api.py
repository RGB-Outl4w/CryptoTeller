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
from constants import CMC_API_KEYS, EXCHANGE_RATE_API_KEYS

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