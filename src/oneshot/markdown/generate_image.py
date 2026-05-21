import io
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ..message_queue import q
from ..pattern import pattern

CHAT_MODEL_NAME = os.getenv("CHAT_MODEL", "claude-sonnet-4-6")
# imagen-4.0-ultra-generate-001
# imagen-4.0-generate-001
# imagen-4.0-fast-generate-001
IMAGE_MODEL_NAME = os.getenv("IMAGE_MODEL", "imagen-4.0-ultra-generate-001")

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

        chat_model = _get_chat_model()
        chain = prompt | chat_model | str_output
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
            image_bytes = generated_image.image.image_bytes
            image_obj = Image.open(io.BytesIO(image_bytes))
            image_obj.save(output_path.as_posix())
            print("Image successfully saved to disk.")

        #![](recipename-ingredients.png, e.g. lentil-patties-ingredients.png)
        msg = f"{image_prompt}\n\n![]({image})"
        data = {
            "message": msg,
            "basepath": str(Path(path).parent),
            "image": image,
        }
        logging.info(f"Sending message: {data}")
        q.put(data)
    except BaseException as e:
        logging.error("Failed during image generation: %s", e, exc_info=True)


def _get_chat_model() -> ChatAnthropic:
    return ChatAnthropic(model=CHAT_MODEL_NAME)


def _get_genai_client() -> genai.Client:
    return genai.Client()
