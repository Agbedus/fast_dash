import json
from sqlmodel import Session, select, text
from app.db.session import engine
from app.models.user import User, UserRole

def migrate_roles():
    print("--- Starting User Role Migration ---")
    with Session(engine) as session:
        # Get all users
        statement = select(User)
        users = session.exec(statement).all()
        
        updated_count = 0
        for user in users:
            roles = user.roles
            if "admin" in roles:
                print(f"Updating user {user.email}: {roles} -> ", end="")
                # Replace 'admin' with 'super_admin'
                new_roles = [r if r != "admin" else UserRole.SUPER_ADMIN for r in roles]
                # Ensure no duplicates if they already had super_admin
                new_roles = list(set(new_roles))
                user.roles = new_roles
                session.add(user)
                updated_count += 1
                print(f"{new_roles}")
        
        session.commit()
        print(f"--- Migration Completed. Updated {updated_count} users. ---")

if __name__ == "__main__":
    try:
        migrate_roles()
    except Exception as e:
        print(f"Migration FAILED: {e}")
        # Try raw SQL if model validation fails
        print("Attempting raw SQL fallback...")
        try:
            with engine.connect() as conn:
                # This is a bit risky for JSON but for 'admin' string it should work
                conn.execute(text("UPDATE users SET roles = REPLACE(roles, '\"admin\"', '\"super_admin\"')"))
                conn.commit()
            print("Raw SQL migration successful.")
        except Exception as e2:
            print(f"Raw SQL fallback FAILED: {e2}")
