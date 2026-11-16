from fastapi import FastAPI
from app.routers import menu

app = FastAPI(
    title="Trio Saung Nusantara Web Based Ordering Menu System",
    version="1.0.0"
)

app.include_router(menu.router)

@app.get("/")
def home():
    return {
        "message": "Backend is running"
    }