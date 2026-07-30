import os

from xai_sdk import Client
from xai_sdk.chat import system, user


def list_models() -> list[str]:
    client = _create_client()
    models = client.models.list_language_models()
    model_names = []
    for m in models:
        model_names.append(m.name)

    return model_names


# Fixed: Made call_xai synchronous because the xAI SDK methods are synchronous.
# If asynchronous version is needed, await should be used on SDK methods.
def call_xai(model: str, pattern: str, prompt: str) -> str:
    client = _create_client()

    messages = [system(pattern), user(prompt)]
    chat = client.chat.create(
        model=model,
        messages=messages
    )
    response = chat.sample()

    return response.content


def _create_client() -> Client:
    client = Client(
        api_key=os.environ.get("GROKAI_API_KEY"),
    )
    return client
