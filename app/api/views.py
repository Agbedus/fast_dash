from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy import inspect, text, func, desc
from typing import Optional, List
from app.core.config import settings
from app.db.session import engine, get_db
from sqlmodel import Session, select
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.task import Task, TaskAssignee, TaskStatus, TaskTimeLog
from app.models.client import Client
from app.models.note import Note, NoteShare
from app.models.event import Event
from app.core.security import get_password_hash
from app.api.deps import get_current_user
from app.services.user_service import UserService
from app.services.notifications import NotificationService

router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

def get_tables():
    inspector = inspect(engine)
    return inspector.get_table_names()

def get_current_user_from_cookie(request: Request, db: Session) -> Optional[User]:
    """
    Wrapper around deps.get_current_user that returns None instead of raising
    exceptions. Used for template routes that need soft redirects to login.
    """
    try:
        return get_current_user(request, db, token=None)
    except HTTPException:
        return None

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
        
    UserService.safe_delete_user(db, target_user)
    return {"status": "success"}

@router.get("/", include_in_schema=False)
def root(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    # Dashboard Stats
    stats = {
        "users": db.exec(select(func.count(User.id))).one(),
        "projects": db.exec(select(func.count(Project.id))).one(),
        "tasks": db.exec(select(func.count(Task.id))).one(),
        "active_projects": db.exec(
            select(Project)
            .where(Project.status == "in_progress")
            .limit(3)
        ).all()
    }
    
    # Recent Activity (Last 5 tasks)
    recent_tasks = db.exec(
        select(Task)
        .order_by(desc(Task.created_at))
        .limit(5)
    ).all()

    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "current_user": user, 
            "version": settings.VERSION, 
            "tables": get_tables(),
            "stats": stats,
            "recent_tasks": recent_tasks
        }
    )

