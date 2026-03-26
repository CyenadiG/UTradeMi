from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import create_indexes
from app.routes import auth, users, posts, reviews, uploads, Messages


app = FastAPI(title="UTradeMi API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/api/auth",     tags=["auth"])
app.include_router(users.router,    prefix="/api/users",    tags=["users"])
app.include_router(posts.router,    prefix="/api/posts",    tags=["posts"])
app.include_router(reviews.router,  prefix="/api/reviews",  tags=["reviews"])
app.include_router(uploads.router,  prefix="/api/uploads",  tags=["uploads"])
app.include_router(Messages.router, prefix="/api/messages", tags=["messages"])


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}