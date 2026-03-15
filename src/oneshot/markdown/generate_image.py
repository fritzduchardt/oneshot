import logging
import os
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_classic.chains import LLMChain
from langchain_community.utilities.dalle_image_generator import DallEAPIWrapper
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAI
from ..pattern import pattern
chat_model = ChatOpenAI(model="gpt-5.4")

# ingredients_image = (
#     "Create me an image" | model
# )
# final_image = (
#     "Create me an image" | model
# )
#
# runnable = RunnableParallel(image_1=ingredients_image, image_2=final_image)
#
# runnable.ainvoke()

def extract_image_links(md: str) -> [str]:
    regex = r'\!\[\]\((.*)\)'
    matches = re.findall(regex, md)
    res = [str]
    for match in matches:
        res.append(match)
    return res

def generate_food_images(
    md: str
):
    logging.info(f"Creating image prompt for: {md}")
    ingreds_pattern = pattern.get_pattern(os.getenv("OS_CONFIG_PATTERN_DIR"), "food_image_ingreds")
    final_pattern = pattern.get_pattern(os.getenv("OS_CONFIG_PATTERN_DIR"), "food_image_final")
    links = extract_image_links(md)
    logging.info(f"Links: {links}")
    dale = DallEAPIWrapper(model="dall-e-3")

    output_parser = StrOutputParser()
    prompt = ChatPromptTemplate(
        [
            ("system", ingreds_pattern),
            ("human", "Recipe: {md}"),
        ]
    )
    chain = prompt | chat_model | output_parser

    image_prompt = chain.invoke({"md", md})
    logging.info(f"Image prompt: {image_prompt}")

    image_url = dale.run(image_prompt)
    print(image_url)

    prompt = ChatPromptTemplate(
        [
            ("system", final_pattern),
            ("human", "Recipe: {md}"),
        ]
    )
    chain = prompt | chat_model | output_parser

    image_prompt = chain.invoke({"md", md})
    logging.info(f"Image prompt: {image_prompt}")

    image_url = dale.run(image_prompt)
    print(image_url)
