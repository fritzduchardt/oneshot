import os
import warnings

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module=r"google\.genai\.types",
)
from google import genai


def list_models() -> list[str]:
    client = _create_client()
    models = [model.name.lstrip("models/") for model in client.models.list()]
    return models


def _create_client() -> genai.Client:
    client = genai.Client(
        api_key=os.environ.get("GOOGLE_API_KEY"),
    )
    return client
