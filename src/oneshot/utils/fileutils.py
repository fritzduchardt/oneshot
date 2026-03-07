from pathlib import Path

def clear_directory_contents(directory_path: str):
    if not directory_path:
        return
    directory = Path(directory_path)
    if not directory.exists() or not directory.is_dir():
        return
    for entry in directory.iterdir():
        if entry.is_dir():
            for root, dirs, files in os.walk(entry, topdown=False):
                for file_name in files:
                    Path(root, file_name).unlink(missing_ok=True)
                for dir_name in dirs:
                    Path(root, dir_name).rmdir()
            entry.rmdir()
        else:
            entry.unlink(missing_ok=True)
