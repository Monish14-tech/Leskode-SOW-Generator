"""
ScopePilot AI — FastAPI Application Entry Point
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.database import init_db
from app.api.routes import (
    auth, projects, documents, requirements, modules,
    tasks, automations, integrations, clarifications,
    assumptions, templates, sow, validation, knowledge_base,
    admin, health
)

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ScopePilot AI backend...")
    init_db()
    logger.info("Database initialised.")
    yield
    logger.info("Shutting down ScopePilot AI backend.")


app = FastAPI(
    title="ScopePilot AI",
    description="AI-Powered SOW Generation and Zoho Implementation Planning Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    redirect_slashes=False,
)

# ─── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again or contact support."},
    )

# ─── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(requirements.router, prefix="/api/requirements", tags=["Requirements"])
app.include_router(modules.router, prefix="/api/modules", tags=["Module Mapping"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Scope Tasks"])
app.include_router(automations.router, prefix="/api/automations", tags=["Automations"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(clarifications.router, prefix="/api/clarifications", tags=["Clarifications"])
app.include_router(assumptions.router, prefix="/api/assumptions", tags=["Assumptions & Exclusions"])
app.include_router(templates.router, prefix="/api/templates", tags=["SOW Templates"])
app.include_router(sow.router, prefix="/api/sow", tags=["SOW Generation"])
app.include_router(validation.router, prefix="/api/validation", tags=["Validation"])
app.include_router(knowledge_base.router, prefix="/api/kb", tags=["Knowledge Base"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
