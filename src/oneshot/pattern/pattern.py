import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

def get_pattern(path: str, pattern: str) -> str | None:
    pattern_path = f"{path}/{pattern}/system.md"
    try:
        with open(pattern_path) as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Error: File '{pattern_path}' not found")
        return None

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
Current Date: {datetime.now().strftime("%d-%m-%Y")}
Current Timestamp: {datetime.now().timestamp()}
Current Directory: {os.curdir}
{pattern}
    """
