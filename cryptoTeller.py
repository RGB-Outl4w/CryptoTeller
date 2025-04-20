import os
from dotenv import load_dotenv
from telebot import TeleBot, types
import requests
import time
import uuid
from constants import (
    HELP_PAGES, COOLDOWN_TIME_CRYPTO, CURRENCY_PAGES, SUPPORTED_CURRENCIES, CRYPTO_SYMBOLS, CMC_API_KEYS, TON_ADDRESS_REGEX
)
from crypto_api import get_crypto_prices, current_api_key_index, get_currency_rate, get_ton_token_info
import re

# Load environment variables
load_dotenv()
bot = TeleBot(os.getenv("MAIN_KEY"))

# Global variables for caching and rate limiting
last_used_time = {}
cached_crypto_data = {}
last_sent_message_ids = {}

@bot.message_handler(commands=["start"])
def handle_start(message):
    """Handles the /start command."""
    if message.chat.type == "private":
        bot.send_message(message.chat.id, "**What's up!** Add me into a group to access my functionality", parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "**Greetings!** I'm [CryptoTeller](https://t.me/crypteller_bot), your friend in the world of cryptocurrencies", parse_mode='Markdown', disable_web_page_preview=True)

def create_help_markup():
    """Creates the help menu pagination keyboard."""
    markup = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(f"{i}️⃣", callback_data=f"help_page_{i}")
        for i in range(1, 4)
    ]
    return markup.row(*buttons)

@bot.message_handler(commands=["help"])
def handle_help(message):
    """Displays the help message in multiple pages."""
    markup = create_help_markup()
    bot.send_message(
        message.chat.id,
        HELP_PAGES[1],
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("help_page_"))
def handle_help_pagination(call):
    """Handles help message pagination."""
    page_num = int(call.data.split("_")[-1])

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=HELP_PAGES[page_num],
        parse_mode='Markdown',
        reply_markup=create_help_markup()
    )

@bot.message_handler(commands=["crypto"])
def get_crypto_price(message):
    """Fetches and displays cryptocurrency prices."""
    global cached_crypto_data
    chat_id = str(message.chat.id)

    if message.chat.type in ("group", "supergroup"):
        if chat_id not in last_used_time or time.time() - last_used_time[chat_id] >= COOLDOWN_TIME_CRYPTO:
            try:
                # Fetch all currencies at once
                all_currencies = [symbol for page in CURRENCY_PAGES for symbol in page]
                cached_crypto_data = get_crypto_prices(all_currencies)
                last_used_time[chat_id] = time.time()

                # Display first page by default
                page1_data = get_current_page_data(0)
                message_text_page1 = format_price_message(page1_data)
                markup = create_pagination_keyboard(1)
                sent_message = bot.send_message(chat_id, message_text_page1, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=markup)

                if chat_id in last_sent_message_ids:
                    bot.delete_message(chat_id, last_sent_message_ids[chat_id])
                last_sent_message_ids[chat_id] = sent_message.message_id
            except requests.exceptions.RequestException as e:
                print(e)
                bot.send_message(chat_id, "Error fetching prices. Please try again.")
        else:
            remaining_time = COOLDOWN_TIME_CRYPTO - (time.time() - last_used_time[chat_id])
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            cooldown_text = f'*Command on cooldown.* Values will refresh in: *{minutes}* minutes *{seconds}* seconds'
            bot.send_message(chat_id, cooldown_text, parse_mode='Markdown')

def get_current_page_data(page):
    """Retrieves data for the specified page."""
    return {k: cached_crypto_data.get(k) for k in CURRENCY_PAGES[page] if k in cached_crypto_data}

def format_price_message(data):
    """Formats the cryptocurrency price message."""
    message_lines = []
    for symbol, values in data.items():
        try:
            price = values["price"]
            change_24h = values["percent_change_24h"]
            message_lines.append(f"• *${symbol}*:  {price:.6f}_$_ *({change_24h:.2f}%)*")
        except (TypeError, KeyError) as e:
            # If there's a formatting issue or missing data, skip or provide a fallback
            message_lines.append(f"• *${symbol}*:  Data not available")
            print(f"Skipping formatting issue for {symbol}: {e}")

    message_text = (
        "Current cryptocurrency prices:\n\n"
        + "\n".join(message_lines) +
        f"\n\n  ∟  Prices from: *CoinMarketCap*\n    🤍 Sponsor: None"
    )
    return message_text

