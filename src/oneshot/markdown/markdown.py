import asyncio
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
        base_name = Path(path).name.rstrip(".md")
        files = [file for file in Path(path).parent.iterdir() if file.is_file() and file.name.startswith(base_name)]
        for file in files:
            os.remove(file)
        return True
    except FileNotFoundError:
        logging.error(f"Error: File '{path}' not found")
        return False

def save_markdown(md, path, pattern_config_pattern_dir):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        logging.info(f"Saving markdown file: {path}")
        with open(f"{path}", "w") as f:
            f.write(md.strip())
        asyncio.run(generate_image.generate_food_images(md, path, pattern_config_pattern_dir))
        return True
    except OSError as e:
        logging.error(f"Failed to write markdown to '{path}'")
        return False
