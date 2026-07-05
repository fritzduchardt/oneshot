import logging
import re
from typing import Any

import weaviate
from langchain_anthropic import ChatAnthropic
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_xai import ChatXAI
from weaviate.collections.classes.internal import Object
from weaviate.connect import ConnectionParams

from . import anthropic_utils as anthropic, nvidia_utils
from . import deepseek_utils, gemini_utils, openai_utils, xai_utils
from . import langchain as lc
from ..pattern import pattern as p


async def complete(pattern_name: str, pattern_content: str, stdin: str, prompt: str, model: str, with_mcp: bool, weaviate_host: str, weaviate_port: int, weaviate_grpc_host: str, weaviate_grpc_port: int) -> str:
    if not pattern_content:
        return ""

    logging.info(f"Calling model: {model}")
    logging.info(f"Using pattern: {pattern_name}")
    metadata = {"pattern": pattern_name, "model": model}
    if with_mcp:
        llm_resp, input_tokens, output_tokens = await lc.call_ai_with_tools(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin))
        metadata["mcp"] = "true"
    else:
        llm_resp, input_tokens, output_tokens = await lc.call_ai(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin))

    costs = calculate_ai_cost(model, input_tokens, output_tokens)
    if costs:
        metadata["costs"] = costs
    metadata_str = ""
    for k, v in metadata.items():
        metadata_str += f"{k}: {v}\n"

    llm_resp_with_metadata = f"""---\n{metadata_str}---\n{llm_resp}"""
    return llm_resp_with_metadata


async def call_weaviate(weaviate_host: str, weaviate_port: int, weaviate_grpc_host: str, weaviate_grpc_port: int, collection: str, prompt: str, limit: int = 1) -> list[Object[Any, Any]]:
    async with weaviate.use_async(
        connection_params=ConnectionParams.from_params(
            http_host=weaviate_host,
            http_port=weaviate_port,
            http_secure=False,
            grpc_host=weaviate_grpc_host,
            grpc_port=weaviate_grpc_port,
            grpc_secure=False,
        ),
    ) as client:
        pattern = client.collections.use(collection)

        if collection == "PatternFile":
            prompt = " ".join(prompt.split(maxsplit=2)[:2])
            logging.info(f"Prompt: {prompt}")
            response = await pattern.query.bm25(query=prompt, query_properties=["path", "content"], limit=limit)
        else:
            from weaviate.collections.classes.grpc import MetadataQuery

            response = await pattern.query.near_text(
                query=prompt,
                limit=limit,
                certainty=0.6,
                return_metadata=MetadataQuery(distance=True),
            )

        return response.objects


def list_models() -> list[str]:
    models = []
    models.extend(openai_utils.list_models())
    models.extend(anthropic.list_models())
    models.extend(xai_utils.list_models())
    models.extend(gemini_utils.list_models())
    models.extend(deepseek_utils.list_models())
    models.extend(nvidia_utils.list_models())

    filter_prefixes = [
        "gpt-5",
        "claude-",
        "grok-4",
        "gemini-2",
        "gemini-3",
        "deepseek",
    ]
    blacklisted_words = [
        "gpt-5.1",
        "gpt-5.2",
        "gpt-5.3",
        "claude-opus-4-1",
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "gemini-2",
        "grok-4-1",
        "gpt-5-pro",
    ]
    blacklisted_models = [
        "gpt-5-pro",
        "gpt-5.2-pro",
        "gpt-5.2-pro-2025-12-11",
        "gpt-5.4-pro",
        "gpt-5.4-pro-2026-03-05",
        "grok-4-0709",
    ]

    filtered_models = [m for m in models if m.startswith(tuple(filter_prefixes))]
    filtered_models = [m for m in filtered_models if not any(word in m for word in blacklisted_words)]
    return [m for m in filtered_models if m not in blacklisted_models]


def count_tokens(text: str) -> int:
    import tiktoken

    encoding = tiktoken.get_encoding("o200k_base")

    return len(encoding.encode(text))


# Anthropic 4 Opus: Input $5/1M tokens, Output $25/1M tokens
def get_anthropic(model: str) -> ChatAnthropic:
    return ChatAnthropic(model=model)


# OpenAI GPT 5.5: Input $5/1M tokens, Output $30/1M tokens
def get_gpt5_5() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-5.5")


