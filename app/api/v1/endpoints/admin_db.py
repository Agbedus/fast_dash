from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, text
from app.api import deps
from app.db.session import get_db, engine
from app.models.user import User
from sqlalchemy import inspect

router = APIRouter()

@router.patch("/tables/{table_name}/{pk_column}/{pk_value}")
def update_generic_table_row(
    table_name: str,
    pk_column: str,
    pk_value: str,
    update_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
):
    """
    Generic endpoint to update a row in any table.
    Restricted to Super Admins.
    """
    # 1. Verify table exists
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    # 2. Verify columns exist
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    if pk_column not in columns:
        raise HTTPException(status_code=400, detail=f"Primary key column '{pk_column}' not found in '{table_name}'")
    
    for col in update_data.keys():
        if col not in columns:
            raise HTTPException(status_code=400, detail=f"Column '{col}' not found in '{table_name}'")

    # 3. Construct Update Query safely
    # Note: SQLModel/SQLAlchemy core doesn't support completely dynamic table updates cleanly without reflection
    # We will use text() but with bind parameters for values to prevent injection.
    # The column names are validated against schema above, preventing SQLi via identifiers.
    
    # Auto-update updated_at if valid column
    from datetime import datetime
    if "updated_at" in columns and "updated_at" not in update_data:
        update_data["updated_at"] = datetime.utcnow().isoformat()
    
    set_clauses = [f"`{col}` = :val_{i}" for i, col in enumerate(update_data.keys())]
    set_clause_str = ", ".join(set_clauses)
    
    query_str = f"UPDATE `{table_name}` SET {set_clause_str} WHERE `{pk_column}` = :pk_value"
    
    params = {"pk_value": pk_value}
    for i, (key, value) in enumerate(update_data.items()):
        params[f"val_{i}"] = value

    try:
        # We use the connection directly for this raw execution
        with engine.connect() as connection:
            result = connection.execute(text(query_str), params)
            connection.commit()
            
            if result.rowcount == 0:
                 raise HTTPException(status_code=404, detail="Record not found or no changes made")
                 
            return {"status": "success", "rows_affected": result.rowcount}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tables/{table_name}")
def create_generic_table_row(
    table_name: str,
    create_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_superuser),
):
    """
    Generic endpoint to create a row in any table.
    Restricted to Super Admins.
    """
    # 1. Verify table exists
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    # 2. Verify columns exist
    inspector = inspect(engine)
    valid_columns = [col["name"] for col in inspector.get_columns(table_name)]
    
    # 3. Inject Auto Fields if missing and valid
    from datetime import datetime
    import uuid
    
    # Auto-generate ID for UUID/String PKs if missing
    # (Checking if 'id' is a valid column and assuming it's a string if it's the PK and type is VARCHAR/TEXT, 
    # but simplest heuristic is just: if 'id' is missing and is a valid column, try to inject UUID str. 
    # If the column is int, this might fail or cast, so we should be careful. 
    # However, 'users', 'clients' use UUID strings. 'projects', 'tasks' use Ints.
    # We can inspect the column type or just try to inject for known string ID tables)
    
    # Better approach: check column type.
    pk_constraint = inspector.get_pk_constraint(table_name)
    pk_cols = pk_constraint.get('constrained_columns', [])
    if 'id' in valid_columns and 'id' not in create_data:
        # Check if 'id' is a string column
        for col in inspector.get_columns(table_name):
            if col['name'] == 'id' and str(col['type']).startswith(('VARCHAR', 'TEXT', 'String')):
                create_data['id'] = str(uuid.uuid4())
                break

    # Auto-generate Timestamps
    now_iso = datetime.utcnow().isoformat()
    if 'created_at' in valid_columns and 'created_at' not in create_data:
        create_data['created_at'] = now_iso
    if 'updated_at' in valid_columns and 'updated_at' not in create_data:
        create_data['updated_at'] = now_iso

    # Extract many-to-many fields BEFORE validation (they're not real columns)
    many_to_many_data = {}
    if table_name == "tasks" and "assignees" in create_data:
        many_to_many_data["assignees"] = create_data.pop("assignees")
    if table_name == "notes" and "shared_with" in create_data:
        many_to_many_data["shared_with"] = create_data.pop("shared_with")

    # 4. Final Validation
    for col in create_data.keys():
        if col not in valid_columns:
            raise HTTPException(status_code=400, detail=f"Column '{col}' not found in '{table_name}'")

    # 5. Construct Insert Query safely
    col_names_str = ", ".join([f"`{col}`" for col in create_data.keys()])
    val_placeholders = ", ".join([f":val_{i}" for i in range(len(create_data))])
    
    query_str = f"INSERT INTO `{table_name}` ({col_names_str}) VALUES ({val_placeholders})"
    
    params = {}
    for i, value in enumerate(create_data.values()):
        params[f"val_{i}"] = value

    try:
        with engine.connect() as connection:
            result = connection.execute(text(query_str), params)
            connection.commit()
            
            # Handle many-to-many relationships for tasks
            if table_name == "tasks" and "assignees" in many_to_many_data:
                # Get the newly created task ID
                task_id = result.lastrowid
                assignee_ids = many_to_many_data["assignees"]
                
                # Ensure it's a list
                if isinstance(assignee_ids, str):
                    assignee_ids = [assignee_ids]
                
                # Create TaskAssignee records
                for user_id in assignee_ids:
                    assign_query = text("INSERT INTO `task_assignees` (`task_id`, `user_id`) VALUES (:task_id, :user_id)")
                    connection.execute(assign_query, {"task_id": task_id, "user_id": user_id})
                connection.commit()
            
            # Handle many-to-many relationships for notes
            if table_name == "notes" and "shared_with" in many_to_many_data:
                # Get the newly created note ID
                note_id = result.lastrowid
                shared_user_ids = many_to_many_data["shared_with"]
                
                # Ensure it's a list
                if isinstance(shared_user_ids, str):
                    shared_user_ids = [shared_user_ids]
                
                # Create NoteShare records
                for user_id in shared_user_ids:
                    share_query = text("INSERT INTO `note_shares` (`note_id`, `user_id`) VALUES (:note_id, :user_id)")
                    connection.execute(share_query, {"note_id": note_id, "user_id": user_id})
                connection.commit()
            
            return {"status": "success", "detail": "Record created"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
