import ast
import asyncio
import json
import logging
import os
import queue
import shutil
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, PlainTextResponse
from pydantic import BaseModel

from src.oneshot.ai.langchain import call_ai_only_tools
from .ai import ai_utils
from .message_queue import q
from .pattern import pattern
from .pattern import render
from .social import telegram
from .utils import fileutils

log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)
logging.getLogger("uvicorn.access").setLevel(logging.ERROR)


if not load_dotenv(os.getenv("OS_CONFIG_ENV_FILE")):
    logging.error(f"Failed to read env file.")

# import after env file was loaded
from .markdown import markdown

app = FastAPI()

READ_TIMEOUT = 600


class CompletionRequest(BaseModel):
    markdown: str | None = None
    with_mcp: bool = False
    message: str
    pattern: str
    model: str

class ChartRequest(BaseModel):
    pattern: str
    model: str
    message: str
    markdown: str | None = None


class MarkdownStoreRequest(BaseModel):
    path: str
    markdown: str


class TelegramSendRequest(BaseModel):
    markdown: str


@app.get("/stream")
async def stream():
    async def event_stream():
        try:
            while True:
                try:
                    data = q.get_nowait()
                    yield f"event: update\ndata: {json.dumps(data)}\n\n"
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/chart")
async def chart(body: ChartRequest):
    pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    pattern_name, prompt = _grep_pattern(pattern_dir, body.pattern, body.message)
    pattern_content = pattern.get_pattern(pattern_dir, pattern_name)
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    if body.markdown:
        markdown_file_content = Path(f"{base_path}/{body.markdown}").read_text()
        markdown_file_content = f"Journal File: {body.markdown}\n\n{markdown_file_content}"
        prompt = pattern.create_complete_prompt(prompt, markdown_file_content)
    result = await call_ai_only_tools(body.model, pattern.create_complete_pattern(body.model, body.pattern, pattern_content), prompt, "create_chart", )
    try:
        data = ast.literal_eval(result)
        return PlainTextResponse(content=data[0]["text"])
    except:
        return PlainTextResponse(content=f"---\npattern: {pattern_name}\n---\n{result}")


@app.post("/completion")
async def completion(body: CompletionRequest):
    try:
        pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
        base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
        markdown_path = body.markdown
        with_mcp = body.with_mcp
        weaviate_host = os.getenv("WEAVIATE_HOST", "localhost")
        weaviate_port = os.getenv("WEAVIATE_PORT", 80)
        weaviate_grpc_host = os.getenv("WEAVIATE_GRPC_HOST", "localhost")
        weaviate_grpc_port = os.getenv("WEAVIATE_GRPC_PORT", 50051)
        prompt = body.message
        pattern_name = body.pattern

        pattern_name, prompt = _grep_pattern(pattern_dir, pattern_name, prompt)
        if pattern_name == "weaviate":
            resp = ai_utils.call_weaviate(weaviate_host, weaviate_port, weaviate_grpc_host, weaviate_grpc_port, "PatternFile", prompt)
            if resp:
                logging.info(f"Weaviate found pattern: {resp[0].properties.get('path')}")
                pattern_name = Path(resp[0].properties["path"]).parent.name
            else:
                pattern_name = "general"

        pattern_content = pattern.get_pattern(pattern_dir, pattern_name)

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
                    weaviate_path = str(obj.properties["path"]).removeprefix(base_path + "/")
                    logging.info(f"Weaviate found markdown: {weaviate_path}")
                    markdown_path = weaviate_path
                    markdown_file_content += f"{obj.properties['content']}\n\n"
            else:
                markdown_file_content = Path(f"{base_path}/{markdown_path}").read_text()

        if markdown_file_content:
            markdown_file_content = f"Journal File: {markdown_path}\n\n{markdown_file_content}"

        if pattern_name == "prompt":
            pattern_content = await pattern.generate_pattern_from_prompt(pattern_content, body.model, prompt, markdown_file_content)
            logging.info(f"Generated pattern: {pattern_content}")

        llm_response = await ai_utils.complete(
            pattern_name,
            pattern_content,
            markdown_file_content,
            prompt,
            body.model,
            with_mcp,
            weaviate_host,
            weaviate_port,
            weaviate_grpc_host,
            weaviate_grpc_port,
        )
        return PlainTextResponse(content=llm_response)
    except BaseException as e:
        msg = f"Error in {e}"
        logging.error(msg)
        return PlainTextResponse(content=msg)


