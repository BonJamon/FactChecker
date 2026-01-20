from thenewsapi_mcp.server import create_server as create_news_server
from fastmcp.client import Client
from langchain.agents import create_agent
from dotenv import load_dotenv
from factchecker.templates import NEWS_AGENT_TEMPLATE
import os
from langsmith import traceable
from factchecker.helper import load_langchain_tools, Answer

@traceable(name="search_news")
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
                model="openai:gpt-4.1-nano",
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
        return Answer(answer="Unknown", summary="Internal errors", links=[])
    