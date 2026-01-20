from langchain_core.tools import StructuredTool 
from pydantic import BaseModel, confloat
from typing import Literal, Annotated, List, Any
from langchain.agents import create_agent
from factchecker.templates import CLASSIFICATION_TEMPLATE
from langsmith import traceable
from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langgraph.runtime import Runtime


async def load_langchain_tools(client, original_tools):
    """
    Adapt FastMCP tools to LangChain tools
    """
    tools = []
    for tool in original_tools:
        tool_name = tool.name
        async def _tool_runner(_tool_name = tool_name, **kwargs):
            result = await client.call_tool(_tool_name, kwargs)
            return result.structured_content

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


class ContentFilterMiddleware(AgentMiddleware):
    """Deterministic guardrail: Block requests containing banned keywords."""

    def __init__(self, banned_keywords: list[str]):
        super().__init__()
        self.banned_keywords = [kw.lower() for kw in banned_keywords]

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        # Get the first user message
        if not state["messages"]:
            return None

        first_message = state["messages"][0]
        if first_message.type != "human":
            return None

        content = first_message.content.lower()

        # Check for banned keywords
        for keyword in self.banned_keywords:
            if keyword in content:
                # Block execution before any processing
                return {
                    "messages": [{
                        "role": "assistant",
                        "content": "Inappropriate"
                    }],
                    "jump_to": "end"
                }

        return None
    
    

class Classification(BaseModel):
    classification: Literal["Factual", "Interpretive", "Predictive", "Subjective"]
    wikipedia_prob: Annotated[float, confloat(ge=0.0, le=1.0)]
    news_prob: Annotated[float, confloat(ge=0.0, le=1.0)]


@traceable(name="classify_claim")
async def classify_and_score(query: str):
    """
    Takes a claim query and returns:
    - claim type
    - probability Wikipedia can answer
    - probability News can answer
    """
    agent = create_agent(
        model="openai:gpt-4.1-nano",
        system_prompt=CLASSIFICATION_TEMPLATE,
        response_format=Classification,
        middleware=[ContentFilterMiddleware(banned_keywords=["hack", "exploit", "malware"])]
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    #Check if guardrails detected prompt injection attack
    if result["messages"][-1].content=="Inappropriate":
        return "Inappropriate"
    else:
        return result["structured_response"]

