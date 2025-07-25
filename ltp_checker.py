import requests

# Replace this with your actual Discord webhook URL
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1396199636498124953/nAoA79bKy-9Zls5VXw2_Dapy6oGQgn0SLesqkec0Gov_6JoSvjVDXVR9c0_-Y9dG3m1W"

# Format: "SYMBOL": {"target": target_price, "stop_loss": stop_loss_price}
# The stop_loss price should be a value below which you want to be alerted.
WATCHLIST = {
    "SHIVM": {"target": 750, "stop_loss": 200},
    "GLH": {"target": 375, "stop_loss": 280}
}

def send_discord_message(content):
    """
    Sends a message to the configured Discord webhook.

    Args:
        content (str): The message content to send.
    """
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": content})
    except requests.exceptions.RequestException as e:
        print(f"Error sending Discord message: {e}")

def main():
    """
    Fetches the latest traded price (LTP) for symbols in the WATCHLIST,
    checks against target and stop-loss prices, and sends Discord notifications.
    """
    for symbol, prices in WATCHLIST.items():
        target = prices.get("target")
        stop_loss = prices.get("stop_loss")

        try:
            # Fetch data from the NEPSE API
            response = requests.get(f"https://nepse-test.vercel.app/api?symbol={symbol}")
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            ltp = data.get("ltp")

            if ltp is None:
                send_discord_message(f"❌ Could not fetch LTP for `{symbol}`. API response missing 'ltp'.")
                continue

            ltp = float(ltp)

            # Check for stop-loss hit
            if stop_loss is not None and ltp <= stop_loss:
                send_discord_message(f"<@452828777559621642> , 🔴 `{symbol}` has hit your stop-loss! 📉 LTP: {ltp} (Stop-Loss: {stop_loss})")
            # Check for target hit
            elif target is not None and ltp >= target:
                send_discord_message(f"<@452828777559621642> , ✅ `{symbol}` has reached your target! 🎯 LTP: {ltp} (Target: {target})")
            # Otherwise, just report the current LTP
            else:
                message = f"ℹ️ `{symbol}` LTP: {ltp}"
                if target is not None:
                    message += f" (Target: {target})"
                if stop_loss is not None:
                    message += f" (Stop-Loss: {stop_loss})"
                send_discord_message(message)

        except requests.exceptions.HTTPError as e:
            send_discord_message(f"⚠️ HTTP Error checking `{symbol}`: {e} - Status Code: {e.response.status_code}")
        except requests.exceptions.ConnectionError as e:
            send_discord_message(f"⚠️ Connection Error checking `{symbol}`: {e} - Could not connect to API.")
        except requests.exceptions.Timeout as e:
            send_discord_message(f"⚠️ Timeout Error checking `{symbol}`: {e} - Request timed out.")
        except requests.exceptions.RequestException as e:
            send_discord_message(f"⚠️ An unexpected Request Error occurred for `{symbol}`: {e}")
        except ValueError:
            send_discord_message(f"⚠️ Could not convert LTP to float for `{symbol}`. Received: '{ltp}'")
        except Exception as e:
            send_discord_message(f"⚠️ An unexpected error occurred checking `{symbol}`: {e}")

if __name__ == "__main__":
    main()
