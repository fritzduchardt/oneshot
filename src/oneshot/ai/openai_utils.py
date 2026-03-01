import json
import os

import mcp
import mcp.client
from mcp.client.streamable_http import streamable_http_client
from openai import OpenAI

def list_models() -> list[str]:
    client = create_client()
    models = [ model.id for model in client.models.list()]
    return models

def call_openai(model: str, pattern: str, prompt: str) -> str:
    client = create_client()
    messages = create_messages(pattern, prompt)
    if model.endswith("-codex"):
        response = client.responses.create(
            model=model,
            input=messages
        )
        return response.output_text
    else:
        response = client.chat.completions.create(
            messages=messages,
            model=model,
        )
        if response.choices:
            return response.choices[0].message.content

    return "The LLMs has not answers for you"


async def call_openai_with_tools(mcp_url: str, model: str, pattern: str, prompt: str) -> str:
    async with (streamable_http_client(f"{mcp_url}/mcp") as (
            read_stream,
            write_stream,
            _,
    )):
        client = create_client()

        # Create a session using the client streams
        async with mcp.ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()

            input_list = create_messages(pattern, prompt)
            available_tools = await mcp_to_openai_tools(session)
            response = client.responses.create(
                tools=available_tools,
                model=model,
                input=input_list
            )

            # make sure tool blocks are part of message
            input_list += response.output

            # Call Tools as indicated by LLM
            final_text: list[str] = []
            for item in response.output:
                if item.type == 'function_call':
                    tool_name = item.name
                    tool_args = json.loads(item.arguments)
                    result = await session.call_tool(tool_name, tool_args)
                    input_list.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": result.content[0].text
                    })

            # Second call to LLM with tool results
            response = client.responses.create(
                input=input_list,
                model=model,
                tools=available_tools
            )

            if response.output and response.output[0].content:
                final_text.append(response.output[0].content[0].text)

            return "\n".join(final_text)


def create_client() -> OpenAI:
    client = OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    return client


def create_messages(pattern: str, prompt: str):
    return [
        {
            "role": "assistant",
            "content": pattern,
        },
        {
            "role": "user",
            "content": prompt,
        }
    ]


async def mcp_to_openai_tools(session: mcp.ClientSession) -> list:
    """Convert MCP tools to OpenAI function format."""
    mcp_tools = await session.list_tools()
    openai_tools = []
    for tool in mcp_tools.tools:
        openai_tools.append({
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        })
    return openai_tools
