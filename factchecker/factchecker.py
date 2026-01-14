from factchecker.helper import run_news_agent, run_wikipedia_agent, classify_and_score, Answer

async def run_agent_by_source(source, query):
    assert source in ["Wikipedia", "News"]
    if source=="Wikipedia":
        result = await run_wikipedia_agent(query)
    elif source=="News":
        result = await run_news_agent(query)
    return result

async def factchecker(query):
    #1.) Classify if it can actually be checked
    response = await classify_and_score(query)

    query_classification = response.classification
    if query_classification != "Factual":
        #Cannot be checked
        return Answer(answer="Unknown", summary="Cannot be validated because claim is "+query_classification.lower(), links=[])
    
    print("classification: "+str(response))
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
