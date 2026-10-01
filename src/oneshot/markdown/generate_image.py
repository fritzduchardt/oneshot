import asyncio
import base64
import io
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing_extensions import Buffer

from PIL import Image
from google import genai
from google.genai import types
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ..ai.ai_utils import get_model
from ..message_queue import q
from ..pattern import pattern


IMAGE_MODEL_NAME = os.getenv("IMAGE_MODEL", "gemini-3.1-flash-lite-image")
IMAGE_PROMPT_MODEL_NAME = os.getenv("IMAGE_PROMPT_MODEL", "deepseek-v4-flash")

_image_executor = ThreadPoolExecutor(max_workers=4)


def extract_images(md: str) -> list[str]:
    regex = r"\!\[\]\((.*)\)"
    matches = re.findall(regex, md)
    res = []
    for match in matches:
        s = str(match)
        res.append(s)
    return res


async def generate_food_images(
    md: str,
    base_path: str,
    path: str,
    pattern_config_pattern_dir: str,
):
    ingreds_pattern = pattern.get_pattern(pattern_config_pattern_dir, "food_image_ingreds")
    final_pattern = pattern.get_pattern(pattern_config_pattern_dir, "food_image_final")
    images = extract_images(md)
    str_output = StrOutputParser()
    if images:
        logging.info(f"Generating images for: {path}")
    else:
        logging.info(f"No images in {path}")
        return

    # Fire and forget each image generation task
    for image in images:
        cur_pattern = ingreds_pattern if image.endswith("ingredients.png") else final_pattern
        asyncio.create_task(
            generate_image(
                image,
                cur_pattern,
                md,
                base_path,
                path,
                str_output,
            )
        )


async def generate_image(
    image: str,
    cur_pattern: str,
    md: str,
    base_path: str,
    path: str,
    str_output: StrOutputParser,
):
    try:
        prompt = ChatPromptTemplate(
            [
                ("system", cur_pattern),
                ("human", "Recipe: {md}"),
            ]
        )
        prompt_model = get_model(IMAGE_PROMPT_MODEL_NAME)
        logging.info(f"Generating image prompt with: {IMAGE_PROMPT_MODEL_NAME}")
        chain = prompt | prompt_model | str_output
        image_prompt = await chain.ainvoke({"md": md})
        logging.info(f"Generating image: {image} with {IMAGE_MODEL_NAME}")
        client = _get_genai_client()

        response = await asyncio.to_thread(
            client.interactions.create,
            model=IMAGE_MODEL_NAME,
            input=image_prompt,
        )
        output_path = Path(f"{base_path}/{Path(path).parent}/{image}")
        with open(output_path.as_posix(), "wb") as f:
            f.write(base64.b64decode(response.output_image.data))

        #![](recipename-ingredients.png, e.g. lentil-patties-ingredients.png)
        msg = f"---\nmodel: {IMAGE_PROMPT_MODEL_NAME}\n---\n{image_prompt}\n\n![]({image})"
        data = {
            "message": msg,
            "basepath": str(Path(path).parent),
            "image": image,
        }
        q.put_nowait(data)
    except BaseException as e:
        logging.error("Failed during image generation: %s", e, exc_info=True)



def _get_genai_client() -> genai.Client:
    return genai.Client()
