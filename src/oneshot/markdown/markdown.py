import logging
import os.path
from pathlib import Path

import aiofiles

from . import generate_image


async def list_files(path: str) -> list[str]:
    import asyncio
    if not os.path.exists(path):
        logging.error(f"Path not found: {path}")
        return []

    files = await asyncio.to_thread(lambda: list(Path(path).glob("**/*.md")))
    res: list[str] = []
    for f in files:
        if ".trash" not in str(f):
            res.append(str(f))
    res.sort()
    return res


async def get_md(path: str) -> str:
    async with aiofiles.open(path) as f:
        return await f.read()


async def delete_md(path: str) -> bool:
    import asyncio
    import os as sync_os
    from pathlib import Path
    try:
        base_name = Path(path).name.rstrip(".md")
        parent = Path(path).parent
        # List files synchronously in thread
        files = await asyncio.to_thread(
            lambda: [f for f in parent.iterdir() if file.is_file() and file.name.startswith(base_name)]
        )
        for file in files:
            await asyncio.to_thread(sync_os.remove, file)
        return True
    except FileNotFoundError:
        logging.error(f"Error: File '{path}' not found")
        return False


async def save_markdown(md: str, base_path, path, pattern_config_pattern_dir):
    import asyncio
    import os as sync_os
    full_path = f"{base_path}/{path}"
    try:
        await asyncio.to_thread(sync_os.makedirs, sync_os.path.dirname(full_path), exist_ok=True)
        logging.info(f"Saving markdown file: {full_path}")
        clean_md = ""
        for l in md.split("\n"):
            if not l.strip().startswith("FILENAME:"):
                clean_md += f"{l}\n"
        # Write file asynchronously
        async with aiofiles.open(full_path, mode='w') as f:
            await f.write(clean_md)
        if "/Food/" in full_path:
            await generate_image.generate_food_images(md, base_path, path, pattern_config_pattern_dir)
        else:
            logging.info(f"Not generating images for: {full_path}")
        return True
    except BaseException as e:
        logging.error(f"Failed to write markdown to {full_path}: {e}", exc_info=True)
        return False
