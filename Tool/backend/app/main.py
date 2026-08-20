import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, SessionLocal
from .routers import catalogs, assessments, evidence, export, settings, profiles
from .seed import seed_if_empty

app = FastAPI(
    title="OSCAL Compliance Suite — NIS2 Audit Backend",
    description="OSCAL Parser Engine, Assessment Engine und Export Engine fuer NIS2-Audits.",
    version="1.0.0",
)

origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalogs.router)
app.include_router(assessments.router)
app.include_router(evidence.router)
app.include_router(export.router)
app.include_router(settings.router)
app.include_router(profiles.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    if os.getenv("SEED_DEMO_DATA", "false").lower() == "true":
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}
