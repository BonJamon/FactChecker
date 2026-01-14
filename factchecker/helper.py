from wikipedia_mcp.server import create_server as create_wikipedia_server
from thenewsapi_mcp.server import create_server as create_news_server
from fastmcp.client import Client
from langchain_core.tools import StructuredTool 
from pydantic import BaseModel, confloat
from typing import Literal, Annotated, List
from langchain.agents import create_agent
from dotenv import load_dotenv
from factchecker.templates import NEWS_AGENT_TEMPLATE, WIKIPEDIA_AGENT_TEMPLATE, CLASSIFICATION_TEMPLATE
import os

async def load_langchain_tools(client, original_tools):
    """
    Adapt FastMCP tools to LangChain tools
    """
    tools = []
    for tool in original_tools:
        tool_name = tool.name
        async def _tool_runner(_tool_name = tool_name, **kwargs):
            return await client.call_tool(_tool_name, kwargs)

        tools.append(
            StructuredTool(
                name=tool.name,
                description=tool.description or "",
                args_schema=tool.inputSchema,
                coroutine=_tool_runner,
            )
        )
    return tools

class Answer(BaseModel):
    answer: Literal["True", "False", "Unknown"]
    summary: str
    links: List[str]

async def run_wikipedia_agent(query):
    load_dotenv()
    try:
        mcp = create_wikipedia_server()

        client = Client(mcp)
        async with client:
            tools = await client.list_tools()
            tools = await load_langchain_tools(client, tools)


            system_prompt=WIKIPEDIA_AGENT_TEMPLATE

            agent = create_agent(
                model="openai:gpt-4.1-mini",
                tools=tools,
                system_prompt=system_prompt,
                response_format=Answer
            )

            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": query}]}
            )
            return result["structured_response"]

        
    except ValueError as e:
        # Handle misconfiguration errors
        print(f"Error: {e}")
        return []
    

async def run_news_agent(query):
    load_dotenv()
    try:
        mcp = create_news_server(os.getenv("THENEWSAPI_API_KEY"))

        client = Client(mcp)
        async with client:
            tools = await client.list_tools()
            tools = await load_langchain_tools(client, tools)


            system_prompt=NEWS_AGENT_TEMPLATE

            agent = create_agent(
                model="openai:gpt-4.1-mini",
                tools=tools,
                system_prompt=system_prompt,
                response_format=Answer
            )

            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": query}]}
            )
            return result["structured_response"]

        
    except ValueError as e:
        # Handle misconfiguration errors
        print(f"Error: {e}")
        return []
    

class Classification(BaseModel):
    classification: Literal["Factual", "Interpretive", "Predictive", "Subjective"]
    wikipedia_prob: Annotated[float, confloat(ge=0.0, le=1.0)]
    news_prob: Annotated[float, confloat(ge=0.0, le=1.0)]



async def classify_and_score(query: str):
    """
    Takes a claim query and returns:
    - claim type
    - probability Wikipedia can answer
    - probability News can answer
    """
    agent = create_agent(
        model="openai:gpt-4.1-mini",
        system_prompt=CLASSIFICATION_TEMPLATE,
        response_format=Classification
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    return result["structured_response"]
