import logging
import os
import re
from pathlib import Path

from src.oneshot.ai.ai_utils import clean_llm_response


def write_to_disk(content: str) -> None:
    pattern = r'^FILENAME:\s*(.+?)\s*$'
    file_path: str = ""
    file_content: str = ""

    for line in content.split("\n"):
        match = re.search(pattern, line)
        if match:
            # Before handling a new FILENAME marker, flush any pending file content to disk
            if file_path:
                file_content = clean_llm_response(file_content)
                _write_file(file_content, file_path)
                file_path = ""
                file_content = ""
            else:
                # No pending file_path, but there may be orphan content
                if file_content.strip():
                    logging.warning(f"No file path for: {file_content.strip()}")

            raw_path = match.group(1)
            parts = raw_path.split(" ", 1)
            if len(parts) > 1:
                if parts[0].upper() == "DELETE":
                    _delete_file(parts[1].strip())
                else:
                    logging.warning(f"Unknown filename modifier: {parts[0]}")
                # After modifier, reset state (no file_path is set)
                file_path = ""
                file_content = ""
            else:
                # Normal filename marker
                file_path = raw_path
                file_content = ""
        else:
            # Accumulate content for the current file
            file_content += f"{line}\n"

    # Flush the last file after loop
    if file_path:
        file_content = clean_llm_response(file_content)
        _write_file(file_content, file_path)
    elif file_content.strip():
        logging.warning(f"No file path for: {file_content.strip()}")


def _write_file(content: str, path: str) -> bool:
    """Write content to disk at the given relative path. Returns True on success."""
    if content and path:
        full_path = Path(f"{os.curdir}/{path}")
        logging.info(f"Writing: {full_path}")
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content.strip())
        except FileExistsError as e:
            logging.error(f"Failed to write: {full_path}: {e}")
            return False
        return True
    else:
        return False


def _delete_file(path: str) -> bool:
    """Delete the file at the given relative path. Returns True on success."""
    full_path = Path(f"{os.curdir}/{path}")
    try:
        logging.info(f"Deleting file: {full_path}")
        try:
            full_path.unlink()
        except FileNotFoundError as e:
            logging.error(f"Failed to delete: {full_path}: {e}")
            return False
        return True
    except FileNotFoundError:
        logging.warning(f"Failed to delete: {full_path}")
        return False
