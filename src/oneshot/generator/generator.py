import logging
import os
import re
from pathlib import Path

from src.oneshot.ai.ai_utils import clean_llm_response


def write_to_disk(content: str):
    pattern = r'^FILENAME:\s*(.+?)\s*$'
    file_path = ""
    file_content = ""
    for line in content.split("\n"):
        match = re.search(pattern, line)
        if match:
            # check for deletion
            file_path_line = match.group(1)
            parts = file_path_line.split(" ")
            if len(parts) > 1:
                if parts[0] == "DELETE":
                    _delete_file(parts[1].strip())
                else:
                    logging.warning(f"Unknown filename modifier: {parts[0]}")
                file_path = ""
                continue
            else:
                if file_path:
                    file_content = clean_llm_response(file_content)
                    _write_file(file_content, file_path)
                elif file_content.strip():
                    logging.warning(f"No file path for: {file_content.strip()}")
                file_path = match.group(1)
                file_content = ""
        else:
            file_content += f"{line}\n"

    file_content = clean_llm_response(file_content)
    if not file_content.strip():
        return
    if not file_path:
        logging.warning(f"No file path for: {file_content}")
    elif not _write_file(file_content, file_path):
        logging.warning("Writing back to disk failed. Writing to stdout")
        print(file_content)


def _write_file(content: str, path: str) -> bool:
    if content and path:
        path = Path(f"{os.curdir}/{path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip())
        logging.info(f"Writing: {path}")
        return True
    else:
        return False

def _delete_file(path: str) -> bool:
    try:
        logging.info(f"Deleting file: {path}")
        Path(f"{os.curdir}/{path}").unlink()
        return True
    except FileNotFoundError:
        logging.warning(f"Failed to delete: {path}")
        return False
