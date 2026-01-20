from factchecker.helper import classify_and_score, Answer
from factchecker.wikipedia_search import search_wikipedia
from factchecker.news_search import run_news_agent
from langsmith import traceable


async def run_agent_by_source(source, query):
    assert source in ["Wikipedia", "News"]
    if source=="Wikipedia":
        result = await search_wikipedia(query)
    elif source=="News":
        result = await run_news_agent(query)
    return result

@traceable(name="factchecker")
async def factchecker(query):
    #1.) Classify if it can actually be checked
    response = await classify_and_score(query)

    #If guardrails detected potential prompt injection
    if response=="Inappropriate":
        return Answer(answer="Unknown", summary="Claims containing inappropriate content cannot be processed. Please rephrase your claim.", links=[])
    #If claim is not factual it cannot be verified
    query_classification = response.classification
    if query_classification != "Factual":
        #Cannot be checked
        return Answer(answer="Unknown", summary="Cannot be validated because claim is "+query_classification.lower(), links=[])
    
    #2.) Determine which sources to check (Wikipedia, News)
    threshold = 0.8
    wp = response.wikipedia_prob+0.05 #To make sure wikipedia is checked first if both are 1.0
    np = response.news_prob
    if (wp > threshold) and (np > threshold):
        if wp > np:
            check_order = ["Wikipedia", "News"]
        else:
            check_order = ["News", "Wikipedia"]
    elif (wp > threshold):
        check_order = ["Wikipedia"]
    elif (np > threshold):
        check_order = ["News"]
    else:
        check_order = []

    #3.) Check sources in order
    while check_order:
        source = check_order.pop(0)
        result = await run_agent_by_source(source, query)
        if result.answer != "Unknown":
            return result
    
    #4.) Return Unknown result
    return Answer(answer="Unknown", summary="Could not find relevant information", links=[])
