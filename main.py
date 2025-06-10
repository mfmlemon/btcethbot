# === CoinGecko BTC/ETH Arbitrage Signal Bot with Filters ===
from flask import Flask
from threading import Thread
import requests
import time
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from statistics import mean, stdev
import nest_asyncio
import asyncio
from telegram import Bot
from keep_alive import keep_alive

nest_asyncio.apply()
# Start the keep-alive server
keep_alive()
print("🌐 Keep-alive server started on port 8080")
print("🤖 Starting trading bot...")


# === CONFIGURATION ===
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/{coin}/market_chart"
COINS = ["bitcoin", "ethereum", "cosmos","dexe", "bitget-token",]
DAYS = 2
VS_CURRENCY = "usd"
Z_SCORE_THRESHOLD = 1.5
EMA_PERIOD = 10
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
SL_THRESHOLD = -2.5  # z-score stop loss
TP_THRESHOLD = 2.5   # z-score take profit
CHECK_INTERVAL = 3600  # every hour in seconds
TELEGRAM_BOT_TOKEN = "7345979104:AAEwHyn5PbYG3tkl6mJJ2vSejsCVeljkTMk"
TELEGRAM_CHAT_ID = "6027104508"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# === FUNCTIONS ===
def fetch_coin_data(coin):
    url = COINGECKO_API_URL.format(coin=coin)
    params = {"vs_currency": VS_CURRENCY, "days": DAYS}
    response = requests.get(url, params=params)
    data = response.json()
    if "prices" not in data:
        print(f"[ERROR] No 'prices' key found for {coin}: {data}")
        return None
    return [price[1] for price in data["prices"]]  # Only closing prices

def calculate_zscore(prices):
    if len(prices) < 30:
        return 0
    mean_val = mean(prices)
    std_val = stdev(prices)
    return (prices[-1] - mean_val) / std_val if std_val != 0 else 0

def apply_technical_indicators(prices):
    df = pd.DataFrame(prices, columns=["close"])
    df["ema"] = EMAIndicator(close=df["close"], window=EMA_PERIOD).ema_indicator()
    df["rsi"] = RSIIndicator(close=df["close"], window=RSI_PERIOD).rsi()
    return df

async def send_signal(message):
 await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


async def check_signals():
    signal_found = False
    for coin in COINS:
        prices = fetch_coin_data(coin)
        if not prices:
            continue

        z_score = calculate_zscore(prices)
        df = apply_technical_indicators(prices)

        current_price = prices[-1]
        latest_ema = df["ema"].iloc[-1]
        latest_rsi = df["rsi"].iloc[-1]

        signal = None

        if z_score >= TP_THRESHOLD:
            signal = f"[TAKE PROFIT] {coin} z-score high ({z_score:.2f})!"
        elif z_score <= SL_THRESHOLD:
            signal = f"[STOP LOSS] {coin} z-score low ({z_score:.2f})!"
        elif abs(z_score) >= Z_SCORE_THRESHOLD:
            if current_price > latest_ema and latest_rsi < RSI_OVERBOUGHT:
                signal = f"[BUY] {coin.upper()} | Price: {current_price:.2f} | Z-score: {z_score:.2f} | RSI: {latest_rsi:.2f}"
            elif current_price < latest_ema and latest_rsi > RSI_OVERSOLD:
                signal = f"[SELL] {coin.upper()} | Price: {current_price:.2f} | Z-score: {z_score:.2f} | RSI: {latest_rsi:.2f}"

        if signal:
            print(f"[SIGNAL] {signal}")
            signal_found = True 
            await send_signal(signal)
        else:
            print(f"[NO SIGNAL] {coin}: Z-score within range")
       # ✅ Add this block at the END (outside the for loop)
    if not signal_found:
        relax_msg = "relax I'm here – no trading signal at this time"
        print(relax_msg)
        await send_signal(relax_msg)          
async def main():
    while True:
        await check_signals()
        await asyncio.sleep(CHECK_INTERVAL)
# === RUN THE BOT ===
asyncio.run(main())
