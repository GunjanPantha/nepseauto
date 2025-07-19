import requests

# Replace this with your actual Discord webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1396199636498124953/nAoA79bKy-9Zls5VXw2_Dapy6oGQgn0SLesqkec0Gov_6JoSvjVDXVR9c0_-Y9dG3m1W"

# Format: "SYMBOL": target_price
WATCHLIST = {
    "SHIVM": 750,
    "GLH": 280
}

def send_discord_message(content):
    requests.post(DISCORD_WEBHOOK_URL, json={"content": content})

def main():
    for symbol, target in WATCHLIST.items():
        try:
            response = requests.get(f"https://nepse-test.vercel.app/api?symbol={symbol}")
            data = response.json()
            ltp = data.get("ltp")

            if ltp is None:
                send_discord_message(f"❌ Could not fetch LTP for {symbol}")
                continue

            ltp = float(ltp)

            if ltp >= target:
                send_discord_message(f"<@452828777559621642> , ✅ `{symbol}` has reached your target! 🎯 LTP: {ltp} (Target: {target})")
            else:
                send_discord_message(f"ℹ️ `{symbol}` LTP: {ltp} (Target: {target})")

        except Exception as e:
            send_discord_message(f"⚠️ Error checking {symbol}: {e}")

if __name__ == "__main__":
    main()
