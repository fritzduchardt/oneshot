import logging
import re
from typing import Any

import weaviate
from langchain_anthropic import ChatAnthropic
from langchain_deepseek import ChatDeepSeek
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from weaviate.collections.classes.internal import Object
from weaviate.connect import ConnectionParams

from . import anthropic_utils as anthropic
from . import deepseek_utils, gemini_utils, openai_utils, xai_utils
from . import langchain as lc
from ..pattern import pattern as p


async def complete(pattern_dir: str, pattern_name: str, stdin: str, prompt: str, model: str, with_mcp: bool, weaviate_host: str, weaviate_port: int, weaviate_grpc_host: str, weaviate_grpc_port: int) -> str:
    pattern_content = p.get_pattern(pattern_dir, pattern_name)
    if not pattern_content:
        return ""

    logging.info(f"Calling model: {model}")
    logging.info(f"Using pattern: {pattern_name}")

    if with_mcp:
        llm_resp = await lc.call_ai_with_tools(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin))
    else:
        llm_resp = lc.call_ai(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin))

    return llm_resp


def call_weaviate(weaviate_host: str, weaviate_port: int, weaviate_grpc_host: str, weaviate_grpc_port: int, collection: str, prompt: str, limit: int = 1) -> list[Object[Any, Any]]:
    with weaviate.WeaviateClient(
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
            response = pattern.query.bm25(query=prompt, query_properties=["path", "content"], limit=limit)
        else:
            from weaviate.collections.classes.grpc import MetadataQuery

            response = pattern.query.near_text(
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


def clean_llm_response(response: str) -> str:
    """
        Removes starting and trailing code block description from response
    """
    if response.startswith("```"):
        response = re.sub(r"^```[^\n]*\n", "", response)
    if response.endswith("```"):
        response = re.sub(r"\n```$", "", response)
    return response
