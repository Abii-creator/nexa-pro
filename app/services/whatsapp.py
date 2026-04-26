import os
import requests
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

GRAPH_API_VERSION = "v25.0"


def clean_phone(phone: str) -> str:
    raw = "".join(ch for ch in (phone or "") if ch.isdigit())

    if not raw:
        return ""

    if raw.startswith("00"):
        raw = raw[2:]

    if raw.startswith("0"):
        return "255" + raw[1:]

    if raw.startswith("255"):
        return raw

    if len(raw) == 9:
        return "255" + raw

    return raw


def check_config():
    if not WHATSAPP_TOKEN:
        return False, "WHATSAPP_TOKEN haijawekwa kwenye .env"

    if not WHATSAPP_PHONE_NUMBER_ID:
        return False, "WHATSAPP_PHONE_NUMBER_ID haijawekwa kwenye .env"

    return True, None


def get_messages_url():
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"


def get_media_url():
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/media"


def safe_json(response):
    try:
        return response.json()
    except ValueError:
        return {"raw_response": response.text}


def post_json(payload: dict) -> dict:
    ok, error = check_config()
    if not ok:
        return {"success": False, "error": error}

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        print("WHATSAPP POST URL:", get_messages_url())
        print("WHATSAPP PAYLOAD TO:", payload.get("to"))
        print("WHATSAPP PAYLOAD TYPE:", payload.get("type"))

        response = requests.post(
            get_messages_url(),
            headers=headers,
            json=payload,
            timeout=30
        )

        response_data = safe_json(response)

        print("WHATSAPP STATUS CODE:", response.status_code)
        print("WHATSAPP RESPONSE:", response_data)

        return {
            "success": response.status_code in [200, 201],
            "status_code": response.status_code,
            "response": response_data
        }

    except requests.exceptions.RequestException as e:
        print("WHATSAPP REQUEST ERROR:", str(e))
        return {"success": False, "error": str(e)}


def send_whatsapp_text(to_phone: str, message: str) -> dict:
    to_phone = clean_phone(to_phone)

    if not to_phone:
        return {"success": False, "error": "Namba ya mpokeaji haipo"}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message
        }
    }

    return post_json(payload)


def upload_whatsapp_media(file_path: str, filename: str = "qr_code.png") -> dict:
    ok, error = check_config()
    if not ok:
        return {"success": False, "error": error}

    if not file_path or not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"QR file haijapatikana: {file_path}"
        }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}"
    }

    data = {
        "messaging_product": "whatsapp",
        "type": "image/png"
    }

    try:
        print("WHATSAPP MEDIA UPLOAD URL:", get_media_url())
        print("WHATSAPP FILE PATH:", file_path)

        with open(file_path, "rb") as file:
            files = {
                "file": (filename, file, "image/png")
            }

            response = requests.post(
                get_media_url(),
                headers=headers,
                data=data,
                files=files,
                timeout=30
            )

        response_data = safe_json(response)

        print("WHATSAPP MEDIA STATUS CODE:", response.status_code)
        print("WHATSAPP MEDIA RESPONSE:", response_data)

        return {
            "success": response.status_code in [200, 201],
            "status_code": response.status_code,
            "response": response_data,
            "media_id": response_data.get("id")
        }

    except requests.exceptions.RequestException as e:
        print("WHATSAPP MEDIA REQUEST ERROR:", str(e))
        return {"success": False, "error": str(e)}


def send_whatsapp_document_by_media_id(
    to_phone: str,
    media_id: str,
    filename: str,
    caption: str = ""
) -> dict:
    to_phone = clean_phone(to_phone)

    if not to_phone:
        return {"success": False, "error": "Namba ya mpokeaji haipo"}

    if not media_id:
        return {"success": False, "error": "Media ID haipo"}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "document",
        "document": {
            "id": media_id,
            "filename": filename,
            "caption": caption
        }
    }

    return post_json(payload)


def send_whatsapp_qr(to_phone: str, image_path: str, guest_name: str, guest_code: str) -> dict:
    to_phone = clean_phone(to_phone)

    print("========== WHATSAPP QR SEND START ==========")
    print("FINAL TO PHONE:", to_phone)
    print("FILE PATH:", image_path)
    print("GUEST NAME:", guest_name)
    print("GUEST CODE:", guest_code)
    print("PHONE NUMBER ID:", WHATSAPP_PHONE_NUMBER_ID)

    if not to_phone:
        return {"success": False, "error": "Namba ya mpokeaji haipo"}

    filename = f"{guest_code or 'guest'}_qr_code.png"

    caption = (
        "Nexa Event Invitation\n\n"
        f"Name: {guest_name or '-'}\n"
        f"Code: {guest_code or '-'}\n\n"
        "QR code yako inatumwa kama file hapa chini. "
        "Please present this QR code at check-in."
    )

    upload_result = upload_whatsapp_media(
        file_path=image_path,
        filename=filename
    )

    if not upload_result.get("success"):
        result = {
            "success": False,
            "stage": "upload_media",
            "to_phone": to_phone,
            "upload_result": upload_result
        }

        print("WHATSAPP FINAL RESULT:", result)
        print("========== WHATSAPP QR SEND END ==========")
        return result

    media_id = upload_result.get("media_id")

    document_result = send_whatsapp_document_by_media_id(
        to_phone=to_phone,
        media_id=media_id,
        filename=filename,
        caption=caption
    )

    result = {
        "success": document_result.get("success"),
        "stage": "send_qr_document",
        "to_phone": to_phone,
        "media_id": media_id,
        "upload_result": upload_result,
        "document_result": document_result
    }

    print("WHATSAPP FINAL RESULT:", result)
    print("========== WHATSAPP QR SEND END ==========")

    return result