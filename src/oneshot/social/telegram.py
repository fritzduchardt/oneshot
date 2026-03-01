import random

import requests

URL = f"https://api.telegram.org/"

def send(msg: str, token: str):
    payload = {
        "chat_id": random.randint(100_000_000, 999_999_999),
        "text": msg
    }
    response = requests.post(f"{URL}/bot{token}/sendMessage", json=payload)
    response.raise_for_status()
