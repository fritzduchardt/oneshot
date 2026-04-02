import asyncio
import logging
from typing import Any

import weaviate
from weaviate.collections.classes.internal import Object
from weaviate.connect import ConnectionParams

from .ai import anthropic_utils as anthropic
from .ai import langchain as lc
from .ai import openai_utils, gemini_utils, deepseek_utils, xai_utils
from .pattern import pattern as p


def complete(pattern_dir: str, pattern_name: str, stdin: str, prompt: str, model: str, with_mcp: bool, weaviate_host: str, weaviate_port: int, weaviate_grpc_host: str, weaviate_grpc_port: int) -> str:

    pattern_content = p.get_pattern(pattern_dir, pattern_name)
    if not pattern_content:
        return ""

    logging.info(f"Calling model: {model}")
    logging.info(f"Using pattern: {pattern_name}")

    if with_mcp:
        llm_resp = asyncio.run(lc.call_ai_with_tools(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin)))
    else:
        llm_resp = lc.call_ai(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin))

    return llm_resp


def call_weaviate(weaviate_host: str, weaviate_port: int, weaviate_grpc_host: str, weaviate_grpc_port: int, collection:str, prompt: str, limit: int=1) -> list[Object[Any, Any]]:
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
            ## KEYWORD
            logging.info(f"Prompt: {prompt}")
            response = pattern.query.bm25(
                query=prompt,
                query_properties=["path", "content"],
                limit=limit
            )
        else:
            from weaviate.collections.classes.grpc import MetadataQuery
            response = pattern.query.near_text(
                query=prompt,
                limit=limit,
                certainty=0.6,
                return_metadata=MetadataQuery(distance=True)
            )

        return response.objects


def list_models() -> list[str]:
    models = []
    models.extend(openai_utils.list_models())
    models.extend(anthropic.list_models())
    models.extend(xai_utils.list_models())
    models.extend(gemini_utils.list_models())
    models.extend(deepseek_utils.list_models())

    filter_prefixes = ["gpt-5.", "claude-", "grok-4", "gemini-2", "gemini-3", "deepseek"]
    blacklisted_models = [
        "gpt-5.2-pro",
        "gpt-5.2-pro-2025-12-11",
        "gpt-5.4-pro",
        "gpt-5.4-pro-2026-03-05",
    ]
    filtered_models = [m for m in models if m.startswith(tuple(filter_prefixes))]
    return [m for m in filtered_models if not m in tuple(blacklisted_models)]



def count_tokens(text: str) -> int:
    import tiktoken

    encoding = tiktoken.get_encoding("o200k_base")

    return len(encoding.encode(text))
