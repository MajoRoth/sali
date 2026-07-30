import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.api import api_router
from core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Hello from supermarket-api-backend!"}


@app.get("/ping")
def ping():
    return {"status": "ok"}


app.include_router(api_router)


def main():
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)


if __name__ == "__main__":
    main()
