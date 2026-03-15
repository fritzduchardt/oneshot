import asyncio
import logging
import re
from pathlib import Path

from langchain_community.utilities.dalle_image_generator import DallEAPIWrapper
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from urllib.request import urlretrieve

from ..pattern import pattern

chat_model = ChatOpenAI(model="gpt-5.4")
dalle = DallEAPIWrapper(model="dall-e-3")

def extract_images(md: str) -> list[str]:
    regex = r'\!\[\]\((.*)\)'
    matches = re.findall(regex, md)
    res = []
    for match in matches:
        s = str(match)
        res.append(s)
    return res

async def generate_food_images(
    md: str,
    md_file_path: str,
    pattern_config_pattern_dir,
):
    ingreds_pattern = pattern.get_pattern(pattern_config_pattern_dir, "food_image_ingreds")
    final_pattern = pattern.get_pattern(pattern_config_pattern_dir, "food_image_final")
    images = extract_images(md)
    str_output = StrOutputParser()

    tasks = []
    for image in images:
        cur_pattern = ingreds_pattern if image.endswith("ingredients.png") else final_pattern
        tasks.append(generate_image(image, cur_pattern, md, md_file_path, str_output))

    await asyncio.gather(*tasks)


async def generate_image(image: str, cur_pattern: str, md: str, md_file_path: str, str_output: StrOutputParser):
    logging.info(f"Generating image: {image}")
    prompt = ChatPromptTemplate(
        [
            ("system", cur_pattern),
            ("human", "Recipe: {md}"),
        ]
    )

    chain = prompt | chat_model | str_output
    image_prompt = await chain.ainvoke({"md": md})
    logging.info(f"Image prompt: {image_prompt}")

    image_url = await asyncio.to_thread(dalle.run, image_prompt)
    logging.info(f"Image url: {image_url}")
    output_path = f"{Path(md_file_path).parent}/{image}"
    logging.info(f"Image output path: {output_path}")
    await asyncio.to_thread(urlretrieve, image_url, output_path)