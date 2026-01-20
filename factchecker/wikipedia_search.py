from wikipedia_mcp.server import create_server as create_wikipedia_server
from fastmcp.client import Client
from pydantic import BaseModel
from typing import Literal, Annotated, List, Any, Dict
from langchain.agents import create_agent
from dotenv import load_dotenv
from factchecker.templates import  WIKIPEDIA_SEARCH_TEMPLATE, WIKIPEDIA_SELECTION_TEMPLATE, WIKIPEDIA_VERIFICATION_TEMPLATE
from langsmith import traceable
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
import re
import json

from factchecker.helper import load_langchain_tools, Answer

'''
Tool Helper Functions
'''

def sections_titles_only(tool_result):
    sc = tool_result.structured_content

    return {
        "pageid": sc.get("pageid"),
        "sections": [
            section["title"]
            for section in sc.get("sections", [])
            if "title" in section
        ],
    }    

def _wordcount(text: str) -> int:
    return len(text.split()) if text else 0


def _first_sentences(text: str, max_sentences: int = 2) -> str:
    if not text:
        return ""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return " ".join(sentences[:max_sentences])

def _aggregate_metadata(section: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregate wordcount, leaf count, and find summary text for a subtree.
    """
    total_words = _wordcount(section.get("text", ""))
    leaf_count = 0

    summary_text = section.get("text", "") or ""

    for child in section.get("sections", []):
        child_meta = _aggregate_metadata(child)
        total_words += child_meta["aggregate_wordcount"]
        leaf_count += child_meta["leaf_count"]

        if not summary_text and child_meta["summary"]:
            summary_text = child_meta["summary"]

    if not section.get("sections"):
        leaf_count = 1

    return {
        "aggregate_wordcount": total_words,
        "leaf_count": leaf_count,
        "summary": _first_sentences(summary_text),
    }

def _extract_text(section: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregate wordcount, leaf count, and find summary text for a subtree.
    """
    full_text = section.get("text", "") or ""
    total_words = _wordcount(section.get("text", ""))
    for child in section.get("sections", []):
        child_data = _extract_text(child)
        total_words += child_data["aggregate_wordcount"]
        full_text += child_data["text"]
    return {"aggregate_wordcount": total_words,
            "text": full_text}




def _build_units(
    sections: List[Dict[str, Any]],
    path: List[str] = []
) -> List[Dict[str, Any]]:
    """
    Build retrieval units from hierarchical sections.
    """
    units = []

    for section in sections:
        current_path = path + [section["title"]]
        level = section["level"]

        # Define unit roots (levels 0–2)
        if level <= 2:
            meta = _aggregate_metadata(section)

            units.append({
                "id": " > ".join(current_path),
                "path": current_path,
                "depth": level,
                "aggregate_wordcount": meta["aggregate_wordcount"],
                "leaf_count": meta["leaf_count"],
                "summary": meta["summary"],
            })

        # Always recurse
        units.extend(_build_units(section.get("sections", []), current_path))

    return units


def _build_units_fulltext(
    sections: List[Dict[str, Any]],
    path: List[str] = []
) -> List[Dict[str, Any]]:
    """
    Build retrieval units from hierarchical sections.
    """
    units = []

    for section in sections:
        current_path = path + [section["title"]]
        level = section["level"]

        # Define unit roots (levels 0–2)
        if level <= 2:
            data = _extract_text(section)
            text = data["text"]
            wordcount = data["aggregate_wordcount"]

            units.append({
                "id": " > ".join(current_path),
                "path": current_path,
                "text": text,
                "aggregate_wordcount": wordcount
            })

        # Always recurse
        units.extend(_build_units_fulltext(section.get("sections", []), current_path))
    return units


async def inspect_section_structure(title: str, get_sections_tool):
    sc = await get_sections_tool.ainvoke({"title": title})

    units = _build_units(sc["sections"])

    # Optional: filter out tiny / useless units
    units = [
        u for u in units
        if u["aggregate_wordcount"] >= 200
    ]

    return {
        "title": title,
        "units": units,
    }


async def get_unit_text(title: str, unit_id: str, get_sections_tool):
    sc = await get_sections_tool.ainvoke({"title": title})

    units = _build_units_fulltext(sc["sections"])

    # Optional: filter out tiny / useless units
    units = [
        u for u in units
        if u["aggregate_wordcount"] >= 200
    ]

    #Find unit with right unit_id
    try:
        unit = [unit for unit in units if unit["id"]==unit_id][0]
        text = unit["text"]
    except IndexError:
        print("Cannot find unit with id "+unit_id)
        text = "Unit not found with id"+str(unit_id)
    return text

'''
Structured Responses
'''


class SearchResult(BaseModel):
    title: str


class SearchResultList(BaseModel):
    results: List[SearchResult]

class SectionResult(BaseModel):
    unit_id: str
    reason: str

class ShortAnswer(BaseModel):
    answer: Literal["True", "False", "Unknown"]
    summary: str
'''
Agent Functions
'''
@traceable(name="search_wikipedia_articles")
async def get_wikipedia_articles(query, search_tool):
    #Get potential articles
    system_prompt=WIKIPEDIA_SEARCH_TEMPLATE

    agent = create_agent(
        model="openai:gpt-4.1-nano",
        tools=[search_tool],
        system_prompt=system_prompt,
        response_format=SearchResultList
    )

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )
    articles = result["structured_response"].results
    return articles