def _grep_pattern(pattern_dir: str | Any, pattern_name: str, prompt: str) -> tuple[str, str]:
    if pattern_name == "grep":
        if ":" in prompt:
            parts = prompt.split(":", 1)
            term = parts[0].strip()
            prompt = parts[1].strip()
        elif " " in prompt:
            parts = prompt.split(" ", 1)
            term = parts[0].strip()
            prompt = parts[1].strip()
        else:
            term = prompt.strip()
        if not (pattern_name := pattern.grep_pattern(pattern_dir, term)):
            logging.info("Grep pattern not found")
            pattern_name = "general"
    return pattern_name, prompt


@app.get("/patterns/names")
async def pattern_names():
    pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    logging.info(f"Listing patterns in: {pattern_dir}")
    patterns = pattern.list_patterns(pattern_dir)
    return JSONResponse(content=patterns)


@app.get("/patterns/{name}")
async def get_pattern(name: str):
    pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    # return plain text to avoid quoting
    return PlainTextResponse(content=pattern.get_pattern(pattern_dir, name))


@app.delete("/patterns/{name}")
async def delete_pattern(name: str):
    pattern_dir = os.getenv("OS_PATTERN_TEMPLATE_DIR")
    if pattern.delete_pattern(pattern_dir, name):
        return PlainTextResponse(content="OK")
    return PlainTextResponse(content="Failure")


@app.get("/models/names")
async def model_names():
    return JSONResponse(content=ai_utils.list_models())


@app.post("/patterns/generate")
async def generate_patterns():
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
    return PlainTextResponse(content="OK")


@app.get("/markdown/paths")
async def markdown_paths():
    paths: list[str] = []
    count: int = 1
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    while os.getenv(f"OS_MARKDOWN_VAULT_DIR_{count}"):
        path = os.getenv(f"OS_MARKDOWN_VAULT_DIR_{count}")
        paths.extend(markdown.list_files(f"{base_path}/{path}"))
        count = count + 1
    # trim base_path
    paths = [path.replace(f"{base_path}/", "") for path in paths]
    return JSONResponse(content=paths)


@app.get("/markdown/{file_path:path}")
async def get_markdown(file_path: str):
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
            raise HTTPException(status_code=404)
    content = markdown.get_md(md_path)
    return PlainTextResponse(content=content)


@app.delete("/markdown/{file_path:path}")
async def delete_markdown(file_path: str):
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    if markdown.delete_md(f"{base_path}/{file_path}"):
        return PlainTextResponse(content="OK")
    return PlainTextResponse(content="Failure")


@app.post("/markdown/store")
async def markdown_store(body: MarkdownStoreRequest):
    path = body.path
    md = body.markdown
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    pattern_config_pattern_dir = os.getenv("OS_CONFIG_PATTERN_DIR")
    if markdown.save_markdown(md, base_path, path, pattern_config_pattern_dir):
        return PlainTextResponse(content="OK")
    return PlainTextResponse(content="Failure")


@app.post("/telegram/send")
async def telegram_send(body: TelegramSendRequest):
    url_path = body.markdown
    count: int = 1
    while os.getenv(f"OS_MARKDOWN_VAULT_DIR_{count}"):
        url_path = url_path.replace(os.getenv(f"OS_MARKDOWN_VAULT_DIR_{count}"), "")
        count = count + 1
    url_path = url_path.replace(".md", ".html")
    logging.info(f"Sharing path: {url_path}")
    try:
        telegram.send(f"https://yummy.duchardt.net/{url_path}", os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID"))
        return PlainTextResponse(content="OK")
    except Exception as e:
        logging.error(e)
        return PlainTextResponse(content="Failure")


@app.get("/image/{image_path:path}")
async def get_image(image_path: str):
    base_path = os.getenv("OS_MARKDOWN_BASE_DIR")
    full_image_path = f"{base_path}/{image_path}"
    if not Path(full_image_path).exists():
        raise HTTPException(status_code=404)
    return FileResponse(full_image_path, media_type="image/jpeg")


@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        response = PlainTextResponse("OK", status_code=200)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        return response
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        timeout_keep_alive=READ_TIMEOUT,
    )
