import logging
import os
from pathlib import Path
from . import ai_utils

from flask import Flask, request
from .pattern import pattern
from .pattern import render
from .markdown import markdown
from .social import telegram
from .utils import fileutils

log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__)

@app.route("/completion", methods=["POST"])
def completion():
    data = request.get_json()
    env_file = os.getenv("OS_CONFIG_ENV_FILE")
    pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    markdown_path = data["markdown"]
    with_mcp = data["with_mcp"]
    weaviate_host = os.getenv("WEAVIATE_HOST", "localhost")
    weaviate_port = os.getenv("WEAVIATE_PORT", 80)
    weaviate_grpc_host = os.getenv("WEAVIATE_GRPC_HOST", "localhost")
    weaviate_grpc_port = os.getenv("WEAVIATE_GRPC_PORT", 50051)
    prompt = data["message"]

    markdown_file_content="Journal Files:\n\n"
    if markdown_path:
        if markdown_path == "weaviate":
            resp = ai_utils.call_weaviate(weaviate_host, weaviate_port, weaviate_grpc_host, weaviate_grpc_port, "ObsidianFile", prompt, 5)
            for obj in resp:
                logging.info(f"Weaviate found markdown: {obj.properties["path"]}")
                markdown_file_content += f"FILENAME: {obj.properties["path"]}\n"
                markdown_file_content += f"{obj.properties["content"]}\n\n"
        else:
            markdown_file_content = Path(f"{base_path}/{markdown_path}").read_text()

    return ai_utils.complete(
        env_file,
        pattern_dir,
        data["pattern"],
        markdown_file_content,
        prompt,
        data["model"],
        os.getenv("MCP_URL") if with_mcp else "",
        weaviate_host,
        weaviate_port,
        weaviate_grpc_host,
        weaviate_grpc_port
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
def model_names(
):
    env_file = os.getenv("OS_CONFIG_ENV_FILE")
    return ai_utils.list_models(env_file)

@app.route("/patterns/generate", methods=["POST"])
def generate_patterns():
    output_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    pattern_dir_1 = os.getenv("OS_PATTERN_TEMPLATE_DIR")
    pattern_dir_2 = f"{os.getenv("OS_MARKDOWN_BASE_DIR")}/{os.getenv('OS_MARKDOWN_VAULT_PATTERN_DIR')}"
    fileutils.clear_directory_contents(output_dir)
    render.render_jinja2_templates(output_dir, {pattern_dir_1, pattern_dir_2})
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
    paths = [ path.replace(f"{base_path}/", "") for path in paths]
    return paths

@app.route("/markdown/file")
def get_markdown():
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    path = request.args.get("path")
    return markdown.get_md(f"{base_path}/{path}")

@app.route("/markdown/file", methods=["DELETE"])
def delete_markdown():
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    path = request.args.get("path")
    if markdown.delete_md(f"{base_path}/{path}"):
        return "OK"
    return "Failure"

@app.route("/markdown/store", methods=["POST"])
def markdown_store():
    data = request.get_json()
    path = data["path"]
    md = data["markdown"]
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    if markdown.save_markdown(md, f"{base_path}/{path}"):
        return "OK"
    return "Failure"

@app.route("/telegram/send", methods=["POST"])
def telegram_send():
    data = request.get_json()
    telegram.send(data["message"], os.getenv("TELEGRAM_BOT_TOKEN"))

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
