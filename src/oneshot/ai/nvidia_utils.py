import os

from openai import OpenAI

def list_models() -> list[str]:
    client = _create_client()
    models = [ model.id for model in client.models.list()]
    return models


def _create_client() -> OpenAI:
    client = OpenAI(
        base_url = os.environ.get("NVIDIA_API_BASE_URL"),
        api_key = os.environ.get("NVIDIA_API_KEY")
    )

    return client
