import io
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
from google import genai
from google.genai import types
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ..ai.ai_utils import get_deepseek, get_anthropic
from ..message_queue import q
from ..pattern import pattern

# imagen-4.0-ultra-generate-001
# imagen-4.0-generate-001
# imagen-4.0-fast-generate-001
IMAGE_MODEL_NAME = os.getenv("IMAGE_MODEL", "imagen-4.0-ultra-generate-001")
# IMAGE_PROMPT_MODEL_NAME = os.getenv("IMAGE_PROMPT_MODEL", "deepseek-v4-pro")
IMAGE_PROMPT_MODEL_NAME = os.getenv("IMAGE_PROMPT_MODEL", "claude-opus-4-7")

_image_executor = ThreadPoolExecutor(max_workers=4)


def extract_images(md: str) -> list[str]:
    regex = r"\!\[\]\((.*)\)"
    matches = re.findall(regex, md)
    res = []
    for match in matches:
        s = str(match)
        res.append(s)
    return res


def generate_food_images(
    md: str,
    base_path: str,
    path: str,
    pattern_config_pattern_dir: str,
):
    ingreds_pattern = pattern.get_pattern(pattern_config_pattern_dir, "food_image_ingreds")
    final_pattern = pattern.get_pattern(pattern_config_pattern_dir, "food_image_final")
    images = extract_images(md)
    str_output = StrOutputParser()

    for image in images:
        cur_pattern = ingreds_pattern if image.endswith("ingredients.png") else final_pattern
        # Submit image generation as fire and forget task to thread pool
        _image_executor.submit(
            generate_image,
            image,
            cur_pattern,
            md,
            base_path,
            path,
            str_output,
        )


def generate_image(
    image: str,
    cur_pattern: str,
    md: str,
    base_path: str,
    path: str,
    str_output: StrOutputParser,
):
    try:
        logging.info(f"Generating image: {image} with {IMAGE_MODEL_NAME}")
        prompt = ChatPromptTemplate(
            [
                ("system", cur_pattern),
                ("human", "Recipe: {md}"),
            ]
        )

        if IMAGE_PROMPT_MODEL_NAME.startswith("deepseek"):
            prompt_model = get_deepseek(IMAGE_PROMPT_MODEL_NAME)
        elif IMAGE_PROMPT_MODEL_NAME.startswith("claude"):
            prompt_model = get_anthropic(IMAGE_PROMPT_MODEL_NAME)
        else:
            raise RuntimeError(f"Unknown image model: {IMAGE_PROMPT_MODEL_NAME}")
        chain = prompt | prompt_model | str_output
        image_prompt = chain.invoke({"md": md})

        client = _get_genai_client()
        response = client.models.generate_images(
            model=IMAGE_MODEL_NAME,
            prompt=image_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="4:3"
            )
        )
        output_path = Path(f"{base_path}/{Path(path).parent}/{image}")
        for generated_image in response.generated_images:
            image_bytes: bytes | None = generated_image.image.image_bytes
            image_obj = Image.open(io.BytesIO(image_bytes))
            image_obj.save(output_path.as_posix())
            print("Image successfully saved to disk.")

        #![](recipename-ingredients.png, e.g. lentil-patties-ingredients.png)
        msg = f"---\nmodel: {IMAGE_PROMPT_MODEL_NAME}\npattern: {cur_pattern}---\n{image_prompt}\n\n![]({image})"
        data = {
            "message": msg,
            "basepath": str(Path(path).parent),
            "image": image,
        }
        q.put(data)
    except BaseException as e:
        logging.error("Failed during image generation: %s", e, exc_info=True)


def _get_genai_client() -> genai.Client:
    return genai.Client()