def create_pagination_keyboard(current_page):
    """Creates a pagination keyboard for navigating between pages."""
    markup = types.InlineKeyboardMarkup()
    left_button = types.InlineKeyboardButton("⬅️", callback_data="prev_page")
    page_button = types.InlineKeyboardButton(f"{current_page}️⃣", callback_data=f"page_{current_page}")
    right_button = types.InlineKeyboardButton("➡️", callback_data="next_page")
    markup.row(left_button, page_button, right_button)
    return markup

@bot.callback_query_handler(func=lambda call: call.data in ["prev_page", "next_page", "page_1", "page_2", "page_3"])
def handle_pagination(call):
    """Handles pagination for cryptocurrency prices."""
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    # Extract the current page number from the call data
    current_page = int(call.message.reply_markup.keyboard[0][1].text[0]) - 1

    if call.data == "prev_page":
        page = max(0, current_page - 1)
    elif call.data == "next_page":
        page = min(len(CURRENCY_PAGES) - 1, current_page + 1)
    else:
        page = current_page

    data = get_current_page_data(page)
    message_text = format_price_message(data)
    markup = create_pagination_keyboard(page + 1)
    bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=message_text, parse_mode='Markdown', reply_markup=markup, disable_web_page_preview=True)

@bot.message_handler(commands=["api"])
def get_current_key(message):
    """Displays the currently used API key."""
    try:
        key_names = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF"]

        # Check if current_api_key_index is within the range of available keys
        if 0 <= current_api_key_index < len(CMC_API_KEYS):
            current_key_name = key_names[current_api_key_index] if current_api_key_index < len(key_names) else f"KEY {current_api_key_index + 1}"
            bot.send_message(message.chat.id, f"*Current API Key:* {current_key_name} (#{current_api_key_index + 1})", parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "Error: API key index is out of range.", parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, "`Error: Failed to check current API key.`", parse_mode='Markdown')
        print(f"Error checking API key: {e}")

@bot.message_handler(commands=["devblog"])
def share_dev_channel(message):
    """Shares the development blog channel."""
    try:
        bot.reply_to(message, "• [ʀɢʙ.ᴅᴇᴠ](https://t.me/rgbdevelopment) - Your key to knowledge.", parse_mode='Markdown')
    except:
        bot.send_message(message.chat.id, "`Error: Could not access desired function.`", parse_mode='Markdown')

