"""
PM Insights — FastAPI entry point
Sprint 1 skeleton: routes are wired but services are stubbed.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="PM Insights API",
    version="1.0.0",
    description="Turns app store reviews into PM artifacts.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


# TODO Sprint 1: mount routers here once built
# from api.v1.routes import apps, runs, artifacts
# app.include_router(apps.router, prefix="/api/v1")
# app.include_router(runs.router, prefix="/api/v1")
# app.include_router(artifacts.router, prefix="/api/v1")
