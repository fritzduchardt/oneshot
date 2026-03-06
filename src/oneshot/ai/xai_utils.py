import logging
import os

from xai_sdk import Client

from xai_sdk.chat import system, user

def list_models() -> list[str]:
    client = create_client()
    models = client.models.list_language_models()
    model_names = []
    for m in models:
        model_names.append(m.name)

    return model_names


async def call_xai(model: str, pattern: str, prompt: str):

    client = create_client()

    messages = [system(pattern), user(prompt)]
    chat = await client.chat.create(
        model=model,
        messages=messages
    )
    response = chat.sample()

    return response.content


def create_client() -> Client:
    client = Client(
        api_key=os.environ.get("GROKAI_API_KEY"),  # This is the default and can be omitted
    )
    return client
