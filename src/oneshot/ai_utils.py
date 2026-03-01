import asyncio
import logging

from pattern import pattern as p
from dotenv import load_dotenv

import ai.anthropic_utils as anthropic
import ai.openai_utils as openai
import ai.xai_utils as xai

def complete(env_file: str, pattern_dir: str, pattern_name: str, stdin: str, prompt: str, model: str, mcp_url: str):

    pattern_content = p.get_pattern(pattern_dir, pattern_name)

    if pattern_content is None:
        return ""

    if not load_dotenv(env_file):
        logging.error(f"Failed to read: {env_file}")
        return ""

    logging.info(f"Calling model: {model}")
    logging.info(f"Using pattern: {pattern_name}")

    llm_resp: str = ""
    if model.startswith("claude"):
        if mcp_url:
            logging.info(f"Connecting to MCP Server: {mcp_url}")
            llm_resp = asyncio.run(anthropic.call_anthropic_with_tools(mcp_url, model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin)))
        else:
            llm_resp = anthropic.call_anthropic(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin))
    elif model.startswith("gpt"):
        if mcp_url:
            logging.info(f"Connecting to MCP Server: {mcp_url}")
            llm_resp = asyncio.run(openai.call_openai_with_tools(mcp_url, model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin)))
        else:
            llm_resp = openai.call_openai(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin))

    elif model.startswith("grok"):
        llm_resp = xai.call_xai(model, p.create_complete_pattern(model, pattern_name, pattern_content), p.create_complete_prompt(prompt, stdin))

    return llm_resp


def list_models(env_file: str) -> list[str]:

    if not load_dotenv(env_file):
        logging.error(f"Failed to read: {env_file}")
        return ""
    models = []
    models.extend(openai.list_models())
    models.extend(anthropic.list_models())
    models.extend(xai.list_models())

    filter_prefixes = ["gpt-5.", "claude-", "grok-4"]

    return [m for m in models if m.startswith(tuple(filter_prefixes))]
