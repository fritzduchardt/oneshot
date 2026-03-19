import json
import logging
import os

import mcp
import mcp.client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult
from openai import OpenAI
from openai.types.responses import ResponseApplyPatchToolCall, ResponseApplyPatchToolCallOutput, ResponseCodeInterpreterToolCall, ResponseCompactionItem, ResponseComputerToolCall, ResponseCustomToolCall, ResponseFileSearchToolCall, ResponseFunctionShellToolCall, ResponseFunctionShellToolCallOutput, ResponseFunctionToolCall, ResponseFunctionWebSearch, ResponseOutputMessage, ResponseReasoningItem, ResponseToolSearchCall, ResponseToolSearchOutputItem
from openai.types.responses.response_output_item import ImageGenerationCall, LocalShellCall, McpApprovalRequest, McpCall, McpListTools


def list_models() -> list[str]:
    client = _create_client()
    models = [ model.id for model in client.models.list()]
    return models

async def call_openai(model: str, pattern: str, prompt: str) -> str:
    logging.info("Calling openai API without tools")
    client = _create_client()
    messages = create_messages(pattern, prompt)
    if model.endswith("-codex"):
        # noinspection PyTypeChecker
        response = client.responses.create(
            model=model,
            input=messages
        )
        logging.info(f"Input tokens: {response.usage.input_tokens}")
        logging.info(f"Output tokens: {response.usage.output_tokens}")
        return response.output_text
    else:
        # noinspection PyTypeChecker
        response = client.chat.completions.create(
            messages=messages,
            model=model,
        )
        logging.info(f"Input tokens: {response.usage.prompt_tokens}")
        logging.info(f"Output tokens: {response.usage.completion_tokens}")
        if response.choices:
            return response.choices[0].message.content

    return "The LLMs has not answers for you"


async def call_openai_with_tools(mcp_url: str, model: str, pattern: str, prompt: str) -> str:
    logging.info(f"Calling openai API with tools: {mcp_url}")
    # noinspection PyBroadException
    try:
        async with (streamable_http_client(f"{mcp_url}/mcp") as (
                read_stream,
                write_stream,
                _,
        )):
            client = _create_client()
            #  noinspection PyBroadException
            # Create a session using the client streams
            async with mcp.ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                await session.initialize()

                input_list = create_messages(pattern, prompt)
                available_tools = await mcp_to_openai_tools(session)
                # noinspection PyTypeChecker
                response = client.responses.create(
                    tools=available_tools,
                    model=model,
                    input=input_list
                )
                logging.info(f"Available tools: {available_tools}")
                # make sure tool blocks are part of message
                input_list += response.output

                # Call Tools as indicated by LLM
                final_text: list[str] = []
                for item in response.output:
                    if item.type == 'function_call':
                        tool_name = item.name
                        tool_args = json.loads(item.arguments)
                        logging.info(f"Calling tool: {tool_name} with args: {tool_args}")
                        try:
                            result = await session.call_tool(tool_name, tool_args)
                            if result.content:
                                _append_message(input_list, item.call_id, result.content[0].text)
                            else:
                                logging.error(f"Empty tools response")
                                _append_message(input_list, item.call_id, "Empty tools response")
                        except Exception as e:
                            logging.error(f"Failed on tool call: {e}")
                            _append_message(input_list, item.call_id, f"Failed to call tool: {e}")
                    elif item.type == "message":
                        logging.info("LLM does not invoke tool")
                        if item.content:
                            final_text.append(item.content[0].text)
                            return "\n".join(final_text)
                    else:
                        logging.error(f"Unexpected message type: {item.type}")
                        final_text.append("Failure to call mcp")
                        return "\n".join(final_text)

                # Second call to LLM with tool results
                # noinspection PyTypeChecker
                logging.info(f"Final call to LLM with tool results: {input_list}")
                response = client.responses.create(
                    input=input_list,
                    model=model,
                )

                if response.output and response.output[0].content:
                    final_text.append(response.output[0].content[0].text)
                else:
                    final_text.append("LLM not sure what to do with tool results")

                return "\n".join(final_text)
    except Exception:
        logging.exception("Failure to call MCP Server or LLM")
        return "Failed on call to MCP Server and / or LLM. Check logs"


def _append_message(input_list: list[dict[str, str]], call_id:str, output:str):
    input_list.append({
        "type": "function_call_output",
        "call_id": call_id,
        "output": output
    })


def _create_client() -> OpenAI:
    client = OpenAI(
        # This is the default and can be omitted
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    return client

def create_messages(pattern: str, prompt: str):
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
