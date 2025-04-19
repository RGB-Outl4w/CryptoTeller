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


import os
from dotenv import load_dotenv
from telebot import TeleBot, types
import requests
import time
import uuid
import constants
from crypto_api import get_crypto_prices, current_api_key_index, get_currency_rate

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

@bot.message_handler(commands=["help"])
def handle_help(message):
    """Displays the help message."""
    help_text = """
**Currently I can only provide information about cryptocurrencies, but nobody knows, how far this will get.**
Here are my available commands:

• **/start** - Starts a conversation with me.
• **/crypto** - Shows the prices of specific cryptocurrencies.

• **/help** - Displays this help message.
• **/api** - **[DEV ONLY]** Shows currently used API key.
"""
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=["crypto"])
def get_crypto_price(message):
    """Fetches and displays cryptocurrency prices."""
    global cached_crypto_data
    chat_id = str(message.chat.id)

    if message.chat.type in ("group", "supergroup"):
        if chat_id not in last_used_time or time.time() - last_used_time[chat_id] >= constants.COOLDOWN_TIME_CRYPTO:
            try:
                # Fetch all currencies at once
                all_currencies = [symbol for page in constants.CURRENCY_PAGES for symbol in page]
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
            remaining_time = constants.COOLDOWN_TIME_CRYPTO - (time.time() - last_used_time[chat_id])
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            cooldown_text = f'*Command on cooldown.* Values will refresh in: *{minutes}* minutes *{seconds}* seconds'
            bot.send_message(chat_id, cooldown_text, parse_mode='Markdown')

def get_current_page_data(page):
    """Retrieves data for the specified page."""
    return {k: cached_crypto_data.get(k) for k in constants.CURRENCY_PAGES[page] if k in cached_crypto_data}

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
        page = min(len(constants.CURRENCY_PAGES) - 1, current_page + 1)
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
        if 0 <= current_api_key_index < len(constants.CMC_API_KEYS):
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
        user_input = inline_query.query.upper()
        parts = user_input.split()

        if len(parts) == 2:  # Expecting two currencies
            from_currency = parts[0]
            to_currency = parts[1]
            amount = 1.0  # Default amount

        elif len(parts) == 3:  # Expecting amount and two currencies
            # Check if the first element is a number
            try:
                amount = float(parts[0])
                from_currency = parts[1]
                to_currency = parts[2]
            except ValueError:
                # If it's not a number, assume it's a currency
                from_currency = parts[0]
                to_currency = parts[1]
                amount = 1.0

            if (from_currency in constants.SUPPORTED_CURRENCIES and
                to_currency in constants.SUPPORTED_CURRENCIES and
                not (from_currency in ["TON", "BTC", "ETH", "DOGE", "DOGS", "NOT", "SOL", "STON", "GRAM"] or
                     to_currency in ["TON", "BTC", "ETH", "DOGE", "DOGS", "NOT", "SOL", "STON", "GRAM"])):

                # Both are fiat currencies and NOT crypto, use ExchangeRate-API
                rate = get_currency_rate(from_currency, to_currency)

                if rate is not None:
                    converted_amount = amount * rate
                    result_text = f"💸 {amount:.2f} {from_currency} = 💸 {converted_amount:.2f} {to_currency}"

                    result = types.InlineQueryResultArticle(
                        id=str(uuid.uuid4()),
                        title=result_text,
                        input_message_content=types.InputTextMessageContent(
                            message_text=result_text,
                            parse_mode='Markdown'
                        ),
                        thumbnail_url="https://i.imgur.com/ubbkPd7.jpeg"
                    )
                    bot.answer_inline_query(inline_query.id, [result])
                else:
                    bot.answer_inline_query(inline_query.id, [], switch_pm_text="Invalid currency codes.")

            elif (from_currency in constants.SUPPORTED_CURRENCIES or to_currency in constants.SUPPORTED_CURRENCIES):
                # At least one is crypto, use CoinMarketCap

                try:
                    # Determine which currency is crypto and which is fiat
                    if from_currency in ["TON", "BTC", "ETH", "DOGE", "DOGS", "NOT", "SOL", "STON", "GRAM"]:
                        crypto_symbol = from_currency
                        fiat_currency = to_currency
                    else:
                        crypto_symbol = to_currency
                        fiat_currency = from_currency

                    crypto_data = get_crypto_prices([crypto_symbol])
                    crypto_price_usd = crypto_data.get(crypto_symbol, {}).get("price")

                    if crypto_price_usd is not None:
                        # Get the USD to target fiat currency rate:
                        usd_to_fiat_rate = get_currency_rate("USD", fiat_currency)

                        if usd_to_fiat_rate is None:
                            bot.answer_inline_query(inline_query.id, [], switch_pm_text=f"Unable to get exchange rate for USD/{fiat_currency}")
                        else:
                            if from_currency == crypto_symbol:  # Convert crypto to fiat
                                converted_amount = amount * crypto_price_usd * usd_to_fiat_rate
                                result_text = f"🪙 {amount:.2f} ${from_currency} = 💸 {converted_amount:.2f} {to_currency}"
                            else:  # Convert fiat to crypto
                                converted_amount = amount / crypto_price_usd * usd_to_fiat_rate
                                result_text = f"💸 {amount:.2f} {from_currency} = 🪙 {converted_amount:.2f} ${to_currency}"

                            result = types.InlineQueryResultArticle(
                                id=str(uuid.uuid4()),
                                title=result_text,
                                input_message_content=types.InputTextMessageContent(
                                    message_text=result_text,
                                    parse_mode='Markdown'
                                ),
                                thumbnail_url="https://i.imgur.com/ubbkPd7.jpeg"
                            )
                            bot.answer_inline_query(inline_query.id, [result])
                    else:
                        bot.answer_inline_query(inline_query.id, [], switch_pm_text="Cryptocurrency data not found.")

                except Exception as e:
                    print(f"Error fetching cryptocurrency data: {e}")
                    bot.answer_inline_query(inline_query.id, [], switch_pm_text="Error fetching cryptocurrency data.")

            else:
                bot.answer_inline_query(inline_query.id, [], switch_pm_text="At least one currency should be supported.")

        else:
            bot.answer_inline_query(inline_query.id, [], switch_pm_text="Invalid format. Use: amount currency1 currency2")

    except Exception as e:
        print(f"Error in inline query handler: {e}")
        bot.answer_inline_query(inline_query.id, [], switch_pm_text="An error occurred.")

if __name__ == "__main__":
    bot.infinity_polling()