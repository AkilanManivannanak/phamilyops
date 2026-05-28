"""
PhamilyOps — FastAPI Backend
AI-Native HR & Operations Platform for Phamily (Jaan Health)

Built by: Akilan Manivannan & Akila Lourdes Miriyala Francis
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from config import settings
from routers import screener, copilot, audit, automations, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: warm up ML models so first request is fast."""
    print("PhamilyOps backend starting...")
    try:
        from services.nlp_service import _get_ner_pipeline
        from services.vector_service import _get_model
        _get_ner_pipeline()
        _get_model()
        print("ML models loaded and ready.")
    except Exception as e:
        print(f"Model warm-up warning: {e}")
    yield
    print("PhamilyOps backend shutting down.")


app = FastAPI(
    title="PhamilyOps API",
    description="AI-Native HR & Operations Platform for Phamily",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS — allow the frontend (Vercel) and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "*",  # tighten this in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers
app.include_router(screener.router)
app.include_router(copilot.router)
app.include_router(audit.router)
app.include_router(automations.router)
app.include_router(analytics.router)


@app.get("/")
async def root():
    return {
        "service": "PhamilyOps API",
        "version": "1.0.0",
        "status": "operational",
        "built_by": "Akilan Manivannan & Akila Lourdes Miriyala Francis",
        "modules": ["screener", "copilot", "audit", "automations", "analytics"],
    }


@app.get("/health")
async def health():
    """Railway health check endpoint."""
    from database.supabase_client import get_supabase
    try:
        db = get_supabase()
        db.table("analytics_snapshots").select("id").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"
    return {
        "status": "healthy",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "detail": "Internal server error"}
    )
