from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from factchecker.check_claims import check_claim
from factchecker.helper import Answer


def create_app() -> FastAPI:
    load_dotenv()
    app = FastAPI()

    origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_headers=["*"],
        allow_methods=["*"],
    )

    @app.get("/")
    async def root():
        return {"message": "Factchecker API"}

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    @app.get("/verify", response_model=Answer)
    async def verify(claim: str):
        try:
            answer = await check_claim(claim)
            return answer
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error in Verification endpoint: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app
if __name__ == "__main__":
    import uvicorn
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)

