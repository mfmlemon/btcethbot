# === BTC/ETH Arbitrage Signal Bot ===

from keep_alive import keep_alive
import requests
import time
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from statistics import mean, stdev
import nest_asyncio
import asyncio
from telegram import Bot

# === Enable nested event loop for Replit ===
nest_asyncio.apply()

# === Start UptimeRobot-compatible server ===
keep_alive()

print("🌐 Keep-alive web server launched")
print("🤖 Running crypto signal bot...")

# === Configuration ===
COINS = ["bitcoin", "ethereum", "cosmos", "dexe", "bitget-token"]
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
CHECK_INTERVAL = 3600  # Every hour

TELEGRAM_BOT_TOKEN = "7345979104:AAEwHyn5PbYG3tkl6mJJ2vSejsCVeljkTMk"
TELEGRAM_CHAT_ID = "6027104508"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# === Functions ===
def fetch_coin_data(coin):
    try:
        url = COINGECKO_API_URL.format(coin=coin)
        params = {"vs_currency": VS_CURRENCY, "days": DAYS}
        response = requests.get(url, params=params)
        data = response.json()
        return [entry[1] for entry in data["prices"]] if "prices" in data else None
    except Exception as e:
        print(f"[ERROR] {coin}: {e}")
        return None

def calculate_zscore(prices):
    if len(prices) < 30:
        return 0
    return (prices[-1] - mean(prices)) / stdev(prices)

def apply_indicators(prices):
    df = pd.DataFrame(prices, columns=["close"])
    df["ema"] = EMAIndicator(close=df["close"], window=EMA_PERIOD).ema_indicator()
    df["rsi"] = RSIIndicator(close=df["close"], window=RSI_PERIOD).rsi()
    return df

async def send_signal(text):
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

async def check_signals():
    signal_found = False
    for coin in COINS:
        prices = fetch_coin_data(coin)
        if not prices:
            continue

        z = calculate_zscore(prices)
        df = apply_indicators(prices)
        price = prices[-1]
        ema = df["ema"].iloc[-1]
        rsi = df["rsi"].iloc[-1]
        signal = None

        if z >= TP_THRESHOLD:
            signal = f"✅ [TAKE PROFIT] {coin.upper()} z-score high ({z:.2f})"
        elif z <= SL_THRESHOLD:
            signal = f"⚠️ [STOP LOSS] {coin.upper()} z-score low ({z:.2f})"
        elif abs(z) >= Z_SCORE_THRESHOLD:
            if price > ema and rsi < RSI_OVERBOUGHT:
                signal = f"📈 [BUY] {coin.upper()} | Price: {price:.2f} | Z: {z:.2f} | RSI: {rsi:.2f}"
            elif price < ema and rsi > RSI_OVERSOLD:
                signal = f"📉 [SELL] {coin.upper()} | Price: {price:.2f} | Z: {z:.2f} | RSI: {rsi:.2f}"

        if signal:
            print(signal)
            await send_signal(signal)
            signal_found = True
        else:
            print(f"[NO SIGNAL] {coin}: Z-score neutral")

    if not signal_found:
        await send_signal("😴 No signals for now. Monitoring continues...")

async def main():
    while True:
        await check_signals()
        await asyncio.sleep(CHECK_INTERVAL)

# === Start Async Bot ===
asyncio.run(main())