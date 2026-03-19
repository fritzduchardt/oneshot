import requests

URL = "https://api.telegram.org"


def send(msg: str, token: str, chat_id: int):
    if chat_id is None:
        raise ValueError("chat_id is required")

    payload = {
        "chat_id": chat_id,
        "text": msg,
    }
    response = requests.post(f"{URL}/bot{token}/sendMessage", json=payload)
    response.raise_for_status()
