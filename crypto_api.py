import requests
from datetime import datetime, timezone, timedelta
from constants import CMC_API_KEYS, EXCHANGE_RATE_API_KEYS, DEXSCREENER_API_URL

# Global variables for API key rotation
current_api_key_index = 0
current_exchange_rate_api_key_index = 0

# Caching dictionaries and timeouts
crypto_price_cache = {}
CRYPTO_CACHE_DURATION = timedelta(minutes=5) # Cache crypto prices for 5 minutes

exchange_rate_cache = {}
EXCHANGE_RATE_CACHE_DURATION = timedelta(hours=1) # Cache exchange rates for 1 hour

def get_crypto_prices(symbols):
    """
    Fetches the latest cryptocurrency prices from CoinMarketCap, using cache if available.

    Args:
        symbols (list): List of cryptocurrency symbols to fetch prices for.

    Returns:
        dict: A dictionary containing the prices and other details for the requested symbols.
    """
    global current_api_key_index, crypto_price_cache
    results = {}
    symbols_to_fetch = []
    now = datetime.now(timezone.utc)

    # Check cache first
    for symbol in symbols:
        if symbol in crypto_price_cache:
            cached_data, timestamp = crypto_price_cache[symbol]
            if now - timestamp < CRYPTO_CACHE_DURATION:
                results[symbol] = cached_data
            else:
                symbols_to_fetch.append(symbol)
        else:
            symbols_to_fetch.append(symbol)

    # Fetch missing symbols
    if symbols_to_fetch:
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        params = {"symbol": ",".join(symbols_to_fetch), "convert": "USD"}
        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}

        while True:
            try:
                response = requests.get(url, params=params, headers=headers, timeout=10) # Added timeout
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                if response.status_code == 200:
                    data = response.json().get("data", {})
                    fetch_time = datetime.now(timezone.utc)
                    for symbol in symbols_to_fetch:
                        if symbol in data and 'quote' in data[symbol] and 'USD' in data[symbol]['quote']:
                            price_data = data[symbol]["quote"]["USD"]
                            results[symbol] = price_data
                            crypto_price_cache[symbol] = (price_data, fetch_time) # Update cache
                        else:
                            # Handle cases where a specific symbol wasn't returned or data is incomplete
                            print(f"Warning: Data for symbol {symbol} not found or incomplete in API response.")
                            results[symbol] = None # Indicate data unavailable
                    break # Exit while loop on success

            except requests.exceptions.HTTPError as http_err:
                if response.status_code == 429:  # Rate limit
                    print(f"Rate limit hit for CMC API key index {current_api_key_index}. Switching key.")
                    # Try all available API keys before giving up
                    initial_key = current_api_key_index
                    while True:
                        switch_api_key()
                        if current_api_key_index == initial_key:
                            print("All API keys exhausted. Waiting 60 seconds before retry.")
                            time.sleep(60)  # Wait before retrying with first key
                        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}
                        try:
                            response = requests.get(url, params=params, headers=headers, timeout=10)
                            response.raise_for_status()
                            if response.status_code == 200:
                                break
                        except requests.exceptions.HTTPError as retry_err:
                            if retry_err.response.status_code != 429:
                                raise  # Re-raise if it's not a rate limit error
                elif 400 <= response.status_code < 500:
                    print(f"Client error occurred: {http_err} - Status Code: {response.status_code}")
                    if response.status_code == 401:  # Unauthorized
                        switch_api_key()  # Try another key
                        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}
                    else:
                        return results  # Return partial results for other client errors
                else:  # 500+ server errors
                    print(f"Server error occurred: {http_err} - Status Code: {response.status_code}")
                    time.sleep(2)  # Wait before retry on server error
            except requests.exceptions.RequestException as e:
                print(f"Error fetching crypto prices: {e}")
                retry_count = 0
                max_retries = 3
                retry_delay = 1  # Initial delay in seconds
                
                while retry_count < max_retries:
                    try:
                        print(f"Retrying request (attempt {retry_count + 1}/{max_retries})...")
                        time.sleep(retry_delay)
                        
                        # Switch API key before retry
                        switch_api_key()
                        headers = {"X-CMC_PRO_API_KEY": CMC_API_KEYS[current_api_key_index]}
                        
                        response = requests.get(url, params=params, headers=headers, timeout=10)
                        response.raise_for_status()
                        
                        if response.status_code == 200:
                            data = response.json().get("data", {})
                            fetch_time = datetime.now(timezone.utc)
                            for symbol in symbols_to_fetch:
                                if symbol in data and 'quote' in data[symbol] and 'USD' in data[symbol]['quote']:
                                    price_data = data[symbol]["quote"]["USD"]
                                    results[symbol] = price_data
                                    crypto_price_cache[symbol] = (price_data, fetch_time)
                            return results
                            
                    except requests.exceptions.RequestException as retry_error:
                        print(f"Retry attempt {retry_count + 1} failed: {retry_error}")
                        retry_count += 1
                        retry_delay *= 2  # Exponential backoff
                
                print("All retry attempts failed. Returning partial results.")
                break

    return results

