import logging
import os

import anthropic
import httpx
import mcp
import mcp.client
from mcp.client.streamable_http import streamable_http_client

MAX_TOKENS=20000

def list_models() -> list[str]:
    client = _create_client()
    models = [ model.id for model in client.models.list()]
    return models

async def call_anthropic(model: str, pattern: str, prompt: str) -> str:
    logging.info("Calling anthropic API without tools")
    client = _create_client()
    messages = _create_messages(pattern, prompt)
    # noinspection PyTypeChecker
    response = client.messages.create(
        max_tokens=MAX_TOKENS,
        messages =messages,
        model=model
    )
    logging.info(f"Input tokens: {response.usage.input_tokens}")
    logging.info(f"Output tokens: {response.usage.output_tokens}")
    return str(response.content[0].text)


def _create_client() -> anthropic.Anthropic:
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),  # This is the default and can be omitted
    )
    return client


async def call_anthropic_with_tools(mcp_url: str, model: str, pattern: str, prompt: str) -> str:
    logging.info(f"Calling anthropic API with tools: {mcp_url}")

    # noinspection PyBroadException
    try:
        async with streamable_http_client(f"{mcp_url}/mcp") as (
                read_stream,
                write_stream,
                _,
        ):
            client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY"),  # This is the default and can be omitted
            )

            # Create a session using the client streams
            async with mcp.ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                await session.initialize()

                response = await session.list_tools()
                available_tools = []
                for tool in response.tools:
                    available_tools.append({
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    })
                logging.info(f"Available tools: {available_tools}")
                messages = _create_messages(pattern, prompt)
                # noinspection PyTypeChecker
                response = client.messages.create(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    messages=messages,
                    tools=available_tools
                )
                # make sure tool blocks are part of message
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Call Tools as indicated by LLM
                final_text: list[str] = []
                tool_result_contents = []
                for content in response.content:
                    if content.type == 'tool_use':
                        tool_name = content.name
                        tool_args = content.input

                        # Execute tool call
                        logging.info(f"Calling tool: {tool_name} with args: {tool_args}")
                        try:
                            result = await session.call_tool(tool_name, tool_args)
                            content = {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result.content
                            }
                            tool_result_contents.append(content)
                        except httpx.HTTPStatusError as e:
                            logging.error(f"Failed on tool call: {e}")
                            content = {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": f"Failed to call tool: {e}"
                            }
                            tool_result_contents.append(content)
                    elif content.type == 'text':
                        logging.info("LLM does not invoke tool")
                        final_text.append(content.text)
                        return "\n".join(final_text)
                    else:
                        logging.error(f"Unexpected message type: {content.type}")
                        final_text.append("Failure to call mcp")
                        return "\n".join(final_text)
                messages.append({
                    "role": "user",
                    "content": tool_result_contents
                })

                # Second call to LLM with tool results
                # noinspection PyTypeChecker
                response = client.messages.create(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    messages=messages,
                    tools=available_tools
                )
                logging.info(f"Input tokens: {response.usage.input_tokens}")
                logging.info(f"Output tokens: {response.usage.output_tokens}")
                final_text.append(response.content[0].text)

                return "\n".join(final_text)
    except Exception:
        logging.exception("Failure to call MCP Server or LLM")
        return "Failed on call to MCP Server and / or LLM. Check logs"

def _create_messages(pattern: str, prompt: str):
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
