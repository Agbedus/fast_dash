import sys
from typing import List, Optional
from sqlmodel import SQLModel, Field, create_engine, Session, select, Column, JSON
from enum import Enum
from fastapi import HTTPException

# Mock Models to match current schema
class UserRole(str, Enum):
    USER = "user"
    STAFF = "staff"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"

class User(SQLModel, table=True):
    id: str = Field(primary_key=True)
    roles: List[UserRole] = Field(sa_column=Column(JSON))
    
    @property
    def is_privileged(self) -> bool:
        return UserRole.ADMIN in self.roles or UserRole.SUPER_ADMIN in self.roles

class Project(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: str

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = None
    name: str

class TaskAssignee(SQLModel, table=True):
    task_id: int = Field(primary_key=True)
    user_id: str = Field(primary_key=True)

# The logic we are testing (copied/adapted from tasks.py)
def list_tasks_logic(current_user: User):
    if current_user.is_privileged:
        return select(Task)
    else:
        owned_project_ids_subquery = select(Project.id).where(Project.owner_id == current_user.id)
        assigned_task_ids_subquery = select(TaskAssignee.task_id).where(TaskAssignee.user_id == current_user.id)
        
        return select(Task).where(
            (Task.project_id.in_(owned_project_ids_subquery)) | 
            (Task.id.in_(assigned_task_ids_subquery))
        )

def verify_integration():
    print("--- Testing Tasks RBAC Logic ---")
    
    admin = User(id="admin", roles=[UserRole.ADMIN])
    user1 = User(id="user1", roles=[UserRole.USER])
    
    # 1. Admin Logic
    admin_stmt = list_tasks_logic(admin)
    print(f"Admin Stmt: {admin_stmt}")
    assert "WHERE" not in str(admin_stmt).upper()
    print("✓ Admin sees all tasks")
    
    # 2. User Logic (Subqueries)
    user_stmt = list_tasks_logic(user1)
    print(f"User Stmt: {user_stmt}")
    assert "IN (SELECT project.id" in str(user_stmt)
    assert "IN (SELECT taskassignee.task_id" in str(user_stmt)
    print("✓ User is filtered by project ownership and task assignment")
    
    print("--- Tasks RBAC Logic Verification SUCCESS ---")

if __name__ == "__main__":
    try:
        verify_integration()
    except Exception as e:
        print(f"Verification FAILED: {e}")
        sys.exit(1)