@router.get("/database", include_in_schema=False)
def database_explorer(
    request: Request, 
    table_name: Optional[str] = None, 
    q: Optional[str] = None, 
    page: int = 1,
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    # Check permissions
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.MANAGER not in user.roles:
        raise HTTPException(status_code=403, detail="Not authorized to view database explorer")

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    current_table = table_name
    columns = []
    rows = []
    pk_column = "id" # default guess
    db_summary = {}
    
    pagination = {
        "page": page,
        "total_records": 0,
        "total_pages": 0,
        "page_size": 50,
        "has_next": False,
        "has_prev": page > 1
    }
    
    if not current_table:
        # Fetch stats for all tables
        with engine.connect() as connection:
            for t in tables:
                try:
                    count_query = text(f"SELECT COUNT(*) FROM `{t}`")
                    count_result = connection.execute(count_query).scalar()
                    db_summary[t] = count_result
                except Exception as e:
                    db_summary[t] = "Error"
    
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
            
            # Filter rows based on search query
            if q:
                filtered_rows = [
                    row for row in all_rows 
                    if any(str(val).lower().find(q.lower()) != -1 for val in row.values())
                ]
            else:
                filtered_rows = all_rows

            # Apply pagination after search filtering
            pagination["total_records"] = len(filtered_rows)
            pagination["total_pages"] = (pagination["total_records"] + 49) // 50
            pagination["has_next"] = page < pagination["total_pages"]
            
            start_idx = (page - 1) * 50
            end_idx = start_idx + 50
            rows = filtered_rows[start_idx:end_idx]

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
            "status": [s.value for s in TaskStatus],
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
            "pagination": pagination,
            "fk_data": fk_data,
            "field_options": field_options.get(current_table, {}),
            "multi_select_fields": multi_select_fields.get(current_table, {}),
            "db_summary": db_summary
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

    # Get client if exists
    client = None
    if project.client_id:
        client = db.get(Client, project.client_id)

    return templates.TemplateResponse(
        "project_detail.html", 
        {
            "request": request, 
            "current_user": user,
            "project": project,
            "client": client,
            "tables": get_tables()
        }
    )

@router.get("/projects/{project_id}/edit", include_in_schema=False)
def project_edit_page(request: Request, project_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Check permissions (admins or owner)
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.MANAGER not in user.roles and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this project")
        
    clients = db.exec(select(Client)).all()
    users = db.exec(select(User)).all()
    
    return templates.TemplateResponse(
        "project_edit.html",
        {
            "request": request,
            "current_user": user,
            "project": project,
            "clients": clients,
            "users": users,
            "tables": get_tables()
        }
    )

@router.post("/projects/{project_id}/edit", include_in_schema=False)
async def project_edit_submit(
    request: Request, 
    project_id: int,
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.MANAGER not in user.roles and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this project")
    
    form = await request.form()
    
    # Update fields
    project.name = form.get("name")
    project.key = form.get("key") or None
    project.description = form.get("description")
    project.status = form.get("status")
    project.priority = form.get("priority")
    project.client_id = form.get("client_id") or None
    project.owner_id = form.get("owner_id") or None
    project.start_date = form.get("start_date") or None
    project.end_date = form.get("end_date") or None
    project.budget = int(float(form.get("budget") or 0)) if form.get("budget") else None
    project.currency = form.get("currency")
    project.billing_type = form.get("billing_type")
    project.is_archived = 1 if form.get("is_archived") == "on" else 0
    project.tags = form.get("tags")
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Notify Super Admins and Managers
    await NotificationService.notify_managers(
        db, 
        title="Project Updated", 
        message=f"Project '{project.name}' was updated by {user.full_name or user.email}",
        sender_id=user.id,
        resource_type="project",
        resource_id=project.id
    )
    
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@router.post("/projects/{project_id}/delete", include_in_schema=False)
def project_delete(request: Request, project_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.MANAGER not in user.roles and project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this project")
        
    db.delete(project)
    db.commit()
    
    return RedirectResponse(url="/database?table_name=projects", status_code=303)

@router.get("/tasks/{task_id}", include_in_schema=False)
def task_detail_page(request: Request, task_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    project = None
    if task.project_id:
        project = db.get(Project, task.project_id)

    # Fetch assignees
    assignees_stmt = select(User).join(TaskAssignee, User.id == TaskAssignee.user_id).where(TaskAssignee.task_id == task_id)
    assignees = db.exec(assignees_stmt).all()

    # Fetch time logs
    time_logs = db.exec(select(TaskTimeLog).where(TaskTimeLog.task_id == task_id).order_by(desc(TaskTimeLog.start_time))).all()

    # Check for active timer
    active_timer = db.exec(
        select(TaskTimeLog).where(
            TaskTimeLog.task_id == task_id,
            TaskTimeLog.user_id == user.id,
            TaskTimeLog.end_time == None
        )
    ).first()

    return templates.TemplateResponse(
        "task_detail.html", 
        {
            "request": request, 
            "current_user": user,
            "task": task,
            "project": project,
            "assignees": assignees,
            "time_logs": time_logs,
            "active_timer": active_timer,
            "tables": get_tables()
        }
    )

@router.get("/tasks/{task_id}/edit", include_in_schema=False)
def task_edit_page(request: Request, task_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    projects = db.exec(select(Project)).all()
    users = db.exec(select(User)).all()
    
    # Get current assignee IDs
    assignee_ids = [ta.user_id for ta in task.task_assignees]

    # Fetch potential dependencies (tasks in same project or all tasks)
    stmt = select(Task).where(Task.id != task_id)
    if task.project_id:
        stmt = stmt.where(Task.project_id == task.project_id)
    dependencies = db.exec(stmt).all()
    
    return templates.TemplateResponse(
        "task_edit.html",
        {
            "request": request,
            "current_user": user,
            "task": task,
            "projects": projects,
            "users": users,
            "current_assignee_ids": assignee_ids,
            "dependencies": dependencies,
            "statuses": [s.value for s in TaskStatus],
            "tables": get_tables()
        }
    )

@router.post("/tasks/{task_id}/edit", include_in_schema=False)
async def task_edit_submit(
    request: Request, 
    task_id: int,
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    form = await request.form()
    
    # Update fields
    task.name = form.get("name")
    task.description = form.get("description")
    task.status = form.get("status")
    task.priority = form.get("priority")
    task.due_date = form.get("due_date") or None
    
    project_id_val = form.get("project_id")
    task.project_id = int(project_id_val) if project_id_val else None

    # New fields
    task.qa_required = form.get("qa_required") == "on"
    task.review_required = form.get("review_required") == "on"
    
    depends_on_val = form.get("depends_on_id")
    task.depends_on_id = int(depends_on_val) if depends_on_val and depends_on_val != "None" else None
    
    # Update assignments
    # First remove existing
    existing_links = db.exec(select(TaskAssignee).where(TaskAssignee.task_id == task_id)).all()
    for link in existing_links:
        db.delete(link)
        
    # Add new
    assignee_ids = form.getlist("assignees")
    for uid in assignee_ids:
        new_link = TaskAssignee(task_id=task_id, user_id=uid)
        db.add(new_link)
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Notify Super Admins and Managers
    await NotificationService.notify_managers(
        db, 
        title="Task Updated", 
        message=f"Task '{task.name}' was updated by {user.full_name or user.email}",
        sender_id=user.id,
        resource_type="task",
        resource_id=task.id
    )
    
    # Notify New Assignees
    if assignee_ids:
        for user_id in assignee_ids:
            await NotificationService.send_notification(
                db, 
                recipient_id=user_id,
                title="Task Assignment Updated",
                message=f"You are assigned to task: '{task.name}'",
                type="info",
                sender_id=user.id,
                resource_type="task",
                resource_id=task.id
            )

    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

@router.post("/tasks/{task_id}/delete", include_in_schema=False)
def task_delete(request: Request, task_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Also delete assignees associations
    links = db.exec(select(TaskAssignee).where(TaskAssignee.task_id == task_id)).all()
    for link in links:
        db.delete(link)
        
    db.delete(task)
    db.commit()
    
    return RedirectResponse(url="/database?table_name=tasks", status_code=303)

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

@router.get("/clients/{client_id}/edit", include_in_schema=False)
def client_edit_page(request: Request, client_id: str, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    # Check permissions (admins only)
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.MANAGER not in user.roles:
        raise HTTPException(status_code=403, detail="Not authorized to edit clients")
    
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    return templates.TemplateResponse(
        "client_edit.html",
        {
            "request": request,
            "current_user": user,
            "client": client,
            "tables": get_tables()
        }
    )

@router.post("/clients/{client_id}/edit", include_in_schema=False)
async def client_edit_submit(
    request: Request, 
    client_id: str,
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.MANAGER not in user.roles:
        raise HTTPException(status_code=403, detail="Not authorized to edit clients")
    
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    form = await request.form()
    
    # Update fields
    client.company_name = form.get("company_name")
    client.contact_person_name = form.get("contact_person_name") or None
    client.contact_email = form.get("contact_email") or None
    client.website_url = form.get("website_url") or None
    
    db.add(client)
    db.commit()
    db.refresh(client)
    
    return RedirectResponse(url=f"/clients/{client_id}", status_code=303)

@router.post("/clients/{client_id}/delete", include_in_schema=False)
def client_delete(request: Request, client_id: str, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.MANAGER not in user.roles:
        raise HTTPException(status_code=403, detail="Not authorized to delete clients")
    
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
        
    db.delete(client)
    db.commit()
    
    return RedirectResponse(url="/database?table_name=clients", status_code=303)

@router.get("/events/{event_id}", include_in_schema=False)
def event_detail_page(request: Request, event_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Parse reminders for display
    import json
    reminders_list = []
    if event.reminders:
        try:
            reminders_list = json.loads(event.reminders)
        except:
            pass

    return templates.TemplateResponse(
        "event_detail.html", 
        {
            "request": request, 
            "current_user": user,
            "event": event,
            "reminders_list": reminders_list,
            "tables": get_tables()
        }
    )

@router.get("/events/{event_id}/edit", include_in_schema=False)
def event_edit_page(request: Request, event_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    return templates.TemplateResponse(
        "event_edit.html",
        {
            "request": request,
            "current_user": user,
            "event": event,
            "tables": get_tables()
        }
    )

@router.post("/events/{event_id}/edit", include_in_schema=False)
async def event_edit_submit(
    request: Request, 
    event_id: int,
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    form = await request.form()
    
    # Update fields
    event.title = form.get("title")
    event.description = form.get("description")
    event.start = form.get("start")
    event.end = form.get("end")
    event.location = form.get("location")
    event.status = form.get("status")
    event.privacy = form.get("privacy")
    event.recurrence = form.get("recurrence")
    event.color = form.get("color")
    event.all_day = 1 if form.get("all_day") == "on" else 0
    event.reminders = form.get("reminders") or None
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Notify Super Admins and Managers
    await NotificationService.notify_managers(
        db, 
        title="Event Updated", 
        message=f"Event '{event.title}' was updated by {user.full_name or user.email}",
        sender_id=user.id,
        resource_type="event",
        resource_id=event.id
    )

    return RedirectResponse(url=f"/events/{event_id}", status_code=303)

@router.post("/events/{event_id}/delete", include_in_schema=False)
def event_delete(request: Request, event_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
        
    db.delete(event)
    db.commit()
    
    return RedirectResponse(url="/database?table_name=events", status_code=303)

@router.get("/notes/{note_id}", include_in_schema=False)
def note_detail_page(request: Request, note_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Fetch shared users
    shared_users_stmt = select(User).join(NoteShare, User.id == NoteShare.user_id).where(NoteShare.note_id == note_id)
    shared_users = db.exec(shared_users_stmt).all()

    return templates.TemplateResponse(
        "note_detail.html", 
        {
            "request": request, 
            "current_user": user,
            "note": note,
            "shared_users": shared_users,
            "tables": get_tables()
        }
    )

@router.get("/notes/{note_id}/edit", include_in_schema=False)
def note_edit_page(request: Request, note_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    # Check permissions (owner only for now, maybe shared users can edit too? Let's restrict to owner or admin)
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.MANAGER not in user.roles and note.user_id != user.id:
         raise HTTPException(status_code=403, detail="Not authorized to edit this note")

    users = db.exec(select(User)).all()
    
    # Get current shared user IDs
    # Access relationship via note.shared_with or query NoteShare
    # Note model has shared_with relationship
    shared_user_ids = [u.id for u in note.shared_with]

    return templates.TemplateResponse(
        "note_edit.html",
        {
            "request": request,
            "current_user": user,
            "note": note,
            "users": users,
            "current_shared_user_ids": shared_user_ids,
            "tables": get_tables()
        }
    )

@router.post("/notes/{note_id}/edit", include_in_schema=False)
async def note_edit_submit(
    request: Request, 
    note_id: int,
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
        
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.MANAGER not in user.roles and note.user_id != user.id:
         raise HTTPException(status_code=403, detail="Not authorized to edit this note")
    
    form = await request.form()
    
    # Update fields
    note.title = form.get("title")
    note.content = form.get("content")
    note.type = form.get("type")
    note.tags = form.get("tags")
    note.is_pinned = 1 if form.get("is_pinned") == "on" else 0
    note.is_archived = 1 if form.get("is_archived") == "on" else 0
    note.is_favorite = 1 if form.get("is_favorite") == "on" else 0
    
    # Update sharing
    # First remove existing
    existing_shares = db.exec(select(NoteShare).where(NoteShare.note_id == note_id)).all()
    for share in existing_shares:
        db.delete(share)
        
    # Add new
    shared_ids = form.getlist("shared_with")
    for uid in shared_ids:
        new_share = NoteShare(note_id=note_id, user_id=uid)
        db.add(new_share)
    
    db.add(note)
    db.commit()
    db.refresh(note)
    
    # Notify Super Admins and Managers
    await NotificationService.notify_managers(
        db, 
        title="Note Updated", 
        message=f"Note '{note.title}' was updated by {user.full_name or user.email}",
        sender_id=user.id,
        resource_type="note",
        resource_id=note.id
    )
    
    # Notify New Shared Users
    if shared_ids:
        for user_id in shared_ids:
            await NotificationService.send_notification(
                db, 
                recipient_id=user_id,
                title="Note Sharing Updated",
                message=f"You now have access to note: '{note.title}'",
                type="info",
                sender_id=user.id,
                resource_type="note",
                resource_id=note.id
            )

    return RedirectResponse(url=f"/notes/{note_id}", status_code=303)

@router.post("/notes/{note_id}/delete", include_in_schema=False)
def note_delete(request: Request, note_id: int, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login")
    
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if UserRole.SUPER_ADMIN not in user.roles and UserRole.MANAGER not in user.roles and note.user_id != user.id:
         raise HTTPException(status_code=403, detail="Not authorized to delete this note")
        
    # Also delete shares
    shares = db.exec(select(NoteShare).where(NoteShare.note_id == note_id)).all()
    for share in shares:
        db.delete(share)
        
    db.delete(note)
    db.commit()
    
    return RedirectResponse(url="/database?table_name=notes", status_code=303)
