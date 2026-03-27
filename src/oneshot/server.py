import logging
import os
import shutil
from pathlib import Path

from flask import Flask, request, send_file, abort

from . import ai_utils
from .pattern import pattern
from .pattern import render
from .social import telegram
from .utils import fileutils
from dotenv import load_dotenv

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)


if not load_dotenv(os.getenv("OS_CONFIG_ENV_FILE")):
    logging.error(f"Failed to read env file.")

# import after env file was loaded
from .markdown import markdown

app = Flask(__name__)


@app.route("/completion", methods=["POST"])
def completion():
    data = request.get_json()
    pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    markdown_path = data["markdown"]
    with_mcp = data["with_mcp"]
    weaviate_host = os.getenv("WEAVIATE_HOST", "localhost")
    weaviate_port = os.getenv("WEAVIATE_PORT", 80)
    weaviate_grpc_host = os.getenv("WEAVIATE_GRPC_HOST", "localhost")
    weaviate_grpc_port = os.getenv("WEAVIATE_GRPC_PORT", 50051)
    prompt = data["message"]
    pattern_name = data["pattern"]

    if pattern_name == "weaviate":
        resp = ai_utils.call_weaviate(weaviate_host, weaviate_port, weaviate_grpc_host, weaviate_grpc_port, "PatternFile", prompt)
        if resp:
            logging.info(f"Weaviate found pattern: {resp[0].properties.get("path")}")
            pattern_name = Path(resp[0].properties["path"]).parent.name
        else:
            pattern_name = "general"

    markdown_file_content = ""
    if markdown_path:
        if markdown_path == "weaviate":
            resp = ai_utils.call_weaviate(
                weaviate_host,
                weaviate_port,
                weaviate_grpc_host,
                weaviate_grpc_port,
                "ObsidianFile",
                prompt,
                5,
            )
            for obj in resp:
                weaviate_path = str(obj.properties['path']).removeprefix(base_path + "/")
                logging.info(f"Weaviate found markdown: {weaviate_path}")
                markdown_file_content += f"FILENAME: {weaviate_path}\n"
                markdown_file_content += f"{obj.properties['content']}\n\n"
        else:
            markdown_file_content = Path(f"{base_path}/{markdown_path}").read_text()

    if markdown_file_content:
        markdown_file_content = f"Journal Files:\n\n{markdown_file_content}"

    return ai_utils.complete(
        pattern_dir,
        pattern_name,
        markdown_file_content,
        prompt,
        data["model"],
        with_mcp,
        weaviate_host,
        weaviate_port,
        weaviate_grpc_host,
        weaviate_grpc_port,
    )


@app.route("/patterns/names")
def pattern_names():
    pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    logging.info(f"Listing patterns in: {pattern_dir}")
    patterns = pattern.list_patterns(pattern_dir)
    return patterns


@app.route("/patterns/<name>")
def get_pattern(name: str):
    pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    return pattern.get_pattern(pattern_dir, name)


@app.route("/patterns/<name>", methods=["DELETE"])
def delete_pattern(name: str):
    pattern_dir = os.getenv("OS_PATTERN_TEMPLATE_DIR")
    if pattern.delete_pattern(pattern_dir, name):
        return "OK"
    return "Failure"


@app.route("/models/names")
def model_names():
    return ai_utils.list_models()


@app.route("/patterns/generate", methods=["POST"])
def generate_patterns():
    output_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    sync_pattern_dir = os.getenv("OS_SYNC_PATTERN_DIR")
    pattern_dir_1 = os.getenv("OS_PATTERN_TEMPLATE_DIR")
    pattern_dir_2 = (
        f"{os.getenv('OS_MARKDOWN_BASE_DIR')}/"
        f"{os.getenv('OS_MARKDOWN_VAULT_PATTERN_DIR')}"
    )
    # shutils fails on emptydir
    fileutils.clear_directory_contents(output_dir)
    render.render_jinja2_templates(output_dir, {pattern_dir_1, pattern_dir_2})
    if sync_pattern_dir:
        logging.info(f"Syncing patterns in {sync_pattern_dir}")
        fileutils.clear_directory_contents(sync_pattern_dir)
        shutil.copytree(output_dir, sync_pattern_dir, dirs_exist_ok=True)
    return "OK"


@app.route("/markdown/paths")
def markdown_paths():
    paths: list[str] = []
    count: int = 1
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    while os.getenv(f"OS_MARKDOWN_VAULT_DIR_{count}"):
        path = os.getenv(f"OS_MARKDOWN_VAULT_DIR_{count}")
        paths.extend(markdown.list_files(f"{base_path}/{path}"))
        count = count + 1
    # trim base_path
    paths = [path.replace(f"{base_path}/", "") for path in paths]
    return paths


@app.route("/markdown/<path:file_path>")
def get_markdown(file_path:str):
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    md_path = f"{base_path}/{file_path}"
    if not Path(md_path).exists():
        md_name = Path(md_path).name
        logging.info(f"Path inconclusive: {md_path}. Looking for: {md_name}")
        found = False
        for file in Path(base_path).rglob(md_name):
            md_path = file
            found = True
            break
        if not found:
            abort(404)
    return markdown.get_md(md_path)


@app.route("/markdown/<path:file_path>", methods=["DELETE"])
def delete_markdown(file_path:str):
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    if markdown.delete_md(f"{base_path}/{file_path}"):
        return "OK"
    return "Failure"


@app.route("/markdown/store", methods=["POST"])
def markdown_store():
    data = request.get_json()
    path = data["path"]
    md = data["markdown"]
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    pattern_config_pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    if markdown.save_markdown(md, f"{base_path}/{path}", pattern_config_pattern_dir):
        return "OK"
    return "Failure"


@app.route("/telegram/send", methods=["POST"])
def telegram_send():
    data = request.get_json()
    url_path = data["markdown"]
    count: int = 1
    while os.getenv(f"OS_MARKDOWN_VAULT_DIR_{count}"):
        url_path = url_path.replace(os.getenv(f"OS_MARKDOWN_VAULT_DIR_{count}"), "")
        count = count + 1
    url_path = url_path.replace('.md', '.html')
    logging.info(f"Sharing path: {url_path}")
    try:
        telegram.send(f"https://yummy.duchardt.net/{url_path}", os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID"))
        return "OK"
    except Exception as e:
        logging.error(e)
        return "Failure"


@app.route("/image/<path:image_path>")
def get_image(image_path: str):
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    image_path = f"{base_path}/{image_path}"
    if not Path(image_path).exists():
        return abort(404)
    logging.info(f"Sending image: {image_path}")
    return send_file(image_path, mimetype="image/jpeg")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
