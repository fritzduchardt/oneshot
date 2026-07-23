import asyncio
import json
import logging
import os
import sys
from typing import List

import typer
from rich.console import Console
from rich.markdown import Markdown

from dotenv import load_dotenv

from .ai import ai_utils
from .collector import collector as c
from .generator import generator
from .pattern import pattern as p
from .pattern import render

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if not load_dotenv(os.getenv("OS_CONFIG_ENV_FILE")):
    logging.error("Failed to read env file.")

oneshot = typer.Typer(help="Oneshot AI CLI", context_settings={"help_option_names": {"-h", "--help"}})
# Groups
patterns_grp = typer.Typer(help="Manage your pattern files")
models_grp = typer.Typer(help="Manage API Models")
tokens_grp = typer.Typer(help="Calculate tokens")
oneshot.add_typer(patterns_grp, name="patterns")
oneshot.add_typer(models_grp, name="models")
oneshot.add_typer(tokens_grp, name="tokens")

@oneshot.command(name="shoot")
def shoot_cmd(
    pattern_name: str = typer.Option("general", "--pattern", "-p", help="Predefined prompt pattern"),
    pattern_dir: str = typer.Option(
        "",
        "--pattern-dir",
        help="Directory where prompt patterns are located",
        envvar="OS_PATTERN_DIR",
    ),
    with_mcp: bool = typer.Option(False, "--mcp", help="Call with mcp server url"),
    output_to_disk: bool = typer.Option(False, "--output-to-disk", "-o", help="Write LLM output back to disk"),
    model: str = typer.Option(..., "--model", "-m", help="LLM model to use", envvar="DEFAULT_MODEL"),
    read_stdin: bool = typer.Option(False, "--stdin", "-s", help="Read input from stdin"),
    prompt: List[str] = typer.Argument([], help="User prompt"),
    weaviate_host: str = typer.Option("localhost", "--weaviate-host", help="Weaviate host", envvar="WEAVIATE_HOST"),
    weaviate_port: int = typer.Option(80, "--weaviate-port", help="Weaviate port", envvar="WEAVIATE_PORT"),
    weaviate_grpc_host: str = typer.Option(
        "localhost",
        "--weaviate-grpc-host",
        help="Weaviate grpc host",
        envvar="WEAVIATE_GRPC_HOST",
    ),
    weaviate_grpc_port: int = typer.Option(
        50051,
        "--weaviate-grpc-port",
        help="Weaviate grpc port",
        envvar="WEAVIATE_GRPC_PORT",
    ),
):
    if pattern_dir == "":
        pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")

    stdin = ""
    if read_stdin:
        data = sys.stdin.buffer.read()
        stdin = data.decode("utf-8", errors="replace")

    prompt_str = ""
    if prompt:
        prompt_str = " ".join(prompt)

    llm_resp, metadata = asyncio.run(ai_utils.complete(
        pattern_name,
        p.get_pattern(pattern_dir, pattern_name),
        stdin,
        prompt_str,
        model,
        with_mcp,
        weaviate_host,
        weaviate_port,
        weaviate_grpc_host,
        weaviate_grpc_port,
    ))
    if metadata["costs"]:
        logging.info(f"Costs: {metadata["costs"]}")

    if output_to_disk:
        generator.write_to_disk(llm_resp)
    else:
        encoding = sys.stdout.encoding or "utf-8"
        sys.stdout.buffer.write(llm_resp.encode(encoding, "replace"))

@oneshot.command(name="collect")
def collect_cmd(
    collect_dir: str = typer.Argument(".", help="Collect directory or regex"),
    include_hidden: bool = typer.Option(False, "--hidden", "-H", help="Include hidden files in collection"),
    num_threads: int = typer.Option(1, "--threads", "-t", help="Number of concurrent threads for operation"),
):
    collect_dir = collect_dir.lstrip("./")
    if num_threads > 1:
        logging.debug(f"Running with {num_threads} threads")
        c.collect_files_async(collect_dir, include_hidden, num_threads)
    else:
        logging.debug("Running single threaded")
        c.collect_files(collect_dir, include_hidden)

@oneshot.command(name="md")
def md_cmd():
    content = sys.stdin.read()
    console = Console(width=100)
    print("\n")
    console.print(Markdown(content, justify="left"))
    print("\n")

@patterns_grp.command(name="list")
def list_patterns_cmd(
    pattern_dir: str = typer.Option(
        "",
        "--pattern-dir",
        help="Directory where prompt patterns are located",
        envvar="OS_CONFIG_PATTERN_DIR",
    ),
):
    logging.info(f"Listing patterns in: {pattern_dir}")
    patterns = asyncio.run(p.list_patterns(pattern_dir))
    print(json.dumps(patterns))

@patterns_grp.command(name="generate")
def generate_patterns_cmd(
    output_dir: str = typer.Option(
        ...,
        "--output-dir",
        "-o",
        help="Output directory for generated pattern files",
    ),
    pattern_template_dir: list[str] = typer.Option(
        ...,
        "--template-dir",
        "-t",
        help="Template directories with Fabric pattern templates to process (can be used multiple times)",
    ),
):
    if not os.path.exists(output_dir):
        logging.error(f"Output dir does not exist: {output_dir}")
        return

    render.render_jinja2_templates(output_dir, set(pattern_template_dir))

@models_grp.command(name="list")
def list_models_cmd():
    print(json.dumps(ai_utils.list_models()))

@tokens_grp.command(name="count")
def count_tokens_cmd():
    data = sys.stdin.buffer.read()
    stdin = data.decode("utf-8", errors="replace")
    print(ai_utils.count_tokens(stdin))

if __name__ == "__main__":
    oneshot()
