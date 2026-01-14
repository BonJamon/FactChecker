from factchecker.factchecker import factchecker
from dotenv import load_dotenv
import os
import asyncio


load_dotenv()

result = asyncio.run(factchecker("Several demonstrants died in protests in Iran in January 2026."))
print(result)