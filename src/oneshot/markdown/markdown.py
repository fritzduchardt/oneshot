import logging
import os.path
from pathlib import Path
from . import generate_image

def list_files(path: str) -> list[str]:
    if not os.path.exists(path):
        logging.error(f"Path not found: {path}")
        return []

    logging.info(f"Listing files in: {path}")
    files = list(Path(path).glob("**/*.md"))
    res: list[str] = []
    for f in files:
        if not ".trash" in str(f):
            res.append(str(f))
    res.sort()
    return res

def get_md(path: str) -> str | None:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        logging.error(f"Error: File '{path}' not found")
        return None

def delete_md(path: str) -> bool:
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        logging.error(f"Error: File '{path}' not found")
        return False

def save_markdown(md, path):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(f"{path}", "w") as f:
            f.write(md)
            generate_image.generate_images(md)
        return True
    except OSError as e:
        logging.error(f"Failed to write mardown to '{path}'")
        return False
