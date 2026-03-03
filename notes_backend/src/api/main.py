from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.config import get_settings
from src.api.routers.auth import router as auth_router
from src.api.routers.notes import router as notes_router
from src.api.routers.tags import router as tags_router

settings = get_settings()

openapi_tags = [
    {"name": "auth", "description": "User registration, login, and profile."},
    {"name": "notes", "description": "User-scoped notes CRUD and search."},
    {"name": "tags", "description": "User-scoped tag CRUD."},
]

app = FastAPI(
    title=settings.app_name,
    description="REST API for a private notes app (JWT auth, notes/tags CRUD, search).",
    version=settings.app_version,
    openapi_tags=openapi_tags,
)

# CORS for Next.js frontend. If you need additional origins, set CORS_ORIGINS env var (comma-separated).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tags_router)
app.include_router(notes_router)


@app.get("/", tags=["health"], summary="Health check", operation_id="health_check")
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}
