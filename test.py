from factchecker.factchecker import factchecker
from dotenv import load_dotenv
import os
import asyncio
from langchain_openai import ChatOpenAI



load_dotenv()

result = asyncio.run(factchecker("Pluto is the 9nth planet."))
print(result)
