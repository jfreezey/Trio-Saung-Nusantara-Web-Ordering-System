import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import config
from app.core.database import pool
from app.routers import auth, cashier, category, customer, menu, report, table

logger = logging.getLogger("trio_saung")


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open(wait=True, timeout=15)  # gagal cepat kalau .env / database salah
    yield
    pool.close()


app = FastAPI(
    title="Trio Saung Nusantara Web Based Ordering Menu System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,  # jangan pakai "*"
    allow_credentials=False,  # token dikirim lewat header, bukan cookie
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Customer-Token"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# Format error message

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Sengaja TIDAK mengembalikan "input" dari Pydantic: bisa berisi password.
    errors = [
        {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": "Data yang dikirim tidak valid.", "errors": errors},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Detail error hanya di log server, tidak dikirim ke client.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"success": False, "message": "Terjadi kesalahan pada server."},
    )


# Routers & file statis 

config.MENU_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

app.include_router(auth.router)
app.include_router(category.router)
app.include_router(menu.router)
app.include_router(table.router)
app.include_router(customer.router)
app.include_router(cashier.router)
app.include_router(report.router)


@app.get("/", tags=["Health"])
def home():
    return {"success": True, "message": "Backend is running"}
