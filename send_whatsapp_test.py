import os
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

if not ACCESS_TOKEN:
    raise ValueError("WHATSAPP_TOKEN haijawekwa kwenye .env")

if not PHONE_NUMBER_ID:
    raise ValueError("WHATSAPP_PHONE_NUMBER_ID haijawekwa kwenye .env")

TO_PHONE = "255776043399"

url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

data = {
    "messaging_product": "whatsapp",
    "to": TO_PHONE,
    "type": "text",
    "text": {
        "preview_url": False,
        "body": "Test message from Amisda Nexa Event System."
    }
}

print("TOKEN START:", ACCESS_TOKEN[:20])
print("PHONE NUMBER ID:", PHONE_NUMBER_ID)
print("SENDING TO:", TO_PHONE)

response = requests.post(url, headers=headers, json=data, timeout=30)

print("Status Code:", response.status_code)
print("Response:", response.text)