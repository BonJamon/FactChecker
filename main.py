from wikipedia_mcp.wikipedia_client import WikipediaClient
from wikipedia_mcp.server import create_server
import asyncio
from fastmcp.client import Client
from langchain_core.tools import StructuredTool 
from pydantic import BaseModel
from typing import Literal
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from dotenv import load_dotenv

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

async def main():
    load_dotenv()
    try:
        mcp = create_server()

        client = Client(mcp)
        async with client:
            tools = await client.list_tools()
            tools = await load_langchain_tools(client, tools)

            class Answer(BaseModel):
                answer: Literal["True", "False", "Unknown"]
                summary: str
                links: str

            system_prompt="""You are a fact checker that verifies information based on wikipedia entries.
            You call tools of the wikipedia mcp server and return the following:
            1.) A short answer that is one of these options [True, False, Unknown]. Use Unknown if it cannot be known for sure or you could not find prove.
            2.) A short 1-3 sentence summary of why this is the answer
            3.) Any wikipedia links from where you have this information."""

            agent = create_agent(
                model="openai:gpt-4.1-mini",
                tools=tools,
                system_prompt=system_prompt,  # default tool-calling prompt
                response_format=Answer
            )

            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": "Brad Pitt is a big fan of cheese"}]}
            )
            print(result["structured_response"])

        
        

    except ValueError as e:
        # Handle misconfiguration errors (e.g., unsupported country codes)
        print(f"Error: {e}")
        print("\nUse --list-countries to see supported country codes.")
        return


if __name__ == "__main__":
    asyncio.run(main())
