import os
import langchain_community
from logger import logger

llm = None
clinet = None

def traslate_text(text):
    from langchain_community.llms import Ollama
    global llm
    if not llm:
        Ollama(base_url="http://192.168.1.2:11434", model="qwen3:14b")
    # Initialize the Ollama LLM
    # Generate text from the model
    response = llm.invoke("以下是小学一年级课本中的教学课文的英文语句，请将这句英文翻译成中文{}, 请通顺翻译，并且只需要翻译结果，不需要额外解释。".format(text))
    logger.info(response)

def traslate_text(text):
    global clinet
    if not clinet:
        from ollama import Client
        client = Client(host='http://192.168.1.2:11434')
    response = client.chat(model='qwen3:14b', messages=[
        {
            'role': 'user',
            'content': "请将这句英文翻译成中文{}。只给出翻译结果，不需要额外解释，注意简洁明了。".format(text),
        },
    ])
    ctx = response["message"]["content"]
    logger.info("traslate_text：{}".format(ctx))
    return ctx

if __name__ == "__main__":
    # traslate_text("I love you")
    text = "I love you"
    traslate_text(text)