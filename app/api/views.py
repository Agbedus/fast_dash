from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy import inspect, text
from typing import Optional, List
from app.core.config import settings
from app.db.session import engine, get_db
from sqlmodel import Session, select
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.task import Task
from app.models.client import Client
from app.models.note import Note
from app.models.event import Event
from jose import jwt, JWTError
from app.schemas.auth import TokenData
from app.core.security import get_password_hash

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

def get_tables():
    inspector = inspect(engine)
    return inspector.get_table_names()

def get_current_user_from_cookie(request: Request, db: Session) -> Optional[User]:
    token = request.cookies.get("access_token")
    if not token or not token.startswith("Bearer "):
        return None
    token = token.replace("Bearer ", "")
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        email = payload.get("sub")
        if email is None:
            return None
    except (JWTError):
        return None
    
    user = db.exec(select(User).where(User.email == email)).first()
    return user

@router.get("/login", include_in_schema=False)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register", include_in_schema=False)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/create-user", include_in_schema=False)
def create_user_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "create_user.html", 
        {
            "request": request, 
            "current_user": user,
            "roles": [role.value for role in UserRole],
            "tables": get_tables()
        }
    )

@router.get("/users/{user_id}", include_in_schema=False)
def user_detail_page(request: Request, user_id: str, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return templates.TemplateResponse(
        "user_detail.html", 
        {
            "request": request, 
            "current_user": user,
            "user": target_user,
            "all_roles": [role.value for role in UserRole],
            "tables": get_tables()
        }
    )

@router.delete("/users/{user_id}", include_in_schema=False)
def delete_user_route(user_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if UserRole.SUPER_ADMIN not in user.roles:
        raise HTTPException(status_code=403, detail="Only super admins can delete users")
        
    target_user = db.get(User, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if target_user.id == user.id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")
        
    db.delete(target_user)
    db.commit()
    return {"status": "success"}

@router.get("/", include_in_schema=False)
def root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "current_user": user, "version": settings.VERSION, "tables": get_tables()}
    )

@router.get("/database", include_in_schema=False)
def database_explorer(request: Request, table_name: Optional[str] = None, q: Optional[str] = None, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    # Check permissions
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.ADMIN not in user.roles:
        # If not admin, maybe just reject or show empty? 
        # For now, let's redirect to home with a query param or something, or just raise 403
        raise HTTPException(status_code=403, detail="Not authorized to view database explorer")

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    current_table = table_name
    columns = []
    rows = []
    pk_column = "id" # default guess
    
    if current_table:
        cols_info = inspector.get_columns(current_table)
        columns = [col["name"] for col in cols_info]
        
        # Try to find PK
        pk_info = inspector.get_pk_constraint(current_table)
        if pk_info and pk_info['constrained_columns']:
            pk_column = pk_info['constrained_columns'][0]
        
        with engine.connect() as connection:
            query = text(f"SELECT * FROM `{current_table}`")
            result = connection.execute(query)
            
            all_rows = [dict(zip(columns, row)) for row in result.fetchall()]
            
            # Special handling for tasks - fetch assignees
            if current_table == "tasks":
                for row in all_rows:
                    task_id = row.get('id')
                    if task_id:
                        # Query task assignees
                        assignee_query = text("""
                            SELECT u.full_name, u.email 
                            FROM task_assignees ta
                            JOIN users u ON ta.user_id = u.id
                            WHERE ta.task_id = :task_id
                        """)
                        assignee_result = connection.execute(assignee_query, {"task_id": task_id})
                        assignees = [r[0] or r[1] for r in assignee_result.fetchall()]
                        row['assignees'] = ', '.join(assignees) if assignees else 'None'
                
                # Add assignees to columns if not already there
                if 'assignees' not in columns:
                    columns.append('assignees')
            
            # Special handling for notes - fetch shared_with users
            if current_table == "notes":
                for row in all_rows:
                    note_id = row.get('id')
                    if note_id:
                        # Query shared users
                        share_query = text("""
                            SELECT u.full_name, u.email 
                            FROM note_shares ns
                            JOIN users u ON ns.user_id = u.id
                            WHERE ns.note_id = :note_id
                        """)
                        share_result = connection.execute(share_query, {"note_id": note_id})
                        shared_users = [r[0] or r[1] for r in share_result.fetchall()]
                        row['shared_with'] = ', '.join(shared_users) if shared_users else 'None'
                
                # Add shared_with to columns if not already there
                if 'shared_with' not in columns:
                    columns.append('shared_with')

            # Special handling for events - fetch creator info
            if current_table == "events":
                for row in all_rows:
                    u_id = row.get('user_id')
                    if u_id:
                        user_obj = db.get(User, u_id)
                        if user_obj:
                            row['creator'] = user_obj.full_name or user_obj.email
                        else:
                            row['creator'] = 'Deleted User'
                    else:
                        row['creator'] = 'System'
                
                # Add creator to columns if not already there
                if 'creator' not in columns:
                    columns.append('creator')
            
            if q:
                rows = [
                    row for row in all_rows 
                    if any(str(val).lower().find(q.lower()) != -1 for val in row.values())
                ]
            else:
                rows = all_rows

    # Fetch simple lists for dropdowns (id, display_name)
    # We catch errors just in case tables don't exist yet to avoid 500s during setup
    fk_data = {
        "users": [],
        "clients": [],
        "projects": [],
        "tasks": []
    }
    
    try:
        fk_data["users"] = [{"id": u.id, "name": f"{u.full_name} ({u.email})"} for u in db.exec(select(User)).all()]
    except Exception as e:
        print(f"Error fetching users: {e}")
    
    try:
        fk_data["clients"] = [{"id": c.id, "name": c.company_name} for c in db.exec(select(Client)).all()]
    except Exception as e:
        print(f"Error fetching clients: {e}")
    
    try:
        fk_data["projects"] = [{"id": p.id, "name": p.name} for p in db.exec(select(Project)).all()]
    except Exception as e:
        print(f"Error fetching projects: {e}")
    
    try:
        fk_data["tasks"] = [{"id": t.id, "name": t.name} for t in db.exec(select(Task)).all()]
    except Exception as e:
        print(f"Error fetching tasks: {e}")

    # Define field options for specific columns
    field_options = {
        "projects": {
            "status": ["planning", "in_progress", "completed", "on_hold"],
            "priority": ["low", "medium", "high"],
            "currency": ["USD", "EUR", "GBP", "CAD", "AUD", "GHS"],
            "billing_type": ["non_billable", "hourly", "fixed_cost"]
        },
        "tasks": {
            "status": ["task", "in_progress", "completed", "waiting"],
            "priority": ["low", "medium", "high"]
        },
        "events": {
             "status": ["tentative", "confirmed", "cancelled"],
             "privacy": ["public", "private", "confidential"],
             "recurrence": ["none", "daily", "weekly", "monthly", "yearly"]
        }
    }

    # Define many-to-many multi-select fields
    multi_select_fields = {
        "tasks": {
            "assignees": "users"  # Field name -> FK data source
        },
        "notes": {
            "shared_with": "users"
        }
    }

    return templates.TemplateResponse(
        "database.html", 
        {
            "request": request, 
            "current_user": user,
            "tables": tables,
            "current_table": current_table,
            "columns": columns,
            "pk_column": pk_column,
            "rows": rows,
            "q": q or "",
            "fk_data": fk_data,
            "field_options": field_options.get(current_table, {}),
            "multi_select_fields": multi_select_fields.get(current_table, {})
        }
    )

@router.get("/projects/{project_id}", include_in_schema=False)
def project_detail_page(request: Request, project_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return templates.TemplateResponse(
        "project_detail.html", 
        {
            "request": request, 
            "current_user": user,
            "project": project,
            "tables": get_tables()
        }
    )

@router.get("/tasks/{task_id}", include_in_schema=False)
def task_detail_page(request: Request, task_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return templates.TemplateResponse(
        "task_detail.html", 
        {
            "request": request, 
            "current_user": user,
            "task": task,
            "tables": get_tables()
        }
    )

@router.get("/clients/{client_id}", include_in_schema=False)
def client_detail_page(request: Request, client_id: str, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return templates.TemplateResponse(
        "client_detail.html", 
        {
            "request": request, 
            "current_user": user,
            "client": client,
            "tables": get_tables()
        }
    )

@router.get("/events/{event_id}", include_in_schema=False)
def event_detail_page(request: Request, event_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return templates.TemplateResponse(
        "event_detail.html", 
        {
            "request": request, 
            "current_user": user,
            "event": event,
            "tables": get_tables()
        }
    )

@router.get("/notes/{note_id}", include_in_schema=False)
def note_detail_page(request: Request, note_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return templates.TemplateResponse(
        "note_detail.html", 
        {
            "request": request, 
            "current_user": user,
            "note": note,
            "tables": get_tables()
        }
    )
