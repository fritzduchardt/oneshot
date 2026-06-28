import httpx

URL = "https://api.telegram.org"


async def send(msg: str, token: str, chat_id: int):
    if chat_id is None:
        raise ValueError("chat_id is required")

    payload = {
        "chat_id": chat_id,
        "text": msg,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{URL}/bot{token}/sendMessage", json=payload)
        response.raise_for_status()
