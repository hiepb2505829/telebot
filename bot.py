import ccxt
import pandas as pd
import time
import requests

# ================== CẤU HÌNH ==================
TIMEFRAME = '4h'
LOOKBACK = 30
VOLUME_MULTIPLIER = 1.8
CHECK_INTERVAL = 600  # 10 phút

TELEGRAM_TOKEN = '8562616165:AAFucsz61WmelMnjHFm5NjRJCe6aeTeeqk4'
CHAT_ID = 6335578454

# ================== KẾT NỐI BINANCE ==================
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# ================== LẤY TOÀN BỘ ALTCOIN USDT ==================
def get_usdt_symbols(exchange, min_volume=100_000_000):
    markets = exchange.load_markets()
    symbols = []

    for symbol, data in markets.items():
        if (
            symbol.endswith('/USDT')
            and data['active']
            and not symbol.startswith(('USDC', 'BUSD', 'TUSD', 'FDUSD'))
        ):
            try:
                ticker = exchange.fetch_ticker(symbol)
                if ticker['quoteVolume'] and ticker['quoteVolume'] > min_volume:
                    symbols.append(symbol)
            except:
                continue

    return symbols

SYMBOLS = get_usdt_symbols(exchange)
print(f"📊 Đang quét {len(SYMBOLS)} cặp USDT")

# ================== TELEGRAM ==================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": msg
    })

print("🚀 Bot đang chạy...")

last_alert = {}

# ================== MAIN LOOP ==================
while True:
    for symbol in SYMBOLS:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, TIMEFRAME, limit=300)
            df = pd.DataFrame(
                ohlcv,
                columns=['time', 'open', 'high', 'low', 'close', 'volume']
            )

            # EMA
            df['ema34'] = df['close'].ewm(span=34).mean()
            df['ema89'] = df['close'].ewm(span=89).mean()
            df['ema200'] = df['close'].ewm(span=200).mean()

            last = df.iloc[-1]

            # Chỉ báo khi nến H4 đóng
            if time.time() * 1000 < last['time'] + 4*60*60*1000:
                continue

            prev = df.iloc[-LOOKBACK-1:-1]
            highest_high = prev['high'].max()
            lowest_low = prev['low'].min()
            avg_volume = prev['volume'].mean()

            key = f"{symbol}_{last['time']}"
            if key in last_alert:
                continue

            # BREAK UP
            if (
                last['close'] > highest_high and
                last['volume'] > avg_volume * VOLUME_MULTIPLIER and
                last['close'] > last['ema200'] and
                last['ema34'] > last['ema89']
            ):
                send_telegram(
                    f"🚀 BREAK UP H4\n"
                    f"{symbol}\n"
                    f"Close: {last['close']:.4f}"
                )
                last_alert[key] = True

            # BREAK DOWN
            elif (
                last['close'] < lowest_low and
                last['volume'] > avg_volume * VOLUME_MULTIPLIER and
                last['close'] < last['ema200'] and
                last['ema34'] < last['ema89']
            ):
                send_telegram(
                    f"🔻 BREAK DOWN H4\n"
                    f"{symbol}\n"
                    f"Close: {last['close']:.4f}"
                )
                last_alert[key] = True

        except Exception as e:
            print(symbol, e)

    time.sleep(CHECK_INTERVAL)
