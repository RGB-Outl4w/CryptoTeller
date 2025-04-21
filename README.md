```python
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
```
# CryptoTeller Bot

CryptoTeller is a Telegram bot designed to provide real-time cryptocurrency prices and currency conversion rates. It supports multiple cryptocurrencies and fiat currencies, and it can be used in both private chats and groups. The bot uses CoinMarketCap and ExchangeRate-API to fetch the latest data.

## Features

- **Real-time Cryptocurrency Prices**: Get the latest prices for popular cryptocurrencies like Bitcoin (BTC), Ethereum (ETH), and more.
- **Currency Conversion**: Convert between various fiat currencies and cryptocurrencies.
- **Pagination**: Navigate through multiple pages of cryptocurrency data.
- **API Key Rotation**: Automatically rotate through multiple API keys to avoid rate limits.
- **(TON) Address Detection**: Automatically detects TON contract addresses in messages and provides token details and a DS link.

## Commands

- **/start**: Starts a conversation with the bot.
- **/crypto**: Displays the current prices of supported cryptocurrencies.
- **/help**: Displays a list of available commands and their descriptions.
- **/api**: (Developer Only) Shows the currently used API key.

## Setup

### Prerequisites

- Python 3.7 or higher
- A Telegram bot token (obtainable from [BotFather](https://t.me/BotFather))
- CoinMarketCap API key(s) (available from [CoinMarketCap](https://coinmarketcap.com/api/))
- ExchangeRate-API key(s) (available from [ExchangeRate-API](https://www.exchangerate-api.com/))

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/RGB-Outl4w/CryptoTeller.git
   cd CryptoTeller
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory and add your Telegram bot token:
   ```plaintext
   MAIN_KEY=your_telegram_bot_token
   ```

4. Update the `constants.py` file with your CoinMarketCap and ExchangeRate-API keys.

### Running the Bot

To start the bot, run:
```bash
python cryptoTeller.py
```

## Configuration

- **CoinMarketCap API Keys**: Add your API keys to the `CMC_API_KEYS` list in `constants.py`.
- **ExchangeRate-API Keys**: Add your API keys to the `EXCHANGE_RATE_API_KEYS` list in `constants.py`.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue if you have any suggestions or find any bugs.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

## Acknowledgments

- [CoinMarketCap](https://coinmarketcap.com/) for providing the cryptocurrency data.
- [ExchangeRate-API](https://www.exchangerate-api.com/) for providing the currency conversion rates.
- [pyTelegramBotAPI](https://github.com/eternnoir/pyTelegramBotAPI) for the Telegram bot library.

## Support

If you find this project useful, consider supporting it by donating or becoming a sponsor. Your support helps keep the project alive and continuously improved.

[![Donate](https://img.shields.io/badge/Donate-Boosty-orange.svg)](https://boosty.to/rgboutlaw/donate)
