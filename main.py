import os
import time
import glob
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from PIL import Image, ImageChops
import schedule
import requests
from requests.exceptions import RequestException

from selenium.webdriver.common.by import By

# Load environment variables from .env file
load_dotenv()

# Binance new listings URL
URL = "https://www.binance.com/en/support/announcement/new-cryptocurrency-listing?c=48&navId=48"
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SCREENSHOTS_DIR = "screenshots"

# Ensure the screenshots directory exists
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def is_connected():
    """Check if there is an active internet connection."""
    try:
        requests.get("https://www.google.com", timeout=5)
        return True
    except RequestException:
        return False

# Function to send notification via Telegram
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        requests.post(url, data=payload)
    except RequestException as e:
        print(f"Failed to send Telegram message: {e}")

# Function to send notification via Telegram (with screenshot)
def send_telegram_photo(photo_path, caption=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open(photo_path, "rb") as photo:
            payload = {
                "chat_id": CHAT_ID,
                "caption": caption,
                "parse_mode": "HTML"
            }
            files = {
                "photo": photo
            }
            response = requests.post(url, data=payload, files=files)
            if response.status_code == 200:
                print(f"Screenshot sent to Telegram successfully.")
            else:
                print(f"Failed to send screenshot to Telegram: {response.text}")
    except RequestException as e:
        print(f"Failed to send Telegram photo: {e}")

# Function to capture a screenshot of the page
def capture_screenshot():
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(URL)
        time.sleep(5)

        # Save full-page screenshot
        screenshot_path = "full_screenshot.png"
        driver.save_screenshot(screenshot_path)
        driver.quit()

        # Crop to the highlighted area
        left, top, right, bottom = 70, 240, 800, 800
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        with Image.open(screenshot_path) as img:
            cropped_img = img.crop((left, top, right, bottom))
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"screenshot_{timestamp}.png")
            cropped_img.save(screenshot_path)
            print("Cropped screenshot saved successfully.")

        return screenshot_path
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        return None

# Function to compare two screenshots
def screenshots_are_different(image1_path, image2_path):
    try:
        image1 = Image.open(image1_path)
        image2 = Image.open(image2_path)

        diff = ImageChops.difference(image1, image2)
        return diff.getbbox() is not None
    except Exception as e:
        print(f"Error comparing screenshots: {e}")
        return False

# Function to maintain only the latest 5 screenshots
def maintain_screenshot_history():
    screenshots = sorted(glob.glob(os.path.join(SCREENSHOTS_DIR, "screenshot_*.png")))
    while len(screenshots) > 5:
        os.remove(screenshots.pop(0))

# Function to check for updates
def check_for_updates():
    print(f"[{datetime.now()}] Checking for updates on Binance listings page...")
    
    # Check for internet connectivity
    if not is_connected():
        print(f"[{datetime.now()}] No internet connection. Skipping this check.")
        return

    # Capture a new screenshot
    new_screenshot = capture_screenshot()
    if not new_screenshot:
        print(f"[{datetime.now()}] Screenshot capture failed. Skipping this check.")
        return

    # Maintain a history of the last 5 screenshots
    maintain_screenshot_history()

    # Get the last two screenshots
    screenshots = sorted(glob.glob(os.path.join(SCREENSHOTS_DIR, "screenshot_*.png")))
    if len(screenshots) >= 2:
        if screenshots_are_different(screenshots[-2], screenshots[-1]):
            print(f"[{datetime.now()}] Change detected on the page!")
            send_telegram_photo(new_screenshot, "🔔 Change detected on Binance listings page! Check the page for updates.")
            send_telegram_message(URL)
        else:
            print(f"[{datetime.now()}] No changes detected.")
    else:
        print(f"[{datetime.now()}] Not enough screenshots to compare yet.")

# Schedule the check every 1 minute
schedule.every(1).minutes.do(check_for_updates)

# Run the scheduler
if __name__ == "__main__":
    print(f"[{datetime.now()}] Bot started. Checking for updates every 1 minute.")
    while True:
        schedule.run_pending()
        time.sleep(1)
