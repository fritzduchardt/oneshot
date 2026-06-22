import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from ..message_queue import q

from ..ai import ai_utils
from ..utils import dates


def get_pattern(path: str, pattern: str) -> str | None:
    pattern_path = f"{path}/{pattern}/system.md"
    try:
        with open(pattern_path) as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Error: File '{pattern_path}' not found")
        return None


def grep_pattern(path: str, term: str) -> str:

    # Check for exact match
    if any(term == i.name for i in Path(path).iterdir()):
        return term

    # General
    if any(f"{term}_general" == i.name for i in Path(path).iterdir()):
        return f"{term}_general"

    # shortest starting match
    matches = [p.name for p in Path(path).iterdir() if p.name.startswith(term)]
    if matches:
        return min(matches,key=len)

    # shortest match anywhere in the pattern
    matches = [p.name for p in Path(path).iterdir() if term in p.name]
    if matches:
        return min(matches,key=len)

    # match of string contained in pattern
    for p in Path(path).iterdir():
        if term in (p / Path("system.md")).read_text():
            return p.name

    return ""


def delete_pattern(path: str, pattern: str) -> bool:
    pattern_path = f"{path}/{pattern}"
    try:
        shutil.rmtree(pattern_path)
        logging.info(f"Deleted: '{pattern_path}'")
        return True
    except FileNotFoundError:
        logging.error(f"Error: File '{pattern_path}' not found")
        return False

def list_patterns(path: str) -> list[str]:
    files = list(Path(path).glob("**/system.md"))
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


def generate_pattern_from_prompt(
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
        generated_prompt = ai_utils.clean_llm_response(chain.invoke({"md": create_complete_prompt(prompt, markdown_content)}))
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
