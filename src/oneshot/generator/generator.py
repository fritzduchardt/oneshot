import logging
import os
import re
from pathlib import Path


def write_to_disk(content: str):
    pattern = r'^FILENAME:\s*(.+?)\s*$'
    file_path = ""
    file_content = ""
    for line in content.split("\n"):
        match = re.search(pattern, line)
        if match:
            write_file(file_content, file_path)
            file_path = match.group(1)
            file_content = ""
        else:
            file_content += f"{line}\n"

    if not write_file(file_content, file_path):
        logging.warning("Writing back to disk failed. Writing to stdout")
        print(file_content)


def write_file(content: str, path: str) -> bool:
    if content and path:
        path = Path(f"{os.curdir}/{path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content.strip())
        logging.info(f"Writing: {path}")
        return True
    else:
        return False
