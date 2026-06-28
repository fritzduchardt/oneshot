import json
import logging
import os
import warnings

from langchain_nvidia_ai_endpoints import ChatNVIDIA

warnings.filterwarnings(
    "ignore",
    message=r".*Core Pydantic V1 functionality isn't compatible with Python 3\.14 or greater.*",
    category=UserWarning,
    module=r"langchain_core\._api\.deprecation",
)

from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.callbacks import CallbackContext
from langchain.chat_models import init_chat_model, BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from . import ai_utils
from ..message_queue import q

MAX_INPUT_TOKENS_MCP = 20000
MAX_INPUT_TOKENS_CLI = 200000
MAX_OUTPUT_TOKENS_MCP = 20000
MAX_OUTPUT_TOKENS_CLI = -1

# Cache for tools retrieved from MCP client to avoid repeated network calls
_tools_cache = None

async def _get_cached_tools():
    """Return cached tools or fetch and cache them."""
    global _tools_cache
    if _tools_cache is None:
        _tools_cache = await client.get_tools()
    return _tools_cache


async def progress_handler(
        progress: float,
        total: float | None,
        message: str | None,
        context: CallbackContext,
) -> None:
    if total:
        pct = (progress / total) * 100
        logging.debug(f"[{context.tool_name}] {pct:.1f}% - {message}")


async def log_handler(
        params,
        context: CallbackContext,
) -> None:
    logging.debug(f"Notification from: {context.tool_name}\n{params.data}")
    data = {
        "message": params.data,
        "basepath": "",
        "image": "",
    }
    q.put_nowait(data)


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
    },
    # callbacks=Callbacks(
    #     on_logging_message=log_handler,
    #     on_progress=progress_handler,
    # ),
)


async def call_ai(model: str, pattern: str, prompt: str) -> str:
    logging.info("Calling AI without tools")
    llm = _create_llm(model, MAX_OUTPUT_TOKENS_CLI)
    messages = _create_messages(pattern, prompt)

    _validate_token_count(llm, messages, MAX_INPUT_TOKENS_CLI)

    response = await llm.ainvoke(messages)
    response_text = response.text.strip()
    response_text = ai_utils.clean_llm_response(response_text)
    logging.info(f"Input tokens: {response.usage_metadata['input_tokens']}")
    logging.info(f"Output tokens: {response.usage_metadata['output_tokens']}")
    return response_text


async def call_ai_with_tools(model: str, pattern: str, prompt: str) -> str:
    try:
        available_tools = await _get_cached_tools()
        llm = _create_llm(model, MAX_OUTPUT_TOKENS_MCP)
        messages = _create_messages(pattern, prompt)

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
    except Exception as e:
        logging.exception(f"Failure to call MCP Server or LLM: {e}")
        return "Failed on call to MCP Server and / or LLM. Check logs"


async def call_ai_only_tools(model: str, pattern_content: str, prompt: str, tool_name: str) -> str | None:
    try:
        available_tools = await _get_cached_tools()
        logging.info(f"Available tools: {available_tools}")
        llm = _create_llm(model, MAX_OUTPUT_TOKENS_MCP)
        # bind only the requested tool so the llm is forced to call it
        matching_tools = [tool for tool in available_tools if tool.name == tool_name]
        llm_with_tools = llm.bind_tools(matching_tools)
        messages = _create_messages(pattern_content, f"Use tool call to: {tool_name} in order to: {prompt}")

        response = await llm_with_tools.ainvoke(messages)
        logging.info(f"Input tokens: {response.usage_metadata["input_tokens"]}")
        logging.info(f"Output tokens: {response.usage_metadata["output_tokens"]}")
        for call in response.tool_calls:
            for tool in matching_tools:
                if tool.name == tool_name:
                    result = await tool.ainvoke(call["args"])
                    return str(result)
        return f"Tool not found: {tool_name}"
    except BaseException as e:
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

    logging.info(f"Estimated tokens: {estimated_tokens}")
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
    elif model.startswith("nvidia"):
        ret = ChatNVIDIA(
            model=model,
            api_key=os.environ.get("NVIDIA_API_KEY"),
            temperature=1,
            top_p=0.95,
            max_tokens=16384,
            reasoning_budget=16384,
            chat_template_kwargs={"enable_thinking":True},
        )
        if max_output_tokens > 0:
            ret.max_tokens = max_output_tokens
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
