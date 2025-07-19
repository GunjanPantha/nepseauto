import datetime
from playwright.sync_api import sync_playwright
import requests
import time
import re

# --- Configuration ---
WATCHLIST = ['GLH', 'SHIVM'] # Use your actual watchlist here
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1396199636498124953/nAoA79bKy-9Zls5VXw2_Dapy6oGQgn0SLesqkec0Gov_6JoSvjVDXVR9c0_-Y9dG3m1W"
NEPALSTOCK_URL = "https://www.nepalstock.com/today-price"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 7 
BROWSER_TIMEOUT_MS = 90000 

# --- Playwright Scraper Function ---
def fetch_ltp():
    """
    Fetches Last Traded Price (LTP) data for symbols in the watchlist from Nepal Stock Exchange.
    Handles potential SSL errors and includes retry logic, specifically for SPAs.
    Selects '500' items per page and applies the filter.
    """
    ltp_data = {}
    
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"Attempt {attempt}/{MAX_RETRIES} to fetch LTP data...")
        try:
            with sync_playwright() as p:
                browser = p.firefox.launch(headless=True) # Keep headless=True for production
                context = browser.new_context(ignore_https_errors=True) 
                page = context.new_page() 
                
                print(f"Navigating to {NEPALSTOCK_URL}...")
                page.goto(NEPALSTOCK_URL, timeout=BROWSER_TIMEOUT_MS)
                
                print("Waiting for preloader to disappear...")
                page.wait_for_selector('.preloader', state='hidden', timeout=BROWSER_TIMEOUT_MS)
                
                # --- NEW: Select '500' items per page AND click Filter button ---
                ITEMS_PER_PAGE_SELECT_SELECTOR = 'div.box__filter--field:has-text("Items Per Page") select'
                FILTER_BUTTON_SELECTOR = 'button.box__filter--search[type="button"]' # Specific selector for the Filter button
                
                print(f"Attempting to select '500' items per page and click Filter...")
                
                try:
                    # 1. Wait for the select element to be visible
                    page.wait_for_selector(ITEMS_PER_PAGE_SELECT_SELECTOR, state='visible', timeout=BROWSER_TIMEOUT_MS)
                    # 2. Select the option with value "500"
                    page.select_option(ITEMS_PER_PAGE_SELECT_SELECTOR, value="500")
                    print("Selected 500 items per page. Now clicking Filter button...")
                    
                    # 3. Click the Filter button and wait for navigation/network to settle
                    # Using page.click() and then waiting for networkidle is more robust
                    # than a fixed time.sleep()
                    page.click(FILTER_BUTTON_SELECTOR)
                    
                    # Wait for network activity to cease or for the page to finish loading the new data
                    # 'networkidle' is a good state for this, as the new table content is loaded via AJAX.
                    page.wait_for_load_state('networkidle', timeout=BROWSER_TIMEOUT_MS) 
                    
                    print("Filter applied. Page should now show more items.")
                    time.sleep(2) # Small additional pause for rendering stability
                    
                except Exception as select_filter_err:
                    print(f"Warning: Could not select 'Items Per Page' option or click Filter button: {select_filter_err}")
                    print("Proceeding with default items per page. Watchlist symbols might be missed.")
                    # If this fails, the script will continue with the default (20 items)

                TABLE_SELECTOR = 'table.table.table__lg.table-striped.table__border.table__border--bottom'
                print(f"Waiting for table '{TABLE_SELECTOR}' to be visible and populated...")
                
                # Wait for at least one row within the tbody of this specific table
                page.wait_for_selector(f'{TABLE_SELECTOR} tbody tr', state='visible', timeout=BROWSER_TIMEOUT_MS)
                
                # No need for another sleep here if networkidle was effective
                # time.sleep(2) 

                print("Table rows found. Extracting data...")
                rows = page.query_selector_all(f'{TABLE_SELECTOR} tbody tr')

                if not rows:
                    print("Error: No table rows found after waiting for preloader and table. This might indicate an empty table or a different loading issue.")
                    raise Exception("No table rows found.") 

                print(f"Found {len(rows)} rows in the table.") 

                for i, row in enumerate(rows): 
                    cols = row.query_selector_all('td')
                    
                    if len(cols) >= 10: 
                        symbol_element = cols[1].query_selector('a') 
                        last_price_element = cols[9].query_selector('span') 

                        if symbol_element and last_price_element:
                            symbol = symbol_element.inner_text().strip()
                            raw_price = last_price_element.inner_text().strip()
                            
                            try:
                                cleaned_price = float(raw_price.replace(',', ''))
                                last_price = f"{cleaned_price:,.2f}"
                            except ValueError:
                                last_price = "N/A"
                            
                            if symbol in WATCHLIST:
                                ltp_data[symbol] = last_price
                                print(f"  Found Watchlist Symbol: {symbol}, Price: {last_price}")
                
                print("Data extraction complete.")
                browser.close()
                return ltp_data
                
        except Exception as e:
            print(f"Error fetching LTP data (Attempt {attempt}): {e}")
            if "SEC_ERROR_UNKNOWN_ISSUER" in str(e):
                print("SSL error encountered despite 'ignore_https_errors'. This might be a deeper network/proxy issue.")
            elif "TimeoutError" in str(e):
                print("Timeout waiting for element. The page might be taking too long to load or selectors are incorrect.")
            
            if attempt < MAX_RETRIES:
                print(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print("Max retries reached.")

    return {}

# --- Discord Webhook Function ---
def send_discord_message(message):
    data = {"content": message}
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data, headers=headers)
        response.raise_for_status()
        print("Message sent to Discord successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send message to Discord: {e}")
        status_code = getattr(e.response, 'status_code', 'N/A')
        response_text = getattr(e.response, 'text', 'N/A')
        print(f"Response status code: {status_code}")
        print(f"Response text: {response_text}")

# --- Main Execution ---
if __name__ == "__main__":
    print("Starting Nepse LTP Checker...")
    ltp_data = fetch_ltp()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if ltp_data:
        message = f"📈 **Nepse LTP Checker Update**\n🕒 Checked at `{now}`\n\n"
        for symbol in WATCHLIST:
            price = ltp_data.get(symbol, '❓ Not Found')
            message += f"**{symbol}**: {price}\n"
        
        send_discord_message(message)
    else:
        error_message = f"🚨 **Nepse LTP Checker Alert**\nFailed to fetch LTP data for watchlist at `{now}` after multiple attempts. Please check the script or website."
        send_discord_message(error_message)

    print("Script finished.")