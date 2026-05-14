import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

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
    matches = [p.name for p in Path(path).iterdir() if p.name.startswith(term)]
    if matches:
        return min(matches,key=len)

    matches = [p.name for p in Path(path).iterdir() if term in p.name]
    if matches:
        return min(matches,key=len)

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