@bot.inline_handler(lambda query: len(query.query) > 0)
def handle_inline_query(inline_query):
    """Handles inline queries for currency and cryptocurrency conversions."""
    try:
        user_input = inline_query.query.strip().upper()
        # Regex to parse input: optional amount, currency1, optional 'to', currency2
        match = re.match(r"^(?:(\d*\.?\d+)\s)?([A-Z]{3,5})\s(?:TO\s)?([A-Z]{3,5})$", user_input)

        if not match:
            # Try parsing just two currencies (amount defaults to 1)
            match_simple = re.match(r"^([A-Z]{3,5})\s(?:TO\s)?([A-Z]{3,5})$", user_input)
            if match_simple:
                amount = 1.0
                from_currency = match_simple.group(1)
                to_currency = match_simple.group(2)
            else:
                bot.answer_inline_query(inline_query.id, [], switch_pm_text="Invalid format. Use: [amount] CUR1 [to] CUR2")
                return
        else:
            amount_str, from_currency, to_currency = match.groups()
            amount = float(amount_str) if amount_str else 1.0

        # Validate currencies
        if from_currency not in SUPPORTED_CURRENCIES:
            bot.answer_inline_query(inline_query.id, [], switch_pm_text=f"Unsupported currency: {from_currency}")
            return
        if to_currency not in SUPPORTED_CURRENCIES:
            bot.answer_inline_query(inline_query.id, [], switch_pm_text=f"Unsupported currency: {to_currency}")
            return

        is_from_crypto = from_currency in CRYPTO_SYMBOLS
        is_to_crypto = to_currency in CRYPTO_SYMBOLS

        result_text = ""
        error_message = None

        # Case 1: Fiat to Fiat
        if not is_from_crypto and not is_to_crypto:
            rate = get_currency_rate(from_currency, to_currency)
            if rate is not None:
                converted_amount = amount * rate
                result_text = f"💸 {amount:,.2f} {from_currency} = 💸 {converted_amount:,.2f} {to_currency}"
            else:
                error_message = f"Could not get rate for {from_currency}/{to_currency}."

        # Case 2: Crypto to Fiat
        elif is_from_crypto and not is_to_crypto:
            crypto_data = get_crypto_prices([from_currency])
            crypto_price_usd_data = crypto_data.get(from_currency)

            if crypto_price_usd_data and 'price' in crypto_price_usd_data:
                crypto_price_usd = crypto_price_usd_data['price']
                if to_currency == "USD":
                    converted_amount = amount * crypto_price_usd
                    result_text = f"🪙 {amount:,.4f} ${from_currency} = 💸 {converted_amount:,.2f} {to_currency}"
                else:
                    usd_to_fiat_rate = get_currency_rate("USD", to_currency)
                    if usd_to_fiat_rate is not None:
                        converted_amount = amount * crypto_price_usd * usd_to_fiat_rate
                        result_text = f"🪙 {amount:,.4f} ${from_currency} = 💸 {converted_amount:,.2f} {to_currency}"
                    else:
                        error_message = f"Could not get rate for USD/{to_currency}."
            else:
                error_message = f"Could not get price for ${from_currency}."

        # Case 3: Fiat to Crypto
        elif not is_from_crypto and is_to_crypto:
            crypto_data = get_crypto_prices([to_currency])
            crypto_price_usd_data = crypto_data.get(to_currency)

            if crypto_price_usd_data and 'price' in crypto_price_usd_data:
                crypto_price_usd = crypto_price_usd_data['price']
                if from_currency == "USD":
                    converted_amount = amount / crypto_price_usd
                    result_text = f"💸 {amount:,.2f} {from_currency} = 🪙 {converted_amount:,.6f} ${to_currency}"
                else:
                    fiat_to_usd_rate = get_currency_rate(from_currency, "USD")
                    if fiat_to_usd_rate is not None:
                        converted_amount = (amount * fiat_to_usd_rate) / crypto_price_usd
                        result_text = f"💸 {amount:,.2f} {from_currency} = 🪙 {converted_amount:,.6f} ${to_currency}"
                    else:
                        error_message = f"Could not get rate for {from_currency}/USD."
            else:
                error_message = f"Could not get price for ${to_currency}."

        # Case 4: Crypto to Crypto
        elif is_from_crypto and is_to_crypto:
            crypto_data = get_crypto_prices([from_currency, to_currency])
            from_price_data = crypto_data.get(from_currency)
            to_price_data = crypto_data.get(to_currency)

            if from_price_data and 'price' in from_price_data and to_price_data and 'price' in to_price_data:
                from_price_usd = from_price_data['price']
                to_price_usd = to_price_data['price']
                if to_price_usd > 0: # Avoid division by zero
                    converted_amount = amount * (from_price_usd / to_price_usd)
                    result_text = f"🪙 {amount:,.4f} ${from_currency} = 🪙 {converted_amount:,.6f} ${to_currency}"
                else:
                    error_message = f"Price for ${to_currency} is zero."
            else:
                missing = []
                if not (from_price_data and 'price' in from_price_data):
                    missing.append(from_currency)
                if not (to_price_data and 'price' in to_price_data):
                    missing.append(to_currency)
                error_message = f"Could not get price for ${' and '.join(missing)}."

        # Send result or error
        if result_text:
            result = types.InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=result_text,
                input_message_content=types.InputTextMessageContent(
                    message_text=result_text,
                    parse_mode='Markdown'
                ),
                thumbnail_url="https://i.imgur.com/ubbkPd7.jpeg"
            )
            bot.answer_inline_query(inline_query.id, [result], cache_time=60) # Cache inline result for 1 min
        else:
            bot.answer_inline_query(inline_query.id, [], switch_pm_text=error_message or "Conversion failed.")

    except Exception as e:
        print(f"Error in inline query handler: {e}")
        bot.answer_inline_query(inline_query.id, [], switch_pm_text="An error occurred.")

@bot.message_handler(func=lambda message: True)
def handle_contract_address(message):
    """Detects TON contract addresses and fetches token info."""
    if not message.text:
        return

    matches = re.findall(TON_ADDRESS_REGEX, message.text)
    if not matches:
        return

    # Process only the first found address to avoid spam
    address = matches[0]

    response_text, error_message = get_ton_token_info(address)

    if response_text:
        # Send the formatted message
        bot.reply_to(message, response_text, parse_mode='Markdown', disable_web_page_preview=True)
    elif error_message:
        # Notify user about the error
        bot.reply_to(message, error_message, parse_mode='Markdown')

# Start polling
if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(none_stop=True)