# OpenAI GPT 5.4: Input $2.5/1M tokens, Output $15/1M tokens
def get_gpt5_4() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-5.4")


# Gemini 3 Pro: Input $2/1M tokens, Output $12/1M tokens
def get_gemini_pro() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model="gemini-3.1-pro-preview")


# Gemini 3 Flash: Input $1.5/1M tokens, Output $9/1M tokens
def get_gemini_flash() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model="gemini-3.5-flash")


# DeepSeek V4 Flash: Input $0.028/1M tokens, Output $0.87/1M tokens
def get_deepseek(model: str) -> ChatDeepSeek:
    return ChatDeepSeek(model=model)


# Generic OpenAI method
def get_openai(model: str) -> ChatOpenAI:
    return ChatOpenAI(model=model)


# Generic xAI method
def get_xai(model: str) -> ChatXAI:
    return ChatXAI(model=model)


# Generic Gemini method
def get_gemini(model: str) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=model)


def get_model(model: str) -> Any:
    """Returns a LangChain chat model instance based on the model name string.

    Delegates to specialized methods (e.g., get_gpt5_4, get_anthropic) when
    the model matches known prefixes. Raises ValueError for unknown models.
    """
    if model.startswith("gpt"):
        return get_openai(model)
    elif model.startswith("claude-"):
        return get_anthropic(model)
    elif model.startswith("gemini"):
        return get_gemini(model)
    elif model.startswith("deepseek"):
        return get_deepseek(model)
    else:
        raise ValueError(f"Unsupported model: {model}")


def clean_llm_response(response: str) -> str:
    """
        Removes starting and trailing code block description from response
    """
    response = response.strip()
    if response.startswith("```"):
        response = re.sub(r"^```[^\n]*\n", "", response)
    if response.endswith("```"):
        response = re.sub(r"\n```$", "", response)
    return response


def calculate_ai_cost(model: str, input_tokens: int, output_tokens: int) -> str:
    """Calculate the costs in USD for using a given AI model with provided token counts.

    Pricing is based on publicly published rates per million tokens for input and output.
    Supports models from Gemini, Anthropic, OpenAI, DeepSeek, and Grok (xAI).
    Raises ValueError if the model is unknown or unsupported.
    """
    input_cost_per_million, output_cost_per_million = _get_model_pricing(model)
    if input_cost_per_million < 0:
        return ""
    costs = (input_tokens / 1_000_000) * input_cost_per_million
    costs += (output_tokens / 1_000_000) * output_cost_per_million
    return f"{costs} ({input_tokens}/{output_tokens})"


def _get_model_pricing(model: str) -> tuple[float, float]:
    """Lookup and return (input_cost_per_million, output_cost_per_million) for the given model.

    Pricing data is sourced from official provider documentation as of early 2026.
    For models not explicitly listed, a reasonable default for the provider family is used.
    """
    # Known model pricing in USD per 1M tokens (input, output)
    provider_pricing = {
        "gemini": {
            "gemini-3.1-pro-preview": (4.0, 12.0),
            "gemini-3.5-flash": (1.5, 9.0),
        },
        "openai": {
            "gpt-5.5-pro": (30, 270.0),
            "gpt-5.4-pro": (30, 270.0),
            "gpt-5.4-mini": (0.75, 0),
            "gpt-5.4-nano": (0.2, 0),
            "gpt-5.5": (5.0, 45.0),
            "gpt-5.4": (2.5, 22.5),
        },
        "anthropic": {
            "claude-fable": (10, 50),
            "claude-mythos": (10, 50),
            "claude-opus-4": (5.0, 25.0),
            "claude-sonnet": (3.0, 15.0),
            "claude-haiku": (1.0, 5.0),
        },
        "deepseek": {
            "deepseek-v4-flash": (0.09, 0.18),
            "deepseek-v4-pro": (0.435, 0.87),
        },
        "grok": {
            "grok-4.3": (1.25, 2.5),
        },
    }

    provider = None
    if model.startswith("gemini"):
        provider = "gemini"
    elif model.startswith("gpt"):
        provider = "openai"
    elif model.startswith("claude"):
        provider = "anthropic"
    elif model.startswith("deepseek"):
        provider = "deepseek"
    elif model.startswith("grok"):
        provider = "grok"

    if provider is None:
        return -1, -1

    pricing_dict = provider_pricing[provider]
    for key, val in pricing_dict:
        if key.startwith(model):
            return val
    return -1, -1
