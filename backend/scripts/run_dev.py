import uvicorn


#Run from app/api
uvicorn.run(
    "api.main:create_app",
    factory=True
)