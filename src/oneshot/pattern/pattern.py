import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ..ai import ai_utils
from ..message_queue import q
from ..utils import dates


def get_pattern(path: str, pattern: str) -> str | None:
    pattern_path = f"{path}/{pattern}/system.md"
    try:
        with open(pattern_path) as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Error: File '{pattern_path}' not found")
        return None


async def grep_pattern(path: str, term: str) -> str:
    # Check for exact match
    # Use asyncio.to_thread for filesystem calls that can't be made async
    import asyncio
    dirs = await asyncio.to_thread(lambda: [i.name for i in Path(path).iterdir()])
    if any(term == d for d in dirs):
        return term

    # General
    if any(f"{term}_general" == d for d in dirs):
        return f"{term}_general"

    # shortest starting match
    matches = [d for d in dirs if d.startswith(term)]
    if matches:
        return min(matches, key=len)

    # shortest match anywhere in the pattern
    matches = [d for d in dirs if term in d]
    if matches:
        return min(matches, key=len)

    # match of string contained in pattern - async file reads
    for d in dirs:
        pattern_path = Path(path) / d / "system.md"
        if await asyncio.to_thread(lambda: pattern_path.exists()):
            content = await asyncio.to_thread(lambda: pattern_path.read_text())
            if term in content:
                return d

    return ""


async def delete_pattern(path: str, pattern: str) -> bool:
    pattern_path = f"{path}/{pattern}"
    import asyncio
    try:
        # shutil.rmtree is blocking; run in thread pool
        await asyncio.to_thread(shutil.rmtree, pattern_path, True, None)
        logging.info(f"Deleted: '{pattern_path}'")
        return True
    except FileNotFoundError:
        logging.error(f"Error: File '{pattern_path}' not found")
        return False


async def list_patterns(path: str) -> list[str]:
    import asyncio
    # Use asyncio.to_thread to walk filesystem
    files = await asyncio.to_thread(lambda: list(Path(path).glob("**/system.md")))
    res: list[str] = []
    for f in files:
        res.append(f.parent.name)
    res.sort()
    return res


def create_complete_prompt(prompt: str, stdin: str) -> str:
    if stdin:
        return f"""
Specific User Request: {prompt}
{stdin}
        """
    else:
        return f"""
Specific User Request: {prompt}
        """


def create_complete_pattern(model: str, pattern_name: str, pattern: str) -> str:
    return f"""
Current Model: {model}
Current Pattern: {pattern_name}
Todays Date and Time: {dates.datetime_to_string(datetime.now())}
Current Directory: {os.curdir}
Current User / Me: {os.getenv("ME")}
{pattern}
    """


async def generate_pattern_from_prompt(
        prompt_pattern_content: str,
        prompt_model: str,
        prompt: str,
        markdown_content: str,
) -> str:
    try:
        logging.info(f"Generating custom pattern with model: {prompt_model}")

        messages = [
            ("system", prompt_pattern_content),
            ("human", "{md}")
        ]
        prompt_template = ChatPromptTemplate(messages)
        str_output = StrOutputParser()
        chain = prompt_template | ai_utils.get_model(prompt_model) | str_output
        # Use async invoke for the chain
        generated_prompt = ai_utils.clean_llm_response(await chain.ainvoke({"md": create_complete_prompt(prompt, markdown_content)}))
        generated_prompt_and_metadata = f"""
        ---
        model: {prompt_model}
        prompt: {prompt}
        ---
        {generated_prompt}
        """
        data = {
            "message": generated_prompt_and_metadata,
        }
        q.put(data)
        return generated_prompt_and_metadata
    except BaseException as e:
        logging.error("Failed during image generation: %s", e, exc_info=True)
        raise e
