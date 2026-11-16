from fastapi import FastAPI
from app.routers import menu
from app.routers import category
from app.routers import auth

app = FastAPI(
    title="Trio Saung Nusantara Web Based Ordering Menu System",
    version="1.0.0"
)

app.include_router(menu.router)
app.include_router(category.router)
app.include_router(auth.router)

@app.get("/")
def home():
    return {
        "message": "Backend is running"
    }