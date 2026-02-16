This repo contains a factchecker utilizing wikipedia and trusted news articles to verify claims, wrapped within a RestAPI (FastAPI) and deployed on AWS Lambda via terraform. 
It returns a classification (True, False, Unknown), an explanation of the classification as well as links to the sources used. 

The main functionality can be found in backend/app/factchecker.


