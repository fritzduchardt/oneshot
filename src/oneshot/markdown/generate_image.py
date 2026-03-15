from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-5.4")

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

def generate_images(
    md: str
):
    output_parser = StrOutputParser()
    prompt = ChatPromptTemplate(
        [
            ("system", "You are a helpful AI bot. Your name is {name}."),
            ("human", "Hello, how are you doing?"),
        ]
    )
    chain = prompt | model | output_parser

    result = chain.invoke({"name", "gonzo"})

    print(result)
