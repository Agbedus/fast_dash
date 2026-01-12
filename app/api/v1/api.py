from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, health, users, user_admin, admin_db,
    clients, projects, tasks, notes, events, decisions
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(user_admin.router, prefix="/user-admin", tags=["admin"])
api_router.include_router(admin_db.router, prefix="/admin-db", tags=["admin-db"])

# Resource endpoints
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
