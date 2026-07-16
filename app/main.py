from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.internal import admin
from app.routers import tasks, users
from app import worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker.start()
    try:
        yield
    finally:
        worker.stop()


app = FastAPI(lifespan=lifespan)

app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(
    admin.router,
    responses={418: {"description": "I'm a teapot"}},
)


@app.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}


@app.get("/health")
async def health():
    return {"status": "ok"}
