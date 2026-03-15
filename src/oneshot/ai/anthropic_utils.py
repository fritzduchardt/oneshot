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
        messages=messages,
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

                # Call Tools as indicated by LLM
                final_text: list[str] = []
                tool_call_contents = []
                tool_result_contents = []
                # keep track of last non-tool content block for fallback
                last_text_content = None
                for content in response.content:
                    if content.type == 'tool_use':
                        # make sure tool block is part of message
                        tool_call_contents.append(content)
                        tool_name = content.name
                        tool_args = content.input

                        # Execute tool call
                        logging.info(f"Calling tool: {tool_name} with args: {tool_args}")
                        try:
                            result = await session.call_tool(tool_name, tool_args)
                            tool_result_contents.append(_build_tool_result(content.id, result.content[0].text))
                        except httpx.HTTPStatusError as e:
                            logging.error(f"Failed on tool call: {e}")
                            tool_result_contents.append(_build_tool_result(content.id, f"Failed to call tool: {e}"))
                    elif content.type == 'text':
                        last_text_content = content.text

                if not tool_result_contents:
                    # LLM responded directly without invoking any tools
                    logging.info("LLM does not invoke tool")
                    if last_text_content is not None:
                        final_text.append(last_text_content)
                    return "\n".join(final_text)

                _append_message(messages, tool_call_contents, "assistant")
                _append_message(messages, tool_result_contents, "user")

                # Second call to LLM with tool results
                # noinspection PyTypeChecker
                logging.info(f"Finale messages: {messages}")
                response = client.messages.create(
                    model=model,
                    max_tokens=MAX_TOKENS,
                    messages=messages,
                )
                logging.info(f"Input tokens: {response.usage.input_tokens}")
                logging.info(f"Output tokens: {response.usage.output_tokens}")
                if not response.content:
                    final_text.append("LLM not sure what to do with tool results")
                else:
                    # collect all text blocks from the final response
                    for content in response.content:
                        if content.type == 'text':
                            final_text.append(content.text)
                    if not final_text:
                        final_text.append("LLM not sure what to do with tool results")
                return "\n".join(final_text)
    except Exception as e:
        logging.exception(f"Failure to call MCP Server or LLM: {e}")
        return f"Failed on call to MCP Server and / or LLM: {e}"


def _append_message(messages: list, contents: list, role ="user"):
    if contents:
        messages.append({
            "role": role,
            "content": contents
        })


def _build_tool_result(tool_use_id: str, content) -> dict:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content
    }


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
