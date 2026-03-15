import asyncio
import logging
from pathlib import Path
from typing import Any

import weaviate
from weaviate.classes.query import MetadataQuery
from weaviate.collections.classes.internal import Object
from weaviate.connect import ConnectionParams

from .ai import anthropic_utils as anthropic
from .ai import openai_utils as openai
from .ai import xai_utils as xai
from .pattern import pattern as p


def complete(pattern_dir: str, pattern_name: str, stdin: str, prompt: str, model: str, mcp_url: str, weaviate_host: str, weaviate_port: int, weaviate_grpc_host: str, weaviate_grpc_port: int) -> str:

    if weaviate_host and pattern_name == "weaviate":
        resp = call_weaviate(weaviate_host, weaviate_port, weaviate_grpc_host, weaviate_grpc_port, "PatternFile", prompt)
        if resp:
            logging.info(f"Weaviate found pattern: {resp[0].properties.get("path")}")
            pattern_name = Path(resp[0].properties["path"]).parent.name

    pattern_content = p.get_pattern(pattern_dir, pattern_name)
    if not pattern_content:
        return ""

    logging.info(f"Calling model: {model}")
    logging.info(f"Using pattern: {pattern_name}")

    llm_resp: str = ""
    if model.startswith("claude"):
        if mcp_url:
            llm_resp = asyncio.run(anthropic.call_anthropic_with_tools(mcp_url, model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin)))
        else:
            llm_resp = asyncio.run(anthropic.call_anthropic(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin)))
    elif model.startswith("gpt"):
        if mcp_url:
            llm_resp = asyncio.run(openai.call_openai_with_tools(mcp_url, model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin)))
        else:
            llm_resp = asyncio.run(openai.call_openai(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin)))

    elif model.startswith("grok"):
        llm_resp = asyncio.run(xai.call_xai(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin)))

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
        response = pattern.query.near_text(
            query=prompt,
            limit=limit,
            return_metadata=MetadataQuery(distance=True)
        )
        return response.objects


def list_models() -> list[str]:
    models = []
    models.extend(openai.list_models())
    models.extend(anthropic.list_models())
    models.extend(xai.list_models())

    filter_prefixes = ["gpt-5.", "claude-", "grok-4"]

    return [m for m in models if m.startswith(tuple(filter_prefixes))]


def count_tokens(text: str) -> int:
    import tiktoken

    encoding = tiktoken.get_encoding("o200k_base")

    return len(encoding.encode(text))
