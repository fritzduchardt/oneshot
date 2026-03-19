import os

from openai import OpenAI


def list_models() -> list[str]:
    client = _create_client()
    models = [model.id for model in client.models.list()]
    return models


def _create_client() -> OpenAI:
    client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY"),
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
    )
    return client