import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import engine, Base
from app.scripts.seed_data import seed_database
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.personnel import router as personnel_router
from app.api.v1.endpoints.welfare import router as welfare_router
from app.api.v1.endpoints.commander import router as commander_router
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.demo import router as demo_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Prismarine: Production-Grade Zero-Trust Defense Personnel Stress & Welfare Monitoring Platform. "
        "Formed under sustained operational pressure, structurally layered, and defined by clarity rather than opacity. "
        "Engineered with Column-Level AES-256-GCM Encryption, Rotating Pseudonyms, "
        "k-Anonymity (k>=5), Game-Theoretic Alert Ranking with Crisis Hard-Override, "
        "and Access-Pattern Intrusion Detection backed by an HMAC-SHA256 Audit Trail."
    ),
    version=settings.VERSION,
    lifespan=lifespan
)

# Explicit CORS configuration (No invalid wildcard origins with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Core API routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(personnel_router, prefix=settings.API_V1_STR)
app.include_router(welfare_router, prefix=settings.API_V1_STR)
app.include_router(commander_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)

# Demo Router: ONLY mounted when DEMO_MODE is explicitly enabled
if settings.DEMO_MODE:
    app.include_router(demo_router, prefix=settings.API_V1_STR)

# Serve Frontend Static Directory & PWA
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "system": settings.APP_NAME,
        "code": settings.APP_CODE,
        "version": settings.VERSION,
        "demo_mode": settings.DEMO_MODE,
        "encryption": "AES-256-GCM-AUTHENTICATED",
        "privacy_k_anonymity": settings.K_ANONYMITY_THRESHOLD,
        "dp_epsilon": settings.DP_EPSILON,
        "dp_budget_limit_per_day": settings.DP_MAX_BUDGET_PER_DAY,
        "audit_chain": "HMAC-SHA256-EXTERNAL-KEY-WORM-ANCHORED"
    }
