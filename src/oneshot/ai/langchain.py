import json
import logging
import os
import warnings

warnings.filterwarnings(
    "ignore",
    message=r".*Core Pydantic V1 functionality isn't compatible with Python 3\.14 or greater.*",
    category=UserWarning,
    module=r"langchain_core\._api\.deprecation",
)

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.chat_models import init_chat_model, BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from . import ai_utils

MAX_INPUT_TOKENS_MCP = 20000
MAX_INPUT_TOKENS_CLI = 200000
MAX_OUTPUT_TOKENS_MCP = 20000
MAX_OUTPUT_TOKENS_CLI = -1

client = MultiServerMCPClient(
    {
        "oneshot-mcp": {
            "transport": "http",
            "url": f"{os.environ.get('MCP_URL_ONESHOT')}/mcp",
        },
        "finclaw": {
            "transport": "http",
            "url": f"{os.environ.get('MCP_URL_FINCLAW')}/mcp",
        },
    }
)


def call_ai(model: str, pattern: str, prompt: str) -> str:
    logging.info("Calling AI without tools")
    llm = _create_llm(model, MAX_OUTPUT_TOKENS_CLI)
    messages = _create_messages(pattern, prompt)

    _validate_token_count(llm, messages, MAX_INPUT_TOKENS_CLI)

    response = llm.invoke(messages)
    logging.info(f"Input tokens: {response.usage_metadata['input_tokens']}")
    logging.info(f"Output tokens: {response.usage_metadata['output_tokens']}")
    return response.text


async def call_ai_with_tools(model: str, pattern: str, prompt: str) -> str:
    try:
        available_tools = await client.get_tools()
        llm = _create_llm(model, MAX_OUTPUT_TOKENS_MCP)
        messages = _create_messages(pattern, prompt)

        _validate_token_count(llm, messages, MAX_INPUT_TOKENS_MCP)

        agent = create_agent(
            model=llm,
            tools=available_tools,
        )

        logging.info(f"Available tools: {available_tools}")
        # noinspection PyTypeChecker
        response = await agent.ainvoke({"messages": messages})
        logging.info(f"Input tokens: {response['messages'][-1].usage_metadata['input_tokens']}")
        logging.info(f"Output tokens: {response['messages'][-1].usage_metadata['output_tokens']}")
        return response["messages"][-1].text
    except ValueError as e:
        logging.warning(f"Token limit exceeded, interrupting before agent execution: {e}")
        return str(e)
    except Exception as e:
        logging.exception(f"Failure to call MCP Server or LLM: {e}")
        return "Failed on call to MCP Server and / or LLM. Check logs"


def _validate_token_count(llm, messages, token_count) -> None:
    estimated_tokens = None

    if hasattr(llm, "get_num_tokens_from_messages"):
        try:
            estimated_tokens = llm.get_num_tokens_from_messages(messages)
        except Exception:
            estimated_tokens = None

    if estimated_tokens is None:
        estimated_tokens = ai_utils.count_tokens(json.dumps(messages))

    if estimated_tokens > token_count:
        raise ValueError(
            f"Interrupting before execution: estimated input tokens {estimated_tokens} exceed limit {token_count}."
        )


def _create_llm(model: str, max_output_tokens: int) -> BaseChatModel:
    ret: BaseChatModel
    if model.startswith("gemini"):
        ret = ChatGoogleGenerativeAI(
            model=model,
            temperature=0,
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
        )
    else:
        ret = init_chat_model(model)
    if max_output_tokens > 0:
        ret.max_tokens = max_output_tokens
    return ret


def _create_messages(pattern: str, prompt: str):
    return [
        {
            "role": "system",
            "content": pattern,
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]