def switch_api_key():
    """
    Switches to the next available CoinMarketCap API key.
    """
    global current_api_key_index
    current_api_key_index = (current_api_key_index + 1) % len(CMC_API_KEYS)

def get_currency_rate(from_currency, to_currency):
    """
    Fetches the currency conversion rate from ExchangeRate-API, using cache if available.

    Args:
        from_currency (str): The source currency code.
        to_currency (str): The target currency code.

    Returns:
        float: The conversion rate, or None if an error occurs or rate not found.
    """
    global current_exchange_rate_api_key_index, exchange_rate_cache
    cache_key = (from_currency, to_currency)
    now = datetime.now(timezone.utc)

    # Check cache
    if cache_key in exchange_rate_cache:
        rate, timestamp = exchange_rate_cache[cache_key]
        if now - timestamp < EXCHANGE_RATE_CACHE_DURATION:
            return rate

    # Fetch from API if not in cache or expired
    while True:
        current_api_key = EXCHANGE_RATE_API_KEYS[current_exchange_rate_api_key_index]
        try:
            url = f"https://v6.exchangerate-api.com/v6/{current_api_key}/pair/{from_currency}/{to_currency}"
            # Using the /pair endpoint is more direct
            response = requests.get(url, timeout=10) # Added timeout
            response.raise_for_status()

            data = response.json()
            if data.get("result") == "success":
                rate = data.get('conversion_rate')
                if rate is not None:
                    exchange_rate_cache[cache_key] = (float(rate), datetime.now(timezone.utc)) # Update cache
                    return float(rate)
                else:
                    print(f"Error: 'conversion_rate' not found in ExchangeRate-API response for {from_currency}/{to_currency}. Response: {data}")
                    return None # Rate not found in successful response
            elif data.get("error-type") == "invalid-key" or data.get("error-type") == "inactive-account":
                 print(f"ExchangeRate-API key {current_exchange_rate_api_key_index} is invalid or inactive. Switching key.")
                 switch_exchange_rate_api_key()
                 # Continue loop to retry with new key
            elif data.get("error-type") == "unsupported-code":
                 print(f"Error: Unsupported currency code used: {from_currency} or {to_currency}")
                 return None # Unsupported currency
            else:
                print(f"Error: ExchangeRate-API request failed. Response: {data}")
                error_type = data.get("error-type", "unknown")
                
                # Switch API key for specific error types that might benefit from using a different key
                if error_type in ["quota-reached", "plan-upgrade-required", "server-error"]:
                    print(f"Switching API key due to error: {error_type}")
                    switch_exchange_rate_api_key()
                    continue  # Retry with new key
                
                # For rate limiting, implement exponential backoff
                if error_type == "rate-limit-reached":
                    retry_delay = 2
                    max_retries = 3
                    for retry in range(max_retries):
                        print(f"Rate limit reached. Waiting {retry_delay} seconds before retry {retry + 1}/{max_retries}")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        switch_exchange_rate_api_key()
                        continue
                
                return None  # Failed for other unrecoverable reasons

        except requests.exceptions.RequestException as e:
            print(f"Error fetching exchange rate: {e}")
            retry_count = 0
            max_retries = 3
            retry_delay = 1  # Initial delay in seconds
            
            while retry_count < max_retries:
                try:
                    print(f"Retrying exchange rate request (attempt {retry_count + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    
                    # Switch API key before retry
                    switch_exchange_rate_api_key()
                    current_api_key = EXCHANGE_RATE_API_KEYS[current_exchange_rate_api_key_index]
                    
                    url = f"https://v6.exchangerate-api.com/v6/{current_api_key}/pair/{from_currency}/{to_currency}"
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    
                    data = response.json()
                    if data.get("result") == "success":
                        rate = data.get('conversion_rate')
                        if rate is not None:
                            exchange_rate_cache[cache_key] = (float(rate), datetime.now(timezone.utc))
                            return float(rate)
                    
                except requests.exceptions.RequestException as retry_error:
                    print(f"Retry attempt {retry_count + 1} failed: {retry_error}")
                    retry_count += 1
                    retry_delay *= 2  # Exponential backoff
            
            print("All retry attempts failed")
            return None  # Return None after all retries exhausted

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