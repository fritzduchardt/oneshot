import base64
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from openai import OpenAI
from openai.types.images_response import ImagesResponse

from ..message_queue import q
from ..pattern import pattern

chat_model = ChatOpenAI(model="gpt-5.5")
openai_client = OpenAI()

_image_executor = ThreadPoolExecutor(max_workers=4)


def extract_images(md: str) -> list[str]:
    regex = r'\!\[\]\((.*)\)'
    matches = re.findall(regex, md)
    res = []
    for match in matches:
        s = str(match)
        res.append(s)
    return res


def generate_food_images(
    md: str,
    md_file_path: str,
    pattern_config_pattern_dir,
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
            md_file_path,
            str_output,
        )


def generate_image(image: str, cur_pattern: str, md: str, md_file_path: str, str_output: StrOutputParser):
    logging.info(f"Generating image: {image}")
    prompt = ChatPromptTemplate(
        [
            ("system", cur_pattern),
            ("human", "Recipe: {md}"),
        ]
    )

    chain = prompt | chat_model | str_output
    image_prompt = chain.invoke({"md": md})
    logging.info(f"Image prompt: {image_prompt}")

    response: ImagesResponse = openai_client.images.generate(
        model="gpt-image-2",
        prompt=image_prompt,
    )
    output_path = Path(f"{Path(md_file_path).parent}/{image}")
    logging.info(f"Image output path: {output_path}")
    output_path.write_bytes(base64.b64decode(response.data[0].b64_json))
    q.put({"message": f"Saved: {Path(md_file_path).name}/{image}"})
