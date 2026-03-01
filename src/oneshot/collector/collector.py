import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def collect_files(collect_expr: str, include_hidden: bool) -> None:
    pattern = re.compile(rf"{collect_expr}")
    for root, dirs, files in os.walk("."):

        if not include_hidden:
            dirs[:] = filter_dirs(dirs)
            files = filter_files(files)

        for filename in files:
            full_path = Path(root) / filename
            if pattern.search(str(full_path)):
                cat_file(full_path)

def collect_files_async(collect_expr: str, include_token: bool, num_threads: int):
    pattern = re.compile(rf"{collect_expr}")
    futures = []

    # iterate over all files in directory tree
    for root, dirs, files in os.walk("."):

        # remove hidden
        if not include_token:
            dirs[:] = filter_dirs(dirs)
            files = filter_files(files)

        # match files
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures.extend([executor.submit(search_file, str(Path(root) / f), pattern) for f in files])

    # write files
    for future in as_completed(futures):
        result = future.result()
        if result:
            cat_file(result)

def filter_files(files: list[str]) -> list[str]:
    return [f for f in files if not f.startswith(".") \
            and not f.endswith("lock.json") \
            and not f.endswith(".ico") \
            and not f.endswith(".png") \
            and not f.endswith(".jpg") \
            and not f.endswith(".jpeg") \
            and not f.endswith(".gif") \
        ]

def filter_dirs(dirs: list[str]) -> list[str]:
    return [d for d in dirs if not d.startswith(".") \
            and not d.startswith("__") \
            and not d.startswith("node_modules") \
            and not d.startswith("dist") \
        ]

def search_file(path: str, pattern) -> str:
    if pattern.search(path):
        return path
    return ""

def cat_file(path: str):
    print(f"FILENAME: {path}")
    print("\n")
    print(Path(path).read_text(encoding="utf-8"))
