import requests
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from statistics import mean, stdev
import nest_asyncio
import asyncio
from telegram import Bot

nest_asyncio.apply()

# === CONFIGURATION ===
# You can add/remove coins freely here. This list is used in your main loop.
COINS = ["bitcoin", "conflux-token", "bitget-token", "arbitrum", "pepe"]

COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
DAYS = 2
VS_CURRENCY = "usd"
EMA_PERIOD = 10
RSI_PERIOD = 14
Z_SCORE_THRESHOLD = 1.5
TP_THRESHOLD = 2.5
SL_THRESHOLD = -2.5
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30

# === TELEGRAM ALERT SETUP ===
TELEGRAM_BOT_TOKEN = "7345979104:AAEwHyn5PbYG3tkl6mJJ2vSejsCVeljkTMk"
TELEGRAM_CHAT_ID = "6027104508"
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# === DATA FETCHING FUNCTIONS ===

# Get historical price list for a coin from CoinGecko (every hour)
def fetch_prices(coin):
    url = COINGECKO_API_URL.format(coin=coin)
    params = {"vs_currency": VS_CURRENCY, "days": DAYS}
    try:
        response = requests.get(url, params=params)
        data = response.json()
        return [p[1] for p in data["prices"]] if "prices" in data else None
    except Exception as e:
        print(f"Error fetching data for {coin}: {e}")
        return None

# Calculate Z-score for price deviation
def z_score(prices):
    return (prices[-1] - mean(prices)) / stdev(prices) if len(prices) >= 30 else 0

# Generate EMA and RSI indicators from price list
def indicators(prices):
    df = pd.DataFrame(prices, columns=["close"])
    df["ema"] = EMAIndicator(df["close"], window=EMA_PERIOD).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], window=RSI_PERIOD).rsi()
    return df

# Send message to your Telegram bot
async def send_alert(text):
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

# === MAIN LOGIC FUNCTION ===
async def analyze():
    signal_found = False

    # === Step 1: Analyze BTC separately ===
    btc_prices = fetch_prices("bitcoin")
    if not btc_prices:
        return

    btc_z = z_score(btc_prices)
    btc_df = indicators(btc_prices)
    btc_price = btc_prices[-1]
    btc_ema = btc_df["ema"].iloc[-1]
    btc_rsi = btc_df["rsi"].iloc[-1]

    # Define BTC trend state
    btc_bullish = btc_price > btc_ema and 50 < btc_rsi < RSI_OVERBOUGHT and btc_z >= Z_SCORE_THRESHOLD
    btc_bearish = btc_price < btc_ema and btc_rsi > RSI_OVERSOLD and btc_z <= -Z_SCORE_THRESHOLD

    # === Step 2: Analyze PEPE only if BTC is trending ===
    if btc_bullish or btc_bearish:
        pepe_prices = fetch_prices("pepe")
        if pepe_prices:
            pepe_df = indicators(pepe_prices)
            pepe_price = pepe_prices[-1]
            pepe_ema = pepe_df["ema"].iloc[-1]
            pepe_rsi = pepe_df["rsi"].iloc[-1]

            # PEPE signal depends on BTC condition
            if btc_bullish and pepe_price > pepe_ema and pepe_rsi < RSI_OVERBOUGHT:
                signal = f"🔥 PEPE LONG | BTC Trend Bullish | PEPE: {pepe_price:.6f} | RSI: {pepe_rsi:.2f}"
                await send_alert(signal)
                signal_found = True
            elif btc_bearish and pepe_price < pepe_ema and pepe_rsi > RSI_OVERSOLD:
                signal = f"⚠️ PEPE SHORT | BTC Trend Bearish | PEPE: {pepe_price:.6f} | RSI: {pepe_rsi:.2f}"
                await send_alert(signal)
                signal_found = True

    # === Step 3: Loop through user-defined COINS list ===
    for coin in COINS:
        prices = fetch_prices(coin)
        if not prices:
            continue

        z = z_score(prices)
        df = indicators(prices)
        price, ema, rsi = prices[-1], df["ema"].iloc[-1], df["rsi"].iloc[-1]

        signal = None
        if z >= TP_THRESHOLD:
            signal = f"✅ TAKE PROFIT: {coin.upper()} Z-score {z:.2f}"
        elif z <= SL_THRESHOLD:
            signal = f"⚠️ STOP LOSS: {coin.upper()} Z-score {z:.2f}"
        elif abs(z) >= Z_SCORE_THRESHOLD:
            if price > ema and rsi < RSI_OVERBOUGHT:
                signal = f"📈 BUY: {coin.upper()} | Price: {price:.2f} | Z: {z:.2f} | RSI: {rsi:.2f}"
            elif price < ema and rsi > RSI_OVERSOLD:
                signal = f"📉 SELL: {coin.upper()} | Price: {price:.2f} | Z: {z:.2f} | RSI: {rsi:.2f}"

        if signal:
            print(signal)
            await send_alert(signal)
            signal_found = True
        else:
            print(f"No signal for {coin}")

    # If nothing met criteria
    if not signal_found:
        await send_alert("🕵️ No strong trading signals at this time.")

# === START ANALYSIS (Triggered every hour by scheduler or Replit timer) ===
if __name__ == "__main__":
    asyncio.run(analyze())
