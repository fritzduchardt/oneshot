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

client = MultiServerMCPClient(
    {
        "oneshot-mcp": {
            "transport": "http",  # HTTP-based remote server
            # Ensure you start your weather server on port 8000
            "url": f"{os.environ.get("MCP_URL_ONESHOT")}/mcp",
        },
        "finclaw": {
            "transport": "http",  # HTTP-based remote server
            # Ensure you start your weather server on port 8000
            "url": f"{os.environ.get("MCP_URL_FINCLAW")}/mcp",
        }
    }
)

def call_ai(model: str, pattern: str, prompt: str) -> str:
    logging.info("Calling openai API without tools")
    llm = _create_llm(model)
    response = llm.invoke(_create_messages(pattern, prompt))
    logging.info(f"Input tokens: {response.usage_metadata["input_tokens"]}")
    logging.info(f"Output tokens: {response.usage_metadata["output_tokens"]}")
    return response.text


async def call_ai_with_tools(model: str, pattern: str, prompt: str) -> str:
    try:
        available_tools = await client.get_tools()
        llm = _create_llm(model)
        agent = create_agent(
            model=llm,
            tools=available_tools
        )
        messages = _create_messages(pattern, prompt)
        logging.info(f"Available tools: {available_tools}")
        response = await agent.ainvoke({"messages": messages})
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
        }
    ]
