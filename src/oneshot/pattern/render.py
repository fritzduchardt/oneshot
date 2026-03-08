import logging
import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def render_jinja2_templates(output_path: str, pattern_paths_set: set[str]) -> None:

    output_path = Path(output_path)
    template_dirs = [ f"{path}/templates" for path in pattern_paths_set ]
    all_templates_files = []
    all_templates_files.extend(pattern_paths_set)
    all_templates_files.extend(template_dirs)

    # Initialize Jinja2 environment with the template root
    env = Environment(
        loader=FileSystemLoader([Path(path) for path in all_templates_files]),
        keep_trailing_newline=True,  # Preserve newlines (important for configs)
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # files
    context: dict = {
        "recipes": get_files_in_dir(os.getenv('OS_MARKDOWN_BASE_DIR'), os.getenv('OS_MARKDOWN_VAULT_DIR_2')),
    }
    # Walk through all files
    for path in pattern_paths_set:
        logging.info(f"Render root path: {path}")
        for root, dirs, files in os.walk(path):

            dirs[:] = [d for d in dirs if not d.startswith(".") and not d.endswith("templates")]
            files = [f for f in files if not f.startswith(".")]

            for filename in files:
                if not filename.endswith('.j2'):
                    logging.info(f"Skipping: {filename}")
                    continue

                # Calculate relative path from template root
                full_path = Path(root) / filename
                rel_path = full_path.relative_to(path)

                # Render template
                template = env.get_template(rel_path.as_posix())
                rendered = template.render(**context)

                # Write output (strip .j2 extension)
                out_file = output_path / str(rel_path).removesuffix('.j2')
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_text(rendered)
                logging.info(f"Rendered: {out_file}")

def get_files_in_dir(base_path: str, dir_path: str) -> list[str]:
    root_dir = f"{base_path}/{dir_path}"
    logging.info(f"Getting files in: {root_dir}")
    res = []
    if not os.path.exists(root_dir):
        logging.error(f"Directory does not exist: {root_dir}")
        return res

    for root, dirs, files in os.walk(root_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                res.append(file_path.replace(f"{base_path}/", ""))

    return res