@traceable(name="select wikipedia section")
async def select_wikipedia_sections(query, units, title):
    #select one unit of a wikipedia article based on query and units metadata
    parser = PydanticOutputParser(pydantic_object=SectionResult)
    llm = ChatOpenAI(name="openai:gpt-4.1-nano")

    messages = [
        SystemMessage(content=WIKIPEDIA_SELECTION_TEMPLATE),
        HumanMessage(content=(
            f"Claim: {query}\n"
            f"Units: {json.dumps(units, indent=2)}\n"
            f"Article title: {title}\n\n"
        ))
    ]

    output = await llm.ainvoke(messages)
    selection = parser.parse(output.content)
    return selection

@traceable(name="verify claim with section text")
async def verify_claim(query, full_text):
    parser = PydanticOutputParser(pydantic_object=ShortAnswer)
    llm = ChatOpenAI(name="openai:gpt-4.1-nano")

    messages = [SystemMessage(content=WIKIPEDIA_VERIFICATION_TEMPLATE),
                HumanMessage(content=(
                    f"Claim: {query}\n"
                    f"text: {full_text}"
                ))]

    output = await llm.ainvoke(messages)
    answer = parser.parse(output.content)
    return answer
    



@traceable(name="search_wikipedia")
async def search_wikipedia(query):
    load_dotenv()
    try:
        mcp = create_wikipedia_server()

        client = Client(mcp)
        async with client:

            #Convert FastMCP tools to Langchain tools
            tools = await client.list_tools()
            tools = await load_langchain_tools(client, tools)

            #Filter tools
            search_tool = [tool for tool in tools if tool.name=="search_wikipedia"][0]
            get_sections_tool = [tool for tool in tools if tool.name=="get_sections" ][0]

            #1.) GET POTENTIAL ARTICLES
            articles = await get_wikipedia_articles(query, search_tool)
            
            #2.) GO THROUGH ARTICLES
            answer = "Unknown"
            summary = "No relevant information found."
            source = None
            while answer=="Unknown" and articles:
                article = articles.pop(0)
                #Get section structure
                unit_structure = await inspect_section_structure(article.title, get_sections_tool)

                #Select and read most relevant section unit
                section_decision = await select_wikipedia_sections(query,  unit_structure["units"], unit_structure["title"])

                if section_decision.unit_id != "None":
                    #Get full section text
                    full_text = await get_unit_text(article.title, section_decision.unit_id, get_sections_tool)

                    #Verify information based on full text
                    verification = await verify_claim(query, full_text)

                    #Update results
                    answer = verification.answer
                    if answer != "Unknown":
                        summary = verification.summary
                        source = article.title

            #3.) Construct final answer
            if source:
                link = ["https://en.wikipedia.org/wiki/"+source.replace(" ", "_")]
            else:
                link = []
            return Answer(answer=answer, summary=summary, links=link)

    except ValueError as e:
        # Handle misconfiguration errors
        print(f"Error: {e}")
        return Answer(answer="Unknown", summary="Internal errors", links=[])





