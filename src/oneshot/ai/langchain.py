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
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI

TOKEN_LIMIT = 20000

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
    llm = _create_llm(model)
    messages = _create_messages(pattern, prompt)

    if not _validate_token_count(json.dumps(messages)):
        return "Something went wrong, query has too many tokens"

    response = llm.invoke(messages)
    logging.info(f"Input tokens: {response.usage_metadata['input_tokens']}")
    logging.info(f"Output tokens: {response.usage_metadata['output_tokens']}")
    return response.text


def _validate_token_count(llm, messages) -> None:
    estimated_tokens = None

    if hasattr(llm, "get_num_tokens_from_messages"):
        try:
            estimated_tokens = llm.get_num_tokens_from_messages(messages)
        except Exception:
            estimated_tokens = None

    if estimated_tokens is None:
        combined = "\n".join(str(message.get("content", "")) for message in messages)
        estimated_tokens = len(combined) // 4

    if estimated_tokens > TOKEN_LIMIT:
        raise ValueError(
            f"Interrupting before execution: estimated input tokens {estimated_tokens} exceed limit {TOKEN_LIMIT}."
        )


async def call_ai_with_tools(model: str, pattern: str, prompt: str) -> str:
    try:
        available_tools = await client.get_tools()
        llm = _create_llm(model)
        agent = create_agent(
            model=llm,
            tools=available_tools,
        )
        messages = _create_messages(pattern, prompt)

        if not _validate_token_count(llm, messages):
            return "Something went wrong, query has too many tokens"

        logging.info(f"Available tools: {available_tools}")
        response = await agent.ainvoke({"messages": messages})
        logging.info(f"Input tokens: {response['messages'][-1].usage_metadata['input_tokens']}")
        logging.info(f"Output tokens: {response['messages'][-1].usage_metadata['output_tokens']}")
        return response["messages"][-1].text
    except Exception as e:
        logging.exception(f"Failure to call MCP Server or LLM: {e}")
        return "Failed on call to MCP Server and / or LLM. Check logs"


def _create_llm(model: str) -> ChatGoogleGenerativeAI:
    if model.startswith("gemini"):
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0,
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
        )

    return init_chat_model(model)


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
