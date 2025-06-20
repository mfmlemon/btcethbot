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

# Replace these with your actual values or load from environment variables if using GitHub Secrets
TELEGRAM_BOT_TOKEN = "7345979104:AAEwHyn5PbYG3tkl6mJJ2vSejsCVeljkTMk"
TELEGRAM_CHAT_ID = "6027104508"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# === FUNCTIONS ===
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

def z_score(prices):
    return (prices[-1] - mean(prices)) / stdev(prices) if len(prices) >= 30 else 0

def indicators(prices):
    df = pd.DataFrame(prices, columns=["close"])
    df["ema"] = EMAIndicator(df["close"], window=EMA_PERIOD).ema_indicator()
    df["rsi"] = RSIIndicator(df["close"], window=RSI_PERIOD).rsi()
    return df

async def send_alert(text):
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

async def analyze():
    signal_found = False
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

    if not signal_found:
        await send_alert("🕵️ No strong trading signals at this time.")

# === EXECUTE ONCE ===
if __name__ == "__main__":
    asyncio.run(analyze())
