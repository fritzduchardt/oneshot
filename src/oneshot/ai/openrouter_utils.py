import logging
import os

from openai import OpenAI


def list_models() -> list[str]:
    client = _create_client()
    all_models = [model.id for model in client.models.list()]
    logging.info(f"OpenRouter models count: {len(all_models)}")
    return all_models


def _create_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ.get("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
    )