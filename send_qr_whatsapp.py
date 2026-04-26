import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

TO_PHONE = "255776043399"

# QR FILE PATH
file_path = "qr/GST-00001_qr_code.png"

# STEP 1: Upload media
upload_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

files = {
    "file": open(file_path, "rb"),
    "type": (None, "image/png"),
    "messaging_product": (None, "whatsapp")
}

upload_response = requests.post(upload_url, headers=headers, files=files)
upload_data = upload_response.json()

print("UPLOAD RESPONSE:", upload_data)

media_id = upload_data.get("id")

if not media_id:
    print("Upload failed")
    exit()

# STEP 2: Send image
send_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

payload = {
    "messaging_product": "whatsapp",
    "to": TO_PHONE,
    "type": "image",
    "image": {
        "id": media_id,
        "caption": "Nexa Event Invitation\n\nName: Mohamed Al-amin Abdy\nCode: GST-00001\n\nPresent this QR at check-in."
    }
}

send_response = requests.post(send_url, headers=headers, json=payload)

print("SEND STATUS:", send_response.status_code)
print("SEND RESPONSE:", send_response.text)